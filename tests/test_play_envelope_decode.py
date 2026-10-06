"""The playground's envelope decode agrees with the python reference.

The page's dual read (docs/play/index.html: b64urlToObj + normalizeEnvelope)
and omai/lineages.py envelope_from_fragment must speak the same wire: a
python-minted multi-lineage bundle fragment decodes on the page to the same
member count, ids, and doc source, and a legacy single-record fragment still
decodes (normalized to a one-element envelope), forever.

Follows the test_run_url_configuration_param.py technique: extract the page's
top-level functions by brace matching and run them under Node against real
fragments minted by the python reference. Skipped cleanly when Node (or its
DecompressionStream, needed for the gzip fragment) is unavailable; a static
wiring check guards the feature regardless.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from omai import lineages as lin

_REPO = Path(__file__).resolve().parents[1]
_PLAY = _REPO / "docs" / "play" / "index.html"


def _grab_function(html: str, name: str) -> str:
    """Extract a top-level `function name(...) { ... }` body by brace matching."""
    m = re.search(r"(?:async )?function %s\s*\([^)]*\)\s*\{" % re.escape(name), html)
    assert m, f"could not find function {name}"
    i, depth = m.end(), 1
    while i < len(html) and depth:
        c = html[i]
        depth += c == "{"
        depth -= c == "}"
        i += 1
    return html[m.start():i]


# The page's decode path, in dependency order: fragment bytes -> object ->
# normalized envelope. normalizeLineageRecord is normalizeEnvelope's helper.
_DECODE_HELPERS = ("bytesFromB64url", "b64urlToObj",
                   "normalizeLineageRecord", "normalizeEnvelope")


def _node_or_skip() -> str:
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available; decode agreement checked where present")
    probe = subprocess.run(
        [node, "-e", "console.log(typeof DecompressionStream)"],
        capture_output=True, text=True)
    if probe.returncode != 0 or "function" not in probe.stdout:
        pytest.skip("node lacks DecompressionStream (gzip fragments need it)")
    return node


def _decode_on_page(fragment: str) -> dict:
    """Run the page's real decode+normalize under Node on a fragment, returning
    {count, ids, doc_source}."""
    node = _node_or_skip()
    html = _PLAY.read_text()
    src = "\n".join(_grab_function(html, n) for n in _DECODE_HELPERS)
    script = src + """
(async function(){
  var payload = await b64urlToObj(%s);
  var env = normalizeEnvelope(payload);
  console.log(JSON.stringify({
    count: env.lineages.length,
    ids: env.lineages.map(function(m){ return m.id || null; }),
    doc_source: env.doc && env.doc.source || null
  }));
})().catch(function(e){ console.error(e); process.exit(1); });
""" % json.dumps(fragment)
    proc = subprocess.run([node, "-e", script], capture_output=True, text=True)
    assert proc.returncode == 0, f"node failed: {proc.stderr}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


# The page's #id= resolver, in dependency order: a flat instances.json entry ->
# the record shape (instanceToRecord), then the pure hash lookup over the
# projection (resolveInstanceById). Both are DOM-free and gzip-free, so a plain
# Node runs them; SHA256_RE is a page global the resolver references, supplied
# in the harness preamble exactly as the page hoists it.
_RESOLVE_HELPERS = ("instanceToRecord", "resolveInstanceById")


def _node_plain_or_skip() -> str:
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available; resolver agreement checked where present")
    return node


def _resolve_on_page(hash_: str, instances: list) -> dict:
    """Run the page's real #id= resolver under Node against a projection,
    returning the resolver result {ok, reason?, record?}."""
    node = _node_plain_or_skip()
    html = _PLAY.read_text()
    src = "var SHA256_RE = /^[0-9a-f]{64}$/;\n" + \
        "\n".join(_grab_function(html, n) for n in _RESOLVE_HELPERS)
    script = src + """
var res = resolveInstanceById(%s, %s);
console.log(JSON.stringify(res));
""" % (json.dumps(hash_), json.dumps(instances))
    proc = subprocess.run([node, "-e", script], capture_output=True, text=True)
    assert proc.returncode == 0, f"node failed: {proc.stderr}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


def _member(node_id, mat, val):
    lineage = {"node": node_id, "material": {"name": mat},
               "conditions": {"T": 300.0},
               "values": {"value": val, "units": "W/(m K)"}}
    return {"id": lin.lineage_id(lineage), "lineage": lineage}


# --------------------------------------------------------------------------
# Static wiring: the page speaks the envelope even where Node is unavailable.
# --------------------------------------------------------------------------

def test_page_wires_the_envelope_dispatch():
    html = _PLAY.read_text()
    assert "function normalizeEnvelope" in html, "no envelope normalizer on the page"
    assert "renderShared(payload)" in html, "the #x= decode does not dispatch through renderShared"
    assert "function renderBundle" in html, "no bundle (paper) view on the page"
    assert "from the shared document" in html, "no read-time source inheritance label"
    assert "showLengthFallback" in html and "8000" in html, "no length rule"
    assert "Download it as JSON" in html, "no JSON download fallback"


def test_bundle_stacks_every_datasheet_on_one_page():
    """A bundle shows every member's FULL datasheet on the same page (the
    same-page rule), built by the one shared datasheetHTML so the single and
    stacked views can never drift."""
    html = _PLAY.read_text()
    assert "function datasheetHTML" in html, "no shared datasheet builder"
    assert 'class="rec bundle-member"' in html, "bundle does not stack member datasheets"
    assert "datasheetHTML(mvalid.record, mvalid" in html, \
        "the stacked members do not reuse the shared builder"
    assert "scrollIntoView" in html, "member rows must jump on-page, not re-render"


def test_datasheet_hands_the_derivation_to_the_tracer():
    """The derivation drawing never fit the sheet (2026-10-04): the sheet links
    the tracer, which draws the same derivation at any width."""
    html = _PLAY.read_text()
    assert "function derivationSVG" not in html and "rec-map" not in html
    assert "Trace this derivation" in html
    assert "../map-trace/#node=' + encodeURIComponent(node)" in html


def test_datasheet_reproduce_section_names_codes_and_pinned_runs():
    """A known-node datasheet must say how to reproduce the result: the codes
    that compute the quantity (codes.json coverage) and the conformance target
    that pins this exact lineage (its id equals the record's, so its
    conditions match the value), at 4 significant figures."""
    html = _PLAY.read_text()
    assert "function reproduceHTML" in html, "no reproduce section builder"
    assert "data/codes.json" in html, "the page does not load code coverage"
    assert "data/conformance/index.json" in html, "the page does not load the conformance index"
    assert "t.id === recordId" in html, "targets must match the record's own lineage"
    assert "toPrecision(4)" in html and "Open the target file" not in html
    assert "reproduceHTML(node, record.id, (evidenceReasons(record)" in html, "the datasheet does not wire the section"
    # the index the page reads is committed and non-empty
    idx = json.loads((_REPO / "docs" / "data" / "conformance" / "index.json").read_text())
    assert idx.get("targets"), "committed conformance index is empty"


# --------------------------------------------------------------------------
# Behavior, pinned to the python reference under Node.
# --------------------------------------------------------------------------

def test_python_minted_bundle_decodes_to_member_count_n():
    members = [_member("ThermalConductivity", "Si", 148.0),
               _member("ThermalConductivity", "Ge", 62.0),
               _member("BulkModulus", "Si", 97.8)]
    doc = {"source": "doi:10.1103/PhysRevLett.127.025902", "title": "Demo"}
    frag = lin.envelope_to_fragment(lin.envelope(members, doc=doc))
    got = _decode_on_page(frag)
    ref = lin.envelope_from_fragment(frag)
    assert got["count"] == len(ref["lineages"]) == 3
    assert got["ids"] == [m["id"] for m in ref["lineages"]]
    assert got["doc_source"] == ref["doc"]["source"]


def test_legacy_single_record_fragment_still_renders():
    record = _member("ThermalConductivity", "Si", 148.0)
    frag = lin.record_to_fragment(record)          # a link minted before bundles
    got = _decode_on_page(frag)
    ref = lin.envelope_from_fragment(frag)
    assert got["count"] == len(ref["lineages"]) == 1
    assert got["ids"] == [record["id"]]
    assert got["doc_source"] is None and "doc" not in ref


# --------------------------------------------------------------------------
# #id=<hash>: the canonical lineage id is the share link.
#
# The projection now carries each value's canonical id (omai/map_data.py
# build_instances), and the page resolves #id=<64-hex> against that same
# instances.json the site serves, opening the value through the single-datasheet
# path. These pin the resolver's wire the way the block above pins the envelope
# decode: the page's real JS, driven under Node against the python reference.
# --------------------------------------------------------------------------

def test_projection_carries_the_canonical_id_as_the_share_handle():
    """The share handle is the value's own identity: build_instances projects
    the canonical lineage id onto every flat entry, unique per value (unlike
    node_uid, which names a map node and repeats across its values), and equal to
    lineage_id of that entry's reconstructed lineage."""
    from omai.map_data import build_instances

    insts = build_instances()
    assert insts, "no instances projected"
    ids = [e["id"] for e in insts]
    assert all(re.fullmatch(r"[0-9a-f]{64}", i) for i in ids), "an id is not 64-hex"
    assert len(set(ids)) == len(ids), "canonical ids must be unique per value"
    # the id addresses the value, not its node: node_uid is strictly coarser
    assert len(set(e["node_uid"] for e in insts)) < len(ids), \
        "node_uid should repeat across values; the lineage id must not"


def test_page_wires_the_id_permalink_resolver():
    html = _PLAY.read_text()
    assert "function resolveInstanceById" in html, "no #id= resolver on the page"
    assert "function instanceToRecord" in html, "no instance->record normalizer"
    assert "id=([0-9a-fA-F]+)" in html, "the router does not match the #id= fragment"
    assert "renderInstanceById" in html, "the #id= route is not dispatched"
    assert "fetch('../data/instances.json')" in html, \
        "the resolver does not fetch the projection the site serves"
    # not-found is a plain empty state, never a fabricated value
    assert "function renderInstanceEmpty" in html, "no empty state for an unresolved id"
    assert "No shared value with this id" in html, "no plain not-found heading"
    assert "so no value can open" in html and "The link may be stale" in html, \
        "the empty state must say why the id does not resolve"


def test_valid_hash_resolves_the_right_instance():
    """A committed value's canonical id resolves, on the page, to that exact
    value: same node, material, and headline value, reconstructed into the light
    record shape the datasheet renderer speaks."""
    from omai.map_data import build_instances

    insts = build_instances()
    entry = next(e for e in insts if e["source"]["ref"].startswith("paper:"))
    got = _resolve_on_page(entry["id"], insts)
    assert got["ok"] is True, got
    rec = got["record"]
    assert rec["id"] == entry["id"]
    assert rec["lineage"]["node"] == entry["variable"]
    assert rec["lineage"]["material"] == entry["material"]
    assert rec["lineage"]["values"]["value"] == entry["value"]
    assert rec["lineage"]["values"]["units"] == entry["units"]
    assert rec["kind"] == entry["source"]["kind"]
    # a scheme:ref source rides inside the lineage (identity-bearing), as it does
    # in the python instance record; the verbatim block stays on record.source
    assert rec["lineage"]["source"] == entry["source"]["ref"]
    assert rec["source"]["ref"] == entry["source"]["ref"]


def test_unknown_hash_renders_the_empty_state():
    """A well-formed hash that names no committed value resolves to the plain
    not-found signal (never a fabricated record)."""
    from omai.map_data import build_instances

    insts = build_instances()
    absent = "0" * 64                       # 64-hex, but not a committed id
    assert absent not in {e["id"] for e in insts}
    got = _resolve_on_page(absent, insts)
    assert got["ok"] is False and got["reason"] == "not-found", got
    assert "record" not in got or got.get("record") is None


def test_malformed_hash_is_rejected():
    """A hash that is neither a full sha256 nor a legal 8+ hex prefix is
    rejected outright: not fetched, not resolved, not fabricated."""
    from omai.map_data import build_instances

    insts = build_instances()
    for bad in ("", "xyz", "g" * 64, "abc123", "0" * 65, "1234567"):
        got = _resolve_on_page(bad, insts)
        assert got["ok"] is False and got["reason"] == "malformed", (bad, got)


def test_prefix_resolves_git_style():
    """The DOI-like short form: a unique 8+ hex prefix resolves to its one
    committed value; a matching-nothing prefix is not-found; an ambiguous
    prefix refuses and names the candidates."""
    from omai.map_data import build_instances

    insts = build_instances()
    full = insts[0]["id"]
    for prefix in (full[:12], full[:8], full[:63]):
        got = _resolve_on_page(prefix, insts)
        assert got["ok"] is True, (prefix, got)
        assert got["record"]["id"] == full
    ghost = _resolve_on_page("0" * 63, insts)
    assert ghost["ok"] is False and ghost["reason"] == "not-found"
    # a shared prefix among ids (when one exists) must refuse, never guess
    shared = [
        (a["id"], b["id"]) for i, a in enumerate(insts) for b in insts[i + 1:]
        if a["id"][:8] == b["id"][:8]
    ]
    if shared:
        got = _resolve_on_page(shared[0][0][:8], insts)
        assert got["ok"] is False and got["reason"] == "ambiguous"


def test_datasheet_shows_the_lineage_badge():
    """Every datasheet carries one id (12 hex) with one Copy link: a committed
    value copies its /l/ short link, any other record a link that carries it
    in #x=; a stored set shows its /s/ code."""
    html = _PLAY.read_text()
    assert "function lineageDoiHTML" in html, "no badge builder"
    assert "lineageDoiHTML(record, opts.memberIdx, trace)" in html, \
        "the datasheet header does not show the badge"
    assert "function bundleDoiHTML" in html and "bundleDoi" in html, "no bundle short-link badge"
    assert "var link = 'openmaterials.ai/l/' + short" in html, "the short link is not built"
    assert "data-copy=\"https://' + link + '\"" in html, "the copy button must copy the short link"
    assert "Copy permalink" not in html and "Permalink" not in html, "one id, one Copy link"
    assert "(uncommitted)" in html, "no plain uncommitted state"
    assert "INSTANCE_IDS" in html, "committed test set missing"


# --------------------------------------------------------------------------
# A member citing evidence outside the public registry carries its label on
# every path; #x= is pinned here with the page's real decode and label code
# over the real predicate module and the published registry.
# --------------------------------------------------------------------------

_LABEL = ("Lineage 2 cites a model that is not in the public registry; "
          "its values cannot be checked against the commons.")


def _labels_on_page(fragment: str, registry) -> list:
    node = _node_or_skip()
    html = _PLAY.read_text()
    src = "var PRIVACY = null;\n" + "\n".join(
        _grab_function(html, n) for n in _DECODE_HELPERS + ("evidenceReasons", "evidenceLabel"))
    script = src + """
(async function(){
  var registry = %s;
  if (registry) PRIVACY = { mod: await import(%s), registry: registry };
  var env = normalizeEnvelope(await b64urlToObj(%s));
  console.log(JSON.stringify(env.lineages.map(function(m, i){ return evidenceLabel(m, i + 1); })));
})().catch(function(e){ console.error(e); process.exit(1); });
""" % (json.dumps(registry), json.dumps((_REPO / "docs" / "assets" / "private-members.js").as_uri()),
       json.dumps(fragment))
    proc = subprocess.run([node, "-e", script], capture_output=True, text=True)
    assert proc.returncode == 0, f"node failed: {proc.stderr}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_x_link_labels_the_member_citing_unregistered_evidence():
    marked = dict(_member("ThermalConductivity", "Ge", 62.0),
                  unregistered=[{"kind": "model", "uid": "2" * 64}])
    frag = lin.envelope_to_fragment(lin.envelope(
        [_member("ThermalConductivity", "Si", 148.0), marked]))
    registry = json.loads((_REPO / "docs" / "data" / "registry.json").read_text())
    assert _labels_on_page(frag, registry) == ["", _LABEL]
    # fail closed, no crash: an unread registry, or one whose citation_keys is
    # not the module's bound table, labels every lineage
    unbound = dict(registry, citation_keys={})
    for reg in (None, unbound):
        assert all("could not be read" in label for label in _labels_on_page(frag, reg))


def test_page_wires_the_label_reproduce_note_and_mint_opt_in():
    html = _PLAY.read_text()
    assert "import('../assets/private-members.js')" in html, "the predicate is not loaded"
    assert "fetch('../data/registry.json')" in html
    assert "var evidence = evidenceLabel(record, n);" in html, "the datasheet does not label"
    assert "cites evidence that is not public, so it cannot be rerun" in html
    assert "'?publish_private=1'" in html and "Publish anyway" in html
    assert "where anyone with the code can read it" in html, "the opt-in must state what becomes public"
    assert "if (body) refusal = body;" in html, "a Worker's JSON answer must stop the fallback retry"
    assert "(body && body.error) ||" in html, "the server's answer must be shown"
    assert "(evidenceReasons(record) || []).length &&" in html, "the Reproduce note follows reasons, not the label"
