"""The datasheet shows a simulation record's reported values.

record_simulation keeps a run's value instances in ``results`` (outside the
lineage hash), so a record shared through ``#x=`` used to open as a datasheet
with lineage and execution but no number. resultsHTML renders those instances
whenever the lineage carries no ``values`` of its own. Same technique as
test_play_envelope_decode.py: extract the page functions and run them under
Node; a static wiring check guards the dispatch regardless.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_PLAY = _REPO / "docs" / "play" / "index.html"

_RECORD = {
    "id": "e292099ad3e4",
    "lineage": {"node": "ThermalConductivity[bte_solver=rta]", "node_uid": "d79d88d5",
                "material": {"name": "Si"}, "conditions": {"temperature_K": 300}, "params": {}},
    "execution": {"code": "meskal_rta"},
    "artifacts": [], "mirrors": {},
    "results": [{
        "variable": "ThermalConductivity[bte_solver=rta]", "material": "Si",
        "conditions": {"temperature_K": 300, "method": "bte_rta", "code": "MESKAL"},
        "value": 20.16, "units": "W/(m K)", "uncertainty": 0.5,
        "source": {"kind": "simulation", "ref": "materialscodegraph", "detail": "MESKAL BTE-RTA"},
    }, {"variable": "Bogus", "value": "not a number", "units": "x"}],
}


def _grab_function(html: str, name: str) -> str:
    m = re.search(r"(?:async )?function %s\s*\([^)]*\)\s*\{" % re.escape(name), html)
    assert m, f"could not find function {name}"
    i, depth = m.end(), 1
    while i < len(html) and depth:
        c = html[i]
        depth += c == "{"
        depth -= c == "}"
        i += 1
    return html[m.start():i]


def _render(record: dict) -> str:
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available; render checked where present")
    html = _PLAY.read_text()
    src = "\n".join(_grab_function(html, n)
                    for n in ("esc", "fmtScalar", "fmtValue", "fmtSig", "cleanUnit", "reportedValues", "resultsHTML"))
    script = src + "\nconsole.log(resultsHTML(%s));" % json.dumps(record)
    proc = subprocess.run([node, "-e", script], capture_output=True, text=True)
    assert proc.returncode == 0, f"node failed: {proc.stderr}"
    return proc.stdout


def test_results_render_as_a_values_table():
    out = _render(_RECORD)
    assert "ThermalConductivity[bte_solver=rta]" in out
    assert "20.16 ± 0.5" in out
    assert "W/(m K)" in out
    assert "temperature_K = 300" in out and "code = MESKAL" in out
    assert "Bogus" in out and "not a number" in out, "a stated value renders even when not numeric"
    assert "outside the lineage id" in out


def test_values_display_six_significant_digits():
    rec = {"results": [{"variable": "ThermalConductivity", "value": 19.98035554910192,
                        "uncertainty": 109.46818688469766, "units": "W/(m K)"}]}
    out = _render(rec)
    assert "19.9804 ± 109.468" in out and "19.98035554910192" not in out


def test_list_values_render():
    rec = {"results": [{"variable": "ThermalConductivity", "value": [10, 20, 30], "units": "W/(m K)"}]}
    assert "10 × 20 × 30" in _render(rec)


def test_no_results_renders_nothing():
    assert _render({"results": []}).strip() == ""
    assert _render({}).strip() == ""
    assert _render({"results": "not a list"}).strip() == ""


def test_page_wires_results_after_lineage_values():
    html = _PLAY.read_text()
    assert "function resultsHTML" in html
    assert "(valuesHTML(lineage, node) || resultsHTML(record))" in html
    assert ".rec-vtable{width:100%;table-layout:fixed;" in html
