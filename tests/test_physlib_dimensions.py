"""Guard complete field coverage and the OMAI-to-native-ISQ interpretation."""
import json
from pathlib import Path

from omai.map_data import DOMAINS, build_graph_dict
from omai.physlib_dimensions import ISQ_BASES, build_dimensions_export, dimension_records


def test_all_catalog_nodes_and_all_fields_are_accounted_for():
    records = dimension_records()
    graph = build_graph_dict(DOMAINS)
    assert {r["node"] for r in records} == {n["id"] for n in graph["nodes"]}
    uid_by_name = {n["id"]: n["uid"] for n in graph["nodes"]}
    for r in records:
        assert r["node_uid"] == uid_by_name[r["node"]]
    for domain in DOMAINS:
        for node in domain.nodes:
            assert {r["field"] for r in records if r["node"] == node.name} == {
                field.name for field in node.fields}
    trajectory = [r for r in records if r["node"] == "Trajectory"]
    assert len(trajectory) == 2
    assert len({tuple(r["exponents"]) for r in trajectory}) == 2


def test_current_and_amount_bases_are_not_charge_or_positional_tuple_aliases():
    # These independent examples exercise every nontrivial tuple permutation.
    expected = {
        "AtomicMass": {"mass": 1},
        "CellVolume": {"length": 3},
        "AtomCount": {},
        "Voltage": {"mass": 1, "length": 2, "time": -3, "current": -1},
        "MolarHeatCapacity": {"mass": 1, "length": 2, "time": -2,
                              "temperature": -1, "amount": -1},
        "MagneticMoment": {"length": 2, "current": 1},
    }
    for r in dimension_records():
        if r["node"] in expected:
            actual = {base: power for base, power in zip(ISQ_BASES, r["exponents"]) if power}
            assert actual == expected[r["node"]]


def test_opaque_is_never_exported_as_dimensionless():
    records = dimension_records()
    for r in records:
        if r["status"] == "opaque":
            assert r["exponents"] is None
            assert r["declaration"] is None
    potential = next(r for r in records if r["node"] == "Potential")
    assert potential["status"] == "opaque"
    assert next(r for r in records if r["node"] == "AtomCount")["status"] == "encoded"


def test_generated_current_isq_source_is_current():
    source, stats = build_dimensions_export()
    path = Path(__file__).resolve().parents[1] / "lean/bridge/OMAIPhyslibDimensions.lean"
    assert path.read_text() == source
    published = path.parents[2] / "docs/data/physlib_dimensions.json"
    assert json.loads(published.read_text()) == stats
    assert stats["encoded_fields"] + stats["opaque_fields"] == stats["fields"]
    assert "Dimension ISQDimensionBase" in source
    assert "Dimension7" not in source
    assert "sorry" not in source
