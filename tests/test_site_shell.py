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
SHELL_PAGES = ["index.html", "guide/index.html", "codes/index.html", "lean/index.html", "lean/bridge/index.html",
               "lean/roadmap/index.html", "agreement/index.html",
               "lineage/index.html", "document/index.html", "404.html", "map/index.html",
               "map-3d/index.html", "map-trace/index.html", "play/index.html"]


def _ledger(html_text):
    """dt label -> dd text, tags (such as <wbr>) stripped."""
    return {html.unescape(re.sub(r"<[^>]+>", "", dt)).strip(): html.unescape(re.sub(r"<[^>]+>", "", dd)).strip()
            for dt, dd in re.findall(r"<dt>(.*?)</dt><dd[^>]*>(.*?)</dd>", html_text, re.S)}


def _silicon_near_300(inst):
    """The selection home Fig. 1 draws: crystalline silicon, 270 to 310 K."""
    def t(c):
        return float(re.match(r"[0-9.]+", str(c.get("T", c.get("temperature_K")))).group())
    return sorted((i for i in inst if i["variable"].startswith("ThermalConductivity")
                   and re.fullmatch(r"Si( \(diamond\))?", i["material"]) and 270 <= t(i["conditions"]) <= 310),
                  key=lambda i: i["value"])


def test_fig1_fallback_rows_equal_the_instances():
    """The rows Fig. 1 shows before its script runs summarize the values the script draws:
    each group's values (the recorded runs as a range), each linked id on its own value."""
    fig = re.search(r'<figure class="fig datum" id="fig-1"[^>]*>(.*?)</figure>', HOME, re.S)
    assert fig, "no Fig. 1"
    rows = _ledger(fig.group(1))
    pts = _silicon_near_300(json.loads((DOCS / "data/instances.json").read_text()))
    meas = [i for i in pts if i["source"]["kind"] == "measurement"]
    paper = [i for i in pts if i["source"]["kind"] != "measurement" and i["source"]["ref"].startswith("paper:")]
    runs = [i for i in pts if i not in meas and i not in paper]
    def g3(v):
        return f"{float(format(v, '.3g')):g}"

    def temp(i):
        t = float(str(i["conditions"]["T"]).split()[0])
        return "" if t == 300 else f" ({t:g} K)"

    assert rows["Measured"] == ", ".join(g3(i["value"]) for i in meas)
    assert rows["Published calculations"] == ", ".join(g3(i["value"]) + temp(i) for i in paper)
    assert rows["Recorded runs"] == f"{g3(runs[0]['value'])} to {g3(runs[-1]['value'])}"
    by_id = {i["id"]: i for i in pts}
    for m, shown in re.findall(r'play/#id=([0-9a-f]{64})">([^<]+)<', fig.group(1)):
        assert m in by_id and g3(by_id[m]["value"]) == shown, (m, shown)
    assert 'href="https://materialscodegraph.com/?ref=omai-home#hero-connect"' in fig.group(1)


def test_the_contribute_block_is_the_committed_file():
    fig = re.search(r'<figure class="code" id="contribute-file">\s*<figcaption><a href="([^"]+)">'
                    r'One committed value</a></figcaption>\s*<pre>(.*?)</pre>', HOME, re.S)
    assert fig, "no contribute code block"
    path, body = fig.groups()
    shown = json.loads(html.unescape(body))
    assert shown == json.loads((DOCS / path).read_text())
    assert f'play/#id={shown["id"]}' in HOME, "the example is a record Fig. 1 links"


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
        "/l/paper:qhgk-2019-isaeva": None,
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
        assert not re.search(r"Geist[-\w]*\.woff2|geist\.css", s), rel
        assert "assets/fonts/newsreader-latin.woff2" in s and "assets/site.css" in s, rel
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
        "s-values": str(len(inst)),
        "s-sim": str(kinds.count("simulation")),
        "s-meas": str(kinds.count("measurement")),
    }
    for el_id, want in expect.items():
        got = re.search(r'id="%s">([^<]*)<' % el_id, HOME)
        assert got and got.group(1) == want, f"#{el_id}: {got and got.group(1)!r} != {want!r}"
    bindings = _data("formula_bindings.json")
    binds = {"codes": len(codes), "lean-nodes": len(lean["nodes"]),
             "lean-ops": bindings["coverage"]["operators_compiled"], "version12": ver["version"][:12],
             "n-nodes": len(g["nodes"]), "n-values": len(inst), "n-meas": kinds.count("measurement")}
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


_SOURCES = r"""
const fs = require('fs');
eval(fs.readFileSync(process.argv[1].replace('sources.js', 'map-words.js'), 'utf8'));   // nodeName
eval(fs.readFileSync(process.argv[1], 'utf8'));   // assets/sources.js: var Sources
const page = fs.readFileSync(process.argv[2], 'utf8');
const label = new Function(page.slice(page.indexOf('var METHOD'), page.indexOf('var DATA')) + '; return methodLabel;')();
const [recs, agreement, codes] = process.argv.slice(3).map(f => JSON.parse(fs.readFileSync(f, 'utf8')));
const byRef = {};
for (const r of recs) (byRef[r.source.ref] = byRef[r.source.ref] || []).push(r);
const titles = {};
for (const ref in byRef) titles[ref] = Sources.titleOf(byRef[ref], codes);
const one = id => recs.find(r => r.id.startsWith(id));
console.log(JSON.stringify({titles, quotes: recs.map(r => Sources.parts(r.source.detail).quote),
  conds: recs.map(r => Sources.condText(r.conditions)), methods: recs.map(r => Sources.methodLine(r, codes)),
  ptse2: Sources.condText(one('457f936b93d9').conditions), si: Sources.condText(one('f735a05c14db').conditions),
  conformance: Sources.methodLine(one('f64affbf549a'), codes),
  precision: Sources.condText(one('c7f4680c4137').conditions),
  ethanol: [...new Set(Sources.groups(recs)['atomisticskills-chem-bond-dissociation-ethanol'].map(r => Sources.methodLine(r, codes)))],
  name: nodeName('ThermalConductivity[bte_solver=direct_inverse]'),
  labels: [].concat(...agreement.groups.map(g => g.members.map(m => label(m)))),
  fam: [Sources.family('atomisticskills-chem-bond-dissociation-ethanol-bond3'), Sources.family('paper:esfarjani-2011')]}));
"""


def test_sources_take_their_citations_and_print_plain_words():
    """A source is titled by the citation its records carry, or as its code's run; conditions read T in
    kelvin and drop curator notes, commit asides and hashes; a run prints one method line from its
    structured fields; the agreement page prints a method label, never the raw method string."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not available")
    out = subprocess.run([node, "-e", _SOURCES, str(DOCS / "assets/sources.js"), str(DOCS / "agreement/index.html"),
                          *(str(DOCS / "data" / f) for f in ("instances.json", "agreement.json", "codes.json"))],
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    got = json.loads(out.stdout)
    titles = got["titles"]
    kaldo = titles["paper:kaldo-2020-barbalinardo"]
    assert kaldo.startswith("G. Barbalinardo, Z. Chen") and kaldo.endswith("J. Appl. Phys. 128, 135104 (2020)")
    assert titles["glassbrenner-slack-1964"] == "Glassbrenner and Slack, Phys. Rev. 134, A1058 (1964)"
    assert all(titles[r] for r in titles if r.startswith("paper:")), "every paper source carries a citation"
    assert titles["kaldo"].endswith(" run") and not titles["materialscodegraph"], "a code's run, or the ref"
    assert not [t for t in titles.values() if re.search(r"doi:|arXiv:|\[", t)]
    assert not [q for q in got["quotes"] if "[MIGRATED" in q]
    assert got["ptse2"].endswith("method = first-principles BTE, solver not stated")
    assert got["si"].startswith("T 300 K · ")
    assert not [c for c in got["conds"] if "unstated" in c or re.search(r"\b[0-9a-f]{64}\b", c)]
    assert got["conformance"].endswith(" 2.2.1 run of Si with the Tersoff potential")
    assert "precision = frozen eskm reference output; MESCAL reproduces it on the CPU complex128 path" in got["precision"]
    assert "commit" not in got["precision"] and "source of truth" not in got["precision"]
    assert got["ethanol"] == ["Computed with MACE-OFF23-small"], "one line per distinct method"
    assert not [m for m in got["methods"] if ".json" in m], "no repo paths in a method line"
    assert got["name"] == "Thermal conductivity (direct inverse)"
    assert got["fam"] == ["atomisticskills-chem-bond-dissociation-ethanol", "paper:esfarjani-2011"]
    assert set(got["labels"]) <= {"Direct inversion", "RTA", "Solver not stated", "Measured"}


def test_the_lineage_tour_opens_its_example():
    ex = {e["slug"]: e for e in json.loads((DOCS / "examples/index.json").read_text())}["a-si-kappa-qhgk"]
    page = (DOCS / "lineage/index.html").read_text()
    assert '../play/#/play?tab=lineage&amp;x=' + ex["fragment"] + '"' in page
    assert ">Id " + ex["id"] + "<" in page


def test_the_home_names_codes_that_ran_values():
    """The Values section names a few codes; each one ran committed values, by its codes.json name."""
    inst, codes = _data("instances.json"), _data("codes.json")
    ran = {i["source"]["ref"].split("-")[0] for i in inst} | {str(i["conditions"].get("code", "")).split(" ")[0] for i in inst}
    named = re.search(r"Values come from published papers and from runs of ([^.<]+)\.", HOME).group(1)
    alias = {a: rep for rep, e in codes.items() for a in next(iter(e.values())).get("aliases", [])}
    ran |= {alias[k] for k in ran if k in alias}
    for key in ("kaldo", "phono3py", "qe", "meskal", "xtb"):
        assert key in ran and next(iter(codes[key].values()))["name"] in named, key
