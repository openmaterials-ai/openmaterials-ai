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
  const err = d.getElementById('err');
  document.getElementById('out').textContent = 'RESULT ' + JSON.stringify({result, err: err && err.style.display === 'block' ? err.textContent : null});
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
    got = run(server, "", "return {formulas: d.querySelectorAll('.formula').length, circles: d.querySelectorAll('.formula circle').length};")
    assert got == {"formulas": len(LAYERS["formulas"]), "circles": len(LAYERS["formulas"])}


def test_quantities_keep_their_places(server):
    fixture = json.loads((ROOT / "tests" / "fixtures" / "map_order.json").read_text())
    assert run(server, "", ORDER) == fixture


def test_link_formats_still_open(server):
    checks = {
        "#node=Temperature": "return !!d.querySelector('.node.sel[data-id=\"Temperature\"]') && d.getElementById('panel').style.display === 'block';",
        "#operator=apply_conductance_drift": "return d.getElementById('panel').textContent.includes('apply_conductance_drift');",
        "#code=kaldo": "return d.getElementById('codeFilter').value === 'kaldo' && d.querySelectorAll('.node:not(.dim)').length > 0;",
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
      for (const el of d.querySelectorAll('.node, .formula')) { const c = [...el.classList].find(c => c.startsWith('rung-')); r[(el.dataset.id ? 'q:' + el.dataset.id : 'f:' + el.dataset.op)] = c; }
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
              "q: d.querySelectorAll('.node.out').length, f: d.querySelectorAll('.formula.out').length, "
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
    assert "Lean theorem citing Physlib" in got and "Not covered" in got and "absoluteTemperature_roundtrip" in got
    op = run(server, "#operator=solve_bte%5Bbte_solver%3Ddirect_inverse%5D", "return d.getElementById('panel').textContent;")
    assert "Lean theorem over Mathlib" in op


def test_panel_without_bindings():
    with serve(blocked={"/data/formula_bindings.json"}) as s:
        got = run(s, "#node=Temperature", "return d.getElementById('panel').textContent;")
    assert "Lean theorem citing Physlib" in got and "absoluteTemperature_roundtrip" in got and "did not load" in got


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
