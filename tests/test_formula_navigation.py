"""Run the bridge and map reference-navigation behavior checks in the test gate."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_formal_reference_navigation():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not available")
    result = subprocess.run(
        [node, "--test", "docs/lean/bridge/lib.test.js", "docs/map/formal-navigation.test.js"],
        cwd=ROOT, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
