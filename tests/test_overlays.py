"""Private overlays (omai/overlays.py; spec docs/specs/models-releases-overlays.md,
section 6), checked on the synthetic fixture overlay omai/vectors/overlay.json."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from omai import lineages as lin
from omai.evidence import _DATA_DIR
from omai.gates import VOCABULARY, validate_contribution
from omai.map_data import _lineage_version
from omai.overlays import OverlayError, load, overlay_version
from omai.store import Store
from omai.tools import gen_vectors

_REPO = Path(__file__).resolve().parents[1]
VECTOR = json.loads((_REPO / "omai" / "vectors" / "overlay.json").read_text())
FILES = {path: json.loads(text) for path, text in VECTOR["files"].items()}
NODE = "example:SyntheticQuantity"
NODE_UID = FILES["map.json"][0]["payload"]["uid"]
MODEL = FILES["models/synthetic.json"]["uid"]
BASE = FILES["overlay.json"]["base_graph_version"]
TEMPERATURE = gen_vectors._TEMPERATURE
NAME_TO_UID = {"Temperature": TEMPERATURE}
COMMIT = "1" * 40


def _overlay(root: Path, **edits) -> Path:
    """The fixture overlay under ``root``: its exact files, each ``edits``
    entry (``/`` written as ``__``) replacing one, None deleting it, "symlink"
    linking it to a file outside the overlay."""
    files = {**VECTOR["files"], **{path.replace("__", "/"): doc
                                   for path, doc in edits.items()}}
    for path, doc in files.items():
        if doc is None:
            continue
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        if doc == "symlink":
            outside = root.parent / f"{root.name}-outside.json"
            outside.write_text(VECTOR["files"]["models/synthetic.json"])
            (root / path).symlink_to(outside)
        else:
            (root / path).write_text(doc if isinstance(doc, str) else json.dumps(doc))
    return root


def _release(version, commit=COMMIT):
    return {"version": version, "tag": version, "commit": commit,
            "released": "2026-10-11", "spdx": "CC0-1.0", "license_source": "synthetic"}


def test_the_fixture_overlay_loads_against_the_public_map(tmp_path):
    (overlay,) = load([_DATA_DIR, _overlay(tmp_path)])
    assert overlay.namespace == "example" and overlay.base == BASE
    assert overlay.version == VECTOR["overlay_version"]
    assert overlay.names == {NODE: NODE_UID}
    assert load([_DATA_DIR]) == [] and load(None) == []


def test_the_contribution_is_checked_with_the_overlay_vocabulary():
    current = Store(_REPO / "map").read(BASE)
    assert any(p.startswith("[registry]")
               for p in validate_contribution(FILES["map.json"], current))
    vocabulary = {**VOCABULARY,
                  "quantity_tags": {**VOCABULARY["quantity_tags"],
                                    **FILES["registry.json"]["quantity_tags"]}}
    # the overlay's symbol dimension is unknown publicly: the dimensional gate skips
    assert validate_contribution(FILES["map.json"], current, vocabulary) == []


def test_overlay_version_covers_every_file_except_overlay_json_and_hidden_ones(tmp_path):
    root = _overlay(tmp_path)
    version = overlay_version(root)
    (root / "overlay.json").write_text(json.dumps(FILES["overlay.json"], indent=4))
    (root / ".DS_Store").write_bytes(b"\0synthetic")
    (root / "models" / ".hidden").mkdir()
    (root / "models" / ".hidden" / "x.json").write_text("{}")
    assert overlay_version(root) == version
    (root / "notes.txt").write_text("a synthetic note\n")
    assert overlay_version(root) != version


_KIND = next(iter(VOCABULARY["index_kinds"].values()))
_REGISTRY = FILES["registry.json"]
_MAP = FILES["map.json"]
_CODE = FILES["codes.json"]["example:code"]["example:SyntheticQuantity"]


@pytest.mark.parametrize("edits, match", [
    ({"overlay.json": {"namespace": "Example:1", "base_graph_version": BASE}},
     "lowercase namespace"),
    ({"overlay.json": {"namespace": "example", "base_graph_version": "0" * 64}},
     "not a version of the public map"),
    ({"map.json": _MAP + [{"op": "edit_meta", "payload": {
        "uid": TEMPERATURE, "identity": {}, "meta": {"name": "example:T"}}}]},
     "add_node and add_edge only"),
    ({"map.json": [{**_MAP[0], "payload": {**_MAP[0]["payload"], "meta": {
        **_MAP[0]["payload"]["meta"], "name": "SyntheticQuantity"}}}, _MAP[1]]},
     "starting 'example:'"),
    ({"map.json": _MAP + [{"op": "add_node", "payload": {
        "uid": TEMPERATURE, "meta": {"name": "example:Temperature"}, "identity": {
            "fields": [{"dimension": "Th^1", "indices": []}], "gauge": "observable",
            "labels": {}, "quantity": "temperature"}}}]},
     "cite the public one"),
    ({"registry.json": {"symbol_dimensions": _REGISTRY["symbol_dimensions"]}},
     r"\[registry\] node"),
    ({"registry.json": {**_REGISTRY, "symbol_dimensions": {
        "x_example": [1, 2, -2, 0, 0, 0, 0]}}}, r"\[dimensional\]"),
    ({"registry.json": {**_REGISTRY, "quantity_tags": {"temperature": "taken"}}},
     "held by the public registry"),
    ({"registry.json": {**_REGISTRY, "label_keys": {"order": ["2"]}}},
     "held by the public registry"),
    ({"registry.json": {**_REGISTRY, "index_kinds": {"example_index": _KIND}}},
     "held by the public registry"),
    ({"registry.json": {**_REGISTRY, "symbol_dimensions": {"T": [0, 0, 0, 1, 0, 0, 0]}}},
     "held by the public registry"),
    ({"registry.json": {**_REGISTRY, "symbol_dimensions": {"x_example": [0, 1]}}},
     "malformed"),
    ({"models__si-tersoff.json": (_DATA_DIR / "models" / "si-tersoff.json").read_text()},
     "is public .*: remove the overlay copy"),
    ({"codes.json": {"code": {NODE: _CODE}}}, "names each code"),
    ({"codes.json": {"example:code": {NODE: {**_CODE, "license": ""}}}},
     "names each code"),
    ({"releases__kaldo.json": {"aliases": [], "releases": [_release("2.2.1")]}},
     "names two commits"),
    ({"releases__example__code.json": {"aliases": ["kaldo"], "releases": [_release("1")]}},
     "names a representation"),
    ({"releases__example__code.json": {"aliases": ["quantum-espresso"],
                                        "releases": [_release("1.0")]}},
     "alias 'quantum-espresso' already names 'qe'"),
    ({"models__synthetic.json": None, "models__link.json": "symlink"},
     "no symlinks"),
    ({"codes.json": {"example:code": {NODE: _CODE, "example:Missing": _CODE}}},
     "covers 'example:Missing', which neither the public map nor the overlay"),
    ({"codes.json": {"example:code": {NODE: _CODE, "NoSuchNode": _CODE}}},
     "covers 'NoSuchNode'"),
])
def test_an_overlay_is_refused(tmp_path, edits, match):
    with pytest.raises(OverlayError, match=match):
        load([_DATA_DIR, _overlay(tmp_path, **edits)])


def test_a_second_overlay_may_not_reuse_a_namespace_or_vocabulary(tmp_path):
    first = _overlay(tmp_path / "a")
    with pytest.raises(OverlayError, match="namespace"):
        load([_DATA_DIR, first, _overlay(tmp_path / "b")])
    other = tmp_path / "c"
    other.mkdir()
    (other / "overlay.json").write_text(json.dumps(
        {"namespace": "other", "base_graph_version": BASE}))
    (other / "registry.json").write_text(json.dumps(
        {"quantity_tags": {"example_synthetic_quantity": "again"}}))
    with pytest.raises(OverlayError, match="another overlay"):
        load([_DATA_DIR, first, other])


def test_an_overlay_registers_releases_of_its_code_and_of_a_public_one(tmp_path):
    # the fixture registers example:code 1.0 at releases/example/code.json
    root = _overlay(tmp_path, **{
        "releases__kaldo.json": {"aliases": [], "releases": [_release("2.2.1-example")]},
        "codes.json": {"example:code": {NODE: _CODE, "Temperature": _CODE}}})
    roots = [_DATA_DIR, root]
    load(roots)
    rows = {"registry": [{"id": "kaldo", "version": "2.2.1-example"},
                         {"id": "example:code", "version": "v1.0"}]}
    assert lin.release_check(rows, roots=roots) == []
    assert [r["reason"] for r in lin.release_check(rows)] == [
        "version not registered", "not a representation"]


def _uses_the_overlay(record, roots):
    assert record["overlay_version"] == VECTOR["overlay_version"]
    assert record["lineage_version"] == _lineage_version(BASE)
    bare = {k: v for k, v in record.items()
            if k not in ("lineage_version", "overlay_version")}
    with pytest.raises(lin.LineageError, match="carries lineage_version and overlay_version"):
        lin.validate_light(bare, name_to_uid=NAME_TO_UID, roots=roots)


def test_a_record_made_against_an_overlay_names_it(tmp_path):
    roots = [_DATA_DIR, _overlay(tmp_path / "overlay")]
    record = lin.record_light(lineage={"node": NODE, "material": {"name": "Si"}},
                              name_to_uid=NAME_TO_UID, roots=roots)
    assert record["lineage"]["node_uid"] == NODE_UID
    _uses_the_overlay(record, roots)
    with pytest.raises(lin.LineageError, match="not a live map node"):
        lin.validate_light(record, name_to_uid=NAME_TO_UID)
    # a cited overlay model uses the overlay too, and resolves through it
    cites = {"template": "synthetic", "conditions": {"potential_sha256": MODEL}}
    _uses_the_overlay(lin.record_light(lineage=cites, roots=roots), roots)
    with pytest.raises(lin.LineageError, match="cites model"):
        lin.record_light(lineage=cites)
    path = lin.record_simulation(
        lineage={"node": NODE, "material": {"name": "Si"}},
        execution={"code": "example:code"}, sim_dir=tmp_path / "sims",
        artifacts=[{"path": "r.json", "bytes": 1, "sha256": "a" * 64, "role": "result"}],
        name_to_uid=NAME_TO_UID, roots=roots)
    _uses_the_overlay(json.loads(path.read_text()), roots)


def test_a_record_is_made_against_one_overlay(tmp_path):
    other = tmp_path / "other"
    (other / "models").mkdir(parents=True)
    (other / "overlay.json").write_text(json.dumps(
        {"namespace": "other", "base_graph_version": BASE}))
    model = {**FILES["models/synthetic.json"], "uid": "c" * 64,
             "files": [{**FILES["models/synthetic.json"]["files"][0], "sha256": "c" * 64}]}
    (other / "models" / "other.json").write_text(json.dumps(model))
    roots = [_DATA_DIR, _overlay(tmp_path / "example"), other]
    with pytest.raises(lin.LineageError, match="made against one"):
        lin.record_light(lineage={"node": NODE, "conditions": {"potential_sha256": "c" * 64}},
                         name_to_uid=NAME_TO_UID, roots=roots)


def _temperature_named(names):
    from omai.map_data import _domains

    return tuple(dataclasses.replace(d, nodes=tuple(
        dataclasses.replace(s, names=names) if s.name == "Temperature" else s
        for s in d.nodes)) for d in _domains())


def test_a_published_node_keeps_its_overlay_name():
    from omai.map_data import build_graph_dict

    domains = _temperature_named(("example:Temperature",))
    record = lin.record_light(lineage={"node": "example:Temperature"}, domains=domains)
    assert record["lineage"]["node_uid"] == TEMPERATURE
    (node,) = [n for n in build_graph_dict(domains)["nodes"] if n["id"] == "Temperature"]
    assert node["names"] == ["example:Temperature"]


def test_sync_carries_a_node_name_into_map_meta(monkeypatch):
    import omai.map_data
    from omai.sync import compute_sync

    monkeypatch.setattr(omai.map_data, "_DOMAINS_CACHE",
                        _temperature_named(("example:Temperature",)))
    proposal = compute_sync(Store(_REPO / "map").read())
    assert {"op": "edit_meta", "payload": {
        "uid": TEMPERATURE, "meta": {"names": ["example:Temperature"]}}} in proposal["edit_meta"]


@pytest.mark.parametrize("payload", [
    # a forged node carrying a public uid
    {"op": "add_node", "payload": {"uid": TEMPERATURE, "identity": {
        "fields": [], "gauge": "observable", "labels": {}, "quantity": "example_synthetic_quantity"},
        "meta": {"name": "example:Forged"}}},
    # a junk edge
    {"op": "add_edge", "payload": {"uid": "0" * 64, "identity": {
        "inputs": ["1" * 64], "outputs": ["2" * 64], "output": "2" * 64,
        "formula": "none", "schemes": {}}, "meta": {"name": "example:junk"}}},
])
def test_without_a_map_log_the_live_map_checks_the_contribution(tmp_path, monkeypatch, payload):
    import omai.overlays

    monkeypatch.setattr(omai.overlays, "_STORE", tmp_path / "no-map")
    (overlay,) = load([_DATA_DIR, _overlay(tmp_path / "ok")])
    assert overlay.names == {NODE: NODE_UID}
    with pytest.raises(OverlayError, match="map.json"):
        load([_DATA_DIR, _overlay(tmp_path / "bad", **{"map.json": _MAP + [payload]})])


def test_overlay_version_refuses_a_symlink(tmp_path):
    with pytest.raises(OverlayError, match="no symlinks"):
        overlay_version(_overlay(tmp_path / "o", **{"models__link.json": "symlink"}))


def test_a_hidden_record_is_not_a_record(tmp_path):
    from omai.evidence import resolve

    root = _overlay(tmp_path, **{"models__synthetic.json": None,
                                 "models__.synthetic.json": FILES["models/synthetic.json"]})
    (overlay,) = load([_DATA_DIR, root])
    assert resolve("model", MODEL, [root]) is None
    assert overlay.version == overlay_version(_overlay(tmp_path / "bare",
                                                       **{"models__synthetic.json": None}))


def test_an_overlay_name_may_not_rename_a_public_node(tmp_path):
    roots = [_DATA_DIR, _overlay(tmp_path)]
    record = lin.record_light(lineage={"node": NODE}, name_to_uid=NAME_TO_UID, roots=roots)
    # the published node, same uid: fine
    lin.validate_light(record, name_to_uid={**NAME_TO_UID, NODE: NODE_UID}, roots=roots)
    with pytest.raises(lin.LineageError, match="rename or drop it in the overlay"):
        lin.validate_light(record, name_to_uid={**NAME_TO_UID, NODE: TEMPERATURE},
                           roots=roots)


@pytest.mark.parametrize("names", [("Temperature2",), ("example:T", "example:T")])
def test_kept_names_are_namespaced_and_unique(names):
    from omai.map_data import build_graph_dict

    with pytest.raises(AssertionError):
        build_graph_dict(_temperature_named(names))
