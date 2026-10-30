"""Harmonic lattice-dynamics proofs: Physlib-anchored and local bindings, and the catalog
defects of the phonon transport layer.

Frozen literals are reviewed pins. The compiler probes consume an already-built package
selected with PHYSLIB_BRIDGE_PACKAGE and never write build evidence.
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
from physlib_tranches import TRANCHES

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "lean/bridge"
CONTRACT = BRIDGE / "phonon-structure-formula-contract.json"
NS = "OMAI.PhyslibBridge.Lattice."
LD = "lean/bridge/OMAIPhyslibLatticeDynamics.lean"
DISP = "lean/bridge/OMAIPhyslibPhononDispersion.lean"
GV = "lean/bridge/OMAIPhyslibGroupVelocity.lean"
WIT = "lean/bridge/OMAIPhyslibLatticeWitness.lean"
KC = "lean/bridge/OMAIPhyslibKappaContraction.lean"
RTA = "lean/bridge/OMAIPhyslibRTAConductivity.lean"
PR = "lean/bridge/OMAIPhyslibParticipationRatio.lean"
MODULES = (LD, DISP, GV, WIT, KC, RTA, PR)

# operator -> (Lean definition, defining source, reviewed definition text)
DEFINITIONS = {
    "compute_dynamical_matrix": ("ForceConstants.dynamicalMatrix", LD,
        "fun i j => (∑ R ∈ Φ.shell, ψ R * (Φ.fc R i j : ℂ)) / (Real.sqrt (M i.1 * M j.1) : ℂ)"),
    "compute_dispersion": ("DispersionRelation", LD, "∀ i, ∑ j, D i j * e j = omega2 * e i"),
    "compute_group_velocity": ("catalogGroupVelocity", GV,
        "(∑ j, ∑ i, conj (e i) * dD i j * e j) / (2 * (omega : ℂ))"),
    "contract_kappa[bte_solver=rta]": ("modeContractedKappa", KC,
        "fun α β => (∑ m, F m β * c m * v m α) / (Nq * V)"),
    "compute_participation_ratio": ("participationRatio", PR, "1 / (N * ∑ i, a i ^ 2)"),
}
AUXILIARY_TEXT = {
    LD: ["Complex.exp (((∑ α, q α * pos R α : ℝ) : ℂ) * Complex.I)",
         "Φ.phi ⟨0, i.1⟩ i.2 ⟨R, j.1⟩ j.2"],
    DISP: ["∑ R ∈ Φ.shell with QuotientAddGroup.mk (s := N) R = b.cell - a.cell"],
    KC: ["fun β => v β / (2 * Γ)", "∀ α m, ∑ m', F m' α * Mcol m m' = c m * v m α",
         "Real.sqrt (∑ α, F m α ^ 2)"],
    PR: ["∑ α, ‖e i α‖ ^ 2"],
}
CITED = {
    "crystal-dynamical-matrix": (LD, {"ForceConstants.fc_neg", "ForceConstants.dynamicalMatrix_isHermitian",
                                      "ForceConstants.three_le_finrank_ker_gamma"}),
    "crystal-phonon-dispersion": (DISP, {"ForceConstants.dynamicalMatrix_posSemidef_of_stable",
                                         "ForceConstants.fold_dynamicalMatrix",
                                         "ForceConstants.planeWave_dynamicalMatrix_posSemidef_of_folded_stable"}),
    "crystal-group-velocity": (GV, {"hellmann_feynman", "ForceConstants.catalogGroupVelocity_eq_deriv"}),
    "canonical-rta-thermal-conductivity": (RTA, {"rtaKappa_canonical"}),
    "participation-ratio-bounds": (PR, {"participationRatio_bounds", "participationRatio_eq_one_iff",
                                        "participationRatio_eq_inv_iff"}),
}
SOURCES = {
    "crystal-dynamical-matrix": {"Physlib.CondensedMatter.Crystal", "Physlib.CondensedMatter.Crystal.Site"},
    "crystal-phonon-dispersion": {"Physlib.CondensedMatter.Crystal", "Physlib.CondensedMatter.Crystal.Site",
                                  "Physlib.CondensedMatter.Crystal.siteEquiv"},
    "crystal-group-velocity": {"Physlib.CondensedMatter.Crystal", "Physlib.CondensedMatter.Crystal.Site"},
    "canonical-rta-thermal-conductivity": {"CanonicalEnsemble.heatCapacity",
                                           "QuantumMechanics.OneDimension.HarmonicOscillator"},
    "participation-ratio-bounds": set(),
}
KEY_THEOREMS = {
    LD: {"fc_neg": "Φ.fc (-R) j i = Φ.fc R i j", "three_le_finrank_ker_gamma": "3 ≤ Module.finrank ℂ"},
    DISP: {"fold_dynamicalMatrix": "(Φ.fold N).dynamicalMatrix ψbar M = Φ.dynamicalMatrix ψ M",
           "planeWave_dynamicalMatrix_posSemidef_of_folded_stable":
               "(hq : ∀ L ∈ N, planeWave pos q L = 1)"},
    GV: {"hellmann_feynman": "HasDerivAt lam (star (e t) ⬝ᵥ A'.mulVec (e t)).re t ∧",
         "catalogGroupVelocity_eq_deriv": "v ∧ HasDerivAt (fun s => Real.sqrt (lam s)) v 0"},
    WIT: {"chain_groupVelocity": "((a * Real.sqrt (K / Mass) * Real.cos (q 0 * a / 2) : ℝ) : ℂ)",
          "einstein_stable": "(einstein K).Stable"},
    RTA: {"rtaKappa_canonical": "κ.IsSymm ∧ κ.PosSemidef ∧"},
    KC: {"lbteKappa_posSemidef": "(modeContractedKappa c v F Nq V).PosSemidef",
         "cumulativeKappa_mono": "(hmodal : ∀ m (x : Fin 3 → ℝ), 0 ≤ c m * (v m ⬝ᵥ x) * (F m ⬝ᵥ x))",
         "tp_cumulative_omega_not_monotone":
             "¬ Monotone (fun cut => cumulativeKappa θ tpOmega tpCap tpVelocity (tpF P L) Nq V cut 0 0)",
         "tp_cumulative_mfp_not_monotone": "¬ Monotone (fun cut =>"},
    PR: {"participationRatio_eq_inv_iff":
             "∃ i, atomAmplitude e i = 1 ∧ ∀ j, j ≠ i → atomAmplitude e j = 0"},
}
# Present in the modules, never cited: helpers, Mathlib restatements and results whose
# catalog formulas are defective.
NOT_CITED = {"planeWave_conj", "planeWave_zero", "planeWave_add", "neg_mem_shell",
             "planeWave_dynamicalMatrix_isHermitian", "gamma_translationMode",
             "translationMode_linearIndependent", "fc_eq_zero_of_not_mem_shell", "sum_sites",
             "hermitian_form_of_real_symmetric", "bloch_cell_sum", "bloch_energy", "catalogGroupVelocity_eq",
             "planeWave_line", "hasDerivAt_planeWave_line", "hasDerivAt_dynamicalMatrix", "lbteKappa_eq",
             "lbteKappa_posSemidef", "cumulativeKappa_mono", "cumulativeKappa_not_monotone",
             "rta_modal_nonneg", "rtaKappa_quadratic", "canonicalModeHeatCapacity_pos", "sumSq_bounds",
             "atomAmplitude_nonneg", "tp_cumulative_omega_not_monotone", "tp_cumulative_mfp_not_monotone"}
# Removed after review as restatements of Mathlib's spectral theorem or of PSD-implies-nonneg,
# or replaced by the physical three-mode witness.
REMOVED = ("dispersion_orthonormal_real", "dispersion_eigenvalue_real", "dispersion_real_frequencies_of_stable",
           "cumulativeKappa_saturates", "witnessCollision")
# Formalization exposed these as catalog defects; the formulas are corrected
# (issue 188) and each reason says so, but none carries a theorem.
CATALOG_DEFECTS = {"apply_nac_correction": "Corrected (issue 188)",
                   "solve_bte[bte_solver=direct_inverse]": "Corrected (issue 188)",
                   "contract_kappa[bte_solver=direct_inverse]": "symmetric by construction",
                   "contract_cumulative_kappa[wrt=omega]": "signed partial sum",
                   "contract_cumulative_kappa[wrt=mfp]": "signed partial sum"}
UNBOUND = {"identity_dm", "sum_linewidths", "solve_bte[bte_solver=rta]", *CATALOG_DEFECTS}


def _binding(payload, binding_id):
    return next(b for b in payload["bindings"] if b["id"] == binding_id)


def _tranche():
    return next(t for t in TRANCHES if t["name"] == "phonon")


def test_contract_endpoints_match_the_live_catalog_and_sources():
    contract = json.loads(CONTRACT.read_text())
    assert contract["source_path"] == LD
    assert contract["source_sha256"] == hashlib.sha256((ROOT / LD).read_bytes()).hexdigest()
    inventory = catalog_inventory()
    ops = {row["id"]: row for row in inventory["operators"]}
    nodes = {row["id"]: row for row in inventory["nodes"]}
    assert {row["id"] for row in contract["operators"]} == set(DEFINITIONS)
    for row in contract["operators"]:
        live = ops[row["id"]]
        assert (row["uid"], row["formula_sha256"], row["formula_latex"]) == (
            live["uid"], live["formula_sha256"], live["formula_latex"])
        name, source, _ = DEFINITIONS[row["id"]]
        assert row["lean_definition"] == NS + name
        assert row.get("definition_source_path", contract["source_path"]) == source
    for row in contract["nodes"]:
        assert row["uid"] == nodes[row["id"]]["uid"]


def test_lean_definitions_are_the_reviewed_transcriptions():
    for _, source, text in DEFINITIONS.values():
        assert text in (ROOT / source).read_text(), text
    for source, texts in AUXILIARY_TEXT.items():
        for text in texts:
            assert text in (ROOT / source).read_text(), text
    for source, theorems in KEY_THEOREMS.items():
        body = (ROOT / source).read_text()
        for name, statement in theorems.items():
            assert re.search(r"theorem " + name + r"\b", body), name
            assert statement in body, name
    joined = "\n".join((ROOT / source).read_text() for source in MODULES)
    for name in REMOVED:
        assert not re.search(r"\b" + name + r"\b", joined), name


def test_modules_have_no_escape_hatch_and_local_modules_import_mathlib_only():
    for source in MODULES:
        body = (ROOT / source).read_text()
        for word in ("sorry", "admit", "axiom", "native_decide", "unsafe", "set_option"):
            assert not re.search(r"\b" + word + r"\b", body), (source, word)
    for source in (KC, PR):
        imports = re.findall(r"^public import (\S+)", (ROOT / source).read_text(), re.M)
        assert imports and all(name.startswith("Mathlib.") for name in imports), source


def test_bindings_cite_exactly_the_reviewed_theorems_and_sources():
    payload = _packaged_bindings()
    for binding_id, (source, cited) in CITED.items():
        binding = _binding(payload, binding_id)
        assert binding["evidence"]["kind"] == "compiled_bridge"
        assert binding["evidence"]["source_path"] == source
        assert {n.removeprefix(NS) for n in binding["evidence"]["declarations"]} == cited
        assert not {n.rsplit(".", 1)[1] for n in binding["evidence"]["declarations"]} & NOT_CITED
        assert {s["name"] for s in binding["sources"]} == SOURCES[binding_id]
        assert binding["relation"] == ("local" if not SOURCES[binding_id] else "conditional")
        assert binding["conditions"] and binding["remaining_obligations"]


def test_registry_entry_matches_the_payload():
    payload = _packaged_bindings()
    tranche = _tranche()
    assert tranche["bindings"] == frozenset(CITED)
    subjects = {(t["kind"], t["id"]) for b in tranche["bindings"]
                for t in compiled_targets(_binding(payload, b), payload["inventory"])}
    assert subjects == tranche["subjects"]
    for binding_id in tranche["bindings"]:
        binding = _binding(payload, binding_id)
        assert {(t["kind"], t["id"]) for t in binding["targets"]} == {
            (t["kind"], t["id"]) for t in compiled_targets(binding, payload["inventory"])}
    assert tranche["contracts"] == (CONTRACT.name,)
    contract = json.loads(CONTRACT.read_text())
    pairs = {(NS + DEFINITIONS[row["id"]][0], Path(DEFINITIONS[row["id"]][1]).stem)
             for row in contract["operators"]}
    assert pairs == {(p["name"], p["module"]) for p in tranche["pairs"]}
    assert tranche["modules"] == tuple(Path(m).stem for m in MODULES)
    rows = {(kind, row["id"]): row for kind, key in (("node", "nodes"), ("operator", "operators"))
            for row in payload["inventory"][key]}
    relations = {b["id"]: b["relation"] for b in payload["bindings"]}
    for subject in tranche["subjects"]:
        ids = rows[subject]["binding_ids"]
        expected = "local" if all(relations[i] == "local" for i in ids) else "mapped"
        assert rows[subject]["status"] == expected, subject


def test_corrected_catalog_formulas_stay_gaps_with_their_reasons():
    from omai.map_data import DOMAINS
    op = next(e for d in DOMAINS for e in d.edges if e.name == "apply_nac_correction")
    # The Born-charge contraction sums q_gamma against the field index of Z*.
    assert "Sum(Z^*[i, \\gamma, \\alpha]*q[\\gamma], (\\gamma, 1, 3))" in repr(op.formula)
    payload = _packaged_bindings()
    rows = {row["id"]: row for row in payload["inventory"]["operators"]}
    for op_id in UNBOUND:
        assert rows[op_id]["binding_ids"] == [] and rows[op_id]["status"] == "gap", op_id
    for op_id, marker in CATALOG_DEFECTS.items():
        assert marker in rows[op_id]["reason"], op_id
    assert "Gonze and Lee" in rows["apply_nac_correction"]["reason"]
    assert "C^(1/2) Omega~ C^(1/2)" in rows["solve_bte[bte_solver=direct_inverse]"]["reason"]
    assert "not monotone" in rows["contract_cumulative_kappa[wrt=mfp]"]["reason"]


def test_conventions_a_user_could_get_wrong_are_stated():
    payload = _packaged_bindings()
    for binding_id in ("crystal-dynamical-matrix", "crystal-phonon-dispersion", "crystal-group-velocity"):
        conventions = _binding(payload, binding_id)["conventions"]
        assert "e^{-i q.tau}" in conventions["admissibility"]
        assert "1 Angstrom THz = 100 m/s" in conventions["frequency_convention"]
        assert "OMAI-local" in conventions["model_scope"]
    text = json.dumps(_binding(payload, "crystal-group-velocity"))
    assert "away from Gamma" in text and "Gamma-X" in text
    text = json.dumps(_binding(payload, "crystal-phonon-dispersion"))
    assert "commensurate" in text and "19x19x19" in text
    assert "Im Sigma" in json.dumps(_binding(payload, "canonical-rta-thermal-conductivity"))
    assert "mass-weighted" in json.dumps(_binding(payload, "participation-ratio-bounds"))
    assert "Newton" not in json.dumps([_binding(payload, b) for b in CITED])


def test_roadmap_marks_every_proved_operator():
    roadmap = json.loads((ROOT / "docs/data/lean_roadmap.json").read_text())
    proven = {row["op"] for row in roadmap["rows"] if row["proven"]}
    for kind, name in _tranche()["subjects"]:
        if kind == "operator":
            assert name in proven, name
    for name in UNBOUND:
        assert name not in proven, name


def _probe(package: Path, filename: str, body: str) -> subprocess.CompletedProcess:
    path = package / ".lake" / filename
    path.write_text(body)
    try:
        return subprocess.run(["lake", "--no-build", "env", "lean", str(path)], cwd=package,
                              text=True, capture_output=True, timeout=1800, check=False)
    finally:
        path.unlink()


def _package():
    package = os.environ.get("PHYSLIB_BRIDGE_PACKAGE")
    if not package:
        pytest.skip("optional real-compiler check: set PHYSLIB_BRIDGE_PACKAGE to the built package")
    return (ROOT / package).resolve()


def test_compiled_lattice_theorems_use_standard_axioms_only():
    package = _package()
    payload = _packaged_bindings()
    names = sorted({n for b in CITED for n in _binding(payload, b)["evidence"]["declarations"]}
                   | {"OMAI.PhyslibBridge.LatticeWitness." + n for n in ("chain_groupVelocity", "einstein_stable")}
                   | {NS + n for n in ("lbteKappa_posSemidef", "cumulativeKappa_mono",
                                       "tp_cumulative_omega_not_monotone", "tp_cumulative_mfp_not_monotone")})
    result = _probe(package, "PhononAxioms.lean",
                    "import OMAIPhyslibBridge\n" + "\n".join(f"#print axioms {name}" for name in names) + "\n")
    assert result.returncode == 0, result.stdout + result.stderr
    reported = re.findall(r"'([^']+)' depends on axioms: \[([^\]]*)\]", result.stdout)
    assert {name for name, _ in reported} == set(names)
    for name, axioms in reported:
        assert set(a.strip() for a in axioms.split(",")) <= {"propext", "Classical.choice", "Quot.sound"}, name


def test_every_cited_physlib_declaration_is_used_by_the_cited_theorems():
    """Walk the cited theorems through OMAI declarations only; each cited Physlib source must be
    reached, so no binding cites a Physlib declaration its proof does not use."""
    package = _package()
    payload = _packaged_bindings()
    for binding_id, cited in SOURCES.items():
        if not cited:
            continue
        roots = _binding(payload, binding_id)["evidence"]["declarations"]
        body = "import OMAIPhyslibBridge\nimport Lean\nopen Lean Elab Command\nrun_cmd do\n" + \
            "  let env ← getEnv\n" + \
            "  let roots : List Name := [" + ", ".join(f"`{n}" for n in roots) + "]\n" + \
            "  let cited : List Name := [" + ", ".join(f"`{n}" for n in sorted(cited)) + "]\n" + \
            """  let mut seen : NameSet := {}
  let mut found : NameSet := {}
  let mut todo := roots
  let mut fuel := 200000
  while !todo.isEmpty && fuel > 0 do
    fuel := fuel - 1
    let n := todo.head!
    todo := todo.tail!
    if seen.contains n then continue
    seen := seen.insert n
    if let some ci := env.find? n then
      let used := ci.type.getUsedConstants ++ ((ci.value? (allowOpaque := true)).map (·.getUsedConstants) |>.getD #[])
      for c in used do
        if cited.contains c then found := found.insert c
        if (`OMAI).isPrefixOf c && !seen.contains c then todo := c :: todo
  for c in cited do
    if found.contains c then logInfo m!"OMAI_USED|{c}" else logInfo m!"OMAI_UNUSED|{c}"
"""
        result = _probe(package, "PhononUses.lean", body)
        assert result.returncode == 0, result.stdout + result.stderr
        assert set(re.findall(r"OMAI_USED\|(\S+)", result.stdout)) == cited, (binding_id, result.stdout)
        assert "OMAI_UNUSED" not in result.stdout, (binding_id, result.stdout)
