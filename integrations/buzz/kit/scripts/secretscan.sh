#!/usr/bin/env bash
# secretscan.sh <relay.env> <dir>...: names of files under the dirs that contain a kit secret (key files, relay
# secrets, the Claude credential), never the values, then hits=<0|1>. Runs as root with the key volumes (/humankeys,
# /keys/<role>) and the credential env file; setup copies the relay env file and the dirs in with docker cp.
set -uo pipefail
relay_env=${1:?relay env file}; shift
hits=0
for f in /humankeys/*.sec /keys/*/*.sec; do [ -s "$f" ] && { grep -rlF -f "$f" "$@" && hits=1; }; done
for v in "${CLAUDE_CODE_OAUTH_TOKEN:-}" "${ANTHROPIC_API_KEY:-}"; do [ -n "$v" ] && { grep -rlF -e "$v" "$@" && hits=1; }; done
while IFS='=' read -r k v; do
  case "$k" in BUZZ_RELAY_PRIVATE_KEY|BUZZ_GIT_HOOK_HMAC_SECRET|POSTGRES_PASSWORD|REDIS_PASSWORD|BUZZ_S3_SECRET_KEY)
    [ -n "$v" ] && { grep -rlF -e "$v" "$@" && hits=1; };; esac
done < "$relay_env"
echo "secret-scan hits=$hits"
