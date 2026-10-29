"""Render each code's social card as a picture of its submap: docs/assets/og/codes/<key>.png.

The card is a 1200 x 630 screenshot of the embedded map with the code's coverage lit
(``map/?embed=1#code=<key>``), taken with headless Chrome against a local server on docs/.
Without Chrome the SVG text card drawn by ``omai.code_pages`` stays. The PNGs are a release
artifact: their bytes depend on the browser build and fonts, the HTML does not.

Run after ``python -m omai.code_pages``::

    PYTHONPATH=. python -m omai.code_cards
"""

from __future__ import annotations

import http.server
import json
import shutil
import socketserver
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CARDS = DOCS / "assets" / "og" / "codes"
CHROME = next((c for c in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser") if shutil.which(c)), None)


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # one line per asset per code would drown the result line
        pass


def _serve() -> tuple[socketserver.TCPServer, int]:
    handler = lambda *a, **k: _Quiet(*a, directory=str(DOCS), **k)  # noqa: E731
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def render(keys: list[str], port: int) -> list[str]:
    done = []
    for key in keys:
        out = CARDS / f"{key}.png"
        # headless Chrome leaves the bottom 88 px of the window outside the viewport: render taller, crop to 1200 x 630
        subprocess.run(
            [CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--window-size=1200,718",
             "--virtual-time-budget=10000", f"--screenshot={out}", f"http://127.0.0.1:{port}/map/?embed=1#code={key}"],
            check=True, capture_output=True,
        )
        try:
            from PIL import Image
        except ImportError:
            pass
        else:
            with Image.open(out) as im:
                im.crop((0, 0, 1200, 630)).save(out, optimize=True)
        done.append(key)
    return done


def main() -> int:
    if not CHROME:
        print("no Chrome on the PATH; the SVG text cards stay", file=sys.stderr)
        return 0
    codes = json.loads((DOCS / "data" / "codes.json").read_text())
    registry = json.loads((DOCS / "data" / "registry.json").read_text()).get("code", {})
    keys = sorted(k for k in codes if (registry.get(k) or {}).get("visibility") != "private")
    httpd, port = _serve()
    try:
        done = render(keys, port)
    finally:
        httpd.shutdown()
    print(f"{len(done)} cards rendered under {CARDS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
