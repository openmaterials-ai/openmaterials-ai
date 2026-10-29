"""Reviewed Physlib correspondences and local Lean proofs, kept outside map identities.

A source correspondence is not an OMAI theorem or implementation validation.
Bindings record their model assumptions separately from any compiled bridge
proof. A ``local`` binding is a compiled theorem about an OMAI formula that has
no Physlib physics counterpart; it cites no Physlib source and is counted
separately from Physlib-anchored proofs. The package owns this metadata; the website receives an identical copy.

Regenerate: ``python -m omai.formula_bindings``.  Audit source references with
``python -m omai.formula_bindings --check --physlib-path /path/to/pinned/clone``.
Neither operation runs a simulation or changes the map's identity records.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
import tempfile
from functools import lru_cache
from importlib import resources
from pathlib import Path

import jsonschema
import sympy as sp

from omai.operator.identity import edge_id, formula_fingerprint, node_id

_REPO = Path(__file__).resolve().parents[1]
_DATA = resources.files("omai").joinpath("data")
_RELATIONS = ("exact_definition", "conditional", "conceptual", "local")
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
        "The quantity may still occur elsewhere in Physlib."
    )


def compiled_targets(binding: dict, inventory: dict) -> list[dict]:
    """Subjects of a compiled formula bridge, not every associated input.

    Authors can state a narrower scope or a standalone quantity interpretation
    in ``evidence.proved_targets``. Otherwise the scope consists of the bound
    operators and their bound output quantities. An input reference does not
    prove that input's producing formula.
    """
    if binding["evidence"]["kind"] != "compiled_bridge":
        return []
    if "proved_targets" in binding["evidence"]:
        return copy.deepcopy(binding["evidence"]["proved_targets"])
    operators = {target["id"] for target in binding["targets"] if target["kind"] == "operator"}
    outputs = {output for row in inventory["operators"] if row["id"] in operators
               for output in row["outputs"]}
    return [{"kind": target["kind"], "id": target["id"]} for target in binding["targets"]
            if target["kind"] == "operator" or target["id"] in outputs]


def physlib_declaration_index(payload: dict | None = None) -> list[dict]:
    """Unique upstream declarations with every referring OMAI binding ID.

    This is an index of reviewed references, not an inventory of all Physlib
    declarations and not a claim that a declaration has an inverse formula.
    """
    payload = _packaged_bindings() if payload is None else payload
    declarations: dict[tuple[str, str], dict] = {}
    for binding in payload["bindings"]:
        for source in binding["sources"]:
            key = (source["module"], source["name"])
            row = declarations.setdefault(key, {**source, "binding_ids": []})
            if {key: value for key, value in row.items() if key != "binding_ids"} != source:
                raise ValueError(f"inconsistent metadata for upstream declaration: {key}")
            if binding["id"] not in row["binding_ids"]:
                row["binding_ids"].append(binding["id"])
    for row in declarations.values():
        row["binding_ids"].sort()
    return copy.deepcopy([declarations[key] for key in sorted(declarations)])


def _row_status(binding_ids: list[str], relations: dict[str, str]) -> str:
    """``mapped`` when a Physlib-anchored binding references the row, ``local`` when
    only local bindings do, ``gap`` otherwise."""
    if not binding_ids:
        return "gap"
    return "local" if all(relations[i] == "local" for i in binding_ids) else "mapped"


_LOCAL_REASON = " A local Lean proof over Mathlib covers it under that binding's conditions; see its conditions and evidence."


def _coverage(bindings: list[dict], inventory: dict) -> dict:
    """Physlib-anchored counts keep their original meaning; local proofs are counted apart.

    ``*_mapped`` and ``*_compiled`` count only bindings that cite Physlib. ``*_local``
    counts rows referenced only by local bindings, ``*_compiled_local`` the local proof
    subjects not already proved with a Physlib anchor, and ``*_proved`` the union.
    """
    relations = {binding["id"]: binding["relation"] for binding in bindings}
    anchored = [binding for binding in bindings if binding["relation"] != "local"]
    proved = {(target["kind"], target["id"]) for binding in anchored
              for target in compiled_targets(binding, inventory)}
    local_proved = {(target["kind"], target["id"]) for binding in bindings
                    if binding["relation"] == "local"
                    for target in compiled_targets(binding, inventory)} - proved
    statuses = {(kind, row["id"]): _row_status(row["binding_ids"], relations)
                for kind, key in (("node", "nodes"), ("operator", "operators"))
                for row in inventory[key]}
    output_nodes = {output for operator in inventory["operators"]
                    if ("operator", operator["id"]) in proved for output in operator["outputs"]
                    if ("node", output) in proved}
    interpretation_nodes = {name for kind, name in proved if kind == "node"} - output_nodes
    declarations = physlib_declaration_index({"bindings": anchored})
    return {
        "nodes_total": len(inventory["nodes"]),
        "nodes_mapped": sum(status == "mapped" for (kind, _), status in statuses.items() if kind == "node"),
        "operators_total": len(inventory["operators"]),
        "operators_mapped": sum(status == "mapped" for (kind, _), status in statuses.items()
                                if kind == "operator"),
        "nodes_local": sum(status == "local" for (kind, _), status in statuses.items() if kind == "node"),
        "operators_local": sum(status == "local" for (kind, _), status in statuses.items()
                               if kind == "operator"),
        "bindings_total": len(bindings),
        "source_correspondences": sum(b["evidence"]["kind"] == "source_correspondence" for b in bindings),
        "compiled_bridges": sum(b["evidence"]["kind"] == "compiled_bridge" for b in bindings),
        "nodes_compiled": sum(kind == "node" for kind, _ in proved),
        "nodes_compiled_outputs": len(output_nodes),
        "nodes_compiled_interpretations": len(interpretation_nodes),
        "operators_compiled": sum(kind == "operator" for kind, _ in proved),
        "operators_compiled_local": sum(kind == "operator" for kind, _ in local_proved),
        "nodes_compiled_local": sum(kind == "node" for kind, _ in local_proved),
        "operators_proved": sum(kind == "operator" for kind, _ in proved | local_proved),
        "nodes_proved": sum(kind == "node" for kind, _ in proved | local_proved),
        "upstream_declarations_referenced": len(declarations),
        "upstream_modules_referenced": len({row["module"] for row in declarations}),
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
    relations = {binding["id"]: binding["relation"] for binding in bindings}
    for kind, key in (("node", "nodes"), ("operator", "operators")):
        for row in inventory[key]:
            row["binding_ids"] = sorted(by_target.get((kind, row["id"]), []))
            row["status"] = _row_status(row["binding_ids"], relations)
            row["reason"] = {
                "mapped": "See the conditions and evidence for each mapping.",
                "local": _gap_reason(kind, row, inventory, reasons) + _LOCAL_REASON,
                "gap": _gap_reason(kind, row, inventory, reasons),
            }[row["status"]]
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
        str(path.relative_to(root)) for path in bridge_root.glob("*.lean")
        if ".lake" not in path.relative_to(bridge_root).parts
    } | {"lean/bridge/" + name for name in (
        "lean-toolchain", "lakefile.toml", "lake-manifest.json", "semantic-formula-contract.json",
        "audit.py", "verify_contracts.py",
    )} | {str(path.relative_to(root)) for path in bridge_root.glob("*-formula-contract.json")}
    if not required <= hashes.keys():
        raise ValueError("build record omits proof source/configuration/endpoint dependencies")
    for relative, digest in hashes.items():
        path = root / relative
        if (not path.resolve().is_relative_to(bridge_root.resolve())
                or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest):
            raise ValueError(f"compiled dependency hash mismatch: {relative}")
    expected_names = set()
    for contract_path in bridge_root.glob("*-formula-contract.json"):
        contract = json.loads(contract_path.read_text())
        for endpoint in [*contract.get("operators", []), *contract.get("nodes", [])]:
            if "lean_definition" in endpoint:
                definition_source = root / endpoint.get("definition_source_path", contract["source_path"])
                if not definition_source.resolve().is_relative_to(bridge_root.resolve()):
                    raise ValueError("contract definition path is outside the bridge package")
                module = ".".join(definition_source.relative_to(bridge_root).with_suffix("").parts)
                expected_names.add((endpoint["lean_definition"], module))
    expected_pairs = [{"name": name, "module": module} for name, module in sorted(expected_names)]
    name_audit = record.get("contract_name_audit", {})
    if (name_audit.get("status") != "passed" or name_audit.get("pairs") != expected_pairs
            or name_audit.get("pair_count") != len(expected_pairs)):
        raise ValueError("compiled bridge lacks matching contract name/module audit")
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
    # A cited declaration lives in the evidence source or in a bridge module that the
    # evidence source imports; every such module is hashed in the build record above.
    texts = [path.read_text() for path in _bridge_import_closure(source, bridge_root)]
    for declaration in evidence["declarations"]:
        leaf = declaration.rsplit(".", 1)[-1]
        pattern = re.compile(r"\b(?:theorem|lemma)\s+" + re.escape(leaf) + r"(?=\s|[({:]|$)")
        if not any(pattern.search(text) for text in texts):
            raise ValueError(f"bridge declaration absent from compiled source: {declaration}")


_LEAN_IMPORT = re.compile(r"^\s*(?:public\s+)?(?:meta\s+)?import\s+(?:all\s+)?(\S+)", re.MULTILINE)


def _bridge_import_closure(source: Path, bridge_root: Path) -> list[Path]:
    """The evidence source and every bridge-local Lean module it imports, transitively."""
    seen: list[Path] = []
    stack = [source]
    while stack:
        path = stack.pop()
        if path in seen:
            continue
        seen.append(path)
        for module in _LEAN_IMPORT.findall(path.read_text()):
            candidate = bridge_root / (module.replace(".", "/") + ".lean")
            if candidate.is_file():
                stack.append(candidate)
    return seen


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
        if binding["relation"] in ("conditional", "local") and not binding["conditions"]:
            raise ValueError(f"{binding['relation']} binding requires explicit conditions")
        if (binding["relation"] == "local") != (not binding["sources"]):
            raise ValueError("a local binding cites no Physlib source; every other binding cites one")
        if binding["relation"] == "local" and binding["evidence"]["kind"] != "compiled_bridge":
            raise ValueError("a local binding must be a compiled proof")
        if binding["relation"] == "local" and not binding["remaining_obligations"]:
            raise ValueError("a local binding must disclose its remaining obligations")
        if (binding["evidence"]["kind"] == "source_correspondence"
                and not binding["remaining_obligations"]):
            raise ValueError("uncompiled correspondence must disclose remaining bridge obligations")
        if binding["relation"] == "conceptual" and binding["evidence"]["kind"] == "compiled_bridge":
            raise ValueError("conceptual reference cannot claim a compiled formula bridge")
        if "proved_targets" in binding["evidence"]:
            subjects = [(target["kind"], target["id"])
                        for target in binding["evidence"]["proved_targets"]]
            if len(set(subjects)) != len(subjects) or not set(subjects) <= set(targets):
                raise ValueError("compiled proof subjects must be distinct binding targets")
        declarations = [(source["module"], source["name"]) for source in binding["sources"]]
        if len(set(declarations)) != len(declarations):
            raise ValueError(f"duplicate source declaration: {binding['id']}")
        for source in binding["sources"]:
            if source["source_url"] != _source_url(payload["upstream"], source):
                raise ValueError("source URL does not match pinned upstream")
        if proof_root is not None and binding["evidence"]["kind"] == "compiled_bridge":
            _check_compiled_evidence(binding, payload["upstream"], proof_root)
    relations = {binding["id"]: binding["relation"] for binding in bindings}
    for key, row in lookup.items():
        if row["binding_ids"] != sorted(expected[key]):
            raise ValueError(f"inconsistent inventory binding IDs: {key}")
        if row["status"] != _row_status(sorted(expected[key]), relations):
            raise ValueError(f"inconsistent coverage status: {key}")
    # Schema v1 predates the additive proof-subject/reverse-index counters.
    # Accept retained v1 payloads; check every supplied counter, including new ones.
    actual_coverage = _coverage(bindings, inventory)
    supplied = payload["coverage"]
    if any(binding["relation"] == "local" for binding in bindings):
        missing = {"operators_compiled_local", "nodes_compiled_local", "operators_proved",
                   "nodes_proved", "operators_local", "nodes_local"} - supplied.keys()
        if missing or "local" not in supplied["relations"]:
            raise ValueError("a payload with local bindings must report its local counts")
    relations = actual_coverage["relations"]
    if (any(actual_coverage[key] != value for key, value in supplied.items() if key != "relations")
            or any(relations[key] != supplied["relations"].get(key, 0) for key in relations)):
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
    """Check pinned source files and declaration lines, not qualified names or proofs.

    Use ``verify_compiled_source_names`` to check fully qualified names and their
    defining modules in Lean's compiled environment.
    """
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


def verify_compiled_source_names(payload: dict, lean_package: Path) -> None:
    """Check declaration names and defining modules with the pinned Lean compiler.

    This checks source references, not formula equivalence. The probe is temporary
    and is not part of the OMAI bridge's theorem or coverage counts.
    """
    lean_package = lean_package.resolve()
    if (lean_package / "lean-toolchain").read_text().strip() != payload["upstream"]["lean_toolchain"]:
        raise ValueError("source-name audit toolchain differs from reviewed source metadata")
    verify_source_references(payload, lean_package / ".lake/packages/physlib")
    declarations = sorted({(source["name"], source["module"])
                           for binding in payload["bindings"] for source in binding["sources"]})
    # Accept ordinary dotted Lean identifiers, including Unicode and primes.
    # Reject quoted identifiers and control characters rather than inserting
    # arbitrary metadata text into an executable Lean command.
    identifier = r"(?:[^\W\d]|_)[\w']*(?:\.(?:[^\W\d]|_)[\w']*)*"
    for name, module in declarations:
        if not re.fullmatch(identifier, name) or not re.fullmatch(identifier, module):
            raise ValueError(f"unsupported source declaration identifier: {name!r}")
    modules = sorted({module for _, module in declarations})
    if not declarations:
        return
    environment = os.environ.copy()
    environment.setdefault("LEAN_NUM_THREADS", "4")
    environment.setdefault("MATHLIB_NO_CACHE_ON_UPDATE", "1")
    subprocess.run(["lake", "build", "--wfail", *["+" + module for module in modules]],
                   cwd=lean_package, check=True, env=environment)
    imports = "\n".join("import " + module for module in modules)
    pairs = ",\n    ".join(f"(`{name}, `{module})" for name, module in declarations)
    probe_source = imports + "\n" + """import Lean
open Lean Elab Command
run_cmd do
  let env ← getEnv
  let expected : List (Name × Name) := [
    """ + pairs + """
  ]
  for (name, expectedModule) in expected do
    let some index := env.getModuleIdxFor? name
      | throwError m!"Source declaration is absent: {name}"
    let actualModule := env.header.moduleNames[index.toNat]!
    unless actualModule == expectedModule do
      throwError m!"Source declaration {name} belongs to {actualModule}, not {expectedModule}"
"""
    with tempfile.TemporaryDirectory(prefix="source-names-", dir=lean_package / ".lake") as directory:
        probe = Path(directory) / "SourceNames.lean"
        probe.write_text(probe_source)
        result = subprocess.run(["lake", "env", "lean", str(probe)], cwd=lean_package,
                                text=True, capture_output=True, env=environment)
        if result.returncode:
            raise ValueError("compiled source declaration audit failed:\n" + result.stdout + result.stderr)


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


def formula_bindings_for_physlib(*, declaration: str | None = None,
                                module: str | None = None) -> list[dict]:
    """Return full OMAI binding records for an exact Physlib name and/or module.

    At least one selector is required; providing both intersects them. Unknown
    names return an empty list. Results include all conditions and evidence,
    and each binding appears once even when several declarations match.
    """
    if not declaration and not module:
        raise ValueError("provide an exact Physlib declaration or module")
    return copy.deepcopy([
        binding for binding in _packaged_bindings()["bindings"]
        if any((declaration is None or source["name"] == declaration)
               and (module is None or source["module"] == module)
               for source in binding["sources"])
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
    parser.add_argument("--lean-package", type=Path,
                        help="pinned Lean package for compiled declaration-name/module audit")
    args = parser.parse_args()
    payload = build_formula_bindings()
    validate_formula_bindings(payload, check_catalog=True, proof_root=_REPO)
    if args.physlib_path is not None:
        verify_source_references(payload, args.physlib_path)
    if args.lean_package is not None:
        verify_compiled_source_names(payload, args.lean_package)
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
