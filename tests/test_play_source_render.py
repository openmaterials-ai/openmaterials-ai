"""The datasheet's Source section reads source.detail the way a reader needs it.

A paper source renders its verbatim quote with the page, the citation and the
DOI; any other source its method. Bracketed curator notes ([MIGRATED ...]) and
repo paths are cut at render time; the hashed data keeps them (2026-10-04).
Same technique as test_play_results_render.py: the page's functions under Node.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_PLAY = _REPO / "docs" / "play" / "index.html"
_INSTANCES = json.loads((_REPO / "docs" / "data" / "instances.json").read_text())


def _grab_function(html: str, name: str) -> str:
    m = re.search(r"function %s\s*\([^)]*\)\s*\{" % re.escape(name), html)
    assert m, f"could not find function {name}"
    i, depth = m.end(), 1
    while i < len(html) and depth:
        c = html[i]
        depth += c == "{"
        depth -= c == "}"
        i += 1
    return html[m.start():i]


def _rows(details: list) -> list:
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available; render checked where present")
    html = _PLAY.read_text()
    src = re.search(r"var REPO_PATH = .*;", html).group(0) + "\n" + "\n".join(
        _grab_function(html, n) for n in ("esc", "readerDetail", "paperParts", "sourceRows"))
    script = src + "\nconsole.log(JSON.stringify(%s.map(function(d){ return sourceRows(d).join(''); })));" \
        % json.dumps(details)
    proc = subprocess.run([node, "-e", script], capture_output=True, text=True)
    assert proc.returncode == 0, f"node failed: {proc.stderr}"
    return json.loads(proc.stdout)


def _detail(prefix: str) -> str:
    return next(e["source"]["detail"] for e in _INSTANCES if e["id"].startswith(prefix))


def test_paper_source_renders_quote_page_citation_and_doi():
    (out,) = _rows([_detail("f735a05c14db")])
    assert "“which gives κQ,Inv = 147 Wm−1K−1” (p. 6)" in out
    assert "J. Appl. Phys. 128, 135104 (2020)</dd>" in out
    assert 'href="https://doi.org/10.1063/5.0020443"' in out


def test_curator_notes_and_repo_paths_never_render():
    (out,) = _rows([_detail("55ee996282a6")])
    assert "<dd>Glassbrenner and Slack, Phys. Rev. 134, A1058 (1964)</dd>" in out
    assert "<dd>steady-state measurement, bulk single crystal, natural isotopic abundance</dd>" in out
    details = [e["source"]["detail"] for e in _INSTANCES if (e.get("source") or {}).get("detail")]
    for out in _rows(details):
        assert "[MIGRATED" not in out, out
        for path in (".agents/skills/", "omai/materials/", "runs/germanium_tersoff",
                     "experiments/qe_si_crosscheck", "mcg/tools/", "reference/fixtures/"):
            assert path not in out, out
