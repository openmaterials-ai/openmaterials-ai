"""Local linearized-BTE proofs: Chaput's collision matrix, the RTA limit and the conductivity.

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
HELPERS = ['def bose (x : ℝ) : ℝ := 1 / (exp x - 1)', "def chaputCollision {Q ι : Type*} [Fintype Q] [AddCommGroup Q] [DecidableEq Q] [Fintype ι]\n    [DecidableEq ι] (hbar kB T : ℝ) (delta : ℝ → ℝ) (omega Gamma : Q → ι → ℝ)\n    (V3 : Q → ι → Q → ι → Q → ι → ℝ) : Matrix (Q × ι) (Q × ι) ℝ :=\n  fun m m' =>\n    2 * Gamma m.1 m.2 * (if m = m' then 1 else 0) +\n      π / (Fintype.card Q * hbar ^ 2) *\n        ∑ ν'', V3 m.1 m.2 m'.1 m'.2 (-m.1 - m'.1) ν'' *\n          (2 * √(bose (hbar * omega (-m.1 - m'.1) ν'' / (kB * T)) *\n            (1 + bose (hbar * omega (-m.1 - m'.1) ν'' / (kB * T))))) *\n          (delta (omega m'.1 m'.2 - omega m.1 m.2 + omega (-m.1 - m'.1) ν'') +\n            delta (omega m'.1 m'.2 - omega m.1 m.2 - omega (-m.1 - m'.1) ν'') +\n            delta (omega m'.1 m'.2 + omega m.1 m.2 - omega (-m.1 - m'.1) ν''))", "def lbteMatrix {κ : Type*} (c : κ → ℝ) (Ω : Matrix κ κ ℝ) : Matrix κ κ ℝ :=\n  fun m m' => √(c m * c m') * Ω m m'"]
OUTPUTS = {"MeanFreeDisplacement[bte_solver=direct_inverse]", "ThermalConductivity[bte_solver=direct_inverse]"}
KEY_THEOREMS = {
    'chaputCollision_isSymm': "{hbar kB T : ℝ} (delta : ℝ → ℝ) (omega Gamma : Q → ι → ℝ)\n    (V3 : Q → ι → Q → ι → Q → ι → ℝ) (heven : ∀ x, delta (-x) = delta x)\n    (hV3 : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = V3 q' ν' q ν (-q - q') ν'') :\n    (chaputCollision hbar kB T delta omega Gamma V3).IsSymm",
    'lbteMatrix_isSymm': '{κ : Type*} (c : κ → ℝ) {Ω : Matrix κ κ ℝ} (hΩ : Ω.IsSymm) :\n    (lbteMatrix c Ω).IsSymm',
    'lbteSolves_rta_limit': "{Q ι : Type*} [Fintype Q] [AddCommGroup Q] [DecidableEq Q]\n    [Fintype ι] [DecidableEq ι] {hbar kB T : ℝ} (delta : ℝ → ℝ) (omega Gamma : Q → ι → ℝ)\n    (V3 : Q → ι → Q → ι → Q → ι → ℝ) (c : Q × ι → ℝ) (v F : Q × ι → Fin 3 → ℝ)\n    (hV3 : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = 0) (hGamma : ∀ q ν, Gamma q ν ≠ 0)\n    (hc : ∀ m, 0 < c m) :\n    lbteSolves (lbteMatrix c (chaputCollision hbar kB T delta omega Gamma V3)) c v F ↔\n      ∀ m α, F m α = v m α / (2 * Gamma m.1 m.2)",
    'lbteKappa_isSymm': '{M : Matrix κ κ ℝ} (hM : M.IsSymm) {c : κ → ℝ} {v F : κ → Fin 3 → ℝ}\n    (h : lbteSolves M c v F) (V Nq : ℝ) : (lbteKappa c v F V Nq).IsSymm',
    'lbteKappa_posSemidef': '[DecidableEq κ] {Ω : Matrix κ κ ℝ} (hΩ : Ω.PosSemidef) {c : κ → ℝ}\n    (hc : ∀ m, 0 ≤ c m) {v F : κ → Fin 3 → ℝ} (h : lbteSolves (lbteMatrix c Ω) c v F) {V Nq : ℝ}\n    (hVN : 0 < V * Nq) : (lbteKappa c v F V Nq).PosSemidef',
}
NOT_CITED = {NS + "lbteKappa_eq_sum", NS + "lbteMatrix_eq_conj", NS + "chaputCollision_isSymm_of_all"}
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


def test_module_uses_mathlib_and_the_local_contraction_only():
    source = (ROOT / SOURCE).read_text()
    imports = re.findall(r"^public import (\S+)", source, re.M)
    assert imports and all(name.startswith("Mathlib.") or name == "OMAIPhyslibKappaContraction"
                           for name in imports)
    dep = (ROOT / "lean/bridge/OMAIPhyslibKappaContraction.lean").read_text()
    assert all(name.startswith("Mathlib.") for name in re.findall(r"^public import (\S+)", dep, re.M))
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
                   "enters as a hypothesis", "odd under q -> -q", "Gamma != 0"):
        assert phrase in conditions, phrase
    assert "is a hypothesis here, not a result" in binding["statement"]
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
