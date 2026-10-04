"""The evidence resolver (omai/evidence.py): kinds, model identity, roots."""
from __future__ import annotations

import hashlib
import json

import pytest

from omai.evidence import EvidenceError, check, model_uid, resolve

A = hashlib.sha256(b"a").hexdigest()
B = hashlib.sha256(b"b").hexdigest()


def _model(**over):
    record = {"uid": A, "node": "Potential", "name": "fixture", "family": "nep",
              "format": "nep.txt", "elements": ["O", "Si"],
              "files": [{"path": "a.txt", "role": "model", "sha256": A,
                         "bytes": 1}],
              "license": {"spdx": "NOASSERTION", "license_source": "none"},
              "citation": "fixture", "doi": None,
              "provenance": [{"kind": "repository", "ref": "x", "detail": ""}]}
    record.update(over)
    return record


def test_model_uid_is_the_file_digest_or_the_sorted_manifest_digest():
    assert model_uid([A]) == A
    manifest = json.dumps({"files": sorted([A, B])}, separators=(",", ":"))
    assert model_uid([B, A]) == hashlib.sha256(manifest.encode()).hexdigest()
    with pytest.raises(EvidenceError):
        model_uid([])


def test_check_reproduces_a_model_uid_and_ignores_training_state():
    state = {"path": "a.restart", "role": "training_state", "sha256": B, "bytes": 2}
    assert check("model", _model(files=_model()["files"] + [state]),
                 where="m") == A
    for bad in (_model(uid=B),
                _model(files=[{**_model()["files"][0], "role": "weights"}]),
                _model(elements=["Si", "O"]),
                _model(license={"spdx": "MIT"}),
                _model(uid="sha256:" + A),
                _model(uid=A + "\n"),
                _model(aliases=["not-a-uid"])):
        with pytest.raises(EvidenceError):
            check("model", bad, where="m")


def test_resolve_reads_data_directories_and_registry_files_in_order(tmp_path):
    (tmp_path / "data" / "models").mkdir(parents=True)
    (tmp_path / "data" / "models" / "fixture.json").write_text(json.dumps(_model()))
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"model": {B: "models/other.json"}}))
    roots = [tmp_path / "data", registry]
    assert resolve("model", A, roots) == "models/fixture.json"
    assert resolve("model", B, roots) == "models/other.json"
    assert resolve("model", "0" * 64, roots) is None
    assert resolve("configuration", A, roots) is None


def test_resolve_matches_a_former_uid_kept_as_an_alias(tmp_path):
    (tmp_path / "configurations").mkdir()
    record = {"canonical": {"uid": A, "aliases": [B]}}
    (tmp_path / "configurations" / "cell.json").write_text(json.dumps(record))
    assert check("configuration", record, where="c") == A
    for uid in (A, B):
        assert resolve("configuration", uid, [tmp_path]) == "configurations/cell.json"


def test_a_missing_root_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        resolve("model", A, [tmp_path / "registry.json"])


def test_committed_model_records_reproduce_their_uids():
    from omai.evidence import _DATA_DIR, records

    uids = {check("model", r, where=p) for p, r in records("model", _DATA_DIR)}
    # NEP89 (GPUMD v4.7) and Si.tersoff (the committed kaldo and phono3py
    # instances), re-read from the upstream files at registration.
    assert {"75168ece02e840e4a32644f982b78d43cba697f5b64b4c8134ab66c7a8c28be1",
            "52a93e90596829c57d54eef091de6215f1fac7ca15d57eac7568ddfdda26adfb"} <= uids
