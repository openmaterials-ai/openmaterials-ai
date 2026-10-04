"""Code releases: authored data, the registry, projections."""
from __future__ import annotations

import json

import pytest

from omai.evidence import (_DATA_DIR, REGISTRY, EvidenceError, check_releases,
                           code_releases, release_files)

_RELEASE = {"version": "1.0", "tag": "v1.0", "commit": "a" * 40,
            "released": "2026-01-01", "spdx": "MIT",
            "license_source": "https://example.org/x (LICENSE)"}


def test_check_releases_lists_every_representation_and_refuses_malformed_files():
    ok = {"x": {"aliases": ["x-code"], "releases": [_RELEASE]}}
    assert check_releases(ok, ["x", "y"]) == {
        "x": ok["x"], "y": {"aliases": [], "releases": []}}
    for files in ({"z": ok["x"]},
                  {"x": {"aliases": ["y"], "releases": [_RELEASE]}},
                  {"x": {"aliases": [], "releases": []}},
                  {"x": {"aliases": [], "releases": [{**_RELEASE, "commit": "abc"}]}},
                  {"x": {"aliases": [], "releases": [{**_RELEASE, "released": "2026"}]}},
                  {"x": {"aliases": [], "releases": [{**_RELEASE, "extra": "1"}]}},
                  {"x": {"aliases": [], "releases": [_RELEASE, {**_RELEASE, "tag": "t"}]}},
                  {"x": ok["x"], "y": {"aliases": ["x-code"], "releases": [_RELEASE]}},
                  {"x": {"aliases": [], "releases": [
                      _RELEASE, {**_RELEASE, "version": "v1.0", "commit": "b" * 40}]}}):
        with pytest.raises(EvidenceError):
            check_releases(files, ["x", "y"])


def test_releases_resolve_alike_from_the_source_tree_and_the_registry():
    tree, shipped = code_releases([_DATA_DIR]), code_releases([REGISTRY])
    assert tree == shipped
    assert set(tree) == set(json.loads((_DATA_DIR / "codes.json").read_text()))
    assert set(release_files(_DATA_DIR)) == {"gpumd", "kaldo", "lammps", "phono3py", "qe"}
    assert tree["qe"]["aliases"] == ["quantum-espresso"]
    assert tree["xtb"] == {"aliases": [], "releases": []}


def test_releases_project_into_the_index_and_codes_json(tmp_path):
    from omai.index_data import write_index

    write_index(tmp_path)
    qe = json.loads((tmp_path / "codes" / "qe.json").read_text())
    authored = release_files(_DATA_DIR)["qe"]
    assert (qe["aliases"], qe["releases"]) == (authored["aliases"], authored["releases"])
    assert "releases" not in json.loads((tmp_path / "codes" / "xtb.json").read_text())
    codes = json.loads((_DATA_DIR / "codes.json").read_text())
    assert all(entry["releases"] == authored["releases"] for entry in codes["qe"].values())


def test_write_index_removes_the_file_of_a_former_representation(tmp_path):
    from omai.index_data import write_index

    (tmp_path / "codes").mkdir()
    (tmp_path / "codes" / "gone.json").write_text("{}")
    write_index(tmp_path)
    assert not (tmp_path / "codes" / "gone.json").exists()
    assert (tmp_path / "codes" / "qe.json").exists()
