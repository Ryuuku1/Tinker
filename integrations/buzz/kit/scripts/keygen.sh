#!/usr/bin/env bash
# Kit identities (admin, agent) and relay secrets. Runs once, as root in the relay image:
#   keygen.sh <port> <relay-image>
# Writes the key files into their volumes and /out/.env inside the container (setup copies it out with docker cp);
# prints PUBLIC keys only. Refuses to run over existing keys.
set -euo pipefail
umask 077
port=${1:?port}; image=${2:?relay image}
mkdir -p /out
[ ! -e /out/.env ] || { echo "refusing: .env exists"; exit 1; }
[ ! -e /humankeys/admin.sec ] && [ ! -e /agentkey/agent.sec ] || { echo "refusing: keys exist"; exit 1; }
gen() {  # gen <dir> <name>
  local out; out=$(buzz-admin generate-key)
  [[ $out =~ Public\ key:[[:space:]]+([0-9a-f]{64}) ]] || { echo "unexpected generate-key output"; exit 1; }
  printf '%s' "${BASH_REMATCH[1]}" > "$1/$2.pub"
  [[ $out =~ Secret\ key:[[:space:]]+([^[:space:]]+) ]] || { echo "unexpected generate-key output"; exit 1; }
  printf '%s' "${BASH_REMATCH[1]}" > "$1/$2.sec"
}
gen /humankeys admin; gen /agentkey agent
relay=$(buzz-admin generate-key)
[[ $relay =~ Secret\ key:[[:space:]]+([^[:space:]]+) ]] || { echo "unexpected generate-key output"; exit 1; }
relay_sec=${BASH_REMATCH[1]}
rand() { head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n'; }
# RELAY_URL's authority (localhost:<port>) is the exact Host every client must send; there is no fallback tenant.
cat > /out/.env <<EOF
BUZZ_IMAGE=$image
BUZZ_DOMAIN=localhost
RELAY_URL=ws://localhost:$port
BUZZ_MEDIA_BASE_URL=http://localhost:$port/media
BUZZ_MEDIA_SERVER_DOMAIN=localhost:$port
BUZZ_CORS_ORIGINS=http://localhost:$port
BUZZ_REQUIRE_AUTH_TOKEN=true
BUZZ_REQUIRE_RELAY_MEMBERSHIP=true
BUZZ_ALLOW_NIP_OA_AUTH=true
BUZZ_AUTO_MIGRATE=true
BUZZ_GIT_CONFORMANCE_PROBE=false
BUZZ_PUSH_ENABLED=false
BUZZ_PUSH_GATEWAY_DELIVERY_URL=https://push.invalid/v1/deliveries/apns
RUST_LOG=buzz_relay=info,buzz_db=info,buzz_auth=info
RELAY_OWNER_PUBKEY=$(cat /humankeys/admin.pub)
BUZZ_RELAY_PRIVATE_KEY=$relay_sec
BUZZ_GIT_HOOK_HMAC_SECRET=$(rand)
POSTGRES_DB=buzz
POSTGRES_USER=buzz
POSTGRES_PASSWORD=$(rand)
REDIS_PASSWORD=$(rand)
BUZZ_S3_ACCESS_KEY=kit$(rand | head -c 12)
BUZZ_S3_SECRET_KEY=$(rand)
BUZZ_S3_BUCKET=buzz-media
BUZZ_S3_ADDRESSING_STYLE=path
BUZZ_HTTP_PORT=127.0.0.1:$port
EOF
cp /agentkey/agent.pub /humankeys/agent.pub
chown -R 10001:10001 /humankeys /agentkey
chmod 400 /humankeys/*.sec /agentkey/*.sec; chmod 444 /humankeys/*.pub /agentkey/*.pub
for w in admin agent; do echo "$w=$(cat /humankeys/$w.pub)"; done
