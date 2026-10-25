#!/usr/bin/env bash
# Additive current-Physlib gate. Historical ../check.sh is deliberately separate.
set -euo pipefail
BRIDGE_DIR="$(cd "$(dirname "$0")" && pwd)"
export PATH="$HOME/.elan/bin:$PATH"
export MATHLIB_NO_CACHE_ON_UPDATE=1
export LEAN_NUM_THREADS="${LEAN_NUM_THREADS:-4}"
cd "$BRIDGE_DIR"
if [[ "${1:-}" != "--no-cache" ]]; then
  # Resolve only pinned dependencies. The committed manifest fixes transitives.
  lake env true
  mapfile -t cache_modules < <(python3 cache_roots.py)
  if [[ "${#cache_modules[@]}" == 0 ]]; then
    echo "No cache imports found; refusing an accidental full-cache request" >&2
    exit 1
  fi
  lake exe cache get "${cache_modules[@]}"
fi
lake build --wfail
python3 audit.py
