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
            "compute_adsorption_energy": ("adsorptionEnergy", "def adsorptionEnergy (Eadslab Eslab Eadsorbate : ℝ) : ℝ := Eadslab - Eadsorbate - Eslab"),
            "compute_intercalation_voltage": ("intercalationVoltage", "def intercalationVoltage (Efull Eempty n mu q : ℝ) : ℝ := (mu * n + Eempty - Efull) / (n * q)"),
            "compute_surface_energy": ("surfaceEnergy", "def surfaceEnergy (Eslab Ebulk N A : ℝ) : ℝ := (-N * Ebulk + Eslab) / (2 * A)"),
            "compute_grain_boundary_energy": ("grainBoundaryEnergy", "def grainBoundaryEnergy (EGB Ebulk N A : ℝ) : ℝ := (-N * Ebulk + EGB) / (2 * A)"),
            "compute_reaction_energy": ("catalogReactionEnergy", "def catalogReactionEnergy {ι : Type*} [Fintype ι] (c N h : ι → ℝ) : ℝ := ∑ i, c i * N i * h i"),
        },
        "helpers": [
            "def hullEnergy (S : Set ι) (x : ι → κ → ℝ) (h : ι → ℝ) (y : κ → ℝ) : ℝ :=\n  sInf (decompositionEnergies S x h y)",
            "(∀ j, 0 ≤ w j) ∧ (∀ j, j ∉ S → w j = 0) ∧ ∑ j, w j = 1 ∧ ∀ a, ∑ j, w j * x j a = y a",
        ],
        "outputs": {"EnergyAboveHull", "AdsorptionEnergy", "Voltage", "SurfaceEnergy", "GrainBoundaryEnergy",
                    "ReactionEnergy"},
        "key_theorems": {
            "energyAboveHull_affine_invariant": " {S : Set ι} (x : ι → κ → ℝ) (h : ι → ℝ) (c : ℝ)\n    (δ : κ → ℝ) {i : ι} (hi : i ∈ S) :\n    energyAboveHull S x (fun j => h j + (c + ∑ a, δ a * x j a)) i = energyAboveHull S x h i",
            "energyAboveHull_formationEnergy_reference_independent": " (S : Set ι) (Ecell : ι → ℝ)\n    (n : ι → κ → ℝ) (hN : ∀ j ∈ S, ∑ a, n j a ≠ 0) {i : ι} (hi : i ∈ S) (μ μ' : κ → ℝ) :\n    energyAboveHull S (fun j a => n j a / ∑ b, n j b) (fun j => formationEnergy (Ecell j) (n j) μ') i =\n      energyAboveHull S (fun j a => n j a / ∑ b, n j b) (fun j => formationEnergy (Ecell j) (n j) μ) i",
            "adsorptionEnergy_offset_invariant_iff": " {E : Type*} [Fintype E] [DecidableEq E]\n    (Eadslab Eslab Eadsorbate : ℝ) (nAdslab nSlab nAdsorbate : E → ℝ) :\n    (∀ δ : E → ℝ, adsorptionEnergy (Eadslab + ∑ a, nAdslab a * δ a) (Eslab + ∑ a, nSlab a * δ a)\n        (Eadsorbate + ∑ a, nAdsorbate a * δ a) = adsorptionEnergy Eadslab Eslab Eadsorbate) ↔\n      nAdslab = nSlab + nAdsorbate",
            "intercalationVoltage_offset_invariant_iff": " {E : Type*} [Fintype E] [DecidableEq E]\n    (Efull Eempty n mu q : ℝ) (hn : n ≠ 0) (hq : q ≠ 0) (ion : E) (nFull nEmpty : E → ℝ) :\n    (∀ δ : E → ℝ, intercalationVoltage (Efull + ∑ a, nFull a * δ a)\n        (Eempty + ∑ a, nEmpty a * δ a) n (mu + δ ion) q = intercalationVoltage Efull Eempty n mu q) ↔\n      nFull = nEmpty + n • Pi.single ion 1",
            "intercalationVoltage_eq_mean_ocv": " {Ecell E' : ℝ → ℝ} {n mu q : ℝ} {s : Set ℝ}\n    (hs : s.Countable) (hc : ContinuousOn Ecell (Set.uIcc 0 n))\n    (hderiv : ∀ x ∈ Set.Ioo (min 0 n) (max 0 n) \\ s, HasDerivAt Ecell (E' x) x)\n    (hint : IntervalIntegrable E' MeasureTheory.volume 0 n) :\n    intercalationVoltage (Ecell n) (Ecell 0) n mu q =\n      (∫ x in (0 : ℝ)..n, (mu - E' x) / q) / n",
            "surfaceEnergy_thickness_independent_iff": " {e c Ebulk A : ℝ} (hA : A ≠ 0) :\n    (∀ N M : ℝ, N ≠ M →\n        (surfaceEnergy (N * e + c) Ebulk N A = surfaceEnergy (M * e + c) Ebulk M A ↔ Ebulk = e)) ∧\n      (Ebulk = e → ∀ N, surfaceEnergy (N * e + c) Ebulk N A = c / (2 * A)) ∧\n      (Ebulk ≠ e → Tendsto (fun N : ℝ => |surfaceEnergy (N * e + c) Ebulk N A|) atTop atTop)",
            "catalogReactionEnergy_reference_independent_iff": " {σ E : Type*} [Fintype σ] [Fintype E]\n    [DecidableEq E] (c Ecell : σ → ℝ) (n : σ → E → ℝ) (hN : ∀ s, ∑ a, n s a ≠ 0) :\n    (∀ μ : E → ℝ, catalogReactionEnergy c (fun s => ∑ a, n s a)\n        (fun s => formationEnergy (Ecell s) (n s) μ) = ∑ s, c s * Ecell s) ↔\n      ∀ a, ∑ s, c s * n s a = 0",
        },
    },
    "calphad-binary-equilibrium": {
        "source": "lean/bridge/OMAICalphad.lean",
        "contract": "lean/bridge/thermochemistry-formula-contract.json",
        "module": "OMAICalphad",
        "ns": "OMAI.PhyslibBridge.Calphad.",
        "definitions": {
            "solve_equilibrium": ("equilibriumGibbs", "def equilibriumGibbs {P : Type*} (g : P → ℝ → ℝ) (x : ℝ) : ℝ := sInf (mixtureEnergies g x)"),
            "compute_molar_enthalpy": ("molarEnthalpy", "def molarEnthalpy (G : ℝ → ℝ) (T : ℝ) : ℝ := G T - T * derivWithin G (Ioi T) T"),
            "compute_calphad_entropy": ("calphadEntropy", "def calphadEntropy (G : ℝ → ℝ) (T : ℝ) : ℝ := -derivWithin G (Ioi T) T"),
            "compute_chemical_potentials": ("chemicalPotentials", "def chemicalPotentials (G : ℝ → ℝ) (x : ℝ) : Fin 2 → ℝ :=\n  ![G x - x * deriv G x, G x + (1 - x) * deriv G x]"),
            "compute_phase_fractions": ("leverFractions", "def leverFractions (x1 x2 x : ℝ) : Fin 2 → ℝ := ![(x2 - x) / (x2 - x1), (x - x1) / (x2 - x1)]"),
            "compute_transition_temperature": ("transitionTemperature", "def transitionTemperature (dG : ℝ → ℝ) (T1 T2 : ℝ) : ℝ := sInf {T | T ∈ Icc T1 T2 ∧ dG T ≤ 0}"),
        },
        "helpers": ["def equilibriumGibbsT {P : Type*} (gT : ℝ → P → ℝ → ℝ) (x T : ℝ) : ℝ := equilibriumGibbs (gT T) x"],
        "outputs": {"MolarGibbsEnergy", "MolarEnthalpy", "CalphadMolarEntropy", "ChemicalPotential",
                    "PhaseFraction", "TransitionTemperature"},
        "key_theorems": {
            "equilibriumGibbs_isConvexEnvelope": " [Nonempty P] {B : ℝ}\n    (hB : ∀ p y, y ∈ Icc (0 : ℝ) 1 → B ≤ g p y) :\n    ConvexOn ℝ (Icc 0 1) (equilibriumGibbs g) ∧\n      (∀ p y, y ∈ Icc (0 : ℝ) 1 → equilibriumGibbs g y ≤ g p y) ∧\n      ∀ φ : ℝ → ℝ, ConvexOn ℝ (Icc 0 1) φ → (∀ p y, y ∈ Icc (0 : ℝ) 1 → φ y ≤ g p y) →\n        ∀ x ∈ Icc (0 : ℝ) 1, φ x ≤ equilibriumGibbs g x",
            "equilibriumGibbsT_concaveOn": " {gT : ℝ → P → ℝ → ℝ} {I : Set ℝ} (hI : Convex ℝ I)\n    {B : ℝ → ℝ} (hB : ∀ T ∈ I, ∀ p y, y ∈ Icc (0 : ℝ) 1 → B T ≤ gT T p y)\n    (hconc : ∀ p y, y ∈ Icc (0 : ℝ) 1 → ConcaveOn ℝ I (fun T => gT T p y)) (x : ℝ) :\n    ConcaveOn ℝ I (equilibriumGibbsT gT x)",
            "equilibrium_entropy_monotoneOn": " {P : Type*} {gT : ℝ → P → ℝ → ℝ} {I : Set ℝ}\n    (hI : Convex ℝ I) {B : ℝ → ℝ} (hB : ∀ T ∈ I, ∀ p y, y ∈ Icc (0 : ℝ) 1 → B T ≤ gT T p y)\n    (hconc : ∀ p y, y ∈ Icc (0 : ℝ) 1 → ConcaveOn ℝ I (fun T => gT T p y)) (x : ℝ) :\n    MonotoneOn (calphadEntropy (equilibriumGibbsT gT x)) (interior I)",
            "equilibrium_enthalpy_monotoneOn": " {P : Type*} {gT : ℝ → P → ℝ → ℝ} {I : Set ℝ}\n    (hI : Convex ℝ I) {B : ℝ → ℝ} (hB : ∀ T ∈ I, ∀ p y, y ∈ Icc (0 : ℝ) 1 → B T ≤ gT T p y)\n    (hconc : ∀ p y, y ∈ Icc (0 : ℝ) 1 → ConcaveOn ℝ I (fun T => gT T p y))\n    (hpos : ∀ T ∈ interior I, 0 ≤ T) (x : ℝ) :\n    MonotoneOn (molarEnthalpy (equilibriumGibbsT gT x)) (interior I)",
            "commonTangent_of_isLocalExtr": " {g1 g2 : ℝ → ℝ} {x x1 x2 : ℝ} (h1 : x1 < x) (h2 : x < x2)\n    (hd1 : DifferentiableAt ℝ g1 x1) (hd2 : DifferentiableAt ℝ g2 x2)\n    (hext1 : IsLocalExtr (fun y => twoPhaseEnergy g1 g2 x y x2) x1)\n    (hext2 : IsLocalExtr (fun y => twoPhaseEnergy g1 g2 x x1 y) x2) :\n    deriv g1 x1 = (g2 x2 - g1 x1) / (x2 - x1) ∧ deriv g2 x2 = (g2 x2 - g1 x1) / (x2 - x1) ∧\n      chemicalPotentials g1 x1 = chemicalPotentials g2 x2",
            "deriv_equilibriumGibbs_of_twoPhaseChord": " {P : Type*} {g : P → ℝ → ℝ} {g1 g2 : ℝ → ℝ}\n    {x x1 x2 : ℝ} (henv : equilibriumGibbs g =ᶠ[𝓝 x] fun y => twoPhaseEnergy g1 g2 y x1 x2) :\n    deriv (equilibriumGibbs g) x = (g2 x2 - g1 x1) / (x2 - x1)",
            "chemicalPotentials_equilibriumGibbs_of_twoPhaseChord": " {P : Type*} {g : P → ℝ → ℝ}\n    {g1 g2 : ℝ → ℝ} {x x1 x2 : ℝ} (h12 : x1 < x2)\n    (henv : equilibriumGibbs g =ᶠ[𝓝 x] fun y => twoPhaseEnergy g1 g2 y x1 x2)\n    (hd1 : deriv g1 x1 = (g2 x2 - g1 x1) / (x2 - x1))\n    (hd2 : deriv g2 x2 = (g2 x2 - g1 x1) / (x2 - x1)) :\n    chemicalPotentials (equilibriumGibbs g) x = chemicalPotentials g1 x1 ∧\n      chemicalPotentials (equilibriumGibbs g) x = chemicalPotentials g2 x2",
            "transitionTemperature_unique": " {dG dS : ℝ → ℝ} {T1 T2 : ℝ} (h12 : T1 < T2)\n    (hcont : ContinuousOn dG (Icc T1 T2))\n    (hderiv : ∀ T ∈ Ioo T1 T2, HasDerivAt dG (-dS T) T) (hS : ∀ T ∈ Ioo T1 T2, 0 < dS T)\n    (hstart : 0 < dG T1) (hend : dG T2 < 0) :\n    transitionTemperature dG T1 T2 ∈ Ioo T1 T2 ∧ dG (transitionTemperature dG T1 T2) = 0 ∧\n      (∀ T ∈ Icc T1 T2, dG T = 0 → T = transitionTemperature dG T1 T2) ∧\n      (∀ T ∈ Ico T1 (transitionTemperature dG T1 T2), 0 < dG T) ∧\n      (∀ T ∈ Ioc (transitionTemperature dG T1 T2) T2, dG T < 0)",
        },
    },
}
# Restatements of a definition and support lemmas kept out of the citations.
NOT_CITED = {
    "OMAI.PhyslibBridge.Stability.energyAboveHull_nonneg",
    "OMAI.PhyslibBridge.Stability.energyAboveHull_mono_competitors",
    "OMAI.PhyslibBridge.Stability.energyAboveHull_congr",
    "OMAI.PhyslibBridge.Stability.combination_offset_invariant_iff",
    "OMAI.PhyslibBridge.Stability.catalogReactionEnergy_eq_reactionEnergy",
    "OMAI.PhyslibBridge.Stability.reactionEnergy_reference_independent_iff",
    "OMAI.PhyslibBridge.Stability.grainBoundaryEnergy_eq_surfaceEnergy",
    "OMAI.PhyslibBridge.Calphad.equilibriumGibbs_convexOn",
    "OMAI.PhyslibBridge.Calphad.equilibriumGibbs_le",
    "OMAI.PhyslibBridge.Calphad.le_equilibriumGibbs_of_convex",
    "OMAI.PhyslibBridge.Calphad.calphadEntropy_monotoneOn",
    "OMAI.PhyslibBridge.Calphad.molarEnthalpy_monotoneOn",
}
# Removed after review as obvious (quotient and product rules); must not come back.
REMOVED = ("gibbs_helmholtz", "gibbs_duhem", "molarEnthalpy_calphadEntropy_heatCapacity")
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
        assert "theorem " + name + statement + " :=" in source, name


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
        assert "Physlib" in rows[op]["reason"] and "local Lean proof" in rows[op]["reason"]
        assert binding_id in rows[op]["binding_ids"]


def test_closed_form_definitions_are_not_proof_subjects():
    payload = _packaged_bindings()
    rows = {row["id"]: row for row in payload["inventory"]["operators"]}
    for op in DEFINITIONS_ONLY:
        assert rows[op]["status"] == "gap" and rows[op]["binding_ids"] == []
    roadmap = json.loads((ROOT / "docs/data/lean_roadmap.json").read_text())
    proven = {row["op"] for row in roadmap["rows"] if row["proven"]}
    assert not proven & DEFINITIONS_ONLY


def test_reaction_energy_is_bound_after_the_weight_correction():
    """The 2026-10-29 catalog correction multiplies each formula-unit coefficient by the atoms of
    its formula unit; the corrected sum is transcribed and its reference independence is a subject."""
    import sympy as sp
    from omai.stability.operator.edges import compute_reaction_energy
    assert "N^{fu}" in sp.srepr(compute_reaction_energy.formula)
    rows = {row["id"]: row for row in _packaged_bindings()["inventory"]["operators"]}
    row = rows["compute_reaction_energy"]
    assert row["status"] == "local" and row["binding_ids"] == ["dft-stability-energy-differences"]
    binding = next(b for b in _packaged_bindings()["bindings"] if b["id"] == "dft-stability-energy-differences")
    text = " ".join(binding["conditions"])
    for phrase in ("catalogReactionEnergy", "N^fu[i] the atoms of the formula unit",
                   "exactly when the reaction is balanced", "catalogReactionEnergy_reference_independent_iff"):
        assert phrase in text, phrase
    assert "compute_reaction_energy" not in _packaged_bindings().get("gap_reasons", {}).get("operators", {})


def test_obvious_calculus_identities_are_gone():
    source = (ROOT / TRANCHES["calphad-binary-equilibrium"]["source"]).read_text()
    for name in REMOVED:
        assert not re.search(r"theorem " + name + r"\b", source), name


def test_conventions_a_user_could_get_wrong_are_stated():
    stability = " ".join(_binding("dft-stability-energy-differences")["conditions"])
    for phrase in ("lower convex hull, not only for a unique ground state", "MP2020", "one correction class",
                   "MaterialsProjectDFTMixingScheme", "n z e", "q = z e", "stoichiometric slab",
                   "fully periodic bicrystal", "relax_cell=False", "fractional gas-phase references",
                   "-(E_full - E_empty - n mu)/(n q)", "countable set"):
        assert phrase in stability, phrase
    calphad = " ".join(_binding("calphad-binary-equilibrium")["conditions"])
    for phrase in ("per mole of atoms", "Gibbs is not Helmholtz", "binary system", "right temperature derivative",
                   "apparent heat capacity", "line compounds", "unary system or a congruent", "T0 temperature",
                   "1250.0 K", "Continuous transitions"):
        assert phrase in calphad, phrase
    assert "boundary locus" not in _binding("calphad-binary-equilibrium")["statement"]
    obligations = " ".join(_binding("calphad-binary-equilibrium")["remaining_obligations"])
    assert "Caratheodory" in obligations and "reference shift linear in composition" in obligations


def test_registry_pins_this_tranche():
    from physlib_tranches import TRANCHES as REGISTRY
    entry = next(t for t in REGISTRY if t["name"] == "thermochem-stability")
    payload = _packaged_bindings()
    assert entry["bindings"] == set(TRANCHES)
    assert set(entry["contracts"]) == {Path(spec["contract"]).name for spec in TRANCHES.values()}
    subjects = {(t["kind"], t["id"]) for binding_id in TRANCHES
                for t in compiled_targets(_binding(binding_id), payload["inventory"])}
    assert entry["subjects"] == subjects
    assert {p["name"] for p in entry["pairs"]} == {
        spec["ns"] + name for spec in TRANCHES.values() for name, _ in spec["definitions"].values()}


def test_build_record_covers_these_sources_with_standard_axioms():
    record = json.loads((ROOT / "lean/bridge/build-evidence.json").read_text())
    tracked = {spec[key] for spec in TRANCHES.values() for key in ("source", "contract")}
    assert {path: record["sources"][path] for path in tracked} == {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in tracked}
    audit = record["axiom_audit"]
    assert audit["status"] == "passed"
    assert {spec["module"] for spec in TRANCHES.values()} <= set(audit["source_modules"])
    declarations = audit["declarations"]
    names = {name for binding_id in sorted(TRANCHES) for name in _binding(binding_id)["evidence"]["declarations"]}
    names |= {spec["ns"] + name for spec in TRANCHES.values() for name in spec["key_theorems"]}
    names |= NOT_CITED
    for name in sorted(names):
        assert name in declarations, name
        assert set(declarations[name]) <= {"propext", "Classical.choice", "Quot.sound"}, name


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
