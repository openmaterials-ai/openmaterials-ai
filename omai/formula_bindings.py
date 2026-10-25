"""Reviewed Physlib correspondences, kept outside scientific map identities.

A source correspondence is not an OMAI theorem or implementation validation.
Bindings record their model assumptions separately from any compiled bridge
proof. The package owns this metadata; the website receives an identical copy.

Regenerate: ``python -m omai.formula_bindings``.  Audit source references with
``python -m omai.formula_bindings --check --physlib-path /path/to/pinned/clone``.
Neither operation runs a simulation or changes the map's identity records.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
from functools import lru_cache
from importlib import resources
from pathlib import Path

import jsonschema
import sympy as sp

from omai.operator.identity import edge_id, formula_fingerprint, node_id

_REPO = Path(__file__).resolve().parents[1]
_DATA = resources.files("omai").joinpath("data")
_RELATIONS = ("exact_definition", "conditional", "conceptual")
_ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_resource(name: str) -> dict:
    return json.loads(_DATA.joinpath(name).read_text(encoding="utf-8"))


def catalog_inventory() -> dict[str, list[dict]]:
    """All real domain operators, including zero-input source formulas.

    Graph presentation links are deliberately NOT the operator inventory:
    they omit zero-input operators and include synthetic parameter links.
    """
    from omai.map_data import DOMAINS, build_graph_dict

    graph = build_graph_dict(DOMAINS)
    nodes = [{"id": n["id"], "uid": n["uid"]} for n in graph["nodes"]]
    operators = []
    for domain in DOMAINS:
        for op in domain.edges:
            formula = formula_fingerprint(op.formula)
            operators.append({
                "id": op.name,
                "uid": edge_id(op, node_id),
                "domain": domain.name,
                "formula_sha256": _sha256(formula),
                "formula_latex": sp.latex(op.formula) if op.formula is not None else "",
                "inputs": [space.name for space in op.inputs],
                "outputs": [space.name for space in op.outputs],
            })
    for name, rows in (("nodes", nodes), ("operators", operators)):
        if len({row["id"] for row in rows}) != len(rows):
            raise ValueError(f"duplicate {name} in live catalog")
    return {
        "nodes": sorted(nodes, key=lambda row: row["id"]),
        "operators": sorted(operators, key=lambda row: row["id"]),
    }


def _source_url(upstream: dict, source: dict) -> str:
    return (f"{upstream['repository']}/blob/{upstream['revision']}/"
            f"{source['module'].replace('.', '/')}.lean#L{source['line']}")


def _gap_reason(kind: str, row: dict, inventory: dict, reasons: dict) -> str:
    override = reasons.get(kind + "s", {}).get(row["id"])
    if override:
        return override
    domain_reasons = reasons.get("domains", {})
    domains = ([row["domain"]] if kind == "operator" else sorted({
        op["domain"] for op in inventory["operators"]
        if row["id"] in op["outputs"] or row["id"] in op["inputs"]
    }))
    applicable = list(dict.fromkeys(domain_reasons[d] for d in domains if d in domain_reasons))
    return " ".join(applicable) or (
        "No reviewed formula-level Physlib correspondence at this revision. "
        "This is an explicit bridge coverage gap, not a claim that the quantity is absent upstream."
    )


def _coverage(bindings: list[dict], inventory: dict) -> dict:
    return {
        "nodes_total": len(inventory["nodes"]),
        "nodes_mapped": sum(bool(row["binding_ids"]) for row in inventory["nodes"]),
        "operators_total": len(inventory["operators"]),
        "operators_mapped": sum(bool(row["binding_ids"]) for row in inventory["operators"]),
        "bindings_total": len(bindings),
        "source_correspondences": sum(b["evidence"]["kind"] == "source_correspondence" for b in bindings),
        "compiled_bridges": sum(b["evidence"]["kind"] == "compiled_bridge" for b in bindings),
        "relations": {relation: sum(b["relation"] == relation for b in bindings)
                      for relation in _RELATIONS},
    }


def build_formula_bindings(seeds: dict | None = None) -> dict:
    """Bind reviewed source metadata to the live, immutable scientific IDs."""
    seeds = copy.deepcopy(seeds if seeds is not None else _read_resource("physlib_formula_seeds.json"))
    if seeds.get("schema_version") != 1:
        raise ValueError("unsupported formula seed schema_version")
    inventory = catalog_inventory()
    lookup = {(kind, row["id"]): row for kind, key in (("node", "nodes"), ("operator", "operators"))
              for row in inventory[key]}
    reasons = seeds.get("gap_reasons", {})
    for kind in ("node", "operator"):
        unknown = set(reasons.get(kind + "s", {})) - {key[1] for key in lookup if key[0] == kind}
        if unknown:
            raise ValueError(f"unknown {kind} gap targets: {sorted(unknown)}")
    known_domains = {row["domain"] for row in inventory["operators"]}
    if set(reasons.get("domains", {})) - known_domains:
        raise ValueError("unknown domain gap reason")
    bindings = seeds["bindings"]
    by_target: dict[tuple[str, str], list[str]] = {}
    for binding in bindings:
        for target in binding["targets"]:
            key = (target["kind"], target["id"])
            if key not in lookup:
                raise ValueError(f"unknown formula binding target {key}")
            row = lookup[key]
            if target.get("uid") != row["uid"]:
                raise ValueError(f"reviewed target UID missing or stale; re-review required: {key}")
            if (target["kind"] == "operator"
                    and target.get("formula_sha256") != row["formula_sha256"]):
                raise ValueError(f"reviewed formula fingerprint missing or stale; re-review required: {key}")
            by_target.setdefault(key, []).append(binding["id"])
        binding["targets"].sort(key=lambda target: (target["kind"], target["id"]))
        for source in binding["sources"]:
            source["source_url"] = _source_url(seeds["upstream"], source)
    bindings.sort(key=lambda binding: binding["id"])
    for kind, key in (("node", "nodes"), ("operator", "operators")):
        for row in inventory[key]:
            row["binding_ids"] = sorted(by_target.get((kind, row["id"]), []))
            row["status"] = "mapped" if row["binding_ids"] else "gap"
            row["reason"] = ("Reviewed correspondence; see each binding's conditions and evidence."
                             if row["binding_ids"] else _gap_reason(kind, row, inventory, reasons))
    payload = {
        "schema_version": 1,
        "upstream": seeds["upstream"],
        "bindings": bindings,
        "inventory": inventory,
        "coverage": _coverage(bindings, inventory),
    }
    validate_formula_bindings(payload, check_catalog=True)
    return payload


def _check_compiled_evidence(binding: dict, upstream: dict, root: Path) -> None:
    evidence = binding["evidence"]
    if binding["relation"] == "conceptual":
        raise ValueError("conceptual reference cannot claim a compiled formula bridge")
    bridge_root = root / "lean" / "bridge"
    source = root / evidence["source_path"]
    record_path = root / evidence["build_record"]
    for path in (source, record_path):
        if not path.resolve().is_relative_to(bridge_root.resolve()):
            raise ValueError("compiled bridge paths must remain in lean/bridge")
    module = ".".join(source.relative_to(bridge_root).with_suffix("").parts)
    if evidence["module"] != module:
        raise ValueError("compiled bridge module does not match source path")
    actual = hashlib.sha256(source.read_bytes()).hexdigest()
    if actual != evidence["source_sha256"]:
        raise ValueError(f"compiled bridge source hash mismatch: {binding['id']}")
    record = json.loads(record_path.read_text())
    if (record.get("status") != "passed" or record.get("command") != "lake build --wfail"
            or record.get("upstream_revision") != upstream["revision"]
            or record.get("lean_toolchain") != upstream["lean_toolchain"]
            or record.get("sources", {}).get(evidence["source_path"]) != actual):
        raise ValueError(f"missing matching successful bridge build: {binding['id']}")
    hashes = record["sources"]
    required = {
        str(path.relative_to(root)) for path in bridge_root.rglob("*.lean")
        if ".lake" not in path.relative_to(bridge_root).parts
    } | {"lean/bridge/" + name for name in (
        "lean-toolchain", "lakefile.toml", "lake-manifest.json", "semantic-formula-contract.json",
    )}
    if not required <= hashes.keys():
        raise ValueError("build record omits proof source/configuration/endpoint dependencies")
    for relative, digest in hashes.items():
        path = root / relative
        if (not path.resolve().is_relative_to(bridge_root.resolve())
                or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest):
            raise ValueError(f"compiled dependency hash mismatch: {relative}")
    audit = record.get("axiom_audit", {})
    declarations = audit.get("declarations", {})
    if (audit.get("status") != "passed" or not declarations
            or audit.get("declaration_count") != len(declarations)
            or not isinstance(audit.get("theorem_count"), int)
            or not 0 < audit["theorem_count"] <= len(declarations)
            or set(audit.get("allowed_axioms", [])) != _ALLOWED_AXIOMS
            or any(set(axioms) - _ALLOWED_AXIOMS for axioms in declarations.values())
            or not set(evidence["declarations"]) <= declarations.keys()):
        raise ValueError("compiled bridge lacks a complete successful approved-axiom audit")
    manifest = json.loads((bridge_root / "lake-manifest.json").read_text())
    dependencies = {item["name"].lower(): item["rev"] for item in manifest["packages"]}
    if record.get("dependencies") != dependencies or dependencies.get("physlib") != upstream["revision"]:
        raise ValueError("compiled dependency revisions do not match the pinned manifest")
    if (bridge_root / "lean-toolchain").read_text().strip() != upstream["lean_toolchain"]:
        raise ValueError("compiled toolchain does not match bridge source metadata")
    text = source.read_text()
    for declaration in evidence["declarations"]:
        leaf = declaration.rsplit(".", 1)[-1]
        if not re.search(r"\b(?:theorem|lemma)\s+" + re.escape(leaf) + r"(?=\s|[({:]|$)", text):
            raise ValueError(f"bridge declaration absent from compiled source: {declaration}")


def validate_formula_bindings(payload: dict, *, check_catalog: bool = False,
                              proof_root: Path | None = None) -> None:
    """Validate evidence boundaries; optionally check live catalog/proof bytes.

    Static metadata validation is not Lean proof checking. ``proof_root``
    verifies the recorded build provenance; reproducibility still requires
    running the pinned Lean package's build command.
    """
    jsonschema.Draft202012Validator(_read_resource("formula_bindings.schema.json")).validate(payload)
    bindings = payload["bindings"]
    if len({binding["id"] for binding in bindings}) != len(bindings):
        raise ValueError("duplicate binding ID")
    inventory = payload["inventory"]
    lookup = {}
    for kind, key in (("node", "nodes"), ("operator", "operators")):
        for row in inventory[key]:
            identity = (kind, row["id"])
            if identity in lookup:
                raise ValueError(f"duplicate inventory target: {identity}")
            lookup[identity] = row
    expected: dict[tuple[str, str], list[str]] = {key: [] for key in lookup}
    for binding in bindings:
        targets = [(target["kind"], target["id"]) for target in binding["targets"]]
        if len(set(targets)) != len(targets):
            raise ValueError(f"duplicate binding target: {binding['id']}")
        for target, key in zip(binding["targets"], targets, strict=True):
            if key not in lookup or target["uid"] != lookup[key]["uid"]:
                raise ValueError(f"unknown or stale target UID: {key}")
            if key[0] == "operator" and target["formula_sha256"] != lookup[key]["formula_sha256"]:
                raise ValueError(f"stale operator formula: {key}")
            expected[key].append(binding["id"])
        if binding["relation"] == "conditional" and not binding["conditions"]:
            raise ValueError("conditional correspondence requires explicit conditions")
        if (binding["evidence"]["kind"] == "source_correspondence"
                and not binding["remaining_obligations"]):
            raise ValueError("uncompiled correspondence must disclose remaining bridge obligations")
        if binding["relation"] == "conceptual" and binding["evidence"]["kind"] == "compiled_bridge":
            raise ValueError("conceptual reference cannot claim a compiled formula bridge")
        declarations = [(source["module"], source["name"]) for source in binding["sources"]]
        if len(set(declarations)) != len(declarations):
            raise ValueError(f"duplicate source declaration: {binding['id']}")
        for source in binding["sources"]:
            if source["source_url"] != _source_url(payload["upstream"], source):
                raise ValueError("source URL does not match pinned upstream")
        if proof_root is not None and binding["evidence"]["kind"] == "compiled_bridge":
            _check_compiled_evidence(binding, payload["upstream"], proof_root)
    for key, row in lookup.items():
        if row["binding_ids"] != sorted(expected[key]):
            raise ValueError(f"inconsistent inventory binding IDs: {key}")
        if row["status"] != ("mapped" if expected[key] else "gap"):
            raise ValueError(f"inconsistent coverage status: {key}")
    if payload["coverage"] != _coverage(bindings, inventory):
        raise ValueError("coverage counts do not match bindings and inventory")
    if check_catalog:
        actual = catalog_inventory()
        for kind, key in (("node", "nodes"), ("operator", "operators")):
            if {row["id"] for row in inventory[key]} != {row["id"] for row in actual[key]}:
                raise ValueError(f"{kind} inventory does not match live catalog")
            for row in actual[key]:
                stored = lookup[(kind, row["id"])]
                if any(stored[field] != value for field, value in row.items()):
                    raise ValueError(f"stale live catalog binding: {kind} {row['id']}")


def verify_source_references(payload: dict, physlib_path: Path) -> None:
    """Check pinned clone revision and exact declaration start lines, not proofs."""
    revision = subprocess.run(["git", "-C", str(physlib_path), "rev-parse", "HEAD"],
                              check=True, capture_output=True, text=True).stdout.strip()
    if revision != payload["upstream"]["revision"]:
        raise ValueError("Physlib clone revision differs from reviewed source revision")
    changed = subprocess.run(["git", "-C", str(physlib_path), "diff", "--name-only", "HEAD", "--", "Physlib"],
                             check=True, capture_output=True, text=True).stdout.strip()
    if changed:
        raise ValueError("Physlib sources differ from the reviewed pinned commit")
    tracked = set(subprocess.run(
        ["git", "-C", str(physlib_path), "ls-tree", "-r", "--name-only", "HEAD", "Physlib"],
        check=True, capture_output=True, text=True,
    ).stdout.splitlines())
    seen = set()
    for binding in payload["bindings"]:
        for source in binding["sources"]:
            key = (source["module"], source["name"], source["line"], source["kind"])
            if key in seen:
                continue
            seen.add(key)
            relative = source["module"].replace(".", "/") + ".lean"
            if relative not in tracked:
                raise ValueError(f"source module is absent from the pinned commit: {source['module']}")
            path = physlib_path / relative
            lines = path.read_text().splitlines()
            leaf = source["name"].rsplit(".", 1)[-1]
            pattern = (r"\b" + re.escape(source["kind"]) + r"\s+" + re.escape(leaf)
                       + r"(?=\s|[({:]|$)")
            if source["line"] > len(lines) or not re.search(pattern, lines[source["line"] - 1]):
                raise ValueError(f"source declaration/line mismatch: {source['name']}")


@lru_cache(maxsize=1)
def _packaged_bindings() -> dict:
    payload = _read_resource("formula_bindings.json")
    validate_formula_bindings(payload)
    return payload


def formula_bindings_for(element_id: str, *, kind: str | None = None) -> list[dict]:
    """Reviewed bindings for a quantity/operator; empty list is a coverage gap.

    ``kind`` is ``node`` or ``operator`` (the resolver's ``edge`` is accepted).
    Return isolated data so callers cannot mutate the shared packaged metadata.
    """
    if kind == "edge":
        kind = "operator"
    if kind not in (None, "node", "operator"):
        raise ValueError("kind must be node or operator")
    return copy.deepcopy([
        binding for binding in _packaged_bindings()["bindings"]
        if any(target["id"] == element_id and (kind is None or target["kind"] == kind)
               for target in binding["targets"])
    ])


def write_formula_bindings() -> dict:
    """Regenerate package and site metadata, preserving all scientific records."""
    payload = build_formula_bindings()
    validate_formula_bindings(payload, proof_root=_REPO)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    for path in (_REPO / "omai/data/formula_bindings.json", _REPO / "docs/data/formula_bindings.json"):
        path.write_text(text)
    _packaged_bindings.cache_clear()
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check committed artifacts without writing")
    parser.add_argument("--physlib-path", type=Path, help="read-only pinned source clone for declaration audit")
    args = parser.parse_args()
    payload = build_formula_bindings()
    validate_formula_bindings(payload, check_catalog=True, proof_root=_REPO)
    if args.physlib_path is not None:
        verify_source_references(payload, args.physlib_path)
    if args.check:
        expected = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        for path in (_REPO / "omai/data/formula_bindings.json", _REPO / "docs/data/formula_bindings.json"):
            if path.read_text() != expected:
                raise SystemExit(f"stale generated bridge metadata: {path}")
    else:
        write_formula_bindings()
    print(json.dumps(payload["coverage"], sort_keys=True))


if __name__ == "__main__":
    main()
