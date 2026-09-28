#!/usr/bin/env bash
# as.sh <identity> <buzz args...>: the buzz CLI as a kit identity (admin). Never prints keys.
set -euo pipefail
. /kit/forward.sh
who=$1; shift
BUZZ_PRIVATE_KEY=$(cat "/humankeys/$who.sec"); export BUZZ_PRIVATE_KEY
exec buzz --relay "http://localhost:$KIT_PORT" "$@"
