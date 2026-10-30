"""Run the bridge and map reference-navigation behavior checks in the test gate."""
from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_formal_reference_navigation():
    from node_runner import node_cmd
    result = subprocess.run(
        node_cmd() + ["--test", "docs/lean/lib.test.js", "docs/lean/roadmap/lib.test.js",
                      "docs/lean/bridge/lib.test.js", "docs/map/formal-navigation.test.js"],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
