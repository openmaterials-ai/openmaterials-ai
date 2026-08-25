"""Tests for the external-solve request envelope (omai.external_solve).

One committed fixture (tests/fixtures/external_solve/kaldo-direct-bte-si.json)
pins the kALDo direct-BTE frontier: the solve_bte[bte_solver=direct_inverse]
edge, its MeanFreeDisplacement output, and the downstream
ThermalConductivity[bte_solver=direct_inverse] target, with the lineage taken
verbatim from the committed commons instance
docs/data/instances/si-thermalconductivity-bte-solver-direct-inverse-kaldo-tersoff-pinned.json
so the request's lineage_id IS that instance's existing id, recomputed
independently. No provider compute runs anywhere here.

The fixture is regenerated, never hand-edited: it must equal what
build_request mints from the live Python producers at the current store head.
When a map contribution advances the head, regenerate it with build_request
(same discipline as index/codes/). The negative tests mutate the fixture and
re-mint its hashes so exactly one gate fires per test; the tamper tests
deliberately do NOT re-mint.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from omai.external_solve import (
    ExternalSolveRequestError,
    build_request,
    parse_request,
    request_id,
    validate_request,
)
from omai.lineages import lineage_id
from omai.store import Store

_REPO = Path(__file__).resolve().parents[1]
_MAP = _REPO / "map"
_FIXTURE = Path(__file__).parent / "fixtures" / "external_solve" / "kaldo-direct-bte-si.json"
_PINNED_INSTANCE = (_REPO / "docs" / "data" / "instances" /
                    "si-thermalconductivity-bte-solver-direct-inverse-kaldo-tersoff-pinned.json")

_SOLVE_EDGE_NAME = "solve_bte[bte_solver=direct_inverse]"
_MFD_NODE_NAME = "MeanFreeDisplacement[bte_solver=direct_inverse]"
_TARGET_NODE_NAME = "ThermalConductivity[bte_solver=direct_inverse]"


def _fixture() -> dict[str, Any]:
    fixture: dict[str, Any] = json.loads(_FIXTURE.read_text())
    return fixture


def _reminted(request: dict[str, Any], **over: Any) -> dict[str, Any]:
    """A mutated copy with lineage_id and request_id re-minted, so the
    tamper gate stays quiet and exactly the targeted map gate fires."""
    mutated = {**request, **over}
    mutated["lineage_id"] = lineage_id(mutated["lineage"])
    mutated["request_id"] = request_id(mutated)
    return mutated


def _tmp_store(tmp_path: Path) -> Path:
    """A private copy of the live log, safe to push deprecations onto."""
    root = tmp_path / "map"
    root.mkdir()
    shutil.copy(_MAP / "log.jsonl", root / "log.jsonl")
    return root


# --------------------------------------------------------------------------
# The kALDo direct-BTE fixture.
# --------------------------------------------------------------------------

def test_fixture_parses_and_validates_against_the_live_map() -> None:
    report = validate_request(parse_request(_FIXTURE.read_text()))
    fx = _fixture()
    assert report["request_id"] == fx["request_id"]
    assert report["map_version"] == Store(_MAP).head
    assert report["operator_uid"] == fx["operator"]["uid"]
    assert report["target_uid"] == fx["target"]["uid"]


def test_fixture_pins_the_exact_solve_edge_output_and_target() -> None:
    """The frontier is the direct-inverse BTE solve edge, its output the
    mean-free-displacement node, its target the thermal conductivity, all
    resolved by name against the live materialized view."""
    fx = _fixture()
    current = Store(_MAP).read()
    assert fx["operator"]["name"] == _SOLVE_EDGE_NAME
    assert current["edges"][fx["operator"]["uid"]]["meta"]["name"] == _SOLVE_EDGE_NAME
    [output_uid] = fx["output_node_uids"]
    assert current["nodes"][output_uid]["meta"]["name"] == _MFD_NODE_NAME
    assert fx["target"]["name"] == _TARGET_NODE_NAME
    assert current["nodes"][fx["target"]["uid"]]["meta"]["name"] == _TARGET_NODE_NAME
    assert fx["representation"] == {
        "scheme": "kaldo",
        "discretization": {"collision_matrix_assembly": "full_grid",
                           "linear_solver": "scipy.linalg.solve"},
    }


def test_fixture_regenerates_from_the_live_producers() -> None:
    """The committed fixture equals what build_request mints from the Python
    domain objects at the live head: every uid recomputed via
    omai.operator.identity, never copied from the stored map or from the
    fixture itself. If a map contribution moved the head, regenerate the
    fixture with exactly this call."""
    from omai.thermal_transport.operator import (
        THERMAL_CONDUCTIVITY_DIRECT,
        solve_bte_direct,
    )
    from omai.thermal_transport.representation.kaldo import KALDO_SOLVE_BTE_DIRECT

    fx = _fixture()
    rebuilt = build_request(
        operator=solve_bte_direct,
        target=THERMAL_CONDUCTIVITY_DIRECT,
        scheme=KALDO_SOLVE_BTE_DIRECT.representation_name,
        discretization=dict(KALDO_SOLVE_BTE_DIRECT.discretization_choices),
        lineage=json.loads(_PINNED_INSTANCE.read_text())["lineage"],
        execution=fx["execution"],
    )
    assert rebuilt == fx


def test_fixture_lineage_id_is_the_committed_instance_id() -> None:
    """The envelope recomputes the EXISTING lineage id independently: the
    fixture's lineage is the committed commons instance's lineage verbatim,
    and its lineage_id equals that instance's stated id."""
    fx = _fixture()
    pinned = json.loads(_PINNED_INSTANCE.read_text())
    assert fx["lineage"] == pinned["lineage"]
    assert fx["lineage_id"] == pinned["id"]
    assert lineage_id(fx["lineage"]) == pinned["id"]


# --------------------------------------------------------------------------
# Canonical serialization and the identity rule.
# --------------------------------------------------------------------------

def test_request_id_is_stable_under_key_reordering() -> None:
    fx = _fixture()
    reordered = dict(reversed(list(fx.items())))
    assert request_id(reordered) == fx["request_id"]


def test_execution_metadata_stays_outside_identity() -> None:
    fx = _fixture()
    without = {k: v for k, v in fx.items() if k != "execution"}
    altered = {**fx, "execution": {"code": "kaldo", "runner": "elsewhere"}}
    assert request_id(without) == fx["request_id"]
    assert request_id(altered) == fx["request_id"]


def test_lineage_float_noise_collapses_to_one_request_id() -> None:
    """The lineages float rule (6 decimals in conditions and friends)
    applies inside the request hash too."""
    fx = _fixture()
    noisy = json.loads(json.dumps(fx))
    noisy["lineage"]["conditions"]["temperature_K"] = 300.0000000001
    assert request_id(noisy) == fx["request_id"]
    assert lineage_id(noisy["lineage"]) == fx["lineage_id"]


def test_a_different_lineage_mints_a_different_request_id() -> None:
    fx = _fixture()
    changed = json.loads(json.dumps(fx))
    changed["lineage"]["conditions"]["mesh"] = [7, 7, 7]
    assert request_id(changed) != fx["request_id"]


# --------------------------------------------------------------------------
# Tampering fails before any map access.
# --------------------------------------------------------------------------

def test_tampered_lineage_without_reminting_fails() -> None:
    fx = _fixture()
    fx["lineage"]["conditions"]["temperature_K"] = 301.0
    with pytest.raises(ExternalSolveRequestError, match="tampered"):
        parse_request(json.dumps(fx))


def test_tampered_request_id_fails() -> None:
    fx = _fixture()
    fx["request_id"] = ("0" if fx["request_id"][0] != "0" else "1") + fx["request_id"][1:]
    with pytest.raises(ExternalSolveRequestError, match="request_id"):
        parse_request(json.dumps(fx))


def test_tampered_lineage_id_fails() -> None:
    fx = _fixture()
    fx["lineage_id"] = "f" * 64
    with pytest.raises(ExternalSolveRequestError, match="lineage_id"):
        parse_request(json.dumps(fx))


# --------------------------------------------------------------------------
# Malformed schema fields fail at parse time.
# --------------------------------------------------------------------------

def test_malformed_requests_fail_closed() -> None:
    fx = _fixture()
    malformed: list[tuple[dict[str, Any], str]] = [
        ({k: v for k, v in fx.items() if k != "target"}, "missing fields"),
        ({**fx, "dispatch": True}, "unknown fields"),
        ({**fx, "v": 2}, "v must be"),
        ({**fx, "map_version": "not-a-hash"}, "map_version"),
        ({**fx, "operator": {"name": "", "uid": fx["operator"]["uid"]}},
         "operator.name"),
        ({**fx, "operator": {**fx["operator"], "extra": 1}}, "unknown keys"),
        ({**fx, "input_node_uids": []}, "non-empty list"),
        ({**fx, "input_node_uids": ["nope"]}, "input_node_uids"),
        ({**fx, "representation": {"scheme": "", "discretization": {}}},
         "scheme"),
        ({**fx, "representation": {"scheme": "kaldo",
                                   "discretization": {"mesh": 5}}},
         "discretization"),
        ({**fx, "lineage": "not-an-object"}, "lineage must be an object"),
        ({**fx, "execution": {}}, "execution.code"),
    ]
    for request, match in malformed:
        with pytest.raises(ExternalSolveRequestError, match=match):
            parse_request(json.dumps(request))
    with pytest.raises(ExternalSolveRequestError, match="not valid JSON"):
        parse_request("{nope")


# --------------------------------------------------------------------------
# The live-map gate.
# --------------------------------------------------------------------------

def test_unknown_map_version_fails_closed() -> None:
    request = _reminted(_fixture(), map_version="e" * 64)
    with pytest.raises(ExternalSolveRequestError, match="unknown map version"):
        validate_request(request)


def test_stale_map_version_fails_closed() -> None:
    """A version that exists in the log but is not the head is stale."""
    first = json.loads((_MAP / "log.jsonl").read_text().splitlines()[0])
    request = _reminted(_fixture(), map_version=first["version"])
    with pytest.raises(ExternalSolveRequestError, match="stale map version"):
        validate_request(request)


def test_unknown_operator_edge_fails_closed() -> None:
    fx = _fixture()
    request = _reminted(fx, operator={**fx["operator"], "uid": "a" * 64})
    with pytest.raises(ExternalSolveRequestError, match="unknown operator edge"):
        validate_request(request)


def test_operator_name_mismatch_fails_closed() -> None:
    fx = _fixture()
    request = _reminted(
        fx, operator={**fx["operator"], "name": "solve_bte[bte_solver=rta]"})
    with pytest.raises(ExternalSolveRequestError, match="does not match the stored edge name"):
        validate_request(request)


def test_reordered_input_uids_fail_closed() -> None:
    """The stored canonical order is part of the contract: a reordered,
    noncanonical binding is a different claim and fails."""
    fx = _fixture()
    request = _reminted(
        fx, input_node_uids=list(reversed(fx["input_node_uids"])))
    with pytest.raises(ExternalSolveRequestError, match="input_node_uids"):
        validate_request(request)


def test_wrong_output_uid_fails_closed() -> None:
    fx = _fixture()
    request = _reminted(fx, output_node_uids=[fx["target"]["uid"]])
    with pytest.raises(ExternalSolveRequestError, match="output_node_uids"):
        validate_request(request)


def test_unknown_target_node_fails_closed() -> None:
    fx = _fixture()
    request = _reminted(fx, target={**fx["target"], "uid": "b" * 64})
    with pytest.raises(ExternalSolveRequestError, match="unknown node"):
        validate_request(request)


def test_target_uid_name_mismatch_fails_closed() -> None:
    """The target must resolve by name AND uid together: the right name on
    the wrong node uid fails."""
    fx = _fixture()
    [mfd_uid] = fx["output_node_uids"]
    request = _reminted(fx, target={**fx["target"], "uid": mfd_uid})
    with pytest.raises(ExternalSolveRequestError, match="stored node name"):
        validate_request(request)


def test_non_downstream_target_fails_closed() -> None:
    """An upstream node (the frontier's own HeatCapacity input) resolves by
    name plus uid but is not structurally downstream, so it fails."""
    fx = _fixture()
    current = Store(_MAP).read()
    upstream_uid = fx["input_node_uids"][0]
    upstream_name = current["nodes"][upstream_uid]["meta"]["name"]
    request = _reminted(fx, target={"name": upstream_name, "uid": upstream_uid})
    with pytest.raises(ExternalSolveRequestError, match="not structurally downstream"):
        validate_request(request)


def test_lineage_node_must_name_the_target() -> None:
    fx = _fixture()
    lineage = {**fx["lineage"], "node": _MFD_NODE_NAME}
    request = _reminted(fx, lineage=lineage)
    with pytest.raises(ExternalSolveRequestError, match="does not name the request target"):
        validate_request(request)


def test_stale_lineage_node_uid_pin_fails_closed() -> None:
    fx = _fixture()
    lineage = {**fx["lineage"], "node_uid": "d" * 64}
    request = _reminted(fx, lineage=lineage)
    with pytest.raises(ExternalSolveRequestError, match="node_uid pin"):
        validate_request(request)


def test_deprecated_operator_edge_fails_closed(tmp_path: Path) -> None:
    root = _tmp_store(tmp_path)
    store = Store(root)
    fx = _fixture()
    store.push("deprecate", {"uid": fx["operator"]["uid"], "note": "test"},
               "test", "2026-08-25", "test deprecation")
    request = _reminted(fx, map_version=store.head)
    with pytest.raises(ExternalSolveRequestError, match="deprecated"):
        validate_request(request, store_root=root)


def test_superseded_target_node_fails_closed(tmp_path: Path) -> None:
    root = _tmp_store(tmp_path)
    store = Store(root)
    fx = _fixture()
    store.push("supersede", {"old_uids": [fx["target"]["uid"]],
                             "new_uids": ["f" * 64]},
               "test", "2026-08-25", "test supersession")
    request = _reminted(fx, map_version=store.head)
    with pytest.raises(ExternalSolveRequestError, match="superseded"):
        validate_request(request, store_root=root)


def test_request_minted_before_a_map_change_goes_stale(tmp_path: Path) -> None:
    """A push moves the head; the un-re-minted request now fails as stale,
    never silently validates against the new map."""
    root = _tmp_store(tmp_path)
    store = Store(root)
    fx = _fixture()
    request = _reminted(fx, map_version=store.head)
    validate_request(request, store_root=root)
    store.push("deprecate", {"uid": fx["operator"]["uid"], "note": "test"},
               "test", "2026-08-25", "test deprecation")
    with pytest.raises(ExternalSolveRequestError, match="stale map version"):
        validate_request(request, store_root=root)


# --------------------------------------------------------------------------
# The executor is untouched.
# --------------------------------------------------------------------------

def test_executor_still_raises_external_solve_required() -> None:
    """No resolver was added anywhere: the implicit edge still refuses
    exactly as before this module existed."""
    from omai.representation.executor import ExternalSolveRequired, apply_edge
    from omai.thermal_transport.operator import solve_bte_direct

    with pytest.raises(ExternalSolveRequired):
        apply_edge(solve_bte_direct)
