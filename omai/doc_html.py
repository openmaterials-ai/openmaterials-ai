"""Build docs/document/index.html from docs/openmaterials.tex.

The document page is generated, never hand edited: this module preprocesses
the LaTeX source (lifting the abstract into the body and replacing the two
TikZ diagrams with clearly marked fallback blocks that keep their captions),
shells out to pandoc for the LaTeX-to-HTML conversion, then post-processes
the fragment (heading levels, section numbering matching the PDF, cross
reference texts, table scroll wrappers) and wraps it in the site chrome with
a sidebar table of contents. Math is emitted as raw TeX in pandoc's
``span.math`` elements and rendered client side by the vendored KaTeX.

Run as::

    PYTHONPATH=. python -m omai.doc_html

The build is deterministic: the output depends only on the LaTeX source and
this module, so running it twice changes zero bytes.
"""

from __future__ import annotations

import html as _html
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEX_PATH = ROOT / "docs" / "openmaterials.tex"
OUT_PATH = ROOT / "docs" / "document" / "index.html"

PANDOC_CANDIDATES = ("/usr/local/bin/pandoc", "/opt/homebrew/bin/pandoc")
# The committed page is byte-exact to this pandoc; other versions emit
# different HTML, so they are not used.
PANDOC_VERSION = "pandoc 2.9.2.1"

ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def find_pandoc() -> str | None:
    """Locate a pandoc binary whose version is PANDOC_VERSION, preferring
    the known system installs; None if no candidate matches."""
    for cand in (*PANDOC_CANDIDATES, shutil.which("pandoc")):
        if not cand or not Path(cand).is_file():
            continue
        try:
            out = subprocess.run([cand, "--version"], capture_output=True,
                                 text=True, check=False).stdout
        except OSError:
            continue
        if out.split("\n", 1)[0] == PANDOC_VERSION:
            return cand
    return None


# ---------------------------------------------------------------------------
# LaTeX helpers
# ---------------------------------------------------------------------------

def balanced_arg(text: str, start: int) -> tuple[str, int]:
    """Return the balanced-brace argument starting at ``text[start] == '{'``.

    Returns (content, index_after_closing_brace).
    """
    assert text[start] == "{"
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:i], i + 1
    raise ValueError("unbalanced braces in LaTeX source")


def command_titles(tex: str, command: str) -> list[str]:
    """All balanced-brace titles of ``\\command{...}`` (unstarred form)."""
    out = []
    for m in re.finditer(r"\\%s\{" % command, tex):
        title, _ = balanced_arg(tex, m.end() - 1)
        out.append(title)
    return out


def title_to_text(title: str) -> str:
    """Normalize a LaTeX heading title to the plain text pandoc emits."""
    t = re.sub(r"\\texttt\{([^{}]*)\}", r"\1", title)
    t = re.sub(r"\\emph\{([^{}]*)\}", r"\1", t)
    t = t.replace(r"\_", "_").replace(r"\&", "&").replace("~", " ")
    t = t.replace("``", '"').replace("''", '"').replace("`", "'")
    return re.sub(r"\s+", " ", t).strip()


STRAIGHT_QUOTES = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'"})


# ---------------------------------------------------------------------------
# Stage 1: preprocess the LaTeX source
# ---------------------------------------------------------------------------

def preprocess_tex(tex: str) -> tuple[str, list[str]]:
    """Prepare the LaTeX source for pandoc.

    Returns the rewritten source and a list of degradation notes (constructs
    that could not be converted and were replaced by marked fallbacks).
    """
    notes: list[str] = []

    # The abstract is metadata to pandoc's fragment writer and would be
    # dropped; lift it into the body between markers the post-processor
    # turns into a styled block.
    def lift_abstract(m: re.Match) -> str:
        body = m.group(1).strip()
        body = re.sub(r"^\\noindent\s*", "", body)
        return "OMAIDOCABSSTART\n\n%s\n\nOMAIDOCABSEND" % body

    tex, n_abs = re.subn(
        r"\\begin\{abstract\}(.*?)\\end\{abstract\}",
        lift_abstract, tex, flags=re.S)
    if n_abs == 0:
        notes.append("no abstract environment found in the LaTeX source")

    # TikZ diagrams cannot be converted by pandoc. Replace each figure that
    # contains one with a marked fallback paragraph that keeps the caption;
    # the post-processor styles it and points at the PDF.
    fig_count = [0]

    def replace_figure(m: re.Match) -> str:
        body = m.group(1)
        if "tikzpicture" not in body:
            return m.group(0)
        fig_count[0] += 1
        n = fig_count[0]
        cap = ""
        cm = re.search(r"\\caption\{", body)
        if cm:
            cap, _ = balanced_arg(body, cm.end() - 1)
        notes.append(
            "figure %d: TikZ diagram replaced by a marked fallback block "
            "(caption kept, diagram only in the PDF)" % n)
        return ("OMAIDOCFIGSTART%d\n\n%s\n\nOMAIDOCFIGEND%d"
                % (n, cap.strip(), n))

    tex = re.sub(r"\\begin\{figure\}(?:\[[^\]]*\])?(.*?)\\end\{figure\}",
                 replace_figure, tex, flags=re.S)

    # Any tikzpicture outside a figure would still break pandoc; drop it the
    # same way (none exist today, this is a guard).
    def replace_bare_tikz(m: re.Match) -> str:
        fig_count[0] += 1
        notes.append("bare TikZ picture %d replaced by a marked fallback "
                     "block" % fig_count[0])
        return ("OMAIDOCFIGSTART%d\n\nDiagram.\n\nOMAIDOCFIGEND%d"
                % (fig_count[0], fig_count[0]))

    tex = re.sub(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}",
                 replace_bare_tikz, tex, flags=re.S)

    # \today would make the build nondeterministic (the date is not in the
    # fragment output today, but keep the guard explicit).
    tex = tex.replace(r"\date{\today}", r"\date{}")

    # A p{width} column is print layout; pandoc would turn it into fixed
    # table and column widths, so the HTML gets a plain l column and the
    # table sizes itself.
    tex = re.sub(
        r"\\begin\{tabular\}\{((?:[^{}]|\{[^{}]*\})*)\}",
        lambda m: "\\begin{tabular}{%s}"
        % re.sub(r"p\{[^{}]*\}", "l", m.group(1)),
        tex)
    return tex, notes


# ---------------------------------------------------------------------------
# Stage 2: pandoc
# ---------------------------------------------------------------------------

def run_pandoc(tex: str, pandoc: str) -> str:
    """Convert LaTeX to an HTML body fragment with math left as TeX."""
    proc = subprocess.run(
        [pandoc, "-f", "latex", "-t", "html", "--katex"],
        input=tex.encode("utf-8"), capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError("pandoc failed: %s"
                           % proc.stderr.decode("utf-8", "replace")[:2000])
    return proc.stdout.decode("utf-8")


# ---------------------------------------------------------------------------
# Stage 3: post-process the fragment
# ---------------------------------------------------------------------------

HEADING_RE = re.compile(r"<h([1-6])([^>]*)>(.*?)</h\1>", re.S)


def remap_heading_levels(body: str) -> str:
    """Shift pandoc's part/section levels to a natural h1..h5 ladder.

    pandoc 2.9 emits \\part as h1, \\section as h3, \\subsection as h4,
    \\subsubsection as h5 and \\paragraph as h6; close the gap.
    """
    for old, new in (("h3", "h2"), ("h4", "h3"), ("h5", "h4"), ("h6", "h5")):
        body = re.sub(r"<%s(\s[^>]*)?>" % old,
                      lambda m, new=new: "<%s%s>" % (new, m.group(1) or ""),
                      body)
        body = body.replace("</%s>" % old, "</%s>" % new)
    return body


def dedupe_class_attr(body: str) -> str:
    """pandoc 2.9 duplicates class="unnumbered" on starred headings."""
    return re.sub(
        r'(<h[1-6][^>]*class="unnumbered"[^>]*) class="unnumbered"',
        r"\1", body)


class Heading:
    def __init__(self, level: int, attrs: str, inner: str, span: tuple):
        self.level = level
        self.attrs = attrs
        self.inner = inner
        self.span = span
        m = re.search(r'id="([^"]*)"', attrs)
        self.id = m.group(1) if m else ""
        self.unnumbered = "unnumbered" in attrs
        self.number = ""
        self.refnum = ""


def collect_headings(body: str) -> list[Heading]:
    return [Heading(int(m.group(1)), m.group(2), m.group(3), m.span())
            for m in HEADING_RE.finditer(body)]


def assign_numbers(headings: list[Heading]) -> None:
    """Number parts/sections/subsections the way the compiled PDF does:
    roman parts, sections numbered continuously across parts, lettered
    appendix sections, dotted subsections."""
    part_i = 0
    sec_i = 0
    app_i = -1  # -1: not yet in the appendices
    sub_i = 0
    cur_sec = ""
    for h in headings:
        if h.level == 1:
            if h.id == "appendices" or h.inner.strip() == "Appendices":
                app_i = 0
            elif not h.unnumbered:
                part_i += 1
                h.number = ROMAN[part_i - 1] if part_i <= len(ROMAN) else ""
        elif h.level == 2 and not h.unnumbered:
            if app_i >= 0:
                h.number = LETTERS[app_i]
                app_i += 1
            else:
                sec_i += 1
                h.number = str(sec_i)
            cur_sec = h.number
            sub_i = 0
        elif h.level == 3 and not h.unnumbered and cur_sec:
            sub_i += 1
            h.number = "%s.%s" % (cur_sec, sub_i)


def inject_numbers(body: str, headings: list[Heading]) -> str:
    """Prepend the computed number to each numbered heading, in place."""
    out = []
    last = 0
    for h in headings:
        start, end = h.span
        out.append(body[last:start])
        if h.level == 1 and h.number:
            label = '<span class="partno">Part %s</span>' % h.number
        elif h.number:
            label = '<span class="secno">%s</span> ' % h.number
        else:
            label = ""
        out.append("<h%d%s>%s%s</h%d>"
                   % (h.level, h.attrs, label, h.inner, h.level))
        last = end
    out.append(body[last:])
    return "".join(out)


def rewrite_refs(body: str, headings: list[Heading]) -> str:
    """Give \\ref links the same numbers the headings display.

    pandoc numbers sections with its own counters (and leaves part refs
    empty); replace each resolvable reference text with the computed
    number so 'Part IV' and 'Appendix A' read correctly. A label on an
    unnumbered heading (the source labels one \\paragraph) resolves to
    the nearest preceding numbered heading, which is what LaTeX's \\ref
    prints for it.
    """
    last = ""
    for h in headings:
        if h.number:
            last = h.number
        h.refnum = h.number or last
    numbers = {h.id: h.refnum for h in headings if h.id and h.refnum}
    return re.sub(
        r'(<a href="#([^"]+)"[^>]*data-reference-type="ref"[^>]*>)([^<]*)</a>',
        lambda m: (m.group(1) + numbers[m.group(2)] + "</a>")
        if m.group(2) in numbers else m.group(0),
        body)


def wrap_markers(body: str) -> str:
    """Turn the preprocess markers into styled blocks."""
    body = body.replace(
        "<p>OMAIDOCABSSTART</p>",
        '<div class="abstract"><span class="abstract-label">Abstract</span>')
    body = body.replace("<p>OMAIDOCABSEND</p>", "</div>")
    body = re.sub(
        r"<p>OMAIDOCFIGSTART(\d+)</p>",
        r'<div class="fig-fallback">'
        r'<span class="fig-fallback-label">Figure \1: diagram not converted '
        r'to HTML.</span> <span class="fig-fallback-note">This diagram is '
        r'drawn with TikZ and renders only in '
        r'<a href="../openmaterials.pdf">the PDF</a>. Its caption:</span>',
        body)
    body = re.sub(r"<p>OMAIDOCFIGEND(\d+)</p>", "</div>", body)
    return body


def wrap_tables(body: str) -> str:
    """Wrap every table in a horizontal-scroll container."""
    body = body.replace("<table>", '<div class="tblwrap"><table>')
    body = body.replace("</table>", "</table></div>")
    return body


def build_toc(headings: list[Heading]) -> str:
    """Nested TOC list: parts as groups, sections, subsections."""

    def text_of(h: Heading) -> str:
        return re.sub(r"<[^>]+>", "", h.inner).strip()

    items = []
    stack_open = {2: False, 3: False}

    def close_sub():
        if stack_open[3]:
            items.append("</ol>")
            stack_open[3] = False

    def close_sec():
        close_sub()
        if stack_open[2]:
            items.append("</ol>")
            stack_open[2] = False

    for h in headings:
        if h.level > 3 or not h.id:
            continue
        anchor = _html.escape(h.id, quote=True)
        text = text_of(h)
        if h.level == 1:
            close_sec()
            label = ("Part %s" % h.number) if h.number else ""
            items.append(
                '<li class="toc-part"><a href="#%s">'
                '%s<span class="toc-part-title">%s</span></a>'
                % (anchor,
                   ('<span class="toc-partno">%s</span>' % label)
                   if label else "", _html.escape(text)))
            items.append('<ol class="toc-secs">')
            stack_open[2] = True
        elif h.level == 2:
            close_sub()
            if not stack_open[2]:
                items.append('<ol class="toc-secs">')
                stack_open[2] = True
            num = ('<span class="toc-no">%s</span>' % h.number) \
                if h.number else ""
            items.append('<li><a href="#%s">%s%s</a>'
                         % (anchor, num, _html.escape(text)))
            items.append('<ol class="toc-subs">')
            stack_open[3] = True
        elif h.level == 3:
            if not stack_open[3]:
                continue
            num = ('<span class="toc-no">%s</span>' % h.number) \
                if h.number else ""
            items.append('<li><a href="#%s">%s%s</a></li>'
                         % (anchor, num, _html.escape(text)))
    close_sec()
    return '<ol class="toc-parts">%s</ol>' % "".join(items)


# ---------------------------------------------------------------------------
# Stage 4: the page template
# ---------------------------------------------------------------------------

PAGE_CSS = """
  /* the document on the content-page grammar (spec 4.1, 4.2); .page-head, .page-body and .prose come from site.css */
  .doc-byline { margin-top: 12px; font-size: 14px; line-height: 20px; color: var(--ink-2); }
  .doc-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin-top: 24px; }
  .doc-actions .hint { font-size: 14px; line-height: 20px; color: var(--ink-2); }
  .doc-toc { font-size: 14px; line-height: 20px; border: 1px solid var(--line); border-radius: var(--radius); padding: 12px 16px; }
  .doc-toc summary { cursor: pointer; font-weight: 500; color: var(--ink); }
  .doc-toc ol { list-style: none; margin: 0; padding: 0; }
  .toc-parts { margin-top: 12px; }
  .toc-parts > li.toc-part { margin: 12px 0 4px; }
  .doc-toc a { display: block; padding: 2px 0; color: var(--ink-2); text-decoration: none; }
  .toc-part > a { color: var(--ink); }
  .toc-partno { display: block; font-size: 12px; line-height: 16px; color: var(--ink-2); }
  .toc-subs > li > a { padding-left: 12px; font-size: 13px; }
  .doc-toc a:hover, .doc-toc a.active { color: var(--ink); }
  .toc-no { display: inline-block; min-width: 2.2em; font-variant-numeric: tabular-nums; color: var(--ink-2); }
  .doc-body [id] { scroll-margin-top: calc(var(--header-h) + 24px); }
  .doc-body h1 { font: 450 32px/40px var(--font-sans); letter-spacing: -0.04em; margin: 64px 0 16px; padding-top: 32px; border-top: 1px solid var(--line); }
  .doc-body h1:first-child { margin-top: 0; padding-top: 0; border-top: 0; }
  .doc-body h2 { margin-top: 48px; }
  .partno { display: block; margin: 0 0 8px; font: 500 14px/20px var(--font-sans); letter-spacing: 0; color: var(--ink-2); }
  .doc-body h5 { font: 500 14px/20px var(--font-sans); margin: 20px 0 8px; color: var(--ink-2); }
  .secno { margin-right: .35em; font-variant-numeric: tabular-nums; color: var(--ink-2); }
  .doc-body pre { margin: 0 0 16px; padding: 16px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--page); font: 400 13px/20px var(--font-mono); white-space: pre-wrap; overflow-wrap: anywhere; }
  .doc-body pre code { padding: 0; background: none; font: inherit; }
  .doc-body .math.display { display: block; overflow-x: auto; overflow-y: hidden; margin: 0 0 16px; padding: 4px 0; text-align: center; }
  .tblwrap { margin: 0 0 16px; }
  .abstract { margin-bottom: 32px; }
  .abstract .abstract-label { display: block; margin: 0 0 8px; font: 500 14px/20px var(--font-sans); color: var(--ink-2); }
  .fig-fallback { margin: 0 0 24px; }
  .fig-fallback-label { display: block; font-weight: 500; color: var(--ink-2); }
  .fig-fallback-note { display: block; margin: 0 0 8px; color: var(--ink-2); }
  @media (min-width: 961px) {
    .doc-layout { grid-template-columns: 200px minmax(0, 720px); gap: 64px; }
    .doc-toc { position: sticky; top: calc(var(--header-h) + 24px); align-self: start; max-height: calc(100vh - var(--header-h) - 48px); overflow-y: auto; padding: 0; border: 0; border-radius: 0; }
  }
"""

PAGE_SCRIPT = """
(function () {
  'use strict';
  // Render pandoc's math spans with the vendored KaTeX. A few commands the
  // source uses are not KaTeX built-ins; probe and polyfill via macros so
  // nothing silently renders as an error.
  var macros = {};
  if (typeof katex !== 'undefined') {
    [['\\\\textsc', '\\\\text{#1}'], ['\\\\textup', '\\\\text{#1}']]
      .forEach(function (pair) {
        try { katex.renderToString(pair[0] + '{a}', { throwOnError: true }); }
        catch (e) { macros[pair[0]] = pair[1]; }
      });
    try { katex.renderToString('\\\\AA', { throwOnError: true }); }
    catch (e) { macros['\\\\AA'] = '\\\\text{\\u00c5}'; }
    var maths = document.querySelectorAll('.doc-body .math');
    for (var i = 0; i < maths.length; i++) {
      var el = maths[i];
      var displayMode = el.classList.contains('display');
      var src = el.textContent;
      try {
        katex.render(src, el, {
          displayMode: displayMode, throwOnError: false, macros: macros
        });
      } catch (e) { /* keep the TeX source visible */ }
    }
  }

  // The TOC is a <details>: collapsed by default on narrow screens, forced
  // open (with the summary acting as a plain title) on wide ones.
  var toc = document.getElementById('toc');
  if (toc && window.matchMedia('(min-width: 961px)').matches) {
    toc.open = true;
  }

  // Scroll spy: highlight the TOC entry of the section in view.
  var links = toc ? toc.querySelectorAll('a[href^="#"]') : [];
  var byId = {};
  for (var j = 0; j < links.length; j++) {
    byId[decodeURIComponent(links[j].hash.slice(1))] = links[j];
  }
  var current = null;
  function activate(id) {
    var link = byId[id];
    if (!link || link === current) return;
    if (current) current.classList.remove('active');
    link.classList.add('active');
    current = link;
  }
  if ('IntersectionObserver' in window && links.length) {
    var seen = [];
    var obs = new IntersectionObserver(function (entries) {
      for (var k = 0; k < entries.length; k++) {
        var e = entries[k];
        var idx = seen.indexOf(e.target);
        if (e.isIntersecting && idx === -1) seen.push(e.target);
        if (!e.isIntersecting && idx !== -1) seen.splice(idx, 1);
      }
      if (seen.length) {
        seen.sort(function (a, b) {
          return a.getBoundingClientRect().top - b.getBoundingClientRect().top;
        });
        activate(seen[0].id);
      }
    }, { rootMargin: '-70px 0px -60% 0px' });
    var heads = document.querySelectorAll(
      '.doc-body h1[id], .doc-body h2[id], .doc-body h3[id]');
    for (var h = 0; h < heads.length; h++) obs.observe(heads[h]);
  }
})();
"""

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The document | OpenMaterials</title>
<meta name="description" content="The full OpenMaterials specification (vision, product, architecture, kernel, and status) is published here as HTML, generated from docs/openmaterials.tex. The typeset PDF is linked at the top.">
<link rel="canonical" href="https://openmaterials.ai/document/">
<meta name="theme-color" content="#FFFFFF" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#000000" media="(prefers-color-scheme: dark)">
<link rel="icon" href="../assets/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="../assets/apple-touch-icon.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="openmaterials.ai">
<meta property="og:title" content="The document | OpenMaterials">
<meta property="og:description" content="The full OpenMaterials specification is published here as HTML, with the typeset PDF.">
<meta property="og:url" content="https://openmaterials.ai/document/">
<meta property="og:image" content="https://openmaterials.ai/assets/og.png">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta property="og:image:alt" content="The openmaterials.ai mark and wordmark above the line &quot;A versioned map of physics.&quot; A smaller line gives the licenses: map data CC BY 4.0 and code Apache 2.0.">
<meta name="twitter:card" content="summary_large_image">
<script>try{const t=localStorage.getItem('theme');if(t==='light'||t==='dark')document.documentElement.dataset.theme=t}catch{}</script>
<link rel="preload" href="../assets/fonts/Geist-Variable.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="../assets/fonts/GeistMono-Variable.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="../assets/vendor/katex/dist/katex.min.css">
<link rel="stylesheet" href="../assets/site.css">
<style>__CSS__</style>
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<div data-site-header></div>

<main class="frame" id="main">
<header class="doc-hero page-head">
  <p class="eyebrow">Document</p>
  <h1>openmaterials.ai</h1>
  <p class="doc-tagline lede">Specification and status of the OpenMaterials map</p>
  <p class="doc-byline">The OpenMaterials project. Map data is
    <a href="https://github.com/openmaterials-ai/openmaterials-ai/blob/main/LICENSE-DATA">CC BY 4.0</a> and code is
    <a href="https://github.com/openmaterials-ai/openmaterials-ai/blob/main/LICENSE">Apache 2.0</a>.</p>
  <div class="doc-actions">
    <a class="btn btn--secondary btn--sm" href="../openmaterials.pdf" id="download-pdf">Download the PDF</a>
    <span class="hint">This page is generated from the LaTeX source; the PDF is the typeset original.</span>
  </div>
</header>

<div class="doc-layout page-body">
  <details class="doc-toc" id="toc">
    <summary>On this page</summary>
    <nav aria-label="Table of contents">
__TOC__
    </nav>
  </details>
  <article class="doc-body prose">
__BODY__
  </article>
</div>
</main>

<div data-site-footer></div>
<script src="../assets/site.js"></script>
<script src="../assets/vendor/katex/dist/katex.min.js"></script>
<script>__SCRIPT__</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build_page(tex: str, pandoc: str) -> tuple[str, list[str]]:
    """Full pipeline: LaTeX source text to the final page HTML."""
    pre, notes = preprocess_tex(tex)
    body = run_pandoc(pre, pandoc)
    # straight quotes in the HTML; the PDF keeps TeX's curly quotes
    body = body.translate(STRAIGHT_QUOTES)
    body = dedupe_class_attr(body)
    body = remap_heading_levels(body)
    headings = collect_headings(body)
    assign_numbers(headings)
    body = inject_numbers(body, headings)
    headings = collect_headings(body)
    # recover numbers (and clean titles) from the injected spans so the
    # TOC and cross references see them
    assign_numbers_from_spans(headings)
    body = rewrite_refs(body, headings)
    body = wrap_markers(body)
    body = wrap_tables(body)
    toc = build_toc(headings)
    page = (PAGE_TEMPLATE
            .replace("__CSS__", PAGE_CSS)
            .replace("__TOC__", toc)
            .replace("__BODY__", body.strip())
            .replace("__SCRIPT__", PAGE_SCRIPT))
    return page, notes


def assign_numbers_from_spans(headings: list[Heading]) -> None:
    """Recover each heading's number from the injected span and strip the
    span from the inner text used by the TOC."""
    for h in headings:
        m = re.match(
            r'\s*<span class="(?:partno|secno)">(?:Part )?([^<]*)</span>\s*',
            h.inner)
        if m:
            h.number = m.group(1)
            h.inner = h.inner[m.end():]


def main() -> int:
    pandoc = find_pandoc()
    if pandoc is None:
        raise SystemExit("%s not found (the page is byte-exact to that "
                         "version); install it or adjust PANDOC_CANDIDATES "
                         "in omai/doc_html.py" % PANDOC_VERSION)
    tex = TEX_PATH.read_text(encoding="utf-8")
    page, notes = build_page(tex, pandoc)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    changed = (not OUT_PATH.exists()
               or OUT_PATH.read_text(encoding="utf-8") != page)
    OUT_PATH.write_text(page, encoding="utf-8")
    n_sec = len(command_titles(tex, "section"))
    n_sub = len(command_titles(tex, "subsection"))
    print("wrote %s (%s)" % (OUT_PATH.relative_to(ROOT),
                             "changed" if changed else "unchanged"))
    print("sections: %d, subsections: %d" % (n_sec, n_sub))
    for note in notes:
        print("degraded: %s" % note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
