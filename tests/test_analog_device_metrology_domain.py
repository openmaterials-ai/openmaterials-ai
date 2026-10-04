"""Tests for the analog-device-metrology contribution (records 250-257).

A definitional domain: the conductance family of analog resistive devices, four
nodes and four closed-form edges the dimensional gate proves and apply_edge
runs. It connects to the map through ElectricalConductivity[carrier=electronic].
No code representation and no measured value attach yet.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from omai.map_data import DOMAINS, build_graph_dict
from omai.operator.dimcheck import dimensional_report
from omai.operator.identity import edge_id, node_id, node_identity
from omai.operator.validate import validate_dag
from omai.representation.executor import _dimensional_bridge, apply_edge, operator_form_spec
from omai.representation.instance import Representation

_REPO = Path(__file__).resolve().parents[1]

_NODES = {
    "ConductanceState": "conductance_state",
    "ConductanceWindow": "conductance_window",
    "ConductanceDriftExponent": "conductance_drift_exponent",
    "StateCoefficientOfVariation": "state_coefficient_of_variation",
}
_EDGES = (
    "contract_device_conductance",
    "contract_conductance_window",
    "contract_state_coefficient_of_variation",
    "apply_conductance_drift",
)


def _all_nodes_edges():
    nodes, edges, seen_n, seen_e = [], [], set(), set()
    for d in DOMAINS:
        for s in d.nodes:
            if s.name not in seen_n:
                seen_n.add(s.name)
                nodes.append(s)
        for op in d.edges:
            if op.name not in seen_e:
                seen_e.add(op.name)
                edges.append(op)
    return nodes, edges


def _rep(space, symbol, data):
    return Representation(space_adapter_spec=operator_form_spec(space),
                          observable_name=symbol, data=np.asarray(data), is_operator=True)


def test_the_four_nodes_and_four_edges():
    from omai.analog_device_metrology.operator import EDGES, NODES

    assert [s.name for s in NODES] == list(_NODES)
    assert [op.name for op in EDGES] == list(_EDGES)
    for s in NODES:
        assert node_identity(s)["quantity"] == _NODES[s.name], s.name
        assert s.labels == {} and "[" not in s.name, s.name
    assert len({node_id(s) for s in NODES}) == 4


def test_conductance_is_the_siemens_and_not_a_conductivity():
    from omai.analog_device_metrology.operator.nodes import CONDUCTANCE_STATE
    from omai.electronic_transport.operator.nodes import ELECTRICAL_CONDUCTIVITY_ELECTRONIC
    from omai.operator.dimensions import CONDUCTANCE, DIMENSIONS, ELECTRICAL_CONDUCTIVITY, LENGTH
    from omai.representation.units import UNITS, dimension_si_scale

    assert CONDUCTANCE.exponents == (-1, -2, 3, 0, 0, 2, 0)
    assert (ELECTRICAL_CONDUCTIVITY * LENGTH).exponents == CONDUCTANCE.exponents
    assert sum(d.exponents == CONDUCTANCE.exponents for d in DIMENSIONS.values()) == 1
    assert UNITS["siemens"].dimension == CONDUCTANCE and dimension_si_scale(CONDUCTANCE) == 1.0
    sigma = ELECTRICAL_CONDUCTIVITY_ELECTRONIC.fields[0].dimension
    assert CONDUCTANCE_STATE.fields[0].dimension.exponents != sigma.exponents


def test_every_edge_is_dimensionally_proven_and_bridged():
    from omai.analog_device_metrology.operator import EDGES

    report = dimensional_report(*_all_nodes_edges())
    for op in EDGES:
        assert op.name in report["ok"], (op.name, report)
        assert op.is_executable_in_sympy, op.name
        bridge = _dimensional_bridge(op)
        assert np.isfinite(bridge) and bridge > 0, op.name


def test_device_conductance_executes():
    from omai.analog_device_metrology.operator.edges import contract_device_conductance
    from omai.electronic_transport.operator.nodes import ELECTRICAL_CONDUCTIVITY_ELECTRONIC

    # sigma 100 S/m, A = 1e8 A^2, L = 5e3 A: G = 100 * 1e-12 / 5e-7 = 2e-4 S.
    out = apply_edge(contract_device_conductance,
                     _rep(ELECTRICAL_CONDUCTIVITY_ELECTRONIC, "sigma", 100.0),
                     constants={"A_g": 1e8, "L_g": 5e3})
    assert out.space.name == "ConductanceState"
    np.testing.assert_allclose(float(out.data), 2e-4, rtol=1e-12)


def test_the_two_ratios_execute():
    from omai.analog_device_metrology.operator import edges as E
    from omai.analog_device_metrology.operator.nodes import CONDUCTANCE_STATE

    g = _rep(CONDUCTANCE_STATE, "G_c", 1e-6)
    cases = [(E.contract_conductance_window, {"G_min": 2.5e-7}, "ConductanceWindow", 4.0),
             (E.contract_state_coefficient_of_variation, {r"\sigma_G": 5e-8},
              "StateCoefficientOfVariation", 0.05)]
    for op, constants, name, want in cases:
        out = apply_edge(op, g, constants=constants)
        assert out.space.name == name
        np.testing.assert_allclose(float(out.data), want, rtol=1e-12)


def test_conductance_drift_executes_with_g0_as_a_parameter():
    from omai.analog_device_metrology.operator.edges import apply_conductance_drift
    from omai.analog_device_metrology.operator.nodes import CONDUCTANCE_DRIFT_EXPONENT

    assert [s.name for s in apply_conductance_drift.inputs] == ["ConductanceDriftExponent"]
    out = apply_edge(apply_conductance_drift, _rep(CONDUCTANCE_DRIFT_EXPONENT, "nu", 0.1),
                     constants={"G_0": 1e-4, "t_d": 100.0, "t_{d,0}": 1.0})
    np.testing.assert_allclose(float(out.data), 1e-4 * 100.0 ** -0.1, rtol=1e-12)


def test_every_operand_is_an_input_symbol_or_a_parameter():
    from omai.analog_device_metrology.operator import EDGES
    from omai.operator.vocabulary import FORMULA_CONSTANTS, SPACE_SYMBOLS

    for op in EDGES:
        allowed = set(FORMULA_CONSTANTS) | {p.name for p in op.parameters}
        for inp in op.inputs:
            allowed |= set(SPACE_SYMBOLS.get(inp.name, frozenset()))
        for sym in op.formula.rhs.free_symbols:
            assert sym.name in allowed, (op.name, sym.name)


def test_the_quantity_tags_are_registered():
    from omai.operator.registry import QUANTITY_TAGS

    for tag in _NODES.values():
        assert QUANTITY_TAGS.get(tag), tag


def test_validate_dag_is_clean_and_the_tier_exists():
    assert validate_dag(*_all_nodes_edges()) == []
    g = build_graph_dict(DOMAINS)
    tier_of = {n["id"]: n["tier"] for n in g["nodes"]}
    for name in _NODES:
        assert tier_of[name] == "Analog device metrology", name


def test_contribution_connects_through_the_electronic_conductivity():
    from omai.analog_device_metrology.operator import EDGES, NODES
    from omai.electronic_transport.operator.nodes import ELECTRICAL_CONDUCTIVITY_ELECTRONIC
    from omai.gates import validate_contribution
    from omai.genesis import _formula_srepr
    from omai.operator.identity import edge_identity

    records = [{"op": "add_node", "payload": {"uid": node_id(s), "identity": node_identity(s),
                                              "meta": {"name": s.name}}} for s in NODES]
    records += [{"op": "add_edge", "payload": {
        "uid": edge_id(op, node_id), "identity": edge_identity(op, node_id),
        "meta": {"name": op.name, "schemes": op.schemes,
                 "formula_srepr": _formula_srepr(op.formula)}}} for op in EDGES]
    sigma = ELECTRICAL_CONDUCTIVITY_ELECTRONIC
    current = {"nodes": {node_id(sigma): {"uid": node_id(sigma), "identity": node_identity(sigma),
                                          "meta": {}}}, "edges": {}}
    assert validate_contribution(records, current) == []


def test_semantic_aliases_resolve_to_the_nodes():
    from omai.semantics import resolve

    sem = json.loads((_REPO / "docs" / "data" / "semantics.json").read_text())
    for phrase, node in {"conductance state": "ConductanceState",
                         "electrical conductance": "ConductanceState",
                         "on off ratio": "ConductanceWindow",
                         "LTP window": "ConductanceWindow",
                         "conductance drift": "ConductanceDriftExponent",
                         "conductance coefficient of variation": "StateCoefficientOfVariation",
                         }.items():
        hits = resolve(phrase, sem, limit=3)
        assert any(h["id"] == node for h in hits), (phrase, hits)


def test_no_representation_and_no_instance_attaches():
    import omai.analog_device_metrology.representation as rep
    from omai.representation.adapter import SpaceRepresentationSpec

    assert not any(isinstance(v, SpaceRepresentationSpec) for v in vars(rep).values())
    insts = json.loads((_REPO / "docs" / "data" / "instances.json").read_text())
    assert not any(i.get("variable") in _NODES for i in insts)


def test_committed_store_holds_records_250_to_257():
    """Records 250-257 are the four add_node then the four add_edge of the
    contribution, with the domain's uids; records 1-249 are untouched."""
    from omai.analog_device_metrology.operator import EDGES, NODES
    from omai.store import Store

    m = Store(_REPO / "map").read()
    lines = (_REPO / "map" / "log.jsonl").read_text().splitlines()
    assert len(lines) >= 257
    recs = [json.loads(line) for line in lines[249:257]]
    assert [r["op"] for r in recs] == ["add_node"] * 4 + ["add_edge"] * 4
    assert [r["payload"]["uid"] for r in recs[:4]] == [node_id(s) for s in NODES]
    assert [r["payload"]["uid"] for r in recs[4:]] == [edge_id(op, node_id) for op in EDGES]
    for op in EDGES:
        assert not m["edges"][edge_id(op, node_id)].get("superseded_by"), op.name
