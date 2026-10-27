"""Held-out fit errors and the committee force-spread exceedance of a fitted
potential (2026-10-23): two contributions, records 290-295 and 296-297, each
passing the gates on the store before it. Positions are history and never move.
"""
from __future__ import annotations

import json
from pathlib import Path

from omai.dft_ground_state.operator.edges import (
    compute_potential_energy_fit_error,
    compute_potential_force_fit_error,
    compute_potential_virial_fit_error,
)
from omai.dft_ground_state.operator.nodes import (
    POTENTIAL_ENERGY_FIT_ERROR,
    POTENTIAL_FORCE_FIT_ERROR,
    POTENTIAL_VIRIAL_FIT_ERROR,
)
from omai.gates import validate_contribution
from omai.map_data import DOMAINS, build_graph_dict
from omai.operator.identity import edge_id, node_id
from omai.operator.registry import quantity_tag_for
from omai.semantics import build_semantics, resolve
from omai.store import Store
from omai.thermal_transport.operator.edges import compute_potential_uncertainty_exceedance
from omai.thermal_transport.operator.nodes import POTENTIAL_UNCERTAINTY_EXCEEDANCE

_MAP = Path(__file__).resolve().parents[1] / "map"
_SEQ_289 = "baf99346621bee3269400670c5044dac03c89e0bf7cd0dff673593344540852c"
_SEQ_295 = "d8096810100c5916139d0f5c477d4b936c9f94b060f55b36a0b355f27ea3c68a"
_SEQ_297 = "9476086d423e60b00ef1ff94f5152046f405b86096ba31949a0cc8021917fd68"
_FIT_NODES = (POTENTIAL_ENERGY_FIT_ERROR, POTENTIAL_FORCE_FIT_ERROR, POTENTIAL_VIRIAL_FIT_ERROR)
_FIT_EDGES = (compute_potential_energy_fit_error, compute_potential_force_fit_error,
              compute_potential_virial_fit_error)


def _records(first: int, last: int) -> list[dict]:
    lines = (_MAP / "log.jsonl").read_text().splitlines()
    assert len(lines) >= last, "the contribution has not landed"
    return [json.loads(line) for line in lines[first - 1:last]]


def _passes_gates_on(recs: list[dict], head: str) -> None:
    assert recs[0]["prev"] == head
    contribution = [{"op": r["op"], "payload": r["payload"]} for r in recs]
    assert validate_contribution(contribution, Store(_MAP).read(head)) == []


def test_fit_error_contribution_is_records_290_to_295():
    recs = _records(290, 295)
    assert [r["op"] for r in recs] == ["add_node"] * 3 + ["add_edge"] * 3
    assert [r["payload"]["uid"] for r in recs] == (
        [node_id(n) for n in _FIT_NODES] + [edge_id(op, node_id) for op in _FIT_EDGES])
    assert recs[-1]["version"] == _SEQ_295
    _passes_gates_on(recs, _SEQ_289)
    # One field, one quantity tag per node; each edge reads only its own label.
    assert [len(n.fields) for n in _FIT_NODES] == [1, 1, 1]
    assert len({quantity_tag_for(n.name) for n in _FIT_NODES}) == 3
    assert [op.inputs[1].name for op in _FIT_EDGES] == ["TotalEnergy", "Forces", "Stress"]


def test_exceedance_contribution_is_records_296_to_297():
    recs = _records(296, 297)
    assert [r["op"] for r in recs] == ["add_node", "add_edge"]
    assert [r["payload"]["uid"] for r in recs] == [
        node_id(POTENTIAL_UNCERTAINTY_EXCEEDANCE),
        edge_id(compute_potential_uncertainty_exceedance, node_id)]
    assert recs[-1]["version"] == _SEQ_297
    _passes_gates_on(recs, _SEQ_295)


def test_aliases_resolve():
    sem = build_semantics(build_graph_dict(DOMAINS))
    fit = {n.name for n in _FIT_NODES}
    for q in ("validation RMSE", "test-set RMSE", "holdout error"):
        assert {h["id"] for h in resolve(q, sem)[:3]} == fit
    for q in ("model deviation", "query by committee"):
        assert resolve(q, sem)[0]["id"] == POTENTIAL_UNCERTAINTY_EXCEEDANCE.name
