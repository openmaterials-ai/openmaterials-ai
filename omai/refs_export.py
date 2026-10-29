"""Export the per-code reference lists from a Zotero library into docs/data/references/<key>.json.

The curated lists live in Zotero as ``MCG codes / <key>`` with subcollections ``<key> code``,
``<key> methods`` and ``<key> applications`` (case-insensitive). Zotero supplies the membership;
every entry's title, authors, year and journal come from the doi.org registry record (CSL JSON),
with the Zotero copy as the fallback when the registry is unreachable. The JSON is committed, so
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
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "data" / "references"
GROUPS = ("code", "methods", "applications")
# Papers added by hand to a group (DOIs). Metadata comes from the Zotero library when the item is
# there, otherwise from doi.org (CSL JSON). The Zotero collections should carry them too; this map
# is the record of what was curated and why until they do.
CURATED = {
    "gpumd": {"methods": ["10.1103/PhysRevB.104.104309", "10.1038/s43588-026-01009-6"],  # NEP framework; NEP89, the potential the platform serves through GPUMD
              "applications": ["10.1103/PhysRevB.100.064306", "10.1103/PhysRevB.97.094305", "10.1038/s41467-024-54554-x"]},  # graphene HNEMD; EMD vs NEMD silicon; 16-metal NEP, all name GPUMD as the engine
    "kaldo": {"methods": ["10.1038/s41467-019-11572-4", "10.1103/PhysRevB.48.12581"],  # QHGK (Isaeva 2019); Allen-Feldman
              "applications": ["10.1038/s41524-023-01116-2", "10.1103/PhysRevB.103.024204"]},  # finite-size scaling in glasses; amorphous alloys, both computed with kALDo
    "shengbte": {"methods": ["10.1016/0921-4526(95)00016-3"],  # iterative BTE (Omini and Sparavigna 1995)
                 "applications": ["10.1103/PhysRevLett.113.185501", "10.1039/c4cp04858j", "10.1038/s41567-019-0520-x"]},  # compressive sensing lattice dynamics; phosphorene; Wigner transport in glasses, all run ShengBTE
    "phono3py": {"methods": ["10.1103/PhysRevLett.110.265506"],  # direct solution of the BTE (Chaput 2013)
                 "applications": ["10.1103/PhysRevX.12.041011", "10.1039/c8cp00350e"]},  # Wigner formulation implemented in phono3py; Janus MoSSe with phono3py
    "phonopy": {"applications": ["10.1103/PhysRevB.92.144308", "10.1039/c6cp03474h"]},  # MAPbI3 lattice dynamics; dynamic disorder in hybrid perovskites, both with phonopy
    "amset": {"applications": ["10.1021/acsenergylett.2c01464", "10.1038/s41524-021-00521-9"]},  # band versus polaron mobilities; Cs3Cu2I5, both with AMSET
    "ase": {"applications": ["10.1088/2053-1583/aacfc1", "10.1038/s41467-022-29939-5"]},  # C2DB workflow in ASE; NequIP forces through ASE
    "xtb": {"methods": ["10.1021/acs.jctc.9b00143"]},  # xtb's own metadynamics on GFN2-xTB (Grimme 2019); CREST is a separate program and stays out
    "plumed": {"applications": ["10.1103/PhysRevLett.104.190601", "10.1073/pnas.1303186110", "10.1103/PhysRevLett.111.230602", "10.1073/pnas.1811056115"]},  # well-tempered ensemble; funnel metadynamics; infrequent metadynamics; polymorph prediction
    "i-pi": {"applications": ["10.1063/1.4883861", "10.1063/1.4971438", "10.1073/pnas.1815117116"]},  # TRPMD; high-order PIMD; ab initio water thermodynamics
    "mp-api": {"applications": ["10.1126/sciadv.1600225", "10.1126/sciadv.aaq0148", "10.1038/s41524-020-00362-y"]},  # metastability scale; synthesis limit; stability predictions, all on Materials Project data
    "pymatgen-analysis-diffusion": {"applications": ["10.1021/acs.chemmater.5b04013", "10.1038/ncomms11009", "10.1021/acs.chemmater.5b03656"]},  # Na3PSe4 (Ceder group); Na10SnP2S12, pymatgen named for the MSD fit; Na3PS4 (Ong group)
    "rxn-network": {"applications": ["10.1021/jacs.1c06229", "10.1021/acscentsci.3c01051"]},
    "matgl": {"applications": ["10.1038/s41524-024-01500-6"]},  # fine-tuning universal potentials, benchmarks M3GNet-matgl and CHGNet-matgl
    "fairchem": {"code": ["10.48550/arXiv.2410.12771"], "applications": ["10.1038/s41524-023-01121-5"]},  # OMat24; AdsorbML with the OCP pretrained checkpoints
    "pycalphad": {"applications": ["10.1557/mrc.2019.59"]},  # ESPEI, pycalphad as the thermodynamic engine, applied to Cu-Mg
    "pymatgen": {"applications": ["10.1126/sciadv.1600225", "10.1126/sciadv.aaq0148"]},  # metastability scale (pymatgen input sets, substitutions); synthesis limit (pymatgen workflow)
    "mattergen": {"applications": ["10.1021/acs.jpclett.6c01568", "10.1016/j.jpowsour.2026.240034", "10.1002/batt.202500309", "10.1039/d5mh00010f"]},  # Li-Ga-Sn phase diagrams; garnet conductors; battery chemical space; Szymanski-Bartel benchmark (full text: MatterGen run and retrained)
    "diffcsp": {"applications": ["10.1038/s41524-026-02117-7", "10.1016/j.patter.2026.101537", "10.1038/s41563-025-02355-y"]},  # guided diffusion for superconductors (DiffCSP pretrained and fine-tuned); diffusion models in unexplored chemical space; SCIGEN on DiffCSP  # YMnO3 selectivity, enumerated with the reaction-network package; thermodynamic selectivity with experiments
}
EXCLUDE_APPLICATIONS_REVIEWS = {  # reviews, perspectives and overviews that cite a code without using it
    "10.1063/5.0055593": "review of thermal transport in defective materials, kALDo in the references only (Hanus 2021)",
    "10.1007/s40766-023-00041-w": "review of non-Fourier transport, kALDo in the references only (Benenti 2023)",
    "10.1038/s41563-021-00918-3": "review of phonon-engineered materials, ShengBTE in the references only (Qian 2021)",
    "10.1038/s41524-023-01107-3": "EPW review, AMSET named among alternative codes (Lee 2023)",
    "10.1063/1.5064602": "tutorial review of phonon frameworks, no ASE-driven calculation (McGaughey 2019)",
    "10.1063/5.0069175": "perspective, paywalled, GPUMD use not verifiable (Gu 2021)",
    "10.1038/s41586-023-06735-9": "GNoME trains its own network; M3GNet appears as a baseline only (Merchant 2023)",
    "10.1038/s43246-022-00315-6": "review of graph neural networks, OC20 named as a dataset (Reiser 2022)",
    "10.1038/s41524-022-00734-6": "review of deep learning methods, Open Catalyst in passing (Choudhary 2022)",
    "10.1038/s41586-023-06221-2": "perspective on AI in science, OC20 in the references only (Wang 2023)",
    "10.1016/j.softx.2015.06.001": "GROMACS software paper (Abraham 2015)",
    "10.1088/1361-648x/ab4007": "QuantumATK software paper (Smidstrup 2019)",
    "10.1063/1.5143190": "DFTB+ software paper (Hourahine 2020)",
    "10.1016/j.actamat.2020.08.008": "review of computational thermodynamics, pycalphad among the references (Liu 2020)",
    "10.1016/j.actamat.2020.10.043": "high-entropy oxide thermodynamics review, no CALPHAD computation stated (McCormack 2021)",
    "10.1039/c7ee03364h": "lattice-dynamics descriptor study; package use not verifiable, full text closed (Muy 2018)",
    "10.1103/physrevlett.115.205901": "screening on Materials Project data; pymatgen cited next to the data, no use statement (Seko 2015)",
    "10.1016/j.neuron.2018.08.011": "review (Molecular Dynamics Simulation for All), not an OpenMM study",
    "10.1002/aenm.201800035": "review of solid electrolyte design strategies (Park 2018)",
    "10.1038/s41578-019-0157-5": "review of interface stability in solid-state batteries (Xiao 2019)",
    "10.1016/j.esci.2022.02.008": "review of solid-state lithium batteries (Guo 2022)",
    "10.1007/s10853-022-06915-4": "review of computational synthesis prediction (Bartel 2022)",
    "10.1021/acs.chemrev.1c00637": "review of solid-state reaction synthesis (Kumar 2022)",
    "10.1021/acs.chemrev.4c00055": "review of self-driving laboratories (Tom 2024)",
    "10.1038/s41563-025-02272-0": "Materials Project overview, cites many codes (Horton 2025)",
    "10.1021/acsnano.5c04200": "review of AI for materials discovery (Madika 2025)",
    "10.1016/j.matt.2025.102138": "review of AI for catalyst design (Zhang 2025)",
    "10.1038/s41563-025-02403-7": "review of AI-driven materials design (Cheng 2026)",
    "10.1038/s41586-025-09269-4": "hydrogel design paper, a passing citation (Liao 2025)",
    "10.1038/s41524-024-01443-y": "a competing generative model (Luo 2024)",
    "10.1016/j.matt.2024.05.017": "perspective on generative models (Park 2024)",
    "10.1016/j.cocom.2025.e01139": "review of machine learning materials discovery (Nematov 2025)",
    "10.1002/aenm.202403876": "review of machine learning multiscale design (Mortazavi 2025)",
    "10.1080/09506608.2019.1709354": "review of additive manufacturing (Reichardt 2021)",
    "10.1016/j.mser.2021.100645": "review of high-entropy alloy studies (Huang 2022)",
    "10.1038/s41563-025-02272-0": "Materials Project overview, cites many codes (Horton 2025)",
}
# Never exported as an application: a paper that cites the code but is another tool's software or
# method paper, a dataset, or a review, found in the 2026-10-28 physics review. Kept here rather
# than in Zotero so a re-export stays consistent; the Zotero items carry the tag "not-an-application".
EXCLUDE_PER_CODE = {  # a paper that uses another code of the roster: (code key, doi) pairs
    ("phono3py", "10.1103/physrevb.92.144308"): "harmonic phonons with phonopy, no lifetimes (Brivio 2015)",
    ("phono3py", "10.1039/c6cp03474h"): "finite displacements with phonopy, lifetimes measured by Raman (Leguy 2016)",
}
EXCLUDE_APPLICATIONS = {
    "10.1103/physrevb.73.155114": "CASTEP DFPT paper (Refson 2006), not a VASP study",
    "10.1063/5.0155600": "DeePMD-kit software paper",
    "10.1021/acs.jctc.9b00143": "xtb metadynamics (Grimme 2019), does not use PLUMED (it is an xtb methods paper, see CURATED)",
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


def _clean_title(title: str) -> str:
    """Registry titles carry MathML and HTML; em and en dashes become colon and hyphen, the site's house style."""
    import re
    t = re.sub(r"<[^>]+>", " ", title)
    return " ".join(t.replace(chr(0x2014), ": ").replace(chr(0x2013), "-").replace(" :", ":").split())


def _entry_from_doi(db: sqlite3.Connection, doi: str, prefer_registry: bool = False) -> dict | None:
    """The Zotero item with this DOI, or the doi.org CSL record when the library lacks it (or when asked)."""
    row = None if prefer_registry else db.execute(
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
               if a.get("family") else a.get("name", "").strip()  # a consortium is a literal name
               for a in csl.get("author", []) if a.get("family") or a.get("name")]
    return {"doi": doi, "title": _clean_title(str(csl.get("title", ""))), "authors": authors, "year": year,
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
        "title": _clean_title(title),
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
                if e and group == "applications" and (e["doi"].lower() in {*EXCLUDE_APPLICATIONS, *EXCLUDE_APPLICATIONS_REVIEWS}
                                                      or (key, e["doi"].lower()) in EXCLUDE_PER_CODE):
                    continue
                if e:  # the registry record is the reference of record; Zotero's copy can carry a PDF's embedded metadata
                    try:
                        e = _entry_from_doi(db, e["doi"], prefer_registry=True) or e
                    except Exception as err:  # offline: keep the Zotero record and say so
                        print(f"registry lookup failed for {e['doi']}: {err}", file=sys.stderr)
                if e and e["doi"].lower() not in {x["doi"].lower() for x in groups[group]}:
                    groups[group].append(e)
        for group, dois in CURATED.get(key, {}).items():
            for doi in dois:
                if doi.lower() not in {x["doi"].lower() for x in groups[group]}:
                    e = _entry_from_doi(db, doi, prefer_registry=True)  # curated DOIs take the registry record
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
