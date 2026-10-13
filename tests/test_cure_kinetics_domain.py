"""Cure-kinetics domain: neutral nodes, the Kamal-Sourour conversion, the DiBenedetto T_g.

Rosetti, Alcouffe, Pascault, Gérard, Lortie, Materials 11, 1960 (2018),
doi:10.3390/ma11101960, CC BY 4.0, gives a consistency check, not a prediction.
p. 6: "it was impossible to experimentally determine a value of ΔCp∞. Thus the
parameter λ was determined by fitting the Di Benedetto curve to the experimental
points", and λ = ΔCp∞/ΔCp0. Table 1 (p. 7) lists x = 0 (measured) and x = 1
(calculated) values: T_g0 = -10.8 °C, ΔCp0 = 0.53; T_g∞ = 216 °C, ΔCp∞ = 0.27
J/(g K). The printed points lie on that fitted curve: x_gel = 0.45 -> gel T_g =
55 °C (p. 7), and Table 2 (p. 8), whose x "are evaluated from the Di Benedetto
curve": 0.55, 0.74, 0.85 -> 75, 122, 156 °C.
"""
from __future__ import annotations

import json
from pathlib import Path

import sympy as sp

from omai.cure_kinetics.operator import EDGES, NODES
from omai.gates import validate_contribution
from omai.map_data import DOMAINS, build_graph_dict
from omai.operator.dimcheck import dimensional_report
from omai.operator.identity import edge_id, node_id
from omai.operator.registry import QUANTITY_TAGS
from omai.semantics import build_semantics, resolve
from omai.store import Store

_EDGES = {op.name: op for op in EDGES}
_MAP = Path(__file__).resolve().parents[1] / "map"
_K = 273.15
_ROSETTI = ((0.45, 55), (0.55, 75), (0.74, 122), (0.85, 156))  # (x, printed T_g in °C)


def _symbols(expr):
    return {s.name: s for s in expr.free_symbols}


def _dibenedetto():
    rhs = _EDGES["dibenedetto_glass_transition"].formula.rhs
    s = _symbols(rhs)
    return rhs, s[r"\alpha_{cure}"], s[r"\lambda_{DiB}"], s["T_{g0}"], s[r"T_{g\infty}"]


def test_dibenedetto_endpoints_and_slopes():
    # End slopes lambda (T_g_inf - T_g0) and (T_g_inf - T_g0) / lambda pin the convention.
    f, a, lam, tg0, tginf = _dibenedetto()
    df = sp.diff(f, a)
    assert sp.simplify(f.subs(a, 0) - tg0) == 0
    assert sp.simplify(f.subs(a, 1) - tginf) == 0
    assert sp.simplify(df.subs(a, 0) - lam * (tginf - tg0)) == 0
    assert sp.simplify(df.subs(a, 1) - (tginf - tg0) / lam) == 0


def test_dibenedetto_matches_the_rosetti_curve():
    f, a, lam, tg0, tginf = _dibenedetto()
    curve = f.subs({tg0: -10.8 + _K, tginf: 216 + _K, lam: sp.Rational(27, 53)})
    for x, tg in _ROSETTI:
        # 2 K is tighter than the printed precision: x to 0.01 alone is 1.7 K at 0.85.
        assert abs(float(curve.subs(a, x)) - (tg + _K)) < 2


def test_kamal_edge_is_the_isothermal_rate_law():
    f = _EDGES["kamal_cure_conversion"].formula
    s = _symbols(f)
    a = s[r"\alpha_{cure}"]
    rt = s["N_A"] * s["k_B"] * s["T"]
    k1 = s["A_{1,cure}"] * sp.exp(-s["E_{1,cure}"] / rt)
    k2 = s["A_{2,cure}"] * sp.exp(-s["E_{2,cure}"] / rt)
    rate = (k1 + k2 * a ** s["m_{cure}"]) * (1 - a) ** s["n_{cure}"]
    assert sp.simplify(sp.diff(f.rhs, a) * rate) == 1  # dt/d alpha = 1 / rate
    assert f.rhs.subs(a, s[r"\alpha_{0,cure}"]).is_zero  # t = 0 at the initial conversion


def test_both_edges_are_dimension_proven():
    rep = dimensional_report([], list(EDGES))
    assert set(rep["ok"]) == set(_EDGES)


def test_neutral_nodes_and_method_schemes():
    assert [n.name for n in NODES] == ["CureConversion", "GlassTransitionTemperature"]
    assert not any(n.labels for n in NODES)
    assert {"cure_conversion", "glass_transition_temperature"} <= set(QUANTITY_TAGS)
    kamal, dib = _EDGES["kamal_cure_conversion"], _EDGES["dibenedetto_glass_transition"]
    assert kamal.schemes == {"method": "kamal_sourour"}
    assert dib.schemes == {"method": "dibenedetto_pascault_williams"}
    assert [i.name for i in kamal.inputs] == ["Temperature"]
    assert dib.inputs == kamal.outputs


def test_aliases_resolve():
    sem = build_semantics(build_graph_dict(DOMAINS))
    for q in ("degree of cure", "extent-of-cure"):
        assert resolve(q, sem)[0]["id"] == "CureConversion"
    assert resolve("glass transition temperature", sem)[0]["id"] == "GlassTransitionTemperature"
    assert {h["id"] for h in resolve("cure-kinetics", sem)} == {
        "CureConversion", "GlassTransitionTemperature",
        "kamal_cure_conversion", "dibenedetto_glass_transition"}


def test_the_cure_records_pass_the_gates_on_the_store_before_them():
    log = [json.loads(line) for line in (_MAP / "log.jsonl").read_text().splitlines()]
    uids = [node_id(n) for n in NODES] + [edge_id(op, node_id) for op in EDGES]
    first = next(i for i, r in enumerate(log) if r["payload"].get("uid") == uids[0])
    new = log[first:first + len(uids)]
    assert [r["payload"]["uid"] for r in new] == uids
    assert [r["op"] for r in new] == ["add_node"] * 2 + ["add_edge"] * 2
    before = Store(_MAP).read(log[first - 1]["version"])
    records = [{"op": r["op"], "payload": r["payload"]} for r in new]
    assert validate_contribution(records, before) == []
