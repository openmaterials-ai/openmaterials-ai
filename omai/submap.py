"""A code's submap as inline SVG: its quantities in tier columns, named, with the data flow between them.

Drawn at build time from docs/data/graph.json and codes.json for the code pages. Each box links to
the quantity on the interactive map. Labels are 13 px at natural size; a wide submap scrolls
sideways inside its figure instead of shrinking under the floor. A code that serves fewer than
four quantities also shows their direct inputs and outputs on the map, hollow, as context.

Plain names mirror ``nodeName`` in docs/assets/map-words.js (the word tables are read from that
file so the two never drift). Symbols are the map's LaTeX turned into text with sub and
superscripts; one the converter cannot read falls back to the name alone.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORDS_JS = ROOT / "docs" / "assets" / "map-words.js"

BOX_W, BOX_H, ROW_GAP = 184, 48, 14
COL_W, COL_GAP, HEAD_H, PAD = 208, 60, 30, 12

GREEK = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε", "varepsilon": "ε", "zeta": "ζ", "eta": "η",
    "theta": "θ", "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ", "pi": "π", "rho": "ρ", "sigma": "σ",
    "tau": "τ", "phi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω", "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ",
    "Xi": "Ξ", "Pi": "Π", "Sigma": "Σ", "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω", "infty": "∞", "parallel": "∥",
    "langle": "⟨", "rangle": "⟩", "cdot": "·", "times": "×", "hbar": "ħ", "nabla": "∇", "partial": "∂",
}
SCRIPT = {"D": "𝒟", "G": "𝒢", "S": "𝒮", "T": "𝒯", "L": "ℒ", "H": "ℋ", "E": "ℰ", "F": "ℱ"}


def _js_table(name: str) -> dict[str, str]:
    src = WORDS_JS.read_text(encoding="utf-8")
    m = re.search(r"var %s = \{(.*?)\};" % name, src, re.S)
    if not m:
        raise ValueError(f"{name} not found in {WORDS_JS}")
    out = {}
    for mm in re.finditer(r"""(?:'(?P<qk>[^']+)'|(?P<k>\w+))\s*:\s*(?:'(?P<qv>(?:[^'\\]|\\.)*)'|"(?P<dv>[^"]*)")""", m.group(1)):
        key = mm.group("qk") or mm.group("k")
        val = mm.group("qv") if mm.group("qv") is not None else mm.group("dv")
        out[key] = val.replace("\\'", "'")
    return out


WORDS = _js_table("WORDS")
HUMAN_PROP = _js_table("HUMAN_PROP")
PHRASES = [
    (re.compile(r"\bGreen Kubo\b"), "Green-Kubo"), (re.compile(r"\bHOMO LUMO\b"), "HOMO-LUMO"),
    (re.compile(r"\bHasselman Johnson\b"), "Hasselman-Johnson"), (re.compile(r"\bNan effective kappa\b"), "Nan effective-medium kappa"),
    (re.compile(r"\bNan, "), "Nan effective medium, "), (re.compile(r"\bphase space 3phonon\b"), "three-phonon phase space"),
    (re.compile(r"\bheat capacity p\b"), "heat capacity at constant pressure"), (re.compile(r" (QHA|EOS)$"), r" (\1)"),
    (re.compile(r"\bidentity dm\b"), "identity (dynamical matrix)"), (re.compile(r"\bforces HF\b"), "forces (Hellmann-Feynman)"),
    (re.compile(r"\bGibbs hts\b"), "Gibbs energy (G = H - TS)"), (re.compile(r"\bNAC correction\b"), "non-analytic correction"),
]


def plain_words(s: str) -> str:
    s = re.sub(r"[A-Za-z0-9]+", lambda m: WORDS.get(m.group(0).lower(), m.group(0)), s)
    for rx, rep in PHRASES:
        s = rx.sub(rep, s)
    return s


def humanize_id(ident: str) -> str:
    w = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", ident)
    w = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", w)
    parts = re.sub(r"[_-]+", " ", w).strip().split()
    words = []
    for i, x in enumerate(parts):
        if re.fullmatch(r"[A-Z0-9]{2,}", x):
            words.append(x)
        else:
            words.append(x.lower() if i else x[:1].upper() + x[1:].lower())
    return plain_words(" ".join(words)) if words else "Property"


def node_name(ident: str) -> str:
    base = re.sub(r"\[.*$", "", ident)
    q = re.search(r"\[(.*)\]$", ident)
    name = HUMAN_PROP.get(base) or humanize_id(base)
    if q:
        name += " (" + plain_words(re.sub(r"\w+=", "", q.group(1)).replace("_", " ").replace(",", ", ")) + ")"
    return name


# ---- symbols: LaTeX to text runs [(text, level)] with level 0, "sub" or "sup"

def _braced(s: str, i: int) -> tuple[str, int]:
    """The argument starting at s[i]: a {...} group or a single token; returns (content, next index)."""
    if i < len(s) and s[i] == "{":
        depth, j = 0, i
        while j < len(s):
            depth += s[j] == "{"
            depth -= s[j] == "}"
            j += 1
            if depth == 0:
                return s[i + 1:j - 1], j
        return s[i + 1:], len(s)
    m = re.match(r"\\[A-Za-z]+|.", s[i:])
    return (m.group(0), i + len(m.group(0))) if m else ("", i)


def symbol_runs(latex: str, level: str = "") -> list[tuple[str, str]] | None:
    runs: list[tuple[str, str]] = []
    s, i = latex, 0
    while i < len(s):
        c = s[i]
        if c == "\\":
            m = re.match(r"\\([A-Za-z]+)", s[i:])
            if not m:
                i += 1
                continue
            name = m.group(1)
            i += len(m.group(0))
            if name in ("mathrm", "mathbf", "text", "operatorname"):
                arg, i = _braced(s, i)
                inner = symbol_runs(arg, level)
                if inner is None:
                    return None
                runs += inner
            elif name == "mathcal":
                arg, i = _braced(s, i)
                runs.append(("".join(SCRIPT.get(ch, ch) for ch in arg), level))
            elif name in ("left", "right"):
                continue
            elif name in GREEK:
                runs.append((GREEK[name], level))
                i += len(s[i:]) - len(s[i:].lstrip(" "))
            else:
                return None
        elif c in "_^":
            arg, i = _braced(s, i + 1)
            inner = symbol_runs(arg, "sub" if c == "_" else "sup")
            if inner is None:
                return None
            runs += inner
        elif c in "{}":
            i += 1
        else:
            runs.append((c, level))
            i += 1
    merged: list[tuple[str, str]] = []
    for t, lv in runs:
        if merged and merged[-1][1] == lv:
            merged[-1] = (merged[-1][0] + t, lv)
        else:
            merged.append((t, lv))
    return merged


def symbol_svg(latex: str) -> str:
    runs = symbol_runs(latex or "")
    if not runs:
        return ""
    out = []
    for t, lv in runs:
        t = html.escape(t)
        if lv == "sub":
            out.append(f'<tspan baseline-shift="sub" font-size="75%">{t}</tspan>')
        elif lv == "sup":
            out.append(f'<tspan baseline-shift="super" font-size="75%">{t}</tspan>')
        else:
            out.append(t)
    return "".join(out)


def symbol_html(latex: str) -> str:
    runs = symbol_runs(latex or "")
    if not runs:
        return ""
    return "".join(f"<{lv}>{html.escape(t)}</{lv}>" if lv else html.escape(t) for t, lv in runs)


# ---- layout

def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def layout(graph: dict, lit: set[str]) -> dict:
    nodes = {n["id"]: n for n in graph["nodes"]}
    links = [(l["source"], l["target"]) for l in graph["links"] if l["source"] in nodes and l["target"] in nodes]
    drawn = set(i for i in lit if i in nodes)
    ctx: set[str] = set()
    if len(drawn) < 4:  # the inputs the code's quantities need, and their outputs when there are few
        ins = {s for s, t in links if t in drawn and s not in drawn}
        outs = {t for s, t in links if s in drawn and t not in drawn}
        ctx = ins | (outs if len(outs) <= 6 else set())
    shown = drawn | ctx
    edges = [(s, t) for s, t in links if s in shown and t in shown]
    order = {t["name"]: t.get("order", i) for i, t in enumerate(graph["tiers"])}
    tiers = sorted({nodes[i].get("tier") or "Other" for i in shown}, key=lambda n: (order.get(n, 1e6), n))
    # depth within the shown subgraph orders a column top to bottom
    preds: dict[str, list[str]] = {i: [] for i in shown}
    for s, t in edges:
        preds[t].append(s)
    depth: dict[str, int] = {}

    def d(i: str, seen=()) -> int:
        if i in depth:
            return depth[i]
        if i in seen:
            return 0
        depth[i] = 1 + max((d(p, seen + (i,)) for p in preds[i]), default=-1)
        return depth[i]

    for i in shown:
        d(i)
    columns = {t: sorted((i for i in shown if (nodes[i].get("tier") or "Other") == t), key=lambda i: (depth[i], i)) for t in tiers}
    pos: dict[str, dict] = {}
    for ci, t in enumerate(tiers):
        x = PAD + ci * (COL_W + COL_GAP) + (COL_W - BOX_W) / 2
        for ri, i in enumerate(columns[t]):
            y = PAD + HEAD_H + ri * (BOX_H + ROW_GAP)
            pos[i] = {"x": x, "y": y, "col": ci, "row": ri}
    width = PAD * 2 + len(tiers) * COL_W + max(0, len(tiers) - 1) * COL_GAP
    height = PAD * 2 + HEAD_H + max((len(c) for c in columns.values()), default=0) * (BOX_H + ROW_GAP) - ROW_GAP
    return {"tiers": tiers, "columns": columns, "pos": pos, "edges": edges, "ctx": ctx, "nodes": nodes, "width": width, "height": max(height, 80)}


def _edge_path(a: dict, b: dict) -> str:
    if b["col"] > a["col"]:
        x0, y0 = a["x"] + BOX_W, a["y"] + BOX_H / 2
        x1, y1 = b["x"], b["y"] + BOX_H / 2
        dx = max(24, (x1 - x0) * 0.5)
        return f"M{x0:.0f} {y0:.0f} C{x0 + dx:.0f} {y0:.0f} {x1 - dx:.0f} {y1:.0f} {x1:.0f} {y1:.0f}"
    if b["col"] == a["col"]:
        x0, y0 = a["x"] + BOX_W, a["y"] + BOX_H / 2
        x1, y1 = b["x"] + BOX_W, b["y"] + BOX_H / 2
        bow = 28 + 6 * abs(b["row"] - a["row"])
        return f"M{x0:.0f} {y0:.0f} C{x0 + bow:.0f} {y0:.0f} {x1 + bow:.0f} {y1:.0f} {x1:.0f} {y1:.0f}"
    x0, y0 = a["x"] + BOX_W / 2, a["y"]
    x1, y1 = b["x"] + BOX_W / 2, b["y"]
    top = min(y0, y1) - 40
    return f"M{x0:.0f} {y0:.0f} C{x0:.0f} {top:.0f} {x1:.0f} {top:.0f} {x1:.0f} {y1:.0f}"


def svg(graph: dict, lit: set[str], map_href: str = "../../map/") -> str:
    L = layout(graph, lit)
    nodes, pos = L["nodes"], L["pos"]
    out = [
        f'<svg class="submap-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {L["width"]} {L["height"]}" '
        f'width="{L["width"]}" height="{L["height"]}" role="img" aria-label="The quantities on the map, by tier, with the data flow between them">',
        '<defs><marker id="sm-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M0 0 L10 5 L0 10 Z" class="sm-head"/></marker></defs>',
    ]
    for ci, t in enumerate(L["tiers"]):
        x = PAD + ci * (COL_W + COL_GAP)
        out.append(f'<rect class="sm-col" x="{x}" y="{PAD}" width="{COL_W}" height="{L["height"] - 2 * PAD}" rx="4"/>')
        out.append(f'<text class="sm-tier" x="{x + 12}" y="{PAD + 19}">{html.escape(t)}</text>')
    for s, t in L["edges"]:
        out.append(f'<path class="sm-edge" d="{_edge_path(pos[s], pos[t])}" marker-end="url(#sm-arrow)"/>')
    for i, p in pos.items():
        n = nodes[i]
        name = node_name(i)
        sym = symbol_svg(n.get("symbol") or "")
        cls = "sm-node" + (" sm-ctx" if i in L["ctx"] else "") + (" sm-hid" if n.get("type") == "hidden" else "")
        href = f"{map_href}#node={html.escape(i, quote=True)}"
        out.append(f'<a href="{href}" class="{cls}"><title>{html.escape(name)}: {html.escape(i)}</title>')
        out.append(f'<rect x="{p["x"]:.0f}" y="{p["y"]:.0f}" width="{BOX_W}" height="{BOX_H}" rx="6"/>')
        if sym:
            out.append(f'<text class="sm-name" x="{p["x"] + 12:.0f}" y="{p["y"] + 20:.0f}">{html.escape(_truncate(name, 26))}</text>')
            out.append(f'<text class="sm-sym" x="{p["x"] + 12:.0f}" y="{p["y"] + 38:.0f}">{sym}</text>')
        else:
            out.append(f'<text class="sm-name" x="{p["x"] + 12:.0f}" y="{p["y"] + 29:.0f}">{html.escape(_truncate(name, 26))}</text>')
        out.append("</a>")
    out.append("</svg>")
    return "".join(out)


CSS = """
  .submap { margin: 16px 0 8px; overflow-x: auto; -webkit-overflow-scrolling: touch; }
  .submap-svg { display: block; max-width: none; font-family: var(--font-serif); }
  .submap-svg a { text-decoration: none; }
  .submap-svg.fit { width: 100%; height: auto; }
  .sm-col { fill: var(--surface); stroke: var(--line); }
  .sm-tier { font: 500 11px var(--font-mono); letter-spacing: .06em; text-transform: uppercase; fill: var(--ink-2); }
  .sm-edge { fill: none; stroke: var(--edge); stroke-width: 1.4; opacity: .8; }
  .sm-head { fill: var(--edge); }
  .sm-node rect { fill: var(--page); stroke: var(--accent); stroke-width: 1.4; }
  .sm-node.sm-hid rect { stroke-dasharray: 4 3; }
  .sm-node.sm-ctx rect { stroke: var(--line); }
  .sm-node.sm-ctx .sm-name, .sm-node.sm-ctx .sm-sym { fill: var(--ink-2); }
  .sm-node:hover rect, .sm-node:focus rect { fill: var(--surface-2); }
  .sm-name { font-size: 13px; fill: var(--ink); }
  .sm-sym { font: 400 12px var(--font-mono); fill: var(--accent); }
  .sm-node.sm-ctx .sm-sym { fill: var(--ink-2); }
"""


if __name__ == "__main__":  # a quick look at one code: python -m omai.submap gpumd > /tmp/x.svg
    import sys

    graph = json.loads((ROOT / "docs" / "data" / "graph.json").read_text())
    codes = json.loads((ROOT / "docs" / "data" / "codes.json").read_text())
    print(svg(graph, set(codes[sys.argv[1]])))
