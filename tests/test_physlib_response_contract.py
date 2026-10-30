"""Cp-only integration and provenance regressions.

Frozen literals are reviewed preservation pins, not regenerated expectations.
Synthetic unit fixtures test metadata guards only; they are never published as
proof evidence. Final-artifact tests fail while integration is incomplete.
Compiler probes use an already-built package and never run its audit writer.
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
from contextlib import ExitStack
from dataclasses import fields, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

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
from omai.operator.identity import canonical_json
from physlib_tranches import (
    GLOBAL_COVERAGE, bindings_after, contracts_after, pairs_after, subjects_after,
)

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "lean/bridge"
REVISION = "9b583cb6ef6e9cc537c4d4b786b508de1abbcf42"
OLD_REVISION = "8ddcc004043c5b537e4225fa763121c176b62a4a"
PREVIOUS_REVISIONS = (OLD_REVISION, "d70acc20677320d37b38e602e331e900466b704d")
TOOLCHAIN = "leanprover/lean4:v4.35.0"
BINDING_ID = "harmonic-static-cp-identity"
CONTRACT_NAME = "response-formula-contract.json"
MODULE = "OMAIPhyslibHarmonicResponse"
SOURCE = "lean/bridge/OMAIPhyslibHarmonicResponse.lean"
NAMESPACE = "OMAI.PhyslibBridge.Response."
DEFINITION = NAMESPACE + "heatCapacityPIdentity"
FINAL_THEOREMS = frozenset({
    NAMESPACE + "harmonic_static_heatCapacityP_eq_omai",
    NAMESPACE + "harmonic_static_heatCapacityP_ge_heatCapacityV",
})
WITNESS_THEOREMS = frozenset({
    NAMESPACE + "nonzero_expansion_witness",
    NAMESPACE + "zero_response_control",
})
OPERATOR = "contract_heat_capacity_p_identity"
OUTPUT = "HeatCapacityConstantP"
OPERATOR_UID = "79a11e58595c8b262c104330dcfc622f13a787da6bae856cf4f40b57a6a93639"
FORMULA_SHA = "97ed2e0d3a11efad01a3ab0017d21be3da3009446b0b9364673fad4b8fdcb0f1"
OUTPUT_UID = "08057e4554a3420c933329b3821de9295e2b5950191e23cafe310b0a15adc7b6"
CATALOG_ID_SHA = "4e77f8c9e46367ffb17f83207c60371afc98ef310c9961680d70f5847467334c"
CP_SUBJECTS = frozenset({("operator", OPERATOR), ("node", OUTPUT)})
BASELINE_OPERATORS = frozenset({
    "compute_entropy", "compute_free_energy", "compute_heat_capacity",
    "compute_internal_energy", "contract_molar_entropy", "contract_molar_free_energy",
    "contract_molar_heat_capacity", "contract_molar_internal_energy",
    "contract_power_factor", "contract_pressure", "contract_volumetric_heat_capacity",
    "contract_zt", "sum_thermal_conductivity",
})
BASELINE_NODES = frozenset({
    "Entropy", "HeatCapacity", "HelmholtzFreeEnergy", "InternalEnergy",
    "MolarEntropy", "MolarHeatCapacity", "MolarHelmholtzFreeEnergy", "MolarInternalEnergy",
    "PowerFactor", "Pressure", "Temperature", "ThermalConductivity[contribution=total]",
    "VolumetricHeatCapacity", "ZT",
})
BASELINE_SUBJECTS = frozenset(
    [("operator", name) for name in BASELINE_OPERATORS]
    + [("node", name) for name in BASELINE_NODES]
)
NEW_SOURCES = frozenset("lean/bridge/" + name + ".lean" for name in (
    "OMAIPhyslibStaticEnsemble", "OMAIPhyslibResponseUnits",
    "OMAIPhyslibResponseCalculus", "OMAIPhyslibHarmonicVolume",
    "OMAIPhyslibResponseWitness", MODULE,
))
# Preserve the seven earlier contracts byte-for-byte; the new endpoint is additive.
LEGACY_CONTRACT_HASHES = {
    "semantic-formula-contract.json": "21002241bb9dae2d674df0ede26cf7f0804823591675bcb4099142e7a5d1b123",
    "continuum-formula-contract.json": "b5fb4368abccaac9fcde8b6ccb6dfd55402f14f1a9537e898645484ba69b2e8f",
    "harmonic-ensemble-formula-contract.json": "787bff6c81de388b2631c77b044b394a03c8562c744493931f09db60e8f663ab",
    "harmonic-sums-formula-contract.json": "c897e8de5d7c1b7211f95e0cd599479c87a738de946be683bd5ab3ae78be1699",
    "harmonic-product-formula-contract.json": "adffdaa7139f3d919eb1ea058130fb502ad0d6e2e375bf2465ce47abf472d995",
    "harmonic-density-formula-contract.json": "b3f5f43df5ae50417ec309a996dcdbbef311fcac9bd4bb72957f45da28533ba8",
    "joint-density-formula-contract.json": "f5a5bb01044f479cf9770573121442a84117af1a84a6976d5ede0765256dfd04"
}
CP_ERA_CONTRACTS = frozenset(LEGACY_CONTRACT_HASHES) | {CONTRACT_NAME}
GAMMA_CONTRACT_NAME = "thermal-gruneisen-formula-contract.json"
# Later tranches add their own required contracts; see tests/physlib_tranches.py.
REQUIRED_CONTRACTS = CP_ERA_CONTRACTS | {GAMMA_CONTRACT_NAME} | contracts_after()
BASELINE_BINDINGS = frozenset(
    ['absolute-temperature',
     'abstract-crystal-structure',
     'classical-harmonic-frequency',
     'classical-harmonic-potential-force',
     'continuum-stress-sign',
     'harmonic-joint-molar-ensemble',
     'harmonic-joint-volumetric-heat-capacity',
     'harmonic-mode-entropy',
     'harmonic-mode-free-energy',
     'harmonic-mode-heat-capacity',
     'harmonic-mode-internal-energy',
     'harmonic-molar-entropy',
     'harmonic-molar-free-energy',
     'harmonic-molar-heat-capacity',
     'harmonic-molar-internal-energy',
     'harmonic-volumetric-heat-capacity',
     'thermodynamic-pressure',
     'thermoelectric-figure-of-merit',
     'thermoelectric-input-coefficients',
     'thermoelectric-power-factor',
     'thermoelectric-total-conductivity']
)
BASELINE_PAIRS = [{'module': 'OMAIPhyslibSemantics', 'name': 'OMAI.PhyslibBridge.figureOfMerit'},
 {'module': 'OMAIPhyslibSemantics', 'name': 'OMAI.PhyslibBridge.harmonicEntropy'},
 {'module': 'OMAIPhyslibSemantics', 'name': 'OMAI.PhyslibBridge.harmonicFreeEnergy'},
 {'module': 'OMAIPhyslibHarmonicEnsemble', 'name': 'OMAI.PhyslibBridge.harmonicHeatCapacity'},
 {'module': 'OMAIPhyslibSemantics', 'name': 'OMAI.PhyslibBridge.harmonicInternalEnergy'},
 {'module': 'OMAIPhyslibHarmonicSums', 'name': 'OMAI.PhyslibBridge.harmonicMolarEntropy'},
 {'module': 'OMAIPhyslibHarmonicSums', 'name': 'OMAI.PhyslibBridge.harmonicMolarFreeEnergy'},
 {'module': 'OMAIPhyslibHarmonicSums',
  'name': 'OMAI.PhyslibBridge.harmonicMolarHeatCapacity'},
 {'module': 'OMAIPhyslibHarmonicSums',
  'name': 'OMAI.PhyslibBridge.harmonicMolarInternalEnergy'},
 {'module': 'OMAIPhyslibHarmonicDensity',
  'name': 'OMAI.PhyslibBridge.harmonicVolumetricHeatCapacity'},
 {'module': 'OMAIPhyslibSemantics', 'name': 'OMAI.PhyslibBridge.powerFactor'},
 {'module': 'OMAIPhyslibContinuum', 'name': 'OMAI.PhyslibBridge.pressureFromStress'},
 {'module': 'OMAIPhyslibSemantics', 'name': 'OMAI.PhyslibBridge.totalThermalConductivity'}]
# Scientific protocol, golden vectors, historical package and seven retained proofs.
PRESERVED_HASHES = {
    "map/log.jsonl": "59ef7d3e29fa63bca61bfbeccaa6a56d27406a71878cb50269df85139f1d6941",
    "docs/data/version.json": "fb4fe1f294120184294492e20263db133e250645dd9d229d469a5c322e64b520",
    "omai/operator/identity.py": "e8be3c3b86521e19c9ed1a855f33d2b187bbc2fb9158f269ae219855295ef9f0",
    "omai/lineages.py": "3266c424e4920d11bd54a1e8f0fad0fc8aeeb8a2dcfb4c2dbb3da66a61a5c552",
    "omai/schema.py": "69ee90c2eebf6f891abcc9cc31351b885d23a6f3a6d37e46b810959474bd2f36",
    "omai/vectors/configurations.json": "920e393a2646cb260eca44adf36a494180d5ab0f283dc4f234778c19ee4d9fed",
    "omai/vectors/lineage_ids.json": "cfc3fabec94b6f6316151338de57e6cd520c69ae671cc0e3eb546f3bd7047b35",
    "omai/vectors/models.json": "8ca7486a92055d79065a779e663be9ec7897a078435bec521528ff430ff93872",
    "omai/vectors/overlay.json": "4d26fb3f8a94dcf20e57ab1e71d0a9e11957084cede64af7365078eb8e40d0a2",
    "omai/vectors/private.json": "42995cae634ce5631dbb654e853239e5357f3f66c3dcd924ffd2b3c2c3b5e279",
    "omai/vectors/records.json": "d9aff626f7153b4b0b1b4db40d886b09ac4af8bc354048c221dae79dfa3f777f",
    "omai/vectors/releases.json": "e14c995a44f307fcfce04ea701cb59ad933a7f41239085a9799e6d3ed2c81bd3",
    "omai/vectors/render.json": "e01c9344751de35c5862da063da0ae27c8549aaed035d5117c6fcdb748446e76",
    "lean/bridge/OMAIPhyslibSemantics.lean": "9ce9bbe14c751333465a9f08bdb5319f369361e136f2f8233e8e72e6614797a5",
    "lean/bridge/OMAIPhyslibContinuum.lean": "e8bff3cb5d44cd78885d8c5f200d8761e8c568cd0d101fc0c2110f521bdca7ff",
    "lean/bridge/OMAIPhyslibHarmonicEnsemble.lean": "1a1f7e60f5cf4a3e468d173109b0127d7685123e6e0130b69374df687b94e172",
    "lean/bridge/OMAIPhyslibHarmonicSums.lean": "5b3c3afbfc6a0fe5e9951091d66fc61b0802ebd6b5ca786927c67ecba2193e52",
    "lean/bridge/OMAIPhyslibHarmonicProduct.lean": "4c0af6605e43ceed3460a8c7fe9198f486bd48cf2ac6e538fa0c45ac1a644578",
    "lean/bridge/OMAIPhyslibHarmonicDensity.lean": "cf4d59af5b660a1fc73b079d63451f269081e1bd9a3018047e1f6f41517013ea",
    "lean/bridge/OMAIPhyslibJointDensity.lean": "9f5f729c3db288f9d5b7e1b285b050c40df8caeabf72df09591d6203c6e7fde7"
}


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
    return {
        (target["kind"], target["id"])
        for binding in payload["bindings"]
        for target in compiled_targets(binding, payload["inventory"])
    }


def _response_binding(payload):
    rows = [row for row in payload["bindings"] if row["id"] == BINDING_ID]
    assert len(rows) == 1, "integration pending: expected exactly one reviewed Cp binding"
    return rows[0]


def _assert_selected_scope(payload):
    binding = _response_binding(payload)
    assert binding["relation"] == "conditional"
    evidence = binding["evidence"]
    assert evidence["kind"] == "compiled_bridge"
    explicit = [(row["kind"], row["id"]) for row in evidence.get("proved_targets", [])]
    assert len(explicit) == 2 and set(explicit) == CP_SUBJECTS, "Cp proof scope broadened"
    assert _subjects(payload) == BASELINE_SUBJECTS | CP_SUBJECTS, "unique proof subjects changed"
    assert {row["id"] for row in payload["bindings"]} == BASELINE_BINDINGS | {BINDING_ID}
    inventory = catalog_inventory()
    expected = {
        "nodes_total": len(inventory["nodes"]), "operators_total": len(inventory["operators"]),
        "operators_compiled": 14, "nodes_compiled": 15,
        "nodes_compiled_outputs": 14, "nodes_compiled_interpretations": 1,
        "bindings_total": 22, "compiled_bridges": 17, "source_correspondences": 5,
    }
    for key, value in expected.items():
        assert payload["coverage"][key] == value, key


GAMMA_BINDING_ID = "harmonic-static-thermal-gruneisen-identity"
GAMMA_SUBJECTS = {("operator", "contract_thermal_gruneisen_identity"), ("node", "ThermalGruneisen")}
GAMMA_PAIR = {"name": "OMAI.PhyslibBridge.Response.thermalGruneisenIdentity",
              "module": "OMAIPhyslibThermalGruneisen"}
LATER_BINDING_IDS = bindings_after()
LATER_SUBJECTS = subjects_after()
LATER_PAIRS = pairs_after()


def _assert_current_scope(payload):
    """Exact real-payload ledger after the thermal Gruneisen tranche and every later one.

    The Cp scope itself stays exactly CP_SUBJECTS; synthetic Cp-only tests keep
    using _assert_selected_scope unchanged.
    """
    binding = _response_binding(payload)
    assert binding["relation"] == "conditional"
    evidence = binding["evidence"]
    assert evidence["kind"] == "compiled_bridge"
    explicit = [(row["kind"], row["id"]) for row in evidence.get("proved_targets", [])]
    assert len(explicit) == 2 and set(explicit) == CP_SUBJECTS, "Cp proof scope broadened"
    gamma = [row for row in payload["bindings"] if row["id"] == GAMMA_BINDING_ID]
    assert len(gamma) == 1, "integration pending: expected exactly one reviewed thermal Gruneisen binding"
    gamma_explicit = [(row["kind"], row["id"]) for row in gamma[0]["evidence"].get("proved_targets", [])]
    assert len(gamma_explicit) == 2 and set(gamma_explicit) == GAMMA_SUBJECTS, "gamma proof scope broadened"
    assert _subjects(payload) == BASELINE_SUBJECTS | CP_SUBJECTS | GAMMA_SUBJECTS | LATER_SUBJECTS, \
        "unique proof subjects changed"
    assert {row["id"] for row in payload["bindings"]} == (
        BASELINE_BINDINGS | {BINDING_ID, GAMMA_BINDING_ID} | LATER_BINDING_IDS)
    for key, value in GLOBAL_COVERAGE.items():
        assert payload["coverage"][key] == value, key


def _assert_response_contract(contract, root=ROOT):
    assert contract["schema_version"] == 1
    assert contract["source_path"] == SOURCE, "reviewed proof source changed"
    assert contract["source_sha256"] == _digest(root / SOURCE), "reviewed source hash changed"
    assert len(contract["operators"]) == 1, "reviewed operator endpoint set changed"
    operator = contract["operators"][0]
    expected = {"id": OPERATOR, "uid": OPERATOR_UID,
                "formula_sha256": FORMULA_SHA, "lean_definition": DEFINITION}
    for key, value in expected.items():
        assert operator[key] == value, f"reviewed operator endpoint {key} changed"
    assert operator.get("definition_source_path", SOURCE) == SOURCE, "definition owner changed"
    assert len(contract.get("nodes", [])) == 1, "reviewed node endpoint set changed"
    node = contract["nodes"][0]
    assert (node["id"], node["uid"]) == (OUTPUT, OUTPUT_UID), "reviewed node endpoint changed"
    if "lean_definition" in node:
        assert node["lean_definition"] == DEFINITION, "extra interpreted-node endpoint"
        assert node.get("definition_source_path", SOURCE) == SOURCE, "definition owner changed"


def _synthetic_scope_seeds():
    """Metadata-only fixture: neither a scientific theorem nor persisted evidence."""
    seeds = _load_json(ROOT / "omai/data/physlib_formula_seeds.json")
    seeds["bindings"] = [b for b in seeds["bindings"] if b["id"] in BASELINE_BINDINGS]
    example = copy.deepcopy(next(b for b in seeds["bindings"]
                                 if b["id"] == "harmonic-mode-heat-capacity"))
    example.update(
        id=BINDING_ID,
        statement="Synthetic scope-guard fixture, not scientific proof evidence.",
        relation="conditional",
        targets=[{"kind": "operator", "id": OPERATOR, "uid": OPERATOR_UID,
                  "formula_sha256": FORMULA_SHA},
                 {"kind": "node", "id": OUTPUT, "uid": OUTPUT_UID}],
    )
    example["evidence"] = {
        "kind": "compiled_bridge", "module": MODULE, "source_path": SOURCE,
        "source_sha256": "0" * 64, "build_record": "lean/bridge/build-evidence.json",
        "declarations": sorted(FINAL_THEOREMS),
        "proved_targets": [{"kind": kind, "id": name} for kind, name in sorted(CP_SUBJECTS)],
    }
    seeds["bindings"].append(example)
    return seeds


def _target(kind, name):
    inventory = catalog_inventory()["operators" if kind == "operator" else "nodes"]
    row = next(row for row in inventory if row["id"] == name)
    target = {"kind": kind, "id": name, "uid": row["uid"]}
    if kind == "operator":
        target["formula_sha256"] = row["formula_sha256"]
    return target


def _write_contract(directory, contract):
    path = directory / "mutated-formula-contract.json"
    path.write_text(json.dumps(contract))
    return path


@pytest.fixture(scope="module")
def response_payload():
    payload = build_formula_bindings()
    _response_binding(payload)  # Missing final artifacts fail, never skip or xfail.
    return payload


@pytest.fixture(scope="module")
def response_contract():
    path = PACKAGE / CONTRACT_NAME
    assert path.is_file(), "integration pending: reviewed response contract is absent"
    contract = _load_json(path)
    _assert_response_contract(contract)
    return contract


@pytest.fixture
def synthetic_contract(tmp_path):
    root = tmp_path / "repo"
    source = root / SOURCE
    source.parent.mkdir(parents=True)
    source.write_text("-- Synthetic source bytes for hash-guard tests, not a Lean proof.\n")
    contract = {
        "schema_version": 1, "source_path": SOURCE, "source_sha256": _digest(source),
        "operators": [{"id": OPERATOR, "uid": OPERATOR_UID,
                       "formula_sha256": FORMULA_SHA, "lean_definition": DEFINITION}],
        "nodes": [{"id": OUTPUT, "uid": OUTPUT_UID}],
    }
    _assert_response_contract(contract, root)
    return root, contract


@pytest.fixture
def evidence_copy(tmp_path):
    """Valid recorded baseline snapshot for consumer mutations, not worktree acceptance.

    Copy only recorded bytes; the final integration test separately requires
    every new source in the actual worktree and the actual response binding.
    """
    payload = build_formula_bindings()
    binding = copy.deepcopy(next(b for b in payload["bindings"]
                                 if b["id"] == "harmonic-mode-heat-capacity"))
    record_path = Path(binding["evidence"]["build_record"])
    record = _load_json(ROOT / record_path)
    target_root = tmp_path / "repo"
    for relative, digest in record["sources"].items():
        source = ROOT / relative
        assert source.resolve().is_relative_to(PACKAGE.resolve())
        assert _digest(source) == digest, f"recorded input changed during test: {relative}"
        destination = target_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    target_record = target_root / record_path
    target_record.write_text(json.dumps(record))
    data = SimpleNamespace(root=target_root, binding=binding,
                           upstream=copy.deepcopy(payload["upstream"]),
                           record=record, record_path=target_record)
    _check_compiled_evidence(data.binding, data.upstream, data.root)
    return data


def test_response_unit_catalog_identity_projection_and_cp_pins():
    inventory = catalog_inventory()
    projection = {
        "nodes": [{key: row[key] for key in ("id", "uid")} for row in inventory["nodes"] if row["id"] == OUTPUT],
        "operators": [{key: row[key] for key in ("id", "uid", "formula_sha256")}
                      for row in inventory["operators"] if row["id"] == OPERATOR],
    }
    assert hashlib.sha256(canonical_json(projection).encode()).hexdigest() == CATALOG_ID_SHA
    assert _target("operator", OPERATOR) == {
        "kind": "operator", "id": OPERATOR, "uid": OPERATOR_UID, "formula_sha256": FORMULA_SHA,
    }
    assert _target("node", OUTPUT)["uid"] == OUTPUT_UID


@pytest.mark.parametrize("relative,digest", sorted(PRESERVED_HASHES.items()))
def test_response_unit_preserved_scientific_protocol_bytes(relative, digest):
    assert _digest(ROOT / relative) == digest, relative


@pytest.mark.parametrize("name,digest", sorted(LEGACY_CONTRACT_HASHES.items()))
def test_response_unit_retained_contract_bytes(name, digest):
    assert _digest(PACKAGE / name) == digest, name


def test_response_unit_scope_helper_accepts_synthetic_metadata_only():
    _assert_selected_scope(build_formula_bindings(_synthetic_scope_seeds()))


@pytest.mark.parametrize("kind,name", [
    ("operator", "compute_heat_capacity_p"), ("operator", "contract_thermal_gruneisen_identity"),
    ("operator", "contract_thermal_gruneisen"), ("operator", "contract_molar_volume"),
    ("operator", "compute_msd"), ("operator", "compute_velocity_autocorrelation"),
    ("node", "Structure"), ("node", "MolarVolume"), ("node", "ThermalExpansion"),
    ("node", "BulkModulus"), ("node", "MolarHeatCapacity"), ("node", "Temperature"),
])
def test_response_unit_scope_guard_rejects_extra_subjects(kind, name):
    seeds = _synthetic_scope_seeds()
    binding = next(b for b in seeds["bindings"] if b["id"] == BINDING_ID)
    binding["targets"].append(_target(kind, name))
    binding["evidence"]["proved_targets"].append({"kind": kind, "id": name})
    payload = build_formula_bindings(seeds)
    with pytest.raises(AssertionError, match="Cp proof scope broadened"):
        _assert_selected_scope(payload)


def test_response_unit_duplicate_proof_is_depth_not_new_subjects():
    seeds = _synthetic_scope_seeds()
    before = build_formula_bindings(seeds)
    duplicate = copy.deepcopy(next(b for b in seeds["bindings"] if b["id"] == BINDING_ID))
    duplicate["id"] = "synthetic-second-cp-proof"
    seeds["bindings"].append(duplicate)
    after = build_formula_bindings(seeds)
    assert _subjects(before) == _subjects(after) == BASELINE_SUBJECTS | CP_SUBJECTS
    for key in ("operators_compiled", "nodes_compiled", "nodes_compiled_outputs",
                "nodes_compiled_interpretations"):
        assert before["coverage"][key] == after["coverage"][key]
    assert after["coverage"]["bindings_total"] == before["coverage"]["bindings_total"] + 1


def test_response_unit_associations_do_not_become_proof_subjects():
    seeds = _synthetic_scope_seeds()
    binding = next(b for b in seeds["bindings"] if b["id"] == BINDING_ID)
    binding["targets"].extend(_target("node", name) for name in (
        "Temperature", "MolarHeatCapacity", "MolarVolume", "ThermalExpansion", "BulkModulus",
    ))
    payload = build_formula_bindings(seeds)
    _assert_selected_scope(payload)
    assert {(x["kind"], x["id"]) for x in compiled_targets(
        _response_binding(payload), payload["inventory"])} == CP_SUBJECTS


@pytest.mark.parametrize("field", ["uid", "formula_sha256"])
def test_response_unit_generator_refuses_stale_reviewed_cp_pin(field):
    seeds = _synthetic_scope_seeds()
    binding = next(b for b in seeds["bindings"] if b["id"] == BINDING_ID)
    next(t for t in binding["targets"] if t["kind"] == "operator")[field] = "0" * 64
    with pytest.raises(ValueError, match="reviewed .*stale"):
        build_formula_bindings(seeds)


@pytest.mark.parametrize("mutation", [
    "operator_uid", "formula_sha", "node_uid", "definition", "source", "source_hash",
    "definition_source", "extra_operator", "extra_node",
])
def test_response_unit_contract_guard_rejects_endpoint_drift(synthetic_contract, mutation):
    root, contract = synthetic_contract
    if mutation == "operator_uid":
        contract["operators"][0]["uid"] = "0" * 64
    elif mutation == "formula_sha":
        contract["operators"][0]["formula_sha256"] = "0" * 64
    elif mutation == "node_uid":
        contract["nodes"][0]["uid"] = "0" * 64
    elif mutation == "definition":
        contract["operators"][0]["lean_definition"] = "Invented.Response.heatCapacityPIdentity"
    elif mutation == "source":
        contract["source_path"] = "lean/bridge/OMAIPhyslibResponseCalculus.lean"
    elif mutation == "source_hash":
        contract["source_sha256"] = "0" * 64
    elif mutation == "definition_source":
        contract["operators"][0]["definition_source_path"] = "lean/bridge/OMAIPhyslibContinuum.lean"
    elif mutation == "extra_operator":
        contract["operators"].append(copy.deepcopy(contract["operators"][0]))
    elif mutation == "extra_node":
        contract["nodes"].append({"id": "Temperature", "uid": "0" * 64})
    else:
        raise AssertionError(mutation)
    with pytest.raises(AssertionError):
        _assert_response_contract(contract, root)


def test_response_unit_phonopy_notes_preserve_ids_and_representation_projections():
    import omai.quasiharmonic.representation as package
    import omai.quasiharmonic.representation.phonopy as module
    from omai.index_data import _index_docs
    from omai.map_data import DOMAINS, build_codes, build_graph_dict, build_registry
    from omai.representation.adapter import representation_to_operator
    from omai.semantics import build_semantics

    old_space = module.PHONOPY_THERMAL_GRUNEISEN
    old_operator = module.PHONOPY_CONTRACT_THERMAL_GRUNEISEN
    # This invariant tests exclusion of notes from IDs, not correctness of this prose.
    space = replace(old_space, notes=old_space.notes + " Notes-only regression fixture.")
    operator = replace(old_operator, notes=old_operator.notes + " Notes-only regression fixture.")
    for old, new in ((old_space, space), (old_operator, operator)):
        assert old != new  # Dataclass equality is NOT the scientific content identity.
        assert all(getattr(old, f.name) == getattr(new, f.name)
                   for f in fields(old) if f.name != "notes")
    assert representation_to_operator(space, "gamma_thermal") == 1
    builders = {
        "inventory": catalog_inventory, "graph": lambda: build_graph_dict(DOMAINS),
        "codes": lambda: build_codes(DOMAINS), "index": lambda: _index_docs(DOMAINS),
        "registry": build_registry,
        "semantics": lambda: build_semantics(build_graph_dict(DOMAINS)),
        "formula_bindings": build_formula_bindings,
    }
    before = {key: builder() for key, builder in builders.items()}
    with ExitStack() as stack:
        for mod in (module, package):
            stack.enter_context(patch.object(mod, "PHONOPY_THERMAL_GRUNEISEN", space))
            stack.enter_context(patch.object(mod, "PHONOPY_CONTRACT_THERMAL_GRUNEISEN", operator))
        assert {key: builder() for key, builder in builders.items()} == before
    assert module.PHONOPY_THERMAL_GRUNEISEN is old_space
    assert module.PHONOPY_CONTRACT_THERMAL_GRUNEISEN is old_operator


def test_response_record_copy_is_accepted(evidence_copy):
    _check_compiled_evidence(evidence_copy.binding, evidence_copy.upstream, evidence_copy.root)


@pytest.mark.parametrize("mutation", [
    *(f"old_revision:{revision}" for revision in PREVIOUS_REVISIONS),
    "failed_build", "wrong_command", "wrong_toolchain", "missing_source_hash",
    "binding_source_hash", "binding_module", "record_primary_source_hash",
    "unrecorded_helper", "proof_bytes", "contract_bytes", "audit_bytes", "verifier_bytes",
    "missing_pair_audit", "failed_pair_audit", "missing_pair", "duplicate_pair", "wrong_owner",
    "wrong_pair_count", "missing_axiom_audit", "failed_axiom_audit", "unapproved_axiom",
    "missing_advertised_declaration", "wrong_declaration_count", "zero_theorem_count",
    *(f"wrong_dependencies:{revision}" for revision in PREVIOUS_REVISIONS), "missing_file",
])
def test_response_record_consumer_refuses_provenance_drift(evidence_copy, mutation):
    data = evidence_copy
    record = data.record
    if mutation.startswith("old_revision:"):
        record["upstream_revision"] = mutation.partition(":")[2]
    elif mutation == "failed_build":
        record["status"] = "failed"
    elif mutation == "wrong_command":
        record["command"] = "lake build"
    elif mutation == "wrong_toolchain":
        record["lean_toolchain"] = "leanprover/lean4:v4.31.0"
    elif mutation == "missing_source_hash":
        del record["sources"]["lean/bridge/audit.py"]
    elif mutation == "binding_source_hash":
        data.binding["evidence"]["source_sha256"] = "0" * 64
    elif mutation == "binding_module":
        data.binding["evidence"]["module"] = "OMAIPhyslibContinuum"
    elif mutation == "record_primary_source_hash":
        record["sources"][data.binding["evidence"]["source_path"]] = "0" * 64
    elif mutation == "unrecorded_helper":
        (data.root / "lean/bridge/UnrecordedHelper.lean").write_text("-- unrecorded\n")
    elif mutation in {"proof_bytes", "contract_bytes", "audit_bytes", "verifier_bytes"}:
        relative = {
            "proof_bytes": "lean/bridge/OMAIPhyslibContinuum.lean",
            "contract_bytes": "lean/bridge/harmonic-product-formula-contract.json",
            "audit_bytes": "lean/bridge/audit.py",
            "verifier_bytes": "lean/bridge/verify_contracts.py",
        }[mutation]
        file = data.root / relative
        file.write_bytes(file.read_bytes() + b"\n")
    elif mutation == "missing_pair_audit":
        del record["contract_name_audit"]
    elif mutation == "failed_pair_audit":
        record["contract_name_audit"]["status"] = "failed"
    elif mutation == "missing_pair":
        record["contract_name_audit"]["pairs"].pop()
        record["contract_name_audit"]["pair_count"] -= 1
    elif mutation == "duplicate_pair":
        record["contract_name_audit"]["pairs"].append(
            copy.deepcopy(record["contract_name_audit"]["pairs"][0]))
        record["contract_name_audit"]["pair_count"] += 1
    elif mutation == "wrong_owner":
        record["contract_name_audit"]["pairs"][0]["module"] = "OMAIPhyslibContinuum"
    elif mutation == "wrong_pair_count":
        record["contract_name_audit"]["pair_count"] += 1
    elif mutation == "missing_axiom_audit":
        del record["axiom_audit"]
    elif mutation == "failed_axiom_audit":
        record["axiom_audit"]["status"] = "failed"
    elif mutation == "unapproved_axiom":
        name = data.binding["evidence"]["declarations"][0]
        record["axiom_audit"]["declarations"][name].append("sorryAx")
    elif mutation == "missing_advertised_declaration":
        del record["axiom_audit"]["declarations"][data.binding["evidence"]["declarations"][0]]
        record["axiom_audit"]["declaration_count"] -= 1
    elif mutation == "wrong_declaration_count":
        record["axiom_audit"]["declaration_count"] += 1
    elif mutation == "zero_theorem_count":
        record["axiom_audit"]["theorem_count"] = 0
    elif mutation.startswith("wrong_dependencies:"):
        record["dependencies"]["physlib"] = mutation.partition(":")[2]
    elif mutation == "missing_file":
        (data.root / "lean/bridge/harmonic-product-formula-contract.json").unlink()
    else:
        raise AssertionError(mutation)
    data.record_path.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        _check_compiled_evidence(data.binding, data.upstream, data.root)


class _ReachedCompiler(Exception):
    """Sentinel: the temporary pre-build gate passed; no compiler/writer ran."""


def _temporary_required_contract_gate(tmp_path, monkeypatch, missing=None):
    module = _load_module("response_required_contract_gate", "audit.py")
    root = tmp_path / "repo"
    package = root / "lean/bridge"
    package.mkdir(parents=True)
    # Contents are deliberately synthetic: only the missing-file preflight is exercised.
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


def test_response_unit_required_contract_preflight_reaches_sentinel_when_complete(tmp_path, monkeypatch):
    module, package = _temporary_required_contract_gate(tmp_path, monkeypatch)
    with pytest.raises(_ReachedCompiler):
        module.run()
    assert not (package / "build-evidence.json").exists()


@pytest.mark.parametrize("missing", sorted(REQUIRED_CONTRACTS))
def test_response_required_contract_deletion_refused_before_subprocess(tmp_path, monkeypatch, missing):
    module, package = _temporary_required_contract_gate(tmp_path, monkeypatch, missing)
    with pytest.raises(ValueError, match=r"reviewed formula contracts are missing:.*" + re.escape(missing)):
        module.run()
    assert not (package / "build-evidence.json").exists()


def test_response_integration_contract_is_exact_and_reviewed(response_contract):
    _assert_response_contract(response_contract)


def test_response_integration_unique_delta_and_binding_declarations(response_payload):
    _assert_current_scope(response_payload)
    binding = _response_binding(response_payload)
    evidence = binding["evidence"]
    assert evidence["module"] == MODULE and evidence["source_path"] == SOURCE
    assert set(evidence["declarations"]) == FINAL_THEOREMS
    assert not WITNESS_THEOREMS.intersection(evidence["declarations"])
    assert all(t["id"] != "compute_heat_capacity_p" for t in evidence["proved_targets"])
    assert binding["conditions"] and binding["remaining_obligations"]
    assert all(binding["conventions"].values())


def test_response_integration_current_record_covers_all_sources(response_payload, response_contract):
    from omai.physlib_dimensions import PHYSLIB_REV

    validate_formula_bindings(response_payload, check_catalog=True, proof_root=ROOT)
    record = _load_json(PACKAGE / "build-evidence.json")
    manifest = _load_json(PACKAGE / "lake-manifest.json")
    dependencies = {p["name"].lower(): p["rev"] for p in manifest["packages"]}
    lakefile = tomllib.loads((PACKAGE / "lakefile.toml").read_text())
    direct = next(p for p in lakefile["require"] if p["name"].lower() == "physlib")
    assert direct["rev"] == dependencies["physlib"] == record["upstream_revision"] == REVISION
    assert response_payload["upstream"]["revision"] == PHYSLIB_REV == REVISION
    assert _load_json(ROOT / "docs/data/physlib_dimensions.json")["physlib_rev"] == REVISION
    assert (PACKAGE / "lean-toolchain").read_text().strip() == TOOLCHAIN
    assert NEW_SOURCES <= record["sources"].keys()
    assert {"lean/bridge/" + name for name in REQUIRED_CONTRACTS} <= record["sources"].keys()
    expected_pairs = sorted([*BASELINE_PAIRS, {"name": DEFINITION, "module": MODULE}, GAMMA_PAIR, *LATER_PAIRS],
                            key=lambda row: (row["name"], row["module"]))
    assert record["contract_name_audit"] == {
        "status": "passed", "pair_count": len(expected_pairs), "pairs": expected_pairs,
    }
    source_modules = sorted(
        ".".join(path.relative_to(PACKAGE).with_suffix("").parts)
        for path in PACKAGE.glob("*.lean")
    )
    assert record["axiom_audit"]["scope"] == "source_modules_union_namespace_v1"
    assert record["axiom_audit"]["source_modules"] == source_modules
    assert record["axiom_audit"]["namespace_prefix"] == "OMAI.PhyslibBridge"
    assert FINAL_THEOREMS | WITNESS_THEOREMS <= record["axiom_audit"]["declarations"].keys()


@pytest.mark.parametrize("relative", sorted(NEW_SOURCES | {"lean/bridge/" + CONTRACT_NAME}))
def test_response_integration_consumer_rejects_changed_new_source(response_payload, evidence_copy, relative):
    data = evidence_copy
    assert relative in data.record["sources"], f"integration pending: unrecorded {relative}"
    path = data.root / relative
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError):
        _check_compiled_evidence(_response_binding(response_payload), data.upstream, data.root)


def test_response_integration_reproducibility_and_exact_reverse_lookup(response_payload, tmp_path, monkeypatch):
    text = json.dumps(response_payload, indent=2, ensure_ascii=False) + "\n"
    assert (ROOT / "omai/data/formula_bindings.json").read_text() == text
    assert (ROOT / "docs/data/formula_bindings.json").read_text() == text
    assert build_formula_bindings() == response_payload
    binding = _response_binding(response_payload)
    monkeypatch.chdir(tmp_path)
    assert binding in formula_bindings_for(OPERATOR, kind="operator")
    for source in binding["sources"]:
        rows = formula_bindings_for_physlib(declaration=source["name"], module=source["module"])
        assert binding in rows
        matching = next(row for row in rows if row["id"] == BINDING_ID)
        matching["conditions"].append("isolated caller mutation")
        fresh = formula_bindings_for_physlib(declaration=source["name"], module=source["module"])
        assert all("isolated caller mutation" not in row["conditions"] for row in fresh)


def _configured_compiled_package():
    configured = os.environ.get("PHYSLIB_BRIDGE_PACKAGE")
    if not configured:
        pytest.skip("optional real-compiler check: set PHYSLIB_BRIDGE_PACKAGE to the built package")
    package = Path(configured).resolve()
    manifest = _load_json(package / "lake-manifest.json")
    assert next(p["rev"] for p in manifest["packages"]
                if p["name"].lower() == "physlib") == REVISION, "wrong compiled-package pin"
    assert (package / "lean-toolchain").read_text().strip() == TOOLCHAIN
    return package


@pytest.fixture(scope="module")
def compiled_package():
    return _configured_compiled_package()


@pytest.fixture(scope="module")
def response_compiled_package(response_contract):
    # First require the real frozen artifact; optional compiler opt-in must not
    # hide an absent response contract behind an environment-based skip.
    return _configured_compiled_package()


def _verify_strict(paths, package):
    """Use the real existing verifier; add warnings-as-errors to its real command."""
    verifier = _load_module("response_strict_contract_verifier", "verify_contracts.py")
    real_run = subprocess.run

    def strict_run(command, **kwargs):
        assert command[:5] == ["lake", "--no-build", "env", "lean", "-j2"]
        assert kwargs["env"]["LEAN_NUM_THREADS"] == "2"
        assert kwargs["env"]["MATHLIB_NO_CACHE_ON_UPDATE"] == "1"
        assert kwargs["timeout"] == verifier._probe_timeout()
        return real_run([*command[:5], "-DwarningAsError=true", *command[5:]], **kwargs)

    verifier.subprocess = SimpleNamespace(run=strict_run, TimeoutExpired=subprocess.TimeoutExpired)
    return verifier.verify_compiled_contract_names(paths, package)


def test_response_real_current_baseline_contract_names(compiled_package):
    pairs = _verify_strict([compiled_package / name for name in LEGACY_CONTRACT_HASHES], compiled_package)
    assert pairs == BASELINE_PAIRS


@pytest.mark.parametrize("mutation,diagnostic", [
    ("namespace", "Contract declaration is absent: InventedOMAI"),
    ("owner", "belongs to OMAIPhyslibSemantics, not OMAIPhyslibContinuum"),
])
def test_response_real_baseline_provenance_negatives(compiled_package, tmp_path, mutation, diagnostic):
    contract = _load_json(compiled_package / "semantic-formula-contract.json")
    if mutation == "namespace":
        contract["operators"][0]["lean_definition"] = "InventedOMAI.PhyslibBridge.harmonicEntropy"
    else:
        contract["operators"][0]["definition_source_path"] = "lean/bridge/OMAIPhyslibContinuum.lean"
    with pytest.raises(ValueError, match=diagnostic):
        _verify_strict([_write_contract(tmp_path, contract)], compiled_package)


def test_response_real_final_endpoint(response_compiled_package):
    package = response_compiled_package
    pairs = _verify_strict([package / name for name in sorted(CP_ERA_CONTRACTS)], package)
    assert len(pairs) == 14
    assert {"name": DEFINITION, "module": MODULE} in pairs


@pytest.mark.parametrize("mutation,diagnostic", [
    ("namespace", "Contract declaration is absent: InventedOMAI"),
    ("owner", "belongs to OMAIPhyslibHarmonicResponse, not OMAIPhyslibContinuum"),
])
def test_response_real_final_provenance_negatives(response_compiled_package, response_contract, tmp_path,
                                                  mutation, diagnostic):
    contract = copy.deepcopy(response_contract)
    if mutation == "namespace":
        contract["operators"][0]["lean_definition"] = "InventedOMAI.Response.heatCapacityPIdentity"
    else:
        contract["operators"][0]["definition_source_path"] = "lean/bridge/OMAIPhyslibContinuum.lean"
    with pytest.raises(ValueError, match=diagnostic):
        _verify_strict([_write_contract(tmp_path, contract)], response_compiled_package)


def test_response_real_witness_ownership_separate_from_final_binding(response_compiled_package, tmp_path):
    # A temporary name-provenance probe, not another reviewed formula contract/binding.
    contract = {
        "source_path": "lean/bridge/OMAIPhyslibResponseWitness.lean",
        "nodes": [{"id": "witness-name-probe", "lean_definition": name}
                  for name in sorted(WITNESS_THEOREMS)],
    }
    pairs = _verify_strict([_write_contract(tmp_path, contract)], response_compiled_package)
    assert pairs == [{"name": name, "module": "OMAIPhyslibResponseWitness"}
                     for name in sorted(WITNESS_THEOREMS)]


def _typed_response_consumer_source():
    """Modern public consumer: actual models/branches, not declaration-name checks."""
    return """module
import OMAIPhyslibHarmonicResponse
set_option autoImplicit false
open OMAI.PhyslibBridge OMAI.PhyslibBridge.Response

example (A : ℝ) (hA : 0 < A) :
    ∃ B : StableBranchAt (nonzeroModel A hA).freeEnergy (nonzeroModel A hA).domain 0 1,
      B.volume 1 = A ∧ (1, A) ∈ (nonzeroModel A hA).domain ∧
        0 < FVV (nonzeroModel A hA).freeEnergy (1, A) ∧
        0 < expansion B.volume 1 ∧
        (nonzeroModel A hA).cv (1, A) < (nonzeroModel A hA).actualCp 0 B.volume 1 ∧
        (nonzeroModel A hA).actualCp 0 B.volume 1 =
          heatCapacityPIdentity ((nonzeroModel A hA).cv (1, A)) 1 A
            (expansion B.volume 1) (bulk (nonzeroModel A hA).freeEnergy (1, A)) := by
  obtain ⟨B, hV, hAlpha, hGap⟩ := nonzero_expansion_witness A hA
  refine ⟨B, hV, ?_, ?_, hAlpha, hGap, ?_⟩
  · simpa only [hV] using B.in_domain
  · simpa only [hV] using B.stable
  · simpa only [hV] using harmonic_static_heatCapacityP_eq_omai (nonzeroModel A hA) 0 1 B

example (A : ℝ) (hA : 0 < A) :
    ∃ B : StableBranchAt (zeroModel A hA).freeEnergy (zeroModel A hA).domain 0 1,
      B.volume 1 = A ∧ (1, A) ∈ (zeroModel A hA).domain ∧
        0 < FVV (zeroModel A hA).freeEnergy (1, A) ∧
        expansion B.volume 1 = 0 ∧
        (zeroModel A hA).actualCp 0 B.volume 1 = (zeroModel A hA).cv (1, A) ∧
        (zeroModel A hA).actualCp 0 B.volume 1 =
          heatCapacityPIdentity ((zeroModel A hA).cv (1, A)) 1 A
            (expansion B.volume 1) (bulk (zeroModel A hA).freeEnergy (1, A)) := by
  obtain ⟨B, hV, hAlpha, hEqual⟩ := zero_response_control A hA
  refine ⟨B, hV, ?_, ?_, hAlpha, hEqual, ?_⟩
  · simpa only [hV] using B.in_domain
  · simpa only [hV] using B.stable
  · simpa only [hV] using harmonic_static_heatCapacityP_eq_omai (zeroModel A hA) 0 1 B

example (Cv T Vm alpha K : ℝ) :
    heatCapacityPIdentity Cv T Vm alpha K = Cv + T * Vm * alpha ^ 2 * K := rfl

example (M : HarmonicVolumeModel) (p t : ℝ)
    (B : StableBranchAt M.freeEnergy M.domain p t) :
    M.actualCp p B.volume t =
      heatCapacityPIdentity (M.cv (t, B.volume t)) t (B.volume t)
        (expansion B.volume t) (bulk M.freeEnergy (t, B.volume t)) :=
  harmonic_static_heatCapacityP_eq_omai M p t B

example (M : HarmonicVolumeModel) (p t : ℝ)
    (B : StableBranchAt M.freeEnergy M.domain p t) :
    M.cv (t, B.volume t) ≤ M.actualCp p B.volume t :=
  harmonic_static_heatCapacityP_ge_heatCapacityV M p t B

example (M : HarmonicVolumeModel) {t v : ℝ} (ht : 0 < t) (hv : v ∈ M.J) :
    FV M.freeEnergy (t, M.reference.avogadro * v) = deriv (M.cellFreeEnergy t) v :=
  M.FV_eq_cell_deriv ht hv

example (M : HarmonicVolumeModel) {t v : ℝ} (ht : 0 < t) (hv : v ∈ M.J) :
    bulk M.freeEnergy (t, M.reference.avogadro * v) =
      v * deriv (deriv (M.cellFreeEnergy t)) v :=
  M.bulk_eq_cell_bulk ht hv
"""


def _typed_response_negative_source(case):
    header = ("module\nimport OMAIPhyslibHarmonicResponse\nset_option autoImplicit false\n"
              "open OMAI.PhyslibBridge OMAI.PhyslibBridge.Response\n")
    if case == "wrong_model":
        return header + """
example (A : ℝ) (hA : 0 < A) :
    ∃ B : StableBranchAt (zeroModel A hA).freeEnergy (zeroModel A hA).domain 0 1,
      B.volume 1 = A ∧ 0 < expansion B.volume 1 ∧
        (zeroModel A hA).cv (1, A) < (zeroModel A hA).actualCp 0 B.volume 1 :=
  nonzero_expansion_witness A hA
"""
    if case == "wrong_bulk_scale":
        return header + """
example (M : HarmonicVolumeModel) {t v : ℝ} (ht : 0 < t) (hv : v ∈ M.J) :
    bulk M.freeEnergy (t, M.reference.avogadro * v) =
      M.reference.avogadro * v * deriv (deriv (M.cellFreeEnergy t)) v :=
  M.bulk_eq_cell_bulk ht hv
"""
    raise AssertionError(case)


def _check_typed_response_source(package, tmp_path, text):
    # No private-build search paths: these committed tests consume the selected
    # canonical package. A separate private preflight is not a canonical pass.
    with TemporaryDirectory(prefix="response-typed-", dir=tmp_path) as temporary:
        directory = Path(temporary)
        source = directory / "ResponseTypedConsumer.lean"
        source.write_text(text)
        return _run_scope_lean(package, directory, source)


def test_response_real_typed_actual_witnesses_and_endpoint(response_compiled_package, tmp_path):
    result = _check_typed_response_source(
        response_compiled_package, tmp_path, _typed_response_consumer_source())
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("case,expected_term", [
    ("wrong_model", "nonzero_expansion_witness"),
    ("wrong_bulk_scale", "bulk_eq_cell_bulk"),
])
def test_response_real_typed_model_and_scale_negatives(
    response_compiled_package, tmp_path, case, expected_term,
):
    result = _check_typed_response_source(
        response_compiled_package, tmp_path, _typed_response_negative_source(case))
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "type mismatch" in output.lower(), output
    assert expected_term in output, output
    assert not any(message in output.lower()
                   for message in ("unknown module", "unknown identifier", "unknown constant")), output


@pytest.fixture(scope="module")
def axiom_audit_api():
    # Import only the parent's pure production seam; never call its build/writer.
    return _load_module("response_axiom_scope_api", "audit.py")


def _synthetic_axiom_output():
    """Parser-only input; not generated or published proof evidence."""
    modules = ["ResponseAuditFixture", "ResponseAuditImported"]
    lines = [
        *("OMAI_AXIOM_MODULE|" + name for name in modules),
        "OMAI_AXIOMS|theorem|OMAI.PhyslibBridge.scopeAuditSentinel|",
        "OMAI_AXIOMS|definition|globalScopeValue|propext",
        "OMAI_AXIOM_SCOPE_OK|2|2",
    ]
    return modules, lines


def test_response_unit_axiom_parser_accepts_complete_scope(axiom_audit_api):
    modules, lines = _synthetic_axiom_output()
    result = axiom_audit_api.parse_axiom_output("\n".join(lines), source_modules=modules[::-1])
    assert result == {
        "status": "passed", "theorem_count": 1, "declaration_count": 2,
        "allowed_axioms": ["Classical.choice", "Quot.sound", "propext"],
        "declarations": {"OMAI.PhyslibBridge.scopeAuditSentinel": [],
                         "globalScopeValue": ["propext"]},
        "scope": "source_modules_union_namespace_v1", "source_modules": modules,
        "namespace_prefix": "OMAI.PhyslibBridge",
    }


@pytest.mark.parametrize("mutation,diagnostic", [
    ("missing_module", "source-module markers"),
    ("duplicate_module", "source-module markers"),
    ("wrong_module", "source-module markers"),
    ("extra_module", "source-module markers"),
    ("reversed_modules", "source-module markers"),
    ("malformed_module", "source-module markers"),
    ("missing_completion", "scope-completion marker"),
    ("duplicate_completion", "scope-completion marker"),
    ("malformed_completion", "scope-completion marker"),
    ("wrong_module_count", "completion counts"),
    ("wrong_declaration_count", "completion counts"),
    ("missing_declaration", "completion counts"),
    ("duplicate_declaration", "duplicates declarations"),
    ("unknown_declaration_kind", "malformed"),
    ("extra_malformed_declaration", "malformed"),
    ("no_theorem", "output is empty"),
    ("no_declarations", "output is empty"),
    ("unapproved_axiom", "unapproved transitive axioms"),
    ("private_unapproved_axiom", "unapproved transitive axioms"),
])
def test_response_unit_axiom_parser_rejects_incomplete_or_unsafe_output(
    axiom_audit_api, mutation, diagnostic,
):
    modules, lines = _synthetic_axiom_output()
    if mutation == "missing_module":
        del lines[1]
    elif mutation == "duplicate_module":
        lines.insert(1, lines[0])
    elif mutation == "wrong_module":
        lines[1] = "OMAI_AXIOM_MODULE|WrongModule"
    elif mutation == "extra_module":
        lines.insert(2, "OMAI_AXIOM_MODULE|UnrequestedModule")
        lines[-1] = "OMAI_AXIOM_SCOPE_OK|3|2"
    elif mutation == "reversed_modules":
        lines[:2] = lines[:2][::-1]
    elif mutation == "malformed_module":
        lines[1] += "|unexpected"
    elif mutation == "missing_completion":
        lines.pop()
    elif mutation == "duplicate_completion":
        lines.append(lines[-1])
    elif mutation == "malformed_completion":
        lines[-1] = "OMAI_AXIOM_SCOPE_OK|not-a-count|2"
    elif mutation == "wrong_module_count":
        lines[-1] = "OMAI_AXIOM_SCOPE_OK|3|2"
    elif mutation == "wrong_declaration_count":
        lines[-1] = "OMAI_AXIOM_SCOPE_OK|2|3"
    elif mutation == "missing_declaration":
        del lines[3]
    elif mutation == "duplicate_declaration":
        lines[3] = lines[2]
    elif mutation == "unknown_declaration_kind":
        lines[3] = lines[3].replace("|definition|", "|axiom|")
    elif mutation == "extra_malformed_declaration":
        lines.insert(3, "OMAI_AXIOMS|unparseable")
    elif mutation == "no_theorem":
        lines[2] = lines[2].replace("|theorem|", "|definition|")
    elif mutation == "no_declarations":
        del lines[2:4]
    elif mutation == "unapproved_axiom":
        lines[3] += ",sorryAx"
    elif mutation == "private_unapproved_axiom":
        name = "_private.ResponseAuditFixture.0.hiddenScopeAssumption"
        lines.insert(4, f"OMAI_AXIOMS|definition|{name}|{name}")
        lines[-1] = "OMAI_AXIOM_SCOPE_OK|2|3"
    else:
        raise AssertionError(mutation)
    with pytest.raises(ValueError, match=diagnostic):
        axiom_audit_api.parse_axiom_output("\n".join(lines), source_modules=modules)


@pytest.mark.parametrize("field", ["imports", "source_modules"])
@pytest.mark.parametrize("invalid", [[], ["Same", "Same"], ["Bad\n#eval 1"], ("NotAList",)])
def test_response_unit_axiom_probe_rejects_unsafe_module_arguments(axiom_audit_api, field, invalid):
    arguments = {"imports": ["ResponseAuditFixture"], "source_modules": ["ResponseAuditFixture"]}
    arguments[field] = invalid
    with pytest.raises(ValueError):
        axiom_audit_api.axiom_probe_source(**arguments)
    if field == "source_modules":
        with pytest.raises(ValueError):
            axiom_audit_api.parse_axiom_output("", source_modules=invalid)


def _run_scope_lean(package, directory, source, *arguments):
    """Real isolated compile/probe, with the fixture path added inside Lake's env."""
    assert source.resolve().is_relative_to(directory.resolve())
    environment = os.environ.copy()
    environment.update(LEAN_NUM_THREADS="2", MATHLIB_NO_CACHE_ON_UPDATE="1")
    command = [
        "lake", "--no-build", "env", "bash", "-c",
        'export LEAN_PATH="$1${LEAN_PATH:+:$LEAN_PATH}"; shift; '
        'exec lean -j2 -DwarningAsError=true "$@"',
        "response-audit-fixture", str(directory), f"--root={directory}",
        *arguments, str(source),
    ]
    return subprocess.run(command, cwd=package, env=environment, text=True,
                          capture_output=True, check=False,
                          timeout=_load_module("response_probe_timeout", "verify_contracts.py")._probe_timeout())


def _compile_scope_fixture(package, directory, module, text):
    source = directory / (module + ".lean")
    source.write_text(text)
    result = _run_scope_lean(package, directory, source, "-o", str(source.with_suffix(".olean")))
    assert result.returncode == 0, "Fixture failed before its audit:\n" + result.stdout + result.stderr
    assert source.with_suffix(".olean").is_file()
    assert source.with_suffix(".olean.private").is_file()


@pytest.mark.parametrize("case", ["benign", "private", "global", "missing_module", "namespace_fallback"])
def test_response_real_axiom_scope(axiom_audit_api, compiled_package, tmp_path, case):
    """Exercise production selection/parser, never a cloned audit or the writer."""
    with TemporaryDirectory(prefix="response-axiom-", dir=tmp_path) as temporary:
        directory = Path(temporary)
        module = "ResponseAuditFixture"
        sentinel = "OMAI.PhyslibBridge.scopeAuditSentinel"
        header = "module\n"
        if case == "namespace_fallback":
            dependency = "ResponseAuditDependency"
            _compile_scope_fixture(compiled_package, directory, dependency, "module\n"
                                   "public axiom OMAI.PhyslibBridge.scopeFallbackAssumption : False\n")
            header += "public import " + dependency + "\n"
        body = f"public theorem {sentinel} : True := True.intro\n"
        if case == "private":
            body += ("private axiom hiddenScopeAssumption : False\n"
                     "private theorem hiddenScopeUse : False := hiddenScopeAssumption\n")
        elif case == "global":
            body += ("public axiom globalScopeAssumption : False\n"
                     "public theorem globalScopeUse : False := globalScopeAssumption\n")
        else:
            body += ("private theorem scopePrivateTrue : True := True.intro\n"
                     "public def globalScopeValue : Nat := 7\n")
        _compile_scope_fixture(compiled_package, directory, module, header + body)
        modules = [module]
        if case == "missing_module":
            missing = "ResponseAuditUnimported"
            _compile_scope_fixture(compiled_package, directory, missing,
                                   "module\npublic def unimportedValue : Nat := 3\n")
            modules.append(missing)  # Compiled and available, deliberately not imported.
        generated = axiom_audit_api.axiom_probe_source(imports=[module], source_modules=modules)
        probe = directory / "ScopeProbe.lean"
        probe.write_text(generated)
        result = _run_scope_lean(compiled_package, directory, probe)
        output = result.stdout + result.stderr
        if case == "missing_module":
            assert result.returncode != 0
            assert "Missing audited source module: ResponseAuditUnimported" in output
            assert "OMAI_AXIOM_SCOPE_OK|" not in output
            return
        assert result.returncode == 0, "Production scope probe failed:\n" + output
        rows = [line.split("OMAI_AXIOMS|", 1)[1].split("|", 2)
                for line in output.splitlines() if "OMAI_AXIOMS|" in line]
        names = {row[1] for row in rows}
        assert sentinel in names
        if case == "benign":
            audit = axiom_audit_api.parse_axiom_output(output, source_modules=modules)
            private = [name for name in names if name.startswith("_private.")
                       and name.endswith(".scopePrivateTrue")]
            assert len(private) == 1 and audit["declarations"][private[0]] == []
            assert audit["declarations"]["globalScopeValue"] == []
            assert audit["scope"] == "source_modules_union_namespace_v1"
            assert audit["source_modules"] == modules
            assert audit["namespace_prefix"] == "OMAI.PhyslibBridge"
            assert audit["declaration_count"] == len(names)
        else:
            poison = {"private": "hiddenScopeAssumption", "global": "globalScopeAssumption",
                      "namespace_fallback": "scopeFallbackAssumption"}[case]
            assert any(name.endswith(poison) for name in names)
            with pytest.raises(ValueError, match="unapproved transitive axioms.*" + poison):
                axiom_audit_api.parse_axiom_output(output, source_modules=modules)
            if case in {"private", "global"}:
                # The old namespace-only selector would see a clean sentinel,
                # so rejection genuinely tests the added module-origin branch.
                old_rows = [row for row in rows if row[1].startswith("OMAI.PhyslibBridge.")]
                assert old_rows == [["theorem", sentinel, ""]]
                if case == "private":
                    assert any(name.startswith("_private.") and name.endswith(poison)
                               for name in names)
