"""The unregistered marker, the binding evidence check, the version fields
and roots (spec docs/specs/models-releases-overlays.md, sections 5 and 7).

A lineage may cite any configuration or model uid; one no registry holds is
accepted only when the record lists it in ``unregistered``. Every case runs
through validate_light, record_light and record_simulation, which share one
check. The private-evidence predicate is pinned by omai/vectors/private.json,
which the site's JavaScript mirror must agree with.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from omai import lineages as lin
from omai.evidence import CITATION_KEYS, REGISTRY, private_reasons
from omai.schema import validate_record

_REPO = Path(__file__).resolve().parents[1]
_NODE = "ThermalConductivity[transport_model=hnemd]"
_NAME_TO_UID = {_NODE: "e7157a52da5eb7d2ae79e57692acc30d7e63a3a0d1c731b14da4d6ab8fd5eb88"}
TERSOFF = "52a93e90596829c57d54eef091de6215f1fac7ca15d57eac7568ddfdda26adfb"
SI = "7b5e77b1062f0997037cb9fd490d9edb8fce8099c4f700db334aa8afb8af22be"
SI_FORMER = "55bf22ca81868867402ac4ce50a830f91da84c805990c37c3bdafe3b93a69143"
PRIVATE = "2" * 64
KEYS = [k for keys in CITATION_KEYS.values() for k in keys]


def _lineage(conditions=None, configuration=None):
    lineage = {"node": _NODE, "node_uid": _NAME_TO_UID[_NODE],
               "material": {"name": "Si"}, "conditions": conditions or {}}
    if configuration is not None:
        lineage["material"]["configuration"] = configuration
    return lineage


def _record(lineage, **top):
    return {"id": lin.lineage_id(lineage), "lineage": lineage, **top}


def _strict(tmp_path, lineage, **kw):
    return lin.record_simulation(
        lineage=lineage, execution={"code": "fixture"},
        artifacts=[{"path": "r.json", "bytes": 1, "sha256": "a" * 64, "role": "result"}],
        sim_dir=tmp_path, name_to_uid=_NAME_TO_UID, **kw)


# Every writer and validator applies the same check.
def _validate(record):
    return lin.validate_light(record, name_to_uid=_NAME_TO_UID)


def _light(record):
    keep = ("unregistered", "lineage_version", "overlay_version")
    return lin.record_light(lineage=record["lineage"], name_to_uid=_NAME_TO_UID,
                            **{k: record[k] for k in keep if k in record})


PATHS = [_validate, _light]


# --- the binding model check -------------------------------------------------

@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("key", KEYS)
def test_an_unlisted_model_uid_that_resolves_nowhere_is_refused(path, key):
    with pytest.raises(lin.LineageError, match=f"conditions.{key} cites model") as err:
        path(_record(_lineage({key: PRIVATE})))
    # A key fixed by ruling cites what is never registered: only listing helps.
    if key == "calibration_sha256":
        assert "never registered; list it in unregistered" in str(err.value)
        assert "register it" not in str(err.value)
    else:
        assert "register it or list it in unregistered" in str(err.value)


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("key", KEYS)
def test_a_listed_model_uid_is_accepted(path, key):
    path(_record(_lineage({key: PRIVATE}),
                 unregistered=[{"kind": "model", "uid": PRIVATE}]))


@pytest.mark.parametrize("path", PATHS)
def test_a_registered_model_needs_no_marker_and_a_listed_one_is_no_error(path):
    path(_record(_lineage({"potential_sha256": TERSOFF})))
    # Listed at minting, registered since: checked as registered.
    path(_record(_lineage({"potential_sha256": TERSOFF}),
                 unregistered=[{"kind": "model", "uid": TERSOFF}]))


@pytest.mark.parametrize("value", ["sha256:" + TERSOFF, TERSOFF.upper(), None, 7])
def test_a_model_citation_is_a_bare_uid(value):
    with pytest.raises(lin.LineageError, match="bare 64-hex model uid"):
        _validate(_record(_lineage({"potential_sha256": value})))


def test_the_listing_must_name_the_kind_it_cites():
    with pytest.raises(lin.LineageError, match="cites model"):
        _validate(_record(_lineage({"calibration_sha256": PRIVATE}),
                          unregistered=[{"kind": "configuration", "uid": PRIVATE}]))


def test_the_strict_writer_refuses_and_accepts_the_same(tmp_path):
    with pytest.raises(lin.LineageError, match="cites model"):
        _strict(tmp_path, _lineage({"potential_sha256": PRIVATE}))
    marker = [{"kind": "model", "uid": PRIVATE}]
    path = _strict(tmp_path, _lineage({"potential_sha256": PRIVATE}),
                   unregistered=marker, lineage_version="c" * 64)
    stored = json.loads(path.read_text())
    assert stored["unregistered"] == marker and stored["lineage_version"] == "c" * 64
    assert "overlay_version" not in stored


# --- configurations: the same mechanism --------------------------------------

@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("pin", [SI, SI_FORMER, "sha256:" + SI])
def test_the_committed_si_configuration_and_its_alias_resolve(path, pin):
    path(_record(_lineage(configuration=pin)))


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("pin", [PRIVATE, "sha256:" + PRIVATE])
def test_a_private_configuration_needs_the_marker_and_the_pin_is_normalized(path, pin):
    with pytest.raises(lin.LineageError, match="material.configuration cites configuration"):
        path(_record(_lineage(configuration=pin)))
    path(_record(_lineage(configuration=pin),
                 unregistered=[{"kind": "configuration", "uid": PRIVATE}]))


def test_config_dir_still_resolves_beside_roots(tmp_path):
    (tmp_path / "cell.json").write_text(json.dumps({"canonical": {"uid": PRIVATE}}))
    record = _record(_lineage(configuration=PRIVATE))
    lin.validate_light(record, name_to_uid=_NAME_TO_UID, config_dir=tmp_path)
    # The default roots still answer for the committed record.
    lin.validate_light(_record(_lineage(configuration=SI)),
                       name_to_uid=_NAME_TO_UID, config_dir=tmp_path)


# --- roots -------------------------------------------------------------------

def test_the_wheel_registry_alone_resolves_si_and_its_alias():
    # An installed package has no docs/data/: only the shipped registry.
    for pin in (SI, SI_FORMER):
        lin.validate_light(_record(_lineage({"potential_sha256": TERSOFF}, pin)),
                           name_to_uid=_NAME_TO_UID, roots=[REGISTRY])


def test_roots_replace_the_default(tmp_path):
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"model": {PRIVATE: "models/x.json"}}))
    record = _record(_lineage({"potential_sha256": PRIVATE}))
    lin.validate_light(record, name_to_uid=_NAME_TO_UID, roots=[registry])
    with pytest.raises(lin.LineageError, match="cites model"):
        lin.validate_light(_record(_lineage({"potential_sha256": TERSOFF})),
                           name_to_uid=_NAME_TO_UID, roots=[registry])
    lin.record_light(lineage=record["lineage"], name_to_uid=_NAME_TO_UID,
                     roots=[registry])
    _strict(tmp_path, record["lineage"], roots=[registry])


# --- shape rules -------------------------------------------------------------

@pytest.mark.parametrize("bad", [
    None, "", {}, [None], [{}], [{"kind": "model"}],
    [{"kind": "overlay", "uid": PRIVATE}],
    [{"kind": ["model"], "uid": PRIVATE}],
    [{"kind": "model", "uid": "sha256:" + PRIVATE}],
    [{"kind": "model", "uid": PRIVATE, "note": "x"}],
])
def test_a_malformed_marker_is_refused(bad):
    with pytest.raises(lin.LineageError, match="unregistered must be"):
        _validate(_record(_lineage(), unregistered=bad))
    assert validate_record(_record(_lineage(), unregistered=bad))


@pytest.mark.parametrize("key", ["lineage_version", "overlay_version"])
@pytest.mark.parametrize("bad", [None, "", "c" * 63, "C" * 64, 1])
def test_a_malformed_version_field_is_refused(key, bad):
    with pytest.raises(lin.LineageError, match=f"{key} must be a 64-hex lowercase string"):
        _validate(_record(_lineage(), **{key: bad}))
    assert validate_record(_record(_lineage(), **{key: bad}))


def test_writers_omit_fields_without_a_value():
    record = lin.record_light(lineage=_lineage(), name_to_uid=_NAME_TO_UID,
                              unregistered=[], lineage_version=None)
    assert not {"unregistered", "lineage_version", "overlay_version"} & set(record)
    _validate(_record(_lineage(), unregistered=[]))


@pytest.mark.parametrize("bad", [{}, "", 0, False])
def test_writers_refuse_a_falsy_malformed_marker(tmp_path, bad):
    with pytest.raises(lin.LineageError, match="unregistered must be"):
        lin.record_light(lineage=_lineage(), name_to_uid=_NAME_TO_UID, unregistered=bad)
    with pytest.raises(lin.LineageError, match="unregistered must be"):
        _strict(tmp_path, _lineage(), unregistered=bad)


# --- what a producer declares ------------------------------------------------

def test_unregistered_for_lists_each_unresolved_citation_once():
    lineage = _lineage({"potential_sha256": TERSOFF, "base_potential_sha256": PRIVATE,
                        "calibration_sha256": PRIVATE}, "sha256:" + "5" * 64)
    declared = lin.unregistered_for(lineage)
    assert declared == [{"kind": "configuration", "uid": "5" * 64},
                        {"kind": "model", "uid": PRIVATE}]
    record = lin.record_light(lineage=lineage, name_to_uid=_NAME_TO_UID,
                              unregistered=declared)
    assert private_reasons(record)
    assert lin.unregistered_for(_lineage({"potential_sha256": TERSOFF}, SI_FORMER)) == []
    with pytest.raises(lin.LineageError, match="bare 64-hex model uid"):
        lin.unregistered_for(_lineage({"potential_sha256": "sha256:" + TERSOFF}))


def test_unregistered_for_reads_the_roots(tmp_path):
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"model": {PRIVATE: "models/x.json"}}))
    lineage = _lineage({"potential_sha256": PRIVATE}, SI)
    assert lin.unregistered_for(lineage, [registry]) == [
        {"kind": "configuration", "uid": SI}]


# --- identity and the format version -----------------------------------------

def test_the_new_fields_leave_the_id_unchanged_and_validate():
    without = lin.record_light(lineage=_lineage(), name_to_uid=_NAME_TO_UID)
    full = lin.record_light(lineage=_lineage(), name_to_uid=_NAME_TO_UID,
                            unregistered=[{"kind": "model", "uid": PRIVATE}],
                            lineage_version="c" * 64, overlay_version="d" * 64)
    assert full["id"] == without["id"] == lin.lineage_id(_lineage())
    assert validate_record(full) == []


def test_the_descriptor_names_the_new_record_fields():
    fields = lin.FORMAT_DESCRIPTOR["record_fields"]
    assert {"unregistered", "lineage_version", "overlay_version"} <= set(fields)


def test_sharing_keeps_the_marker():
    record = _record(_lineage({"potential_sha256": PRIVATE}),
                     unregistered=[{"kind": "model", "uid": PRIVATE}],
                     overlay_version="d" * 64)
    env = lin.envelope_from_fragment(lin.envelope_to_fragment(lin.envelope([record])))
    assert env["lineages"][0] == record


# --- the published registry and the private-evidence predicate ---------------

def test_the_registry_is_published_under_docs_data_with_the_citation_keys():
    published = (_REPO / "docs" / "data" / "registry.json").read_text()
    assert published == REGISTRY.read_text()
    keys = json.loads(published)["citation_keys"]
    assert keys == {node: list(k) for node, k in CITATION_KEYS.items()}
    assert keys["SetVoltage"] == ["calibration_sha256"]


_PRIVATE = json.loads((_REPO / "omai" / "vectors" / "private.json").read_text())


@pytest.mark.parametrize("case", _PRIVATE["cases"], ids=[c["name"] for c in _PRIVATE["cases"]])
def test_private_reasons_reproduce_the_vectors(case):
    assert private_reasons(case["member"], _PRIVATE["registry"]) == case["reasons"]


def test_the_vectors_cover_the_fail_closed_rules():
    by = {c["name"]: c["reasons"] for c in _PRIVATE["cases"]}
    assert by["public"] == by["unregistered_empty"] == by["overlay_version_null"] == []
    for name in ("unregistered_null", "unregistered_string", "overlay_version_empty_string",
                 "potential_prefixed", "potential_null", "configuration_null",
                 "calibration_unregistered", "legacy_recipe"):
        assert by[name], name
    assert by["configuration_prefixed"] == by["configuration_former_uid"] == []
    assert by["member_not_an_object"] == [{"field": "record", "kind": None}]


@pytest.mark.parametrize("entry", _PRIVATE["refused_registries"],
                         ids=[r["name"] for r in _PRIVATE["refused_registries"]])
def test_a_refused_registry_vector_raises(entry):
    with pytest.raises(ValueError):
        private_reasons({"lineage": {}}, entry["registry"])


def test_a_registry_without_its_tables_is_refused():
    for bad in ({}, {"model": {}, "configuration": {}}, {"citation_keys": [], "model": {},
                                                         "configuration": {}}):
        with pytest.raises(ValueError):
            private_reasons({"lineage": {}}, bad)


def test_the_shipped_registry_is_the_default():
    record = _record(_lineage({"potential_sha256": TERSOFF}, SI_FORMER))
    assert private_reasons(record) == []
    assert private_reasons(_record(_lineage({"potential_sha256": PRIVATE}))) == [
        {"field": "conditions.potential_sha256", "kind": "model"}]


def test_the_site_predicate_agrees_under_node():
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available; the site predicate is checked where present")
    proc = subprocess.run(
        [node, "--test", str(_REPO / "infra" / "site" / "src" / "private-members.test.mjs")],
        capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
