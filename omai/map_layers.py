"""The Lean layer of the map: every quantity's and formula's Lean rung, its counterparts, and the tier ledgers.

The map page (docs/map/) reads docs/data/map_layers.json beside graph.json, and takes each binding's
statement, conditions and remaining obligations from formula_bindings.json. A rung is the strongest
reviewed Lean claim about a mark, read from the generated formula bindings:

- physlib: a Lean theorem that cites Physlib (a compiled target of a binding whose relation is not ``local``);
- local: a Lean theorem over Mathlib alone (a compiled target of a ``local`` binding);
- stated: a Lean declaration that identifies the mark, without a theorem (a ``source_correspondence``
  binding whose relation is not ``conceptual``);
- none: no reviewed Lean theorem or statement.

A theorem may state a property of a formula (a sign, a symmetry, a bound) rather than the formula itself;
the binding's statement says which. A formula takes the rung of its bindings. A quantity takes the weakest
rung among its producing formulas, counting a formula only when the binding that proves it also
covers this output (``via: formulas``), or the rung of a theorem about the quantity itself
when that is higher (``via: quantity``), so a quantity read by a theorem as an input does not climb, and
neither does one with a producing formula outside Lean. A ``conceptual`` correspondence names a related
Physlib concept and is listed under ``related``, never as a rung. Bridge declarations link to their line
on main, the revision the site deploys from, so a change that moves a line in lean/bridge makes the file
stale. Every bridge declaration depends only on the axioms the bridge audit allows, listed once.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from omai.formula_bindings import compiled_targets

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"
BRIDGE = ROOT / "lean" / "bridge"
OUT = DATA / "map_layers.json"
PAPERS = ROOT / "index" / "papers"
PROJECTS = ROOT / "omai" / "data" / "projects.json"
REPOSITORY = "https://github.com/openmaterials-ai/openmaterials-ai"
RUNGS = ("none", "stated", "local", "physlib")
FORMAT = 1

_MODIFIERS = r"(?:(?:public|private|protected|noncomputable|nonrec|partial|unsafe)\s+)*"
_BLOCK = re.compile(r"^\s*(?:@\[[^\]]*\]\s*)?" + _MODIFIERS + r"(namespace|section|mutual)\b\s*(\S*)")
_END = re.compile(r"^\s*end\b")
_DECL = re.compile(r"^\s*(?:open\s.*?\sin\s+)?(?:@\[[^\]]*\]\s*)?" + _MODIFIERS +
                   r"(?:theorem|lemma|def|abbrev|structure|instance|class|inductive|opaque)\s+([^\s:({\[]+)")


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _keys(inventory: dict):
    return [(kind, row["id"]) for kind, key in (("node", "nodes"), ("operator", "operators")) for row in inventory[key]]


def _claims(payload: dict) -> list[tuple[dict, str, tuple[str, str], str | None]]:
    """(binding, rung, mark, route) for every binding that proves or identifies a mark.

    route is None for a claim about the mark itself, or the id of the operator, proved by the same binding,
    whose output the mark is. A quantity a binding proves is reached through such an operator when there
    is one; otherwise the theorem is about the quantity itself.
    """
    out = []
    for b in payload["bindings"]:
        if b["evidence"]["kind"] == "source_correspondence" and b["relation"] != "conceptual":
            out += [(b, "stated", (t["kind"], t["id"]), None) for t in b["targets"]]
        targets = compiled_targets(b, payload["inventory"])
        ops = {t["id"] for t in targets if t["kind"] == "operator"}
        made = {}
        for row in payload["inventory"]["operators"]:
            if row["id"] in ops:
                for o in row["outputs"]:
                    made.setdefault(o, []).append(row["id"])
        rung = "local" if b["relation"] == "local" else "physlib"
        for t in targets:
            key = (t["kind"], t["id"])
            routes = made.get(t["id"]) if t["kind"] == "node" else None
            out += [(b, rung, key, op) for op in routes] if routes else [(b, rung, key, None)]
    return out


def _rank(*rs: str) -> str:
    return max(rs, key=RUNGS.index)


def _rungs_and_routes(payload: dict) -> tuple[dict, dict]:
    """Every mark's rung, and for each quantity whether it comes from its formulas or from itself."""
    own = {key: "none" for key in _keys(payload["inventory"])}
    through: dict[tuple[str, str], str] = {}
    for _, rung, key, route in _claims(payload):
        if route is None:
            own[key] = _rank(own[key], rung)
        else:
            through[(key[1], route)] = _rank(through.get((key[1], route), "none"), rung)
    out, via = dict(own), {}
    producers: dict[str, list[str]] = {}
    for row in payload["inventory"]["operators"]:
        for o in row["outputs"]:
            producers.setdefault(o, []).append(row["id"])
    for row in payload["inventory"]["nodes"]:
        q, key = row["id"], ("node", row["id"])
        route = min((through.get((q, op), "none") for op in producers.get(q, [])), key=RUNGS.index, default="none")
        out[key] = _rank(own[key], route)
        via[q] = None if out[key] == "none" else "quantity" if RUNGS.index(own[key]) > RUNGS.index(route) else "formulas"
    return out, via


def rungs(payload: dict) -> dict[tuple[str, str], str]:
    """The rung of every inventory quantity (``node``) and formula (``operator``)."""
    return _rungs_and_routes(payload)[0]


def _strip_comments(text: str) -> str:
    """Lean comments blanked out, newlines kept, so line numbers stay put. Block comments nest."""
    out, depth, i = [], 0, 0
    while i < len(text):
        two = text[i:i + 2]
        if two == "/-":
            depth += 1
            out.append("  ")
            i += 2
        elif depth and two == "-/":
            depth -= 1
            out.append("  ")
            i += 2
        elif not depth and two == "--":
            j = text.find("\n", i)
            j = len(text) if j < 0 else j
            out.append(" " * (j - i))
            i = j
        else:
            out.append(text[i] if text[i] == "\n" or not depth else " ")
            i += 1
    return "".join(out)


def bridge_lines(lean_text: str) -> dict[str, int]:
    """Fully qualified name -> 1-based line of every named declaration in one Lean source file."""
    stack: list[str] = []
    out: dict[str, int] = {}
    for i, line in enumerate(_strip_comments(lean_text).splitlines(), 1):
        if m := _DECL.match(line):
            name = m.group(1).rstrip(".")
            full = name[len("_root_."):] if name.startswith("_root_.") else ".".join([*filter(None, stack), name])
            out.setdefault(full, i)
        elif m := _BLOCK.match(line):
            stack.append(m.group(2) if m.group(1) == "namespace" else "")
        elif _END.match(line) and stack:
            stack.pop()
    return out


def _bridge_index() -> dict[str, tuple[str, int]]:
    index: dict[str, tuple[str, int]] = {}
    for path in sorted(BRIDGE.glob("*.lean")):
        rel = path.relative_to(ROOT).as_posix()
        for name, line in bridge_lines(path.read_text(encoding="utf-8")).items():
            index.setdefault(name, (rel, line))
    return index


def _binding_entry(b: dict, index: dict, audit: dict) -> dict:
    bridge = []
    if b["evidence"]["kind"] == "compiled_bridge":
        for name in b["evidence"]["declarations"]:
            if name not in index:
                raise ValueError(f"bridge declaration {name} of binding {b['id']} has no source line in lean/bridge")
            if name not in audit:
                raise ValueError(f"bridge declaration {name} of binding {b['id']} is missing from the axiom audit")
            path, line = index[name]
            bridge.append({"name": name, "module": Path(path).stem, "url": f"{REPOSITORY}/blob/main/{path}#L{line}"})
    return {"relation": b["relation"], "evidence": b["evidence"]["kind"],
            "physlib": [{"name": s["name"], "module": s["module"], "kind": s["kind"], "url": s["source_url"]}
                        for s in b["sources"]],
            "bridge": bridge}


def _tags(quantities: set[str], formulas: set[str]) -> dict:
    """Named areas of the map. A paper in index/papers covers the quantities its values sit on and the
    formulas in its curated "formulas" list, never a closure. A cleared project comes from
    omai/data/projects.json. The map page takes codes from codes.json. An empty area is left out."""
    out = {}
    for path in sorted(PAPERS.glob("*.json")):
        rec, slug = _load(path), path.stem
        paper, values = rec.get("paper", {}), rec.get("values", [])
        used = sorted(rec.get("formulas", []))
        if set(used) - formulas:
            raise ValueError(f"paper {slug} lists formulas outside the catalog: {sorted(set(used) - formulas)}")
        qs = sorted({v["node_id"] for v in values} & quantities)
        if not qs and not used:
            continue
        url = (f"https://doi.org/{paper['doi']}" if paper.get("doi")
               else f"https://arxiv.org/abs/{paper['arxiv']}" if paper.get("arxiv") else None)
        out[f"paper:{slug}"] = {"label": paper.get("title") or slug, "url": url, "values": len(values),
                                "quantities": qs, "formulas": used}
    for pr in _load(PROJECTS)["projects"]:
        if set(pr["quantities"]) - quantities or set(pr["formulas"]) - formulas:
            raise ValueError(f"project {pr['id']} names marks outside the catalog")
        if pr["quantities"] or pr["formulas"]:
            out[f"project:{pr['id']}"] = {"label": pr["title"], "url": pr.get("url"), "owner": pr.get("owner"), "values": None,
                                          "quantities": sorted(pr["quantities"]), "formulas": sorted(pr["formulas"])}
    return out


def build_map_layers() -> dict:
    payload = _load(DATA / "formula_bindings.json")
    graph = _load(DATA / "graph.json")
    audit = _load(BRIDGE / "build-evidence.json")["axiom_audit"]
    rung, via = _rungs_and_routes(payload)
    named: dict[tuple[str, str], set[str]] = {}
    for b, _, key, _ in _claims(payload):
        named.setdefault(key, set()).add(b["id"])
    related: dict[str, set[str]] = {}
    for b in payload["bindings"]:
        if b["evidence"]["kind"] == "source_correspondence" and b["relation"] == "conceptual":
            for t in b["targets"]:
                related.setdefault(t["id"], set()).add(b["id"])
    tier_of = {n["id"]: n.get("tier") or "Other" for n in graph["nodes"]}
    quantities = {row["id"]: {"rung": rung[("node", row["id"])], "via": via[row["id"]],
                              "bindings": sorted(named.get(("node", row["id"]), ())),
                              "related": sorted(related.get(row["id"], ()))}
                  for row in payload["inventory"]["nodes"]}
    # a formula's tier is that of its first output in catalog order, the output the map draws it before
    formulas = {row["id"]: {"inputs": row["inputs"], "outputs": row["outputs"], "tier": tier_of[row["outputs"][0]],
                            "rung": rung[("operator", row["id"])],
                            "bindings": sorted(named.get(("operator", row["id"]), ()))}
                for row in payload["inventory"]["operators"]}
    tiers = [t["name"] for i, t in sorted(enumerate(graph["tiers"]), key=lambda it: it[1].get("order", it[0]))]
    tiers += sorted({f["tier"] for f in formulas.values()} - set(tiers))
    index = _bridge_index()
    return {
        "format": FORMAT,
        "upstream": payload["upstream"],
        "axioms": audit["allowed_axioms"],
        "tiers": [{"name": t, "formulas": sum(f["tier"] == t for f in formulas.values()),
                   "theorems": sum(f["tier"] == t and f["rung"] in ("local", "physlib") for f in formulas.values())}
                  for t in tiers],
        "quantities": quantities,
        "formulas": formulas,
        "bindings": {b["id"]: _binding_entry(b, index, audit["declarations"]) for b in payload["bindings"]},
        "tags": _tags(set(quantities), set(formulas)),
        "counts": {kind: {r: sum(m["rung"] == r for m in marks.values()) for r in RUNGS}
                   for kind, marks in (("quantities", quantities), ("formulas", formulas))},
    }


def lean_badge(layers: dict) -> tuple[str, str]:
    """Label and message of /badge/stat/lean.svg, which counts the operators with a Lean theorem out of all operators."""
    f = layers["counts"]["formulas"]
    return "Lean theorems", f"{f['local'] + f['physlib']}/{sum(f.values())} operators"


def write_map_layers(out: Path = OUT) -> Path:
    """Write map_layers.json and the Lean stat badge that counts from it (the Worker serves the same bytes)."""
    from omai.badge import labeled_badge_svg

    layers = build_map_layers()
    out.write_text(json.dumps(layers, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    stat = ROOT / "docs" / "badge" / "stat"
    stat.mkdir(parents=True, exist_ok=True)
    (stat / "lean.svg").write_text(labeled_badge_svg(*lean_badge(layers)) + "\n", encoding="utf-8")
    return out


def main() -> None:
    print("wrote", write_map_layers().relative_to(ROOT))


if __name__ == "__main__":
    main()
