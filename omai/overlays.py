"""Private overlays: an owner's additions to the map, kept by the owner.

An overlay is a directory laid out as a data root (``docs/data/``) plus three
files:

- ``overlay.json``: ``{namespace, base_graph_version}``, the public store head
  the overlay is validated against.
- ``map.json``: its map part, a contribution ``[{op, payload}]`` of
  ``add_node`` and ``add_edge`` only, in the ``map/log.jsonl`` payload shape.
- ``registry.json``: the vocabulary the contribution adds, in the tables of
  :data:`omai.gates.VOCABULARY` (``symbol_dimensions`` maps a symbol to its
  seven SI exponents, M L T Th N I J).

and, as under ``docs/data/``, ``codes.json`` (its representations, credits
included), ``releases/``, ``configurations/`` and ``models/``. Names carry the
namespace (``ns:Name`` for a node, ``ns:code`` for a representation, whose
releases live at ``releases/<ns>/<code>.json``); identity never does, so a
node keeps its uid when published and keeps ``ns:Name`` among its ``names``.
``overlay_version`` is computed, never stored.

``roots`` list the public root first, then overlays. :func:`load` checks every
overlay among them; each lineage validator and writer given ``roots`` runs it,
so a record is never checked against a refused overlay.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import NamedTuple

from omai.evidence import EvidenceError
from omai.operator.identity import canonical_json

_STORE = Path(__file__).resolve().parents[1] / "map"
_NAMESPACE = re.compile(r"[a-z0-9][a-z0-9-]*")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_OPS = ("add_node", "add_edge")

__all__ = ["Overlay", "OverlayError", "load", "overlay_version"]


class OverlayError(EvidenceError):
    """An overlay is malformed, or holds what the public map or another
    loaded overlay holds."""


class Overlay(NamedTuple):
    root: Path
    namespace: str
    base: str     # base_graph_version
    version: str  # overlay_version
    names: dict   # ns:Name -> node uid


def overlay_version(root) -> str:
    """The sha256 of the canonical JSON ``{"base": base_graph_version,
    "files": [[path, sha256], ...]}`` over every file of the overlay except
    ``overlay.json`` and hidden ones (a path component starting with "."),
    paths relative, POSIX and sorted."""
    root = Path(root)
    base = json.loads((root / "overlay.json").read_text())["base_graph_version"]
    files = sorted([p.relative_to(root).as_posix(),
                    hashlib.sha256(p.read_bytes()).hexdigest()]
                   for p in root.rglob("*") if p.is_file()
                   and not any(part.startswith(".") for part in p.relative_to(root).parts))
    blob = canonical_json({"base": base,
                           "files": [f for f in files if f[0] != "overlay.json"]})
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _read(path: Path, default):
    return json.loads(path.read_text()) if path.is_file() else default


def load(roots) -> list[Overlay]:
    """Every overlay among ``roots`` (a directory holding ``overlay.json``),
    checked; the other roots are the public ones (default:
    :func:`omai.evidence.default_roots`). Refused, as :class:`OverlayError`:

    - a malformed ``overlay.json`` (namespace lowercase alphanumerics and
      hyphens), or two overlays with one namespace;
    - a vocabulary entry the public registries or an earlier overlay holds;
    - a map part that is not add-only, a node not named ``ns:Name``, or one
      failing ``validate_contribution`` against the public map at
      ``base_graph_version`` with the public vocabulary plus the overlay's
      (where ``map/`` exists; the wheel ships no map log);
    - a node, edge, configuration or model whose uid is public (cite the
      public one);
    - a code not named ``ns:code`` or not credited (citation and license on
      every node it covers), or covering a node neither the public map at the
      base (the live map where ``map/`` is absent) nor the overlay holds; a
      malformed release file; one (code, version)
      naming two commits, or one alias naming two codes, across all roots.
    """
    from omai.evidence import (
        KINDS,
        check,
        check_releases,
        code_releases,
        default_roots,
        record_uids,
        records,
        release_files,
        resolve,
    )
    from omai.gates import VOCABULARY
    from omai.map_data import _domains

    roots = [Path(r) for r in roots or ()]
    paths = [r for r in roots if (r / "overlay.json").is_file()]
    if not paths:
        return []
    _domains()  # the domains register the public symbol dimensions on import
    public = [r for r in roots if r not in paths] or default_roots()
    public_codes = code_releases(public)
    commits: dict = {}
    owners: dict = {}
    _union(public_codes, "the public root", commits, owners)
    held = VOCABULARY
    out: list[Overlay] = []
    for root in paths:
        meta = _read(root / "overlay.json", None)
        ns = meta.get("namespace") if isinstance(meta, dict) else None
        base = meta.get("base_graph_version") if isinstance(meta, dict) else None
        if (set(meta or ()) != {"namespace", "base_graph_version"}
                or not (isinstance(ns, str) and _NAMESPACE.fullmatch(ns))
                or not (isinstance(base, str) and _HEX64.fullmatch(base))):
            raise OverlayError(f"{root}/overlay.json must be {{namespace, "
                               f"base_graph_version}}: a lowercase namespace of "
                               f"alphanumerics and hyphens, a 64-hex base")
        where = f"overlay {ns!r}"
        if ns in {o.namespace for o in out}:
            raise OverlayError(f"{where}: another loaded overlay holds this namespace")
        added = _read(root / "registry.json", {})
        held = _vocabulary(held, added, where)
        names, public_names = _check_map(_read(root / "map.json", []), ns, base,
                                         _vocabulary(VOCABULARY, added, where), where)
        codes = _read(root / "codes.json", {})
        if not isinstance(codes, dict) or not all(
                code.startswith(f"{ns}:") and isinstance(nodes, dict) and nodes
                and all(isinstance(e, dict) and isinstance(e.get(k), str) and e[k]
                        for e in nodes.values() for k in ("citation", "license"))
                for code, nodes in codes.items()):
            raise OverlayError(f"{where}: codes.json names each code '{ns}:code' "
                               f"and credits it (citation, license) on every node")
        for code, nodes in codes.items():
            for node in nodes:
                if node not in names and node not in public_names:
                    raise OverlayError(f"{where}: {code} covers {node!r}, which "
                                       f"neither the public map nor the overlay holds")
        try:
            check_releases(release_files(root), [*public_codes, *codes])
            for kind in KINDS:
                for path, record in records(kind, root):
                    check(kind, record, where=path)
                    public_uid = next((u for u in record_uids(kind, record)
                                       if resolve(kind, u, public)), None)
                    if public_uid:
                        raise OverlayError(
                            f"{path} is public (uid {public_uid[:12]}): remove the "
                            f"overlay copy and cite the public record")
        except EvidenceError as exc:
            raise OverlayError(f"{where}: {exc}") from None
        _union(code_releases([root]), where, commits, owners)
        out.append(Overlay(root, ns, base, overlay_version(root), names))
    return out


def _vocabulary(base: dict, added, where: str) -> dict:
    """``base`` (the tables of :data:`omai.gates.VOCABULARY`) extended by an
    overlay's ``registry.json``; an entry ``base`` holds is refused (for a
    label, a value its key already has)."""
    from omai.operator.dimensions import Dimension

    if not isinstance(added, dict) or not set(added) <= set(base) or not all(
            isinstance(t, dict) for t in added.values()):
        raise OverlayError(f"{where}: registry.json holds tables of {sorted(base)}")
    out = {table: dict(entries) for table, entries in base.items()}
    for table, entries in added.items():
        for key, value in entries.items():
            if table == "label_keys":
                ok = isinstance(value, list) and all(isinstance(v, str) for v in value)
                fresh = ok and not out[table].get(key, frozenset()) & set(value)
                value = out[table].get(key, frozenset()) | set(value) if ok else None
            else:
                if table == "symbol_dimensions":
                    ok = (isinstance(value, list) and len(value) == 7
                          and all(type(v) is int for v in value))
                    value = Dimension(key, tuple(value)) if ok else None
                else:
                    ok = isinstance(value, str) and bool(value)
                fresh = key not in out[table] and not (
                    table == "index_kinds" and value in out[table].values())
            if not ok:
                raise OverlayError(f"{where}: registry.json {table} {key!r} is malformed")
            if not fresh:
                raise OverlayError(f"{where}: registry.json {table} {key!r} is held "
                                   f"by the public registry or another overlay")
            out[table][key] = value
    return out


def _check_map(contribution, ns: str, base: str, vocabulary: dict,
               where: str) -> tuple[dict, set]:
    """``{ns:Name: uid}`` for the nodes an overlay's map part adds, after its
    checks, and the public node names at the base (the live map's where
    ``map/`` is absent)."""
    from omai.gates import no_op_indices, validate_contribution
    from omai.store import Store

    if not isinstance(contribution, list) or not all(
            isinstance(r, dict) and r.get("op") in _OPS
            and isinstance(r.get("payload"), dict)
            and all(isinstance(r["payload"].get(k), dict) for k in ("identity", "meta"))
            for r in contribution):
        raise OverlayError(f"{where}: map.json is a contribution [{{op, payload}}] "
                           f"of {' and '.join(_OPS)} only")
    names: dict = {}
    for r in contribution:
        name = r["payload"]["meta"].get("name")
        if r["op"] == "add_node":
            if not (isinstance(name, str) and name.startswith(f"{ns}:")) or name in names:
                raise OverlayError(f"{where}: node {name!r} needs a unique name "
                                   f"starting '{ns}:'")
            names[name] = r["payload"].get("uid")
    if not (_STORE / "log.jsonl").is_file():
        from omai.map_data import _domains
        return names, {n for d in _domains()
                       for n in (*(s.name for s in d.nodes),
                                 *(p[0] for p in d.param_promotions))}
    try:
        current = Store(_STORE).read(base)
    except ValueError:
        raise OverlayError(f"{where}: base_graph_version {base[:12]} is not a "
                           f"version of the public map") from None
    problems = validate_contribution(contribution, current, vocabulary)
    if problems:
        raise OverlayError(f"{where}: map.json: " + "; ".join(problems))
    if no_op_indices(contribution, current):
        raise OverlayError(f"{where}: map.json adds a uid the public map holds "
                           f"at its base; cite the public one")
    return names, {e["meta"].get("name") for e in current["nodes"].values()}


def _union(codes: dict, where: str, commits: dict, owners: dict) -> None:
    """Add a root's releases to the union across roots: one (code, version or
    tag) names one commit, one alias names one code."""
    for rep, entry in codes.items():
        for alias in entry["aliases"]:
            if owners.setdefault(alias, rep) != rep:
                raise OverlayError(f"{where}: alias {alias!r} already names "
                                   f"{owners[alias]!r}")
        for r in entry["releases"]:
            for name in {r["version"], r["tag"]}:
                if commits.setdefault((rep, name), r["commit"]) != r["commit"]:
                    raise OverlayError(f"{where}: {rep} {name!r} names two commits")
