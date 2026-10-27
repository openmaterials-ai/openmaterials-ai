"""Catch independent scientific-formula / reviewed Lean-interpretation drift.

This is a reviewed endpoint contract, not an automatic semantic translator or
an alternative to compiling Lean. The manifest pins both source sides.
"""
import hashlib
import json
from pathlib import Path

import pytest

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


def test_additional_reviewed_formula_contracts_have_not_drifted():
    """New proof modules retain their own reviewed scientific endpoints."""
    inventory = catalog_inventory()
    operators = {row["id"]: row for row in inventory["operators"]}
    nodes = {row["id"]: row for row in inventory["nodes"]}
    for path in sorted(CONTRACT.parent.glob("*-formula-contract.json")):
        if path == CONTRACT:
            continue
        contract = json.loads(path.read_text())
        source = ROOT / contract["source_path"]
        assert source.resolve().is_relative_to(CONTRACT.parent.resolve())
        assert hashlib.sha256(source.read_bytes()).hexdigest() == contract["source_sha256"]
        assert contract.get("operators") or contract.get("nodes"), path
        for reviewed in contract.get("operators", []):
            current = operators[reviewed["id"]]
            assert current["uid"] == reviewed["uid"]
            assert current["formula_sha256"] == reviewed["formula_sha256"]
            definition_source = ROOT / reviewed.get("definition_source_path", contract["source_path"])
            assert definition_source.resolve().is_relative_to(CONTRACT.parent.resolve())
            definition = reviewed["lean_definition"].rsplit(".", 1)[-1]
            assert f"def {definition} " in definition_source.read_text()
        for reviewed in contract.get("nodes", []):
            assert nodes[reviewed["id"]]["uid"] == reviewed["uid"]


@pytest.mark.parametrize("missing_contract", [
    "harmonic-sums-formula-contract.json", "harmonic-product-formula-contract.json",
    "harmonic-density-formula-contract.json", "joint-density-formula-contract.json",
])
def test_axiom_audit_refuses_a_deleted_reviewed_contract(tmp_path, monkeypatch, missing_contract):
    import importlib.util
    import pytest

    spec = importlib.util.spec_from_file_location("bridge_audit_contract_test", CONTRACT.parent / "audit.py")
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    for path in CONTRACT.parent.glob("*-formula-contract.json"):
        (tmp_path / path.name).write_bytes(path.read_bytes())
    (tmp_path / missing_contract).unlink()
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    with pytest.raises(ValueError, match=missing_contract):
        audit.run()
