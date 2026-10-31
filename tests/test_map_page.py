"""The map page (docs/map/index.html) in headless Chrome: formula marks, the Lean ladder, tier ledgers, layers.

Each check frames /map/ at a given size on a local server, runs a script against the page's own globals
(as tests/test_map_share.py does), and reads back JSON.
"""

import contextlib
import functools
import http.server
import json
import re
import shutil
import subprocess
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
LAYERS = json.loads((DOCS / "data" / "map_layers.json").read_text())
CHROME = next((c for c in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser") if shutil.which(c)), None)

HARNESS = """<!doctype html><meta charset="utf-8"><body style="margin:0"><pre id="out">pending</pre>
<iframe id="f" src="/map/%(src)s" width="%(w)d" height="%(h)d" style="border:0;display:block"></iframe>
<script>
const f = document.getElementById('f'), wait = (ms) => new Promise(r => setTimeout(r, ms));
f.onload = async () => {
  const w = f.contentWindow, d = w.document;
  for (let i = 0; i < 300 && !d.querySelector('%(ready)s'); i++) await wait(100);
  await wait(400);
  let result;
  try { result = await (async () => { %(body)s })(); } catch (e) { result = {error: String(e && e.stack || e)}; }
  const err = d.getElementById('err'), failed = err && err.style.display === 'block';
  // on an error, what each script request returned, to tell a server failure from a page bug
  const scripts = failed ? w.performance.getEntriesByType('resource').filter(r => r.initiatorType === 'script').map(r => [r.name.split('/').pop(), r.responseStatus, r.transferSize]) : null;
  document.getElementById('out').textContent = 'RESULT ' + JSON.stringify({result, err: failed ? err.textContent + ' ' + JSON.stringify(scripts) : null});
};
</script>"""


@contextlib.contextmanager
def serve(extra=None, blocked=()):
    """docs/ on a local port, with harness pages added and the paths in blocked answering 404."""
    pages = dict(extra or {})

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.path.split("?")[0] in blocked:
                self.send_error(404)
                return
            if self.path in pages:
                body = pages[self.path].encode()
                self.send_response(200)
                self.send_header("content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(body)
                return
            super().do_GET()

    class Server(http.server.ThreadingHTTPServer):
        request_queue_size = 64   # the page asks for about fifteen files at once; the default backlog of 5 drops some

    httpd = Server(("127.0.0.1", 0), functools.partial(Handler, directory=str(DOCS)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}", pages
    finally:
        httpd.shutdown()


@pytest.fixture(scope="module")
def server():
    with serve() as s:
        yield s


def run(server, src, body, w=1400, h=900, flags=(), ready=".node"):
    """Frame /map/<src> at w x h, run body (an async function body with w, d and wait in scope), return its result."""
    if not CHROME:
        pytest.skip("Chrome not available")
    base, pages = server
    name = f"/__harness{len(pages)}.html"
    pages[name] = HARNESS % {"src": src, "w": w, "h": h, "body": body, "ready": ready}
    out = subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--virtual-time-budget=60000",
                          f"--window-size={w + 40},{h + 120}", *flags, "--dump-dom", base + name],
                         capture_output=True, text=True, timeout=120).stdout
    m = re.search(r"RESULT (\{.*\})", out)
    assert m, out[-2000:]
    got = json.loads(m.group(1).replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&"))
    assert got["err"] is None, got["err"]
    assert not (isinstance(got["result"], dict) and "error" in got["result"]), got["result"]["error"]
    return got["result"]


# The place of every quantity: tier band, column within the band, and rank from the top of the band.
ORDER = """const pos = w.eval('pos'), out = {};
  const byBand = {};
  for (const [id, p] of Object.entries(pos)) (byBand[p.band] = byBand[p.band] || []).push(id);
  for (const ids of Object.values(byBand)) ids.sort((a, b) => pos[a].y - pos[b].y).forEach((id, i) => { out[id] = [pos[id].band, pos[id].col, i]; });
  return out;"""


def test_every_formula_is_a_circle(server):
    got = run(server, "#node=Temperature", "return {formulas: d.querySelectorAll('.fmark').length, circles: d.querySelectorAll('.fmark circle').length};")
    assert got == {"formulas": len(LAYERS["formulas"]), "circles": len(LAYERS["formulas"])}


def test_quantities_keep_their_places(server):
    fixture = json.loads((ROOT / "tests" / "fixtures" / "map_order.json").read_text())
    assert run(server, "", ORDER) == fixture


def test_link_formats_still_open(server):
    checks = {
        "#node=Temperature": "return !!d.querySelector('.node.sel[data-id=\"Temperature\"]') && d.getElementById('panel').style.display === 'block';",
        "#operator=apply_conductance_drift": "return d.getElementById('panel').textContent.includes('apply_conductance_drift');",
        "#code=kaldo": "return d.getElementById('tagPick').value === 'code:kaldo' && d.querySelectorAll('.node:not(.dim)').length > 0;",
        "#physlib=1": "return !!d.getElementById('formal-search');",
        "?embed=1#node=Temperature": "return d.body.classList.contains('embed') && !!d.querySelector('.node.sel[data-id=\"Temperature\"]');",
    }
    for src, body in checks.items():
        assert run(server, src, body) is True, src


def test_ledgers_equal_the_data(server):
    got = run(server, "", "return [...d.querySelectorAll('#bands .band')].map(b => (b.querySelector('.ledger') || {}).textContent || null);")
    want = [f"{t['theorems']} / {t['formulas']} formulas with a Lean theorem" if t["formulas"] else "no formulas" for t in LAYERS["tiers"]]
    assert got == want


def test_rungs_color_quantities_and_formulas(server):
    got = run(server, "", """const r = {};
      for (const el of d.querySelectorAll('.node, .fmark')) { const c = [...el.classList].find(c => c.startsWith('rung-')); r[(el.dataset.id ? 'q:' + el.dataset.id : 'f:' + el.dataset.op)] = c; }
      return r;""")
    want = {f"q:{i}": f"rung-{r['rung']}" for i, r in LAYERS["quantities"].items()}
    want.update({f"f:{i}": f"rung-{r['rung']}" for i, r in LAYERS["formulas"].items()})
    assert got == want


def test_zoom_out_reaches_the_whole_map(server):
    got = run(server, "", """for (let i = 0; i < 60; i++) d.getElementById('zoomOut').click();
      const VB = w.eval('VB'), GW = w.eval('GW'), sc = w.eval('scaleOf()');
      const heads = [...d.querySelectorAll('#bands .far-head')].map(t => +t.getAttribute('font-size') * sc);
      return {left: VB.x <= 0, right: VB.x + VB.w >= GW - 60, far: d.getElementById('svg').classList.contains('far'),
              labels: getComputedStyle(d.getElementById('labels')).display, heads: heads.length, small: heads.filter(px => px < 11).length};""")
    assert got == {"left": True, "right": True, "far": True, "labels": "none", "heads": len(LAYERS["tiers"]) * 2, "small": 0}


def test_no_horizontal_scroll(server):
    for w, h in ((360, 640), (768, 1024), (1400, 900)):
        assert run(server, "#node=Temperature", "return d.documentElement.scrollWidth <= w.innerWidth;", w, h) is True, (w, h)


NONE_Q = sum(r["rung"] == "none" for r in LAYERS["quantities"].values())
NONE_F = sum(r["rung"] == "none" for r in LAYERS["formulas"].values())


def test_layer_hides_without_moving(server):
    fixture = json.loads((ROOT / "tests" / "fixtures" / "map_order.json").read_text())
    got = run(server, "#layer=lean", "return {order: (() => { " + ORDER + " })(), "
              "q: d.querySelectorAll('.node.out').length, f: d.querySelectorAll('.fmark.out').length, "
              "lean: d.querySelector('input[name=layer][value=lean]').checked};")
    assert got == {"order": fixture, "q": NONE_Q, "f": NONE_F, "lean": True}


def test_layer_survives_selection(server):
    got = run(server, "#layer=lean", "w.navTo('Temperature'); await wait(100); return w.location.hash;")
    assert got == "#layer=lean&node=Temperature"


def test_unknown_links_fall_back(server):
    got = run(server, "#layer=bogus", """return {omai: d.querySelector('input[name=layer][value=omai]').checked,
      note: d.getElementById('panel').style.display === 'block' && d.getElementById('panel').textContent.includes('layer=bogus'),
      marks: d.querySelectorAll('.node').length};""")
    assert got == {"omai": True, "note": True, "marks": len(LAYERS["quantities"])}
    assert run(server, "#node=Nope", "return d.getElementById('panel').textContent.includes('Nope');") is True


def test_layer_is_announced(server):
    got = run(server, "", """const r = d.querySelector('input[name=layer][value=lean]'); r.click(); await wait(100);
      return {status: d.getElementById('mapStatus').textContent, hash: w.location.hash};""")
    assert got["status"].startswith("Lean layer:") and got["hash"] == "#layer=lean"


def test_reduced_motion_has_no_transition(server):
    got = run(server, "", "return getComputedStyle(d.querySelector('.node rect')).transitionDuration;",
              flags=("--force-prefers-reduced-motion",))
    assert set(got.split(", ")) == {"0s"}


def test_panel_reads_the_proof(server):
    got = run(server, "#node=Temperature", "return d.getElementById('panel').textContent;")
    assert "Lean theorem on Physlib definitions" in got and "Not covered" in got and "absoluteTemperature_roundtrip" in got
    op = run(server, "#operator=solve_bte%5Bbte_solver%3Ddirect_inverse%5D", "return d.getElementById('panel').textContent;")
    assert "Lean theorem on OMAI definitions" in op


def test_panel_without_bindings():
    with serve(blocked={"/data/formula_bindings.json"}) as s:
        got = run(s, "#node=Temperature", "return d.getElementById('panel').textContent;")
    assert "Lean theorem on Physlib definitions" in got and "absoluteTemperature_roundtrip" in got and "did not load" in got


def test_search_finds_lean_names(server):
    got = run(server, "", """const q = d.getElementById('q'); q.value = 'absoluteTemperature_roundtrip';
      q.dispatchEvent(new w.Event('input')); await wait(100);
      return [...d.querySelectorAll('.node:not(.dim)')].map(el => el.dataset.id);""")
    assert got == ["Temperature"]


def test_table_lists_every_mark(server):
    got = run(server, "#layer=lean", """d.getElementById('tableBtn').click(); await wait(100);
      const rows = [...d.querySelectorAll('#table tbody tr')];
      return {rows: rows.length, visible: !d.getElementById('table').hidden,
              href: rows[0].querySelector('a').getAttribute('href'), pressed: d.getElementById('tableBtn').getAttribute('aria-pressed')};""")
    assert got["rows"] == len(LAYERS["quantities"]) + len(LAYERS["formulas"]) and got["visible"] and got["pressed"] == "true"
    assert got["href"].startswith("#layer=lean&node=")


def test_without_dagre_the_table_stands_in():
    with serve(blocked={"/assets/vendor/dagre.min.js"}) as s:
        got = run(s, "", "return d.querySelectorAll('#fallback tbody tr').length;", ready="#fallback tbody tr")
    assert got == len(LAYERS["quantities"]) + len(LAYERS["formulas"])


def test_escape_returns_focus_to_the_mark(server):
    got = run(server, "", """const g = d.querySelector('.node[data-id="Temperature"]'); g.focus();
      g.dispatchEvent(new w.KeyboardEvent('keydown', {key: 'Enter', bubbles: true})); await wait(100);
      const open = d.getElementById('panel').style.display === 'block';
      w.dispatchEvent(new w.KeyboardEvent('keydown', {key: 'Escape', bubbles: true})); await wait(100);
      return {open, closed: d.getElementById('panel').style.display === 'none', focus: d.activeElement === g};""")
    assert got == {"open": True, "closed": True, "focus": True}


def test_the_toolbar_keeps_one_row_on_a_laptop(server):
    # one row of 32 px controls with 8 px padding above and below and a 1 px rule; a second row adds 40
    got = run(server, "", "return d.querySelector('.toolbar').getBoundingClientRect().height;", 1400, 900)
    assert got < 60, got


GRAPH = json.loads((DOCS / "data" / "graph.json").read_text())
THEOREMS = sum(r["rung"] in ("local", "physlib") for r in LAYERS["formulas"].values())
OVER = "return d.getElementById('svg').classList.contains('overview');"


def test_search_and_code_links_keep_labels_readable(server):
    assert run(server, "", "const q = d.getElementById('q'); q.value = 'frequency'; q.dispatchEvent(new w.Event('input')); await wait(100); " + OVER) is False
    assert run(server, "#code=phonopy", OVER) is False
    assert run(server, "?embed=1#code=kaldo", OVER, 800, 480) is False


def test_without_map_layers_the_formulas_still_draw():
    with serve(blocked={"/data/map_layers.json"}) as s:
        got = run(s, "", "return {f: d.querySelectorAll('.fmark').length, ledgers: d.querySelectorAll('#bands .ledger').length};")
    assert got == {"f": len({l["op"] for l in GRAPH["links"] if l.get("kind") != "param"}), "ledgers": 0}


def test_a_link_without_layer_keeps_the_layer(server):
    got = run(server, "#layer=lean&node=Temperature", """w.location.hash = '#physlib=1'; await wait(200);
      const lean = d.querySelector('input[name=layer][value=lean]').checked;
      d.getElementById('tableBtn').click(); await wait(50);
      d.querySelector('input[name=layer][value=omai]').click(); await wait(50);
      return {lean, href: d.querySelector('#table tbody a').getAttribute('href')};""")
    assert got["lean"] is True and got["href"].startswith("#node=")


def test_hidden_wires_do_not_catch_the_mouse(server):
    assert run(server, "#layer=lean", "return getComputedStyle(d.querySelector('.wire.out')).pointerEvents;") == "none"


def test_operator_links_work_without_bindings():
    with serve(blocked={"/data/formula_bindings.json"}) as s:
        got = run(s, "#operator=compute_dispersion", "return {text: d.getElementById('panel').textContent, hash: w.location.hash};")
    assert "compute_dispersion" in got["text"] and "No such" not in got["text"] and got["hash"] == "#operator=compute_dispersion"


def test_selecting_a_hidden_mark_shows_the_omai_layer(server):
    got = run(server, "#layer=lean&node=AtomCount", "return {omai: d.querySelector('input[name=layer][value=omai]').checked, hash: w.location.hash};")
    assert got == {"omai": True, "hash": "#node=AtomCount"}
    hidden = run(server, "#layer=lean&code=kaldo", """return w.eval('litIds()').filter(id => d.querySelector('.node[data-id="' + id + '"]').classList.contains('out')).length;""")
    assert hidden == 0


def test_overview_heads_stay_inside_their_bands_on_a_phone(server):
    got = run(server, "", """for (let i = 0; i < 60; i++) d.getElementById('zoomOut').click(); await wait(50);
      return [...d.querySelectorAll('#bands .far-head')].filter(t => getComputedStyle(t).display !== 'none' && t.getAttribute('visibility') !== 'hidden')
        .map(t => { const b = t.getBBox(), left = +t.getAttribute('x') - 26; return b.x + b.width <= left + 360 && b.y + b.height <= +t.dataset.top + 184; });""", 390, 844)
    assert all(got), got


def test_a_parameter_link_dims_the_formulas(server):
    got = run(server, "", """d.querySelector('.edge.param').dispatchEvent(new w.MouseEvent('click', {bubbles: true})); await wait(50);
      return [...d.querySelectorAll('.fmark')].every(el => el.classList.contains('dim'));""")
    assert got is True


def test_a_declaration_of_formulas_only_is_found(server):
    got = run(server, "", """const q = d.getElementById('q'); q.value = 'fold_dynamicalMatrix'; q.dispatchEvent(new w.Event('input')); await wait(100);
      return {status: d.getElementById('mapStatus').textContent, lit: d.querySelectorAll('.fmark:not(.dim)').length};""")
    assert "0 match" not in got["status"] and got["lit"] > 0


def test_lean_search_waits_for_a_lean_name(server):
    got = run(server, "", """const q = d.getElementById('q'); q.value = 'Temperature'; q.dispatchEvent(new w.Event('input')); await wait(100);
      return [...d.querySelectorAll('.node:not(.dim)')].map(el => el.dataset.id);""")
    assert "PhononDOS" not in got


def test_escape_closes_the_table(server):
    got = run(server, "", """d.getElementById('tableBtn').click(); await wait(50);
      w.dispatchEvent(new w.KeyboardEvent('keydown', {key: 'Escape', bubbles: true})); await wait(50);
      return d.getElementById('table').hidden;""")
    assert got is True


def test_the_omai_layer_counts_theorems(server):
    got = run(server, "", "d.querySelector('input[name=layer][value=lean]').click(); d.querySelector('input[name=layer][value=omai]').click(); await wait(50); return d.getElementById('mapStatus').textContent;")
    assert f"{THEOREMS} formulas have a Lean theorem" in got


PTSE2 = "paper:ptse2-2021-donadio"
LIT = "return [...d.querySelectorAll('.node:not(.dim)')].map(el => el.dataset.id).sort();"


def test_a_paper_tag_frames_its_area(server):
    got = run(server, "#tag=" + PTSE2, """const f = d.querySelector('#tagFrame .tag-box'), k = d.querySelector('.node[data-id="ThermalConductivity"] rect');
      const fb = f.getBBox(), kb = k.getBBox();
      return {frames: d.querySelectorAll('#tagFrame .tag-box').length, tab: d.querySelector('#tagFrame .tab-text').textContent,
              inside: fb.x <= kb.x && fb.y <= kb.y && fb.x + fb.width >= kb.x + kb.width && fb.y + fb.height >= kb.y + kb.height,
              pick: d.getElementById('tagPick').value, hash: w.location.hash};""")
    assert got["frames"] == 1 and got["inside"] and got["pick"] == PTSE2 and got["hash"] == "#tag=" + PTSE2
    assert got["tab"].startswith("paper · ") and "\u2014" not in got["tab"] and "formulas with a Lean theorem" in got["tab"]


def test_the_code_hash_is_the_code_tag(server):
    assert run(server, "#code=kaldo", LIT) == run(server, "#tag=code:kaldo", LIT)
    assert run(server, "#code=kaldo", "return d.querySelectorAll('#tagFrame .tag-box').length;") == 1


def test_an_unknown_tag_says_so(server):
    got = run(server, "#tag=paper:nope", "return {note: d.getElementById('panel').textContent.includes('tag=paper:nope'), frames: d.querySelectorAll('#tagFrame .tag-box').length};")
    assert got == {"note": True, "frames": 0}


def test_an_embed_keeps_layer_and_tag(server):
    got = run(server, "?embed=1#layer=lean&tag=" + PTSE2, """return {embed: d.body.classList.contains('embed'),
      lean: d.querySelector('input[name=layer][value=lean]').checked, frames: d.querySelectorAll('#tagFrame .tag-box').length,
      out: d.getElementById('embedOut').getAttribute('href')};""", 800, 480)
    assert got["embed"] and got["lean"] and got["frames"] == 1 and got["out"].endswith("#layer=lean&tag=" + PTSE2)


def test_a_mark_lists_its_papers(server):
    got = run(server, "#node=ThermalConductivity", "return d.getElementById('panel').textContent;")
    assert "Papers" in got and LAYERS["tags"][PTSE2]["label"] in got


def test_clearing_the_tag_clears_its_frame(server):
    got = run(server, "#tag=" + PTSE2, """const p = d.getElementById('tagPick'); p.value = ''; p.dispatchEvent(new w.Event('change')); await wait(50);
      return {frames: d.querySelectorAll('#tagFrame .tag-box').length, hash: w.location.hash, dim: d.querySelectorAll('.node.dim').length};""")
    assert got == {"frames": 0, "hash": "", "dim": 0}


def test_the_legend_and_the_caption_do_not_overlap(server):
    for w_, h_ in ((1400, 900), (1100, 800)):
        got = run(server, "#layer=lean", """const a = d.querySelector('.legend').getBoundingClientRect(), b = d.getElementById('caption').getBoundingClientRect();
          return a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top;""", w_, h_)
        assert got is True, (w_, h_)
