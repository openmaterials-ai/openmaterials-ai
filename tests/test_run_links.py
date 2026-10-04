"""Run links open the connect panel at the top of materialscodegraph.com (#hero-connect).

The app host ends on a sign-in for a first-time visitor, so no page under docs/ links it.
"""
from pathlib import Path

_DOCS = Path(__file__).resolve().parents[1] / "docs"


def test_run_links_open_the_connect_page():
    for page, ref in (("play", "omai-datasheet"), ("experiment", "omai-experiment")):
        html = (_DOCS / page / "index.html").read_text()
        assert f"https://materialscodegraph.com/?ref={ref}#hero-connect" in html, page


def test_no_page_links_the_app_host():
    hits = [p for p in _DOCS.rglob("*") if p.suffix in {".html", ".js", ".txt"}
            and "app.materialscodegraph.com" in p.read_text(errors="ignore")]
    assert not hits, hits


def test_datasheet_hides_run_for_measurements():
    assert "recordKind(record) !== 'measurement'" in (_DOCS / "play" / "index.html").read_text()
