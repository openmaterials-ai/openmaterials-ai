#!/usr/bin/env bash
# Build the map's Lean package against its pinned Physlib and audit its axioms.
set -euo pipefail
BRIDGE_DIR="$(cd "$(dirname "$0")" && pwd)"
export PATH="$HOME/.elan/bin:$PATH"
export MATHLIB_NO_CACHE_ON_UPDATE=1
export LEAN_NUM_THREADS="${LEAN_NUM_THREADS:-4}"
cd "$BRIDGE_DIR"
PYTHON="${PYTHON:-python3}"
"$PYTHON" -c 'import sys; sys.exit("Python 3.11+ is required; activate the OMAI environment or set PYTHON.") if sys.version_info < (3, 11) else None'
if [[ "${1:-}" != "--no-cache" ]]; then
  # Resolve only pinned dependencies. The committed manifest fixes transitives.
  lake env true
  mapfile -t cache_modules < <("$PYTHON" cache_roots.py)
  if [[ "${#cache_modules[@]}" == 0 ]]; then
    echo "No cache imports found; refusing an accidental full-cache request" >&2
    exit 1
  fi
  lake exe cache get "${cache_modules[@]}"
fi
lake build --wfail
"$PYTHON" audit.py
