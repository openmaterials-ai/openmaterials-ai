"""Local effective-medium and cure-kinetics proofs.

Frozen literals are reviewed pins. The compiler probe consumes an already-built
package selected with PHYSLIB_BRIDGE_PACKAGE and never writes build evidence.
Global coverage totals are pinned elsewhere; this file checks only its own
bindings and their place in the local counts.
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
    "composite-effective-medium": {
        "source": "lean/bridge/OMAICompositeConductivity.lean",
        "contract": "lean/bridge/composites-formula-contract.json",
        "module": "OMAICompositeConductivity",
        "ns": "OMAI.PhyslibBridge.Composites.",
        "definitions": {
            "depolarization_factors": ("depolarization", "def depolarization (p : ℝ) : ℝ :=\n  if p = 1 then 1 / 3\n  else if 1 < p then\n    (-√(1 - 1 / p ^ 2) + artanh (√(1 - 1 / p ^ 2))) / (p ^ 2 * (1 - 1 / p ^ 2) ^ ((3 : ℝ) / 2))\n  else\n    (√(-1 + 1 / p ^ 2) - arctan (√(-1 + 1 / p ^ 2))) / (p ^ 2 * (-1 + 1 / p ^ 2) ^ ((3 : ℝ) / 2))"),
            "nan_effective_kappa": ("nanRandom", "def nanRandom (km k11 k33 d1 d3 G f L11 L33 : ℝ) : ℝ :=\n  km * (f * (2 * (1 - L11) * nanBeta km (kapitzaCorrected k11 G d1) L11 +\n      (1 - L33) * nanBeta km (kapitzaCorrected k33 G d3) L33) + 3) /\n    (-f * (2 * L11 * nanBeta km (kapitzaCorrected k11 G d1) L11 +\n      L33 * nanBeta km (kapitzaCorrected k33 G d3) L33) + 3)"),
            "nan_effective_kappa_aligned": ("nanAligned", "def nanAligned (km k33 d3 G f L33 : ℝ) : ℝ :=\n  km * (f * (1 - L33) * nanBeta km (kapitzaCorrected k33 G d3) L33 + 1) /\n    (-L33 * f * nanBeta km (kapitzaCorrected k33 G d3) L33 + 1)"),
            "hasselman_johnson": ("hasselmanJohnson", "def hasselmanJohnson (km k33 a G f : ℝ) : ℝ :=\n  km * (2 * f * (-km + (1 - km / (G * a)) * k33) + 2 * km + (1 + 2 * km / (G * a)) * k33) /\n    (-f * (-km + (1 - km / (G * a)) * k33) + 2 * km + (1 + 2 * km / (G * a)) * k33)"),
        },
        "helpers": [
            "def kapitzaCorrected (k G d : ℝ) : ℝ := k / (1 + 2 * k / (G * d))",
            "def nanBeta (km kc L : ℝ) : ℝ := (-km + kc) / (L * (-km + kc) + km)",
        ],
        "outputs": {"DepolarizationFactor", "ThermalConductivity[effective_medium=nan,orientation=random]",
                    "ThermalConductivity[effective_medium=nan,orientation=aligned]"},
        "key_theorems": {
            "depolarization_eq_integral": "depolarization p = ∫ t in (0 : ℝ)..1, depolIntegrand p t",
            "depolarization_strictAntiOn": "StrictAntiOn depolarization (Ioi 0)",
            "hasselmanJohnson_critical_radius": "(km < hasselmanJohnson km kp a G f ↔ criticalRadius km kp G < a) ∧",
            "nanAligned_strictMonoOn_aspect": "StrictMonoOn (fun p => nanAligned km k d G f (depolarization p)) (Ioi 0)",
            "nanRandom_sub_matrix": "nanRandom km k11 k33 d1 d3 G f L11 L33 - km =\n        km * f * (2 * nanBeta km (kapitzaCorrected k11 G d1) L11 +",
            "nanAligned_strict_wiener": "1 / ((1 - f) / km + f / kapitzaCorrected k G d) < nanAligned km k d G f L ∧",
        },
    },
    "thermoset-cure-kinetics": {
        "source": "lean/bridge/OMAICureKinetics.lean",
        "contract": "lean/bridge/cure-kinetics-formula-contract.json",
        "module": "OMAICureKinetics",
        "ns": "OMAI.PhyslibBridge.CureKinetics.",
        "definitions": {
            "kamal_cure_conversion": ("kamalCureTime", "def kamalCureTime (T A1 E1 A2 E2 m n NA kB alpha0 alpha : ℝ) : ℝ :=\n  ∫ a in alpha0..alpha, 1 / ((1 - a) ^ n *\n    (A1 * exp (-E1 / (NA * T * kB)) + A2 * a ^ m * exp (-E2 / (NA * T * kB))))"),
            "dibenedetto_glass_transition": ("diBenedetto", "def diBenedetto (alpha Tg0 TgInf lam : ℝ) : ℝ :=\n  Tg0 + alpha * lam * (-Tg0 + TgInf) / (-alpha * (1 - lam) + 1)"),
        },
        "helpers": [],
        "outputs": {"CureConversion", "GlassTransitionTemperature"},
        "key_theorems": {
            "kamal_inverse_exists": "∀ᶠ s in 𝓝 (kamalCureTime T A1 E1 A2 E2 m n NA kB alpha0 alpha),\n        kamalCureTime T A1 E1 A2 E2 m n NA kB alpha0 (g s) = s ∧\n        HasDerivAt g (kamalRate T A1 E1 A2 E2 m n NA kB (g s)) s",
            "kamal_inverse_solves_rate_law": "HasDerivAt g (kamalRate T A1 E1 A2 E2 m n NA kB (g s)) s",
            "diBenedetto_lt_linear": "diBenedetto a Tg0 TgInf lam < Tg0 + a * (TgInf - Tg0)",
        },
    },
}
# Corollaries, substitutions, facts about helpers and catalog-to-catalog identities kept out
# of the citations (some are private helpers or no longer in the source).
NOT_CITED = {
    "OMAI.PhyslibBridge.Composites.tendsto_kapitzaCorrected",
    "OMAI.PhyslibBridge.Composites.nanRandom_sphere_eq_hasselmanJohnson",
    "OMAI.PhyslibBridge.Composites.tendsto_depolarization_sphere",
    "OMAI.PhyslibBridge.Composites.criticalRadius_gt_kapitza",
    "OMAI.PhyslibBridge.Composites.tendsto_criticalRadius",
    "OMAI.PhyslibBridge.Composites.nanAligned_needle",
    "OMAI.PhyslibBridge.Composites.nanAligned_disk",
    "OMAI.PhyslibBridge.CureKinetics.diBenedetto_le_linear",
    "OMAI.PhyslibBridge.CureKinetics.diBenedetto_linear_iff",
}


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
    rows = {row["id"]: row for row in payload["inventory"]["operators"] + payload["inventory"]["nodes"]}
    anchored = {(t["kind"], t["id"]) for b in payload["bindings"] if b["relation"] != "local"
                for t in b["targets"]}
    for op in spec["definitions"]:
        assert ("operator", op) not in anchored
        assert rows[op]["status"] == "local"
        assert "local Lean proof" in rows[op]["reason"]
        assert binding_id in rows[op]["binding_ids"]


def test_conventions_a_user_could_get_wrong_are_stated():
    composites = " ".join(_binding("composite-effective-medium")["conditions"])
    for phrase in ("full particle dimensions", "a_rad is the sphere radius", "d_1 = d_3 = 2 a_rad",
                   "doubles the interface penalty", "temperature drop in the direction of that flux",
                   "Axis 3 is the symmetry axis", "k_f[1,1] is the filler conductivity transverse to axis 3",
                   "isotropic three-dimensional orientation", "monodisperse", "held fixed",
                   "not a mass fraction", "Appl. Phys. Lett. 85, 3549 (2004)"):
        assert phrase in composites, phrase
    assert "halves" not in composites
    obligations = " ".join(_binding("composite-effective-medium")["remaining_obligations"])
    assert "slab approximation" in obligations and "L11 = (1 - L33)/2" in obligations
    cure = " ".join(_binding("thermoset-cure-kinetics")["conditions"])
    for phrase in ("per mole", "R = N_A k_B", "not a percentage", "in kelvin", "before vitrification",
                   "cure path", "pure nth-order kinetics"):
        assert phrase in cure, phrase
    statement = _binding("thermoset-cure-kinetics")["statement"]
    assert "not a global solution" in statement


def test_kamal_admissibility_needs_no_order_sign():
    source = (ROOT / TRANCHES["thermoset-cure-kinetics"]["source"]).read_text()
    assert "start : 0 < A1 ∨ (0 < alpha0 ∧ 0 < A2)" in source
    assert "n_nonneg" not in source and "A2_pos" not in source


def test_compiled_theorems_use_standard_axioms_only():
    package = os.environ.get("PHYSLIB_BRIDGE_PACKAGE")
    if not package:
        pytest.skip("optional real-compiler check: set PHYSLIB_BRIDGE_PACKAGE to the built package")
    package = (ROOT / package).resolve()
    names = [name for binding_id in sorted(TRANCHES)
             for name in _binding(binding_id)["evidence"]["declarations"]]
    probe = ("import OMAICompositeConductivity\nimport OMAICureKinetics\n"
             + "\n".join(f"#print axioms {name}" for name in names) + "\n")
    path = package / ".lake" / "CompositesCureAxioms.lean"
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
