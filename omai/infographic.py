"""The infographic drawn from a code's brief: an HTML block in the site's type and colors.

The same markup serves two layouts. On the code page it reflows with the article width and the
theme. On the poster page (docs/codes/<key>/infographic/) the ``poster`` class pins it to a
1920 x 1080 canvas that headless Chrome screenshots for LinkedIn and the social card.

Structure, after the founder's reference: a headline across the top, a light zone on what the
code is and how it works (one hero panel, then feature panels), an accent zone on what people
do with it (the numbers, then landmark studies), a workflow strip, and the sources line.
"""

from __future__ import annotations

import html

from omai import glyphs

SITE = "https://openmaterials.ai"


def esc(s: object) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def _panel(p: dict, cls: str = "info-panel") -> str:
    return (
        f'<div class="{cls}">{glyphs.svg(p["glyph"], 64, "glyph")}'
        f'<div><h4>{esc(p["title"])}</h4><p>{esc(p["text"])}</p></div></div>'
    )


def _source_href(brief: dict, label: str) -> str:
    for s in brief.get("sources") or []:
        if s.get("label") == label:
            return f"https://doi.org/{s['doi']}" if s.get("doi") else s.get("url", "")
    return ""


def self_reported(brief: dict, references: dict | None) -> bool:
    """True when every application entry cites one of the code's own papers rather than an independent study."""
    apps = brief.get("applications") or []
    if not apps or not references:
        return False
    code_dois = {r["doi"].lower() for r in references.get("code", [])}
    by_label = {s["label"]: (s.get("doi") or "").lower() for s in brief.get("sources") or []}
    return all(by_label.get(a["source"]) in code_dois for a in apps)


def _cite(brief: dict, label: str) -> str:
    href = _source_href(brief, label)
    return f'<a class="info-src" href="{esc(href)}" rel="noopener">{esc(label)}</a>' if href else f'<span class="info-src">{esc(label)}</span>'


def card(brief: dict, name: str, key: str) -> str:
    """The 1200 x 630 social card: headline, claim, the numbers and the hero panel."""
    facts = "".join(
        f'<li><span class="info-value">{esc(f["value"])}</span><span class="info-label">{esc(f["label"])}</span><span class="info-src">{esc(f["source"])}</span></li>'
        for f in brief["facts"]
    )
    return (
        f'<div class="info card" data-code="{esc(key)}">'
        f'<header class="info-head"><p class="info-eyebrow">openmaterials.ai / codes / {esc(name)}</p>'
        f'<h2 class="info-title">{esc(brief["headline"])}</h2><p class="info-claim">{esc(brief["claim"])}</p></header>'
        f'<div class="info-zones"><section class="info-zone info-zone-a">{_panel(brief["hero"], "info-panel info-hero")}</section>'
        f'<section class="info-zone info-zone-b"><ul class="info-facts">{facts}</ul></section></div>'
        f'<footer class="info-foot"><span>Sources: {esc(", ".join(s["label"] for s in brief["sources"]))}.</span><span class="info-url">{esc(SITE)}/codes/{esc(key)}/</span></footer>'
        "</div>"
    )


def block(brief: dict, name: str, key: str, poster: bool = False, self_reported: bool = False) -> str:
    """The infographic. ``self_reported`` says the application entries come from the code's own papers."""
    facts = "".join(
        f'<li><span class="info-value">{esc(f["value"])}</span><span class="info-label">{esc(f["label"])}</span>{_cite(brief, f["source"])}</li>'
        for f in brief["facts"]
    )
    apps = brief.get("applications") or []
    app_panels = "".join(
        f'<div class="info-panel info-app">{glyphs.svg(a["glyph"], 64, "glyph")}<div><h4>{esc(a["title"])}</h4><p>{esc(a["text"])} {_cite(brief, a["source"])}</p></div></div>'
        for a in apps
    )
    steps = "".join(f'<li><h4>{esc(s["title"])}</h4><p>{esc(s["text"])}</p></li>' for s in brief["workflow"])
    sources = ", ".join(_cite(brief, s["label"]) for s in brief["sources"])
    page_url = f"{SITE}/codes/{key}/"
    zone_b_title = ("Results in the papers" if self_reported else "What people do with it") if apps else "By the numbers"
    return (
        f'<div class="info{" poster" if poster else ""} n{len(brief["features"])}" data-code="{esc(key)}">'
        f'<header class="info-head"><p class="info-eyebrow">openmaterials.ai / codes / {esc(name)}</p>'
        f'<h2 class="info-title">{esc(brief["headline"])}</h2><p class="info-claim">{esc(brief["claim"])}</p></header>'
        '<div class="info-zones">'
        '<section class="info-zone info-zone-a"><h3>What it is and how it works</h3>'
        + _panel(brief["hero"], "info-panel info-hero")
        + '<div class="info-panels">' + "".join(_panel(f) for f in brief["features"]) + "</div></section>"
        f'<section class="info-zone info-zone-b"><h3>{zone_b_title}</h3><ul class="info-facts">{facts}</ul>'
        + (f'<div class="info-panels">{app_panels}</div>' if apps else "")
        + "</section></div>"
        f'<section class="info-flow"><h3>How it is used</h3><ol>{steps}</ol></section>'
        f'<footer class="info-foot"><span>Sources: {sources}.</span><span class="info-url">{esc(page_url)}</span></footer>'
        "</div>"
    )


CSS = """
  .info { --info-pad: 20px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: var(--ink); overflow: hidden; }
  .info-head { padding: var(--info-pad) var(--info-pad) 12px; border-bottom: 1px solid var(--line); }
  .info-eyebrow { margin: 0 0 6px; font: 500 11px/16px var(--font-mono); letter-spacing: .06em; text-transform: uppercase; color: var(--ink-2); }
  .info-title { margin: 0; font: 450 26px/30px var(--font-serif); letter-spacing: -0.014em; max-width: none; }
  .info-claim { margin: 8px 0 0; font-size: 16px; line-height: 23px; color: var(--ink-2); max-width: none; }
  .info-zones { display: grid; grid-template-columns: 1fr; }
  .info-zone { padding: var(--info-pad); }
  .info-zone-b { background: color-mix(in srgb, var(--accent) 8%, var(--surface)); border-top: 1px solid var(--line); }
  .info-zone h3, .info-flow h3 { margin: 0 0 12px; font: 500 11.5px/16px var(--font-mono); letter-spacing: .06em; text-transform: uppercase; color: var(--ink-2); }
  .info-panels { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }
  .info-panel { display: flex; gap: 12px; align-items: flex-start; min-width: 0; }
  .info-panel .glyph { flex: none; width: 44px; height: 44px; color: var(--ink-2); }
  .info-panel .glyph .a { stroke: var(--accent); }
  .info-panel .glyph rect.a, .info-panel .glyph circle.a, .info-panel .glyph path.f, .info-panel .glyph rect.f, .info-panel .glyph circle.f, .info-panel .glyph ellipse.f { fill: color-mix(in srgb, var(--accent) 14%, transparent); }
  .info-panel .glyph circle.a, .info-panel .glyph rect.a { fill: color-mix(in srgb, var(--accent) 35%, transparent); }
  .info-panel h4 { margin: 0 0 2px; font: 500 15px/20px var(--font-serif); }
  .info-panel p { margin: 0; font-size: 13.5px; line-height: 19px; max-width: none; }
  .info-hero { margin-bottom: 18px; padding-bottom: 18px; border-bottom: 1px solid var(--line); }
  .info-hero .glyph { width: 88px; height: 88px; }
  .info-hero h4 { font-size: 19px; line-height: 24px; }
  .info-hero p { font-size: 15px; line-height: 21px; }
  .info-facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: 0 0 16px; padding: 0; list-style: none; }
  .info-facts li { display: flex; flex-direction: column; max-width: none; }
  .info-value { font: 400 30px/34px var(--font-mono); color: var(--accent); letter-spacing: -0.02em; }
  .info-label { font-size: 13px; line-height: 18px; }
  .info-src { font: 400 11px/16px var(--font-mono); color: var(--ink-2); text-decoration: none; }
  a.info-src:hover { color: var(--ink); text-decoration: underline; }
  .info-flow { padding: var(--info-pad); border-top: 1px solid var(--line); }
  .info-flow ol { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: 0; padding: 0; list-style: none; counter-reset: step; }
  .info-flow li { position: relative; max-width: none; padding-top: 24px; counter-increment: step; }
  .info-flow li::before { content: counter(step, decimal-leading-zero); position: absolute; top: 0; left: 0; font: 500 11px/16px var(--font-mono); color: var(--accent); }
  .info-flow li::after { content: ""; position: absolute; top: 7px; left: 26px; right: 0; border-top: 1px solid var(--line); }
  .info-flow h4 { margin: 0 0 2px; font: 500 14px/20px var(--font-serif); }
  .info-flow p { margin: 0; font-size: 12.5px; line-height: 17px; color: var(--ink-2); max-width: none; }
  .info-foot { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 4px 16px; padding: 12px var(--info-pad); border-top: 1px solid var(--line); font-size: 12px; line-height: 18px; color: var(--ink-2); }
  .info-url { font-family: var(--font-mono); }
  @media (min-width: 700px) { .info-zones { grid-template-columns: 3fr 2fr; } .info-zone-b { border-top: 0; border-left: 1px solid var(--line); } }

  /* the poster: a fixed 1920 x 1080 canvas, always light */
  .info.poster { --info-pad: 36px; position: relative; width: 1920px; height: 1080px; border: 0; border-radius: 0; color-scheme: light; background: #FBFAF6; color: #1C1A17; display: grid; grid-template-rows: auto 1fr auto auto; }
  .info.poster .info-head { padding: 40px 56px 22px; }
  .info.poster .info-eyebrow { font-size: 16px; line-height: 22px; margin-bottom: 10px; }
  .info.poster .info-title { font-size: 54px; line-height: 60px; }
  .info.poster .info-claim { font-size: 25px; line-height: 34px; margin-top: 12px; }
  .info.poster .info-zones { grid-template-columns: 3fr 2fr; min-height: 0; }
  .info.poster .info-zone { padding: 24px 56px; overflow: hidden; }
  .info.poster .info-zone-b { border-top: 0; border-left: 1px solid var(--line); }
  .info.poster .info-zone h3, .info.poster .info-flow h3 { font-size: 15px; line-height: 20px; margin-bottom: 18px; }
  .info.poster .info-panels { grid-template-columns: repeat(2, 1fr); gap: 18px 32px; }
  .info.poster.n5 .info-zone-a .info-panels { grid-template-columns: repeat(3, 1fr); gap: 18px 28px; }
  .info.poster .info-zone-b .info-panels { grid-template-columns: 1fr; gap: 18px; }
  .info.poster .info-panel .glyph { width: 60px; height: 60px; }
  .info.poster .info-panel h4 { font-size: 22px; line-height: 27px; margin-bottom: 4px; }
  .info.poster .info-panel p { font-size: 17.5px; line-height: 24px; }
  .info.poster.n5 .info-zone-a .info-panel p { font-size: 16.5px; line-height: 22px; }
  .info.poster .info-hero { margin-bottom: 20px; padding-bottom: 20px; }
  .info.poster .info-hero .glyph { width: 140px; height: 140px; }
  .info.poster .info-hero h4 { font-size: 30px; line-height: 36px; }
  .info.poster .info-hero p { font-size: 21px; line-height: 29px; }
  .info.poster .info-facts { grid-template-columns: repeat(3, 1fr); gap: 18px; margin-bottom: 22px; }
  .info.poster .info-value { font-size: 36px; line-height: 42px; white-space: nowrap; }
  .info.poster .info-label { font-size: 17px; line-height: 23px; }
  .info.poster .info-src { font-size: 14px; line-height: 20px; }
  .info.poster .info-flow { padding: 20px 56px 24px; overflow: hidden; }
  .info.poster .info-flow ol { grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 24px; }
  .info.poster .info-flow li { padding-top: 30px; }
  .info.poster .info-flow li::before { font-size: 15px; line-height: 20px; }
  .info.poster .info-flow li::after { top: 9px; left: 36px; }
  .info.poster .info-flow h4 { font-size: 21px; line-height: 27px; }
  .info.poster .info-flow p { font-size: 17px; line-height: 23px; }
  .info.poster .info-foot { padding: 18px 56px 26px; font-size: 17px; line-height: 24px; }

  /* the social card: a fixed 1200 x 630 canvas, always light */
  .info.card { --info-pad: 28px; width: 1200px; height: 630px; border: 0; border-radius: 0; color-scheme: light; background: #FBFAF6; color: #1C1A17; display: grid; grid-template-rows: auto 1fr auto; }
  .info.card .info-head { padding: 36px 48px 20px; }
  .info.card .info-eyebrow { font-size: 14px; line-height: 20px; margin-bottom: 10px; }
  .info.card .info-title { font-size: 44px; line-height: 50px; }
  .info.card .info-claim { font-size: 21px; line-height: 29px; margin-top: 10px; }
  .info.card .info-zones { grid-template-columns: 3fr 2fr; min-height: 0; }
  .info.card .info-zone { padding: 24px 48px; overflow: hidden; }
  .info.card .info-zone-b { border-top: 0; border-left: 1px solid var(--line); }
  .info.card .info-hero { margin: 0; padding: 0; border: 0; }
  .info.card .info-hero .glyph { width: 120px; height: 120px; }
  .info.card .info-hero h4 { font-size: 27px; line-height: 33px; }
  .info.card .info-hero p { font-size: 18px; line-height: 25px; }
  .info.card .info-facts { grid-template-columns: 1fr; gap: 10px; margin: 0; }
  .info.card .info-facts li { flex-direction: row; align-items: baseline; gap: 12px; }
  .info.card .info-value { font-size: 30px; line-height: 36px; white-space: nowrap; min-width: 150px; }
  .info.card .info-label { font-size: 15px; line-height: 20px; }
  .info.card .info-src { display: none; }
  .info.card .info-foot { padding: 14px 48px 20px; font-size: 15px; line-height: 22px; }
"""


def poster_page(brief: dict, name: str, key: str, mode: str = "poster", self_reported: bool = False) -> str:
    """The standalone render page behind a PNG: the poster (1920 x 1080) or the card (1200 x 630), not indexed."""
    width = 1920 if mode == "poster" else 1200
    body = block(brief, name, key, poster=True, self_reported=self_reported) if mode == "poster" else card(brief, name, key)
    return f"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width={width}">
<meta name="robots" content="noindex">
<title>{esc(name)} {mode} | OpenMaterials</title>
<link rel="canonical" href="{SITE}/codes/{esc(key)}/">
<link rel="stylesheet" href="../../../assets/site.css">
<style>
  html, body {{ margin: 0; background: #FBFAF6; }}
  body {{ width: {width}px; overflow: hidden; }}
{CSS}</style>
</head>
<body>
{body}
<script>
  // a zone whose text runs past its box is scaled down in 2% steps, never below 80%
  addEventListener("load", function () {{
    document.querySelectorAll(".info-zone, .info-flow").forEach(function (zone) {{
      var kids = Array.prototype.slice.call(zone.children), z = 1;
      while (zone.scrollHeight > zone.clientHeight + 1 && z > 0.8) {{
        z -= 0.02;
        kids.forEach(function (k) {{ k.style.zoom = z; }});
      }}
      if (zone.scrollHeight > zone.clientHeight + 1) document.body.setAttribute("data-overflow", "1");
    }});
  }});
</script>
</body>
</html>
"""
