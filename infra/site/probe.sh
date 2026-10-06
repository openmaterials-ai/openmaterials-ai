#!/bin/sh
# Post-deploy probe of the short-link store: a set whose lineage 1 cites an
# unregistered model must be refused with a 400 naming it. A Worker that
# refuses stores nothing; one that stores the probe is named with its revoke.
# Usage: infra/site/probe.sh [origin]   (default https://openmaterials.ai)
set -eu
origin=${1:-https://openmaterials.ai}
uid=$(printf '0%.0s' $(seq 64))
body='{"v":1,"lineages":[{"lineage":{"node":"ThermalConductivity","material":"probe"},"unregistered":[{"kind":"model","uid":"'$uid'"}]}]}'
resp=$(curl -sS --max-time 20 -w ' %{http_code}' -X POST -H 'origin: https://openmaterials.ai' \
  -H 'content-type: application/json' --data "$body" "$origin/s")
case "$resp" in
  *'Lineage 1 of 1'*'publish_private=1'*' 400') echo "ok: $origin/s refuses lineage 1" ;;
  *) echo "FAIL: $origin/s answered: $resp" >&2
     code=$(printf %s "$resp" | sed -n 's/.*"code":"\([^"]*\)".*/\1/p')
     [ -z "$code" ] || echo "it stored s:$code; revoke: npx wrangler kv key delete --binding SHORTLINKS --remote \"s:$code\"" >&2
     exit 1 ;;
esac
