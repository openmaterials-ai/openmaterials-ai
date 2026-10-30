"""Share-link snapshots: the data a /m/<snapshot>/<selection> link reads, frozen under its content hash.

A snapshot holds the map's quantities with their plain names and symbols already drawn, the data flow,
the public codes, Lean and physlib status, and the uid succession from the map log. Its name is the
sha256 of its canonical bytes, so a link made today renders the same page forever. Files under
docs/data/v/ are written once and never rewritten; index.json lists them in first-seen order.

A selection is a bitset over the snapshot's nodes in order: node 0 is the high bit of the first hex
digit, lowercase hex, whole bytes, trailing zero bytes trimmed, at least one bit set.
docs/assets/share.js holds the same encoding.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from omai import submap

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"
OUT = DATA / "v"


def _load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def _succession() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for line in (ROOT / "map" / "log.jsonl").read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        if rec.get("op") == "supersede":
            for old in rec["payload"]["old_uids"]:
                out[old] = list(rec["payload"]["new_uids"])
    return out


def build_snapshot() -> dict:
    from omai.code_pages import display_name

    graph = _load("graph.json")
    catalog = {e["id"]: e for e in _load("catalog.json")}
    lean = _load("lean.json")["nodes"]
    physlib = _load("physlib_crosswalk.json")["nodes"]
    registry = _load("registry.json").get("code", {})
    nodes = []
    for n in graph["nodes"]:
        runs = submap.symbol_runs(n.get("symbol") or "")
        cat = catalog.get(n["id"], {})
        nodes.append({
            "id": n["id"], "uid": n["uid"], "tier": n.get("tier") or "Other", "type": n.get("type"),
            "symbol": n.get("symbol") or "", "formula": n.get("formula") or "",
            "name": submap.node_name(n["id"]), "sym": [list(r) for r in runs] if runs else None,
            "dimension": cat.get("dimension"), "description": cat.get("description"),
            "lean": n["id"] in lean,
            "physlib": [{"name": p["name"], "module": p["module"], "url": p.get("source_url")} for p in physlib.get(n["id"]) or []],
        })
    codes = {
        key: {"name": display_name(key, rep), "nodes": sorted(rep)}
        for key, rep in sorted(_load("codes.json").items())
        if (registry.get(key) or {}).get("visibility") != "private"
    }
    return {
        "map_version": _load("version.json")["version"],
        "tiers": [{"name": t["name"], "order": t.get("order", i)} for i, t in enumerate(graph["tiers"])],
        "nodes": nodes,
        "links": [[l["source"], l["target"], l.get("op")] for l in graph["links"]],
        "codes": codes,
        "succession": _succession(),
    }


def snapshot_bytes(snap: dict) -> bytes:
    return json.dumps(snap, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def write_snapshot(out: Path = OUT) -> str:
    """Write the current snapshot if it is new, point index.json at it, and return its hash."""
    b = snapshot_bytes(build_snapshot())
    h = hashlib.sha256(b).hexdigest()
    out.mkdir(parents=True, exist_ok=True)
    f = out / f"{h}.json"
    if not f.exists():
        f.write_bytes(b)
    idx_path = out / "index.json"
    seen = json.loads(idx_path.read_text())["snapshots"] if idx_path.exists() else []
    if h not in seen:
        seen.append(h)
    idx_path.write_text(json.dumps({"latest": h, "snapshots": seen}, indent=1) + "\n")
    return h


def encode(snap: dict, ids) -> str:
    order = {n["id"]: i for i, n in enumerate(snap["nodes"])}
    bits = [order[i] for i in ids if i in order]
    if not bits:
        raise ValueError("an empty selection has no link")
    buf = bytearray(max(bits) // 8 + 1)
    for b in bits:
        buf[b // 8] |= 0x80 >> (b % 8)
    return buf.hex()


def decode(snap: dict, hx: str) -> list[str] | None:
    """The selected ids in snapshot order, or None for a malformed or out-of-range selection."""
    n = len(snap["nodes"])
    if not hx or len(hx) % 2 or hx != hx.lower() or any(c not in "0123456789abcdef" for c in hx) or hx.endswith("00"):
        return None
    buf = bytes.fromhex(hx)
    idx = [i for i in range(len(buf) * 8) if buf[i // 8] & (0x80 >> (i % 8))]
    if not idx or idx[-1] >= n:
        return None
    return [snap["nodes"][i]["id"] for i in idx]


if __name__ == "__main__":
    print("wrote snapshot", write_snapshot())
