"""The site Worker serves the static site untouched and adds only the named
dynamic routes.

infra/site is the edge deployment of the SAME docs/ every browser reads:
wrangler serves docs/ as assets and the Worker script runs only for
/l/<id> (the short-link resolver; /i/<id>/ is the canonical page) and
/healthz. These tests pin the
contract statically and, where node is available, run the Worker's pure
resolver logic against the real committed projection.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SITE = _REPO / "infra" / "site"


def _wrangler_config() -> dict:
    raw = (_SITE / "wrangler.jsonc").read_text()
    return json.loads(re.sub(r"^\s*//.*$", "", raw, flags=re.M))


def test_worker_is_additive_over_the_static_site():
    cfg = _wrangler_config()
    assert cfg["assets"]["directory"] == "../../docs", \
        "the Worker must serve the SAME docs/ the static site publishes"
    assert set(cfg["assets"]["run_worker_first"]) == {"/l/*", "/s", "/s/*", "/badge/*", "/healthz"}, \
        "only the named dynamic routes may bypass the assets"
    assert cfg["name"] == "openmaterials-site"


def test_worker_routes_on_the_domain_match_the_dynamic_paths():
    """On openmaterials.ai the Worker is routed for exactly the paths it runs
    first; everything else stays with the static host."""
    cfg = _wrangler_config()
    routes = {(r["pattern"], r["zone_name"]) for r in cfg["routes"]}
    assert routes == {("openmaterials.ai" + p, "openmaterials.ai") for p in cfg["assets"]["run_worker_first"]}


def test_worker_script_falls_through_to_assets():
    src = (_SITE / "src" / "index.js").read_text()
    assert "env.ASSETS.fetch(request)" in src, "no static fallthrough"
    assert "instances.json" in src and "version.json" in src
    for marker in ("API_KEY", "Bearer ", "Authorization"):
        assert marker not in src, f"the site Worker must hold no credentials ({marker})"


def test_resolver_logic_under_node():
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available; resolver checked where present")
    proc = subprocess.run(
        [node, "--test", str(_SITE / "src" / "resolve.test.mjs")],
        capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_short_link_store_contract():
    """The /s short-link store (the one write surface): worker-first routes,
    the KV binding, origin-gated minting, open-CORS immutable raw reads, and
    the playground's #s= route all pinned; the pure logic runs under node
    against the real validation and shell builders."""
    cfg = _wrangler_config()
    assert "/s" in cfg["assets"]["run_worker_first"]
    assert "/s/*" in cfg["assets"]["run_worker_first"]
    assert any(k["binding"] == "SHORTLINKS" for k in cfg.get("kv_namespaces", [])), \
        "no KV namespace bound for the short-link store"

    src = (_SITE / "src" / "index.js").read_text()
    assert "isMintOrigin" in src, "minting must be origin-gated"
    assert "MINTS_PER_DAY" in src, "minting must be rate-limited"
    assert "access-control-allow-origin\": \"*\"" in src or "'access-control-allow-origin': '*'" in src.replace('"', "'"), \
        "raw reads must carry open CORS (a minted payload is public)"
    assert "immutable" in src, "stored payloads never change; raw reads must say so"

    play = (_REPO / "docs" / "play" / "index.html").read_text()
    assert "fetchShortlink" in play and "#s=" in play.replace("\\", ""), \
        "the playground must resolve #s= through the short-link store"
    assert "mintShortlink" in play and "bundleShort" in play, \
        "the bundle view must offer Copy short link"
    assert "public to anyone with the code" in play, \
        "the mint control must state the public-by-construction rule"

    node = shutil.which("node")
    if not node:
        pytest.skip("node not available; short-link logic checked where present")
    proc = subprocess.run(
        [node, "--test", str(_SITE / "src" / "shortlinks.test.mjs")],
        capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_source_first_identifier_routes():
    """The paper goes first in the URL: /l/<scheme:ref> lists the source's
    committed family, /l/<scheme:ref>/<hash> names one value gated by the
    in-hash source (a speaking identifier that cannot lie), and the play badge
    shows the source chip. Pinned here; the logic runs under node."""
    src = (_SITE / "src" / "index.js").read_text()
    assert "parseLPath" in src and "sourceMismatchHTML" in src, "no source routes"
    assert "409" in src, "a mismatched namespace must refuse, never redirect silently"
    play = (_REPO / "docs" / "play" / "index.html").read_text()
    assert "rec-doi-src" in play, "the badge does not show the source namespace chip"
    resolve = (_SITE / "src" / "resolve.js").read_text()
    assert "SOURCE_REF_RE" in resolve and "canonical" in resolve


# The /l/<id> Worker page and the static /i/<id>/ stub must name a value with
# the same bytes; numbers print as the datasheet's fmtSig on both.
_WORKER_PAGES = r"""
import { readFileSync } from "node:fs";
import { permalinkHTML } from __RESOLVE__;
const entries = JSON.parse(readFileSync(__ENTRIES__, "utf8"));
console.log(JSON.stringify({
  pages: Object.fromEntries(entries.map((e) => [e.id, permalinkHTML(e, "https://openmaterials.ai")])),
  numbers: __NUMBERS__.map((v) => String(Number(v.toPrecision(6)))),
}));
"""
_SHARED = re.compile(r'^(?:<title>.*|<meta (?:property="og:|name="twitter:).*|'
                     r'<link rel="canonical".*|<p>[^<]*</p>)$', re.M)
# toPrecision(6) edges: exact ties (away from zero, both signs), carries,
# exponent switches at 1e21 and 1e-7, the double range ends, plain floats.
_NUMBERS = [0.0, -0.0, 6.0, 156, 0.027, -1.057843414e-05, 3.33222233511797e-10,
            1234565, -1234565, 1000005, 999999.5, -999999.5, 0.1 + 0.2, 1 / 3,
            -2 / 3, 1e-06, 1e-07, 1.5e-07, 1e20, 1e21, 1.2345678e21, 5e-324,
            1.7976931348623157e308, 123456.789e3]


def test_value_page_matches_the_share_stub(tmp_path):
    """Every committed value plus crafted ones (escaping, an apostrophe, and a
    bare record that takes every fallback): same title, OG and card tags, and
    paragraph on /l/<id> (Worker) and /i/<id>/ (static stub); numbers print as
    the datasheet's fmtSig."""
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available; the Worker page is checked where present")
    from omai.map_data import _card_number, build_share_stubs
    entries = json.loads((_REPO / "docs" / "data" / "instances.json").read_text())
    entries += [
        {"id": "a" * 64, "variable": "BandGap", "material": 'A & B "x" <y> \'z\'',
         "conditions": {}, "value": 1.1, "units": "eV", "uncertainty": None,
         "source": {"kind": "simulation", "ref": "code&<>"}, "node_uid": "z" * 64},
        {"id": "b" * 64, "source": {}},
    ]
    path = tmp_path / "entries.json"
    path.write_text(json.dumps(entries))
    script = (_WORKER_PAGES
              .replace("__RESOLVE__", json.dumps((_SITE / "src" / "resolve.js").as_uri()))
              .replace("__ENTRIES__", json.dumps(str(path)))
              .replace("__NUMBERS__", json.dumps(_NUMBERS)))
    proc = subprocess.run([node, "--input-type=module", "-e", script],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["numbers"] == [_card_number(v) for v in _NUMBERS]
    stubs = build_share_stubs(entries)
    for e in entries:
        stub = _SHARED.findall(stubs[e["id"]])
        worker = _SHARED.findall(out["pages"][e["id"]])
        assert stub and stub == worker, e["id"][:12]
