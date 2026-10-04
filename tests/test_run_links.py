"""Run links open the MaterialsCodeGraph sign-up panel.

Each link names its place in ref and lands on #hero-connect, the panel with the add command and the
sign-up link (#connect is only the reference block). The app host ends on a sign-in for a first-time
visitor, so no page under docs/ links it.
"""
import re
from pathlib import Path

_DOCS = Path(__file__).resolve().parents[1] / "docs"


def test_run_links_open_the_sign_up_panel():
    for page, ref in (("index.html", "omai-home"), ("index.html", "omai-governance"),
                      ("experiment/index.html", "omai-experiment"), ("play/index.html", "omai-datasheet"),
                      ("llms.txt", "omai-llms")):
        assert f"https://materialscodegraph.com/?ref={ref}#hero-connect" in (_DOCS / page).read_text(), ref


def test_no_page_links_the_app_host_or_the_reference_block():
    bad = re.compile(r"app\.materialscodegraph\.com|materialscodegraph\.com/\?ref=[\w-]+#connect\b")
    hits = [p for p in _DOCS.rglob("*") if p.suffix in {".html", ".js", ".txt"}
            and bad.search(p.read_text(errors="ignore"))]
    assert not hits, hits


def test_datasheet_hides_run_for_measurements():
    assert "recordKind(record) !== 'measurement'" in (_DOCS / "play" / "index.html").read_text()
