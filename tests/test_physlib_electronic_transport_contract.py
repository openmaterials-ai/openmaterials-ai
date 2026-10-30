"""Boltzmann electronic transport, carrier statistics and static dielectric proofs.

Frozen literals are reviewed pins. The compiler probe consumes an already-built
package selected with PHYSLIB_BRIDGE_PACKAGE and never writes build evidence.
The global coverage ledger lives in tests/physlib_tranches.py; this file checks
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
THERMOELECTRIC = "Physlib.CondensedMatter.Thermoelectric.Basic"
TRANCHES = {
    "boltzmann-electronic-transport": {
        "source": "lean/bridge/OMAIPhyslibElectronicTransport.lean",
        "contract": "lean/bridge/electronic-transport-formula-contract.json",
        "module": "OMAIPhyslibElectronicTransport",
        "ns": "OMAI.PhyslibBridge.ElectronicTransport.",
        "relation": "conditional",
        "sources": {
            (THERMOELECTRIC, "CondensedMatter.ThermoelectricMaterial", "structure", 102),
            (THERMOELECTRIC, "CondensedMatter.ThermoelectricMaterial.figureOfMerit", "def", 158),
            (THERMOELECTRIC, "CondensedMatter.ThermoelectricMaterial.figureOfMerit_eq", "lemma", 169),
        },
        "imports": [THERMOELECTRIC, "OMAISommerfeldTransport", "Mathlib.Topology.Algebra.Order.Field",
                    "Mathlib.Tactic"],
        "definitions": {
            "compute_electronic_conductivity": ("boltzmannConductivity", "def boltzmannConductivity (w E : ι → ℝ) (mu e : ℝ) : ℝ := e ^ 2 * kinetic w E mu 0"),
            "compute_seebeck": ("boltzmannSeebeck", "def boltzmannSeebeck (w E : ι → ℝ) (mu e T : ℝ) : ℝ :=\n  -(kinetic w E mu 1 / kinetic w E mu 0) / (e * T)"),
            "compute_electronic_thermal_conductivity": ("boltzmannKappaE", "def boltzmannKappaE (w E : ι → ℝ) (mu T : ℝ) : ℝ :=\n  (kinetic w E mu 2 - kinetic w E mu 1 ^ 2 / kinetic w E mu 0) / T"),
        },
        "helpers": ["def kinetic (w E : ι → ℝ) (mu : ℝ) (k : ℕ) : ℝ := ∑ b, w b * (E b - mu) ^ k"],
        "outputs": {"ElectricalConductivity[carrier=electronic]", "SeebeckCoefficient", "ElectronicThermalConductivity"},
        "key_theorems": {
            "boltzmannKappaE_nonneg_and_eq_zero_iff": " {w : ι → ℝ} (hw : ∀ b, 0 ≤ w b) (E : ι → ℝ)\n    (mu : ℝ) {T : ℝ} (hT : 0 < T) :\n    0 ≤ boltzmannKappaE w E mu T ∧\n      (boltzmannKappaE w E mu T = 0 ↔ ∃ E0, ∀ b, w b ≠ 0 → E b = E0)",
            "exists_boltzmann_thermoelectricMaterial": " {w : ι → ℝ} (hw : ∀ b, 0 ≤ w b) (E : ι → ℝ)\n    {mu e T kappaL : ℝ} (hL0 : 0 < kinetic w E mu 0) (he : e ≠ 0) (hT : 0 < T)\n    (hkl : 0 < kappaL) :\n    ∃ M : ThermoelectricMaterial, M.S = boltzmannSeebeck w E mu e T ∧\n      M.σ = boltzmannConductivity w E mu e ∧ M.κl = kappaL ∧ M.κe = boltzmannKappaE w E mu T",
            "figureOfMerit_lt_mahanSofo": " {w : ι → ℝ} (hw : ∀ b, 0 ≤ w b) (E : ι → ℝ)\n    {mu e T : ℝ} (hL0 : 0 < kinetic w E mu 0) (he : e ≠ 0) (hT : 0 < T)\n    (hvar : 0 < kinetic w E mu 0 * kinetic w E mu 2 - kinetic w E mu 1 ^ 2)\n    (hL1 : kinetic w E mu 1 ≠ 0) :\n    (∀ M : ThermoelectricMaterial, M.S = boltzmannSeebeck w E mu e T →\n      M.σ = boltzmannConductivity w E mu e → M.κe = boltzmannKappaE w E mu T →\n        M.figureOfMerit T <\n          kinetic w E mu 1 ^ 2 / (kinetic w E mu 0 * kinetic w E mu 2 - kinetic w E mu 1 ^ 2)) ∧\n      ∀ eps > 0, ∃ M : ThermoelectricMaterial, M.S = boltzmannSeebeck w E mu e T ∧\n        M.σ = boltzmannConductivity w E mu e ∧ M.κe = boltzmannKappaE w E mu T ∧\n        kinetic w E mu 1 ^ 2 / (kinetic w E mu 0 * kinetic w E mu 2 - kinetic w E mu 1 ^ 2) - eps <\n          M.figureOfMerit T",
        },
        # Support lemmas of the Onsager algebra, kept out of the citations.
        "not_cited": {"lagrange", "kinetic_zero_nonneg", "kinetic_two_nonneg", "variance_nonneg",
                      "figureOfMerit_closed"},
        # The continuum moments cited from the imported support module.
        "support_declarations": {
            "OMAI.PhyslibBridge.Sommerfeld.sommerfeld_moments",
            "OMAI.PhyslibBridge.Sommerfeld.wiedemannFranz_constantTransport",
        },
    },
    "electronic-carrier-statistics": {
        "source": "lean/bridge/OMAIElectronicStatistics.lean",
        "contract": "lean/bridge/carrier-statistics-formula-contract.json",
        "module": "OMAIElectronicStatistics",
        "ns": "OMAI.PhyslibBridge.ElectronicStatistics.",
        "relation": "local",
        "sources": set(),
        "imports": None,
        "definitions": {
            "compute_carrier_mobility": ("boltzmannMobility", "def boltzmannMobility (c : ℝ) (w : κ → ℝ) (tau : κ → ι → ℝ) : ℝ :=\n  c * ∑ k, w k * combinedTime (tau k)"),
            "compute_electronic_dos": ("electronicDOS", "def electronicDOS (g E : ι → ℝ) (phi : ℝ → ℝ) : ℝ := ∑ b, g b * phi (E b)"),
        },
        "helpers": [
            "def combinedTime (tau : ι → ℝ) : ℝ := 1 / ∑ i, 1 / tau i",
            "def mechanismMobility (c : ℝ) (w : κ → ℝ) (tau : κ → ι → ℝ) (i : ι) : ℝ :=\n  c * ∑ k, w k * tau k i",
            "def electronCount (g E : ι → ℝ) (kT mu : ℝ) : ℝ := ∑ b, g b / (1 + exp ((E b - mu) / kT))",
        ],
        "outputs": {"CarrierMobility", "ElectronicDOS"},
        "key_theorems": {
            "boltzmannMobility_le_matthiessen": " {c : ℝ} (hc : 0 < c) {w : κ → ℝ} (hw : ∀ k, 0 ≤ w k)\n    {tau : κ → ι → ℝ} (htau : ∀ k i, 0 < tau k i) :\n    boltzmannMobility c w tau ≤ 1 / ∑ i, 1 / mechanismMobility c w tau i",
            "exists_unique_fermiLevel": " [Nonempty ι] {g : ι → ℝ} (hg : ∀ b, 0 < g b) (E : ι → ℝ)\n    {kT : ℝ} (hkT : 0 < kT) {N : ℝ} (hN0 : 0 < N) (hN : N < ∑ b, g b) :\n    ∃! mu, electronicDOS g E (fun e => 1 / (1 + exp ((e - mu) / kT))) = N",
        },
        "not_cited": {"combinedTime_le", "electronCount_eq_dos"},
        "support_declarations": set(),
    },
    "static-dielectric-ionic-response": {
        "source": "lean/bridge/OMAIStaticDielectric.lean",
        "contract": "lean/bridge/static-dielectric-formula-contract.json",
        "module": "OMAIStaticDielectric",
        "ns": "OMAI.PhyslibBridge.StaticDielectric.",
        "relation": "local",
        "sources": set(),
        "imports": None,
        "definitions": {
            "compute_static_dielectric": ("staticDielectric", "def staticDielectric (epsInf : Matrix (Fin 3) (Fin 3) ℝ) (D : Matrix n n ℝ)\n    (Z : Matrix n (Fin 3) ℝ) (c : ℝ) : Matrix (Fin 3) (Fin 3) ℝ :=\n  epsInf + c • (Zᵀ * D⁻¹ * Z)"),
        },
        "helpers": ["(c / (u ⬝ᵥ epsInf *ᵥ u)) • vecMulVec (Z *ᵥ u) (Z *ᵥ u)"],
        "outputs": {"StaticDielectricTensor"},
        "key_theorems": {
            "staticDielectric_sub_posSemidef": " {epsInf : Matrix (Fin 3) (Fin 3) ℝ} {D : Matrix n n ℝ}\n    (hD : D.PosDef) (Z : Matrix n (Fin 3) ℝ) {c : ℝ} (hc : 0 < c) :\n    (staticDielectric epsInf D Z c - epsInf).PosSemidef ∧\n      ∀ u : Fin 3 → ℝ, u ⬝ᵥ (staticDielectric epsInf D Z c - epsInf) *ᵥ u = 0 ↔ Z *ᵥ u = 0",
            "lyddaneSachsTeller": " {epsInf : Matrix (Fin 3) (Fin 3) ℝ} {D : Matrix n n ℝ}\n    (hD : D.PosDef) (Z : Matrix n (Fin 3) ℝ) (c : ℝ) {u : Fin 3 → ℝ}\n    (hu : 0 < u ⬝ᵥ epsInf *ᵥ u) :\n    ∃ hLO : (D + nonAnalytic epsInf Z c u).IsHermitian,\n      (∏ i, hLO.eigenvalues i) / (∏ i, hD.isHermitian.eigenvalues i) =\n        (u ⬝ᵥ staticDielectric epsInf D Z c *ᵥ u) / (u ⬝ᵥ epsInf *ᵥ u)",
        },
        "not_cited": {"row_mul_col", "quad_ionic"},
        "support_declarations": set(),
    },
}
# The Fermi-window moments: a Mathlib-only support module without a catalog endpoint.
SOMMERFELD = {
    "source": "lean/bridge/OMAISommerfeldTransport.lean",
    "definitions": [
        "def fermiWindow (x : ℝ) : ℝ := exp x / (1 + exp x) ^ 2",
        "def kineticIntegral (Sigma0 mu kT : ℝ) (k : ℕ) : ℝ :=\n  ∫ E, Sigma0 * (E - mu) ^ k * (fermiWindow ((E - mu) / kT) / kT)",
    ],
    "key_theorems": {
        "sommerfeld_moments": " (Sigma0 mu : ℝ) {kT : ℝ} (hkT : 0 < kT) :\n    kineticIntegral Sigma0 mu kT 0 = Sigma0 ∧ kineticIntegral Sigma0 mu kT 1 = 0 ∧\n      kineticIntegral Sigma0 mu kT 2 = Sigma0 * kT ^ 2 * (π ^ 2 / 3)",
        "wiedemannFranz_constantTransport": " {Sigma0 e kB T : ℝ} (mu : ℝ) (he : e ≠ 0)\n    (hkB : 0 < kB) (hT : 0 < T) :\n    -(kineticIntegral Sigma0 mu (kB * T) 1 / kineticIntegral Sigma0 mu (kB * T) 0) / (e * T) = 0 ∧\n      (kineticIntegral Sigma0 mu (kB * T) 2 -\n          kineticIntegral Sigma0 mu (kB * T) 1 ^ 2 / kineticIntegral Sigma0 mu (kB * T) 0) / T =\n        π ^ 2 / 3 * (kB / e) ^ 2 * (e ^ 2 * kineticIntegral Sigma0 mu (kB * T) 0) * T",
    },
    "not_cited": {"fermiWindow_neg", "integral_fermiWindow", "integral_mul_fermiWindow",
                  "integral_sq_mul_fermiWindow", "kineticIntegral_eq"},
}
UNBOUND_DEFECT = "apply_nac_correction"


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
        assert "theorem " + name + statement + " :=" in source, name
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


def test_sommerfeld_support_module_is_cited_without_a_contract():
    source = (ROOT / SOMMERFELD["source"]).read_text()
    assert all(name.startswith("Mathlib.") for name in _imports(source))
    for text in SOMMERFELD["definitions"]:
        assert text in source, text
    for name, statement in SOMMERFELD["key_theorems"].items():
        assert re.search(r"theorem " + name + r"\b", source), name
        assert "theorem " + name + statement + " :=" in source, name
    for word in ("sorry", "admit", "axiom", "native_decide", "unsafe", "set_option"):
        assert not re.search(r"\b" + word + r"\b", source), word
    contracts = {path.name for path in (ROOT / "lean/bridge").glob("*-formula-contract.json")}
    assert not any("sommerfeld" in name for name in contracts)
    for contract in (ROOT / "lean/bridge").glob("*-formula-contract.json"):
        assert "OMAISommerfeldTransport" not in json.loads(contract.read_text())["source_path"]
    declarations = set(_binding("boltzmann-electronic-transport")["evidence"]["declarations"])
    assert TRANCHES["boltzmann-electronic-transport"]["support_declarations"] <= declarations
    assert not {"OMAI.PhyslibBridge.Sommerfeld." + name for name in SOMMERFELD["not_cited"]} & declarations


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
    declarations = set(binding["evidence"]["declarations"])
    own = {name for name in declarations if name.startswith(spec["ns"])}
    assert own and declarations == own | spec["support_declarations"]
    assert not {name.removeprefix(spec["ns"]) for name in own} & spec["not_cited"]
    assert set(spec["key_theorems"]) <= {name.removeprefix(spec["ns"]) for name in own}


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


def test_opaque_producers_are_marked_interpreted_in_the_roadmap():
    roadmap = json.loads((ROOT / "docs/data/lean_roadmap.json").read_text())
    rows = {row["op"]: row for row in roadmap["rows"]}
    for spec in TRANCHES.values():
        for op in spec["definitions"]:
            assert rows[op]["proven"], op
            assert rows[op]["difficulty"] == "na" and "interpreted definition" in rows[op]["reason"], op
    assert not rows[UNBOUND_DEFECT]["proven"]


def test_non_analytic_correction_stays_an_unbound_gap():
    rows = {row["id"]: row for row in _packaged_bindings()["inventory"]["operators"]}
    row = rows[UNBOUND_DEFECT]
    assert row["status"] == "gap" and row["binding_ids"] == []
    assert row["reason"].startswith("Corrected (issue 188)")
    dielectric = json.dumps(_binding("static-dielectric-ionic-response"))
    assert "apply_nac_correction" in dielectric and "Gonze-Lee" in dielectric


def test_conventions_a_user_could_get_wrong_are_stated():
    transport = _binding("boltzmann-electronic-transport")
    text = " ".join(transport["conditions"])
    for phrase in ("opaque Boltzmann-transport outputs", "w_b = Sigma(E_b) (-df/dE)(E_b) Delta E >= 0",
                   "one diagonal Cartesian component", "e > 0 is the elementary charge", "q = -e",
                   "zero-current electronic thermal conductivity", "Peltier correction",
                   "kappa_e >= 0 is proved, not assumed", "L_0 L_2 - L_1^2 > 0", "sharp as kappa_l -> 0",
                   "not about the finite-grid definitions", "2.44e-8 W Ohm/K^2"):
        assert phrase in text, phrase
    assert "Mahan-Sofo" in transport["statement"] and "Sommerfeld Lorenz number" in transport["statement"]
    statistics = " ".join(_binding("electronic-carrier-statistics")["conditions"])
    for phrase in ("separate_mobility", "equality is not claimed", "spin times k-point weight",
                   "0 < N < sum_b g_b", "uniqueness fails there", "1 cm^2/(V s) = 1e-4 m^2/(V s)"):
        assert phrase in statistics, phrase
    dielectric = " ".join(_binding("static-dielectric-ionic-response")["conditions"])
    for phrase in ("frequencies and eigenvectors the catalog lists as inputs", "3N - 3 optical coordinates",
                   "sum_kappa Z*_kappa = 0", "e^2/(eps_0 Omega)", "not individual LO-TO pairs",
                   "no imaginary Gamma mode"):
        assert phrase in dielectric, phrase


def test_registry_pins_this_tranche():
    from physlib_tranches import TRANCHES as REGISTRY
    entry = next(t for t in REGISTRY if t["name"] == "electronic-transport")
    payload = _packaged_bindings()
    assert entry["bindings"] == set(TRANCHES)
    assert set(entry["contracts"]) == {Path(spec["contract"]).name for spec in TRANCHES.values()}
    subjects = {(t["kind"], t["id"]) for binding_id in TRANCHES
                for t in compiled_targets(_binding(binding_id), payload["inventory"])}
    assert entry["subjects"] == subjects
    assert {p["name"] for p in entry["pairs"]} == {
        spec["ns"] + name for spec in TRANCHES.values() for name, _ in spec["definitions"].values()}
    assert entry["modules"] == ("OMAISommerfeldTransport", "OMAIPhyslibElectronicTransport",
                                "OMAIElectronicStatistics", "OMAIStaticDielectric")


def test_compiled_theorems_use_standard_axioms_only():
    package = os.environ.get("PHYSLIB_BRIDGE_PACKAGE")
    if not package:
        pytest.skip("optional real-compiler check: set PHYSLIB_BRIDGE_PACKAGE to the built package")
    package = (ROOT / package).resolve()
    names = [name for binding_id in sorted(TRANCHES)
             for name in _binding(binding_id)["evidence"]["declarations"]]
    probe = ("import OMAISommerfeldTransport\nimport OMAIPhyslibElectronicTransport\n"
             "import OMAIElectronicStatistics\nimport OMAIStaticDielectric\n"
             + "\n".join(f"#print axioms {name}" for name in names) + "\n")
    path = package / ".lake" / "ElectronicTransportAxioms.lean"
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
