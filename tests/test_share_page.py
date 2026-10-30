"""The share landing page (docs/share/index.html): static contract, then a headless Chrome render."""

import functools
import http.server
import json
import re
import shutil
import subprocess
import threading

import pytest

from omai import submap
from omai.snapshots import DATA, decode, encode

PAGE = DATA.parent / "share" / "index.html"
CHROME = next((c for c in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser") if shutil.which(c)), None)


def test_page_contract():
    s = PAGE.read_text()
    assert "<!--share-meta-->" in s
    assert 'from "/assets/share.js"' in s and 'from "/assets/submap.js"' in s
    assert "<noscript>" in s
    assert "\u2014" not in s
    for line in submap.CSS.strip().splitlines():
        assert line.strip() in s, line



def test_hidden_beats_button_display():
    # the Download PNG button carries hidden off the Worker; .btn sets display, so the stylesheet must let hidden win
    css = (DATA.parent / "assets" / "site.css").read_text()
    assert re.search(r"^\[hidden\] \{ display: none !important; \}", css, re.M)
    assert re.search(r'id="png"[^>]*\shidden', PAGE.read_text())

@pytest.fixture(scope="module")
def docs_server():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    handler = functools.partial(Quiet, directory=str(DATA.parent))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def dom(url: str) -> str:
    if not CHROME:
        pytest.skip("Chrome not available")
    proc = subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--virtual-time-budget=10000", "--dump-dom", url],
                          capture_output=True, text=True, timeout=60)
    return proc.stdout


def latest():
    index = json.loads((DATA / "v" / "index.json").read_text())
    return index["latest"], json.loads((DATA / "v" / f"{index['latest']}.json").read_text())


def test_a_code_renders(docs_server):
    h, snap = latest()
    ids = snap["codes"]["kaldo"]["nodes"]
    out = dom(f"{docs_server}/share/#{h[:12]}/{encode(snap, ids)}")
    assert re.search(r'<h1 id="title">kALDo</h1>', out)
    assert '<svg class="submap-svg' in out
    qty = out.split('id="qty"')[1].split("</ul>")[0]
    assert qty.count("<li>") == len(ids)
    assert 'id="related" hidden' not in out


def test_one_quantity_renders_with_context(docs_server):
    h, snap = latest()
    out = dom(f"{docs_server}/share/#{h[:12]}/{encode(snap, ['Temperature'])}")
    name = next(n["name"] for n in snap["nodes"] if n["id"] == "Temperature")
    assert f'<h1 id="title">{name}</h1>' in out
    assert "sm-ctx" in out


@pytest.mark.parametrize("frag,words", [
    ("zz/80", "not a share link"),
    ("ffffffffffff/80", "No snapshot"),
])
def test_bad_links_say_why(docs_server, frag, words):
    out = dom(f"{docs_server}/share/#{frag}")
    assert "This link does not open a selection" in out and words in out


def test_out_of_range_selection_is_refused(docs_server):
    h, snap = latest()
    n = len(snap["nodes"])
    buf = bytearray(n // 8 + 1)
    buf[n // 8] = 0x80 >> (n % 8)
    assert decode(snap, buf.hex()) is None
    out = dom(f"{docs_server}/share/#{h[:12]}/{buf.hex()}")
    assert "does not fit this snapshot" in out


def test_embed_shows_the_submap_alone(docs_server):
    h, snap = latest()
    out = dom(f"{docs_server}/share/?embed=1#{h[:12]}/{encode(snap, snap['codes']['kaldo']['nodes'])}")
    assert 'class="embed"' in out and '<svg class="submap-svg' in out
