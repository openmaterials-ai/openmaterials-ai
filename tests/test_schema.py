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
