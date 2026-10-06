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
                _model(aliases=["not-a-uid"]),
                _model(node="Structure")):
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


def _cited(node):
    """Every (key, value) under a citation key, at any depth of a JSON value."""
    from omai.evidence import CITATION_KEYS

    keys = {k for ks in CITATION_KEYS.values() for k in ks}
    if isinstance(node, dict):
        for key, value in node.items():
            if key in keys:
                yield key, value
            yield from _cited(value)
    elif isinstance(node, list):
        for value in node:
            yield from _cited(value)


def test_every_committed_model_citation_resolves():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    # omai/vectors/private.json cites fixture uids no registry holds, on purpose.
    files = [f for d in ("docs/data", "docs/examples", "omai", "tests/fixtures")
             for f in (root / d).rglob("*.json") if f.name != "private.json"]
    cited = {(k, v) for f in files for k, v in _cited(json.loads(f.read_text()))}
    assert cited, "the committed Si.tersoff instances cite potential_sha256"
    for key, uid in cited:
        assert resolve("model", uid) is not None, f"{key} {uid} is not registered"


def test_model_citations_reports_without_refusing():
    from omai.evidence import model_citations

    lineage = {"conditions": {"potential_sha256": A, "base_potential_sha256":
               "52a93e90596829c57d54eef091de6215f1fac7ca15d57eac7568ddfdda26adfb",
               "T": 300}}
    assert model_citations(lineage) == [
        {"key": "potential_sha256", "uid": A, "record": None},
        {"key": "base_potential_sha256", "uid": lineage["conditions"]
         ["base_potential_sha256"], "record": "models/si-tersoff.json"}]


def test_the_committed_registry_equals_a_fresh_build():
    from omai.evidence import REGISTRY
    from omai.map_data import build_registry

    assert json.loads(REGISTRY.read_text()) == build_registry(), (
        "omai/data/registry.json is stale: rebuild with python -m omai.map_data")


def test_the_registry_resolves_as_the_source_tree_does():
    from omai.evidence import KINDS, REGISTRY

    registry = json.loads(REGISTRY.read_text())
    assert registry["configuration"] and registry["model"]
    for kind in KINDS:
        for uid, path in registry[kind].items():
            assert resolve(kind, uid, [REGISTRY]) == path == resolve(kind, uid)


def test_the_former_si_uid_resolves_under_both_roots():
    from omai.evidence import _DATA_DIR, REGISTRY

    alias = "55bf22ca81868867402ac4ce50a830f91da84c805990c37c3bdafe3b93a69143"
    for root in (_DATA_DIR, REGISTRY):
        assert (resolve("configuration", alias, [root])
                == "configurations/si-diamond-primitive-mp-149.json")


def test_the_registry_ships_in_the_wheel():
    import tomllib
    from pathlib import Path

    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text())["tool"]["setuptools"]["package-data"]
    assert "data/*.json" in data["omai"]
