"""Local linearized-BTE proofs: Chaput's collision matrix, its positivity, the RTA limit and kappa.

Frozen literals are reviewed pins. The compiler probe consumes an already-built
package selected with PHYSLIB_BRIDGE_PACKAGE and never writes build evidence.
The global coverage ledger lives in tests/physlib_tranches.py, and this file
checks only its own binding.
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
BINDING_ID = "linearized-bte-conductivity"
SOURCE = "lean/bridge/OMAILinearizedBTE.lean"
CONTRACT = "lean/bridge/linearized-bte-formula-contract.json"
MODULE = "OMAILinearizedBTE"
NS = "OMAI.PhyslibBridge.LinearizedBTE."
DEFINITIONS = {
    "solve_bte[bte_solver=direct_inverse]": ("lbteSolves", "def lbteSolves {κ : Type*} [Fintype κ] (M : Matrix κ κ ℝ) (c : κ → ℝ) (v F : κ → Fin 3 → ℝ) :\n    Prop :=\n  ∀ m α, ∑ m', M m m' * F m' α = c m * v m α"),
    "contract_kappa[bte_solver=direct_inverse]": ("lbteKappa", 'def lbteKappa {κ : Type*} [Fintype κ] (c : κ → ℝ) (v F : κ → Fin 3 → ℝ) (V Nq : ℝ) :\n    Matrix (Fin 3) (Fin 3) ℝ :=\n  fun α β => (∑ m, c m * v m α * F m β) / (V * Nq)'),
}
HELPERS = ['def bose (x : ℝ) : ℝ := 1 / (exp x - 1)', "def chaputCollision {Q ι : Type*} [Fintype Q] [AddCommGroup Q] [DecidableEq Q] [Fintype ι]\n    [DecidableEq ι] (hbar kB T : ℝ) (delta : ℝ → ℝ) (omega Gamma : Q → ι → ℝ)\n    (V3 : Q → ι → Q → ι → Q → ι → ℝ) : Matrix (Q × ι) (Q × ι) ℝ :=\n  fun m m' =>\n    2 * Gamma m.1 m.2 * (if m = m' then 1 else 0) +\n      π / (Fintype.card Q * hbar ^ 2) *\n        ∑ ν'', V3 m.1 m.2 m'.1 m'.2 (-m.1 - m'.1) ν'' *\n          (2 * √(bose (hbar * omega (-m.1 - m'.1) ν'' / (kB * T)) *\n            (1 + bose (hbar * omega (-m.1 - m'.1) ν'' / (kB * T))))) *\n          (delta (omega m'.1 m'.2 - omega m.1 m.2 + omega (-m.1 - m'.1) ν'') +\n            delta (omega m'.1 m'.2 - omega m.1 m.2 - omega (-m.1 - m'.1) ν'') +\n            delta (omega m'.1 m'.2 + omega m.1 m.2 - omega (-m.1 - m'.1) ν''))", "def lbteMatrix {κ : Type*} (c : κ → ℝ) (Ω : Matrix κ κ ℝ) : Matrix κ κ ℝ :=\n  fun m m' => √(c m * c m') * Ω m m'", 'def boseRoot (hbar kB T ω : ℝ) : ℝ :=\n  √(bose (hbar * ω / (kB * T)) * (1 + bose (hbar * ω / (kB * T))))', "def channelSum (delta : ℝ → ℝ) (ω ω' ω'' : ℝ) : ℝ :=\n  delta (ω' - ω + ω'') + delta (ω' - ω - ω'') + delta (ω' + ω - ω'')", "def detailedBalanceLinewidth {Q ι : Type*} [Fintype Q] [AddCommGroup Q] [Fintype ι]\n    (hbar kB T : ℝ) (delta : ℝ → ℝ) (omega : Q → ι → ℝ) (V3 : Q → ι → Q → ι → Q → ι → ℝ)\n    (q : Q) (ν : ι) : ℝ :=\n  π / (2 * Fintype.card Q * hbar ^ 2) *\n    ∑ q', ∑ ν', ∑ ν'', V3 q ν q' ν' (-q - q') ν'' *\n      (boseRoot hbar kB T (omega q' ν') * boseRoot hbar kB T (omega (-q - q') ν'') /\n        boseRoot hbar kB T (omega q ν)) *\n      channelSum delta (omega q ν) (omega q' ν') (omega (-q - q') ν'')", "def collisionSquares {Q ι : Type*} [Fintype Q] [AddCommGroup Q] [Fintype ι]\n    (hbar kB T : ℝ) (delta : ℝ → ℝ) (omega : Q → ι → ℝ) (V3 : Q → ι → Q → ι → Q → ι → ℝ)\n    (x : Q × ι → ℝ) : ℝ :=\n  ∑ a, ∑ b, ∑ ν'', V3 a.1 a.2 b.1 b.2 (-a.1 - b.1) ν'' *\n    channelSum delta (omega a.1 a.2) (omega b.1 b.2) (omega (-a.1 - b.1) ν'') *\n    (boseRoot hbar kB T (omega a.1 a.2) * boseRoot hbar kB T (omega b.1 b.2) *\n      boseRoot hbar kB T (omega (-a.1 - b.1) ν'')) *\n    (x a / boseRoot hbar kB T (omega a.1 a.2) + x b / boseRoot hbar kB T (omega b.1 b.2) +\n      x (-a.1 - b.1, ν'') / boseRoot hbar kB T (omega (-a.1 - b.1) ν'')) ^ 2"]
OUTPUTS = {"MeanFreeDisplacement[bte_solver=direct_inverse]", "ThermalConductivity[bte_solver=direct_inverse]"}
KEY_THEOREMS = {
    'chaputCollision_isSymm': "{hbar kB T : ℝ} (delta : ℝ → ℝ) (omega Gamma : Q → ι → ℝ)\n    (V3 : Q → ι → Q → ι → Q → ι → ℝ) (heven : ∀ x, delta (-x) = delta x)\n    (hV3 : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = V3 q' ν' q ν (-q - q') ν'') :\n    (chaputCollision hbar kB T delta omega Gamma V3).IsSymm",
    'lbteMatrix_isSymm': '{κ : Type*} (c : κ → ℝ) {Ω : Matrix κ κ ℝ} (hΩ : Ω.IsSymm) :\n    (lbteMatrix c Ω).IsSymm',
    'lbteSolves_rta_limit': "{Q ι : Type*} [Fintype Q] [AddCommGroup Q] [DecidableEq Q]\n    [Fintype ι] [DecidableEq ι] {hbar kB T : ℝ} (delta : ℝ → ℝ) (omega Gamma : Q → ι → ℝ)\n    (V3 : Q → ι → Q → ι → Q → ι → ℝ) (c : Q × ι → ℝ) (v F : Q × ι → Fin 3 → ℝ)\n    (hV3 : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = 0) (hGamma : ∀ q ν, Gamma q ν ≠ 0)\n    (hc : ∀ m, 0 < c m) :\n    lbteSolves (lbteMatrix c (chaputCollision hbar kB T delta omega Gamma V3)) c v F ↔\n      ∀ m α, F m α = v m α / (2 * Gamma m.1 m.2)",
    'lbteKappa_isSymm': '{M : Matrix κ κ ℝ} (hM : M.IsSymm) {c : κ → ℝ} {v F : κ → Fin 3 → ℝ}\n    (h : lbteSolves M c v F) (V Nq : ℝ) : (lbteKappa c v F V Nq).IsSymm',
    'lbteKappa_posSemidef': '[DecidableEq κ] {Ω : Matrix κ κ ℝ} (hΩ : Ω.PosSemidef) {c : κ → ℝ}\n    (hc : ∀ m, 0 ≤ c m) {v F : κ → Fin 3 → ℝ} (h : lbteSolves (lbteMatrix c Ω) c v F) {V Nq : ℝ}\n    (hVN : 0 < V * Nq) : (lbteKappa c v F V Nq).PosSemidef',
    'chaputCollision_quadratic': "{hbar kB T : ℝ} (hh : 0 < hbar) (hk : 0 < kB) (hT : 0 < T)\n    (delta : ℝ → ℝ) (heven : ∀ x, delta (-x) = delta x) (omega Gamma : Q → ι → ℝ)\n    (V3 : Q → ι → Q → ι → Q → ι → ℝ)\n    (h12 : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = V3 q' ν' q ν (-q - q') ν'')\n    (h23 : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = V3 q ν (-q - q') ν'' q' ν')\n    (hzero : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' ≠ 0 →\n      0 < omega q ν ∧ 0 < omega q' ν' ∧ 0 < omega (-q - q') ν'')\n    (x : Q × ι → ℝ) :\n    ∑ a, ∑ b, x a * chaputCollision hbar kB T delta omega Gamma V3 a b * x b =\n      ∑ a, 2 * (Gamma a.1 a.2 - detailedBalanceLinewidth hbar kB T delta omega V3 a.1 a.2) *\n          x a ^ 2 +\n        π / (3 * Fintype.card Q * hbar ^ 2) * collisionSquares hbar kB T delta omega V3 x",
    'chaputCollision_posSemidef': "{hbar kB T : ℝ} (hh : 0 < hbar) (hk : 0 < kB) (hT : 0 < T)\n    (delta : ℝ → ℝ) (hdelta : ∀ x, 0 ≤ delta x) (heven : ∀ x, delta (-x) = delta x)\n    (omega Gamma : Q → ι → ℝ) (V3 : Q → ι → Q → ι → Q → ι → ℝ)\n    (hV3 : ∀ q ν q' ν' ν'', 0 ≤ V3 q ν q' ν' (-q - q') ν'')\n    (h12 : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = V3 q' ν' q ν (-q - q') ν'')\n    (h23 : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = V3 q ν (-q - q') ν'' q' ν')\n    (hzero : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' ≠ 0 →\n      0 < omega q ν ∧ 0 < omega q' ν' ∧ 0 < omega (-q - q') ν'')\n    (hGamma : ∀ q ν, detailedBalanceLinewidth hbar kB T delta omega V3 q ν ≤ Gamma q ν) :\n    (chaputCollision hbar kB T delta omega Gamma V3).PosSemidef",
    'anharmonicLinewidth_eq_detailedBalance': "{hbar kB T : ℝ} (hh : 0 < hbar) (hk : 0 < kB)\n    (hT : 0 < T) (delta : ℝ → ℝ) (hshell : ∀ x, x ≠ 0 → delta x = 0) (omega : Q → ι → ℝ)\n    (homega : ∀ q ν, omega (-q) ν = omega q ν) (V3 Vd : Q → ι → Q → ι → Q → ι → ℝ)\n    (hrel : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = Vd q ν (-q') ν' (q + q') ν'')\n    (q : Q) (ν : ι) (hω : 0 < omega q ν)\n    (hzero : ∀ q' ν' ν'', Vd q ν q' ν' (q - q') ν'' ≠ 0 →\n      0 < omega q' ν' ∧ 0 < omega (q - q') ν'')\n    (hswap : ∀ q' ν' ν'', Vd q ν q' ν' (q - q') ν'' = Vd q ν (q - q') ν'' q' ν') :\n    PhononScattering.anharmonicLinewidth hbar kB T delta omega Vd q ν =\n      detailedBalanceLinewidth hbar kB T delta omega V3 q ν",
    'chaputCollision_posSemidef_onShell': "{hbar kB T : ℝ} (hh : 0 < hbar) (hk : 0 < kB)\n    (hT : 0 < T) (delta : ℝ → ℝ) (hdelta : ∀ x, 0 ≤ delta x) (hshell : ∀ x, x ≠ 0 → delta x = 0)\n    (omega Gamma : Q → ι → ℝ) (homega : ∀ q ν, omega (-q) ν = omega q ν)\n    (V3 Vd : Q → ι → Q → ι → Q → ι → ℝ) (hV3 : ∀ q ν q' ν' ν'', 0 ≤ V3 q ν q' ν' (-q - q') ν'')\n    (h12 : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = V3 q' ν' q ν (-q - q') ν'')\n    (h23 : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = V3 q ν (-q - q') ν'' q' ν')\n    (hzero : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' ≠ 0 →\n      0 < omega q ν ∧ 0 < omega q' ν' ∧ 0 < omega (-q - q') ν'')\n    (hrel : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = Vd q ν (-q') ν' (q + q') ν'')\n    (hGamma : ∀ q ν,\n      PhononScattering.anharmonicLinewidth hbar kB T delta omega Vd q ν ≤ Gamma q ν) :\n    (chaputCollision hbar kB T delta omega Gamma V3).PosSemidef",
    'lbteKappa_posSemidef_onShell': "{B : Type*} [Fintype B] {hbar kB T : ℝ} (hh : 0 < hbar)\n    (hk : 0 < kB) (hT : 0 < T) (delta : ℝ → ℝ) (hdelta : ∀ x, 0 ≤ delta x)\n    (hshell : ∀ x, x ≠ 0 → delta x = 0) (omega : Q → ι → ℝ)\n    (homega : ∀ q ν, omega (-q) ν = omega q ν) (V3 Vd : Q → ι → Q → ι → Q → ι → ℝ)\n    (hV3 : ∀ q ν q' ν' ν'', 0 ≤ V3 q ν q' ν' (-q - q') ν'')\n    (h12 : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = V3 q' ν' q ν (-q - q') ν'')\n    (h23 : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = V3 q ν (-q - q') ν'' q' ν')\n    (hzero : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' ≠ 0 →\n      0 < omega q ν ∧ 0 < omega q' ν' ∧ 0 < omega (-q - q') ν'')\n    (hrel : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = Vd q ν (-q') ν' (q + q') ν'')\n    (deltaIso : ℝ → ℝ) (hdeltaIso : ∀ x, 0 ≤ deltaIso x) (g : B → ℝ) (hg : ∀ b, 0 ≤ g b)\n    (e : Q → ι → B → Fin 3 → ℂ) {L : ℝ} (hL : 0 ≤ L) {c : Q × ι → ℝ} (hc : ∀ m, 0 ≤ c m)\n    {v F : Q × ι → Fin 3 → ℝ}\n    (h : lbteSolves (lbteMatrix c (chaputCollision hbar kB T delta omega\n      (fun q ν => PhononScattering.totalLinewidth\n        (PhononScattering.anharmonicLinewidth hbar kB T delta omega Vd q ν)\n        (PhononScattering.isotopeLinewidth deltaIso omega g e q ν)\n        (PhononScattering.boundaryLinewidth (v (q, ν)) L)) V3)) c v F)\n    {V Nq : ℝ} (hVN : 0 < V * Nq) : (lbteKappa c v F V Nq).PosSemidef",
}
NOT_CITED = {NS + name for name in (
    "lbteKappa_eq_sum", "lbteMatrix_eq_conj", "chaputCollision_isSymm_of_all", "bose_pos'", "sqrt_bose",
    "bose_decay", "bose_absorb", "pair_onShell", "tripleSum_swap12", "tripleSum_swap23", "sos_identity",
    "sum_partner_swap", "sum_eq_of_pair", "boseRoot_nonneg", "boseRoot_pos", "channelSum_nonneg",
    "channelSum_swap12", "channelSum_swap23", "even_of_shell")}
# The digest of solve_bte[bte_solver=direct_inverse]'s auxiliary_formulas[0], the M and Omega~ that
# lbteMatrix and chaputCollision transcribe.
# An edit to Omega~ moves it, so this binding is re-reviewed rather than left on the old matrix.
AUXILIARY_SHA256 = "78c67a3e7822bfbe8d1fb087a0f0f589cd0b0cf40027d606f665e25b2131e6ea"


def _binding():
    return next(b for b in _packaged_bindings()["bindings"] if b["id"] == BINDING_ID)


def test_contract_endpoints_match_the_live_catalog_and_source():
    contract = json.loads((ROOT / CONTRACT).read_text())
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
    assert {row["id"] for row in contract["nodes"]} == OUTPUTS
    for row in contract["nodes"]:
        assert row["uid"] == nodes[row["id"]]["uid"]


def test_lean_definitions_are_the_reviewed_transcriptions():
    source = (ROOT / SOURCE).read_text()
    for _, text in DEFINITIONS.values():
        assert text in source, text
    for text in HELPERS:
        assert text in source, text
    for name, statement in KEY_THEOREMS.items():
        assert re.search(r"theorem " + name + r"\b", source), name
        assert statement in source, name


def test_transcribed_auxiliary_formula_is_the_reviewed_one():
    from omai.map_data import DOMAINS
    from omai.operator.identity import formula_fingerprint
    op = next(e for d in DOMAINS for e in d.edges if e.name == "solve_bte[bte_solver=direct_inverse]")
    text = formula_fingerprint(op.auxiliary_formulas[0])
    assert hashlib.sha256(text.encode()).hexdigest() == AUXILIARY_SHA256


def test_collision_matrix_carries_the_catalog_constants():
    """The diagonal is 2 Gamma, the off-diagonal constant pi/(N_q hbar^2) and the weight 2 sqrt(n''(n'' + 1))."""
    source = (ROOT / SOURCE).read_text()
    for text in ("2 * Gamma m.1 m.2 * (if m = m' then 1 else 0)", "π / (Fintype.card Q * hbar ^ 2)",
                 "(-m.1 - m'.1)", "√(c m * c m') * Ω m m'"):
        assert text in source, text


def test_module_uses_mathlib_and_local_modules_only():
    source = (ROOT / SOURCE).read_text()
    imports = re.findall(r"^public import (\S+)", source, re.M)
    local = {"OMAIPhyslibKappaContraction", "OMAIPhononScattering"}
    assert imports and all(name.startswith("Mathlib.") or name in local for name in imports)
    for name in local:
        dep = (ROOT / "lean/bridge" / f"{name}.lean").read_text()
        assert all(n.startswith("Mathlib.") for n in re.findall(r"^public import (\S+)", dep, re.M))
    for word in ("sorry", "admit", "axiom", "native_decide", "unsafe", "set_option"):
        assert not re.search(r"\b" + word + r"\b", source), word


def test_binding_targets_are_its_proof_subjects():
    binding = _binding()
    payload = _packaged_bindings()
    assert binding["relation"] == "local" and binding["sources"] == []
    assert binding["conditions"] and binding["remaining_obligations"]
    assert binding["evidence"]["kind"] == "compiled_bridge"
    assert binding["evidence"]["module"] == MODULE
    assert binding["evidence"]["source_path"] == SOURCE
    subjects = {(t["kind"], t["id"]) for t in compiled_targets(binding, payload["inventory"])}
    expected = {("operator", op) for op in DEFINITIONS} | {("node", node) for node in OUTPUTS}
    assert subjects == expected
    assert {(t["kind"], t["id"]) for t in binding["targets"]} == expected
    assert binding["evidence"]["declarations"] == [NS + name for name in KEY_THEOREMS]
    assert not set(binding["evidence"]["declarations"]) & NOT_CITED


def test_rows_are_local_and_proven_on_the_roadmap():
    roadmap = json.loads((ROOT / "docs/data/lean_roadmap.json").read_text())
    assert set(DEFINITIONS) <= {r["op"] for r in roadmap["rows"] if r["proven"]}
    payload = _packaged_bindings()
    rows = {row["id"]: row for row in payload["inventory"]["operators"]}
    for op in DEFINITIONS:
        assert rows[op]["status"] == "local"
        assert "local Lean proof" in rows[op]["reason"]
        assert BINDING_ID in rows[op]["binding_ids"]


def test_conventions_a_user_could_get_wrong_are_stated():
    binding = _binding()
    conditions = " ".join(binding["conditions"])
    for phrase in ("Gamma = Im Sigma = 1/(2 tau)", "the constant of 2 Gamma", "closed under q + q' + q'' = 0",
                   "delta(-x) = delta(x)", "time-reversal gauge", "exact energy conservation",
                   "every permutation of its three modes", "physical_mode", "cutoff_frequency", "pinv_method=1",
                   "odd under q -> -q", "Gamma != 0"):
        assert phrase in conditions, phrase
    assert "with no positivity hypothesis" in binding["statement"]
    assert "Gamma >= Gamma^db" in binding["statement"]
    assert "momentum-conserving triples" in binding["statement"]
    assert "not proved here" in " ".join(binding["remaining_obligations"])


def test_compiled_theorems_use_standard_axioms_only():
    package = os.environ.get("PHYSLIB_BRIDGE_PACKAGE")
    if not package:
        pytest.skip("optional real-compiler check: set PHYSLIB_BRIDGE_PACKAGE to the built package")
    package = (ROOT / package).resolve()
    names = _binding()["evidence"]["declarations"]
    probe = "import OMAILinearizedBTE\n" + "\n".join(f"#print axioms {name}" for name in names) + "\n"
    path = package / ".lake" / "LinearizedBTEAxioms.lean"
    path.write_text(probe)
    timeout = float(os.environ.get("OMAI_LEAN_PROBE_TIMEOUT", "1800"))
    try:
        result = subprocess.run(["lake", "--no-build", "env", "lean", str(path)], cwd=package,
                                text=True, capture_output=True, timeout=timeout, check=False)
    finally:
        path.unlink()
    assert result.returncode == 0, result.stdout + result.stderr
    reported = re.findall(r"'([^']+)' depends on axioms: \[([^\]]*)\]", result.stdout)
    assert {name for name, _ in reported} == set(names)
    for name, axioms in reported:
        assert set(a.strip() for a in axioms.split(",")) <= {"propext", "Classical.choice", "Quot.sound"}, name
