"""Build docs/codes/<key>/index.html, one landing page per code on the map.

Every page is generated, never hand edited. Inputs, all under docs/data:

- ``codes.json``: what the code computes (its map representation), citation, DOI, license, URL;
- ``registry.json``: releases and visibility (a private code gets no public page);
- ``references/<key>.json``: the curated papers (the code, methods, applications), exported from Zotero
  by ``omai.refs_export``; without a file the page falls back to the citations in codes.json;
- ``code_pages.json``: the hand-written summary, tagline and links; a key without a summary gets a
  sentence derived from its representation, never invented prose;
- ``briefs/<key>.json``: the brief behind the infographic and the detail sections (``omai.briefs``);
- ``graph.json``: the map itself, for the code's submap (``omai.submap``).

The page opens with the infographic drawn from the brief, then the summary, the detail sections, the
submap with the quantities served, the releases, the references and the citation line. Each code also
gets a poster page at ``codes/<key>/infographic/`` (the same infographic on a 1920 x 1080 canvas, not
indexed) that ``omai.code_cards`` screenshots into the LinkedIn poster and the 1200 x 630 social card
when Chrome is available; without Chrome a text card drawn as SVG and rasterized with ImageMagick stays.
The PNGs are a release artifact whose bytes depend on the build machine, the HTML does not.

Run as::

    PYTHONPATH=. python -m omai.code_pages

The build is deterministic: the output depends only on the data files and this module.
"""

from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
from pathlib import Path

from omai import briefs, infographic, snapshots, submap

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"
OUT = ROOT / "docs" / "codes"
CARDS = ROOT / "docs" / "assets" / "og" / "codes"
POSTERS = ROOT / "docs" / "assets" / "infographics"
SITE = "https://openmaterials.ai"
GROUPS = {
    "code": ("The code", "The papers that describe the code; cite them when you use it."),
    "methods": ("Methods and inputs it builds on", "The methods the code implements and the inputs it relies on, as published."),
    "applications": ("Applications", "Highly cited studies that cite the code, with a few picked by hand."),
}
KEY = re.compile(r"[a-z0-9][a-z0-9.-]*")


def quantities(n: int) -> str:
    return f"{n} quantit{'y' if n == 1 else 'ies'}"


def esc(s: object) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def display_name(key: str, rep: dict) -> str:
    return next((e.get("name") for e in rep.values() if e.get("name")), key)


def node_groups(rep: dict) -> list[dict]:
    """Nodes grouped by citation, largest group first, so the primary citation is the one serving most quantities."""
    groups: dict[tuple, dict] = {}
    for node, e in sorted(rep.items()):
        k = ((e.get("citation") or "").strip(), (e.get("doi") or "").strip())
        g = groups.setdefault(k, {"citation": k[0], "doi": k[1], "nodes": []})
        g["nodes"].append(node)
    out = sorted(groups.values(), key=lambda g: (-len(g["nodes"]), g["citation"]))
    return out


def ref_line(r: dict) -> str:
    authors = r.get("authors") or []
    shown = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
    bits = [esc(shown)] if shown else []
    bits.append("<cite>" + esc(r["title"]) + "</cite>")
    tail = ", ".join(x for x in (r.get("journal"), str(r["year"]) if r.get("year") else "") if x)
    if tail:
        bits.append(esc(tail))
    doi = r.get("doi")
    link = f' <a href="https://doi.org/{esc(doi)}" rel="noopener">doi.org/{esc(doi)}</a>' if doi else ""
    return "<li>" + ", ".join(bits) + "." + link + "</li>"


def card_svg(name: str, tagline: str, n_nodes: int) -> str:
    # 1200 x 630, the site's paper tone; long names shrink so they stay on one line
    size = 112 if len(name) <= 12 else 84 if len(name) <= 20 else 60
    tag_size = 34 if len(tagline) <= 48 else 28 if len(tagline) <= 60 else 22
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">'
        '<rect width="1200" height="630" fill="#F4F1EA"/>'
        '<text x="80" y="120" font-family="DejaVu Sans, sans-serif" font-size="28" fill="#4D4D4D">openmaterials.ai / codes</text>'
        f'<text x="80" y="330" font-family="DejaVu Serif, serif" font-size="{size}" fill="#171717">{esc(name)}</text>'
        f'<text x="80" y="410" font-family="DejaVu Sans, sans-serif" font-size="{tag_size}" fill="#4D4D4D">{esc(tagline)}</text>'
        f'<text x="80" y="540" font-family="DejaVu Sans Mono, monospace" font-size="28" fill="#4D4D4D">'
        f'{quantities(n_nodes)} on the map</text></svg>\n'
    )


def rasterize(svg_path: Path, png_path: Path) -> None:
    conv = shutil.which("convert")
    if conv:
        subprocess.run([conv, str(svg_path), "-define", "png:exclude-chunks=date,time", str(png_path)], check=True)


def page(key: str, rep: dict, reg: dict, refs: dict | None, text: dict, has_card: bool, brief: dict | None = None,
         graph: dict | None = None, has_poster: bool = False, share: str = "") -> str:
    name = display_name(key, rep)
    nodes = sorted(rep)
    tagline = text.get("tagline") or f"{quantities(len(nodes))} on the OpenMaterials map."
    summary = text.get("summary") or (
        f"{name} has a representation on the OpenMaterials map: a record of the quantities it computes, "
        f"through which interface, with a citation and its license. It serves {quantities(len(nodes))}, listed below."
    )
    groups = node_groups(rep)
    primary = next((g for g in groups if g["citation"]), None)
    url = next((e.get("url") for e in rep.values() if e.get("url")), "")
    license_ = next((e.get("license") for e in rep.values() if e.get("license")), "")
    releases = sorted(reg.get("releases") or [], key=lambda r: r.get("released") or "", reverse=True)
    canonical = f"{SITE}/codes/{key}/"
    embed_abs = f"{share}?embed=1" if share else f"{SITE}/map/?embed=1#code={key}"
    snippet = f'<iframe src="{embed_abs}" title="{name} on the OpenMaterials map" width="100%" height="480" loading="lazy" style="border:1px solid #EBEBEB;border-radius:6px"></iframe>'
    og_image = f"{SITE}/assets/og/codes/{key}.png" if has_card else f"{SITE}/assets/og.png"
    description = tagline if tagline.endswith(".") else tagline + "."

    def http(u: str | None) -> str:
        return u if u and u.startswith(("https://", "http://")) else ""

    links = []
    if http(text.get("website")):
        links.append(f'<a href="{esc(text["website"])}" rel="noopener">Website</a>')
    if http(text.get("docs")):
        links.append(f'<a href="{esc(text["docs"])}" rel="noopener">Documentation</a>')
    if http(url) and url != text.get("website"):
        links.append(f'<a href="{esc(url)}" rel="noopener">Repository</a>')
    links.append(f'<a href="../../map/#code={esc(key)}">On the map</a>')
    links.append('<a href="../">All codes</a>')

    info_html = ""
    if brief:
        own = infographic.self_reported(brief, refs)
        poster_links = '<a href="infographic/">Poster page</a>' + (f'<a href="../../assets/infographics/{esc(key)}.png" download>Download the poster (PNG, 1920 x 1080)</a>' if has_poster else "")
        info_html = (
            f'<figure class="gsec info-figure" id="infographic">{infographic.block(brief, name, key, self_reported=own)}'
            f'<figcaption><span>What {esc(name)} is, how it works and what it is used for, from the papers listed as sources. Every number links to its paper.</span>{poster_links}</figcaption></figure>'
        )
    detail_html = ""
    if brief and brief.get("detail"):
        detail_html = '<section class="gsec" id="detail"><h2>In more detail</h2>' + "".join(
            f'<h3>{esc(d["heading"])}</h3><p>{esc(d["text"])}</p>' for d in brief["detail"]
        ) + "</section>"
    submap_html = submap.svg(graph, set(nodes), fit_under=760) if graph else ""

    served = "".join(
        f'<li><a href="../../map/#node={esc(n)}"><span class="bib-node">{esc(n)}</span></a>'
        + (f'<span class="bib-api">{esc(rep[n]["api"])}</span>' if rep[n].get("api") else "")
        + (f'<span class="bib-unit">{esc(rep[n]["unit"])}</span>' if rep[n].get("unit") else "")
        + "</li>"
        for n in nodes
    )

    rel_html = ""
    if releases:
        rows = "".join(
            f'<tr><td>{esc(r.get("version") or r.get("tag"))}</td><td>{esc(r.get("released") or "")}</td><td>{esc(r.get("spdx") or "")}</td></tr>'
            for r in releases
        )
        rel_html = (
            '<section class="gsec" id="releases"><h2>Releases on record</h2>'
            "<p>Versions on record for this code, with the license read from the release itself.</p>"
            f'<table class="releases"><thead><tr><th>Version</th><th>Released</th><th>License</th></tr></thead><tbody>{rows}</tbody></table></section>'
        )

    ref_sections = ""
    if refs and any(refs.get(g) for g in GROUPS):
        for g, (title, lead) in GROUPS.items():
            items = refs.get(g) or []
            if items:
                ref_sections += f'<h3 id="refs-{g}">{title}</h3><p>{lead}</p><ol class="refs">{"".join(ref_line(r) for r in items)}</ol>'
            elif g == "applications":
                ref_sections += f'<h3 id="refs-{g}">{title}</h3><p>No independent study using {esc(name)} is on record here yet. The list fills in when one is verified.</p>'
    else:
        ref_sections += "<p>No curated reference list yet. The citations recorded on the map representation are listed under How to cite.</p>"

    cite_html = ""
    if primary:
        cite_html = f'<p class="bib-cite">{esc(primary["citation"])}</p>'
        if primary["doi"]:
            cite_html += f'<p><a href="https://doi.org/{esc(primary["doi"])}" rel="noopener">doi.org/{esc(primary["doi"])}</a></p>'
        for g in groups[1:]:
            if g["citation"]:
                cite_html += (
                    f'<p class="bib-cite bib-cite-more"><span class="bib-cite-for">for {esc(", ".join(g["nodes"]))}:</span> {esc(g["citation"])}'
                    + (f' <a href="https://doi.org/{esc(g["doi"])}" rel="noopener">doi.org/{esc(g["doi"])}</a>' if g["doi"] else "")
                    + "</p>"
                )
    else:
        cite_html = '<p class="empty">No citation recorded on the map representation.</p>'

    toc = ([("infographic", "At a glance")] if info_html else []) + [("about", f"What {name} is")]
    if detail_html:
        toc.append(("detail", "In more detail"))
    toc.append(("serves", "On the map"))
    if rel_html:
        toc.append(("releases", "Releases"))
    toc += [("references", "References"), ("cite", "How to cite")]
    toc_html = "".join(f'<a href="#{a}">{esc(t)}</a>' for a, t in toc)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(name)} | OpenMaterials</title>
<meta name="description" content="{esc(description)} {esc(name)} on the OpenMaterials map: the quantities it computes, the papers that describe it, and studies that cite it.">
<link rel="canonical" href="{canonical}">
<meta name="theme-color" content="#F4F1EA" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0F0E0C" media="(prefers-color-scheme: dark)">
<link rel="icon" href="../../assets/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="../../assets/apple-touch-icon.png">
<meta property="og:type" content="article">
<meta property="og:site_name" content="openmaterials.ai">
<meta property="og:title" content="{esc(name)} | OpenMaterials">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{og_image}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{esc(name)}: {esc(description)} {quantities(len(nodes))} on the OpenMaterials map.">
<meta name="twitter:card" content="summary_large_image">
<script>try{{const t=localStorage.getItem('theme');if(t==='light'||t==='dark')document.documentElement.dataset.theme=t}}catch{{}}</script>
<link rel="preload" href="../../assets/fonts/newsreader-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="../../assets/fonts/jetbrains-mono-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="../../assets/site.css">
<style>
{{EXTRA_CSS}}
  /* a code's landing page: the infographic first, then the record (generated by omai/code_pages.py) */
  .info-figure {{ margin: 0 0 8px; }}
  .info-figure figcaption, .submap-figure figcaption {{ display: flex; flex-wrap: wrap; gap: 4px 16px; margin-top: 8px; font-size: 14px; line-height: 20px; color: var(--ink-2); }}
  .info-figure figcaption a, .submap-figure figcaption a {{ color: var(--ink); }}
  .submap-figure {{ margin: 16px 0 24px; }}
  .submap-figure details {{ flex-basis: 100%; margin-top: 4px; }}
  .submap-figure summary {{ cursor: pointer; }}
  .submap-figure pre {{ margin: 8px 0 0; padding: 12px; overflow-x: auto; border: 1px solid var(--line); border-radius: var(--radius, 6px); background: var(--surface); font: 400 12px/18px var(--font-mono); white-space: pre-wrap; overflow-wrap: anywhere; }}
  .code-links {{ display: flex; flex-wrap: wrap; gap: 4px 16px; font-size: 14px; line-height: 20px; }}
  .code-links a {{ color: var(--ink); }}
  .serves {{ display: grid; gap: 8px; margin: 12px 0 0; padding: 0; list-style: none; }}
  .serves li {{ max-width: none; }}
  .serves a {{ text-decoration: none; }}
  .bib-node {{ display: block; font: 400 13px/20px var(--font-mono); color: var(--ink); overflow-wrap: anywhere; }}
  .bib-api, .bib-unit {{ display: block; font: 400 12px/16px var(--font-mono); color: var(--ink-2); overflow-wrap: anywhere; }}
  .bib-cite {{ margin: 12px 0 8px; font-size: 14px; line-height: 20px; color: var(--ink-2); max-width: none; }}
  .bib-cite-for {{ font: 400 12px/20px var(--font-mono); color: var(--ink-2); }}
  .refs {{ padding-left: 20px; }}
  .refs li {{ margin: 8px 0; max-width: none; font-size: 14px; line-height: 20px; }}
  .refs cite {{ font-style: italic; }}
  .refs a {{ color: var(--ink); overflow-wrap: anywhere; }}
  table.releases {{ border-collapse: collapse; margin-top: 12px; font-size: 14px; line-height: 20px; }}
  table.releases th, table.releases td {{ padding: 6px 16px 6px 0; text-align: left; border-bottom: 1px solid var(--line); }}
  .empty {{ color: var(--ink-2); }}
</style>
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<div data-site-header></div>

<main class="frame" id="main">
  <header class="page-head">
    <p class="eyebrow">Code</p>
    <h1>{esc(name)}</h1>
    <p class="lede">{esc(tagline)}</p>
  </header>

  <div class="page-body">
    <nav class="toc gtoc" aria-label="Contents">{toc_html}</nav>

    <article class="prose gwrap">
      {info_html}

      <section class="gsec" id="about">
        <h2>What {esc(name)} is</h2>
        <p>{esc(summary)}</p>
        <p class="code-links">{"".join(links)}{f'<span>License: {esc(license_)}</span>' if license_ else ""}</p>
      </section>

      {detail_html}

      <section class="gsec" id="serves">
        <h2>What it computes on the map</h2>
        <p>{quantities(len(nodes))}, drawn by tier with the data flow between them. Dashed boxes are intermediate quantities. Select one for its formula and the other codes that compute it.</p>
        <figure class="submap-figure">
          <div class="submap">{submap_html}</div>
          <figcaption>
            <a href="../../map/#code={esc(key)}">Open the full map</a>{f'<a href="{esc(share)}">Share this submap</a>' if share else ""}
            <details><summary>Embed this submap</summary><pre>{esc(snippet)}</pre></details>
          </figcaption>
        </figure>
        <p>Each quantity with the interface the representation records.</p>
        <ul class="serves">{served}</ul>
      </section>

      {rel_html}

      <section class="gsec" id="references">
        <h2>References</h2>
        {ref_sections}
      </section>

      <section class="gsec" id="cite">
        <h2>How to cite</h2>
        {cite_html}
      </section>
    </article>
  </div>
</main>
<div data-site-footer></div>
<script src="../../assets/site.js"></script>
</body>
</html>
""".replace("{EXTRA_CSS}", (infographic.CSS if info_html else "") + submap.CSS)


def build(write_cards: bool = True) -> list[str]:
    codes = load("codes.json")
    registry = load("registry.json").get("code", {})
    texts = load("code_pages.json")
    graph = load("graph.json")
    latest = load("v/index.json")["latest"]
    snap = load(f"v/{latest}.json")
    built = []
    for key in sorted(codes):
        if not KEY.fullmatch(key):
            raise ValueError(f"code key {key!r} is not a safe path segment")
        reg = registry.get(key) or {}
        if reg.get("visibility") == "private":
            continue
        refs_path = DATA / "references" / f"{key}.json"
        refs = json.loads(refs_path.read_text(encoding="utf-8")) if refs_path.exists() else None
        text = texts.get(key) or {}
        rep = codes[key]
        if write_cards:
            CARDS.mkdir(parents=True, exist_ok=True)
            svg = CARDS / f"{key}.svg"
            svg.write_text(card_svg(display_name(key, rep), text.get("tagline") or f"{quantities(len(rep))} on the OpenMaterials map.", len(rep)), encoding="utf-8")
            rasterize(svg, CARDS / f"{key}.png")
        has_card = (CARDS / f"{key}.png").exists()
        has_poster = (POSTERS / f"{key}.png").exists()
        brief = briefs.load(key)
        if brief:
            problems = briefs.validate(brief, refs)
            if problems:
                raise ValueError(f"brief {key}: " + "; ".join(problems))
        out = OUT / key / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        share = f"{SITE}/m/{latest[:12]}/{snapshots.encode(snap, snap['codes'][key]['nodes'])}" if key in snap["codes"] else ""
        out.write_text(page(key, rep, reg, refs, text, has_card, brief, graph, has_poster, share), encoding="utf-8")
        poster = OUT / key / "infographic" / "index.html"
        if brief:
            poster.parent.mkdir(parents=True, exist_ok=True)
            own = infographic.self_reported(brief, refs)
            poster.write_text(infographic.poster_page(brief, display_name(key, rep), key, self_reported=own), encoding="utf-8")
            (poster.parent / "card.html").write_text(infographic.poster_page(brief, display_name(key, rep), key, mode="card"), encoding="utf-8")
        elif poster.exists():
            shutil.rmtree(poster.parent)
        built.append(key)
    for stale in OUT.iterdir():  # a key dropped from codes.json takes its page with it
        if stale.is_dir() and stale.name not in built:
            shutil.rmtree(stale)
    return built


def main() -> int:
    keys = build()
    print(f"{len(keys)} code pages under docs/codes/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
