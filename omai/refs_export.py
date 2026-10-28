"""Export the per-code reference lists from a Zotero library into docs/data/references/<key>.json.

The curated lists live in Zotero as ``MCG codes / <key>`` with subcollections ``<key> code``,
``<key> methods`` and ``<key> applications`` (case-insensitive). Each entry keeps what a reader
needs to find and cite the paper: DOI, title, authors, year, journal. The JSON is committed, so
the site builds without Zotero; rerun this when the collections change.

Run as::

    PYTHONPATH=. python -m omai.refs_export [--zotero ~/Zotero/zotero.sqlite]

The database is copied before reading, so a running Zotero is never locked.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "data" / "references"
GROUPS = ("code", "methods", "applications")


def _open_copy(db_path: Path) -> sqlite3.Connection:
    tmp = Path(tempfile.mkdtemp())
    for ext in ("-wal", "-shm", ""):
        src = Path(str(db_path) + ext)
        if src.exists():
            shutil.copy(src, tmp / ("z.sqlite" + ext))
    return sqlite3.connect(tmp / "z.sqlite")


def _field(db: sqlite3.Connection, item_id: int, name: str) -> str:
    row = db.execute(
        "select v.value from itemData d join itemDataValues v on v.valueID=d.valueID "
        "join fields f on f.fieldID=d.fieldID where d.itemID=? and f.fieldName=?",
        (item_id, name),
    ).fetchone()
    return row[0] if row else ""


def _authors(db: sqlite3.Connection, item_id: int) -> list[str]:
    rows = db.execute(
        "select c.lastName, c.firstName from itemCreators ic join creators c on c.creatorID=ic.creatorID "
        "where ic.itemID=? order by ic.orderIndex",
        (item_id,),
    ).fetchall()
    out = []
    for last, first in rows:
        initials = " ".join(p[0] + "." for p in (first or "").replace("-", " ").split() if p)
        out.append(f"{initials} {last}".strip() if initials else last)
    return out


def _entry(db: sqlite3.Connection, item_id: int) -> dict | None:
    title = _field(db, item_id, "title").strip()
    doi = _field(db, item_id, "DOI").strip()
    if not title or not doi:
        return None  # a reader cannot resolve it; the Zotero item is tagged needs-metadata upstream
    date = _field(db, item_id, "date")
    year = int(date[:4]) if date[:4].isdigit() else None
    return {
        "doi": doi,
        "title": " ".join(title.replace(chr(0x2014), ": ").replace(chr(0x2013), "-").split()),  # em and en dashes in titles become colon and hyphen, the site's house style
        "authors": _authors(db, item_id),
        "year": year,
        "journal": _field(db, item_id, "publicationTitle").strip() or _field(db, item_id, "journalAbbreviation").strip(),
    }


def export(db_path: Path, out_dir: Path = OUT_DIR) -> dict[str, dict[str, int]]:
    db = _open_copy(db_path)
    row = db.execute("select collectionID from collections where collectionName='MCG codes'").fetchone()
    if not row:
        raise SystemExit("no 'MCG codes' collection in this Zotero library")
    parent = row[0]
    out_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, dict[str, int]] = {}
    for code_id, key in db.execute(
        "select collectionID, collectionName from collections where parentCollectionID=? order by collectionName", (parent,)
    ):
        groups: dict[str, list] = {g: [] for g in GROUPS}
        for sub_id, sub_name in db.execute(
            "select collectionID, collectionName from collections where parentCollectionID=?", (code_id,)
        ):
            group = sub_name.lower().rsplit(" ", 1)[-1]
            if group not in groups:
                continue
            items = db.execute(
                "select ci.itemID from collectionItems ci join items i on i.itemID=ci.itemID "
                "left join deletedItems d on d.itemID=i.itemID where ci.collectionID=? and d.itemID is null "
                "order by ci.itemID",
                (sub_id,),
            ).fetchall()
            for (item_id,) in items:
                e = _entry(db, item_id)
                if e and e["doi"].lower() not in {x["doi"].lower() for x in groups[group]}:
                    groups[group].append(e)
        for g in GROUPS:  # year ascending inside a group: the story of a code reads forward
            groups[g].sort(key=lambda e: (e["year"] or 0, e["title"]))
        (out_dir / f"{key}.json").write_text(json.dumps({"key": key, **groups}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        counts[key] = {g: len(groups[g]) for g in GROUPS}
    return counts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--zotero", default=str(Path.home() / "Zotero" / "zotero.sqlite"))
    args = ap.parse_args()
    for key, c in export(Path(args.zotero).expanduser()).items():
        print(f"{key:28s} code {c['code']:2d}  methods {c['methods']:2d}  applications {c['applications']:2d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
