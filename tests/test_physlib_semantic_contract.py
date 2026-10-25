"""Catch independent scientific-formula / reviewed Lean-interpretation drift.

This is a reviewed endpoint contract, not an automatic semantic translator or
an alternative to compiling Lean. The manifest pins both source sides.
"""
import hashlib
import json
from pathlib import Path

from omai.formula_bindings import catalog_inventory

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "lean/bridge/semantic-formula-contract.json"


def test_reviewed_semantic_formula_endpoints_have_not_drifted():
    contract = json.loads(CONTRACT.read_text())
    source = ROOT / contract["source_path"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == contract["source_sha256"], (
        "Lean semantic source changed: review its correspondence to OMAI formulas "
        "and rebuild before updating the endpoint contract."
    )
    actual = {op["id"]: op for op in catalog_inventory()["operators"]}
    assert {row["id"] for row in contract["operators"]} == {
        "contract_power_factor", "sum_thermal_conductivity", "contract_zt",
        "compute_free_energy", "compute_internal_energy", "compute_entropy",
    }
    for reviewed in contract["operators"]:
        current = actual[reviewed["id"]]
        assert current["uid"] == reviewed["uid"]
        assert current["formula_sha256"] == reviewed["formula_sha256"], (
            reviewed["id"] + " formula changed without semantic bridge review"
        )
        definition = reviewed["lean_definition"].split(".")[-1]
        assert f"def {definition} " in source.read_text()
