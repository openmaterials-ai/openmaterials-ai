"""The map's Share button: a permanent /m/ link for whatever is lit, checked in headless Chrome."""

import functools
import http.server
import json
import re
import shutil
import subprocess
import threading

import pytest

from omai.snapshots import DATA, decode

DOCS = DATA.parent
CHROME = next((c for c in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser") if shutil.which(c)), None)

# Loads the map in a same-origin frame, captures the clipboard, runs the steps, prints what Share copied.
HARNESS = """<!doctype html><meta charset="utf-8"><body><pre id="out">pending</pre><iframe id="f" src="/map/%s" width="1400" height="900"></iframe>
<script>
const f = document.getElementById('f'), wait = (ms) => new Promise(r => setTimeout(r, ms));
f.onload = async () => {
  const w = f.contentWindow, d = w.document;
  let copied = null;
  Object.defineProperty(w.navigator, 'clipboard', { value: { writeText: async (t) => { copied = t; } } });
  for (let i = 0; i < 300 && !d.querySelector('.node'); i++) await wait(100);
  // ready: the hash selection applied (something dimmed, when the link names one) and the share kit loaded
  for (let i = 0; i < 300 && w.location.hash && !d.querySelector('.node.dim'); i++) await wait(100);
  for (let i = 0; i < 300 && !w.eval('shareKit'); i++) await wait(100);
  const picks = %s;
  // the map may still settle its first view; pick until exactly the picks are lit
  for (let i = 0; i < 20 && picks.length && d.querySelectorAll('.node.sel').length !== picks.length; i++) {
    w.eval('clearSel()');
    for (const id of picks) d.querySelector('.node[data-id="' + id + '"]').dispatchEvent(new w.MouseEvent('click', { bubbles: true, shiftKey: true }));
    await wait(200);
  }
  d.getElementById('copylink').click();
  for (let i = 0; i < 300 && copied === null; i++) await wait(100);
  document.getElementById('out').textContent = 'COPIED ' + copied + ' KIT ' + !!w.eval('shareKit') + ' LIT ' + w.eval('litIds()').length;
};
</script>"""


@pytest.fixture(scope="module")
def server():
    pages = {}

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.path in pages:
                body = pages[self.path].encode()
                self.send_response(200)
                self.send_header("content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(body)
                return
            super().do_GET()

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(DOCS)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}", pages
    httpd.shutdown()


def copied(server, hash_, shift_ids):
    if not CHROME:
        pytest.skip("Chrome not available")
    base, pages = server
    name = f"/__harness{len(pages)}.html"
    pages[name] = HARNESS % (hash_, json.dumps(shift_ids))
    out = subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--virtual-time-budget=60000", "--dump-dom", base + name],
                         capture_output=True, text=True, timeout=90).stdout
    m = re.search(r"COPIED ([^<\s]+)", out)
    assert m, out[-2000:]
    return m.group(1)


def snapshot():
    index = json.loads((DATA / "v" / "index.json").read_text())
    return index["latest"], json.loads((DATA / "v" / f"{index['latest']}.json").read_text())


def selection(url, h):
    m = re.fullmatch(r"https://openmaterials\.ai/m/([0-9a-f]{12})/([0-9a-f]+)", url)
    assert m and h.startswith(m.group(1)), url
    return m.group(2)


def test_share_links_the_lit_code(server):
    h, snap = snapshot()
    url = copied(server, "#code=kaldo", [])
    assert set(decode(snap, selection(url, h))) == set(snap["codes"]["kaldo"]["nodes"])


def test_shift_click_picks_exactly_those(server):
    h, snap = snapshot()
    url = copied(server, "", ["Temperature", "Potential"])
    assert set(decode(snap, selection(url, h))) == {"Temperature", "Potential"}


def test_nothing_lit_copies_the_map_view(server):
    url = copied(server, "", [])
    assert url.endswith("/map/")
