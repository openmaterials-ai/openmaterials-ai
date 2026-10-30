"""Node for the tests that run the site's ES modules: the first node on PATH that is version 18 or newer.

OMAI_NODE overrides it with a command line, for hosts whose own node is older, for example
OMAI_NODE="docker run --rm -i -v $PWD:$PWD -w $PWD node:22 node".
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess

import pytest


def node_cmd() -> list[str]:
    if os.environ.get("OMAI_NODE"):
        return shlex.split(os.environ["OMAI_NODE"])
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")
    major = int(subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip().lstrip("v").split(".")[0])
    if major < 18:
        pytest.skip(f"node {major} is older than 18")
    return [node]


def run_module(script: str, stdin: str = "") -> str:
    """Run an ES module script under node and return its stdout."""
    proc = subprocess.run(node_cmd() + ["--input-type=module", "-e", script], input=stdin, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def run_node_test(path) -> None:
    """Run a node:test file and fail with its output when any test fails."""
    proc = subprocess.run(node_cmd() + ["--test", str(path)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
