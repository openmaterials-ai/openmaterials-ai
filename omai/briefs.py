"""The brief behind each code's infographic and detail sections: docs/data/briefs/<key>.json.

A brief is written from the code's own papers (the references under docs/data/references/<key>.json)
and checked claim by claim against them before it ships. Every number names its source. The schema is
fixed so that all codes render as one family; ``validate`` is the contract the tests enforce.

Fields (lengths are character budgets the layout relies on):

- ``key``: the codes.json key.
- ``headline``: the poster title, "<Name>: <what it does>", at most 90 characters.
- ``claim``: one sentence, what the code is and what sets it apart, at most 180 characters.
- ``hero``: the one panel with the large illustration: ``glyph``, ``title`` (at most 40), ``text`` (at most 220).
- ``features``: three to five panels on what it is and how it works: ``glyph``, ``title`` (at most 40), ``text`` (at most 170).
- ``facts``: two or three numbers from the papers: ``value`` (at most 10, as printed), ``label`` (at most 48), ``source`` (a label in ``sources``).
- ``workflow``: three to five steps a user takes, inputs to outputs: ``title`` (at most 26), ``text`` (at most 90).
- ``applications``: two or three landmark studies: ``glyph``, ``title`` (at most 44, the system or question), ``text`` (at most 190, the result with its number), ``source``.
- ``sources``: the papers used, ``label`` ("Fan 2017"), ``doi`` (or ``url`` for documentation), each listed in the code's references or documentation.
- ``detail``: two to four sections for the page, ``heading`` (at most 60) and ``text`` (two to five sentences, at most 700 characters).

Glyphs are the line drawings the renderer knows (``GLYPHS``); a brief may only name those.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIEFS = ROOT / "docs" / "data" / "briefs"

GLYPHS = (
    "crystal", "lattice", "phonon", "scattering", "gpu", "atoms", "molecule", "heat-flow", "chart-up", "chart-down",
    "fit-curve", "spectrum", "network", "neural", "bars", "clock", "pressure", "thermometer", "database", "workflow",
    "surface", "diffusion", "bands", "phase-diagram", "circuit", "orbital", "density", "ensemble", "ring", "free-energy",
    "interface", "cube", "layers", "magnet", "code", "grid", "spring", "wave", "arrow-cycle", "search",
)

LIMITS = {"headline": 90, "claim": 180}
PANEL = {"title": 40, "text": 170}
HERO = {"title": 40, "text": 220}
FACT = {"value": 10, "label": 48}
STEP = {"title": 26, "text": 90}
APP = {"title": 44, "text": 190}
DETAIL = {"heading": 60, "text": 700}


def _check_len(where: str, obj: dict, limits: dict, errors: list[str]) -> None:
    for field, n in limits.items():
        v = obj.get(field)
        if not isinstance(v, str) or not v.strip():
            errors.append(f"{where}: {field} missing")
        elif len(v) > n:
            errors.append(f"{where}: {field} is {len(v)} characters, limit {n}")
        elif chr(0x2014) in v:
            errors.append(f"{where}: {field} holds an em dash")


def validate(brief: dict, references: dict | None = None) -> list[str]:
    """Return the schema violations of a brief (an empty list means it is valid)."""
    errors: list[str] = []
    key = brief.get("key")
    if not key:
        errors.append("key missing")
    _check_len("brief", brief, LIMITS, errors)
    hero = brief.get("hero") or {}
    _check_len("hero", hero, HERO, errors)
    if hero.get("glyph") not in GLYPHS:
        errors.append(f"hero: unknown glyph {hero.get('glyph')!r}")
    labels = {s.get("label") for s in brief.get("sources") or []}
    for i, s in enumerate(brief.get("sources") or []):
        if not s.get("label") or not (s.get("doi") or s.get("url")):
            errors.append(f"sources[{i}]: label and doi or url required")
        elif s.get("url") and not str(s["url"]).startswith("https://"):
            errors.append(f"sources[{i}]: url must be https")
    if references is not None:
        known = {r["doi"].lower() for g in ("code", "methods", "applications") for r in references.get(g, [])}
        for s in brief.get("sources") or []:
            if s.get("doi") and s["doi"].lower() not in known:
                errors.append(f"sources: {s['label']} ({s['doi']}) is not among the code's references")
    for name, items, limits, lo, hi, glyph in (
        ("features", brief.get("features"), PANEL, 3, 5, True),
        ("facts", brief.get("facts"), FACT, 2, 3, False),
        ("workflow", brief.get("workflow"), STEP, 3, 5, False),
        ("applications", brief.get("applications"), APP, 0, 3, True),
        ("detail", brief.get("detail"), DETAIL, 2, 4, False),
    ):
        items = items or []
        if not lo <= len(items) <= hi:
            errors.append(f"{name}: {len(items)} items, expected {lo} to {hi}")
        for i, it in enumerate(items):
            _check_len(f"{name}[{i}]", it, limits, errors)
            if glyph and it.get("glyph") not in GLYPHS:
                errors.append(f"{name}[{i}]: unknown glyph {it.get('glyph')!r}")
            if name in ("facts", "applications") and it.get("source") not in labels:
                errors.append(f"{name}[{i}]: source {it.get('source')!r} is not a listed source")
    return errors


def load(key: str) -> dict | None:
    p = BRIEFS / f"{key}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def main() -> int:
    bad = 0
    for p in sorted(BRIEFS.glob("*.json")):
        refs_p = ROOT / "docs" / "data" / "references" / p.name
        refs = json.loads(refs_p.read_text(encoding="utf-8")) if refs_p.exists() else None
        errs = validate(json.loads(p.read_text(encoding="utf-8")), refs)
        for e in errs:
            print(f"{p.stem}: {e}")
        bad += bool(errs)
    print(f"{len(list(BRIEFS.glob('*.json')))} briefs, {bad} with errors")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
