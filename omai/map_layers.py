"""The Lean layer of the map: every quantity's and formula's Lean rung, its counterparts, and the tier ledgers.

The map page (docs/map/) reads docs/data/map_layers.json beside graph.json. A rung is the strongest Lean
claim about a mark, read from the generated formula bindings:

- physlib: a compiled target of a binding that cites Physlib (relation other than ``local``);
- local: a compiled target of a ``local`` binding, a Lean proof over Mathlib alone;
- stated: a target of a ``source_correspondence`` binding, a Lean declaration named for the mark, not proved;
- none: anything else, including a quantity a compiled bridge only reads as an input.

A mark lists the bindings that prove it or name it, never a binding that only reads it. Each binding lists
the Physlib declarations it cites, at the pinned revision, and the bridge declarations that carry its proof,
with their line on main (the revision the site deploys from) and the axioms the bridge audit records.
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
REPOSITORY = "https://github.com/openmaterials-ai/openmaterials-ai"
RUNGS = ("none", "stated", "local", "physlib")
FORMAT = 1

_BLOCK = re.compile(r"^\s*(?:@\[[^\]]*\]\s*)?(?:(?:public|private)\s+)?(namespace|section)\b\s*(\S*)")
_END = re.compile(r"^\s*end\b")
_DECL = re.compile(r"^\s*(?:@\[[^\]]*\]\s*)?(?:(?:private|protected|noncomputable|nonrec|partial|unsafe)\s+)*"
                   r"(?:theorem|lemma|def|abbrev|structure|instance|class|inductive|opaque)\s+([^\s:({\[]+)")


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _keys(inventory: dict):
    return [(kind, row["id"]) for kind, key in (("node", "nodes"), ("operator", "operators")) for row in inventory[key]]


def _claims(payload: dict) -> list[tuple[dict, str, tuple[str, str]]]:
    """(binding, rung it gives, mark) for every binding that proves a mark or names it."""
    inventory, out = payload["inventory"], []
    for b in payload["bindings"]:
        if b["evidence"]["kind"] == "source_correspondence":
            out += [(b, "stated", (t["kind"], t["id"])) for t in b["targets"]]
        rung = "local" if b["relation"] == "local" else "physlib"
        out += [(b, rung, (t["kind"], t["id"])) for t in compiled_targets(b, inventory)]
    return out


def rungs(payload: dict) -> dict[tuple[str, str], str]:
    """The rung of every inventory quantity (``node``) and formula (``operator``)."""
    out = {key: "none" for key in _keys(payload["inventory"])}
    for _, rung, key in _claims(payload):
        out[key] = max(out[key], rung, key=RUNGS.index)
    return out


def bridge_lines(lean_text: str) -> dict[str, int]:
    """Fully qualified name -> 1-based line of every named declaration in one Lean source file."""
    stack: list[str] = []
    out: dict[str, int] = {}
    for i, line in enumerate(lean_text.splitlines(), 1):
        if m := _BLOCK.match(line):
            stack.append(m.group(2) if m.group(1) == "namespace" else "")
        elif _END.match(line):
            if stack:
                stack.pop()
        elif m := _DECL.match(line):
            name = m.group(1)
            full = name[len("_root_."):] if name.startswith("_root_.") else ".".join([*filter(None, stack), name])
            out.setdefault(full, i)
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
            path, line = index.get(name, (b["evidence"]["source_path"], None))
            bridge.append({"name": name, "module": b["evidence"]["module"],
                           "url": f"{REPOSITORY}/blob/main/{path}" + (f"#L{line}" if line else ""),
                           "axioms": audit.get(name)})
    return {"relation": b["relation"], "evidence": b["evidence"]["kind"],
            "physlib": [{"name": s["name"], "module": s["module"], "kind": s["kind"], "url": s["source_url"]}
                        for s in b["sources"]],
            "bridge": bridge}


def build_map_layers() -> dict:
    payload = _load(DATA / "formula_bindings.json")
    graph = _load(DATA / "graph.json")
    audit = _load(BRIDGE / "build-evidence.json")["axiom_audit"]["declarations"]
    rung = rungs(payload)
    named: dict[tuple[str, str], set[str]] = {}
    for b, _, key in _claims(payload):
        named.setdefault(key, set()).add(b["id"])
    tier_of = {n["id"]: n.get("tier") or "Other" for n in graph["nodes"]}
    quantities = {row["id"]: {"rung": rung[("node", row["id"])], "bindings": sorted(named.get(("node", row["id"]), ()))}
                  for row in payload["inventory"]["nodes"]}
    formulas = {row["id"]: {"inputs": row["inputs"], "outputs": row["outputs"], "tier": tier_of[min(row["outputs"])],
                            "rung": rung[("operator", row["id"])],
                            "bindings": sorted(named.get(("operator", row["id"]), ()))}
                for row in payload["inventory"]["operators"]}
    tiers = [t["name"] for t in sorted(graph["tiers"], key=lambda t: t["order"])]
    tiers += sorted({f["tier"] for f in formulas.values()} - set(tiers))
    index = _bridge_index()
    return {
        "format": FORMAT,
        "upstream": payload["upstream"],
        "tiers": [{"name": t, "formulas": sum(f["tier"] == t for f in formulas.values()),
                   "proved": sum(f["tier"] == t and f["rung"] in ("local", "physlib") for f in formulas.values())}
                  for t in tiers],
        "quantities": quantities,
        "formulas": formulas,
        "bindings": {b["id"]: _binding_entry(b, index, audit) for b in payload["bindings"]},
        "counts": {kind: {r: sum(m["rung"] == r for m in marks.values()) for r in RUNGS}
                   for kind, marks in (("quantities", quantities), ("formulas", formulas))},
    }


def write_map_layers(out: Path = OUT) -> Path:
    out.write_text(json.dumps(build_map_layers(), indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def main() -> None:
    print("wrote", write_map_layers().relative_to(ROOT))


if __name__ == "__main__":
    main()
