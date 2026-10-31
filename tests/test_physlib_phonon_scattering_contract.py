"""Local phonon-scattering proofs: the three linewidth channels and the RTA mean free path.

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
BINDING_ID = "phonon-scattering-channels"
SOURCE = "lean/bridge/OMAIPhononScattering.lean"
CONTRACT = "lean/bridge/phonon-scattering-formula-contract.json"
MODULE = "OMAIPhononScattering"
NS = "OMAI.PhyslibBridge.PhononScattering."
DEFINITIONS = {
    "compute_isotope_scattering": ("isotopeLinewidth", "def isotopeLinewidth {Q ι B : Type*} [Fintype Q] [Fintype ι] [Fintype B]\n    (delta : ℝ → ℝ) (omega : Q → ι → ℝ) (g : B → ℝ) (e : Q → ι → B → Fin 3 → ℂ)\n    (q : Q) (ν : ι) : ℝ :=\n  π / (4 * Fintype.card Q) * omega q ν ^ 2 *\n    ∑ q', ∑ ν', delta (omega q ν - omega q' ν') *\n      ∑ b, g b * ‖∑ α, star (e q ν b α) * e q' ν' b α‖ ^ 2"),
    "compute_linewidth[channel=anharmonic_3ph]": ("anharmonicLinewidth", "def anharmonicLinewidth {Q ι : Type*} [Fintype Q] [AddCommGroup Q] [Fintype ι]\n    (hbar kB T : ℝ) (delta : ℝ → ℝ) (omega : Q → ι → ℝ)\n    (V3 : Q → ι → Q → ι → Q → ι → ℝ) (q : Q) (ν : ι) : ℝ :=\n  π / (2 * Fintype.card Q * hbar ^ 2) *\n    ∑ q', ∑ ν', ∑ ν'', V3 q ν q' ν' (q - q') ν'' *\n      ((1 + bose (hbar * omega q' ν' / (kB * T)) + bose (hbar * omega (q - q') ν'' / (kB * T))) *\n          delta (omega q ν - omega q' ν' - omega (q - q') ν'') +\n        2 * (bose (hbar * omega q' ν' / (kB * T)) - bose (hbar * omega (q - q') ν'' / (kB * T))) *\n          delta (omega q ν + omega q' ν' - omega (q - q') ν''))"),
    "compute_boundary_scattering": ("boundaryLinewidth", "def boundaryLinewidth (v : Fin 3 → ℝ) (L : ℝ) : ℝ := √(∑ α, v α ^ 2) / (2 * L)"),
    "sum_linewidths": ("totalLinewidth", "def totalLinewidth (anh iso bnd : ℝ) : ℝ := anh + iso + bnd"),
    "solve_bte[bte_solver=rta]": ("rtaDisplacement", "def rtaDisplacement (v : Fin 3 → ℝ) (Γ : ℝ) : Fin 3 → ℝ := fun α => v α / (2 * Γ)"),
}
HELPERS = [
    "def bose (x : ℝ) : ℝ := 1 / (exp x - 1)",
    "def norm3 (u : Fin 3 → ℝ) : ℝ := √(∑ α, u α ^ 2)",
]
OUTPUTS = {"Linewidth[channel=isotope]", "Linewidth[channel=anharmonic_3ph]", "Linewidth[channel=boundary]",
           "Linewidth[channel=total]", "MeanFreeDisplacement[bte_solver=rta]"}
KEY_THEOREMS = {
    "isotopeLinewidth_nonneg": "(hg : ∀ b, 0 ≤ g b) : 0 ≤ isotopeLinewidth delta omega g e q ν",
    "isotopeLinewidth_le_dos": "(hg : ∀ b, 0 ≤ g b) (hgmax : ∀ b, g b ≤ gmax)\n    (hnorm : ∀ q ν, ∑ b, ∑ α, ‖e q ν b α‖ ^ 2 = 1) :\n    isotopeLinewidth delta omega g e q ν ≤\n      π / 4 * omega q ν ^ 2 * gmax *\n        ((∑ q', ∑ ν', delta (omega q ν - omega q' ν')) / Fintype.card Q)",
    "anharmonicLinewidth_nonneg": "(hω : 0 < omega q ν) (hV3 : ∀ a b c d e f, 0 ≤ V3 a b c d e f)\n    (hzero : ∀ q' ν' ν'', V3 q ν q' ν' (q - q') ν'' ≠ 0 →\n      0 < omega q' ν' ∧ 0 < omega (q - q') ν'')\n    (hswap : ∀ q' ν' ν'', V3 q ν q' ν' (q - q') ν'' = V3 q ν (q - q') ν'' q' ν')\n    (hdelta : ∀ x, 0 ≤ delta x) (hmono : ∀ x y, |x| ≤ |y| → delta y ≤ delta x) :\n    0 ≤ anharmonicLinewidth hbar kB T delta omega V3 q ν",
    "anharmonicLinewidth_nonneg_of_support": "(hdelta : ∀ x, 0 ≤ delta x) (hsupport : ∀ x, omega q ν < x → delta x = 0) :\n    0 ≤ anharmonicLinewidth hbar kB T delta omega V3 q ν",
    "anharmonicLinewidth_neg_of_nonmonotone": "(∀ x, 0 ≤ delta x) ∧ (∀ x, delta (-x) = delta x) ∧ (∀ q ν, 0 < omega q ν) ∧\n        (∀ a b c d e f, 0 ≤ V3 a b c d e f) ∧\n        (∀ q' ν' ν'', V3 () 0 q' ν' (() - q') ν'' = V3 () 0 (() - q') ν'' q' ν') ∧\n        anharmonicLinewidth 1 1 1 delta omega V3 () 0 < 0",
    "rta_casimir_bound": "(hanh : 0 ≤ anh) (hiso : 0 ≤ iso) :\n    norm3 (rtaDisplacement v (totalLinewidth anh iso (boundaryLinewidth v L))) ≤ L ∧\n      (norm3 (rtaDisplacement v (totalLinewidth anh iso (boundaryLinewidth v L))) = L ↔\n        anh + iso = 0)",
}
# Helpers kept out of the citations.
NOT_CITED = {NS + "bose_pos", NS + "bose_strictAntiOn", NS + "norm3_rtaDisplacement"}


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


def test_catalog_prefactors_are_the_canonical_linewidths():
    """Gamma = Im Sigma = 1/(2 tau): the transcriptions carry pi/(4 N_q), pi/(2 N_q hbar^2) and 2L."""
    source = (ROOT / SOURCE).read_text()
    assert "π / (4 * Fintype.card Q)" in source
    assert "π / (2 * Fintype.card Q * hbar ^ 2)" in source
    assert "/ (2 * L)" in source


def test_local_module_uses_mathlib_only_and_no_escape_hatch():
    source = (ROOT / SOURCE).read_text()
    imports = re.findall(r"^public import (\S+)", source, re.M)
    assert imports and all(name.startswith("Mathlib.") for name in imports)
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
    declarations = binding["evidence"]["declarations"]
    assert declarations == [NS + name for name in KEY_THEOREMS]
    assert not set(declarations) & NOT_CITED


def test_rows_are_local_and_proven_on_the_roadmap():
    roadmap = json.loads((ROOT / "docs/data/lean_roadmap.json").read_text())
    assert set(DEFINITIONS) <= {r["op"] for r in roadmap["rows"] if r["proven"]}
    payload = _packaged_bindings()
    rows = {row["id"]: row for row in payload["inventory"]["operators"] + payload["inventory"]["nodes"]}
    anchored = {(t["kind"], t["id"]) for b in payload["bindings"] if b["relation"] != "local"
                for t in b["targets"]}
    for op in DEFINITIONS:
        assert ("operator", op) not in anchored
        assert rows[op]["status"] == "local"
        assert "local Lean proof" in rows[op]["reason"]
        assert BINDING_ID in rows[op]["binding_ids"]


def test_conventions_a_user_could_get_wrong_are_stated():
    binding = _binding()
    conditions = " ".join(binding["conditions"])
    for phrase in ("Gamma = Im Sigma = 1/(2 tau)", "twice it", "1/N_q", "closed under q - q'",
                   "integrates to the number of branches", "acoustic modes at Gamma",
                   "permutation symmetry of the third-order force constants", "signed offset", "L > 0"):
        assert phrase in conditions, phrase
    statement = binding["statement"]
    for phrase in ("covers the catalog's Gaussian", "not monotone in |x|", "same factor 2", "L/2"):
        assert phrase in statement, phrase
    assert "linear THz" in binding["conventions"]["frequency_convention"]


def test_compiled_theorems_use_standard_axioms_only():
    package = os.environ.get("PHYSLIB_BRIDGE_PACKAGE")
    if not package:
        pytest.skip("optional real-compiler check: set PHYSLIB_BRIDGE_PACKAGE to the built package")
    package = (ROOT / package).resolve()
    names = _binding()["evidence"]["declarations"]
    probe = "import OMAIPhononScattering\n" + "\n".join(f"#print axioms {name}" for name in names) + "\n"
    path = package / ".lake" / "PhononScatteringAxioms.lean"
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
