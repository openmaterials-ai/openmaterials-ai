"""Local proofs about derivatives of an atomistic or cell energy.

Frozen literals are reviewed pins. The compiler probe consumes an already-built
package selected with PHYSLIB_BRIDGE_PACKAGE and never writes build evidence.
Global coverage totals are pinned in tests/physlib_tranches.py; this file checks
only its own contracts, bindings and catalog defect.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from omai.formula_bindings import _packaged_bindings, catalog_inventory, compiled_targets

ROOT = Path(__file__).resolve().parents[1]
AD = "lean/bridge/OMAIAtomisticDerivatives.lean"
CE = "lean/bridge/OMAICellElasticity.lean"
MM = "lean/bridge/OMAIMolecularModes.lean"
NA = "OMAI.PhyslibBridge.Atomistic."
NC = "OMAI.PhyslibBridge.CellElasticity."
NM = "OMAI.PhyslibBridge.MolecularModes."

DEFINITIONS = {
    "compute_forces_hf": (NA + "hfForce", AD,
        "def hfForce (E : (A × Fin 3 → ℝ) → ℝ) (R : A × Fin 3 → ℝ) (i : A) (α : Fin 3) : ℝ :=\n"
        "  -partialAt E (i, α) R"),
    "compute_stress_cell": (NC + "cellStress", CE,
        "def cellStress (E : Cell → ℝ) (V : ℝ) (F : Cell) (a b : Fin 3) : ℝ :=\n"
        "  -(1 / V) * partialAt E (a, b) F"),
    "compute_fc2_finite_displacement": (NA + "fdForceConstant", AD,
        "def fdForceConstant (F : (A × Fin 3 → ℝ) → A × Fin 3 → ℝ) (u : A × Fin 3 → ℝ)\n"
        "    (i j : A × Fin 3) : ℝ :=\n  -partialAt (fun x => F x j) i u"),
    "compute_force_constants[order=2]": (NA + "forceConstant2", AD,
        "def forceConstant2 (V : (A × Fin 3 → ℝ) → ℝ) (u : A × Fin 3 → ℝ) (k l : A × Fin 3) : ℝ :=\n"
        "  partialAt (fun x => partialAt V k x) l u"),
    "compute_force_constants[order=3]": (NA + "forceConstant3", AD,
        "def forceConstant3 (V : (A × Fin 3 → ℝ) → ℝ) (u : A × Fin 3 → ℝ) (k l m : A × Fin 3) : ℝ :=\n"
        "  partialAt (fun y => forceConstant2 V y k l) m u"),
    "compute_elastic_constants": (NC + "elasticConstants", CE,
        "def elasticConstants (E : Cell → ℝ) (V : ℝ) (F : Cell) (a b c d : Fin 3) : ℝ :=\n"
        "  -partialAt (fun G => cellStress E V G a b) (c, d) F"),
    "compute_molecular_frequencies": (NM + "molecularFrequencies", MM,
        "  if 0 ≤ hH.eigenvalues i then Real.sqrt (hH.eigenvalues i) else -Real.sqrt (-hH.eigenvalues i)"),
}
HELPERS = {
    AD: ["def partialAt (f : (ι → ℝ) → ℝ) (k : ι) (x : ι → ℝ) : ℝ := fderiv ℝ f x (Pi.single k 1)",
         "def translate (t : Fin 3 → ℝ) (R : A × Fin 3 → ℝ) : A × Fin 3 → ℝ := fun k => R k + t k.2",
         "(F (u - h • Pi.single i 1) j - F (u + h • Pi.single i 1) j) / (2 * h)"],
    MM: ["  fun k l => forceConstant2 V u k l / Real.sqrt (m k.1 * m l.1)"],
    CE: [],
}
CONTRACTS = {
    "lean/bridge/dft-derivatives-formula-contract.json": (
        AD, {"compute_forces_hf", "compute_stress_cell", "compute_fc2_finite_displacement"},
        {"Forces", "Stress", "ForceConstants[order=2]"}),
    "lean/bridge/force-constants-formula-contract.json": (
        AD, {"compute_force_constants[order=2]", "compute_force_constants[order=3]"},
        {"ForceConstants[order=2]", "ForceConstants[order=3]"}),
    "lean/bridge/elastic-constants-formula-contract.json": (
        CE, {"compute_elastic_constants"}, {"ElasticConstants"}),
    "lean/bridge/molecular-modes-formula-contract.json": (
        MM, {"compute_molecular_frequencies"}, {"MolecularFrequency"}),
}
BINDINGS = {
    "hellmann-feynman-force-balance": ("OMAIAtomisticDerivatives", AD, {"compute_forces_hf"}, {"Forces"}),
    "cell-stress-rotation-balance": ("OMAICellElasticity", CE, {"compute_stress_cell"}, {"Stress"}),
    "force-constant-sum-rules": ("OMAIAtomisticDerivatives", AD,
                                 {"compute_force_constants[order=2]", "compute_force_constants[order=3]"},
                                 {"ForceConstants[order=2]", "ForceConstants[order=3]"}),
    "finite-displacement-force-constants": ("OMAIAtomisticDerivatives", AD,
                                            {"compute_fc2_finite_displacement"}, set()),
    "hyperelastic-elastic-constants": ("OMAICellElasticity", CE, {"compute_elastic_constants"},
                                       {"ElasticConstants"}),
    "molecular-normal-modes": ("OMAIMolecularModes", MM, {"compute_molecular_frequencies"},
                               {"MolecularFrequency"}),
}
KEY_THEOREMS = {
    AD: {
        "hfForce_sum_eq_zero": "(hE : ∀ t, E (translate t R) = E R) (α : Fin 3) : ∑ i, hfForce E R i α = 0",
        "hfForce_torque_eq_zero": "∑ i, (R (i, α) * hfForce E R i β - R (i, β) * hfForce E R i α) = 0",
        "forceConstant2_sum_eq_zero": "∑ s, forceConstant2 V u k (s, β) = 0",
        "forceConstant3_sum_eq_zero": "∑ s, forceConstant3 V u k l (s, γ) = 0",
        "centralDifference_error": "|centralDifference F u i j h - fdForceConstant F u i j| ≤ M * h ^ 2 / 6",
        "pairEnergy_force": "hfForce pairEnergy pairConfig 0 0 = 2",
    },
    CE: {
        "cellStress_rotation_balance":
            "∑ b, cellStress E V F α b * F (β, b) = ∑ b, cellStress E V F β b * F (α, b)",
        "elasticConstants_symmetries":
            "(hfree : ∀ a b, cellStress E V referenceCell a b = 0) (a b c d : Fin 3) :",
    },
    MM: {
        "molecularFrequencies_of_isLocalMin": "(hm : ∀ i, 0 < m i) (hV : ContDiffAt ℝ 2 V u) (hmin : IsLocalMin V u)",
        "massWeightedHessian_translation":
            "massWeightedHessian V u m *ᵥ (fun k => if k.2 = β then Real.sqrt (m k.1) else 0) = 0",
    },
}
# Mathlib restatements and specializations kept out of the citations.
NOT_CITED = {NA + "fderiv_apply_eq_zero_of_invariant_curve", NA + "partialAt_symm",
             NA + "sum_partialAt_eq_zero_of_translate", NA + "central_difference_bound",
             NC + "elasticConstants_major", NM + "massWeightedHessian_isHermitian"}


def _binding(binding_id):
    return next(b for b in _packaged_bindings()["bindings"] if b["id"] == binding_id)


@pytest.mark.parametrize("contract_path", sorted(CONTRACTS))
def test_contract_endpoints_match_the_live_catalog_and_source(contract_path):
    source, operators, outputs = CONTRACTS[contract_path]
    contract = json.loads((ROOT / contract_path).read_text())
    assert contract["source_path"] == source
    assert contract["source_sha256"] == hashlib.sha256((ROOT / source).read_bytes()).hexdigest()
    inventory = catalog_inventory()
    ops = {row["id"]: row for row in inventory["operators"]}
    nodes = {row["id"]: row for row in inventory["nodes"]}
    assert {row["id"] for row in contract["operators"]} == operators
    for row in contract["operators"]:
        live = ops[row["id"]]
        assert (row["uid"], row["formula_sha256"], row["formula_latex"]) == (
            live["uid"], live["formula_sha256"], live["formula_latex"])
        name, definition_source, _ = DEFINITIONS[row["id"]]
        assert row["lean_definition"] == name
        assert row.get("definition_source_path", source) == definition_source
    assert {row["id"] for row in contract["nodes"]} == outputs
    for row in contract["nodes"]:
        assert row["uid"] == nodes[row["id"]]["uid"]


def test_lean_definitions_are_the_reviewed_transcriptions():
    for _, source, text in DEFINITIONS.values():
        assert text in (ROOT / source).read_text(), text
    for source, texts in HELPERS.items():
        for text in texts:
            assert text in (ROOT / source).read_text(), text
    for source, theorems in KEY_THEOREMS.items():
        text = (ROOT / source).read_text()
        for name, statement in theorems.items():
            assert re.search(r"theorem " + name + r"\b", text), name
            assert statement in text, name


@pytest.mark.parametrize("source", [AD, CE, MM])
def test_local_modules_use_no_physlib_and_no_escape_hatch(source):
    text = (ROOT / source).read_text()
    imports = re.findall(r"^public import (\S+)", text, re.M)
    assert imports and all(name.startswith("Mathlib.") or name in (
        "OMAIAtomisticDerivatives", "OMAIElasticity") for name in imports)
    for word in ("sorry", "admit", "axiom", "native_decide", "unsafe", "set_option"):
        assert not re.search(r"\b" + word + r"\b", text), word


@pytest.mark.parametrize("binding_id", sorted(BINDINGS))
def test_binding_targets_are_its_proof_subjects(binding_id):
    module, source, operators, outputs = BINDINGS[binding_id]
    binding = _binding(binding_id)
    payload = _packaged_bindings()
    assert binding["relation"] == "local" and binding["sources"] == []
    assert binding["conditions"] and binding["remaining_obligations"]
    assert binding["evidence"]["kind"] == "compiled_bridge"
    assert (binding["evidence"]["module"], binding["evidence"]["source_path"]) == (module, source)
    expected = {("operator", op) for op in operators} | {("node", node) for node in outputs}
    assert {(t["kind"], t["id"]) for t in compiled_targets(binding, payload["inventory"])} == expected
    assert {(t["kind"], t["id"]) for t in binding["targets"]} == expected
    declarations = binding["evidence"]["declarations"]
    assert declarations and not set(declarations) & NOT_CITED


@pytest.mark.parametrize("operator", sorted(DEFINITIONS))
def test_rows_are_local_and_keep_their_physlib_gap_reason(operator):
    payload = _packaged_bindings()
    row = next(r for r in payload["inventory"]["operators"] if r["id"] == operator)
    assert row["status"] == "local"
    assert "local Lean proof" in row["reason"]


def test_conventions_a_user_could_get_wrong_are_stated():
    forces = " ".join(_binding("hellmann-feynman-force-balance")["conditions"])
    for phrase in ("egg-box", "does not apply to periodic cells", "Pulay"):
        assert phrase in forces, phrase
    stress = " ".join(_binding("cell-stress-rotation-balance")["conditions"])
    assert "compressive positive" in stress and "reference cell volume" in stress
    fd = " ".join(_binding("finite-displacement-force-constants")["conditions"])
    assert "fourth derivative of the potential" in fd and "One-sided differences" in fd
    elastic = " ".join(_binding("hyperelastic-elastic-constants")["conditions"])
    assert "stress-free reference" in elastic and "pre-stressed" in elastic
    modes = _binding("molecular-normal-modes")
    assert "n_imaginary = 0" in modes["statement"]
    assert any("converse fails" in text for text in modes["conditions"])


def test_gruneisen_formula_is_recorded_as_a_catalog_defect():
    payload = _packaged_bindings()
    row = next(r for r in payload["inventory"]["operators"] if r["id"] == "compute_gruneisen")
    assert row["status"] == "gap" and row["binding_ids"] == []
    assert row["reason"].startswith("Catalog defect.")
    for phrase in ("leaves k, R and R' free", "Maradudin-Fein", "e*_{alpha kappa}(q nu)"):
        assert phrase in row["reason"], phrase


def test_compiled_theorems_use_standard_axioms_only():
    package = os.environ.get("PHYSLIB_BRIDGE_PACKAGE")
    if not package:
        pytest.skip("optional real-compiler check: set PHYSLIB_BRIDGE_PACKAGE to the built package")
    package = (ROOT / package).resolve()
    names = [name for binding_id in sorted(BINDINGS) for name in _binding(binding_id)["evidence"]["declarations"]]
    probe = ("import OMAIAtomisticDerivatives\nimport OMAICellElasticity\nimport OMAIMolecularModes\n"
             + "\n".join(f"#print axioms {name}" for name in names) + "\n")
    path = package / ".lake" / "AtomisticDerivativesAxioms.lean"
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
