"""One navigation, everywhere.

site.js renders the one header into a data-site-header mount: the links Map,
Playground, Guide and Document, and the GitHub button. Every content page
mounts it, and the four tool pages mount its app variant (data-variant="app"),
which adds the theme toggle. No page inlines a nav of its own.
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
    "agreement/index.html",
    "codes/index.html",
]

# The tool pages mount the app variant of the same header (spec 2.3, 5.1).
TOOL_PAGES = [
    "map/index.html",
    "map-3d/index.html",
    "map-trace/index.html",
    "play/index.html",
]

# Standalone artifacts, deliberately outside the primary navigation.
EXEMPT_DIRS = {"map-lab", "learn", "i"}


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


def test_tool_pages_mount_the_app_header():
    for rel in TOOL_PAGES:
        s = (DOCS / rel).read_text()
        assert '<div data-site-header data-variant="app"></div>' in s, rel
        assert '<script src="../assets/site.js"></script>' in s, rel
        assert 'aria-label="Primary"' not in s, rel + " still inlines a nav"
        assert 'class="top"' not in s and 'class="pg-top"' not in s, rel + " still inlines a header"


def test_every_page_marks_its_own_nav_item():
    for section, current in (("map/", "map/"), ("map-3d/", "map/"), ("map-trace/", "map/"),
                             ("play/", "play/"), ("guide/", "guide/"), ("document/", "document/")):
        assert "'" + section + "': '" + current + "'" in SITE_JS, section


def test_no_page_is_headerless():
    for page in sorted(DOCS.glob("*/index.html")):
        rel = page.relative_to(DOCS)
        if rel.parts[0] in EXEMPT_DIRS:
            continue
        s = page.read_text()
        assert "data-site-header" in s and "assets/site.js" in s, str(rel)


def test_footer_links_codes_and_lean():
    footer = re.search(r"var FOOTER = \[(.*?)\];", SITE_JS, re.S).group(1)
    assert "['Codes', 'codes/']" in footer
    assert "['Verified layer', 'lean/']" in footer


def test_map_supports_the_code_hash_filter():
    s = (DOCS / "map/index.html").read_text()
    assert "codeFromHash" in s
    assert re.search(r"codeRef && codesData\[codeRef\]", s)
