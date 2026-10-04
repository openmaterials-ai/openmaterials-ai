"""One navigation, everywhere.

site.js renders the one header into a data-site-header mount: the links Map,
Playground, Guide and Document, and the GitHub button. Every content page
mounts it. The four tool pages are pending the final shell pass: they still
inline their own header and nav, and move to the mount with
data-variant="app" when the shell lands there. Until then this contract
accepts either form on those four pages.
"""

import re
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "docs"
SITE_JS = (DOCS / "assets/site.js").read_text()

CANONICAL = ["Map", "Playground", "Guide", "Document"]
GITHUB = "https://github.com/openmaterials-ai/openmaterials-ai"

# Pages whose header is injected by site.js (mount point + script include).
INJECTED = [
    "index.html",
    "404.html",
    "guide/index.html",
    "document/index.html",
    "lean/index.html",
    "lean/roadmap/index.html",
    "lineage/index.html",
    "experiment/index.html",
    "agreement/index.html",
    "codes/index.html",
]

# Pending the final shell pass (spec 5.1): inline header now, the app mount later.
TOOL_PAGES = [
    "map/index.html",
    "map-3d/index.html",
    "map-trace/index.html",
    "play/index.html",
]

# Standalone artifacts, deliberately outside the primary navigation.
EXEMPT_DIRS = {"deck", "slides", "map-lab", "learn", "i"}


def test_sitejs_nav_is_canonical():
    nav = re.search(r"var NAV = \[(.*?)\];", SITE_JS, re.S)
    assert nav, "site.js has no NAV list"
    assert re.findall(r"\['([^']+)', '[^']*'\]", nav.group(1)) == CANONICAL
    assert "var REPO = '" + GITHUB + "';" in SITE_JS
    assert "btn btn--secondary btn--sm\" href=\"' + REPO + '\">GitHub</a>" in SITE_JS, \
        "the header's GitHub button"


def test_injected_pages_mount_the_shared_header():
    for rel in INJECTED:
        s = (DOCS / rel).read_text()
        assert "data-site-header" in s, rel + " lacks the header mount"
        assert "assets/site.js" in s, rel + " lacks the site.js include"
        assert 'aria-label="Primary"' not in s, rel + " still inlines a nav"


def test_tool_pages_carry_a_header_pending_the_shell_pass():
    for rel in TOOL_PAGES:
        s = (DOCS / rel).read_text()
        if "data-site-header" in s:
            assert 'data-variant="app"' in s and "assets/site.js" in s, rel
            continue
        nav = re.search(r'<nav[^>]*aria-label="Primary"[^>]*>(.*?)</nav>', s, re.S)
        assert nav, rel + " has neither the app mount nor its inline nav"
        assert "openmaterials.pdf" not in nav.group(1), rel + " nav links the raw PDF"


def test_no_page_is_headerless():
    for page in sorted(DOCS.glob("*/index.html")):
        rel = page.relative_to(DOCS)
        if rel.parts[0] in EXEMPT_DIRS:
            continue
        s = page.read_text()
        assert "data-site-header" in s or 'aria-label="Primary"' in s, str(rel)


def test_footer_links_codes_and_lean():
    footer = re.search(r"var FOOTER = \[(.*?)\];", SITE_JS, re.S).group(1)
    assert "['Codes', 'codes/']" in footer
    assert "['Verified layer', 'lean/']" in footer


def test_map_supports_the_code_hash_filter():
    s = (DOCS / "map/index.html").read_text()
    assert "codeFromHash" in s
    assert re.search(r"codeRef && codesData\[codeRef\]", s)
