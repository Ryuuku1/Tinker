#!/usr/bin/env bash
# Sets up a local Buzz relay and Tinker's team on this Debian (or other Linux) PC: the bash twin of setup.ps1. Five
# agents (Tinker the Lead, Tinker Planner, Tester, Reviewer and Researcher) and Tinker Flow, which runs whole flows
# across them, owned by your Buzz Desktop identity.
#
# Run it with no arguments for the wizard: it asks a few questions, sets everything up, and asks for your npub once
# Buzz Desktop shows it. With arguments it runs unattended. Idempotent and resumable: after a failure, fix the cause
# and run it again. It never regenerates keys over an existing relay. Keys and relay secrets are generated inside
# containers and never printed; the credential file is only passed to Docker. The only host folders a container
# mounts are the --repository folders, read-only. See GUIDE.md and EXAMPLES.md.
#
#   ./setup.sh                                       # the wizard
#   ./setup.sh --owner-npub npub1... --credential-file ~/tinker-buzz-secrets/claude.env \
#              --repository ~/src/app --repository ~/src/lib
#
# Options (the PowerShell parameter names work too, e.g. -OwnerNpub):
#   --project NAME          default tinker-buzz
#   --port N                1024-65535, default 3000
#   --tinker-repo DIR       default: this checkout
#   --tinker-commit SHA     default: the kit's pin
#   --credential-file FILE  a path only: passed to docker --env-file, never read
#   --owner-npub NPUB       your Buzz Desktop npub; without it, setup stops once the relay and channels are up
#   --repository DIR        repeatable; folders every agent reads at /repos/<name>, read-only; kept for reruns,
#                           --repository '' removes them
#   --state-root DIR        default ${XDG_DATA_HOME:-~/.local/share}/TinkerBuzz; pass the same value to kit.sh and
#                           teardown.sh
set -o pipefail
SELF=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/$(basename -- "${BASH_SOURCE[0]}")
KITDIR=$(dirname -- "$SELF")

Project=tinker-buzz; Port=3000; TinkerRepo="$KITDIR/../../.."; TinkerCommit=; CredentialFile=; OwnerNpub=
Repository=(); RepositoryBound=0; StateRoot=
ARGC=$#
die() { printf 'Error: %s\n' "$*" >&2; exit 1; }
while (($#)); do
  opt=${1,,}; opt=${opt#--}; opt=${opt#-}; opt=${opt//-/}
  (($# >= 2)) || die "$1 needs a value"
  case $opt in
    project) Project=$2 ;;
    port) Port=$2 ;;
    tinkerrepo) TinkerRepo=$2 ;;
    tinkercommit) TinkerCommit=$2 ;;
    credentialfile) CredentialFile=$2 ;;
    ownernpub) OwnerNpub=$2 ;;
    repository) RepositoryBound=1; [[ -n $2 ]] && Repository+=("$2") ;;
    stateroot) StateRoot=$2 ;;
    *) die "Unknown option: $1 (see the top of setup.sh)" ;;
  esac
  shift 2
done
[[ $Port =~ ^[0-9]{1,5}$ ]] && ((10#$Port >= 1024 && 10#$Port <= 65535)) || die "Port must be 1024 to 65535: $Port"
Port=$((10#$Port))

# The wizard: no arguments in an interactive terminal. It runs this script twice, before and after your npub.
if ((ARGC == 0)) && [[ -t 0 && -t 1 ]]; then
  . "$KITDIR/kit.sh" || exit 1
  printf "Tinker's team in Buzz: this sets up a private relay, five agents and Tinker Flow on this PC (GUIDE.md).\n\n"
  if ! Read-SetupAnswers; then echo 'Nothing was changed.'; exit 0; fi
  answers=(--project "$ANSWER_PROJECT" --port "$ANSWER_PORT" --credential-file "$ANSWER_CREDENTIAL_FILE")
  if ((${#ANSWER_REPOSITORY[@]})); then for r in "${ANSWER_REPOSITORY[@]}"; do answers+=(--repository "$r"); done
  else answers+=(--repository ''); fi
  bash "$SELF" "${answers[@]}" || exit 1
  . "$KITDIR/kit.sh" --project "$ANSWER_PROJECT" || exit 1
  if [[ -z $(Read-KitState | jq -r '.owner // empty') ]]; then
    printf '\nIn Buzz Desktop: Add Community, enter ws://localhost:%s, and copy the npub it shows.\n' "$ANSWER_PORT"
    npub=
    until [[ $npub =~ ^npub1[02-9ac-hj-np-z]{58}$ ]]; do
      IFS= read -r -p 'Your npub: ' npub || exit 1
      npub=$(sed 's/^[[:space:]]*//; s/[[:space:]]*$//' <<<"$npub")
    done
    bash "$SELF" "${answers[@]}" --owner-npub "$npub" || exit 1
    printf '\nBack in Buzz Desktop, press Try again, then open #tinker-lab.\n'
  fi
  exit 0
fi
. "$KITDIR/kit.sh" --project "$Project" --state-root "$StateRoot" || exit 1
[[ -d $TinkerRepo ]] || die "Tinker repository not found: $TinkerRepo"
TinkerRepo=$(cd -- "$TinkerRepo" && pwd -P)
[[ -n $TinkerCommit ]] || TinkerCommit=$PIN_TINKER_COMMIT
if [[ -n $OwnerNpub && ! $OwnerNpub =~ ^(npub1[02-9ac-hj-np-z]{58}|[0-9a-f]{64})$ ]]; then die "Not an npub: $OwnerNpub"; fi
resolved=()
for r in "${Repository[@]}"; do
  r=${r/#\~/$HOME}
  [[ -d $r ]] || die "Repository folder not found: $r"
  r=$(cd -- "$r" && pwd -P)
  if [[ -f $r/.git ]]; then   # its .git names a gitdir path outside the mount
    die "A git worktree cannot be mounted, since git inside the container cannot follow its .git file: pass the main clone ($r)"
  fi
  resolved+=("$r")
done
Repository=("${resolved[@]}")
if ((${#Repository[@]})) && [[ -n $(for r in "${Repository[@]}"; do echo "${r##*/}"; done | sort | uniq -d) ]]; then
  die 'Two repositories share a folder name, so they would share one /repos/<name>: rename one'
fi
LOGS="$STATE/logs"; ENVFILE="$STATE/.env"; CTX="$STATE/agent"; ROLES=("${AGENT_ROLES[@]}")
profile_name() { if [[ $1 == flow ]]; then echo "$FLOW_NAME"; else echo "${AGENT_NAME[$1]}"; fi; }
profile_about() { if [[ $1 == flow ]]; then echo "$FLOW_ABOUT"; else echo "${AGENT_ABOUT[$1]}"; fi; }
KITARGS="--project $Project"; [[ -n $StateRoot ]] && KITARGS+=" --state-root '$StateRoot'"   # for the hints below
n=0
Step() { n=$((n + 1)); printf '\n[%d/12] %s\n' "$n" "$1"; }
s_get() { jq -r "$1 // empty" <<<"$S"; }                       # s_get <path>: one value of the settings, or nothing
s_set() { local f=$1; shift; S=$(jq -c "$@" "$f" <<<"$S") || die "Updating the settings failed ($f)"; }
save() { Save-KitState "$S" || exit 1; }
# Final check: file names in the kit folder or the setup logs that hold a key, a relay secret or the credential.
Invoke-SecretScan() {
  printf '\nFinal check: secret scan of the kit folder and the setup logs\n'
  local scan=(create --label "tinker.kit=$Project" --user 0:0 -v "${VOL[humankeys]}:/humankeys:ro") id c result cred
  for id in "${IDENTITIES[@]}"; do scan+=(-v "${VOL[$id-key]}:/keys/$id:ro"); done
  cred=$(s_get .credentialFile); [[ -n $cred ]] && scan+=(--env-file "$cred")
  c=$(docker "${scan[@]}" "$(s_get .image)" bash /kit/secretscan.sh /tmp/relay.env /tmp/kit /tmp/logs) || die 'creating the scan container failed'
  docker cp "$ENVFILE" "$c:/tmp/relay.env" >/dev/null; docker cp "$KIT" "$c:/tmp/kit" >/dev/null; docker cp "$LOGS" "$c:/tmp/logs" >/dev/null
  result=$(docker start -a "$c"); docker rm -f "$c" >/dev/null
  sed 's/^/  /' <<<"$result"
  kit_has_line "$result" 'secret-scan hits=0' ||
    die 'A secret was found in the kit folder or the logs (file names above): delete that copy and rotate the secret'
}

Step 'Preflight: Docker with Linux containers, Compose, buildx, Git, a free port'
os=$(docker version --format '{{.Server.Os}}' 2>/dev/null)
if [[ $? -ne 0 || $os != linux ]]; then
  die 'Docker is not reachable: start it (sudo systemctl start docker) and let your user use it (sudo usermod -aG docker "$USER", then log in again)'
fi
compose=$(docker compose version --short 2>/dev/null) || die 'Docker Compose v2 is required: sudo apt install docker-compose-plugin (Docker repository) or docker-compose-v2'
compose=${compose#v}; cv=${compose%%[!0-9.]*}
[[ $(printf '%s\n%s\n' 2.24.4 "$cv" | sort -V | head -n1) == 2.24.4 ]] || die "Docker Compose 2.24.4 or newer is required (found $compose)"
docker buildx version >/dev/null 2>&1 || die 'Docker buildx is required for the agent image (its build uses cache mounts): sudo apt install docker-buildx-plugin (Docker repository) or docker-buildx'
command -v git >/dev/null || die 'Git is required'
command -v curl >/dev/null || die 'curl is required'
git -C "$TinkerRepo" cat-file -e "$TinkerCommit^{commit}" 2>/dev/null ||
  die "Tinker commit $TinkerCommit is not in $TinkerRepo: fetch it, or pass --tinker-repo and --tinker-commit"
mkdir -p -- "$STATE" "$LOGS" || die "Cannot create $STATE"
S=$(Read-KitState) || exit 1
if [[ -n $(s_get .port) && $(s_get .port) != "$Port" && -f $ENVFILE ]]; then
  die "This project was set up on port $(s_get .port): use --port $(s_get .port), or run teardown.sh first"
fi
ours=0
[[ -f $STATE/compose.yml && -f $ENVFILE && -n $(Invoke-Compose ps -q relay 2>/dev/null) ]] && ours=1
if ((!ours)) && ! Test-PortFree "$Port"; then die "Port $Port is in use: choose another with --port"; fi
s_set '.project = $p | .port = $n | .tinkerCommit = $c' --arg p "$Project" --argjson n "$Port" --arg c "$TinkerCommit"
if ((RepositoryBound)); then s_set '.repositories = $r' --argjson r "$(json_array "${Repository[@]}")"; fi
s_set '.channels //= {} | .agentConfig //= {}'
save
echo "  Docker $os, Compose $compose, state folder $STATE"
while IFS=$'\t' read -r host path; do echo "  Repository $host, read-only at $path"; done < <(Get-RepoMounts "$S")

Step 'Pinned relay image'
docker pull --quiet "$PIN_RELAY_IMAGE" >/dev/null || die "docker pull $PIN_RELAY_IMAGE failed"
[[ $(docker image inspect "$PIN_RELAY_IMAGE" --format '{{index .Config.Labels "org.opencontainers.image.revision"}}') == "$PIN_RELAY_REVISION" ]] ||
  die 'The relay image revision label does not match the pin'
digest=${PIN_RELAY_IMAGE#*@}
echo "  ${digest:0:19}... revision ${PIN_RELAY_REVISION:0:9}"

Step 'Build buzz-acp and buzz from the pinned Buzz source, and the agent image with Tinker (one docker build)'
mapfile -t inputs < <(printf '%s\n' "$KIT/agent/Dockerfile" "$KIT/agent/deny.py"
                      find "$KIT/scripts" "$KIT/roles" -maxdepth 1 -type f | LC_ALL=C sort)
kitHash=$(for f in "${inputs[@]}"; do kit_file_sha256_upper "$f"; done | tr -d '\n' | kit_sha256)
image="$Project-agent:${TinkerCommit:0:12}-${kitHash:0:8}"   # new Tinker commit or kit files: new image
if [[ -z $(docker images -q "$image") ]]; then
  rm -rf -- "$CTX/scripts" "$CTX/roles"   # no stale files
  mkdir -p -- "$CTX/scripts" "$CTX/roles"
  git -c core.autocrlf=false -C "$TinkerRepo" archive --format=tar --prefix=tinker/ -o "$CTX/tinker.tar" "$TinkerCommit" ||
    die 'git archive of Tinker failed'
  cp -f -- "$KIT/agent/Dockerfile" "$KIT/agent/deny.py" "$CTX/"
  cp -f -- "$KIT"/scripts/* "$CTX/scripts/"
  cp -f -- "$KIT"/roles/* "$CTX/roles/"
  echo '  First build: 10-30 minutes, mostly downloads and Rust (log: logs/build-agent.log); a rerun resumes from the cache'
  DOCKER_BUILDKIT=1 docker build -t "$image" "$CTX" > "$LOGS/build-agent.log" 2>&1 || die "docker build failed (see $LOGS/build-agent.log)"
fi
echo "  $image"

Step 'Verify the build: Buzz and archify commits, Cargo Git sources, compose file, binaries, Claude Code, Tinker, the prompts'
facts=$(docker run --rm "$image" bash -c 'cat /kit/buzz-commit.txt /kit/cargo-git.txt /kit/binaries.sha256' | tr -d '\r')
kit_has_line "$facts" "$PIN_BUZZ_COMMIT" || die 'The image was not built from the pinned Buzz commit'
[[ $(docker run --rm "$image" cat /kit/archify-commit.txt | tr -d '\r') == "$PIN_ARCHIFY_COMMIT" ]] ||
  die 'The image was not built from the pinned archify commit'
gitSources=$(grep -oE 'source = "git\+[^"]+"' <<<"$facts" | sed -E 's/^source = "(.*)"$/\1/' | LC_ALL=C sort -u)
[[ $gitSources == "$(printf '%s\n' "${PIN_CARGO_GIT[@]}" | LC_ALL=C sort -u)" ]] || die 'Cargo.lock names Git sources other than the pinned three'
for b in buzz-acp buzz; do
  h=$(grep -E "^[0-9a-f]{64}[[:space:]]+$b$" <<<"$facts" | head -n1 | cut -c1-64)
  if [[ $h == "${PIN_BINARIES[$b]}" ]]; then echo "  $b sha256 matches the lab build"; else echo "  $b sha256 $h (the lab build was ${PIN_BINARIES[$b]})"; fi
done
c=$(docker create "$image") || die 'creating a container to copy compose.yml failed'
docker cp "$c:/kit/compose.yml" "$STATE/compose.yml" >/dev/null; rc=$?
docker rm -f "$c" >/dev/null
((rc == 0)) || die 'copying compose.yml failed'
[[ $(kit_sha256 < "$STATE/compose.yml") == "$PIN_COMPOSE_SHA256" ]] || die 'compose.yml does not match its pinned SHA-256'
check=$(docker run --rm "$image" bash -c 'claude --version; claude plugin list; jq ".permissions.deny | length" ~/.claude/settings.json; '\
'jq .apiKeyHelper ~/.claude/settings.json; compgen -e | grep -cE "^(ANTHROPIC_|CLAUDE_CODE_OAUTH_TOKEN$|CLAUDE_CODE_USE_)"; '\
'jq -r "(.env // {}) | keys[]" ~/.claude/settings.json | grep -cE "^(ANTHROPIC_|CLAUDE_CODE_OAUTH_TOKEN$|CLAUDE_CODE_USE_)"; '\
'git hash-object /opt/tinker/scripts/tinker_runtime.py; buzz-acp --help | head -n 1; grep -c "claude-agent-acp@0.81.2" /opt/acp/npm-ls.txt; '\
"for r in ${ROLES[*]}; do { cat /opt/tinker/integrations/buzz/protocol.md; echo; cat \"/kit/roles/\$r.md\"; } | "\
'cmp -s - "/kit/prompts/$r.md" && echo "prompt $r"; done; git config --system --get core.autocrlf; '\
'for f in base.md flow.py flows.json usage.py rules.py; do test -s "/kit/$f" && echo "kit $f"; done' | tr -d '\r')
# archify as the agents run it (their user, no capabilities, no network): a bundled example through its full gate.
archify=$(docker run --rm --cap-drop ALL --security-opt no-new-privileges:true --network none "$image" bash -c \
  'a=~/.claude/skills/archify; test -w "$a" || echo read-only; echo "updates=${ARCHIFY_UPDATE_CHECK_DISABLED:-on}"; '\
'mkdir /tmp/d && cp "$a/examples/web-app.architecture.json" /tmp/d/c.json && cd /tmp/d && '\
'node "$a/bin/archify.mjs" finalize architecture c.json web-app.html --quality showcase --json | jq -r .status' | tr -d '\r')
blob=$(git -C "$TinkerRepo" rev-parse "$TinkerCommit:scripts/tinker_runtime.py")
# has_seq <text> <line>...: those whole lines, one right after another.
has_seq() { local text=$'\n'$1$'\n' want=$'\n'; shift; local l; for l; do want+=$l$'\n'; done; [[ $text == *"$want"* ]]; }
nl=$'\n'
prompts_ok() { local r; for r in "${ROLES[@]}"; do kit_has_line "$check" "prompt $r" || return 1; done; }
kit_files_ok() { kit_has_line "$check" input || return 1; local f; for f in base.md flow.py flows.json usage.py rules.py; do kit_has_line "$check" "kit $f" || return 1; done; }
checks=(
  'Buzz commit, 3 Cargo Git sources and compose.yml pinned' "$(kit_bool true)"
  'Claude Code 2.1.280' "$(kit_bool grep -qE '2\.1\.280 \(Claude Code\)' <<<"$check")"
  'tinker plugin enabled' "$(kit_bool eval '[[ $check == *tinker@tinker-local*enabled* ]]')"
  "6 deny rules (the Lead's), no apiKeyHelper, no credential names" "$(kit_bool has_seq "$check" 6 null 0 0)"
  'runtime matches the Tinker commit' "$(kit_bool eval '[[ -n $blob && $check == *"$blob"* ]]')"
  'buzz-acp runs; claude-agent-acp 0.81.2' "$(kit_bool eval '[[ $check =~ "ACP harness that bridges Buzz events to AI agents"$nl[1-9] ]]')"
  'each role prompt is the protocol, then its role file' "$(kit_bool prompts_ok)"
  'git reads CRLF checkouts; base prompt, Tinker Flow, usage and rules files present' "$(kit_bool kit_files_ok)"
  'archify files root-owned, no update checks; its full gate passes offline in Chromium' "$(kit_bool has_seq "$archify" read-only updates=1 pass)"
)
failedCheck=0
for ((i = 0; i < ${#checks[@]}; i += 2)); do
  echo "  ${checks[i]}: ${checks[i + 1]}"; [[ ${checks[i + 1]} == True ]] || failedCheck=1
done
((failedCheck == 0)) || die 'The agent image check failed'
s_set '.image = $i' --arg i "$image"; save

Step 'Keys and relay secrets, generated inside containers and never printed'
first=0; [[ -f $ENVFILE ]] || first=1
if ((!first)) && [[ -z $(s_get .admin) ]]; then die '.env exists but kit.json lacks the admin key: run teardown.sh, then setup again'; fi
s_set '.agents //= {}'
missing=(); for id in "${IDENTITIES[@]}"; do [[ -n $(s_get ".agents[\"$id\"]") ]] || missing+=("$id"); done
if ((!first && ${#missing[@]} == 0)); then echo '  Keys exist; never regenerated over a relay'; else
  if ((first)) && kit_has_line "$(docker volume ls -q)" "${Project}_buzz-postgres-data"; then
    die 'The relay database exists but .env is gone: run teardown.sh to start over'
  fi
  mounts=(-v "${VOL[humankeys]}:/humankeys"); for id in "${IDENTITIES[@]}"; do mounts+=(-v "${VOL[$id-key]}:/keys/$id"); done
  c=$(docker create --label "tinker.kit=$Project" --user 0:0 --entrypoint bash "${mounts[@]}" "$PIN_RELAY_IMAGE" /tmp/keygen.sh \
      "$Port" "$PIN_RELAY_IMAGE" "${IDENTITIES[@]}") || die 'creating the key container failed'
  err=
  if ! docker cp "$KIT/scripts/keygen.sh" "$c:/tmp/keygen.sh" >/dev/null; then err='copying keygen.sh failed'
  else
    out=$(docker start -a "$c" | tr -d '\r'); rc=$?   # public keys only; existing keys are kept
    if ((rc)); then err="Key generation failed: $out"
    elif ((first)) && ! docker cp "$c:/out/.env" "$ENVFILE" >/dev/null; then
      err='The admin key exists without relay secrets: run teardown.sh to start over'
    fi
  fi
  docker rm -f "$c" >/dev/null
  [[ -z $err ]] || die "$err"
  declare -A keys=()
  while IFS= read -r l; do [[ $l =~ ^([a-z]+)=([0-9a-f]{64})$ ]] && keys[${BASH_REMATCH[1]}]=${BASH_REMATCH[2]}; done <<<"$out"
  # Keys kit.json already knows must come back unchanged: a different one means the volumes and kit.json disagree.
  for k in admin "${IDENTITIES[@]}"; do
    if [[ $k == admin ]]; then known=$(s_get .admin); else known=$(s_get ".agents[\"$k\"]"); fi
    if [[ -z ${keys[$k]-} ]] || [[ -n $known && $known != "${keys[$k]}" ]]; then die "The $k key does not match kit.json: run teardown.sh to start over"; fi
  done
  s_set '.admin = $a' --arg a "${keys[admin]}"
  for r in "${IDENTITIES[@]}"; do s_set '.agents[$r] = $k' --arg r "$r" --arg k "${keys[$r]}"; done
  save
  if ((first)); then echo "  Generated the admin identity, one per agent ($(kit_join ', ' "${ROLES[@]}")), Tinker Flow's and the relay secrets"
  else echo "  Generated identities for: $(kit_join ', ' "${missing[@]}")"; fi
fi

Step "Relay up, published on 127.0.0.1:$Port only"
Invoke-Compose config --quiet || die 'compose config failed'
Invoke-Compose up -d --wait > "$LOGS/compose-up.log" 2>&1 || die "compose up failed (see $LOGS/compose-up.log)"
mapfile -t published < <(docker port "$Project-relay-1" 3000)
if ((${#published[@]} != 1)) || [[ ${published[0]} != "127.0.0.1:$Port" ]]; then
  die "The relay must be published on 127.0.0.1:$Port only, not: ${published[*]}"
fi
Invoke-Compose ps --format '  {{.Service}}: {{.State}} {{.Health}}'

Step 'Bootstrap check and routing probe'
relayLog=$(Invoke-Compose logs relay 2>&1)
if ! grep -qF "Deployment community ensured\",\"host\":\"localhost:$Port\"" <<<"$relayLog" || ! grep -q 'Relay owner bootstrapped' <<<"$relayLog"; then
  die "The relay did not bootstrap the community for localhost:$Port: check 'docker logs $Project-relay-1'"
fi
ws=(-s -o /dev/null -m 3 -w '%{http_code}' -H 'Connection: Upgrade' -H 'Upgrade: websocket'
    -H 'Sec-WebSocket-Version: 13' -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==')
hostCode=$(curl "${ws[@]}" "http://localhost:$Port/")
wrongCode=$(curl "${ws[@]}" -H 'Host: relay:3000' "http://localhost:$Port/")
probe='. /kit/forward.sh; curl -s -o /dev/null -m 3 -w "%{http_code}" -H "Connection: Upgrade" -H "Upgrade: websocket" '\
'-H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" "http://localhost:$KIT_PORT/"'
inCode=$(docker run --rm --label "tinker.kit=$Project" --network "$NET" -e "KIT_PORT=$Port" "$image" bash -c "$probe")
codes="host=$hostCode wrong-host=$wrongCode container=$inCode"   # curl exits 28 after the upgrade; only the codes count
echo "  $codes"
[[ $codes == 'host=101 wrong-host=404 container=101' ]] || die 'Routing probe failed: clients must reach the relay as localhost:<port>'

Step 'Relay membership (buzz-admin add-member)'
Add-RelayMember() {
  local o; o=$(Invoke-Compose exec -T relay buzz-admin add-member --pubkey "$1" 2>&1 < /dev/null)
  [[ $o =~ (added|already\ a\ member:)[[:space:]]*([0-9a-f]{64}) ]] || die "add-member failed for $1"
  echo "${BASH_REMATCH[2]}"
}
for r in "${IDENTITIES[@]}"; do Add-RelayMember "$(s_get ".agents[\"$r\"]")" >/dev/null || exit 1; done
s_set '.agentMembership = "direct"'   # a direct member never gets an owner recorded; see GUIDE.md, Phase 2
if [[ -n $OwnerNpub ]]; then owner=$(Add-RelayMember "$OwnerNpub") || exit 1; s_set '.owner = $o' --arg o "$owner"; fi
save
for r in "${IDENTITIES[@]}"; do printf '  %-18s %s\n' "$(profile_name "$r")" "$(ConvertTo-Npub "$(s_get ".agents[\"$r\"]")")"; done
[[ -n $(s_get .owner) ]] && printf '  %-18s %s\n' Owner "$(ConvertTo-Npub "$(s_get .owner)")"

Step 'Profiles: a name and an about line, published with each identity'
for r in "${IDENTITIES[@]}"; do
  Invoke-As "$r" users set-profile --name "$(profile_name "$r")" --about "$(profile_about "$r")" < /dev/null > /dev/null ||
    die "setting the $r profile failed"
  echo "  $(profile_name "$r")"
done

Step 'Channels: the owner and every agent as members, a purpose and a canvas each'
all=$(Invoke-Admin channels list < /dev/null) || die 'listing the channels failed'
for name in "${CHANNEL_NAMES[@]}"; do
  id=$(jq -r --arg n "$name" '[.[] | select(.name == $n)][0].channel_id // empty' <<<"$all")
  if [[ -z $id ]]; then
    Invoke-Admin channels create --name "$name" --type stream --visibility open --description "${CHANNEL_PURPOSE[$name]}" < /dev/null > /dev/null ||
      die "creating #$name failed"
    all=$(Invoke-Admin channels list < /dev/null) || die 'listing the channels failed'
    id=$(jq -r --arg n "$name" '[.[] | select(.name == $n)][0].channel_id // empty' <<<"$all")
  fi
  [[ -n $id ]] || die "#$name was not found after creating it"
  s_set '.channels[$n] = $i' --arg n "$name" --arg i "$id"; changed=()
  members=$(Invoke-Admin channels members --channel "$id" < /dev/null | jq -r '.[].pubkey')
  for k in $(for r in "${IDENTITIES[@]}"; do s_get ".agents[\"$r\"]"; done) $(s_get .owner); do
    kit_has_line "$members" "$k" && continue
    Invoke-Admin channels add-member --channel "$id" --pubkey "$k" < /dev/null > /dev/null || die "adding a member to #$name failed"
    changed+=(member)
  done
  purpose=$(Invoke-Admin channels search --query "$name" < /dev/null | jq -r --arg i "$id" '.[] | select(.channel_id == $i) | .purpose // empty')   # get omits the purpose
  if [[ $purpose != "${CHANNEL_PURPOSE[$name]}" ]]; then
    Invoke-Admin channels purpose --channel "$id" --purpose "${CHANNEL_PURPOSE[$name]}" < /dev/null > /dev/null || die "setting the purpose of #$name failed"
    changed+=(purpose)
  fi
  canvas=$(kit_trim_end "$(cat "$KIT/channels/$name.md")")
  if [[ $(kit_trim_end "$(Invoke-Admin canvas get --channel "$id" < /dev/null | tr -d '\r')") != "$canvas" ]]; then
    printf '%s\n' "$canvas" | Invoke-Admin canvas set --channel "$id" --content - > /dev/null || die "setting the canvas of #$name failed"
    changed+=(canvas)
  fi
  line=$(printf '  #%-11s %s' "$name" "$id")
  ((${#changed[@]})) && line+="  (set: $(kit_join ', ' $(printf '%s\n' "${changed[@]}" | awk '!seen[$0]++')))"
  echo "$line"
done
save

[[ -n $CredentialFile ]] || CredentialFile=$(s_get .credentialFile)
if [[ -z $(s_get .owner) || -z $CredentialFile ]]; then   # the agents need both; stop here without starting anything
  again="./setup.sh $KITARGS --port $Port"
  printf '\nThe relay is up at ws://localhost:%s with the channels. Next (GUIDE.md, Buzz Desktop):\n' "$Port"
  if [[ -z $(s_get .owner) ]]; then
    echo "  1. In Buzz Desktop choose Add Community and enter ws://localhost:$Port."
    echo "  2. Copy your npub from 'Not a member yet', then run this again with it and your token file:"
    echo "     $again --owner-npub <your npub> --credential-file <your env file>"
    echo '  3. Back in Buzz Desktop, press Try again.'
  else
    echo "  1. In Buzz Desktop choose Add Community and enter ws://localhost:$Port: you are already a member."
    echo '  2. To start the agents, run this again with your token file (GUIDE.md, section 3):'
    echo "     $again --credential-file <your env file>"
  fi
  Invoke-SecretScan
  exit 0
fi

Step 'Start the agents with the safe settings and you as their owner'
CredentialFile=${CredentialFile/#\~/$HOME}
[[ -f $CredentialFile ]] || die "Credential file not found: $CredentialFile"
names=$(docker run --rm --env-file "$CredentialFile" "$image" bash -c \
  'compgen -e | grep -E "^(ANTHROPIC_|CLAUDE_CODE_OAUTH_TOKEN$|CLAUDE_CODE_USE_|AWS_|GOOGLE_|CLOUD_ML_)" | sort | paste -sd, -' | tr -d '\r')
if [[ $names != CLAUDE_CODE_OAUTH_TOKEN && $names != ANTHROPIC_API_KEY ]]; then
  die "The credential file must set exactly one of CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY (names found: $names)"
fi
echo "  Credential variable: $names (the value is never read)"
s_set '.credentialFile = $c' --arg c "$(cd -- "$(dirname -- "$CredentialFile")" && pwd -P)/$(basename -- "$CredentialFile")"
save
safe=$(kit_file_sha256_upper "$KIT/agent.env")
restart=()
for r in "${ROLES[@]}"; do   # restart an agent only when its run settings changed
  Get-AgentRunArgs "$r" "$S"
  wanted=$(printf '%s\n' "${RUN_ARGS[@]}" "$safe" | head -c -1 | kit_sha256 | tr a-f A-F)
  if kit_running "$Project-$r" && [[ $(s_get ".agentConfig[\"$r\"]") == "$wanted" ]]; then echo "  ${AGENT_NAME[$r]} is already running with these settings"
  else restart+=("$r"); s_set '.agentConfig[$r] = $w' --arg r "$r" --arg w "$wanted"; fi
done
Get-FlowRunArgs "$S"
flowWanted=$(printf '%s\n' "${RUN_ARGS[@]}" | head -c -1 | kit_sha256 | tr a-f A-F)
flowRestart=0
if ! kit_running "$Project-flow" || [[ $(s_get .agentConfig.flow) != "$flowWanted" ]]; then flowRestart=1; fi
s_set '.agentConfig.flow = $w' --arg w "$flowWanted"
save
if ((${#restart[@]})); then Stop-Agent "${restart[@]}" || exit 1; Start-Agent "${restart[@]}" || exit 1; fi
if ((flowRestart)); then Stop-Flow || exit 1; Start-Flow || exit 1; else echo '  Tinker Flow is already running with these settings'; fi

Step 'Startup check'
Test-AgentStartup || exit 1
Test-FlowStartup || exit 1
printf "\nTinker's team is running. In Buzz Desktop write to an agent in its own channel (#requests for Tinker), no @mention\n"
echo "needed, or run a whole flow by writing 'story <request>' in #flows. The team:"
for r in "${IDENTITIES[@]}"; do printf '  %-18s %s\n' "$(profile_name "$r")" "$(ConvertTo-Npub "$(s_get ".agents[\"$r\"]")")"; done
echo "Worked examples: EXAMPLES.md. Status: ./kit.sh $KITARGS Get-KitStatus; ./kit.sh $KITARGS Get-KitUsage   (Stop-Agent and Start-Agent there too)"
Invoke-SecretScan
