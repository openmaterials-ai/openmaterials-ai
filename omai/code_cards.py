"""Render each code's poster and social card from its infographic page.

Headless Chrome screenshots ``codes/<key>/infographic/`` (the brief on a 1920 x 1080 canvas) against
a local server on docs/. The poster is kept as docs/assets/infographics/<key>.png for LinkedIn; the
same picture scaled to 1200 x 675 and trimmed to 630 is the social card docs/assets/og/codes/<key>.png.
A code without a brief keeps the SVG text card drawn by ``omai.code_pages``; without Chrome every card
stays as it is. The PNGs are a release artifact: their bytes depend on the browser build and fonts,
the HTML does not.

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
POSTERS = DOCS / "assets" / "infographics"
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
    from PIL import Image

    done = []
    POSTERS.mkdir(parents=True, exist_ok=True)
    CARDS.mkdir(parents=True, exist_ok=True)
    for key in keys:
        if not (DOCS / "codes" / key / "infographic" / "index.html").exists():
            continue
        poster = POSTERS / f"{key}.png"
        # headless Chrome leaves the bottom 88 px of the window outside the viewport: render taller, crop to 1920 x 1080
        subprocess.run(
            [CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--window-size=1920,1168",
             "--virtual-time-budget=10000", f"--screenshot={poster}", f"http://127.0.0.1:{port}/codes/{key}/infographic/"],
            check=True, capture_output=True,
        )
        dom = subprocess.run(
            [CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--window-size=1920,1168", "--virtual-time-budget=10000",
             "--dump-dom", f"http://127.0.0.1:{port}/codes/{key}/infographic/"],
            check=True, capture_output=True, text=True,
        ).stdout
        if 'data-overflow="1"' in dom:
            raise SystemExit(f"{key}: the poster text overflows even at 80% scale; shorten the brief")
        with Image.open(poster) as im:
            im.convert("RGB").crop((0, 0, 1920, 1080)).save(poster, optimize=True)
        card = CARDS / f"{key}.png"
        subprocess.run(
            [CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--window-size=1200,718",
             "--virtual-time-budget=10000", f"--screenshot={card}", f"http://127.0.0.1:{port}/codes/{key}/infographic/card.html"],
            check=True, capture_output=True,
        )
        with Image.open(card) as im:
            im.convert("RGB").crop((0, 0, 1200, 630)).save(card, optimize=True)
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
    print(f"{len(done)} posters under {POSTERS.relative_to(ROOT)}, cards under {CARDS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
