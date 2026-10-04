"""Content-addressed evidence records: one resolver for every kind.

A kind is defined by its identity rule. Its records live one file per record
under ``<data root>/<directory>/`` and state their uid at a fixed path, with
any former uids beside it under ``aliases``:

- ``configuration``: an atomic structure (:mod:`omai.configurations`), uid at
  ``canonical.uid``, minted by ``canonical_uid``.
- ``model``: parameters a code reads, uid at ``uid``, minted by
  :func:`model_uid` over the files the evaluating code reads. A record names
  the map node it serves (``node``, default ``Potential``), so a CALPHAD
  database or a cluster-expansion coefficient file needs no new kind.

The table below holds where a kind's records live, not its identity function:
:func:`check` reproduces a model uid with :func:`model_uid`, and a
configuration uid needs spglib (``omai.configurations``).

A model record is ``{uid, node, name, release_label?, family, format, files,
elements, license, citation, doi, provenance}``. ``files`` are pointers
``{path, role, sha256, bytes, url?}``: role ``model`` for a file the uid
covers, ``training_state`` for one it does not (a NEP restart file, a
training checkpoint). ``license`` is ``{spdx, license_source}``, ``spdx`` an
SPDX expression, a ``LicenseRef-*`` or ``NOASSERTION``. ``provenance`` is an
append-only list of ``{kind, ref, detail}``. The uid identifies parameters,
not an energy surface: a head or task selection, the evaluation dtype and a
dispersion term added at run time are lineage conditions.

A lineage cites a model by bare uid under its node's fixed keys
(:data:`CITATION_KEYS`): ``conditions.potential_sha256`` for the model it
evaluates, ``conditions.base_potential_sha256`` for the model a training run
starts from. :func:`model_citations` finds and resolves them.

Registering a record publishes it; the commons holds metadata, hashes and
pointers, never the files. :func:`resolve` looks a uid or an alias up in a
list of roots, in order: a data directory (``docs/data/`` in a source tree) or
a registry file (``omai/data/registry.json``, written by ``omai.map_data`` and
shipped in the wheel). An unregistered uid resolves to None; nothing is
refused here.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import NamedTuple

_PACKAGE = Path(__file__).resolve().parent
_DATA_DIR = _PACKAGE.parent / "docs" / "data"
REGISTRY = _PACKAGE / "data" / "registry.json"

MODEL_ROLES = ("model", "training_state")
_HEX64 = re.compile(r"[0-9a-f]{64}")

# The fixed keys under lineage.conditions that cite a model, one set per node a
# model serves, the same for every representation so a model compares across
# codes. Potential: the model a lineage evaluates, and the model a training run
# starts from. Each value is the bare uid, 64 lowercase hex, no "sha256:".
CITATION_KEYS = {"Potential": ("potential_sha256", "base_potential_sha256")}


class EvidenceError(Exception):
    """A record is malformed or does not reproduce its uid."""


def model_uid(digests: list[str]) -> str:
    """The uid of a model from the sha256 of each file of role ``model``.

    One file: its sha256, the bytes the evaluating code reads. Several (SNAP,
    GAP, MEAM): the sha256 of the canonical JSON ``{"files": [...]}``,
    digests sorted. ``training_state`` files never enter.
    """
    if not digests:
        raise EvidenceError("a model has at least one file of role 'model'")
    if len(digests) == 1:
        return digests[0]
    blob = json.dumps({"files": sorted(digests)}, sort_keys=True,
                      separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class Kind(NamedTuple):
    directory: str
    uid_path: tuple[str, ...]


KINDS = {
    "configuration": Kind("configurations", ("canonical", "uid")),
    "model": Kind("models", ("uid",)),
}


def record_uids(kind: str, record: dict) -> list:
    """``[uid, *aliases]``: the uid a record states at its kind's uid path,
    then the former uids it keeps beside it under ``aliases``."""
    *parents, key = KINDS[kind].uid_path
    for parent in parents:
        record = record.get(parent) if isinstance(record, dict) else None
    if not isinstance(record, dict):
        return [None]
    return [record.get(key), *(record.get("aliases") or [])]


def records(kind: str, data_dir: Path) -> list[tuple[str, dict]]:
    """``(path relative to data_dir, record)`` for every record of a kind."""
    directory = KINDS[kind].directory
    return [(f"{directory}/{f.name}", json.loads(f.read_text()))
            for f in sorted((Path(data_dir) / directory).glob("*.json"))]


def check(kind: str, record: dict, *, where: str) -> str:
    """A record's uid, after the checks its kind defines.

    Every kind: the uid and each alias are 64 lowercase hex. A model
    additionally reproduces its uid from its files (configurations reproduce
    theirs through ``omai.configurations``, which needs spglib).
    """
    uids = record_uids(kind, record)
    if not all(isinstance(u, str) and _HEX64.fullmatch(u) for u in uids):
        raise EvidenceError(f"{where}: uid and aliases must be 64 lowercase hex")
    uid = uids[0]
    if kind == "model":
        _check_model(record, uid, where=where)
    return uid


def _check_model(record: dict, uid: str, *, where: str) -> None:
    from omai.lineages import LineageError, _validate_manifest

    for key in ("name", "family", "format", "citation"):
        if not isinstance(record.get(key), str) or not record[key]:
            raise EvidenceError(f"{where}: {key} must be a non-empty string")
    # A node without fixed citation keys could not be cited by a lineage.
    if record.get("node", "Potential") not in CITATION_KEYS:
        raise EvidenceError(f"{where}: node must be one of {sorted(CITATION_KEYS)}")
    files = record.get("files")
    try:
        _validate_manifest(files, where=where)
    except LineageError as exc:
        raise EvidenceError(str(exc)) from None
    roles = {f["role"] for f in files}
    if not roles <= set(MODEL_ROLES):
        raise EvidenceError(f"{where}: file roles must be in {MODEL_ROLES}")
    digests = [f["sha256"] for f in files if f["role"] == "model"]
    if model_uid(digests) != uid:
        raise EvidenceError(
            f"{where}: uid {uid[:12]} is not the uid of its model files "
            f"{model_uid(digests)[:12]}")
    elements = record.get("elements")
    if (not isinstance(elements, list) or not elements
            or elements != sorted(set(elements))):
        raise EvidenceError(f"{where}: elements must be a sorted, unique, "
                            f"non-empty list")
    lic = record.get("license")
    if (not isinstance(lic, dict) or set(lic) != {"spdx", "license_source"}
            or not all(isinstance(v, str) and v for v in lic.values())):
        raise EvidenceError(f"{where}: license must be {{spdx, license_source}}")
    prov = record.get("provenance")
    if (not isinstance(prov, list) or not prov
            or not all(isinstance(p, dict) and {"kind", "ref"} <= set(p)
                       for p in prov)):
        raise EvidenceError(f"{where}: provenance must be a non-empty list of "
                            f"{{kind, ref, detail}}")


def default_roots() -> list[Path]:
    """``docs/data/`` in a source tree, else the registry the wheel ships."""
    return [_DATA_DIR] if _DATA_DIR.is_dir() else [REGISTRY]


def resolve(kind: str, uid: str, roots: list[Path] | None = None) -> str | None:
    """Where a registered uid or alias lives, as the record's path under its
    data root (``models/nep89-20250409.json``); None when no root registers
    it. A root that does not exist raises FileNotFoundError."""
    for root in default_roots() if roots is None else roots:
        root = Path(root)
        if root.is_dir():
            # ponytail: rescans the directory per call; index it once if a
            # validator resolves many uids in a loop.
            for path, record in records(kind, root):
                if uid in record_uids(kind, record):
                    return path
        else:
            hit = json.loads(root.read_text()).get(kind, {}).get(uid)
            if hit is not None:
                return hit
    return None


def model_citations(lineage: dict, roots: list[Path] | None = None) -> list[dict]:
    """Every model a lineage cites, ``{key, uid, record}``, ``record`` being
    the resolved path or None. A report: an unregistered uid is not refused."""
    conditions = lineage.get("conditions") or {}
    return [{"key": key, "uid": conditions[key],
             "record": resolve("model", conditions[key], roots)}
            for keys in CITATION_KEYS.values() for key in keys
            if key in conditions]
