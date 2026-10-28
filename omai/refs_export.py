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
# Papers added by hand to a group (DOIs). Metadata comes from the Zotero library when the item is
# there, otherwise from doi.org (CSL JSON). The Zotero collections should carry them too; this map
# is the record of what was curated and why until they do.
CURATED = {
    "gpumd": {"methods": ["10.1103/PhysRevB.104.104309", "10.1038/s43588-026-01009-6"]},  # NEP framework; NEP89
    "kaldo": {"methods": ["10.1038/s41467-019-11572-4", "10.1103/PhysRevB.48.12581"]},  # QHGK (Isaeva 2019); Allen-Feldman
    "shengbte": {"methods": ["10.1016/0921-4526(95)00016-3"]},  # iterative BTE (Omini and Sparavigna 1995)
    "phono3py": {"methods": ["10.1103/PhysRevLett.110.265506"]},  # direct solution of the BTE (Chaput 2013)
    "fairchem": {"code": ["10.48550/arXiv.2410.12771"]},  # OMat24 dataset and models
    "xtb": {"applications": ["10.1021/acs.jctc.9b00143", "10.1039/C9CP06869D"]},  # CREST conformer search on GFN2-xTB
    "plumed": {"applications": ["10.1103/PhysRevLett.104.190601", "10.1073/pnas.1303186110", "10.1103/PhysRevLett.111.230602", "10.1073/pnas.1811056115"]},  # well-tempered ensemble; funnel metadynamics; infrequent metadynamics; polymorph prediction
    "i-pi": {"applications": ["10.1063/1.4883861", "10.1063/1.4971438", "10.1073/pnas.1815117116"]},  # TRPMD; high-order PIMD; ab initio water thermodynamics
}
EXCLUDE_APPLICATIONS_REVIEWS = {
    "10.1016/j.neuron.2018.08.011": "review (Molecular Dynamics Simulation for All), not an OpenMM study",
}
# Never exported as an application: a paper that cites the code but is another tool's software or
# method paper, a dataset, or a review, found in the 2026-10-28 physics review. Kept here rather
# than in Zotero so a re-export stays consistent; the Zotero items carry the tag "not-an-application".
EXCLUDE_APPLICATIONS = {
    "10.1103/physrevb.73.155114": "CASTEP DFPT paper (Refson 2006), not a VASP study",
    "10.1063/5.0155600": "DeePMD-kit software paper",
    "10.1021/acs.jctc.9b00143": "xtb metadynamics (Grimme 2019), does not use PLUMED",
    "10.1039/d1cp02805g": "Multiwfn method paper",
    "10.1002/jcc.26812": "Multiwfn method paper (IGMH)",
    "10.1063/5.0216272": "Multiwfn software paper",
    "10.1063/5.0007045": "CP2K software paper",
    "10.1063/5.0006002": "Psi4 software paper",
    "10.1063/5.0004997": "NWChem software paper",
    "10.1021/acs.chemrev.0c01111": "review of machine learning force fields",
    "10.1103/physrevb.92.054301": "ALAMODE self-consistent phonons (Tadano 2015), not phono3py",
    "10.1103/physrevb.90.174107": "AFLOW AGL/AEL paper (Toher 2014), not Materials Project or pymatgen",
    "10.1038/s41524-019-0203-2": "PoLyInfo polymer study (Wu 2019), not mp-api",
    "10.1038/s41597-022-01882-6": "SPICE dataset paper",
    "10.1039/d4sc08572h": "AIMNet2 potential paper, not a MACE study",
    "10.1103/physrevb.89.064302": "SSCHA (Errea 2014), not verified as a D3Q user",
    "10.1103/physrevb.89.155426": "finite-difference third-order code (Lindsay 2014), not verified as a D3Q user",
}


def _open_copy(db_path: Path, tmp: Path) -> sqlite3.Connection:
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
        "join creatorTypes ct on ct.creatorTypeID=ic.creatorTypeID "
        "where ic.itemID=? and ct.creatorType='author' order by ic.orderIndex",
        (item_id,),
    ).fetchall()
    out = []
    for last, first in rows:
        initials = " ".join(p[0] + "." for p in (first or "").replace("-", " ").split() if p)
        out.append(f"{initials} {last}".strip() if initials else last)
    return out


def _entry_from_doi(db: sqlite3.Connection, doi: str) -> dict | None:
    """The Zotero item with this DOI, or the doi.org CSL record when the library lacks it."""
    row = db.execute(
        "select d.itemID from itemData d join itemDataValues v on v.valueID=d.valueID join fields f on f.fieldID=d.fieldID "
        "where f.fieldName='DOI' and lower(v.value)=lower(?)",
        (doi,),
    ).fetchone()
    if row:
        return _entry(db, row[0])
    import json as _json
    import urllib.request

    req = urllib.request.Request("https://doi.org/" + doi, headers={"Accept": "application/vnd.citationstyles.csl+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        csl = _json.load(r)
    year = (csl.get("issued") or {}).get("date-parts", [[None]])[0][0]
    authors = [f"{' '.join(p[0] + '.' for p in a.get('given', '').replace('-', ' ').split())} {a.get('family', '')}".strip()
               for a in csl.get("author", []) if a.get("family")]
    return {"doi": doi, "title": " ".join(str(csl.get("title", "")).split()), "authors": authors, "year": year,
            "journal": csl.get("container-title") or csl.get("publisher") or ""}


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
        "journal": next((v for v in (_field(db, item_id, f).strip() for f in ("publicationTitle", "proceedingsTitle", "conferenceName", "journalAbbreviation", "repository")) if v), ""),
    }


def export(db_path: Path, out_dir: Path = OUT_DIR) -> dict[str, dict[str, int]]:
    with tempfile.TemporaryDirectory() as tmp:
        return _export(_open_copy(db_path, Path(tmp)), out_dir)


def _export(db: sqlite3.Connection, out_dir: Path) -> dict[str, dict[str, int]]:
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
                if e and group == "applications" and e["doi"].lower() in {*EXCLUDE_APPLICATIONS, *EXCLUDE_APPLICATIONS_REVIEWS}:
                    continue
                if e and e["doi"].lower() not in {x["doi"].lower() for x in groups[group]}:
                    groups[group].append(e)
        for group, dois in CURATED.get(key, {}).items():
            for doi in dois:
                if doi.lower() not in {x["doi"].lower() for x in groups[group]}:
                    e = _entry_from_doi(db, doi)
                    if e:
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
