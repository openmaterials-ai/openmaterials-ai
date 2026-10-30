"""Local analog-device-metrology, Arrhenius and Nernst-Einstein proofs.

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
    "analog-device-metrology": {
        "source": "lean/bridge/OMAIDeviceMetrology.lean",
        "contract": "lean/bridge/device-metrology-formula-contract.json",
        "module": "OMAIDeviceMetrology",
        "ns": "OMAI.PhyslibBridge.DeviceMetrology.",
        "definitions": {
            "apply_conductance_drift": ("driftConductance", "def driftConductance (nu G0 td td0 : ℝ) : ℝ := G0 / (td / td0) ^ nu"),
            "emit_thermionic_conductance": ("thermionicConductance", "def thermionicConductance (PhiBn T Pth qe kB : ℝ) : ℝ :=\n  Pth * T * qe * exp (-PhiBn / (T * kB)) / kB"),
            "zero_bias_retention": ("retentionTime", "def retentionTime (Em T nu0 kB : ℝ) : ℝ := exp (Em / (T * kB)) / nu0"),
            "ramp_set_voltage": ("rampSetVoltage", "def rampSetVoltage (Em T alphaF nu0 gr kB : ℝ) : ℝ :=\n  -(eulerMascheroniConstant * T * kB) / alphaF +\n    (Em - T * kB * log (T * gr * kB * nu0 / alphaF)) / alphaF"),
            "propagate_programming_error": ("programmingError", "def programmingError (cG WG nw wmax S1 S2 : ℝ) : ℝ :=\n  cG * sqrt (S1 * wmax / (WG - 1) + S2 / 2 + nw * wmax ^ 2 / (2 * (WG - 1) ^ 2)) / S1"),
            "dissipate_pulse_energy": ("pulseEnergy", "def pulseEnergy (Gc Vp tp : ℝ) : ℝ := Gc * Vp ^ 2 * tp"),
            "contract_device_conductance": ("deviceConductance", "def deviceConductance (sigma Ag Lg : ℝ) : ℝ := Ag * sigma / Lg"),
        },
        "helpers": [
            "def thermionicCurrent (PhiBn T Pth qe kB V : ℝ) : ℝ :=\n  Pth * T ^ 2 * exp (-PhiBn / (kB * T)) * (exp (qe * V / (kB * T)) - 1)",
            "def hopRate (Em T alphaF nu0 kB V : ℝ) : ℝ := nu0 * exp (-(Em - alphaF * V) / (kB * T))",
            "def rampLocation (Em T alphaF nu0 gr kB : ℝ) : ℝ :=\n  (Em - T * kB * log (T * gr * kB * nu0 / alphaF)) / alphaF",
        ],
        "outputs": {"ConductanceState", "DotProductError", "ProgrammingPulseEnergy", "RetentionTime", "SetVoltage"},
        "key_theorems": {
            "drift_law_unique": "∃ nu : ℝ, ∀ G0 td td0 : ℝ, 0 < td → 0 < td0 →\n      G0 * phi (td / td0) = driftConductance nu G0 td td0",
            "thermionic_wrongLaw_barrier": "PhiBn - kB * (log (T2 / T1) / (1 / T1 - 1 / T2)) / 2 ∧\n    T1 < log (T2 / T1) / (1 / T1 - 1 / T2) ∧ log (T2 / T1) / (1 / T1 - 1 / T2) < T2",
            # The rate equation is a hypothesis for t >= 0 only.
            "retention_symmetric_relaxation":
                "(hp : ∀ s ∈ Ici (0 : ℝ),\n"
                "      HasDerivWithinAt p ((1 - p s) / retentionTime Em T nu0 kB - p s / retentionTime Em T nu0 kB)\n"
                "        (Ici 0) s)\n"
                "    {t : ℝ} (ht : t ∈ Ici (0 : ℝ)) :\n"
                "    p t = 1 / 2 + (p 0 - 1 / 2) * exp (-2 * t / retentionTime Em T nu0 kB)",
            "ramp_meanSetVoltage": "rampSetVoltage Em T alphaF nu0 gr kB",
            "ramp_expectedHops": "gr * kB * T / (alphaF * (exp (Em / (T * kB)) / nu0))",
            "programmingError_gt": "cG / sqrt (2 * n) < programmingError cG WG n wmax (∑ i, |w i|) (∑ i, w i ^ 2)",
            "deviceConductance_series_le": "A / ∑ i, l i / sigma i ≤",
        },
        # Obvious or definitional results kept in the module as support (review of 15370b7).
        "not_cited": {"leadingHops_hasDerivAt", "leadingHops_eq_exp", "driftConductance_rereference",
                      "driftConductance_logSlope", "thermionicConductance_eq_zeroBiasSlope",
                      "thermionicConductance_ideality", "thermionic_barrier_two_temperatures",
                      "retentionTime_mean_exit", "retention_barrier_two_temperatures",
                      "programmingError_eq_cells", "programmingError_strictAntiOn",
                      "tendsto_programmingError"},
    },
    "arrhenius-ionic-transport": {
        "source": "lean/bridge/OMAIMaterialsTransport.lean",
        "contract": "lean/bridge/materials-transport-formula-contract.json",
        "module": "OMAIMaterialsTransport",
        "ns": "OMAI.PhyslibBridge.MaterialsTransport.",
        "definitions": {
            "fit_arrhenius": ("arrheniusDiffusivity", "def arrheniusDiffusivity (D0 Ea kB T : ℝ) : ℝ := D0 * exp (-Ea / (T * kB))"),
            "compute_ionic_conductivity": ("ionicConductivity", "def ionicConductivity (nc D T z ec kB : ℝ) : ℝ := D * ec ^ 2 * nc * z ^ 2 / (T * kB)"),
        },
        "helpers": [],
        "outputs": {"ActivationEnergy", "ElectricalConductivity[carrier=ionic]"},
        "key_theorems": {
            "arrhenius_wls_recovers_activation": "-kB * wlsSlope w (fun i => 1 / T i)\n      (fun i => log (arrheniusDiffusivity D0 Ea kB (T i))) = Ea",
            "wlsSlope_minimizes": "∑ i, w i * (y i - a - b * x i) ^ 2",
            "ionic_wls_apparent_activation": "∃ Teff, Tlo ≤ Teff ∧ Teff ≤ Thi ∧",
        },
        "not_cited": {"wlsSlope_affine", "ionicConductivity_arrhenius", "wlsSlope_log_mem"},
    },
}
NOTHING_TO_PROVE = {"contract_conductance_window", "contract_state_coefficient_of_variation",
                    "contract_diffusivity"}


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
    assert not {name.removeprefix(spec["ns"]) for name in declarations} & spec["not_cited"]


@pytest.mark.parametrize("binding_id", sorted(TRANCHES))
def test_rows_are_local_and_keep_their_physlib_gap_reason(binding_id):
    spec = TRANCHES[binding_id]
    payload = _packaged_bindings()
    rows = {row["id"]: row for row in payload["inventory"]["operators"]}
    for op in spec["definitions"]:
        assert rows[op]["status"] == "local"
        assert "Physlib" in rows[op]["reason"] and "local Lean proof" in rows[op]["reason"]
        assert binding_id in rows[op]["binding_ids"]


def test_plain_definitions_stay_unbound_with_a_reason():
    rows = {row["id"]: row for row in _packaged_bindings()["inventory"]["operators"]}
    for op in NOTHING_TO_PROVE:
        assert rows[op]["status"] == "gap"
        assert "nothing non-obvious to prove" in rows[op]["reason"]
    schottky = rows["schottky_mott_barrier"]
    assert schottky["status"] == "gap"
    assert "cannot be established algebraically" in schottky["reason"] and "Catalog defect" in schottky["reason"]


def test_conventions_a_user_could_get_wrong_are_stated():
    device = " ".join(_binding("analog-device-metrology")["conditions"])
    for phrase in ("in joules", "exponentially wrong", "ideality factor 1", "laterally homogeneous barrier",
                   "ln(G/T) against 1/T", "Werner and Guttler", "single programmed level", "Gaussian nu",
                   "cannot be separated", "time to failure at a fail fraction", "dwell g_r per volt",
                   "not the catalog's RetentionTime", "same two terminals", "gate pulse is not covered",
                   "does not derive that expression from the stochastic cell model",
                   "length-averaged conductivity"):
        assert phrase in device, phrase
    assert "factor 1.6e-19" not in device
    assert "picojoule" in _binding("analog-device-metrology")["conventions"]["unit_embedding"]
    materials = " ".join(_binding("arrhenius-ionic-transport")["conditions"])
    for phrase in ("energy per particle", "at least two distinct temperatures", "Haven ratio H_R = 1",
                   "number of MSD components"):
        assert phrase in materials, phrase
    statement = _binding("arrhenius-ionic-transport")["statement"]
    assert "exact-data identity" in statement and "sigma T, not sigma" in statement


def test_registry_pins_this_tranche():
    from physlib_tranches import TRANCHES as REGISTRY
    entry = next(t for t in REGISTRY if t["name"] == "devices-materials")
    payload = _packaged_bindings()
    assert entry["bindings"] == set(TRANCHES)
    assert set(entry["contracts"]) == {Path(spec["contract"]).name for spec in TRANCHES.values()}
    subjects = {(t["kind"], t["id"]) for binding_id in TRANCHES
                for t in compiled_targets(_binding(binding_id), payload["inventory"])}
    assert entry["subjects"] == subjects
    assert {p["name"] for p in entry["pairs"]} == {
        spec["ns"] + name for spec in TRANCHES.values() for name, _ in spec["definitions"].values()}


def test_compiled_theorems_use_standard_axioms_only():
    package = os.environ.get("PHYSLIB_BRIDGE_PACKAGE")
    if not package:
        pytest.skip("optional real-compiler check: set PHYSLIB_BRIDGE_PACKAGE to the built package")
    package = (ROOT / package).resolve()
    names = [name for binding_id in sorted(TRANCHES)
             for name in _binding(binding_id)["evidence"]["declarations"]]
    probe = ("import OMAIDeviceMetrology\nimport OMAIMaterialsTransport\n"
             + "\n".join(f"#print axioms {name}" for name in names) + "\n")
    path = package / ".lake" / "DevicesMaterialsAxioms.lean"
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
