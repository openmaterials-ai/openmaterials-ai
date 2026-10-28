"""The browser Lean index (docs/data/lean.json) mirrors the single Lean package.

Every entry is a declaration that exists verbatim in
lean/bridge/OMAIPhyslibDimensions.lean, at the bridge's one Physlib pin, and
the published file is what the generator writes today."""
import json
from pathlib import Path

from omai.physlean_export import build_lean_index
from omai.physlib_dimensions import LEAN_TOOLCHAIN, PHYSLIB_REV, dimension_records

_ROOT = Path(__file__).resolve().parents[1]


def test_index_is_the_bridge_pin_and_only_node_dimensions():
    index = build_lean_index()
    assert set(index) == {"version", "physlib_rev", "lean_toolchain", "source", "nodes"}
    assert index["physlib_rev"] == PHYSLIB_REV
    assert index["lean_toolchain"] == LEAN_TOOLCHAIN
    assert (_ROOT / "lean/bridge/lean-toolchain").read_text().strip() == LEAN_TOOLCHAIN
    bindings = json.loads((_ROOT / "omai/data/formula_bindings.json").read_text())
    assert bindings["upstream"]["revision"] == PHYSLIB_REV


def test_every_encoded_field_and_no_opaque_node():
    index = build_lean_index()
    records = dimension_records()
    encoded = [r for r in records if r["status"] == "encoded"]
    assert sum(len(n["fields"]) for n in index["nodes"].values()) == len(encoded)
    for r in records:
        if r["status"] == "opaque" and all(
                o["status"] == "opaque" for o in records if o["node"] == r["node"]):
            assert r["node"] not in index["nodes"]
    trajectory = index["nodes"]["Trajectory"]
    assert [f["field"] for f in trajectory["fields"]] == ["r", "v"]


def test_declarations_are_verbatim_bridge_source():
    index = build_lean_index()
    source = (_ROOT / index["source"]).read_text()
    for node, entry in index["nodes"].items():
        for block in entry["lean"].split("\ndef ")[1:] + [entry["lean"].split("\ndef ")[0]]:
            text = block if block.startswith("def ") else "def " + block
            assert text in source, node
        for field in entry["fields"]:
            name = field["declaration"].rsplit(".", 1)[1]
            assert f"def {name} : Dimension ISQDimensionBase" in source


def test_bridge_dimensions_restate_nothing():
    source = (_ROOT / "lean/bridge/OMAIPhyslibDimensions.lean").read_text()
    assert "theorem" not in source and "decide" not in source


def test_published_index_is_current():
    published = json.loads((_ROOT / "docs/data/lean.json").read_text())
    assert published == json.loads(json.dumps(build_lean_index()))
