"""Line drawings for the code infographics, one per name in ``omai.briefs.GLYPHS``.

Each glyph is the inner markup of a 64 x 64 SVG: strokes in the current text color, the accent
on the elements of class ``a``, soft fills on class ``f``. The renderer wraps them with ``svg``.
"""

from __future__ import annotations

_RING = '<circle cx="{x}" cy="{y}" r="{r}"{extra}/>'


def _dots(points, r=3.2, cls=""):
    c = f' class="{cls}"' if cls else ""
    return "".join(_RING.format(x=x, y=y, r=r, extra=c) for x, y in points)


def _poly(points, cls="", closed=False):
    d = "M" + " L".join(f"{x} {y}" for x, y in points) + (" Z" if closed else "")
    return f'<path d="{d}"' + (f' class="{cls}"' if cls else "") + "/>"


GLYPHS: dict[str, str] = {
    # a cubic cell with an atom on each corner and one in the middle
    "crystal": (
        _poly([(14, 22), (40, 22), (40, 48), (14, 48)], closed=True)
        + _poly([(24, 14), (50, 14), (50, 40), (40, 48)]) + _poly([(24, 14), (14, 22)]) + _poly([(50, 14), (40, 22)])
        + _poly([(24, 14), (24, 40), (14, 48)]) + _poly([(24, 40), (50, 40)])
        + _dots([(14, 22), (40, 22), (40, 48), (14, 48), (24, 14), (50, 14), (50, 40), (24, 40)], 3, "f")
        + _dots([(32, 31)], 3.6, "a")
    ),
    # a row of atoms joined by springs
    "lattice": (
        '<path d="M14 32 l3 -4 3 8 3 -8 3 8 3 -8 3 8 3 -8 3 8 3 -8 3 8 3 -8 3 8 3 -4"/>'
        + _dots([(12, 32), (32, 32), (52, 32)], 5, "f") + _dots([(32, 32)], 5, "a")
        + '<path d="M12 46 v6 M32 46 v6 M52 46 v6"/>'
    ),
    # a wave passing through a line of atoms displaced along it
    "phonon": (
        '<path class="a" d="M8 36 C14 20 20 20 26 36 S38 52 44 36 S56 20 60 36"/>'
        + _dots([(12, 32), (22, 36), (32, 40), (42, 36), (52, 32)], 3.4, "f")
    ),
    # two phonons meeting and one leaving
    "scattering": (
        '<path d="M10 18 C18 24 26 28 32 32 M10 46 C18 40 26 36 32 32"/>'
        + '<path class="a" d="M32 32 L54 32"/>' + '<path class="a" d="M48 27 L54 32 L48 37"/>'
        + _dots([(32, 32)], 3.5, "a")
    ),
    # a chip with pins
    "gpu": (
        '<rect x="18" y="18" width="28" height="28" rx="3" class="f"/>'
        + '<rect x="26" y="26" width="12" height="12" rx="1" class="a"/>'
        + '<path d="M24 18 v-6 M32 18 v-6 M40 18 v-6 M24 46 v6 M32 46 v6 M40 46 v6 M18 24 h-6 M18 32 h-6 M18 40 h-6 M46 24 h6 M46 32 h6 M46 40 h6"/>'
    ),
    # a bonded cluster
    "atoms": (
        _poly([(20, 44), (32, 22), (44, 44)], closed=True) + _poly([(32, 22), (32, 10)]) + _poly([(20, 44), (10, 52)]) + _poly([(44, 44), (54, 52)])
        + _dots([(32, 10), (10, 52), (54, 52)], 3.5, "f") + _dots([(20, 44), (44, 44)], 4.5, "f") + _dots([(32, 22)], 5, "a")
    ),
    "molecule": (
        _poly([(16, 40), (28, 26), (44, 30), (50, 46)]) + _poly([(28, 26), (24, 12)]) + _poly([(44, 30), (56, 20)])
        + _dots([(16, 40), (50, 46), (24, 12), (56, 20)], 3.5, "f") + _dots([(28, 26), (44, 30)], 5, "a")
    ),
    # heat flowing through a slab, hot to cold
    "heat-flow": (
        '<rect x="12" y="20" width="40" height="24" rx="2" class="f"/>'
        + '<path class="a" d="M6 32 H26 M20 26 L26 32 L20 38"/>' + '<path d="M38 32 H58 M52 26 L58 32 L52 38"/>'
        + '<path d="M18 14 c2 -3 4 -3 6 0 M30 14 c2 -3 4 -3 6 0"/>'
    ),
    "chart-up": (
        '<path d="M12 52 H54 M12 52 V12"/>' + '<rect x="18" y="38" width="7" height="14" class="f"/>' + '<rect x="29" y="30" width="7" height="22" class="f"/>'
        + '<rect x="40" y="20" width="7" height="32" class="f"/>' + '<path class="a" d="M16 34 L30 24 L42 16 L54 10 M48 10 H54 V16"/>'
    ),
    "chart-down": (
        '<path d="M12 52 H54 M12 52 V12"/>' + '<rect x="18" y="20" width="7" height="32" class="f"/>' + '<rect x="29" y="30" width="7" height="22" class="f"/>'
        + '<rect x="40" y="40" width="7" height="12" class="f"/>' + '<path class="a" d="M16 16 L30 26 L42 34 L54 42 M48 42 H54 V36"/>'
    ),
    # scatter with a fitted line
    "fit-curve": (
        '<path d="M12 52 H54 M12 52 V12"/>' + _dots([(18, 44), (24, 38), (30, 34), (36, 26), (42, 24), (48, 16)], 2.4, "f")
        + '<path class="a" d="M14 48 C26 42 36 30 54 14"/>'
    ),
    "spectrum": (
        '<path d="M10 50 H56"/>' + '<path class="a" d="M10 50 C16 50 18 30 22 30 S26 50 30 50 S34 14 38 14 S42 50 46 50 S50 36 56 36"/>'
    ),
    "network": (
        _poly([(14, 46), (30, 20), (50, 30), (36, 48), (14, 46)]) + _poly([(30, 20), (36, 48)]) + _poly([(50, 30), (56, 14)])
        + _dots([(14, 46), (50, 30), (36, 48), (56, 14)], 3.5, "f") + _dots([(30, 20)], 5, "a")
    ),
    # three layers of nodes, fully connected
    "neural": (
        "".join(f'<path d="M14 {y1} L32 {y2}"/>' for y1 in (18, 32, 46) for y2 in (24, 40))
        + "".join(f'<path d="M32 {y1} L50 32"/>' for y1 in (24, 40))
        + _dots([(14, 18), (14, 32), (14, 46)], 3.2, "f") + _dots([(32, 24), (32, 40)], 3.6, "a") + _dots([(50, 32)], 4, "f")
    ),
    "bars": (
        '<path d="M12 52 H54"/>' + '<rect x="16" y="30" width="8" height="22" class="f"/>' + '<rect x="28" y="18" width="8" height="34" class="a"/>'
        + '<rect x="40" y="36" width="8" height="16" class="f"/>'
    ),
    "clock": '<circle cx="32" cy="32" r="20" class="f"/><path class="a" d="M32 18 V32 L42 38"/>' + _dots([(32, 32)], 2, "a"),
    "pressure": (
        '<rect x="22" y="22" width="20" height="20" rx="3" class="f"/>'
        + '<path class="a" d="M32 6 V18 M27 13 L32 18 L37 13 M32 58 V46 M27 51 L32 46 L37 51 M6 32 H18 M13 27 L18 32 L13 37 M58 32 H46 M51 27 L46 32 L51 37"/>'
    ),
    "thermometer": (
        '<path d="M26 12 a6 6 0 0 1 12 0 V38 a10 10 0 1 1 -12 0 Z" class="f"/>' + '<path class="a" d="M32 26 V44"/>' + _dots([(32, 46)], 5, "a")
        + '<path d="M42 18 h6 M42 26 h6 M42 34 h6"/>'
    ),
    "database": (
        '<ellipse cx="32" cy="16" rx="18" ry="6" class="f"/>' + '<path d="M14 16 V48 a18 6 0 0 0 36 0 V16"/>' + '<path class="a" d="M14 32 a18 6 0 0 0 36 0"/>'
    ),
    "workflow": (
        '<rect x="6" y="24" width="14" height="16" rx="2" class="f"/>' + '<rect x="25" y="24" width="14" height="16" rx="2" class="a"/>'
        + '<rect x="44" y="24" width="14" height="16" rx="2" class="f"/>' + '<path d="M20 32 H25 M39 32 H44"/>'
    ),
    # a slab with an adsorbate above it
    "surface": (
        '<rect x="10" y="38" width="44" height="14" rx="1" class="f"/>' + _dots([(16, 38), (26, 38), (36, 38), (46, 38)], 2.6, "f")
        + _poly([(31, 30), (31, 20)]) + _dots([(31, 30)], 4, "a") + _dots([(31, 17)], 3.4, "f")
    ),
    # a random walk through a grid of atoms
    "diffusion": (
        _dots([(x, y) for x in (14, 26, 38, 50) for y in (14, 26, 38, 50)], 2, "f")
        + '<path class="a" d="M14 50 L26 38 L26 26 L38 26 L38 14 L50 14"/>' + _dots([(50, 14)], 3.6, "a")
    ),
    "bands": (
        '<path d="M12 52 H54 M12 52 V12"/>' + '<path d="M14 20 C24 26 34 26 52 18 M14 30 C24 24 34 36 52 30"/>'
        + '<path class="a" d="M14 46 C24 40 34 48 52 40"/>' + '<path d="M12 36 H54" stroke-dasharray="3 3"/>'
    ),
    # a binary phase diagram: liquidus and solidus
    "phase-diagram": (
        '<path d="M12 52 H54 M12 52 V12"/>' + '<path class="a" d="M14 18 C30 22 40 36 52 30"/>' + '<path d="M14 24 C28 34 40 42 52 36"/>'
        + '<path d="M22 52 V22" stroke-dasharray="3 3"/>'
    ),
    "circuit": (
        '<path d="M8 32 H18 l2 -5 4 10 4 -10 4 10 4 -10 2 5 H56"/>' + '<path d="M8 32 V48 H56 V32"/>' + '<path class="a" d="M30 48 V54 M34 48 V54" />'
        + _dots([(8, 32), (56, 32)], 2.4, "a")
    ),
    "orbital": (
        '<ellipse cx="32" cy="32" rx="22" ry="9" transform="rotate(-30 32 32)"/>' + '<ellipse cx="32" cy="32" rx="22" ry="9" transform="rotate(30 32 32)"/>'
        + _dots([(32, 32)], 4, "a") + _dots([(13, 21)], 2.6, "f")
    ),
    # an isosurface blob around two centers
    "density": (
        '<path class="f" d="M18 32 c0 -12 12 -16 20 -10 c10 -8 20 2 16 12 c4 10 -8 18 -16 12 c-10 8 -20 -2 -20 -14 Z"/>'
        + _dots([(26, 32), (44, 32)], 3.2, "a")
    ),
    "ensemble": (
        '<rect x="10" y="22" width="26" height="26" rx="2" class="f"/>' + '<rect x="18" y="16" width="26" height="26" rx="2" class="f"/>'
        + '<rect x="26" y="10" width="26" height="26" rx="2" class="a"/>'
    ),
    # a ring polymer of beads
    "ring": (
        '<circle cx="32" cy="32" r="16"/>' + _dots([(32, 16), (46, 24), (46, 40), (32, 48), (18, 40), (18, 24)], 3.2, "f") + _dots([(46, 24)], 3.2, "a")
    ),
    "free-energy": (
        '<path d="M12 52 H54"/>' + '<path class="a" d="M10 20 C16 44 22 48 28 30 C32 20 36 20 40 30 C44 46 50 44 56 16"/>'
        + _dots([(21, 42)], 3, "f") + _dots([(46, 40)], 3, "a")
    ),
    "interface": (
        '<rect x="10" y="14" width="44" height="16" rx="1" class="f"/>' + '<rect x="10" y="34" width="44" height="16" rx="1"/>'
        + '<path class="a" d="M10 32 H54"/>' + _dots([(18, 22), (32, 22), (46, 22)], 2.4, "f") + _dots([(25, 42), (39, 42)], 2.4, "f")
    ),
    "cube": (
        _poly([(14, 24), (36, 24), (36, 46), (14, 46)], "f", True) + _poly([(14, 24), (26, 14), (48, 14), (36, 24)], "f", True)
        + _poly([(36, 24), (48, 14), (48, 36), (36, 46)], "a", True)
    ),
    "layers": (
        _poly([(10, 24), (32, 14), (54, 24), (32, 34)], "f", True) + '<path d="M10 32 L32 42 L54 32"/>' + '<path class="a" d="M10 40 L32 50 L54 40"/>'
    ),
    "magnet": (
        '<path d="M18 12 V34 a14 14 0 0 0 28 0 V12" stroke-width="6"/>' + '<path class="a" d="M18 12 h8 v10 h-8 Z M38 12 h8 v10 h-8 Z"/>'
    ),
    "code": '<path d="M22 18 L10 32 L22 46 M42 18 L54 32 L42 46"/><path class="a" d="M36 14 L28 50"/>',
    "grid": (
        "".join(f'<path d="M{x} 12 V52"/>' for x in (12, 22, 32, 42, 52)) + "".join(f'<path d="M12 {y} H52"/>' for y in (12, 22, 32, 42, 52))
        + '<rect x="22" y="22" width="10" height="10" class="a"/>'
    ),
    "spring": (
        '<path d="M8 32 h6 l3 -8 6 16 6 -16 6 16 6 -16 6 16 3 -8 h6"/>' + _dots([(8, 32)], 3, "f") + _dots([(56, 32)], 3, "a")
    ),
    "wave": '<path class="a" d="M6 32 C12 16 18 16 24 32 S36 48 42 32 S54 16 60 32"/><path d="M6 44 H58" stroke-dasharray="3 3"/>',
    "arrow-cycle": (
        '<path d="M46 20 A18 18 0 1 0 50 36"/>' + '<path class="a" d="M40 20 H48 V12"/>'
    ),
    "search": '<circle cx="28" cy="28" r="14" class="f"/><path class="a" d="M38 38 L52 52"/>',
}


def svg(name: str, size: int = 64, cls: str = "glyph") -> str:
    body = GLYPHS[name]
    return (
        f'<svg class="{cls}" viewBox="0 0 64 64" width="{size}" height="{size}" aria-hidden="true" focusable="false" '
        'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        + body + "</svg>"
    )
