"""The datasheet's Source section reads a record the way a reader needs it.

A paper source renders its verbatim quote with the page, the citation and the
DOI; the "<citation (year)>; <method>" form its citation and method;
any other source the one Method line assets/sources.js builds from the record's
fields (code and version, material, potential or model), and no row when they
name none, so curator prose with repo paths, tags, hashes or field names never
prints. Bracketed curator notes ([MIGRATED ...]) are cut at render time; the
hashed data keeps them (2026-10-04). The page's functions run under Node with
sources.js loaded, as on the page.
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
_SOURCES_JS = _REPO / "docs" / "assets" / "sources.js"
_INSTANCES = json.loads((_REPO / "docs" / "data" / "instances.json").read_text())
_CODES = json.loads((_REPO / "docs" / "data" / "codes.json").read_text())


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


def _rows(entries: list) -> list:
    """sourceRows of each flat instances.json entry, joined, as the page renders them."""
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available; render checked where present")
    html = _PLAY.read_text()
    src = _SOURCES_JS.read_text() + "\nvar CODES = %s;\n" % json.dumps(_CODES) + "\n".join(
        _grab_function(html, n) for n in ("esc", "codeName", "sourceRows", "instanceToRecord"))
    script = src + "\nconsole.log(JSON.stringify(%s.map(function(e){ return sourceRows(instanceToRecord(e)).join(''); })));" \
        % json.dumps(entries)
    # the script carries codes.json and the records, past Linux's per-argument limit: send it on stdin
    proc = subprocess.run([node, "-"], input=script, capture_output=True, text=True)
    assert proc.returncode == 0, f"node failed: {proc.stderr}"
    return json.loads(proc.stdout)


def _entry(prefix: str) -> dict:
    return next(e for e in _INSTANCES if e["id"].startswith(prefix))


def test_paper_source_renders_quote_page_citation_and_doi():
    (out,) = _rows([_entry("f735a05c14db")])
    assert "“which gives κQ,Inv = 147 Wm−1K−1” (p. 6)" in out
    assert "J. Appl. Phys. 128, 135104 (2020)</dd>" in out
    assert 'href="https://doi.org/10.1063/5.0020443"' in out


def test_citation_form_drops_the_curator_note():
    (out,) = _rows([_entry("55ee996282a6")])
    assert "<dd>Glassbrenner and Slack, Phys. Rev. 134, A1058 (1964)</dd>" in out
    assert "<dd>steady-state measurement, bulk single crystal, natural isotopic abundance</dd>" in out
    assert "MIGRATED" not in out


def test_a_run_prints_one_method_line_from_its_fields():
    (out,) = _rows([_entry("f64affbf549a")])
    assert re.fullmatch(r"<dt>Method</dt><dd>\S+ 2\.2\.1 run of Si with the Tersoff potential</dd>", out), out
    (out,) = _rows([_entry("caed5c8fba6c")])   # names no code, potential or model
    assert out == "", out
    for out in _rows(_INSTANCES):
        text = re.sub(r"<[^>]+>", " ", out)   # what a reader sees; links keep their URLs
        assert "MIGRATED" not in text and "sha256" not in text and "lineage.conditions" not in text, text
        assert not re.search(r"\b[0-9a-f]{32,}\b|\w+/\w+/|\btag\b", text), text
