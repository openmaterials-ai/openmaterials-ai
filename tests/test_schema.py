"""The SimulationRecord JSON Schema accepts every real record and refuses the
shapes that would corrupt the commons.

The acceptance bar: every vector record validates (the schema cannot be
stricter than what the library itself writes), and the three named defects
(an unknown key, a missing node pin, a non-numeric value) are refused with a
message naming where they sit.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from omai.schema import simulation_record_schema, validate_record
from omai.tools import gen_vectors

VECTORS = Path(gen_vectors.__file__).resolve().parent.parent / "vectors"
RECORD_VECTORS = json.loads((VECTORS / "records.json").read_text())


def _light() -> dict:
    return copy.deepcopy(next(e for e in RECORD_VECTORS
                              if e["name"] == "mcg:safe_light")["record"])


def _heavy() -> dict:
    return copy.deepcopy(
        next(e for e in RECORD_VECTORS
             if e["name"] == "mcg:safe_light_with_artifacts")["record"])


@pytest.mark.parametrize("entry", RECORD_VECTORS,
                         ids=[e["name"] for e in RECORD_VECTORS])
def test_every_vector_record_validates(entry):
    assert validate_record(entry["record"]) == []


def test_the_schema_is_draft_2020_12_and_closed():
    schema = simulation_record_schema()
    assert schema["$schema"].endswith("2020-12/schema")
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["id", "lineage"]
    # A fresh dict per call: mutating one caller's copy must not reach another.
    schema["properties"].pop("id")
    assert "id" in simulation_record_schema()["properties"]


def test_an_extra_top_level_key_is_refused():
    record = _light()
    record["totally_new_field"] = 1
    errors = validate_record(record)
    assert errors, "an unknown top-level key must not pass"
    assert any("totally_new_field" in e for e in errors)


def test_an_extra_lineage_key_is_refused():
    record = _light()
    record["lineage"]["sneaky"] = "value"
    errors = validate_record(record)
    assert errors
    assert any("sneaky" in e for e in errors)


def test_a_missing_lineage_node_uid_is_accepted_but_a_malformed_one_is_not():
    # node_uid is the PIN, and a record may legitimately carry none (the
    # commons conformance targets do not). What must never pass is a node_uid
    # that is not a sha256: that is a pin nobody can check.
    record = _light()
    del record["lineage"]["node_uid"]
    assert validate_record(record) == []

    record = _light()
    record["lineage"]["node_uid"] = "not-a-digest"
    errors = validate_record(record)
    assert errors
    assert any("node_uid" in e for e in errors)


def test_a_configuration_pin_is_accepted_bare_and_sha256_prefixed():
    # lineages.py _validate_configuration accepts both spellings, so the schema
    # must not refuse either one.
    uid = "a" * 64
    for pin in (uid, f"sha256:{uid}"):
        record = _light()
        record["lineage"]["material"] = {"name": "Si", "configuration": pin}
        assert validate_record(record) == [], pin


def test_a_malformed_configuration_pin_is_refused():
    record = _light()
    record["lineage"]["material"] = {"name": "Si", "configuration": "sha256:xyz"}
    assert validate_record(record)


def test_a_legacy_recipe_keyed_record_is_out_of_scope_and_refused():
    # The schema describes CURRENT records. record_lineage still READS a
    # recipe-keyed record; validating one is a caller error, and the caller
    # normalizes first. Pinned so the scope stays a decision, not an accident.
    from omai.lineages import record_lineage

    record = _light()
    record["recipe"] = record.pop("lineage")
    assert record_lineage(record) is record["recipe"]
    assert validate_record(record)

    normalized = {**record, "lineage": record_lineage(record)}
    normalized.pop("recipe")
    assert validate_record(normalized) == []


def test_a_missing_lineage_node_is_refused():
    record = _light()
    del record["lineage"]["node"]
    errors = validate_record(record)
    assert errors
    assert any("node" in e for e in errors)


def test_a_non_numeric_result_value_is_refused():
    record = _heavy()
    record["results"][0]["value"] = "137.5"
    errors = validate_record(record)
    assert errors
    assert any("results" in e and "value" in e for e in errors)


def test_a_result_value_may_be_null_for_a_node_with_no_scalar():
    record = _heavy()
    record["results"][0]["value"] = None
    assert validate_record(record) == []


# --- execution.registry: the engine manifest's code rows (0.1.1) -----------
# 0.1.0 declared these as registry HOST strings and refused every record the
# platform serves. The regression that caught it is the proof record vector.

def _code_row(**over) -> dict:
    row = {"id": "gpumd", "name": "GPUMD", "spdx": "GPL-3.0-or-later",
           "license_source": "https://github.com/brucefan1983/GPUMD (LICENSE)",
           "source": "https://github.com/brucefan1983/GPUMD",
           "version": "3.9.5"}
    row.update(over)
    return row


def test_the_cut1_proof_record_validates():
    # The record the platform actually served for run_74cdf438f9e64a9bb90a.
    # This is the vector whose absence let the 0.1.0 defect ship.
    proof = next(e for e in RECORD_VECTORS
                 if e["name"] == "mcg:cut1_proof_run_903616ec")["record"]
    assert proof["id"] == (
        "903616ec0a2fc0ad6bbc59d90a24855d7eeaa6748a691b17b859d8ae0a6f3aa9")
    assert validate_record(proof) == []
    # It is the object shape that matters, not just that it passes.
    assert isinstance(proof["execution"]["registry"][0], dict)


def test_a_registry_code_row_validates():
    record = _light()
    record["execution"]["registry"] = [_code_row()]
    assert validate_record(record) == []


def test_a_registry_row_version_may_be_null():
    # A code pinned by digest alone has no version string to state.
    record = _light()
    record["execution"]["registry"] = [_code_row(version=None)]
    assert validate_record(record) == []


def test_a_registry_host_string_is_refused():
    # The 0.1.0 spelling. No producer emits it; accepting it would keep two
    # vocabularies alive in every consumer that validates.
    record = _light()
    record["execution"]["registry"] = ["ghcr.io/openmaterials-ai"]
    errors = validate_record(record)
    assert errors
    assert any("registry" in e for e in errors)


def test_a_registry_row_missing_a_key_is_refused():
    for missing in ("id", "name", "spdx", "license_source", "source",
                    "version"):
        row = _code_row()
        del row[missing]
        record = _light()
        record["execution"]["registry"] = [row]
        errors = validate_record(record)
        assert errors, f"a row without {missing!r} must be refused"
        assert any(missing in e for e in errors), (missing, errors)


def test_a_registry_row_with_an_extra_key_is_refused():
    record = _light()
    record["execution"]["registry"] = [_code_row(unexpected="x")]
    errors = validate_record(record)
    assert errors
    assert any("unexpected" in e for e in errors)


# --- results[].configuration (0.1.1) ---------------------------------------
# The worker's renderer emits it for a configuration-pinned run
# (record.ts kappaInstanceFrom); 0.1.0 closed results items without it.

def test_a_result_may_carry_a_configuration_pin():
    uid = "b" * 64
    for pin in (uid, f"sha256:{uid}"):
        record = _heavy()
        record["results"][0]["configuration"] = pin
        assert validate_record(record) == [], pin


def test_a_malformed_result_configuration_is_refused():
    record = _heavy()
    record["results"][0]["configuration"] = "not-a-uid"
    errors = validate_record(record)
    assert errors
    assert any("configuration" in e for e in errors)


def test_a_missing_id_is_refused():
    record = _light()
    del record["id"]
    assert validate_record(record)


def test_a_malformed_id_is_refused():
    record = _light()
    record["id"] = "abc"
    assert validate_record(record)


def test_an_execution_without_code_is_refused():
    record = _light()
    del record["execution"]["code"]
    errors = validate_record(record)
    assert errors
    assert any("code" in e for e in errors)


def test_an_artifact_without_a_role_is_refused():
    record = _heavy()
    del record["artifacts"][0]["role"]
    assert validate_record(record)


def test_a_backref_slug_result_is_accepted():
    record = _light()
    record["results"] = ["materialscodegraph-dgeba-cp300-gfn2"]
    assert validate_record(record) == []


def test_errors_name_where_they_sit():
    record = _heavy()
    record["results"][0]["value"] = "137.5"
    errors = validate_record(record)
    assert any(e.startswith("<record>.results[0].value") for e in errors), errors


def test_validation_is_order_stable():
    record = _light()
    record["totally_new_field"] = 1
    record["id"] = "abc"
    assert validate_record(record) == validate_record(record)
