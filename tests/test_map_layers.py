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
    """op_y: X -> Y proved locally, op_z: X -> Y unbound, op_w: -> W unbound with W proved as itself,
    op_d: X -> D proved with D left out of its proved targets, and V named only by a conceptual source
    correspondence. The local binding b also lists its input X."""
    return {
        "inventory": {"nodes": [{"id": i} for i in "DVWXY"],
                      "operators": [{"id": "op_d", "inputs": ["X"], "outputs": ["D"]},
                                    {"id": "op_y", "inputs": ["X"], "outputs": ["Y"]},
                                    {"id": "op_z", "inputs": ["X"], "outputs": ["Y"]},
                                    {"id": "op_w", "inputs": [], "outputs": ["W"]}]},
        "bindings": [{"id": "b", "relation": "local", "sources": [],
                      "targets": [{"kind": "node", "id": "X"}, {"kind": "operator", "id": "op_y"},
                                  {"kind": "node", "id": "Y"}],
                      "evidence": {"kind": "compiled_bridge"}},
                     {"id": "w", "relation": "conditional", "sources": [],
                      "targets": [{"kind": "node", "id": "W"}],
                      "evidence": {"kind": "compiled_bridge", "proved_targets": [{"kind": "node", "id": "W"}]}},
                     {"id": "d", "relation": "local", "sources": [],
                      "targets": [{"kind": "operator", "id": "op_d"}, {"kind": "node", "id": "D"}],
                      "evidence": {"kind": "compiled_bridge", "proved_targets": [{"kind": "operator", "id": "op_d"}]}},
                     {"id": "v", "relation": "conceptual", "sources": [],
                      "targets": [{"kind": "node", "id": "V"}],
                      "evidence": {"kind": "source_correspondence"}}],
    }


def test_committed_file_is_the_generator_output():
    built = json.dumps(map_layers.build_map_layers(), indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    assert (DATA / "map_layers.json").read_text() == built, "stale: run python -m omai.map_layers"


def test_formula_rungs_equal_the_bridge_coverage():
    m, cov = map_layers.build_map_layers(), _bindings()["coverage"]
    f = m["counts"]["formulas"]
    assert (f["physlib"], f["local"]) == (cov["operators_compiled"], cov["operators_compiled_local"])
    assert sum(f.values()) == cov["operators_total"] and sum(m["counts"]["quantities"].values()) == cov["nodes_total"]


def test_stated_needs_a_binding_that_identifies_the_mark():
    m = map_layers.build_map_layers()
    identifying = {(t["kind"], t["id"]) for b in _bindings()["bindings"]
                   if b["evidence"]["kind"] == "source_correspondence" and b["relation"] != "conceptual"
                   for t in b["targets"]}
    for kind, marks in (("node", m["quantities"]), ("operator", m["formulas"])):
        stated = {i for i, r in marks.items() if r["rung"] == "stated"}
        assert stated <= {i for k, i in identifying if k == kind}, kind


def test_rung_rules_on_a_fixture():
    r = map_layers.rungs(_fixture_payload())
    assert r[("operator", "op_y")] == "local" and r[("operator", "op_z")] == "none"
    assert r[("node", "X")] == "none"        # an input reference does not climb
    assert r[("node", "Y")] == "none"        # one of its two producing formulas has no Lean
    assert r[("node", "W")] == "physlib"     # a theorem about the quantity itself
    assert r[("node", "V")] == "none"        # a conceptual analogue is not a statement
    assert r[("operator", "op_d")] == "local" and r[("node", "D")] == "none"   # the binding left D out


def test_a_quantity_says_where_its_rung_comes_from():
    q = map_layers.build_map_layers()["quantities"]
    assert q["Temperature"]["rung"] == "physlib" and q["Temperature"]["via"] == "quantity"
    assert q["ThermalConductivity[bte_solver=rta]"]["via"] == "formulas"
    assert q["Structure"]["rung"] == "none" and q["Structure"]["related"]
    assert q["Frequency"]["rung"] == "none"  # crystal-phonon-dispersion proves compute_dispersion, not its outputs


def test_every_linked_bridge_declaration_is_in_the_axiom_audit_at_its_line():
    audit = _evidence()["axiom_audit"]["declarations"]
    m = map_layers.build_map_layers()
    assert m["axioms"] == _evidence()["axiom_audit"]["allowed_axioms"]
    for b in m["bindings"].values():
        for d in b["bridge"]:
            assert d["name"] in audit and set(audit[d["name"]]) <= set(m["axioms"]), d["name"]
            path, line = re.match(r".*/blob/main/(.+)#L(\d+)$", d["url"]).groups()
            assert d["name"].rsplit(".", 1)[-1] in (ROOT / path).read_text().splitlines()[int(line) - 1], d["name"]


def test_ledgers_count_formulas_by_their_output_tier():
    m = map_layers.build_map_layers()
    assert sum(t["formulas"] for t in m["tiers"]) == len(m["formulas"])
    assert sum(t["theorems"] for t in m["tiers"]) == sum(r["rung"] in ("local", "physlib") for r in m["formulas"].values())


def test_bridge_lines_scopes_sections_mutual_blocks_and_comments():
    src = "\n".join([
        "namespace A",                            # 1
        "noncomputable section",                  # 2
        "/-- theorem decoy in a docstring -/",    # 3
        "theorem t1 : True := trivial",           # 4
        "end",                                    # 5
        "mutual",                                 # 6
        "def m1 : Nat := 0",                      # 7
        "end",                                    # 8
        "/- theorem decoy",                       # 9
        "   theorem decoy2 -/",                   # 10
        "@[simp] private theorem t2 : True := trivial",  # 11
        "theorem _root_.top : True := trivial",   # 12
        "end A",                                  # 13
        "theorem outside : True := trivial",      # 14
        "open Real in theorem B.u.{u} : True := trivial",  # 15
        "public theorem pub : True := trivial",   # 16
    ])
    assert map_layers.bridge_lines(src) == {"A.t1": 4, "A.m1": 7, "A.t2": 11, "top": 12, "outside": 14,
                                            "B.u": 15, "pub": 16}


def test_a_declaration_names_the_module_of_its_file():
    for b in map_layers.build_map_layers()["bindings"].values():
        for d in b["bridge"]:
            assert d["url"].split("/")[-1].split("#")[0] == d["module"] + ".lean", d["name"]


def test_a_missing_bridge_declaration_fails_loudly(monkeypatch):
    monkeypatch.setattr(map_layers, "_bridge_index", lambda: {})
    try:
        map_layers.build_map_layers()
    except ValueError as e:
        assert "OMAI." in str(e)
    else:
        raise AssertionError("a declaration with no source line was accepted")


def test_a_binding_that_only_reads_a_mark_is_not_listed_on_it():
    m = map_layers.build_map_layers()
    reads = {i for b in _bindings()["bindings"] for t in b["targets"] if t["kind"] == "node"
             for i in [t["id"]]} - _proved("node") - _source_correspondence_targets("node")
    for i in reads:
        assert m["quantities"][i]["bindings"] == [], i
