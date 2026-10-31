"""Auxiliary formulas are pinned per edge uid (issue 217).

An edge's uid hashes its main formula, not its auxiliary formulas, yet a code
that claims an operator must implement both (omai/operator/operator.py). An
auxiliary edit under an unchanged uid is therefore a silent change of what the
pinned uid means to every consumer that pins it. This test makes such an edit
deliberate: it fails until the pin below is regenerated and the CHANGELOG
names the edge and what moved.

Regenerate: python tests/test_auxiliary_formula_pins.py --write
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

PINS = pathlib.Path(__file__).parent / "fixtures" / "auxiliary_formula_pins.json"


def _current() -> dict[str, dict[str, str]]:
    from omai.map_data import DOMAINS
    from omai.operator.identity import edge_id, formula_fingerprint, node_id

    out: dict[str, dict[str, str]] = {}
    for domain in DOMAINS:
        for op in domain.edges:
            if not op.auxiliary_formulas:
                continue
            text = "\n".join(formula_fingerprint(f) for f in op.auxiliary_formulas)
            out[edge_id(op, node_id)] = {
                "name": op.name,
                "auxiliary_sha256": hashlib.sha256(text.encode()).hexdigest(),
            }
    return dict(sorted(out.items()))


def test_auxiliary_formulas_match_their_pins():
    pinned = json.loads(PINS.read_text())
    current = _current()
    moved = [
        f"{v['name']} ({uid[:12]})"
        for uid, v in current.items()
        if uid in pinned and pinned[uid]["auxiliary_sha256"] != v["auxiliary_sha256"]
    ]
    assert not moved, (
        "auxiliary formula changed under an unchanged uid: " + ", ".join(moved)
        + "; run python tests/test_auxiliary_formula_pins.py --write and name the edge and the change in CHANGELOG.md"
    )
    assert set(current) == set(pinned), (
        "edges with auxiliary formulas differ from the pins (added, re-minted or removed): "
        + ", ".join(sorted(f"{u[:12]}" for u in set(current) ^ set(pinned)))
        + "; run python tests/test_auxiliary_formula_pins.py --write"
    )


if __name__ == "__main__" and sys.argv[1:] == ["--write"]:
    PINS.write_text(json.dumps(_current(), indent=1) + "\n")
    print(f"wrote {PINS}")
