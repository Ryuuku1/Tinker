#!/usr/bin/env bash
# Stops the agents and the relay of one kit project; asks before deleting its data, keys, images or state folder.
# The bash twin of teardown.ps1.
#
# Without confirmation it only stops containers. Deleting the volumes removes the community, the admin and agent
# identities, the agents' work folder and the build caches; setup.sh then starts from scratch with new keys.
# Only resources named after --project are touched, by exact name. A folder mounted with --repository is never touched.
#
#   ./teardown.sh                          # stop, then asks before deleting volumes
#   ./teardown.sh --images --state-folder  # also asks before deleting the agent image and the state folder
#   Options: --project NAME, --state-root DIR, --yes (confirm every deletion without asking, like -Confirm:$false)
set -o pipefail
KITDIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
Project=tinker-buzz; StateRoot=; Images=0; StateFolder=0; Yes=0
die() { printf 'Error: %s\n' "$*" >&2; exit 1; }
while (($#)); do
  opt=${1,,}; opt=${opt#--}; opt=${opt#-}; opt=${opt//-/}
  case $opt in
    project) (($# >= 2)) || die "$1 needs a value"; Project=$2; shift ;;
    stateroot) (($# >= 2)) || die "$1 needs a value"; StateRoot=$2; shift ;;
    images) Images=1 ;;
    statefolder) StateFolder=1 ;;
    yes|y|confirm:\$false) Yes=1 ;;
    *) die "Unknown option: $1 (see the top of teardown.sh)" ;;
  esac
  shift
done
. "$KITDIR/kit.sh" --project "$Project" --state-root "$StateRoot" || exit 1
S=$(Read-KitState) || exit 1

# ShouldProcess: ask once per deletion (default no); --yes answers for you, and without a terminal nothing is deleted.
confirm() {
  ((Yes)) && return 0
  [[ -t 0 ]] || { echo "Skipped without --yes: $2 ($1)"; return 1; }
  local a; IFS= read -r -p "$2: $1. Continue? [y/N] " a || return 1
  [[ ${a,,} =~ ^(y|yes)$ ]]
}
save() { Save-KitState "$S" || exit 1; }

Stop-Agent || exit 1
Stop-Flow || exit 1
if [[ -f $STATE/compose.yml ]]; then Invoke-Compose down || die 'compose down failed'; fi
echo 'The agents and the relay are stopped.'

existing=$(docker volume ls -q)
ours=()   # + the one-Lead kit's key
for v in "${VOL[@]}" "$Project-agentkey"; do kit_has_line "$existing" "$v" && ours+=("$v"); done
composeVolumes=()
for v in "${Project}_buzz-postgres-data" "${Project}_buzz-redis-data" "${Project}_buzz-git-data"; do kit_has_line "$existing" "$v" && composeVolumes+=("$v"); done
all=("${ours[@]}" "${composeVolumes[@]}")
if ((${#all[@]})) && confirm "$(kit_join ', ' "${all[@]}")" 'Delete the relay data, the admin and agent keys, the work folder and the build caches'; then
  if [[ -f $STATE/compose.yml ]]; then Invoke-Compose down -v || die 'compose down -v failed'; fi
  for v in "${ours[@]}"; do docker volume rm "$v" >/dev/null || die "could not delete volume $v"; done
  rm -f -- "$STATE/.env"   # the relay secrets
  S=$(jq -c 'del(.admin, .agents, .owner, .channels, .agentMembership, .agentConfig, .agent, .leadConfig)' <<<"$S")
  save
  echo 'Deleted the volumes and the relay secrets; setup.sh will generate new identities.'
fi
image=$(jq -r '.image // empty' <<<"$S")
if ((Images)) && [[ -n $image && -n $(docker images -q "$image") ]] && confirm "$image" 'Delete the agent image'; then
  docker image rm "$image" >/dev/null || die "could not delete $image"
  S=$(jq -c 'del(.image)' <<<"$S"); save
fi
if ((StateFolder)) && [[ -d $STATE ]] && confirm "$STATE" 'Delete the state folder (sources, logs, kit.json)'; then
  left=$(docker volume ls -q)
  for v in "${VOL[@]}" "$Project-agentkey"; do kit_has_line "$left" "$v" && die 'Delete the volumes first: the state folder holds their .env'; done
  rm -rf -- "$STATE"
  echo "Deleted $STATE"
fi
echo 'Revoke the Claude token when you no longer need it (GUIDE.md, Cleanup).'
