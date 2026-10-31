"""The Lean ladder's colors on the map hold their contrast in both themes (WCAG 2 ratios)."""

import re
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "docs"


def _tokens() -> dict[str, str]:
    """Custom properties of :root in site.css and in the map page's own style."""
    css = (DOCS / "assets" / "site.css").read_text() + (DOCS / "map" / "index.html").read_text()
    out = {}
    for block in re.findall(r":root\s*\{([^}]*)\}", css):
        for name, value in re.findall(r"--([\w-]+)\s*:\s*([^;]+);", block):
            out.setdefault(name, value.strip())
    return out


def resolve(name: str, mode: str) -> str:
    v = _tokens()[name]
    for _ in range(8):
        if m := re.fullmatch(r"light-dark\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", v):
            v = m.group(1) if mode == "light" else m.group(2)
        elif m := re.fullmatch(r"var\(--([\w-]+)\)", v):
            v = _tokens()[m.group(1)]
        else:
            return v
    raise ValueError(name)


def _luminance(hex_: str) -> float:
    c = [int(hex_.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a: str, b: str) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


PAIRS = [("ink", "surface", 4.5), ("ink", "rung-tint", 4.5), ("on-accent", "accent", 4.5),
         ("accent", "surface", 3.0), ("edge", "surface", 3.0), ("accent", "page", 3.0)]


def test_ladder_contrast_holds_in_both_themes():
    for mode in ("light", "dark"):
        for fg, bg, floor in PAIRS:
            assert contrast(resolve(fg, mode), resolve(bg, mode)) >= floor, (mode, fg, bg)


def test_the_four_rungs_fill_with_distinct_colors():
    for mode in ("light", "dark"):
        fills = {resolve("surface", mode), resolve("rung-tint", mode), resolve("accent", mode)}
        assert len(fills) == 3, mode
