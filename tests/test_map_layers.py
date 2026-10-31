"""The Lean layer of the map (omai/map_layers.py): rungs, counterparts and tier ledgers."""
from __future__ import annotations

import json
import re
from pathlib import Path

from omai import map_layers
from omai.formula_bindings import compiled_targets

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"


def _bindings() -> dict:
    return json.loads((DATA / "formula_bindings.json").read_text())


def _evidence() -> dict:
    return json.loads((ROOT / "lean" / "bridge" / "build-evidence.json").read_text())


def _source_correspondence_targets(kind: str) -> set[str]:
    return {t["id"] for b in _bindings()["bindings"] if b["evidence"]["kind"] == "source_correspondence"
            for t in b["targets"] if t["kind"] == kind}


def _proved(kind: str) -> set[str]:
    payload = _bindings()
    return {t["id"] for b in payload["bindings"] for t in compiled_targets(b, payload["inventory"]) if t["kind"] == kind}


def _fixture_payload() -> dict:
    """One local compiled bridge over op_y: X -> Y whose targets also list its input X."""
    return {
        "inventory": {"nodes": [{"id": "X"}, {"id": "Y"}],
                      "operators": [{"id": "op_y", "inputs": ["X"], "outputs": ["Y"]}]},
        "bindings": [{"id": "b", "relation": "local", "sources": [],
                      "targets": [{"kind": "node", "id": "X"}, {"kind": "operator", "id": "op_y"},
                                  {"kind": "node", "id": "Y"}],
                      "evidence": {"kind": "compiled_bridge"}}],
    }


def test_committed_file_is_the_generator_output():
    assert json.loads((DATA / "map_layers.json").read_text()) == map_layers.build_map_layers()


def test_rung_counts_equal_the_bridge_coverage():
    m, cov = map_layers.build_map_layers(), _bindings()["coverage"]
    f, q = m["counts"]["formulas"], m["counts"]["quantities"]
    assert (f["physlib"], f["local"]) == (cov["operators_compiled"], cov["operators_compiled_local"])
    assert (q["physlib"], q["local"]) == (cov["nodes_compiled"], cov["nodes_compiled_local"])
    assert sum(f.values()) == cov["operators_total"] and sum(q.values()) == cov["nodes_total"]


def test_stated_is_named_by_a_source_correspondence_and_not_proved():
    m = map_layers.build_map_layers()
    stated = {i for i, r in m["quantities"].items() if r["rung"] == "stated"}
    assert stated == _source_correspondence_targets("node") - _proved("node")


def test_an_input_reference_does_not_climb():
    r = map_layers.rungs(_fixture_payload())
    assert r[("node", "X")] == "none"
    assert r[("node", "Y")] == r[("operator", "op_y")] == "local"


def test_every_linked_bridge_declaration_is_in_the_axiom_audit_at_its_line():
    audit = _evidence()["axiom_audit"]["declarations"]
    for b in map_layers.build_map_layers()["bindings"].values():
        for d in b["bridge"]:
            assert d["name"] in audit and d["axioms"] == audit[d["name"]], d["name"]
            path, line = re.match(r".*/blob/main/(.+)#L(\d+)$", d["url"]).groups()
            assert d["name"].rsplit(".", 1)[-1] in (ROOT / path).read_text().splitlines()[int(line) - 1], d["name"]


def test_ledgers_count_formulas_by_their_output_tier():
    m = map_layers.build_map_layers()
    assert sum(t["formulas"] for t in m["tiers"]) == len(m["formulas"])
    assert sum(t["proved"] for t in m["tiers"]) == sum(r["rung"] in ("local", "physlib") for r in m["formulas"].values())
