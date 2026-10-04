"""The header names the map version it renders.

The beta chip is gone (the web style guide: a pill holds a version, a licence
or a state word, never a marketing word). site.js renders the header with a
static version pill and, once data/version.json answers, writes its first 12
hex into the pill and the footer stamp. The shell is rendered here under Node
with the real site.js and the real version.json.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

_DOCS = Path(__file__).resolve().parents[1] / "docs"
_SITE_JS = _DOCS / "assets" / "site.js"

# Every page on the shell: the content pages and the four tool pages.
_SHELL_PAGES = ["index.html", "guide/index.html", "document/index.html",
                "codes/index.html", "lean/index.html", "lean/roadmap/index.html",
                "agreement/index.html", "experiment/index.html",
                "lineage/index.html", "404.html", "map/index.html",
                "map-3d/index.html", "map-trace/index.html", "play/index.html"]

_RENDER = r"""
const fs = require('fs');
const [file, page, variant, ver] = process.argv.slice(1);
const els = {};
const mounts = {
  '[data-site-header]': { innerHTML: '', getAttribute: () => variant || null },
  '[data-site-footer]': { innerHTML: '' },
};
global.location = { href: page, hash: '' };
global.document = {
  currentScript: { src: new URL('/assets/site.js', page).href },
  readyState: 'complete',
  documentElement: { dataset: {} },
  querySelector: (s) => mounts[s] || null,
  querySelectorAll: () => [],
  addEventListener: () => {},
  getElementById: (id) => (els[id] = els[id] || { textContent: '', innerHTML: '' }),
};
global.fetch = () => Promise.resolve({ json: () => Promise.resolve(JSON.parse(ver)) });
eval(fs.readFileSync(file, 'utf8'));
setTimeout(() => console.log(JSON.stringify({
  header: mounts['[data-site-header]'].innerHTML,
  footer: mounts['[data-site-footer]'].innerHTML,
  pill: els['om-version'].textContent,
  stamp: els['om-stamp'].innerHTML,
})), 0);
"""


def _render(page: str, variant: str = "", version: dict | None = None) -> dict:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not available")
    ver = json.dumps(version) if version else (_DOCS / "data" / "version.json").read_text()
    out = subprocess.run([node, "-e", _RENDER, str(_SITE_JS), page, variant, ver],
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_the_pill_and_stamp_carry_the_map_version():
    # a version unlike the static fallback, so the test sees the fetched value
    version = {"version": "ab" * 32, "genesis": "cd" * 32}
    got = _render("https://openmaterials.ai/map-3d/", "app", version)
    assert 'id="om-version"' in got["header"] and "pill pill--mono" in got["header"]
    assert got["pill"] == "map " + "ab" * 6
    assert 'id="om-version" href="https://openmaterials.ai/#cite"' in got["header"], "the pill opens the Cite block"
    assert got["stamp"].split('">', 1)[1] == "ab" * 6 + "</a>", "the stamp carries the map version only"


def test_the_header_links_and_marks_the_current_view():
    for page, current in (("map/", "Map"), ("map-3d/", "Map"), ("map-trace/", "Map"), ("play/", "Playground")):
        got = _render("https://openmaterials.ai/" + page, "app")
        nav = re.search(r'<nav class="site-nav" aria-label="Primary">(.*?)</nav>', got["header"]).group(1)
        assert re.findall(r">([^<]+)</a>", nav) == ["Map", "Playground", "Guide", "Document"], page
        assert re.findall(r'<a href="[^"]*" aria-current="page">([^<]+)</a>', nav) == [current], page
        assert '<fieldset class="theme">' in got["header"], "the app header carries the theme toggle"
        assert 'href="https://github.com/openmaterials-ai/openmaterials-ai">GitHub</a>' in got["header"]
    content = _render("https://openmaterials.ai/guide/")
    assert '<fieldset class="theme">' not in content["header"]
    assert '<fieldset class="theme">' in content["footer"]


def test_every_page_gets_the_pill_and_no_beta_chip():
    """The pill lives in the one header site.js renders, so every page that
    mounts the header shows it; no page carries the beta chip."""
    css = (_DOCS / "assets" / "site.css").read_text()
    assert "om-beta" not in _SITE_JS.read_text() and "om-beta" not in css
    for rel in _SHELL_PAGES:
        s = (_DOCS / rel).read_text()
        assert "om-beta" not in s, rel
        assert "data-site-header" in s and "assets/site.js" in s, rel
    for page in _DOCS.glob("**/*.html"):
        assert "om-beta" not in page.read_text(), str(page.relative_to(_DOCS))
