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


def _ledger(html_text):
    """dt label -> dd text, tags (such as <wbr>) stripped."""
    return {html.unescape(re.sub(r"<[^>]+>", "", dt)).strip(): html.unescape(re.sub(r"<[^>]+>", "", dd)).strip()
            for dt, dd in re.findall(r"<dt>(.*?)</dt><dd[^>]*>(.*?)</dd>", html_text, re.S)}


def test_the_datum_card_equals_its_instance():
    card = re.search(r'<article class="card datum" data-instance="([0-9a-f]{64})">(.*?)</article>', HOME, re.S)
    assert card, "no datum card"
    by_id = {i["id"]: i for i in json.loads((DOCS / "data/instances.json").read_text())}
    inst = by_id[card.group(1)]
    figure = re.search(r'<p class="figure">([^<]+)<span class="unit">([^<]+)</span></p>', card.group(2))
    assert float(figure.group(1)) == inst["value"] and figure.group(2) == inst["units"]
    rows = _ledger(card.group(2))
    assert rows["Quantity"] == inst["variable"]
    assert rows["Material"] == inst["material"]
    assert rows["Conditions"] == ", ".join(f"{k} = {v}" for k, v in inst["conditions"].items())
    assert rows["Source"] == f'{inst["source"]["kind"]}, {inst["source"]["ref"]}'
    assert rows["Id"] == inst["id"]
    # the measurement shown beside it is the committed one, on the same quantity and material
    mid = re.search(r'<dd class="mono" data-instance="([0-9a-f]{64})">', card.group(2)).group(1)
    meas = by_id[mid]
    assert meas["source"]["kind"] == "measurement"
    assert meas["variable"] == inst["variable"].split("[")[0] and meas["material"] == inst["material"].split(" ")[0]
    assert rows["Measured"] == f'{meas["value"]:g} {meas["units"]}, {meas["source"]["ref"]}'
    assert f'play/#id={inst["id"]}' in card.group(2) and f'play/#id={mid}' in card.group(2)


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
    assert robots.splitlines()[:3] == ["User-agent: *", "Allow: /",
                                       "Content-Signal: search=yes, ai-input=yes, ai-train=yes"], \
        "the founder's content signals: search, AI input and AI training all allowed"
    assert "Sitemap: https://openmaterials.ai/sitemap.xml" in robots
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


def _data(name):
    return json.loads((DOCS / "data" / name).read_text())


def test_the_home_static_text_equals_the_data():
    """The home page prints every count and hash statically, so it reads right
    without JS; each one must equal the value recomputed from docs/data."""
    g, codes, inst = _data("graph.json"), _data("codes.json"), _data("instances.json")
    lean, ver, roadmap = _data("lean.json"), _data("version.json"), _data("lean_roadmap.json")
    types = [n["type"] for n in g["nodes"]]
    params = sum(1 for link in g["links"] if link.get("kind") == "param")
    kinds = [i["source"]["kind"] for i in inst]
    expect = {
        "s-nodes": f"{len(types)} ({types.count('observable')} observable, {types.count('hidden')} hidden, "
                   f"{types.count('parameter')} parameter)",
        "s-links": f"{len(g['links'])} ({len(g['links']) - params} formula, {params} parameter)",
        "s-ops": str(len(roadmap["rows"])),
        "s-tiers": str(len(g["tiers"])),
        "s-codes": str(len(codes)),
        "s-lean": f"{len(lean['nodes'])} node dimensions, {len(lean['edges'])} edge theorems, "
                  f"{len(lean['identities'])} identities",
        "s-values": str(len(inst)),
        "s-sim": str(kinds.count("simulation")),
        "s-meas": str(kinds.count("measurement")),
        "s-version": ver["version"],
        "s-graph": ver["graph_version"],
        "s-genesis": ver["genesis"],
    }
    for el_id, want in expect.items():
        got = re.search(r'id="%s">([^<]*)<' % el_id, HOME)
        assert got and got.group(1) == want, f"#{el_id}: {got and got.group(1)!r} != {want!r}"
    binds = {"codes": len(codes), "lean-nodes": len(lean["nodes"]), "lean-edges": len(lean["edges"]),
             "lean-idents": len(lean["identities"]), "version12": ver["version"][:12]}
    for bind, want in binds.items():
        got = re.findall(r'data-bind="%s">([^<]*)<' % bind, HOME)
        assert got and set(got) == {str(want)}, f"data-bind={bind}: {got} != {want}"


def test_the_home_jsonld_matches_the_data_and_the_package():
    import tomllib
    block = re.search(r'<script type="application/ld\+json" id="om-jsonld">(.*?)</script>', HOME, re.S)
    graph = {n["@type"]: n for n in json.loads(block.group(1))["@graph"]}
    steward = {"@id": "https://openmaterials.ai/#steward"}
    ds = graph["Dataset"]
    assert ds["version"] == _data("version.json")["version"]
    assert ds["license"] == "https://creativecommons.org/licenses/by/4.0/"
    assert ds["creator"] == steward and ds["maintainer"] == steward
    for dl in ds["distribution"]:
        assert _docs_file(dl["contentUrl"]).is_file(), dl["contentUrl"]
    assert {"graph.json", "semantics.json", "instances.json", "lean.json", "version.json"} <= \
        {dl["name"] for dl in ds["distribution"]}
    assert graph["Project"]["name"] == "OpenMaterials-AI"
    assert graph["Project"]["description"] == "A foundation in formation."
    pyproject = tomllib.loads((DOCS.parent / "pyproject.toml").read_text())
    assert graph["SoftwareSourceCode"]["name"] == pyproject["project"]["name"]
    assert graph["SoftwareSourceCode"]["version"] == pyproject["project"]["version"]
