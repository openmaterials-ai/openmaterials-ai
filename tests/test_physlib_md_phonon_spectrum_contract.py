"""Molecular-dynamics correlation, VACF spectrum and phonon-spectrum proofs.

Frozen literals are reviewed pins. The compiler probe consumes an already-built
package selected with PHYSLIB_BRIDGE_PACKAGE and never writes build evidence.
Global coverage totals are pinned in tests/physlib_tranches.py; this file checks
only its own bindings.
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
    "md-correlation-estimators": {
        "source": "lean/bridge/OMAIMDCorrelations.lean",
        "contract": "lean/bridge/md-correlations-formula-contract.json",
        "module": "OMAIMDCorrelations",
        "ns": "OMAI.PhyslibBridge.MDCorrelations.",
        "relation": "local",
        "sources": set(),
        "imports": None,
        "definitions": {
            "compute_velocity_autocorrelation": ("catalogVACF", "def catalogVACF (N n : ℕ) (v : Fin N → Fin 3 → ℕ → ℝ) (tau : ℕ) : ℝ :=\n  (∑ t ∈ Icc 1 n, ∑ i, ∑ a, v i a t * v i a (t + tau)) / (N * n)"),
            "compute_msd": ("catalogMSD", "def catalogMSD (N n : ℕ) (r : Fin N → Fin 3 → ℕ → ℝ) (tau : ℕ) : ℝ :=\n  (∑ t ∈ Icc 1 n, ∑ i, ∑ a, (r i a (t + tau) - r i a t) ^ 2) / (N * n)"),
            "autocorrelate_heat_current": ("catalogHeatACF", "def catalogHeatACF (n : ℕ) (J : Fin 3 → ℕ → ℝ) (a b : Fin 3) (tau : ℕ) : ℝ :=\n  (∑ t ∈ Icc 1 n, J a t * J b (t + tau)) / n"),
            "contract_kappa[transport_model=green_kubo]": ("greenKubo", "def greenKubo (V T kB tauMax : ℝ) (Jcorr : ℝ → ℝ) : ℝ :=\n  V * (∫ tau in (0 : ℝ)..tauMax, Jcorr tau) / (kB * T ^ 2)"),
        },
        "helpers": [
            "def helfandMoment (n : ℕ) (G : Fin 3 → ℕ → ℝ) (a b : Fin 3) (tau : ℕ) : ℝ :=\n  (∑ t ∈ Icc 1 n, (G a (t + tau) - G a t) * (G b (t + tau) - G b t)) / n",
            "def linearInterp (dt : ℝ) (c : ℕ → ℝ) (s : ℝ) : ℝ :=\n  c ⌊s / dt⌋₊ + (c (⌊s / dt⌋₊ + 1) - c ⌊s / dt⌋₊) * (s / dt - ⌊s / dt⌋₊)",
            "def lagSum (x y : ℕ → ℝ) (n k : ℕ) : ℝ := ∑ t ∈ Icc 1 n, x t * y (t + k)",
        ],
        "outputs": {"VelocityAutocorrelation", "MeanSquaredDisplacement", "HeatCurrentACF",
                    "ThermalConductivity[transport_model=green_kubo]"},
        "key_theorems": {
            "catalogMSD_eq_vacf": "catalogMSD N n r tau = dt ^ 2 * (tau * catalogVACF N n v 0 +\n      2 * ∑ k ∈ Ico 1 tau, ((tau : ℝ) - k) * catalogVACF N n v k)",
            "greenKubo_symm_eq_helfand": "V / (4 * kB * T ^ 2 * dt) *\n        (helfandMoment n G a b (m + 1) - helfandMoment n G a b (m - 1))",
            "catalogHeatACF_eq_invDFT": "𝓕⁻ (fun k => (starRingEnd ℂ) (𝓕 (fun j : ZMod n => (J a j.val : ℂ)) k) *",
        },
        "not_cited": {"sum_Icc_eq_sum_range", "sum_range_shift_periodic", "sum_Icc_shift_periodic",
                      "increment_eq_sum", "double_sum_by_lag", "increment_product_sum", "linearInterp_eqOn",
                      "integral_linearInterp_piece", "trapezoid_sum", "integral_linearInterp_of_pos",
                      "integral_linearInterp", "helfandMoment_eq", "helfandMoment_succ_sub",
                      "catalogHeatACF_zero_comm", "sum_conj_mul_shift_eq_invDFT"},
    },
    "vacf-spectrum-lorentzian-limit": {
        "source": "lean/bridge/OMAIVACFSpectrum.lean",
        "contract": "lean/bridge/vacf-spectrum-formula-contract.json",
        "module": "OMAIVACFSpectrum",
        "ns": "OMAI.PhyslibBridge.VACFSpectrum.",
        "relation": "local",
        "sources": set(),
        "imports": None,
        "definitions": {
            "fourier_to_dos": ("catalogFourierDOS", "def catalogFourierDOS (Cv : ℝ → ℝ) (omega : ℝ) : ℝ :=\n  (∫ tau in Ioi 0, cos (omega * tau) * Cv tau) / π"),
        },
        "helpers": [
            "def dampedVACF {M : ℕ} (A Gamma w : Fin M → ℝ) (tau : ℝ) : ℝ :=\n  ∑ m, A m * exp (-Gamma m * tau) * cos (w m * tau)",
            "def lorentzian (Gamma x : ℝ) : ℝ := Gamma / (π * (Gamma ^ 2 + x ^ 2))",
        ],
        "outputs": {"PhononDOS"},
        "key_theorems": {
            "catalogFourierDOS_damped": "∑ m, A m / 2 * (lorentzian (Gamma m) (omega - w m) + lorentzian (Gamma m) (omega + w m))",
            "integral_catalogFourierDOS_damped": "∫ omega, catalogFourierDOS (dampedVACF A Gamma w) omega = dampedVACF A Gamma w 0",
            "tendsto_catalogFourierDOS_zero_linewidth": "(𝓝[>] 0) (𝓝 (∑ m, A m / 2 * (phi (w m) + phi (-w m))))",
        },
        "not_cited": {"integrableOn_exp_neg_mul_cos", "integral_exp_neg_mul_cos", "cos_mul_dampedVACF",
                      "integral_lorentzian", "integrable_lorentzian", "lorentzian_eq_scaled", "unitLorentzian_peak"},
    },
    "crystal-dos-landauer-conductance": {
        "source": "lean/bridge/OMAIPhyslibPhononSpectrum.lean",
        "contract": "lean/bridge/phonon-spectrum-formula-contract.json",
        "module": "OMAIPhyslibPhononSpectrum",
        "ns": "OMAI.PhyslibBridge.PhononSpectrum.",
        "relation": "conditional",
        "sources": {
            ("Physlib.CondensedMatter.Crystal.Basic", "Physlib.CondensedMatter.Crystal", "structure", 65),
            ("Physlib.StatisticalMechanics.CanonicalEnsemble.Lemmas", "CanonicalEnsemble.heatCapacity", "def", 417),
            ("Physlib.QuantumMechanics.HarmonicOscillator.OneDimension.Basic",
             "QuantumMechanics.OneDimension.HarmonicOscillator", "structure", 63),
            ("Physlib.Thermodynamics.Temperature.Basic", "Temperature", "structure", 32),
        },
        "imports": ["OMAIPhyslibPhononDispersion", "OMAIPhyslibHarmonicEnsemble",
                    "Mathlib.Analysis.Fourier.FiniteAbelian.PontryaginDuality", "Mathlib.NumberTheory.ZetaValues",
                    "Mathlib.Analysis.SpecialFunctions.Gamma.Basic",
                    "Mathlib.MeasureTheory.Integral.DominatedConvergence",
                    "Mathlib.MeasureTheory.Integral.IntegralEqImproper"],
        "definitions": {
            "compute_dos": ("catalogDOS", "def catalogDOS {Q ι : Type*} [Fintype Q] [Fintype ι] (omega : Q → ι → ℝ) : Measure ℝ :=\n  ((Fintype.card Q : ℝ≥0∞)⁻¹) • ∑ q, ∑ ν, Measure.dirac (omega q ν)"),
            "compute_conductance[transport_model=landauer]": ("catalogLandauer", "def catalogLandauer (hbar kB : ℝ) (trans : ℝ → ℝ) (T : ℝ) : ℝ :=\n  (∫ omega in Ioi 0, hbar * omega * trans omega *\n    deriv (fun t => boseOccupation (hbar * omega / (kB * t))) T) / (2 * π)"),
        },
        "helpers": [
            "Real.sqrt ((Φ.dynamicalMatrix_isHermitian ψ (fun R => (AddChar.map_neg_eq_conj ψ R).symm)\n    M).eigenvalues ν)",
            "def boseKernel (x : ℝ) : ℝ := x ^ 2 * exp x / (exp x - 1) ^ 2",
        ],
        "outputs": {"PhononDOS", "ThermalConductance[transport_model=landauer]"},
        "key_theorems": {
            "crystalDOS_sum_rules": "∫ _, (1 : ℝ) ∂(catalogDOS (crystalFrequencies Φ M)) = 3 * Fintype.card C.UnitCell ∧",
            "landauerWeight_eq_heatCapacity": "(harmonicEnsemble Q).heatCapacity T",
            "catalogLandauer_eq_heatCapacity": "(∫ omega in Ioi 0, trans omega * (harmonicEnsemble (Q omega)).heatCapacity T) / (2 * π)",
            "catalogLandauer_unit_transmission": "catalogLandauer hbar kB (fun _ => 1) T = π ^ 2 * kB ^ 2 * T / (3 * (2 * π * hbar))",
        },
        # Support lemmas, the Bose integral and the restatement with Physlib's h = 2 pi hbar.
        "not_cited": {"integral_catalogDOS", "sum_trace_dynamicalMatrix", "landauerWeight_eq",
                      "boseKernel_eq_tsum", "integral_sq_mul_exp_neg", "integral_boseKernel",
                      "landauerWeight_eq_boseKernel", "catalogLandauer_unit_transmission_physlib"},
    },
}
# The heat-current producer: a recorded catalog defect, never a proof subject.
DEFECT = "compute_heat_current"
NOTHING_TO_PROVE = {"contract_diffusivity"}


def _binding(binding_id):
    return next(b for b in _packaged_bindings()["bindings"] if b["id"] == binding_id)


def _imports(source):
    return re.findall(r"^public import (\S+)", source, re.M)


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
        assert "definition_source_path" not in row
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
    for word in ("sorry", "admit", "axiom", "native_decide", "unsafe", "set_option"):
        assert not re.search(r"\b" + word + r"\b", source), word


@pytest.mark.parametrize("binding_id", sorted(TRANCHES))
def test_module_imports_match_its_relation(binding_id):
    spec = TRANCHES[binding_id]
    imports = _imports((ROOT / spec["source"]).read_text())
    assert imports
    if spec["relation"] == "local":
        assert all(name.startswith("Mathlib.") for name in imports)
    else:
        assert imports == spec["imports"]


@pytest.mark.parametrize("binding_id", sorted(TRANCHES))
def test_binding_targets_are_its_proof_subjects(binding_id):
    spec = TRANCHES[binding_id]
    binding = _binding(binding_id)
    payload = _packaged_bindings()
    assert binding["relation"] == spec["relation"]
    assert {(s["module"], s["name"], s["kind"], s["line"]) for s in binding["sources"]} == spec["sources"]
    assert binding["conditions"] and binding["remaining_obligations"]
    assert binding["evidence"]["kind"] == "compiled_bridge"
    assert binding["evidence"]["module"] == spec["module"]
    assert binding["evidence"]["source_path"] == spec["source"]
    assert "proved_targets" not in binding["evidence"]
    subjects = {(t["kind"], t["id"]) for t in compiled_targets(binding, payload["inventory"])}
    expected = ({("operator", op) for op in spec["definitions"]}
                | {("node", node) for node in spec["outputs"]})
    assert subjects == expected
    assert {(t["kind"], t["id"]) for t in binding["targets"]} == expected
    declarations = binding["evidence"]["declarations"]
    assert declarations and all(name.startswith(spec["ns"]) for name in declarations)
    leaves = {name.removeprefix(spec["ns"]) for name in declarations}
    assert not leaves & spec["not_cited"]
    assert set(spec["key_theorems"]) == leaves


@pytest.mark.parametrize("binding_id", sorted(TRANCHES))
def test_rows_carry_their_status_and_reason(binding_id):
    spec = TRANCHES[binding_id]
    payload = _packaged_bindings()
    rows = {row["id"]: row for row in payload["inventory"]["operators"]}
    for op in spec["definitions"]:
        assert binding_id in rows[op]["binding_ids"]
        if spec["relation"] == "local":
            assert rows[op]["status"] == "local"
            assert "Physlib" in rows[op]["reason"] and "local Lean proof" in rows[op]["reason"]
        else:
            assert rows[op]["status"] == "mapped"


def test_phonon_dos_has_both_a_physlib_anchored_and_a_local_producer_proof():
    payload = _packaged_bindings()
    node = next(row for row in payload["inventory"]["nodes"] if row["id"] == "PhononDOS")
    assert node["status"] == "mapped"
    assert set(node["binding_ids"]) == {"crystal-dos-landauer-conductance", "vacf-spectrum-lorentzian-limit"}


def test_heat_current_is_a_recorded_catalog_defect_and_definitions_stay_unbound():
    rows = {row["id"]: row for row in _packaged_bindings()["inventory"]["operators"]}
    row = rows[DEFECT]
    assert row["status"] == "gap" and row["binding_ids"] == []
    for phrase in ("Catalog defect.", "absolute position", "choice of origin", "off-diagonal stress",
                   "r_ij = r_i - r_j", "W_{i,alpha beta} = (1/2) sum_{j != i} r_{ij,alpha} F_{ij,beta}",
                   "Phys. Rev. B 92, 094301 (2015)"):
        assert phrase in row["reason"], phrase
    for op in NOTHING_TO_PROVE:
        assert rows[op]["status"] == "gap"
        assert "nothing non-obvious to prove" in rows[op]["reason"]
    roadmap = json.loads((ROOT / "docs/data/lean_roadmap.json").read_text())
    proven = {r["op"] for r in roadmap["rows"] if r["proven"]}
    assert DEFECT not in proven and not proven & NOTHING_TO_PROVE
    for spec in TRANCHES.values():
        assert set(spec["definitions"]) <= proven


def test_conventions_a_user_could_get_wrong_are_stated():
    md = " ".join(_binding("md-correlation-estimators")["conditions"])
    for phrase in ("circular-correlation hypothesis", "periodic-padding assumption", "not periodic",
                   "finite-difference velocity of unwrapped positions", "dt^2 F/(2 m)",
                   "energy moment per unit volume (Helfand)", "Jcorr(0)/2", "antisymmetric part",
                   "for a = b no symmetrization is needed", "not hypotheses of the theorem",
                   "exp(-2 pi i j k/n_lag)", "recorded as a defect"):
        assert phrase in md, phrase
    assert "trapezoid rule" in _binding("md-correlation-estimators")["statement"]
    vacf = " ".join(_binding("vacf-spectrum-lorentzian-limit")["conditions"])
    for phrase in ("every linewidth must be positive", "Cv(0)/2 over omega > 0", "factor 2/Cv(0)",
                   "Equal mode weights A_m are not implied", "weak convergence", "omega = 2 pi 10^12 nu"):
        assert phrase in vacf, phrase
    phonon = " ".join(_binding("crystal-dos-landauer-conductance")["conditions"])
    for phrase in ("sum of point masses", "N_q = |G|", "Zero modes count at omega = 0",
                   "on-site self force constant", "full Nat-spectrum oscillator", "harmonic-mode-heat-capacity",
                   "does not by itself establish integrability", "9.46e-13 W/K at 1 K",
                   "Physlib's h is 2 pi hbar"):
        assert phrase in phonon, phrase


def test_registry_pins_this_tranche():
    from physlib_tranches import TRANCHES as REGISTRY
    entry = next(t for t in REGISTRY if t["name"] == "md-phonon-spectrum")
    payload = _packaged_bindings()
    assert entry["bindings"] == set(TRANCHES)
    assert set(entry["contracts"]) == {Path(spec["contract"]).name for spec in TRANCHES.values()}
    subjects = {(t["kind"], t["id"]) for binding_id in TRANCHES
                for t in compiled_targets(_binding(binding_id), payload["inventory"])}
    assert entry["subjects"] == subjects
    assert {p["name"] for p in entry["pairs"]} == {
        spec["ns"] + name for spec in TRANCHES.values() for name, _ in spec["definitions"].values()}
    assert entry["modules"] == ("OMAIMDCorrelations", "OMAIVACFSpectrum", "OMAIPhyslibPhononSpectrum")


def test_compiled_theorems_use_standard_axioms_only():
    package = os.environ.get("PHYSLIB_BRIDGE_PACKAGE")
    if not package:
        pytest.skip("optional real-compiler check: set PHYSLIB_BRIDGE_PACKAGE to the built package")
    package = (ROOT / package).resolve()
    names = [name for binding_id in sorted(TRANCHES)
             for name in _binding(binding_id)["evidence"]["declarations"]]
    probe = ("import OMAIMDCorrelations\nimport OMAIVACFSpectrum\nimport OMAIPhyslibPhononSpectrum\n"
             + "\n".join(f"#print axioms {name}" for name in names) + "\n")
    path = package / ".lake" / "MDPhononSpectrumAxioms.lean"
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
