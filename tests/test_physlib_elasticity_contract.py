"""Local linear-elasticity proofs and the ``local`` binding relation.

Frozen literals are reviewed pins. The compiler probe consumes an already-built
package selected with PHYSLIB_BRIDGE_PACKAGE and never writes build evidence.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from omai.formula_bindings import (
    _packaged_bindings,
    catalog_inventory,
    compiled_targets,
    validate_formula_bindings,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "lean/bridge/OMAIElasticity.lean"
CONTRACT = ROOT / "lean/bridge/elasticity-formula-contract.json"
BINDING_ID = "linear-elasticity-voigt-moduli"
NS = "OMAI.PhyslibBridge.Elasticity."
DEFINITIONS = {
    "contract_bulk_modulus": ("voigtBulk", "def voigtBulk (C : Stiffness) : ℝ := (∑ a, ∑ b, C a a b b) / 9"),
    "contract_shear_modulus": ("voigtShear", "def voigtShear (C : Stiffness) : ℝ := -(∑ a, ∑ b, C a a b b) / 30 + (∑ a, ∑ b, C a b a b) / 10"),
    "contract_youngs_modulus": ("youngsModulus", "def youngsModulus (K G : ℝ) : ℝ := 9 * G * K / (G + 3 * K)"),
    "contract_poisson_ratio": ("poissonRatio", "def poissonRatio (K G : ℝ) : ℝ := (-2 * G + 3 * K) / (2 * G + 6 * K)"),
    "compute_bulk_modulus_eos": ("eosBulk", "def eosBulk (E : ℝ → ℝ) (V0 : ℝ) : ℝ := V0 * deriv (deriv E) V0"),
}
SUBJECTS = {("operator", op) for op in DEFINITIONS} | {
    ("node", n) for n in ("BulkModulus", "ShearModulus", "YoungsModulus", "PoissonRatio")}
KEY_THEOREMS = {
    "voigt_pos_of_posDef": "{C : Stiffness} (hC : ∀ a b c d, C a b c d = C b a c d)\n    (hpos : PosDef C) : 0 < voigtBulk C ∧ 0 < voigtShear C",
    "isotropic_stable_iff": "PosDef (isotropic lam mu) ↔\n      0 < voigtBulk (isotropic lam mu) ∧ 0 < voigtShear (isotropic lam mu)",
    "cubic_trace_stress": "trace (stress (cubic c11 c12 c44) e) = 3 * voigtBulk (cubic c11 c12 c44) * trace e",
    "cubic_relaxed_eosBulk_eq_voigtBulk": "eosBulk (relaxedEnergy (cubic c11 c12 c44) E0 V0) V0 = voigtBulk (cubic c11 c12 c44)",
}
# Restatements and symmetry-blind results that must not be cited (review of 426f141).
NOT_CITED = {"strainEnergy_hydrostatic", "eosBulk_quadratic_strain", "cubic_relaxed_sInf",
             "isotropic_strainEnergy", "isotropic_strainEnergy_split", "poissonRatio_bounds"}


def _binding(payload=None):
    payload = payload or _packaged_bindings()
    return next(b for b in payload["bindings"] if b["id"] == BINDING_ID)


def test_contract_endpoints_match_the_live_catalog_and_source():
    contract = json.loads(CONTRACT.read_text())
    assert contract["source_path"] == SOURCE
    assert contract["source_sha256"] == hashlib.sha256((ROOT / SOURCE).read_bytes()).hexdigest()
    inventory = catalog_inventory()
    ops = {row["id"]: row for row in inventory["operators"]}
    nodes = {row["id"]: row for row in inventory["nodes"]}
    assert {row["id"] for row in contract["operators"]} == set(DEFINITIONS)
    for row in contract["operators"]:
        live = ops[row["id"]]
        assert (row["uid"], row["formula_sha256"], row["formula_latex"]) == (
            live["uid"], live["formula_sha256"], live["formula_latex"])
        assert row["lean_definition"] == NS + DEFINITIONS[row["id"]][0]
    for row in contract["nodes"]:
        assert row["uid"] == nodes[row["id"]]["uid"]


def test_lean_definitions_are_the_reviewed_transcriptions():
    source = (ROOT / SOURCE).read_text()
    for _, text in DEFINITIONS.values():
        assert text in source, text
    for name, statement in KEY_THEOREMS.items():
        assert re.search(r"theorem " + name + r"\b", source)
        assert statement in source, name


def test_local_module_uses_mathlib_only_and_no_escape_hatch():
    source = (ROOT / SOURCE).read_text()
    imports = re.findall(r"^public import (\S+)", source, re.M)
    assert imports and all(name.startswith("Mathlib.") for name in imports)
    for word in ("sorry", "admit", "axiom", "native_decide", "unsafe", "set_option"):
        assert not re.search(r"\b" + word + r"\b", source), word


def test_binding_is_local_compiled_and_scoped():
    binding = _binding()
    payload = _packaged_bindings()
    assert binding["relation"] == "local"
    assert binding["sources"] == []
    assert binding["conditions"] and binding["remaining_obligations"]
    assert binding["evidence"]["kind"] == "compiled_bridge"
    assert binding["evidence"]["source_path"] == SOURCE
    subjects = {(t["kind"], t["id"]) for t in compiled_targets(binding, payload["inventory"])}
    assert subjects == SUBJECTS == {(t["kind"], t["id"]) for t in binding["targets"]}
    cited = {name.rsplit(".", 1)[1] for name in binding["evidence"]["declarations"]}
    assert not cited & NOT_CITED
    assert any("tensile-positive" in condition for condition in binding["conditions"])


def test_local_coverage_is_counted_apart_from_physlib():
    payload = _packaged_bindings()
    coverage = payload["coverage"]
    assert coverage["relations"]["local"] == 1
    assert coverage["operators_compiled_local"] == len(DEFINITIONS)
    assert coverage["operators_proved"] == coverage["operators_compiled"] + coverage["operators_compiled_local"]
    status = {row["id"]: row for row in payload["inventory"]["operators"]}
    for op in DEFINITIONS:
        assert status[op]["status"] == "local"
        assert "Physlib" in status[op]["reason"] and "local Lean proof" in status[op]["reason"]
    anchored = [b for b in payload["bindings"] if b["relation"] != "local"]
    anchored_ops = {t["id"] for b in anchored for t in compiled_targets(b, payload["inventory"])
                    if t["kind"] == "operator"}
    assert coverage["operators_compiled"] == len(anchored_ops)
    assert coverage["operators_mapped"] == sum(row["status"] == "mapped" for row in status.values())


# The schema rejects some mutations before the Python checks run; either layer suffices.
@pytest.mark.parametrize("mutation,message", [
    ("cite_source", r"sources|cites no Physlib source"),
    ("drop_conditions", r"requires explicit conditions"),
    ("source_only", r"compiled_bridge|must be a compiled proof"),
    ("unanchored_conditional", r"sources|cites no Physlib source"),
    ("drop_obligations", r"remaining obligations"),
    ("drop_local_counters", r"local counts"),
])
def test_validator_enforces_the_local_relation(mutation, message):
    payload = copy.deepcopy(_packaged_bindings())
    binding = _binding(payload)
    if mutation == "cite_source":
        binding["sources"] = copy.deepcopy(next(
            b for b in payload["bindings"] if b["sources"])["sources"][:1])
    elif mutation == "drop_conditions":
        binding["conditions"] = []
    elif mutation == "source_only":
        binding["evidence"] = {"kind": "source_correspondence"}
    elif mutation == "unanchored_conditional":
        binding["relation"] = "conditional"
    elif mutation == "drop_obligations":
        binding["remaining_obligations"] = []
    elif mutation == "drop_local_counters":
        for key in ("operators_compiled_local", "nodes_compiled_local", "operators_proved", "nodes_proved"):
            payload["coverage"].pop(key)
    with pytest.raises(Exception, match=message):
        validate_formula_bindings(payload)


def test_retained_payload_without_local_counters_still_validates():
    payload = copy.deepcopy(_packaged_bindings())
    payload["bindings"] = [b for b in payload["bindings"] if b["relation"] != "local"]
    for row in payload["inventory"]["operators"] + payload["inventory"]["nodes"]:
        row["binding_ids"] = [i for i in row["binding_ids"] if i != BINDING_ID]
        if not row["binding_ids"]:
            row["status"] = "gap"
            row["reason"] = row["reason"].replace(" A local Lean proof over Mathlib covers it; see that binding's conditions and evidence.", "")
    from omai.formula_bindings import _coverage
    coverage = _coverage(payload["bindings"], payload["inventory"])
    coverage["relations"].pop("local")
    for key in ("operators_compiled_local", "nodes_compiled_local", "operators_proved",
                "nodes_proved", "operators_local", "nodes_local"):
        coverage.pop(key)
    payload["coverage"] = coverage
    validate_formula_bindings(payload)


def test_compiled_elasticity_theorems_use_standard_axioms_only():
    package = os.environ.get("PHYSLIB_BRIDGE_PACKAGE")
    if not package:
        pytest.skip("optional real-compiler check: set PHYSLIB_BRIDGE_PACKAGE to the built package")
    package = (ROOT / package).resolve()
    names = _binding()["evidence"]["declarations"]
    probe = "import OMAIElasticity\n" + "\n".join(f"#print axioms {name}" for name in names) + "\n"
    path = package / ".lake" / "ElasticityAxioms.lean"
    path.write_text(probe)
    try:
        result = subprocess.run(["lake", "--no-build", "env", "lean", str(path)], cwd=package,
                                text=True, capture_output=True, timeout=1800, check=False)
    finally:
        path.unlink()
    assert result.returncode == 0, result.stdout + result.stderr
    reported = re.findall(r"'([^']+)' depends on axioms: \[([^\]]*)\]", result.stdout)
    assert {name for name, _ in reported} == set(names)
    for name, axioms in reported:
        assert set(a.strip() for a in axioms.split(",")) <= {"propext", "Classical.choice", "Quot.sound"}, name
