"""Quasiharmonic integration, scope, provenance and anti-circularity regressions.

Frozen literals are reviewed pins, not regenerated expectations. Integration tests fail, never
skip, while the reviewed QHA artifacts are absent. Compiler probes consume an already-built
package selected with PHYSLIB_BRIDGE_PACKAGE and never run the canonical audit or its writer.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import tomllib
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest

from omai.formula_bindings import (
    _check_compiled_evidence,
    build_formula_bindings,
    catalog_inventory,
    compiled_targets,
    formula_bindings_for,
    formula_bindings_for_physlib,
    validate_formula_bindings,
)

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "lean/bridge"
REVISION = "9b583cb6ef6e9cc537c4d4b786b508de1abbcf42"
PREVIOUS_REVISIONS = ("8ddcc004043c5b537e4225fa763121c176b62a4a", "d70acc20677320d37b38e602e331e900466b704d")
TOOLCHAIN = "leanprover/lean4:v4.35.0"
NS = "OMAI.PhyslibBridge.Response."

CONTRACT_NAME = "qha-formula-contract.json"
SUPPORT_MODULE = "OMAIPhyslibGibbsBranch"
MODULE = "OMAIPhyslibQHA"
WITNESS_MODULE = "OMAIPhyslibQHAWitness"
SUPPORT_SOURCE = "lean/bridge/OMAIPhyslibGibbsBranch.lean"
SOURCE = "lean/bridge/OMAIPhyslibQHA.lean"
WITNESS_SOURCE = "lean/bridge/OMAIPhyslibQHAWitness.lean"
NEW_SOURCES = frozenset({SUPPORT_SOURCE, SOURCE, WITNESS_SOURCE})

# Earlier tranches, unchanged by this one.
EARLIER_CONTRACTS = frozenset({
    "semantic-formula-contract.json", "continuum-formula-contract.json",
    "harmonic-ensemble-formula-contract.json", "harmonic-sums-formula-contract.json",
    "harmonic-product-formula-contract.json", "harmonic-density-formula-contract.json",
    "joint-density-formula-contract.json", "response-formula-contract.json",
    "thermal-gruneisen-formula-contract.json",
})
REQUIRED_CONTRACTS = EARLIER_CONTRACTS | {CONTRACT_NAME}
EARLIER_PRESERVED = {
    "lean/bridge/OMAIPhyslibResponseCalculus.lean": "aaa0404cc1d8df8b0a437bb24c46fdb97269def69b6f6caece73947dd4ac7b12",
    "lean/bridge/OMAIPhyslibHarmonicVolume.lean": "23effa45ca48c083307f32391413ab30d819db78cbee14bf6c9e62fdacb9dca5",
    "lean/bridge/OMAIPhyslibHarmonicResponse.lean": "1914f2a738ae2ffaa4b35cfce04dc3a880f2d67cbf89a4ff47c7f15ec8a5f9b0",
    "lean/bridge/OMAIPhyslibThermalGruneisen.lean": "6669b924a8682f135cee4daeda9d2d76b5418aa1ee30117dd7975dc86dddece9",
    "lean/bridge/response-formula-contract.json": "f4f446f1967c45ccf508f42232e070d468121b0967459f93fc0c496210adf353",
}
EARLIER_BINDINGS = frozenset([
    "absolute-temperature", "abstract-crystal-structure", "classical-harmonic-frequency",
    "classical-harmonic-potential-force", "continuum-stress-sign", "harmonic-joint-molar-ensemble",
    "harmonic-joint-volumetric-heat-capacity", "harmonic-mode-entropy", "harmonic-mode-free-energy",
    "harmonic-mode-heat-capacity", "harmonic-mode-internal-energy", "harmonic-molar-entropy",
    "harmonic-molar-free-energy", "harmonic-molar-heat-capacity", "harmonic-molar-internal-energy",
    "harmonic-static-cp-identity", "harmonic-static-thermal-gruneisen-identity",
    "harmonic-volumetric-heat-capacity", "thermodynamic-pressure", "thermoelectric-figure-of-merit",
    "thermoelectric-input-coefficients", "thermoelectric-power-factor", "thermoelectric-total-conductivity",
])
EARLIER_OPERATORS = frozenset({
    "compute_entropy", "compute_free_energy", "compute_heat_capacity", "compute_internal_energy",
    "contract_molar_entropy", "contract_molar_free_energy", "contract_molar_heat_capacity",
    "contract_molar_internal_energy", "contract_power_factor", "contract_pressure",
    "contract_volumetric_heat_capacity", "contract_zt", "sum_thermal_conductivity",
    "contract_heat_capacity_p_identity", "contract_thermal_gruneisen_identity",
})
EARLIER_NODES = frozenset({
    "Entropy", "HeatCapacity", "HelmholtzFreeEnergy", "InternalEnergy", "MolarEntropy",
    "MolarHeatCapacity", "MolarHelmholtzFreeEnergy", "MolarInternalEnergy", "PowerFactor", "Pressure",
    "Temperature", "ThermalConductivity[contribution=total]", "VolumetricHeatCapacity", "ZT",
    "HeatCapacityConstantP", "ThermalGruneisen",
})
EARLIER_SUBJECTS = ({("operator", name) for name in EARLIER_OPERATORS}
                    | {("node", name) for name in EARLIER_NODES})
EARLIER_PAIR_COUNT = 15

# Frozen QHA tranche.
LINK = "OMAI.PhyslibBridge.HarmonicVolumeModel.freeEnergy_eq_actual"
OPERATORS = {
    "compute_qha_gibbs": {
        "uid": "2dfd344c598d659dbc5e4c8def4cefcb69b1a0bd215a9202f981618b18611b89",
        "formula_sha256": "8264d933a1f5cf6dab090041c2a1e6367cd92e5de6022aaa8e7dbbbe20ed840e",
        "latex": r"G_{qha} = G^{qha}{\left(E_{tot},\mathcal{S},\omega \right)}",
        "inputs": ["TotalEnergy", "Structure", "Frequency"], "output": "QHAGibbsEnergy",
        "definition": NS + "qhaGibbsEnergy", "binding": "harmonic-qha-gibbs-energy",
        "declarations": ["harmonic_static_qhaGibbs_convex_window", "harmonic_static_qhaGibbs_entropy",
                         "harmonic_static_qhaGibbs_volume"],
        "associations": [], "subject_output": True,
        "sources": ["CanonicalEnsemble.helmholtzFreeEnergy", "CanonicalEnsemble.thermodynamicEntropy"],
    },
    "compute_heat_capacity_p": {
        "uid": "36100a86ef25aada0acd615151092323ba680b4a9791bb58d1175adcea96deb2",
        "formula_sha256": "94c543b5191d7fa6737a2f2fcca9cc68bc4cc38530abd5c2d31b25b091bc4ccf",
        "latex": r"C_{P} = C_P^{qha}{\left(G_{qha} \right)}",
        "inputs": ["QHAGibbsEnergy"], "output": "HeatCapacityConstantP",
        "definition": NS + "qhaHeatCapacityP", "binding": "harmonic-qha-heat-capacity-p",
        "declarations": ["harmonic_static_qhaHeatCapacityP_eq_omai",
                         "harmonic_static_qhaHeatCapacityP_eq_entropy_slope",
                         "harmonic_static_qhaHeatCapacityP_gt_iff"],
        "associations": ["QHAGibbsEnergy"], "subject_output": True,
        "sources": ["CanonicalEnsemble.helmholtzFreeEnergy", "CanonicalEnsemble.meanEnergyT",
                    "CanonicalEnsemble.heatCapacity"],
    },
    "compute_thermal_expansion": {
        "uid": "4e11a6ef1474661ab6ea320a5c99e8774edbe32b5a4dcdb13d97fda4b108995e",
        "formula_sha256": "7a5492ca3cc69da193307f5f74b36985627e5b4ab5c97bc2851120f491553f93",
        "latex": r"\alpha_{V} = \alpha^{qha}{\left(G_{qha} \right)}",
        "inputs": ["QHAGibbsEnergy"], "output": "ThermalExpansion",
        "definition": NS + "qhaThermalExpansion", "binding": "harmonic-qha-thermal-expansion",
        "declarations": ["harmonic_static_qhaThermalExpansion_eq_omai",
                         "harmonic_static_qhaThermalExpansion_pos_iff", LINK],
        "associations": ["QHAGibbsEnergy"], "subject_output": True,
        "sources": ["CanonicalEnsemble.helmholtzFreeEnergy", "CanonicalEnsemble.heatCapacity"],
    },
    "compute_bulk_modulus_qha": {
        "uid": "de67212047d6c2bb08a94d9394adffe1b1cc183b7a1811d838de2dcfb9323235",
        "formula_sha256": "bedbb8f82d002302668176dcdb9aa7abcbbe648e5963121237de436c725b2e7b",
        "latex": r"K = K^{qha}{\left(E_{tot},\mathcal{S},\omega \right)}",
        "inputs": ["TotalEnergy", "Structure", "Frequency"], "output": "BulkModulus",
        "definition": NS + "qhaBulkModulus", "binding": "harmonic-qha-bulk-modulus",
        "declarations": ["harmonic_static_qhaBulkModulus_eq_omai", LINK],
        # BulkModulus is the Voigt average of the elastic tensor: an output association only.
        "associations": [], "subject_output": False,
        "sources": ["CanonicalEnsemble.helmholtzFreeEnergy"],
    },
    "contract_thermal_gruneisen": {
        "uid": "aa554ec7f8a638108f1039bffd5f1c727687f5fd0d018d61d2916e745a5f6f29",
        "formula_sha256": "01d5dfc469084551b1508829d6a3c4d7f55bccf19207530724fb1f9a56137f26",
        "latex": r"\gamma_{th} = \gamma^{qha}{\left(\gamma_{G},\omega \right)}",
        "inputs": ["Gruneisen", "Frequency"], "output": "ThermalGruneisen",
        "definition": NS + "qhaThermalGruneisen", "binding": "harmonic-qha-thermal-gruneisen-contraction",
        "declarations": ["harmonic_static_qhaThermalGruneisen_eq_omai"],
        "associations": [], "subject_output": True,
        "sources": ["CanonicalEnsemble.heatCapacity",
                    "QuantumMechanics.OneDimension.HarmonicOscillator.eigenValue",
                    "CanonicalEnsemble.helmholtzFreeEnergy"],
    },
}
NODE_UIDS = {
    "QHAGibbsEnergy": "bb10912780eb22d45beff551be14f7f4216f3aae26161e8bfd60cdc051f63f58",
    "HeatCapacityConstantP": "08057e4554a3420c933329b3821de9295e2b5950191e23cafe310b0a15adc7b6",
    "ThermalExpansion": "9b42f8aebb6099cdcd910a272a92208881b598688bac7830c3ae0a412152473e",
    "ThermalGruneisen": "22b1bd519d50d93fd24a919e021bab85aff246464a66a08f8274558834983985",
}
BULK_MODULUS_UID = "c0a13e64c02811f49b951271c894373267937676e0c657fc9ef09fac72558ced"
BINDING_IDS = frozenset(row["binding"] for row in OPERATORS.values())
SUBJECTS = ({("operator", name) for name in OPERATORS}
            | {("node", row["output"]) for row in OPERATORS.values() if row["subject_output"]})
PAIRS = sorted([{"name": row["definition"], "module": MODULE} for row in OPERATORS.values()],
               key=lambda row: (row["name"], row["module"]))
WITNESS_THEOREMS = frozenset("OMAI.PhyslibBridge.QHAWitness." + name for name in (
    "rate_gibbsBranch", "rate_window", "positive_qha_witness", "negative_qha_witness",
    "zero_qha_control", "positive_qha_witness_nonunit",
))
SUPPORT_THEOREMS = frozenset(NS + name for name in (
    "exists_gibbsBranchAt", "strictMin_of_convex_interval", "GibbsBranchAt.window_strictMin",
    "GibbsBranchAt.gibbs_temperature_hasDerivAt", "GibbsBranchAt.gibbs_pressure_hasDerivAt",
    "GibbsBranchAt.isotherm_hasDerivAt",
))
# Proved but deliberately not cited: a small-window corollary, a positive-weight mean between its
# bounds, and definitional unfoldings.
NOT_CITED = frozenset(NS + name for name in (
    "harmonic_static_qhaGibbs_window", "qhaThermalGruneisen_mem_Icc",
    "GibbsBranchAt.qhaBulkModulus_eq_bulk", "qhaThermalGruneisen_eq_weightedGruneisen",
))


def _full(name):
    return name if name.startswith("OMAI.") else NS + name


FINAL_THEOREMS = frozenset(_full(name) for row in OPERATORS.values() for name in row["declarations"])
EXPECTED_COVERAGE = {
    "nodes_total": 129,
    "operators_total": 127,
    "operators_compiled": 20,
    "operators_mapped": 20,
    "nodes_compiled": 18,
    "nodes_compiled_outputs": 17,
    "nodes_compiled_interpretations": 1,
    "nodes_mapped": 30,
    "bindings_total": 28,
    "compiled_bridges": 23,
    "source_correspondences": 5,
    "upstream_declarations_referenced": 33,
    "upstream_modules_referenced": 9,
    "relations": {"exact_definition": 1, "conditional": 23, "conceptual": 4},
}
# The producer definitions must not read the response quantities they are proved equal to.
FORBIDDEN_EXACT = frozenset({
    *(NS + name for name in (
        "FT", "FV", "FTT", "FVV", "mixedTV", "internalEnergy", "cv", "bulk", "expansion", "cp",
        "StableBranchAt", "GibbsBranchAt", "GibbsBranchAt.gibbs", "GibbsBranchAt.isobar",
        "thermalGruneisenIdentity", "heatCapacityPIdentity")),
    *("OMAI.PhyslibBridge.HarmonicVolumeModel." + name for name in (
        "freeEnergy", "cellFreeEnergy", "internalEnergy", "entropy", "cv", "actualMolarInternalEnergy",
        "actualCp", "modeGruneisen", "modeHeatCapacity", "weightedGruneisen")),
})
ROOTS = tuple(row["definition"] for row in OPERATORS.values())
ALLOWED_OMAI_CLOSURE = frozenset({
    NS + "Surface", NS + "qhaGibbsEnergy", NS + "gibbsVolume", NS + "qhaHeatCapacityP",
    NS + "qhaThermalExpansion", NS + "qhaBulkModulus", NS + "qhaThermalGruneisen",
    "OMAI.PhyslibBridge.harmonicEnsemble",
})
FORBIDDEN_TEXT = re.compile(r"MUST agree|law_|gruneisen_temperature[^.]*(?:produces|computes)[^.]*weighted",
                            re.IGNORECASE)
_IMPORT = re.compile(r"^\s*(?:public\s+)?(?:meta\s+)?import\s+(?:all\s+)?(\S+)", re.MULTILINE)
BACKTICK = chr(96)


def _load_json(path):
    return json.loads(Path(path).read_text())


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, PACKAGE / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _subjects(payload):
    return {(target["kind"], target["id"]) for binding in payload["bindings"]
            for target in compiled_targets(binding, payload["inventory"])}


def _binding(payload, binding_id):
    rows = [row for row in payload["bindings"] if row["id"] == binding_id]
    assert len(rows) == 1, f"integration pending: expected exactly one reviewed {binding_id} binding"
    return rows[0]


def _lean_imports(path):
    return _IMPORT.findall(Path(path).read_text())


@pytest.fixture(scope="module")
def payload():
    built = build_formula_bindings()
    for binding_id in BINDING_IDS:
        _binding(built, binding_id)
    return built


@pytest.fixture(scope="module")
def contract():
    path = PACKAGE / CONTRACT_NAME
    assert path.is_file(), "integration pending: reviewed QHA contract is absent"
    return _load_json(path)


def test_qha_unit_catalog_pins():
    inventory = catalog_inventory()
    operators = {row["id"]: row for row in inventory["operators"]}
    nodes = {row["id"]: row for row in inventory["nodes"]}
    for name, row in OPERATORS.items():
        live = operators[name]
        assert (live["uid"], live["formula_sha256"]) == (row["uid"], row["formula_sha256"]), name
        assert live["formula_latex"] == row["latex"], name
        assert live["inputs"] == row["inputs"] and live["outputs"] == [row["output"]], name
        assert live["domain"] == "quasiharmonic", name
    assert {name: nodes[name]["uid"] for name in NODE_UIDS} == NODE_UIDS
    assert nodes["BulkModulus"]["uid"] == BULK_MODULUS_UID


@pytest.mark.parametrize("relative,digest", sorted(EARLIER_PRESERVED.items()))
def test_qha_unit_earlier_bytes_preserved(relative, digest):
    assert _digest(ROOT / relative) == digest


def test_qha_integration_contract_is_exact(contract):
    assert set(contract) == {"schema_version", "scope", "source_path", "source_sha256", "operators", "nodes",
                             "interpretations"}
    assert contract["schema_version"] == 1
    assert contract["source_path"] == SOURCE
    assert contract["source_sha256"] == _digest(ROOT / SOURCE)
    assert [(row["id"], row["uid"], row["formula_sha256"], row["formula_latex"], row["lean_definition"])
            for row in contract["operators"]] == [
        (name, row["uid"], row["formula_sha256"], row["latex"], row["definition"])
        for name, row in OPERATORS.items()]
    assert contract["nodes"] == [{"id": name, "uid": uid} for name, uid in NODE_UIDS.items()]
    prose = [contract["scope"], *contract["interpretations"]]
    assert all(text and text.isascii() for text in prose)
    assert not any(FORBIDDEN_TEXT.search(text) for text in prose)


@pytest.mark.parametrize("operator", sorted(OPERATORS))
def test_qha_integration_binding_scope_and_evidence(payload, operator):
    row = OPERATORS[operator]
    binding = _binding(payload, row["binding"])
    assert binding["relation"] == "conditional"
    expected_targets = sorted(
        [("operator", operator), ("node", row["output"]), *(("node", name) for name in row["associations"])],
        key=lambda target: (target[0], target[1]))
    subjects = [("operator", operator)] + ([("node", row["output"])] if row["subject_output"] else [])
    assert [(target["kind"], target["id"]) for target in binding["targets"]] == expected_targets
    evidence = binding["evidence"]
    assert evidence["kind"] == "compiled_bridge"
    assert evidence["module"] == MODULE and evidence["source_path"] == SOURCE
    assert evidence["source_sha256"] == _digest(ROOT / SOURCE)
    assert evidence["build_record"] == "lean/bridge/build-evidence.json"
    assert evidence["declarations"] == [_full(name) for name in row["declarations"]]
    assert [(target["kind"], target["id"]) for target in evidence["proved_targets"]] == subjects
    assert not (WITNESS_THEOREMS | SUPPORT_THEOREMS | NOT_CITED) & set(evidence["declarations"])
    assert [source["name"] for source in binding["sources"]] == row["sources"]
    texts = [binding["statement"], *binding["conditions"], *binding["conventions"].values(),
             *binding["remaining_obligations"]]
    assert all(text and text.isascii() for text in texts)
    assert not any(FORBIDDEN_TEXT.search(text) for text in texts)
    assert any("not verified" in text for text in binding["remaining_obligations"])
    assert any("window" in text for text in binding["conditions"])


def test_qha_integration_global_ledger(payload):
    assert {row["id"] for row in payload["bindings"]} == EARLIER_BINDINGS | BINDING_IDS
    assert _subjects(payload) == EARLIER_SUBJECTS | SUBJECTS
    assert {key: payload["coverage"][key] for key in EXPECTED_COVERAGE} == EXPECTED_COVERAGE


def test_qha_integration_text_obligations(payload):
    contraction = _binding(payload, OPERATORS["contract_thermal_gruneisen"]["binding"])
    obligations = "\n".join(contraction["remaining_obligations"])
    for phrase in ("Maradudin-Fein", "compute_gruneisen", "gruneisen_temperature"):
        assert phrase in obligations, phrase
    assert "corollary" in contraction["statement"]
    modulus = _binding(payload, OPERATORS["compute_bulk_modulus_qha"]["binding"])
    assert any("adiabatic modulus" in text for text in modulus["conditions"])
    assert any("Voigt average" in text and "not a proof subject" in text for text in modulus["conditions"])
    assert "stability premise" in modulus["statement"] and "is positive" not in modulus["statement"]
    capacity = _binding(payload, OPERATORS["compute_heat_capacity_p"]["binding"])
    obligations = "\n".join(capacity["remaining_obligations"])
    for phrase in ("contract_heat_capacity_p_identity", "polyfit_enthalpy_derivative", "heat_capacity_P_polyfit",
                   "heat_capacity_P_numerical"):
        assert phrase in obligations, phrase
    assert "(dS/dV)_T=-F_TV=alpha_V*K_T" in capacity["statement"]
    gibbs = _binding(payload, OPERATORS["compute_qha_gibbs"]["binding"])
    assert "-(N_A/N_q) times the Physlib thermodynamic entropy" in gibbs["statement"]
    for binding_id in BINDING_IDS:
        binding = _binding(payload, binding_id)
        conditions = "\n".join(binding["conditions"])
        assert "certifies itself" in conditions and "strictly inside the scanned range" in conditions
        assert "6.02214076e23" in binding["conventions"]["normalization_basis"]
        assert "1.054571817e-34" in binding["conventions"]["frequency_convention"]
        obligations = "\n".join(binding["remaining_obligations"])
        for phrase in ("imaginary mode at every scanned volume", "shifted mesh", "Born charges",
                       "same cell", "physically unreliable"):
            assert phrase in obligations, (binding_id, phrase)


@pytest.mark.parametrize("operator", ["compute_gruneisen", "contract_molar_volume"])
def test_qha_integration_sibling_gaps(payload, operator):
    assert formula_bindings_for(operator, kind="operator") == []


def test_qha_integration_exact_lookups(payload):
    assert formula_bindings_for("Gruneisen", kind="node") == []
    assert formula_bindings_for("TotalEnergy", kind="node") == []
    for name, row in OPERATORS.items():
        assert [binding["id"] for binding in formula_bindings_for(name, kind="operator")] == [row["binding"]]
    assert sorted(binding["id"] for binding in formula_bindings_for("ThermalGruneisen", kind="node")) == [
        "harmonic-qha-thermal-gruneisen-contraction", "harmonic-static-thermal-gruneisen-identity"]
    assert sorted(binding["id"] for binding in formula_bindings_for("QHAGibbsEnergy", kind="node")) == [
        "harmonic-qha-gibbs-energy", "harmonic-qha-heat-capacity-p", "harmonic-qha-thermal-expansion"]
    bulk = [binding for binding in formula_bindings_for("BulkModulus", kind="node")
            if binding["id"] == "harmonic-qha-bulk-modulus"]
    assert len(bulk) == 1 and ("node", "BulkModulus") not in _subjects({"bindings": bulk,
                                                                          "inventory": payload["inventory"]})
    for binding_id in BINDING_IDS:
        binding = _binding(payload, binding_id)
        for source in binding["sources"]:
            rows = formula_bindings_for_physlib(declaration=source["name"], module=source["module"])
            assert binding in rows


def test_qha_integration_reproducible(payload):
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    assert (ROOT / "omai/data/formula_bindings.json").read_text() == text
    assert (ROOT / "docs/data/formula_bindings.json").read_text() == text
    assert build_formula_bindings() == payload


def test_qha_integration_record_covers_sources(payload, contract):
    validate_formula_bindings(payload, check_catalog=True, proof_root=ROOT)
    record = _load_json(PACKAGE / "build-evidence.json")
    assert record["upstream_revision"] == payload["upstream"]["revision"] == REVISION
    assert record["lean_toolchain"] == TOOLCHAIN
    tracked = NEW_SOURCES | {"lean/bridge/" + CONTRACT_NAME}
    assert {path: record["sources"][path] for path in tracked} == {path: _digest(ROOT / path) for path in tracked}
    assert {"lean/bridge/" + name for name in REQUIRED_CONTRACTS} <= record["sources"].keys()
    audit = record["contract_name_audit"]
    assert audit["status"] == "passed" and audit["pair_count"] == EARLIER_PAIR_COUNT + len(PAIRS)
    assert all(pair in audit["pairs"] for pair in PAIRS)
    axioms = record["axiom_audit"]
    assert {SUPPORT_MODULE, MODULE, WITNESS_MODULE} <= set(axioms["source_modules"])
    declarations = axioms["declarations"]
    for name in sorted(FINAL_THEOREMS | WITNESS_THEOREMS | SUPPORT_THEOREMS | NOT_CITED):
        assert name in declarations, name
        assert set(declarations[name]) <= {"propext", "Classical.choice", "Quot.sound"}, name


@pytest.fixture
def evidence_copy(tmp_path, payload):
    binding = copy.deepcopy(_binding(payload, OPERATORS["compute_heat_capacity_p"]["binding"]))
    record_path = Path(binding["evidence"]["build_record"])
    record = _load_json(ROOT / record_path)
    target_root = tmp_path / "repo"
    for relative, digest in record["sources"].items():
        source = ROOT / relative
        assert _digest(source) == digest, f"recorded input changed during test: {relative}"
        destination = target_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    target_record = target_root / record_path
    target_record.write_text(json.dumps(record))
    data = SimpleNamespace(root=target_root, binding=binding, upstream=copy.deepcopy(payload["upstream"]),
                           record=record, record_path=target_record)
    _check_compiled_evidence(data.binding, data.upstream, data.root)
    return data


RECORD_MUTATIONS = [
    *(f"source_bytes:{path}" for path in sorted(NEW_SOURCES | {"lean/bridge/" + CONTRACT_NAME})),
    *(f"record_revision:{revision}" for revision in PREVIOUS_REVISIONS),
    "missing_source_hash", "binding_source_hash", "unapproved_axiom", "declaration_outside_import_closure",
]


@pytest.mark.parametrize("mutation", RECORD_MUTATIONS)
def test_qha_record_consumer_refuses_drift(evidence_copy, mutation):
    data = evidence_copy
    record = data.record
    kind, _, value = mutation.partition(":")
    if kind == "source_bytes":
        path = data.root / value
        path.write_bytes(path.read_bytes() + b"\n")
    elif kind == "record_revision":
        record["upstream_revision"] = value
    elif kind == "missing_source_hash":
        del record["sources"][SOURCE]
    elif kind == "binding_source_hash":
        data.binding["evidence"]["source_sha256"] = "0" * 64
    elif kind == "unapproved_axiom":
        record["axiom_audit"]["declarations"][NS + "harmonic_static_qhaHeatCapacityP_eq_omai"].append("sorryAx")
    elif kind == "declaration_outside_import_closure":
        # Compiled and audited, but owned by a bridge module the QHA source does not import.
        assert "OMAI.PhyslibBridge.compressiveStress_roundtrip" in record["axiom_audit"]["declarations"]
        data.binding["evidence"]["declarations"].append("OMAI.PhyslibBridge.compressiveStress_roundtrip")
    else:
        raise AssertionError(mutation)
    data.record_path.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        _check_compiled_evidence(data.binding, data.upstream, data.root)


class _ReachedCompiler(Exception):
    """Sentinel: the temporary pre-build gate passed; no compiler or writer ran."""


def _temporary_required_contract_gate(tmp_path, monkeypatch, missing=None):
    module = _load_module("qha_required_contract_gate", "audit.py")
    root = tmp_path / "repo"
    package = root / "lean/bridge"
    package.mkdir(parents=True)
    for name in REQUIRED_CONTRACTS - {missing}:
        (package / name).write_text("{}")
    for name in ("lean-toolchain", "lakefile.toml", "lake-manifest.json", "audit.py", "verify_contracts.py"):
        (package / name).write_text("synthetic pre-build fixture\n")
    monkeypatch.setattr(module, "ROOT", package)
    monkeypatch.setattr(module, "REPO", root)

    def stop_before_compiler(*args, **kwargs):
        raise _ReachedCompiler("no compiler or audit writer executed")

    monkeypatch.setattr(module, "subprocess", SimpleNamespace(run=stop_before_compiler))
    return module, package


def test_qha_unit_required_contract_preflight_reaches_sentinel(tmp_path, monkeypatch):
    module, package = _temporary_required_contract_gate(tmp_path, monkeypatch)
    with pytest.raises(_ReachedCompiler):
        module.run()
    assert not (package / "build-evidence.json").exists()


def test_qha_unit_audit_requires_qha_contract(tmp_path, monkeypatch):
    module, package = _temporary_required_contract_gate(tmp_path, monkeypatch, CONTRACT_NAME)
    with pytest.raises(ValueError, match=r"reviewed formula contracts are missing:.*" + re.escape(CONTRACT_NAME)):
        module.run()
    assert not (package / "build-evidence.json").exists()


def test_qha_unit_cited_link_is_in_import_closure(evidence_copy):
    data = evidence_copy
    data.binding["evidence"]["declarations"].append(LINK)
    _check_compiled_evidence(data.binding, data.upstream, data.root)


def test_qha_integration_import_structure():
    for relative in sorted(NEW_SOURCES):
        assert (ROOT / relative).is_file(), f"integration pending: {relative} is absent"
    assert _lean_imports(ROOT / SUPPORT_SOURCE) == ["OMAIPhyslibResponseCalculus",
                                                    "Mathlib.Analysis.Calculus.ImplicitContDiff",
                                                    "Mathlib.Analysis.Calculus.Deriv.MeanValue"]
    assert _lean_imports(ROOT / SOURCE) == [SUPPORT_MODULE, "OMAIPhyslibModeGruneisen"]
    assert _lean_imports(ROOT / WITNESS_SOURCE) == [MODULE, "OMAIPhyslibGruneisenWitness"]
    root_imports = _lean_imports(PACKAGE / "OMAIPhyslibBridge.lean")
    assert root_imports[-3:] == [SUPPORT_MODULE, MODULE, WITNESS_MODULE]
    assert "OMAIPhyslibThermalGruneisen" not in _lean_imports(ROOT / SOURCE)
    lakefile = tomllib.loads((PACKAGE / "lakefile.toml").read_text())
    assert lakefile["lean_lib"][0]["globs"][-3:] == [SUPPORT_MODULE, MODULE, WITNESS_MODULE]


def _configured_compiled_package():
    configured = os.environ.get("PHYSLIB_BRIDGE_PACKAGE")
    if not configured:
        pytest.skip("optional real-compiler check: set PHYSLIB_BRIDGE_PACKAGE to the built package")
    package = Path(configured).resolve()
    manifest = _load_json(package / "lake-manifest.json")
    assert next(p["rev"] for p in manifest["packages"] if p["name"].lower() == "physlib") == REVISION
    assert (package / "lean-toolchain").read_text().strip() == TOOLCHAIN
    return package


@pytest.fixture(scope="module")
def compiled_package(contract):
    return _configured_compiled_package()


def _verify_strict(paths, package):
    verifier = _load_module("qha_strict_contract_verifier", "verify_contracts.py")
    real_run = subprocess.run

    def strict_run(command, **kwargs):
        assert command[:5] == ["lake", "--no-build", "env", "lean", "-j2"]
        return real_run([*command[:5], "-DwarningAsError=true", *command[5:]], **kwargs)

    verifier.subprocess = SimpleNamespace(run=strict_run, TimeoutExpired=subprocess.TimeoutExpired)
    return verifier.verify_compiled_contract_names(paths, package)


def _check_lean_source(package, tmp_path, text, stem):
    with TemporaryDirectory(prefix="qha-probe-", dir=tmp_path) as temporary:
        directory = Path(temporary)
        source = directory / f"{stem}.lean"
        source.write_text(text)
        environment = os.environ.copy()
        environment.update(LEAN_NUM_THREADS="2", MATHLIB_NO_CACHE_ON_UPDATE="1")
        command = ["lake", "--no-build", "env", "bash", "-c",
                   'export LEAN_PATH="$1${LEAN_PATH:+:$LEAN_PATH}"; shift; '
                   'exec lean -j2 -DwarningAsError=true "$@"',
                   "qha-probe", str(directory), f"--root={directory}", str(source)]
        return subprocess.run(command, cwd=package, env=environment, text=True, capture_output=True,
                              timeout=180, check=False)


def test_qha_real_endpoint_names(compiled_package):
    assert _verify_strict([compiled_package / CONTRACT_NAME], compiled_package) == PAIRS
    pairs = _verify_strict([compiled_package / name for name in sorted(REQUIRED_CONTRACTS)], compiled_package)
    assert len(pairs) == EARLIER_PAIR_COUNT + len(PAIRS) and all(pair in pairs for pair in PAIRS)


@pytest.mark.parametrize("mutation,diagnostic", [
    ("namespace", "Contract declaration is absent: InventedOMAI"),
    ("owner", "belongs to OMAIPhyslibQHA, not OMAIPhyslibContinuum"),
])
def test_qha_real_provenance_negatives(compiled_package, contract, tmp_path, mutation, diagnostic):
    mutated = copy.deepcopy(contract)
    if mutation == "namespace":
        mutated["operators"][0]["lean_definition"] = "InventedOMAI.Response.qhaGibbsEnergy"
    else:
        mutated["operators"][0]["definition_source_path"] = "lean/bridge/OMAIPhyslibContinuum.lean"
    path = tmp_path / "mutated-formula-contract.json"
    path.write_text(json.dumps(mutated))
    with pytest.raises(ValueError, match=diagnostic):
        _verify_strict([path], compiled_package)


_CLOSURE_PROBE = """import OMAIPhyslibBridge
import Lean
open Lean Elab Command Meta

namespace OMAIQHAProbe

def kindOf : ConstantInfo → String
  | .defnInfo _ => "def"
  | .thmInfo _ => "thm"
  | .inductInfo _ => "induct"
  | .ctorInfo _ => "ctor"
  | .recInfo _ => "rec"
  | .axiomInfo _ => "axiom"
  | .opaqueInfo _ => "opaque"
  | .quotInfo _ => "quot"

def usedNames (info : ConstantInfo) : Array Name :=
  match info with
  | .defnInfo val => info.type.getUsedConstants ++ val.value.getUsedConstants
  | .opaqueInfo val => info.type.getUsedConstants ++ val.value.getUsedConstants
  | .inductInfo val => info.type.getUsedConstants ++ val.ctors.toArray
  | _ => info.type.getUsedConstants

def closure (env : Environment) (roots : List Name) : Array Name := Id.run do
  let mut seen : NameSet := {}
  let mut order : Array Name := #[]
  let mut stack := roots
  for _ in [0:1000000] do
    match stack with
    | [] => break
    | name :: rest =>
      stack := rest
      if seen.contains name then
        continue
      seen := seen.insert name
      order := order.push name
      if (__BRIDGE__).isPrefixOf name then
        if let some info := env.find? name then
          for used in usedNames info do
            if !seen.contains used then
              stack := used :: stack
  return order

end OMAIQHAProbe

run_cmd do
  let env := (← getEnv).setExporting false
  let roots : List Name := [__ROOTS__]
  let sentinels : List Name := [__SENTINELS__]
  for sentinel in sentinels do
    logInfo m!"OMAI_QHA_SENTINEL|{sentinel}|{if env.contains sentinel then "present" else "missing"}"
  for root in roots do
    let some info := env.find? root
      | throwError m!"Missing QHA endpoint: {root}"
    let owner := match env.getModuleIdxFor? root with
      | some index => toString (env.header.moduleNames[index.toNat]!)
      | none => "none"
    logInfo m!"OMAI_QHA_ROOT|{root}|{OMAIQHAProbe.kindOf info}|{owner}"
    for name in OMAIQHAProbe.closure env [root] do
      let kind := match env.find? name with
        | some found => OMAIQHAProbe.kindOf found
        | none => "missing"
      logInfo m!"OMAI_QHA_CLOSURE|{root}|{name}|{kind}"
  for name in OMAIQHAProbe.closure env [__CONTROL__] do
    logInfo m!"OMAI_QHA_CONTROL|{name}"
  logInfo m!"OMAI_QHA_CLOSURE_OK|{roots.length}"
"""


def _closure_probe_source():
    names = lambda items: ", ".join(BACKTICK + name for name in items)  # noqa: E731
    return (_CLOSURE_PROBE
            .replace("__BRIDGE__", BACKTICK + "OMAI.PhyslibBridge")
            .replace("__ROOTS__", names(ROOTS))
            .replace("__SENTINELS__", names(sorted(FORBIDDEN_EXACT)))
            .replace("__CONTROL__", BACKTICK + NS + "GibbsBranchAt.isobar"))


def test_qha_real_anti_circularity_closure(compiled_package, tmp_path):
    result = _check_lean_source(compiled_package, tmp_path, _closure_probe_source(), "QHAClosureProbe")
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert re.findall(r"OMAI_QHA_CLOSURE_OK\|(\d+)", output) == [str(len(ROOTS))]
    sentinels = dict(re.findall(r"OMAI_QHA_SENTINEL\|([^|\s]+)\|(present|missing)", output))
    assert sentinels == {name: "present" for name in FORBIDDEN_EXACT}, "sentinel typo or missing constant"
    roots = {name: (kind, owner) for name, kind, owner
             in re.findall(r"OMAI_QHA_ROOT\|([^|\s]+)\|(\w+)\|([^|\s]+)", output)}
    assert roots == {name: ("def", MODULE) for name in ROOTS}
    closures = {}
    for root, name, kind in re.findall(r"OMAI_QHA_CLOSURE\|([^|\s]+)\|([^|\s]+)\|(\w+)", output):
        closures.setdefault(root, {})[name] = kind
    assert set(closures) == set(ROOTS)
    for root in ROOTS:
        reached = closures[root]
        assert not [name for name in reached if name.startswith("_private.")], (root, "private helper")
        forbidden = sorted(name for name in reached if name in FORBIDDEN_EXACT)
        assert not forbidden, (root, forbidden)
        bridge = {name for name, kind in reached.items() if name.startswith("OMAI.PhyslibBridge.") and kind != "thm"}
        assert bridge <= ALLOWED_OMAI_CLOSURE, (root, sorted(bridge - ALLOWED_OMAI_CLOSURE))
    assert "CanonicalEnsemble.heatCapacity" in closures[NS + "qhaThermalGruneisen"]
    assert "sInf" in closures[NS + "qhaGibbsEnergy"] or "InfSet.sInf" in closures[NS + "qhaGibbsEnergy"]
    # Positive control: the walker does reach the branch quantities it forbids above.
    control = set(re.findall(r"OMAI_QHA_CONTROL\|([^|\s]+)", output))
    assert {NS + "GibbsBranchAt", NS + "StableBranchAt"} <= control


_TYPED_CONSUMER = """module
import OMAIPhyslibBridge
set_option autoImplicit false
open OMAI.PhyslibBridge OMAI.PhyslibBridge.Response OMAI.PhyslibBridge.QHAWitness
open OMAI.PhyslibBridge.GruneisenWitness Filter Set
open scoped Topology

example (F : Surface) (I : Set ℝ) (x : ℝ × ℝ) :
    qhaGibbsEnergy F I x = sInf ((fun w => F (x.1, w) + x.2 * w) '' I) := rfl

example (G : ℝ × ℝ → ℝ) (x : ℝ × ℝ) :
    qhaHeatCapacityP G x = -x.1 * deriv (deriv (fun s => G (s, x.2))) x.1 := rfl

example (G : ℝ × ℝ → ℝ) (x : ℝ × ℝ) :
    qhaThermalExpansion G x = deriv (fun s => deriv (fun q => G (s, q)) x.2) x.1 /
      deriv (fun q => G (x.1, q)) x.2 := rfl

example (M : HarmonicVolumeModel) (T : Temperature) (p : ℝ)
    (B : GibbsBranchAt M.freeEnergy M.domain ((T : ℝ), p)) {I : Set ℝ}
    (hI : qhaGibbsEnergy M.freeEnergy I =ᶠ[𝓝 ((T : ℝ), p)] B.gibbs) :
    qhaHeatCapacityP (qhaGibbsEnergy M.freeEnergy I) ((T : ℝ), p) =
        M.actualCp p B.isobar.volume (T : ℝ) ∧
      qhaHeatCapacityP (qhaGibbsEnergy M.freeEnergy I) ((T : ℝ), p) =
        M.cv ((T : ℝ), B.volume ((T : ℝ), p)) + (T : ℝ) * B.volume ((T : ℝ), p) *
          qhaThermalExpansion (qhaGibbsEnergy M.freeEnergy I) ((T : ℝ), p) ^ 2 *
          qhaBulkModulus M.freeEnergy I ((T : ℝ), p) :=
  harmonic_static_qhaHeatCapacityP_eq_omai M T p B hI

example (M : HarmonicVolumeModel) (T : Temperature) (p : ℝ)
    (B : GibbsBranchAt M.freeEnergy M.domain ((T : ℝ), p)) {I : Set ℝ}
    (hI : qhaGibbsEnergy M.freeEnergy I =ᶠ[𝓝 ((T : ℝ), p)] B.gibbs) :
    deriv (fun s => qhaGibbsEnergy M.freeEnergy I (s, p)) (T : ℝ) =
      -((M.reference.avogadro / (M.reference.qCount : ℝ)) *
        (M.ensembleAt (B.volume ((T : ℝ), p) / M.reference.avogadro)
          B.in_domain.self_of_nhds.2).thermodynamicEntropy T) :=
  harmonic_static_qhaGibbs_entropy M T p B hI

example (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n) :
    ∃ ε₀ > 0, ∀ ε, 0 < ε → ε ≤ ε₀ →
      qhaThermalExpansion
          (qhaGibbsEnergy (rateModel negativeRates A hA n hn).freeEnergy (Ioo (A - ε) (A + ε)))
          ((witnessTemperature : ℝ), 0) < 0 ∧
      (rateModel negativeRates A hA n hn).cv ((witnessTemperature : ℝ), A) <
        qhaHeatCapacityP
          (qhaGibbsEnergy (rateModel negativeRates A hA n hn).freeEnergy (Ioo (A - ε) (A + ε)))
          ((witnessTemperature : ℝ), 0) ∧
      qhaThermalGruneisen
          (fun i : Fin n × Fin 3 => (rateModel negativeRates A hA n hn).modeGruneisen i.1 i.2 1)
          (fun i => ((rateModel negativeRates A hA n hn).gridAt 1
            (one_mem_J negativeRates A hA n hn)).oscillator i.1 i.2) witnessTemperature < 0 :=
  negative_qha_witness A hA n hn

example (M : HarmonicVolumeModel) (T : Temperature) (p : ℝ)
    (B : GibbsBranchAt M.freeEnergy M.domain ((T : ℝ), p)) {I : Set ℝ}
    (hI : qhaGibbsEnergy M.freeEnergy I =ᶠ[𝓝 ((T : ℝ), p)] B.gibbs) :
    qhaBulkModulus M.freeEnergy I ((T : ℝ), p) =
      -gibbsVolume (qhaGibbsEnergy M.freeEnergy I) ((T : ℝ), p) /
        deriv (fun q => gibbsVolume (qhaGibbsEnergy M.freeEnergy I) ((T : ℝ), q)) p :=
  harmonic_static_qhaBulkModulus_eq_omai M T p B hI

example (M : HarmonicVolumeModel) (T : Temperature) (p : ℝ)
    (B : GibbsBranchAt M.freeEnergy M.domain ((T : ℝ), p)) {a b : ℝ}
    (hJ : B.volume ((T : ℝ), p) ∈ Ioo a b)
    (hconv : ∀ᶠ t in 𝓝 (T : ℝ), ∀ w ∈ Ioo a b,
      (t, w) ∈ M.domain ∧ 0 < FVV M.freeEnergy (t, w)) :
    qhaGibbsEnergy M.freeEnergy (Ioo a b) =ᶠ[𝓝 ((T : ℝ), p)] B.gibbs :=
  (harmonic_static_qhaGibbs_convex_window M T p B hJ hconv).2

example (M : HarmonicVolumeModel) (T : Temperature) (p : ℝ)
    (B : GibbsBranchAt M.freeEnergy M.domain ((T : ℝ), p)) {I : Set ℝ}
    (hI : qhaGibbsEnergy M.freeEnergy I =ᶠ[𝓝 ((T : ℝ), p)] B.gibbs) :
    deriv (fun w => M.entropy ((T : ℝ), w)) (B.volume ((T : ℝ), p)) =
      qhaThermalExpansion (qhaGibbsEnergy M.freeEnergy I) ((T : ℝ), p) *
        qhaBulkModulus M.freeEnergy I ((T : ℝ), p) :=
  (harmonic_static_qhaHeatCapacityP_eq_entropy_slope M T p B hI).2.2
"""


def test_qha_real_typed_endpoints_and_witnesses(compiled_package, tmp_path):
    result = _check_lean_source(compiled_package, tmp_path, _TYPED_CONSUMER, "QHATypedConsumer")
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("case", ["cv_for_cp", "cp_for_bulk"])
def test_qha_real_typed_negatives(compiled_package, tmp_path, case):
    lhs = "M.actualCp p B.isobar.volume (T : ℝ)"
    if case == "cv_for_cp":
        lhs = "M.cv ((T : ℝ), B.volume ((T : ℝ), p))"
    source = (
        "module\nimport OMAIPhyslibBridge\nset_option autoImplicit false\n"
        "open OMAI.PhyslibBridge OMAI.PhyslibBridge.Response Filter\nopen scoped Topology\n\n"
        "example (M : HarmonicVolumeModel) (T : Temperature) (p : ℝ)\n"
        "    (B : GibbsBranchAt M.freeEnergy M.domain ((T : ℝ), p)) {I : Set ℝ}\n"
        "    (hI : qhaGibbsEnergy M.freeEnergy I =ᶠ[𝓝 ((T : ℝ), p)] B.gibbs) :\n"
        + ("    qhaHeatCapacityP (qhaGibbsEnergy M.freeEnergy I) ((T : ℝ), p) = " + lhs + " :=\n"
           "  (harmonic_static_qhaHeatCapacityP_eq_omai M T p B hI).1\n" if case == "cv_for_cp" else
           "    qhaBulkModulus M.freeEnergy I ((T : ℝ), p) = " + lhs + " :=\n"
           "  harmonic_static_qhaBulkModulus_eq_omai M T p B hI\n"))
    result = _check_lean_source(compiled_package, tmp_path, source, "QHATypedNegative")
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "type mismatch" in output.lower(), output
    assert not any(message in output.lower()
                   for message in ("unknown module", "unknown identifier", "unknown constant")), output
