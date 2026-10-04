"""The site shell (Brand/omai-site-spec-2026-10-03.md, sections 2, 3 and 6).

The static records on the home page equal the files they quote, the
machine-readable files point only at real pages, the 404 page forwards the
short links the site hands out, and no page on the shell loads a retired font
or a third-party font host.
"""
from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urljoin, urlparse

import pytest

DOCS = Path(__file__).resolve().parents[1] / "docs"
HOME = (DOCS / "index.html").read_text()
SHELL_PAGES = ["index.html", "guide/index.html", "codes/index.html", "lean/index.html",
               "lean/roadmap/index.html", "agreement/index.html", "experiment/index.html",
               "lineage/index.html", "document/index.html", "404.html", "map/index.html",
               "map-3d/index.html", "map-trace/index.html", "play/index.html"]


def test_the_datum_card_equals_its_instance():
    card = re.search(r'<article class="card datum" data-instance="([0-9a-f]{64})">(.*?)</article>', HOME, re.S)
    assert card, "no datum card"
    inst = next(i for i in json.loads((DOCS / "data/instances.json").read_text()) if i["id"] == card.group(1))
    fields = {k: html.unescape(v) for k, v in re.findall(r'data-field="(\w+)">([^<]*)<', card.group(2))}
    assert fields == {
        "value": str(inst["value"]), "units": inst["units"], "variable": inst["variable"],
        "material": inst["material"], "id": inst["id"],
        "conditions": ", ".join(f"{k} = {v}" for k, v in inst["conditions"].items()),
        "source": f'{inst["source"]["kind"]}, {inst["source"]["ref"]}',
    }


def test_the_contribute_block_is_the_committed_file():
    fig = re.search(r'<figure class="code" id="contribute-file">\s*<figcaption><a href="([^"]+)">'
                    r'docs/([^<]+)</a></figcaption>\s*<pre>(.*?)</pre>', HOME, re.S)
    assert fig, "no contribute code block"
    href, path, body = fig.groups()
    assert href == path
    assert json.loads(html.unescape(body)) == json.loads((DOCS / path).read_text())


_FORWARD = r"""
const js = require('fs').readFileSync(process.argv[1], 'utf8')
  .match(/<script>(\(function\(\)\{try\{var p=location[\s\S]*?)<\/script>/)[1];
const out = {};
for (const p of JSON.parse(process.argv[2])) {
  let got = null;
  new Function('location', 'document', js)({ pathname: p, replace: (u) => { got = u; } },
                                          { documentElement: { dataset: {} } });
  out[p] = got;
}
console.log(JSON.stringify(out));
"""


def test_404_forwards_the_short_links():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not available")
    cases = {
        "/l/04c6dbdb9b04": "/play/#id=04c6dbdb9b04",
        "/l/04C6DBDB9B04/": "/play/#id=04c6dbdb9b04",
        "/l/paper:qhgk-2019-isaeva/04c6dbdb": "/play/#id=04c6dbdb",
        "/l/paper:qhgk-2019-isaeva": "/experiment/#ref=paper%3Aqhgk-2019-isaeva",
        "/s/2kPq7xYzA": "/play/#s=2kPq7xYzA",
        "/s/2kPq7xYz0": None, "/l/1234567": None, "/guide/missing": None,
    }
    out = subprocess.run([node, "-e", _FORWARD, str(DOCS / "404.html"), json.dumps(list(cases))],
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout) == cases


def _docs_file(url: str) -> Path:
    path = urlparse(url).path.lstrip("/")
    return DOCS / (path + "index.html" if path == "" or path.endswith("/") else path)


def test_robots_sitemap_and_llms_point_at_real_files():
    robots = (DOCS / "robots.txt").read_text()
    assert robots.splitlines()[:2] == ["User-agent: *", "Allow: /"]
    assert "Sitemap: https://openmaterials.ai/sitemap.xml" in robots
    assert "Content-Signal" not in robots, "content signals are the founder's call"
    locs = re.findall(r"<loc>([^<]+)</loc>", (DOCS / "sitemap.xml").read_text())
    assert locs and not [u for u in locs if "/i/" in u], "value pages stay out while they redirect"
    llms = re.findall(r"\((https://openmaterials\.ai/[^)]*)\)", (DOCS / "llms.txt").read_text())
    for url in locs + llms:
        assert _docs_file(url).is_file(), url


def test_shell_pages_link_only_to_files_that_exist():
    for rel in SHELL_PAGES:
        s = (DOCS / rel).read_text()
        assert "fonts.googleapis" not in s and "fonts.gstatic" not in s, rel
        assert not re.search(r"Fraunces|Public Sans|IBM Plex|vendor/(inter|source-serif-4|jetbrains-mono)/", s), rel
        assert "assets/fonts/Geist-Variable.woff2" in s and "assets/site.css" in s, rel
        base = "https://openmaterials.ai/" + rel
        for ref in re.findall(r'(?:href|src)="([^"#]+)', s):
            if "'" in ref:   # a URL a page script assembles at run time
                continue
            url = urljoin(base, html.unescape(ref))
            if urlparse(url).netloc == "openmaterials.ai":
                assert _docs_file(url).exists(), f"{rel}: {ref}"


def test_the_home_jsonld_names_the_dataset_and_the_package():
    block = re.search(r'<script type="application/ld\+json" id="om-jsonld">(.*?)</script>', HOME, re.S)
    graph = {n["@type"]: n for n in json.loads(block.group(1))["@graph"]}
    assert graph["Dataset"]["license"] == "https://creativecommons.org/licenses/by/4.0/"
    assert re.fullmatch(r"[0-9a-f]{64}", graph["Dataset"]["version"])
    assert graph["Organization"]["name"] == "OpenMaterials-AI, a foundation in formation"
    assert graph["SoftwareSourceCode"]["name"] == "openmaterials-ai"
