"""The external-solve request envelope for one implicit graph frontier.

When the representation executor reaches an implicit operator edge (the
direct BTE solve, an eigenvalue problem, a q->0 limit) it raises
``ExternalSolveRequired`` and the caller must inject a precomputed source.
This module defines the neutral, serializable request that lets an external
engine receive that frontier while preserving the map's content-addressed
identities. OpenMaterials owns this contract: graph identity, lineage
identity, and the fail-closed validation against the live map. An execution
engine may later consume the envelope through a separately validated adapter
binding; no dispatcher, resolver, or engine import belongs here.

The envelope (version :data:`REQUEST_VERSION`) is one JSON object:

    {"v", "request_id", "map_version", "operator": {"name", "uid"},
     "input_node_uids", "output_node_uids", "target": {"name", "uid"},
     "representation": {"scheme", "discretization"},
     "lineage", "lineage_id", "execution"?}

``map_version`` pins the live map-store head (:class:`omai.store.Store`);
``operator`` names the implicit edge by metadata name plus content uid;
``input_node_uids`` and ``output_node_uids`` carry the edge's node uids in
the stored canonical order (the sorted order of the edge identity, exactly
as ``map/current/edges.json`` holds them); ``target`` is the downstream node
the caller actually wants, by name plus uid; ``representation`` names the
executing code's scheme and its discretization choices (the
``OperatorRepresentationSpec`` vocabulary); ``lineage`` is an ordinary light
lineage (:mod:`omai.lineages`), the asked computation.

Identity (the content-addressing rule, this module's protocol commitment):

    request_id = sha256 of the canonical JSON of
    ``{"external_solve": {v, map_version, operator, input_node_uids,
    output_node_uids, target, representation, lineage}}`` with the lineage
    float-normalized exactly as :func:`omai.lineages.lineage_id` normalizes
    it (sorted keys, compact separators, floats in
    conditions/params/hyperparameters/values rounded to 6 decimals). The
    stated ``request_id``, the stated ``lineage_id`` (derived data, always
    recomputed independently from the lineage), and ``execution`` (what ran
    or will run: code, version, runner) are OUTSIDE the hash. Attaching or
    editing execution metadata never re-mints a request id, the lineages
    discipline applied to the request envelope.

Validation is fail-closed and happens BEFORE any dispatch concept exists:

    * a map version that is not the live head fails (stale versions and
      unknown versions fail with distinct messages);
    * an operator uid the live map does not carry fails; a deprecated or
      superseded edge or node binding fails;
    * the request's input and output node uids must equal the stored edge
      identity lists exactly, order included (a reordered, noncanonical
      binding fails);
    * the stored edge and target identities must recompute to their own
      uids (a tampered stored map entry fails; reads replay the live log
      via :meth:`omai.store.Store.read`, never ``map/current/``);
    * the target must resolve by name plus uid and be structurally
      downstream of the frontier's outputs over live edges;
    * a lineage that names a node must name the target (and its pin must
      match); a stated request_id or lineage_id that does not recompute
      fails; malformed or unknown fields fail at parse time.

Entry points: :func:`build_request` (mint an envelope from the Python
domain objects, recomputing every uid via :mod:`omai.operator.identity`
rather than copying stored bytes), :func:`parse_request` (wire JSON in,
shape and hash checked), :func:`validate_request` (the live-map gate),
:func:`request_id` (the identity rule).
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from omai.lineages import _canonical_lineage, lineage_id
from omai.operator.identity import (
    canonical_json,
    edge_identity,
    edge_uid_from_identity,
    node_id,
    node_uid_from_identity,
)
from omai.operator.operator import Operator
from omai.operator.space import Space
from omai.store import Store

__all__ = [
    "REQUEST_VERSION",
    "ExternalSolveRequestError",
    "build_request",
    "parse_request",
    "request_id",
    "validate_request",
]

REQUEST_VERSION = 1

_MAP_ROOT = Path(__file__).resolve().parents[1] / "map"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

# The identity-bearing envelope keys, in wire order. Exactly these enter the
# request hash; see request_id.
_IDENTITY_KEYS = ("v", "map_version", "operator", "input_node_uids",
                  "output_node_uids", "target", "representation", "lineage")

# Keys carried on the wire OUTSIDE identity: the stated request id, the
# stated (independently recomputed) lineage id, and the execution metadata.
_OUTSIDE_IDENTITY_KEYS = ("request_id", "lineage_id", "execution")


class ExternalSolveRequestError(Exception):
    """An external-solve request is malformed, tampered, or does not bind
    to the current live map. Raised before any dispatch concept exists."""


# --------------------------------------------------------------------------
# Identity.
# --------------------------------------------------------------------------

def request_id(request: dict[str, Any]) -> str:
    """The content-addressed id of a request: sha256 of the canonical JSON of
    the identity payload under the ``"external_solve"`` domain key.

    Identity is the asked frontier and nothing else: the envelope version,
    the pinned map version, the operator binding, the ordered input and
    output node uids, the target, the representation, and the lineage (float
    normalized exactly as :func:`omai.lineages.lineage_id` normalizes it).
    The stated ``request_id`` and ``lineage_id`` and the ``execution`` block
    are OUTSIDE this hash: editing execution metadata never re-mints an id.
    """
    payload: dict[str, Any] = {key: request.get(key) for key in _IDENTITY_KEYS}
    lineage = payload["lineage"]
    if isinstance(lineage, dict):
        payload["lineage"] = _canonical_lineage(lineage)
    blob = canonical_json({"external_solve": payload})
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Builder (recomputes identity from the Python objects, never copies bytes).
# --------------------------------------------------------------------------

def build_request(*, operator: Operator, target: Space, scheme: str,
                  discretization: dict[str, str], lineage: dict[str, Any],
                  execution: dict[str, Any] | None = None,
                  store_root: Path | None = None) -> dict[str, Any]:
    """Mint an external-solve request for ``operator`` with ``target``.

    Every uid is recomputed from the Python domain objects via
    :mod:`omai.operator.identity` (the reference implementation), never
    copied out of the stored map: :func:`validate_request` then compares
    this independent recomputation against the stored edge, so a fixture
    built here is verified against the live map rather than against its own
    asserted digests. ``map_version`` pins the live store head at build
    time. ``scheme`` and ``discretization`` are the executing code's
    representation vocabulary (``OperatorRepresentationSpec``
    ``representation_name`` and ``discretization_choices``). ``execution``
    (optional) rides outside identity.
    """
    ident: dict[str, Any] = edge_identity(operator, node_id)
    request: dict[str, Any] = {
        "v": REQUEST_VERSION,
        "map_version": Store(store_root or _MAP_ROOT).head,
        "operator": {"name": operator.name,
                     "uid": edge_uid_from_identity(ident)},
        "input_node_uids": list(ident["inputs"]),
        "output_node_uids": list(ident["outputs"]),
        "target": {"name": target.name, "uid": node_id(target)},
        "representation": {"scheme": scheme,
                           "discretization": dict(discretization)},
        "lineage": lineage,
    }
    request["request_id"] = request_id(request)
    request["lineage_id"] = lineage_id(lineage)
    if execution is not None:
        request["execution"] = execution
    _check_shape(request)
    return request


# --------------------------------------------------------------------------
# Parser (deterministic schema; malformed fields fail here).
# --------------------------------------------------------------------------

def _fail(where: str, message: str) -> ExternalSolveRequestError:
    return ExternalSolveRequestError(f"{where}: {message}")


def _check_hex64(value: Any, *, where: str, what: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.match(value):
        raise _fail(where, f"{what} must be a 64-hex-character sha256 string")


def _check_named_binding(binding: Any, *, where: str, what: str) -> None:
    """A ``{"name", "uid"}`` pair: non-empty name, hex64 uid, nothing else."""
    if not isinstance(binding, dict):
        raise _fail(where, f"{what} must be an object")
    extra = set(binding) - {"name", "uid"}
    if extra:
        raise _fail(where, f"{what} carries unknown keys {sorted(extra)!r}")
    name = binding.get("name")
    if not isinstance(name, str) or not name:
        raise _fail(where, f"{what}.name must be a non-empty string")
    _check_hex64(binding.get("uid"), where=where, what=f"{what}.uid")


def _check_uid_list(value: Any, *, where: str, what: str) -> None:
    if not isinstance(value, list) or not value:
        raise _fail(where, f"{what} must be a non-empty list")
    for i, uid in enumerate(value):
        _check_hex64(uid, where=where, what=f"{what}[{i}]")


def _check_shape(request: Any, *, where: str = "<request>") -> None:
    """The deterministic schema gate: exactly the declared fields, each
    well-formed. Runs before any hash recomputation or map access."""
    if not isinstance(request, dict):
        raise _fail(where, "request must be an object")
    known = set(_IDENTITY_KEYS) | set(_OUTSIDE_IDENTITY_KEYS)
    unknown = set(request) - known
    if unknown:
        raise _fail(where, f"unknown fields {sorted(unknown)!r}")
    required = [k for k in (*_IDENTITY_KEYS, "request_id", "lineage_id")
                if k not in request]
    if required:
        raise _fail(where, f"missing fields {sorted(required)!r}")
    # isinstance guards the bool == int coercion: v=true must not alias v=1
    # (it would mint a second request id for the same frontier).
    if isinstance(request["v"], bool) or request["v"] != REQUEST_VERSION:
        raise _fail(where, f"v must be {REQUEST_VERSION}, got {request['v']!r}")
    _check_hex64(request["map_version"], where=where, what="map_version")
    _check_hex64(request["request_id"], where=where, what="request_id")
    _check_hex64(request["lineage_id"], where=where, what="lineage_id")
    _check_named_binding(request["operator"], where=where, what="operator")
    _check_named_binding(request["target"], where=where, what="target")
    _check_uid_list(request["input_node_uids"], where=where,
                    what="input_node_uids")
    _check_uid_list(request["output_node_uids"], where=where,
                    what="output_node_uids")

    representation = request["representation"]
    if not isinstance(representation, dict):
        raise _fail(where, "representation must be an object")
    extra = set(representation) - {"scheme", "discretization"}
    if extra:
        raise _fail(where,
                    f"representation carries unknown keys {sorted(extra)!r}")
    scheme = representation.get("scheme")
    if not isinstance(scheme, str) or not scheme:
        raise _fail(where, "representation.scheme must be a non-empty string")
    discretization = representation.get("discretization")
    if not isinstance(discretization, dict) or not all(
            isinstance(k, str) and isinstance(v, str)
            for k, v in discretization.items()):
        raise _fail(where, "representation.discretization must be an object "
                           "of string choices")

    if not isinstance(request["lineage"], dict):
        raise _fail(where, "lineage must be an object")

    execution = request.get("execution")
    if execution is not None:
        if not isinstance(execution, dict):
            raise _fail(where, "execution must be an object")
        code = execution.get("code")
        if not isinstance(code, str) or not code:
            raise _fail(where, "execution.code must be a non-empty string "
                               "(the code that runs the solve)")


def _check_hashes(request: dict[str, Any], *, where: str) -> None:
    """The tamper gate: the stated request_id and lineage_id must recompute
    from the payload. Independent recomputation, never trust the claim."""
    recomputed = request_id(request)
    if request["request_id"] != recomputed:
        raise _fail(where,
                    f"stated request_id {str(request['request_id'])[:12]} "
                    f"does not recompute from the payload "
                    f"({recomputed[:12]}): tampered request")
    recomputed_lineage = lineage_id(request["lineage"])
    if request["lineage_id"] != recomputed_lineage:
        raise _fail(where,
                    f"stated lineage_id {str(request['lineage_id'])[:12]} "
                    f"does not recompute from the lineage "
                    f"({recomputed_lineage[:12]}): tampered request")


def parse_request(text: str | bytes, *,
                  where: str = "<request>") -> dict[str, Any]:
    """Parse one wire request: JSON in, shape checked, hashes recomputed.

    Fails closed on malformed JSON, unknown or missing fields, malformed
    values, and a stated request_id or lineage_id that does not recompute.
    Returns the parsed request dict; :func:`validate_request` is the
    separate live-map gate.
    """
    try:
        parsed: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise _fail(where, f"not valid JSON: {exc}") from exc
    _check_shape(parsed, where=where)
    request: dict[str, Any] = parsed
    _check_hashes(request, where=where)
    return request


# --------------------------------------------------------------------------
# The live-map gate (fail-closed, before any dispatch concept exists).
# --------------------------------------------------------------------------

def _check_live(entry: dict[str, Any], *, where: str, what: str) -> None:
    """A stored binding must be live: not deprecated, not superseded."""
    if entry.get("deprecated"):
        raise _fail(where, f"{what} is deprecated"
                           f" ({entry.get('deprecation_note') or 'no note'})")
    superseded = entry.get("superseded_by")
    if superseded:
        raise _fail(where, f"{what} is superseded by "
                           f"{[str(u)[:12] for u in superseded]!r}")


def _downstream_of(edges: dict[str, Any], seeds: list[str]) -> set[str]:
    """Node uids structurally downstream of ``seeds`` over live edges.

    The seeds themselves are included (the frontier's own outputs are the
    boundary). Deprecated and superseded edges provide no reachability.
    Fixed-point iteration over the edge set; the map is small.
    """
    reach = set(seeds)
    changed = True
    while changed:
        changed = False
        for entry in edges.values():
            if entry.get("deprecated") or entry.get("superseded_by"):
                continue
            ident = entry["identity"]
            if any(uid in reach for uid in ident["inputs"]):
                new = set(ident["outputs"]) - reach
                if new:
                    reach |= new
                    changed = True
    return reach


def validate_request(request: dict[str, Any], *,
                     store_root: Path | None = None,
                     where: str = "<request>") -> dict[str, Any]:
    """Validate a request against the current live map, fail-closed.

    Re-runs the shape and tamper gates (a dict handed in directly gets the
    same scrutiny as wire JSON), then checks, in order: the pinned map
    version is the live head (stale and unknown versions fail with distinct
    messages); the operator edge exists, is live, matches its stated name,
    and its stored identity recomputes to its own uid; the request's input
    and output node uid lists equal the stored edge identity lists exactly,
    order included; every referenced node exists and is live; the target
    resolves by name plus uid, its stored identity recomputes to its uid,
    and it is structurally downstream of the frontier's outputs; a lineage
    that names a node names the target. Returns a small report; raises
    :class:`ExternalSolveRequestError` on the first failure.
    """
    _check_shape(request, where=where)
    _check_hashes(request, where=where)

    store = Store(store_root or _MAP_ROOT)
    head = store.head
    version = request["map_version"]
    if version != head:
        try:
            store.read(version)
        except ValueError:
            raise _fail(where, f"unknown map version {version[:12]}: not in "
                               f"the live log") from None
        raise _fail(where, f"stale map version {version[:12]}: the live head "
                           f"is {head[:12]}; re-mint the request against it")

    current = store.read()
    nodes: dict[str, Any] = current["nodes"]
    edges: dict[str, Any] = current["edges"]

    operator = request["operator"]
    edge = edges.get(operator["uid"])
    if edge is None:
        raise _fail(where, f"unknown operator edge {operator['uid'][:12]}: "
                           f"not in the live map")
    _check_live(edge, where=where, what=f"operator edge {operator['uid'][:12]}")
    stored_name = edge["meta"].get("name")
    if stored_name != operator["name"]:
        raise _fail(where, f"operator name {operator['name']!r} does not "
                           f"match the stored edge name {stored_name!r}")
    ident = edge["identity"]
    if edge_uid_from_identity(ident) != operator["uid"]:
        raise _fail(where, f"stored edge identity does not recompute to uid "
                           f"{operator['uid'][:12]}: tampered map view")
    if request["input_node_uids"] != ident["inputs"]:
        raise _fail(where, "input_node_uids do not equal the stored operator "
                           "edge inputs (exact canonical order required)")
    if request["output_node_uids"] != ident["outputs"]:
        raise _fail(where, "output_node_uids do not equal the stored operator "
                           "edge outputs (exact canonical order required)")

    target = request["target"]
    referenced = [*ident["inputs"], *ident["outputs"], target["uid"]]
    for uid in referenced:
        entry = nodes.get(uid)
        if entry is None:
            raise _fail(where, f"unknown node {uid[:12]}: not in the live map")
        _check_live(entry, where=where, what=f"node {uid[:12]}")

    target_entry = nodes[target["uid"]]
    stored_target_name = target_entry["meta"].get("name")
    if stored_target_name != target["name"]:
        raise _fail(where, f"target name {target['name']!r} does not match "
                           f"the stored node name {stored_target_name!r} for "
                           f"uid {target['uid'][:12]}")
    if node_uid_from_identity(target_entry["identity"]) != target["uid"]:
        raise _fail(where, f"stored target identity does not recompute to "
                           f"uid {target['uid'][:12]}: tampered map view")
    if target["uid"] not in _downstream_of(edges, request["output_node_uids"]):
        raise _fail(where, f"target {target['name']!r} is not structurally "
                           f"downstream of the external frontier's outputs")

    lineage = request["lineage"]
    lineage_node = lineage.get("node")
    if lineage_node is not None:
        if lineage_node != target["name"]:
            raise _fail(where, f"lineage.node {lineage_node!r} does not name "
                               f"the request target {target['name']!r}")
        pin = lineage.get("node_uid")
        if pin is not None and pin != target["uid"]:
            raise _fail(where, f"lineage.node_uid pin {str(pin)[:12]} does "
                               f"not match the target uid "
                               f"{target['uid'][:12]}")

    return {
        "request_id": request["request_id"],
        "lineage_id": request["lineage_id"],
        "map_version": head,
        "operator_uid": operator["uid"],
        "target_uid": target["uid"],
    }
