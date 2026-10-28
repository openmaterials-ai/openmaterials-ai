"""Local stability energy-difference and CALPHAD equilibrium proofs.

Frozen literals are reviewed pins. The compiler probe consumes an already-built
package selected with PHYSLIB_BRIDGE_PACKAGE and never writes build evidence.
Global coverage totals are pinned in tests/physlib_tranches.py; this file checks
only its own bindings and their place in the local counts.
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
TRANCHES = {
    "dft-stability-energy-differences": {
        "source": "lean/bridge/OMAIStabilityEnergies.lean",
        "contract": "lean/bridge/stability-formula-contract.json",
        "module": "OMAIStabilityEnergies",
        "ns": "OMAI.PhyslibBridge.Stability.",
        "definitions": {
            "compute_energy_above_hull": ("energyAboveHull", "def energyAboveHull (S : Set ι) (x : ι → κ → ℝ) (h : ι → ℝ) (i : ι) : ℝ :=\n  h i - hullEnergy S x h (x i)"),
            "compute_reaction_energy": ("reactionEnergy", "def reactionEnergy {ι : Type*} [Fintype ι] (c h : ι → ℝ) : ℝ := ∑ i, h i * c i"),
            "compute_adsorption_energy": ("adsorptionEnergy", "def adsorptionEnergy (Eadslab Eslab Eadsorbate : ℝ) : ℝ := Eadslab - Eadsorbate - Eslab"),
            "compute_intercalation_voltage": ("intercalationVoltage", "def intercalationVoltage (Efull Eempty n mu q : ℝ) : ℝ := (mu * n + Eempty - Efull) / (n * q)"),
            "compute_surface_energy": ("surfaceEnergy", "def surfaceEnergy (Eslab Ebulk N A : ℝ) : ℝ := (-N * Ebulk + Eslab) / (2 * A)"),
            "compute_grain_boundary_energy": ("grainBoundaryEnergy", "def grainBoundaryEnergy (EGB Ebulk N A : ℝ) : ℝ := (-N * Ebulk + EGB) / (2 * A)"),
        },
        "helpers": [
            "def hullEnergy (S : Set ι) (x : ι → κ → ℝ) (h : ι → ℝ) (y : κ → ℝ) : ℝ :=\n  sInf (decompositionEnergies S x h y)",
            "(∀ j, 0 ≤ w j) ∧ (∀ j, j ∉ S → w j = 0) ∧ ∑ j, w j = 1 ∧ ∀ a, ∑ j, w j * x j a = y a",
        ],
        "outputs": {"EnergyAboveHull", "ReactionEnergy", "AdsorptionEnergy", "Voltage", "SurfaceEnergy",
                    "GrainBoundaryEnergy"},
        "key_theorems": {
            "energyAboveHull_affine_invariant": "energyAboveHull S x (fun j => h j + (c + ∑ a, δ a * x j a)) i = energyAboveHull S x h i",
            "energyAboveHull_mono_competitors": "energyAboveHull S x h i ≤ energyAboveHull S' x h i",
            "reactionEnergy_reference_independent_iff": "∀ a, ∑ s, ν s * n s a = 0",
            "adsorptionEnergy_offset_invariant_iff": "nAdslab = nSlab + nAdsorbate",
            "intercalationVoltage_offset_invariant_iff": "nFull = nEmpty + n • Pi.single ion 1",
            "intercalationVoltage_eq_mean_ocv": "(∫ x in (0 : ℝ)..n, (mu - E' x) / q) / n",
            "surfaceEnergy_thickness_independent_iff": "Tendsto (fun N : ℝ => |surfaceEnergy (N * e + c) Ebulk N A|) atTop atTop",
        },
    },
    "calphad-binary-equilibrium": {
        "source": "lean/bridge/OMAICalphad.lean",
        "contract": "lean/bridge/thermochemistry-formula-contract.json",
        "module": "OMAICalphad",
        "ns": "OMAI.PhyslibBridge.Calphad.",
        "definitions": {
            "solve_equilibrium": ("equilibriumGibbs", "def equilibriumGibbs {P : Type*} (g : P → ℝ → ℝ) (x : ℝ) : ℝ := sInf (mixtureEnergies g x)"),
            "compute_molar_enthalpy": ("molarEnthalpy", "def molarEnthalpy (G : ℝ → ℝ) (T : ℝ) : ℝ := G T - T * deriv G T"),
            "compute_calphad_entropy": ("calphadEntropy", "def calphadEntropy (G : ℝ → ℝ) (T : ℝ) : ℝ := -deriv G T"),
            "compute_chemical_potentials": ("chemicalPotentials", "def chemicalPotentials (G : ℝ → ℝ) (x : ℝ) : Fin 2 → ℝ :=\n  ![G x - x * deriv G x, G x + (1 - x) * deriv G x]"),
            "compute_phase_fractions": ("leverFractions", "def leverFractions (x1 x2 x : ℝ) : Fin 2 → ℝ := ![(x2 - x) / (x2 - x1), (x - x1) / (x2 - x1)]"),
            "compute_transition_temperature": ("transitionTemperature", "def transitionTemperature (dG : ℝ → ℝ) (T1 T2 : ℝ) : ℝ := sInf {T | T ∈ Icc T1 T2 ∧ dG T ≤ 0}"),
        },
        "helpers": [],
        "outputs": {"MolarGibbsEnergy", "MolarEnthalpy", "CalphadMolarEntropy", "ChemicalPotential",
                    "PhaseFraction", "TransitionTemperature"},
        "key_theorems": {
            "equilibriumGibbs_convexOn": "ConvexOn ℝ (Icc 0 1) (equilibriumGibbs g)",
            "le_equilibriumGibbs_of_convex": "φ x ≤ equilibriumGibbs g x",
            "molarEnthalpy_calphadEntropy_heatCapacity": "HasDerivAt (molarEnthalpy G) (T * -G'') T ∧ HasDerivAt (calphadEntropy G) (-G'') T",
            "gibbs_duhem": "x * deriv (fun t => chemicalPotentials G t 1) x = 0",
            "commonTangent_of_isLocalMin": "chemicalPotentials g1 x1 = chemicalPotentials g2 x2",
            "transitionTemperature_unique": "(∀ T ∈ Icc T1 T2, dG T = 0 → T = transitionTemperature dG T1 T2)",
        },
    },
}
# Restatements of a definition and support lemmas kept out of the citations.
NOT_CITED = {
    "OMAI.PhyslibBridge.Stability.energyAboveHull_nonneg",
    "OMAI.PhyslibBridge.Stability.combination_offset_invariant_iff",
}
# Closed-form definitions with nothing to prove: never proof subjects of these tranches.
DEFINITIONS_ONLY = {"compute_formation_energy", "contract_gibbs_hts"}


def _binding(binding_id):
    return next(b for b in _packaged_bindings()["bindings"] if b["id"] == binding_id)


@pytest.mark.parametrize("binding_id", sorted(TRANCHES))
def test_contract_endpoints_match_the_live_catalog_and_source(binding_id):
    spec = TRANCHES[binding_id]
    contract = json.loads((ROOT / spec["contract"]).read_text())
    assert contract["source_path"] == spec["source"]
    assert contract["source_sha256"] == hashlib.sha256((ROOT / spec["source"]).read_bytes()).hexdigest()
    inventory = catalog_inventory()
    ops = {row["id"]: row for row in inventory["operators"]}
    nodes = {row["id"]: row for row in inventory["nodes"]}
    assert {row["id"] for row in contract["operators"]} == set(spec["definitions"])
    for row in contract["operators"]:
        live = ops[row["id"]]
        assert (row["uid"], row["formula_sha256"], row["formula_latex"]) == (
            live["uid"], live["formula_sha256"], live["formula_latex"])
        assert row["lean_definition"] == spec["ns"] + spec["definitions"][row["id"]][0]
    assert {row["id"] for row in contract["nodes"]} == spec["outputs"]
    for row in contract["nodes"]:
        assert row["uid"] == nodes[row["id"]]["uid"]


@pytest.mark.parametrize("binding_id", sorted(TRANCHES))
def test_lean_definitions_are_the_reviewed_transcriptions(binding_id):
    spec = TRANCHES[binding_id]
    source = (ROOT / spec["source"]).read_text()
    for _, text in spec["definitions"].values():
        assert text in source, text
    for text in spec["helpers"]:
        assert text in source, text
    for name, statement in spec["key_theorems"].items():
        assert re.search(r"theorem " + name + r"\b", source), name
        assert statement in source, name


@pytest.mark.parametrize("binding_id", sorted(TRANCHES))
def test_local_module_uses_mathlib_only_and_no_escape_hatch(binding_id):
    source = (ROOT / TRANCHES[binding_id]["source"]).read_text()
    imports = re.findall(r"^public import (\S+)", source, re.M)
    assert imports and all(name.startswith("Mathlib.") for name in imports)
    for word in ("sorry", "admit", "axiom", "native_decide", "unsafe", "set_option"):
        assert not re.search(r"\b" + word + r"\b", source), word


@pytest.mark.parametrize("binding_id", sorted(TRANCHES))
def test_binding_targets_are_its_proof_subjects(binding_id):
    spec = TRANCHES[binding_id]
    binding = _binding(binding_id)
    payload = _packaged_bindings()
    assert binding["relation"] == "local" and binding["sources"] == []
    assert binding["conditions"] and binding["remaining_obligations"]
    assert binding["evidence"]["kind"] == "compiled_bridge"
    assert binding["evidence"]["module"] == spec["module"]
    assert binding["evidence"]["source_path"] == spec["source"]
    subjects = {(t["kind"], t["id"]) for t in compiled_targets(binding, payload["inventory"])}
    expected = ({("operator", op) for op in spec["definitions"]}
                | {("node", node) for node in spec["outputs"]})
    assert subjects == expected
    assert {(t["kind"], t["id"]) for t in binding["targets"]} == expected
    declarations = binding["evidence"]["declarations"]
    assert declarations and all(name.startswith(spec["ns"]) for name in declarations)
    assert not set(declarations) & NOT_CITED


@pytest.mark.parametrize("binding_id", sorted(TRANCHES))
def test_rows_are_local_and_keep_their_physlib_gap_reason(binding_id):
    spec = TRANCHES[binding_id]
    payload = _packaged_bindings()
    rows = {row["id"]: row for row in payload["inventory"]["operators"]}
    for op in spec["definitions"]:
        assert rows[op]["status"] == "local"
        assert "local Lean proof" in rows[op]["reason"]
        assert binding_id in rows[op]["binding_ids"]


def test_closed_form_definitions_are_not_proof_subjects():
    payload = _packaged_bindings()
    rows = {row["id"]: row for row in payload["inventory"]["operators"]}
    for op in DEFINITIONS_ONLY:
        assert rows[op]["status"] == "gap" and rows[op]["binding_ids"] == []
    roadmap = json.loads((ROOT / "docs/data/lean_roadmap.json").read_text())
    proven = {row["op"] for row in roadmap["rows"] if row["proven"]}
    assert not proven & DEFINITIONS_ONLY


def test_conventions_a_user_could_get_wrong_are_stated():
    stability = " ".join(_binding("dft-stability-energy-differences")["conditions"])
    for phrase in ("nu_i N_i", "per atom", "MP2020", "-(E_full - E_empty - n mu)/(n q)",
                   "affine in the number N of bulk units", "two equivalent surfaces"):
        assert phrase in stability, phrase
    calphad = " ".join(_binding("calphad-binary-equilibrium")["conditions"])
    for phrase in ("per mole of atoms", "Gibbs is not Helmholtz", "binary system", "first-order transition",
                   "S_beta > S_alpha"):
        assert phrase in calphad, phrase
    assert "Caratheodory" in " ".join(_binding("calphad-binary-equilibrium")["remaining_obligations"])


def test_compiled_theorems_use_standard_axioms_only():
    package = os.environ.get("PHYSLIB_BRIDGE_PACKAGE")
    if not package:
        pytest.skip("optional real-compiler check: set PHYSLIB_BRIDGE_PACKAGE to the built package")
    package = (ROOT / package).resolve()
    names = [name for binding_id in sorted(TRANCHES)
             for name in _binding(binding_id)["evidence"]["declarations"]]
    probe = ("import OMAIStabilityEnergies\nimport OMAICalphad\n"
             + "\n".join(f"#print axioms {name}" for name in names) + "\n")
    path = package / ".lake" / "ThermochemStabilityAxioms.lean"
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
