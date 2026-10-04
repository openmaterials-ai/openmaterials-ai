"""Code releases: authored data, the registry, projections, the release check."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from omai import lineages as lin
from omai.evidence import (_DATA_DIR, REGISTRY, EvidenceError, check_releases,
                           code_releases, release_files)

_VECTORS = Path(lin.__file__).resolve().parent / "vectors"
_RELEASE = {"version": "1.0", "tag": "v1.0", "commit": "a" * 40,
            "released": "2026-01-01", "spdx": "MIT",
            "license_source": "https://example.org/x (LICENSE)"}


def _rows(*pairs):
    return {"code": "x", "registry": [{"id": i, "version": v} for i, v in pairs]}


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
    assert set(release_files(_DATA_DIR)) == {"gpumd", "kaldo", "lammps", "phono3py", "qe",
                                             "qe-d3q"}
    assert tree["qe"]["aliases"] == ["quantum-espresso"]
    assert tree["xtb"] == {"aliases": [], "releases": []}


def test_the_backfill_registers_each_pair_under_its_exact_string():
    pinned = _rows(("gpumd", "3.9.5"), ("quantum-espresso", "qe-7.5"),
                   ("kaldo", "2.2.1"), ("phono3py", "4.4.0"),
                   ("lammps", "2025.7.22.4.0"))
    assert lin.release_check(pinned) == []
    assert lin.release_check(_rows(("gpumd", "v4.7"))) == [
        {"id": "gpumd", "version": "v4.7", "reason": "version not registered"}]


def _records():
    return {e["name"]: e["record"]
            for e in json.loads((_VECTORS / "records.json").read_text())}


def _light(record):
    """validate_light against the record's own node pin, not the live map,
    without its results (the served form carries no backref)."""
    lineage = record["lineage"]
    return lin.validate_light({k: v for k, v in record.items() if k != "results"},
                              name_to_uid={lineage["node"]: lineage.get("node_uid")})


def test_every_shipped_vector_row_resolves_or_waits_for_its_representation():
    rows = {(r["id"], r["version"]) for record in _records().values()
            for r in record.get("execution", {}).get("registry", [])}
    assert rows == {("gpumd", "3.9.5"), ("quantum-espresso", "qe-7.5"),
                    ("qe-d3q", "q-e-7.5")}
    assert lin.release_check(_rows(*rows)) == []


def _first(cites):
    """The first shipped record whose registry rows include a row of ``cites``."""
    return next(r for r in _records().values()
                if any(row["id"] == cites
                       for row in r.get("execution", {}).get("registry", [])))


def test_validate_light_reports_unresolved_rows_of_the_served_record():
    assert _light(_first("qe-d3q"))["unresolved_registry_rows"] == []
    assert _light(_first("gpumd"))["unresolved_registry_rows"] == []


def test_no_writer_refuses_an_unresolved_row(tmp_path):
    node = "ThermalConductivity[transport_model=hnemd]"
    name_to_uid = {node: "e" * 64}
    lineage = {"node": node, "node_uid": "e" * 64, "material": {"name": "Si"}}
    execution = _rows(("gpumd", "v4.7"), ("qe-d3q", "q-e-7.4"))
    record = lin.record_light(lineage=lineage, execution=execution,
                              name_to_uid=name_to_uid)
    assert len(lin.validate_light(record, name_to_uid=name_to_uid)
               ["unresolved_registry_rows"]) == 2
    path = lin.record_simulation(
        lineage=lineage, execution=execution, sim_dir=tmp_path,
        artifacts=[{"path": "k.json", "bytes": 1, "sha256": "a" * 64, "role": "result"}],
        name_to_uid=name_to_uid)
    assert json.loads(path.read_text())["execution"] == execution


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
