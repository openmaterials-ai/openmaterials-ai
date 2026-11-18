"""The counts the specification (docs/openmaterials.tex) states in prose and tables equal the data.

The tex is written by hand, so a count in it goes stale when the map grows: in November 2026 the
code table still gave GPUMD 13 quantities after MeanPotentialEnergy made it 14, and one section
still said 131 nodes with a dimension after the map reached 132. These tests recompute each count
from docs/data and fail when the text and the data disagree.
"""

import json
import re
from pathlib import Path

from omai.representation.credits import CODE_CREDITS

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"
TEX = (ROOT / "docs" / "openmaterials.tex").read_text()


def _data(name):
    return json.loads((DATA / name).read_text())


def test_dimension_counts_equal_the_lean_data():
    nodes = len(_data("graph.json")["nodes"])
    dimensioned = len(_data("lean.json")["nodes"])
    flat = re.sub(r"\s+", " ", TEX)
    stated = [int(n) for n in re.findall(r"the (\d+) map nodes with dimensional content", flat)]
    pairs = [(int(a), int(b)) for a, b in re.findall(r"dimension of (\d+) of the (\d+) nodes", flat)]
    assert stated and pairs, "the tex no longer states the dimension counts this test reads"
    assert set(stated) == {dimensioned}, (stated, dimensioned)
    assert set(pairs) == {(dimensioned, nodes)}, (pairs, (dimensioned, nodes))


def _table_key(name: str) -> str:
    name = re.sub(r"\s*\(.*\)$", "", name).strip().lower()
    for key, credit in CODE_CREDITS.items():
        if name in (key, (credit.get("name") or "").lower()):
            return key
    raise AssertionError(f"code table row {name!r} names no code in CODE_CREDITS")


def test_code_table_counts_equal_codes_json():
    codes = _data("codes.json")
    rows = re.findall(r"^([A-Za-z][\w .()+-]*?)\s+&\s+(\d+)\s+&\s+[^\n]*\\\\$", TEX, re.M)
    table = {_table_key(name): int(n) for name, n in rows}
    assert set(table) == set(codes), (sorted(set(codes) - set(table)), sorted(set(table) - set(codes)))
    wrong = {k: (table[k], len(codes[k])) for k in table if table[k] != len(codes[k])}
    assert not wrong, f"code table count != codes.json (table, data): {wrong}"
