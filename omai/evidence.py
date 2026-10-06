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
starts from, ``conditions.calibration_sha256`` for the calibration a
``SetVoltage`` device model reads. :func:`model_citations` finds and resolves
them.

Registering a record publishes it; the commons holds metadata, hashes and
pointers, never the files. :func:`resolve` looks a uid or an alias up in a
list of roots, in order: a data directory (``docs/data/`` in a source tree) or
a registry file (``omai/data/registry.json``, written by ``omai.map_data`` and
shipped in the wheel, and published as ``docs/data/registry.json``). An
unregistered uid resolves to None; nothing is refused here. The lineage
validators refuse a cited uid that resolves nowhere unless the record lists
it in its top-level ``unregistered`` marker, and :func:`private_reasons` says
why a record cites evidence that is not public.

Code releases are not content-addressed: a code's identity is its name and
release. They are authored in ``releases/<representation>.json`` under the
data root as ``{aliases, releases}``: ``aliases`` the registry row ids that
name the representation (``quantum-espresso`` for ``qe``), ``releases`` an
append-only list of :data:`RELEASE_KEYS`, the licence read at that release's
tag and ``released`` the tag date in UTC (the tagger date of an annotated tag,
else the date of the tagged commit). :func:`code_releases` reads them from the same roots and lists every
representation (``codes.json``), with empty lists where none is registered;
the registry file holds them under ``code``.
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
# starts from. SetVoltage: the calibration file a set-voltage device model
# reads. A node's keys are normally fixed by its first registered record;
# SetVoltage's are fixed by ruling instead, because its calibration stays
# private to its owner and is never registered (a record lists it in
# `unregistered`). Each value is the bare uid, 64 lowercase hex, no "sha256:".
CITATION_KEYS = {"Potential": ("potential_sha256", "base_potential_sha256"),
                 "SetVoltage": ("calibration_sha256",)}
# The nodes whose keys are fixed by ruling: what they cite is never registered,
# so the commons accepts no model record for them.
RULED_NODES = ("SetVoltage",)


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
    # A node without fixed citation keys could not be cited by a lineage; a
    # node whose keys are fixed by ruling cites evidence that is never registered.
    nodes = sorted(set(CITATION_KEYS) - set(RULED_NODES))
    if record.get("node", "Potential") not in nodes:
        raise EvidenceError(f"{where}: node must be one of {nodes}")
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


RELEASE_KEYS = ("version", "tag", "commit", "released", "spdx", "license_source")
_COMMIT = re.compile(r"[0-9a-f]{40}")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def release_files(data_dir: Path) -> dict[str, dict]:
    """``{representation: {aliases, releases}}`` as authored under
    ``<data_dir>/releases/``."""
    return {f.stem: json.loads(f.read_text())
            for f in sorted((Path(data_dir) / "releases").glob("*.json"))}


def check_releases(files: dict[str, dict], representations) -> dict[str, dict]:
    """``{representation: {aliases, releases}}`` for every representation,
    after checking each release file: it names a representation; each alias
    is neither a representation nor another's alias; each release is exactly
    :data:`RELEASE_KEYS`, non-empty strings, ``commit`` 40 lowercase hex,
    ``released`` YYYY-MM-DD, its ``version`` unique within the file; no
    version or tag string names two commits."""
    owner: dict[str, str] = {}
    for rep, doc in files.items():
        where = f"releases/{rep}.json"
        if rep not in representations:
            raise EvidenceError(f"{where}: {rep!r} is not a representation")
        if (not isinstance(doc, dict) or set(doc) != {"aliases", "releases"}
                or not isinstance(doc["aliases"], list)
                or not isinstance(doc["releases"], list) or not doc["releases"]):
            raise EvidenceError(f"{where}: must be {{aliases, releases}} with "
                                f"at least one release")
        for alias in doc["aliases"]:
            if (not isinstance(alias, str) or not alias
                    or alias in representations or alias in owner):
                raise EvidenceError(f"{where}: alias {alias!r} names a "
                                    f"representation or is already an alias")
            owner[alias] = rep
        seen: dict[str, str] = {}
        for r in doc["releases"]:
            if (not isinstance(r, dict) or set(r) != set(RELEASE_KEYS)
                    or not all(isinstance(r[k], str) and r[k] for k in RELEASE_KEYS)
                    or not _COMMIT.fullmatch(r["commit"])
                    or not _DATE.fullmatch(r["released"])):
                raise EvidenceError(f"{where}: a release is {RELEASE_KEYS}, "
                                    f"commit 40 hex, released YYYY-MM-DD")
            for name in {r["version"], r["tag"]}:
                if seen.setdefault(name, r["commit"]) != r["commit"]:
                    raise EvidenceError(f"{where}: {name!r} names two commits")
        versions = [r["version"] for r in doc["releases"]]
        if len(set(versions)) != len(versions):
            raise EvidenceError(f"{where}: a version is registered twice")
    return {rep: files.get(rep) or {"aliases": [], "releases": []}
            for rep in representations}


def code_releases(roots: list[Path] | None = None) -> dict[str, dict]:
    """``{representation: {aliases, releases}}`` for every representation
    of the roots, the first root holding a representation winning."""
    out: dict[str, dict] = {}
    for root in default_roots() if roots is None else roots:
        root = Path(root)
        if root.is_dir():
            files = release_files(root)
            reps = json.loads((root / "codes.json").read_text())
            codes = {rep: files.get(rep) or {"aliases": [], "releases": []}
                     for rep in reps}
        else:
            codes = json.loads(root.read_text()).get("code", {})
        for rep, entry in codes.items():
            out.setdefault(rep, entry)
    return out


def model_citations(lineage: dict, roots: list[Path] | None = None) -> list[dict]:
    """Every model a lineage cites, ``{key, uid, record}``, ``record`` being
    the resolved path or None. A report: an unregistered uid is not refused."""
    conditions = lineage.get("conditions") or {}
    return [{"key": key, "uid": conditions[key],
             "record": resolve("model", conditions[key], roots)}
            for keys in CITATION_KEYS.values() for key in keys
            if key in conditions]


def private_reasons(record, registry: dict | None = None) -> list[dict]:
    """Why a record cites evidence that is not public, ``[{field, kind}]``;
    ``[]`` when it cites none. Fail closed on shape:

    - ``unregistered`` present and not ``[]``: one reason per entry, ``kind``
      the entry's kind (``configuration`` or ``model``, else None); a value
      that is not a list is one reason with kind None.
    - ``overlay_version`` present and not null: kind ``node``.
    - ``lineage.material.configuration`` (``sha256:`` stripped) absent from
      the registry: kind ``configuration``.
    - any key of ``registry["citation_keys"]`` present in
      ``lineage.conditions`` whose value is not a registered model uid:
      ``field`` ``conditions.<key>``, kind ``model``.
    - a record that is not an object: field ``record``, kind None.

    ``registry`` is a registry.json document (default: the one this package
    ships); one whose tables are missing, or whose ``citation_keys`` is not
    exactly :data:`CITATION_KEYS` (same nodes, same keys in order), raises
    ValueError rather than checking fewer keys. A stale copy over-refuses a
    uid registered after it was built; a key bound later makes the copy and
    the library disagree, which raises, so a reader prefers the live
    registry.
    docs/assets/private-members.js is the same predicate for the site;
    ``omai/vectors/private.json`` holds the cases both must agree on.
    """
    if registry is None:
        registry = json.loads(REGISTRY.read_text())
    if not (isinstance(registry, dict)
            and all(isinstance(registry.get(t), dict)
                    for t in ("citation_keys", "configuration", "model"))
            and registry["citation_keys"] == {
                node: list(keys) for node, keys in CITATION_KEYS.items()}):
        raise ValueError("registry lacks configuration or model, or its "
                         "citation_keys is not CITATION_KEYS")
    if not isinstance(record, dict):
        return [{"field": "record", "kind": None}]
    out = []
    if "unregistered" in record:
        listed = record["unregistered"]
        if not isinstance(listed, list):
            out.append({"field": "unregistered", "kind": None})
        for entry in listed if isinstance(listed, list) else []:
            kind = entry.get("kind") if isinstance(entry, dict) else None
            kind = kind if isinstance(kind, str) and kind in KINDS else None
            out.append({"field": "unregistered", "kind": kind})
    if record.get("overlay_version") is not None:
        out.append({"field": "overlay_version", "kind": "node"})
    lineage = record.get("lineage")
    if lineage is None:
        lineage = record.get("recipe")
    lineage = lineage if isinstance(lineage, dict) else {}
    material = lineage.get("material")
    if isinstance(material, dict) and "configuration" in material:
        pin = material["configuration"]
        if isinstance(pin, str) and pin.startswith("sha256:"):
            pin = pin[len("sha256:"):]
        if not (isinstance(pin, str) and pin in registry["configuration"]):
            out.append({"field": "material.configuration", "kind": "configuration"})
    conditions = lineage.get("conditions")
    conditions = conditions if isinstance(conditions, dict) else {}
    for keys in registry["citation_keys"].values():
        for key in keys:
            uid = conditions.get(key)
            if key in conditions and not (isinstance(uid, str)
                                          and uid in registry["model"]):
                out.append({"field": f"conditions.{key}", "kind": "model"})
    return out
