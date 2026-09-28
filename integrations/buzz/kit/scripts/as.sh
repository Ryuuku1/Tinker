#!/usr/bin/env bash
# as.sh <key file> <buzz args...>: the buzz CLI as a kit identity (the admin or one agent). Never prints keys.
set -euo pipefail
. /kit/forward.sh
key=$1; shift
BUZZ_PRIVATE_KEY=$(cat "$key"); export BUZZ_PRIVATE_KEY
exec buzz --relay "http://localhost:$KIT_PORT" "$@"
