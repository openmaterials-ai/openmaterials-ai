"""Tests for the analog-device-metrology contributions (records 250-257, 258-259,
260-267 and 268-271).

A definitional domain: the conductance family of analog resistive devices, the
error of an analog dot product, the contact barrier with the work function and
electron affinity that set it, and the energy of a programming pulse; nine nodes
and eight closed-form edges the dimensional gate proves and apply_edge runs. It
connects to the map through ElectricalConductivity[carrier=electronic]. No code
representation attaches; two measured work functions (Hou et al. 2025) do.
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
    "DotProductError": "dot_product_error",
    "SchottkyBarrierHeight[band_carrier=electron]": "schottky_barrier_height",
    "WorkFunction": "work_function",
    "ElectronAffinity": "electron_affinity",
    "ProgrammingPulseEnergy": "programming_pulse_energy",
    "SetVoltage": "set_voltage",
    "RetentionTime": "retention_time",
}
_EDGES = (
    "contract_device_conductance",
    "contract_conductance_window",
    "contract_state_coefficient_of_variation",
    "apply_conductance_drift",
    "propagate_programming_error",
    "emit_thermionic_conductance",
    "schottky_mott_barrier",
    "dissipate_pulse_energy",
    "ramp_set_voltage",
    "zero_bias_retention",
)
_EV = 1.602176634e-19  # J; ENERGY values enter in the canonical joule
_KB = 1.380649e-23  # J/K


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


def test_the_eleven_nodes_and_ten_edges():
    from omai.analog_device_metrology.operator import EDGES, NODES

    assert [s.name for s in NODES] == list(_NODES)
    assert [op.name for op in EDGES] == list(_EDGES)
    for s in NODES:
        assert node_identity(s)["quantity"] == _NODES[s.name], s.name
        want = {"band_carrier": "electron"} if s.name.startswith("SchottkyBarrierHeight") else {}
        assert s.labels == want, s.name
    assert len({node_id(s) for s in NODES}) == 11


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


def test_contribution_connects_through_conductivity_and_temperature():
    from omai.analog_device_metrology.operator import EDGES, NODES
    from omai.electronic_transport.operator.nodes import ELECTRICAL_CONDUCTIVITY_ELECTRONIC
    from omai.gates import validate_contribution
    from omai.genesis import _formula_srepr
    from omai.operator.identity import edge_identity
    from omai.materials.operator.nodes import ACTIVATION_ENERGY
    from omai.thermal_transport.operator.nodes import TEMPERATURE_STATE

    records = [{"op": "add_node", "payload": {"uid": node_id(s), "identity": node_identity(s),
                                              "meta": {"name": s.name}}} for s in NODES]
    records += [{"op": "add_edge", "payload": {
        "uid": edge_id(op, node_id), "identity": edge_identity(op, node_id),
        "meta": {"name": op.name, "schemes": op.schemes,
                 "formula_srepr": _formula_srepr(op.formula)}}} for op in EDGES]
    current = {"nodes": {node_id(s): {"uid": node_id(s), "identity": node_identity(s), "meta": {}}
                         for s in (ELECTRICAL_CONDUCTIVITY_ELECTRONIC, TEMPERATURE_STATE,
                                   ACTIVATION_ENERGY)},
               "edges": {}}
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
                         "dot product error": "DotProductError",
                         "schottky barrier height": "SchottkyBarrierHeight[band_carrier=electron]",
                         "thermionic emission": "ConductanceState",
                         "work function": "WorkFunction",
                         "electron affinity": "ElectronAffinity",
                         "programming pulse energy": "ProgrammingPulseEnergy",
                         "switching energy": "ProgrammingPulseEnergy",
                         "set voltage": "SetVoltage",
                         "switching voltage": "SetVoltage",
                         "retention time": "RetentionTime",
                         }.items():
        hits = resolve(phrase, sem, limit=3)
        assert any(h["id"] == node for h in hits), (phrase, hits)


def test_no_representation_attaches_and_two_work_functions_do():
    import omai.analog_device_metrology.representation as rep
    from omai.representation.adapter import SpaceRepresentationSpec

    assert not any(isinstance(v, SpaceRepresentationSpec) for v in vars(rep).values())
    insts = json.loads((_REPO / "docs" / "data" / "instances.json").read_text())
    ours = [i for i in insts if i.get("variable") in _NODES]
    assert sorted((i["variable"], i["material"], i["value"], i["units"]) for i in ours) == [
        ("WorkFunction", "MoS2 (oxygen-plasma treated)", 3.94, "eV"),
        ("WorkFunction", "MoS2 (pristine)", 3.38, "eV")]
    for i in ours:
        assert i["source"]["kind"] == "measurement"
        assert i["source"]["ref"] == "paper:memtransistor-2025-hou"


def test_the_paper_record_pins_each_value_to_its_instance():
    from omai.analog_device_metrology.operator.nodes import WORK_FUNCTION

    paper = json.loads((_REPO / "index" / "papers" / "memtransistor-2025-hou.json").read_text())
    assert paper["paper"]["doi"] == "10.1038/s41467-025-64579-5"
    assert [v["value"] for v in paper["values"]] == [3.38, 3.94]
    for v in paper["values"]:
        inst = json.loads((_REPO / "docs" / "data" / "instances" / v["instance"]).read_text())
        assert inst["lineage"]["node"] == v["node_id"] == "WorkFunction"
        assert v["node_uid"] == node_id(WORK_FUNCTION)
        assert inst["lineage"]["values"] == {"value": v["value"], "units": v["units"]}
        assert v["quote"] in inst["source"]["detail"]


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
    assert [r["payload"]["uid"] for r in recs[:4]] == [node_id(s) for s in NODES[:4]]
    assert [r["payload"]["uid"] for r in recs[4:]] == [edge_id(op, node_id) for op in EDGES[:4]]
    for op in EDGES:
        assert not m["edges"][edge_id(op, node_id)].get("superseded_by"), op.name


def test_dot_product_error_closed_form():
    """The kernel-moment form equals c sqrt(sum (1/r + |w|)^2 / 2) / sum|w| over the
    nonzero weights, r = (W - 1) / max|w|: 0.3368, 0.375, 0.5069 for Prewitt,
    Sobel and Laplacian at W = 7, scaled by c."""
    from omai.analog_device_metrology.operator.edges import propagate_programming_error
    from omai.analog_device_metrology.operator.nodes import (
        CONDUCTANCE_WINDOW,
        STATE_COEFFICIENT_OF_VARIATION,
    )

    kernels = {(-1, -1, -1, 1, 1, 1): 0.3368, (-1, -2, -1, 1, 2, 1): 0.375, (1, 1, -4, 1, 1): 0.5069}
    for w, coef in kernels.items():
        a = [abs(x) for x in w]
        out = apply_edge(propagate_programming_error,
                         _rep(STATE_COEFFICIENT_OF_VARIATION, "c_G", 0.1),
                         _rep(CONDUCTANCE_WINDOW, "W_G", 7.0),
                         constants={"n_w": len(a), "w_max": max(a), "S_1": sum(a),
                                    "S_2": sum(x * x for x in a)})
        assert out.space.name == "DotProductError"
        np.testing.assert_allclose(float(out.data), 0.1 * coef, rtol=2e-4)


def test_committed_store_holds_records_258_and_259():
    """Record 258 adds DotProductError and record 259 its edge."""
    from omai.analog_device_metrology.operator.edges import propagate_programming_error
    from omai.analog_device_metrology.operator.nodes import DOT_PRODUCT_ERROR

    lines = (_REPO / "map" / "log.jsonl").read_text().splitlines()
    assert len(lines) >= 259
    recs = [json.loads(line) for line in lines[257:259]]
    assert [r["op"] for r in recs] == ["add_node", "add_edge"]
    assert recs[0]["payload"]["uid"] == node_id(DOT_PRODUCT_ERROR)
    assert recs[1]["payload"]["uid"] == edge_id(propagate_programming_error, node_id)


def test_the_root_in_the_dot_product_edge_is_not_a_rational_identity():
    from omai.analog_device_metrology.operator.edges import propagate_programming_error
    from omai.lean_roadmap import _classify

    assert _classify(propagate_programming_error)[0] == "special function"


def test_thermionic_conductance_executes_in_si():
    """G = P_th T q_e / k_B exp(-Phi_Bn / k_B T). Phi_Bn = 0.5 eV, T = 300 K and
    P_th = 1.2e-6 A/K^2 (A* = 120 A cm^-2 K^-2 on 1 um^2) give 1.6646e-8 S. The
    dimensional bridge does not rescale inside the exponential, so the barrier
    enters in joules and P_th in SI; T is the Temperature input."""
    from omai.analog_device_metrology.operator.edges import emit_thermionic_conductance
    from omai.analog_device_metrology.operator.nodes import SCHOTTKY_BARRIER_HEIGHT
    from omai.thermal_transport.operator.nodes import TEMPERATURE_STATE

    assert [s.name for s in emit_thermionic_conductance.inputs] == [
        "SchottkyBarrierHeight[band_carrier=electron]", "Temperature"]
    out = apply_edge(emit_thermionic_conductance, _rep(SCHOTTKY_BARRIER_HEIGHT, "Phi_Bn", 0.5 * _EV),
                     _rep(TEMPERATURE_STATE, "temperature", 300.0), constants={"P_th": 1.2e-6})
    assert out.space.name == "ConductanceState"
    want = 1.2e-6 * 300.0 * _EV / _KB * np.exp(-0.5 * _EV / (_KB * 300.0))
    np.testing.assert_allclose(float(out.data), want, rtol=1e-12)
    np.testing.assert_allclose(float(out.data), 1.6646e-8, rtol=1e-4)


def test_schottky_mott_barrier_executes():
    from omai.analog_device_metrology.operator.edges import schottky_mott_barrier
    from omai.analog_device_metrology.operator.nodes import ELECTRON_AFFINITY, WORK_FUNCTION

    out = apply_edge(schottky_mott_barrier, _rep(WORK_FUNCTION, "Phi_W", 4.5 * _EV),
                     _rep(ELECTRON_AFFINITY, "chi_s", 4.0 * _EV))
    assert out.space.name == "SchottkyBarrierHeight[band_carrier=electron]"
    np.testing.assert_allclose(float(out.data), 0.5 * _EV, rtol=1e-12)


def test_pulse_energy_executes_with_the_width_in_the_canonical_time_unit():
    """E = V_p^2 G t_p: 2 V on 1 uS for 1 ms is 4 nJ; t_p enters in the map's
    canonical time unit, 1 ps (1 ms = 1e9)."""
    from omai.analog_device_metrology.operator.edges import dissipate_pulse_energy
    from omai.analog_device_metrology.operator.nodes import CONDUCTANCE_STATE

    out = apply_edge(dissipate_pulse_energy, _rep(CONDUCTANCE_STATE, "G_c", 1e-6),
                     constants={"V_p": 2.0, "t_p": 1e9})
    assert out.space.name == "ProgrammingPulseEnergy"
    np.testing.assert_allclose(float(out.data), 4e-9, rtol=1e-12)


def test_roadmap_classes_of_the_new_edges_and_the_inverse_tangents():
    """The exponential makes thermionic emission analysis; the other two are
    polynomial. atan and atanh count as transcendental, so depolarization_factors
    (a Piecewise of both) is classed by them, not only by its root."""
    from omai.analog_device_metrology.operator import edges as E
    from omai.composites.operator.edges import depolarization_factors
    from omai.lean_roadmap import _classify

    assert _classify(E.emit_thermionic_conductance)[0] == "special function"
    assert _classify(E.schottky_mott_barrier)[0] == "polynomial"
    assert _classify(E.dissipate_pulse_energy)[0] == "polynomial"
    assert _classify(E.ramp_set_voltage)[0] == "special function"
    assert _classify(E.zero_bias_retention)[0] == "special function"
    assert "transcendental" in _classify(depolarization_factors)[2]


def test_committed_store_holds_records_260_to_267():
    """Records 260-263 add the barrier, work function, electron affinity and pulse
    energy nodes, records 264-266 their three edges, and record 267 corrects the
    dot-product edge's description (its identity is unchanged)."""
    from omai.analog_device_metrology.operator import EDGES, NODES

    lines = (_REPO / "map" / "log.jsonl").read_text().splitlines()
    assert len(lines) >= 267
    recs = [json.loads(line) for line in lines[259:267]]
    assert [r["op"] for r in recs] == ["add_node"] * 4 + ["add_edge"] * 3 + ["edit_meta"]
    assert [r["payload"]["uid"] for r in recs[:4]] == [node_id(s) for s in NODES[5:9]]
    assert [r["payload"]["uid"] for r in recs[4:7]] == [edge_id(op, node_id) for op in EDGES[5:8]]
    assert recs[7]["payload"]["uid"] == edge_id(EDGES[4], node_id)
    assert list(recs[7]["payload"]["meta"]) == ["description"]
    assert "the count n_w, the largest weight w_max" in recs[7]["payload"]["meta"]["description"]


def test_ramp_set_voltage_reproduces_the_kmc_calibration():
    """With the KMC device model's MoS2 constants (E_a 1.21 eV, alpha 0.25505 eV/V,
    nu_0 1e13 Hz, group 6.12912 ms/V, 300 K) the Gumbel mean is its calibrated
    2.40 V and the spread pi k_B T / (sqrt(6) alpha) its measured 0.130 V."""
    import math

    from omai.analog_device_metrology.operator.edges import ramp_set_voltage
    from omai.materials.operator.nodes import ACTIVATION_ENERGY
    from omai.thermal_transport.operator.nodes import TEMPERATURE_STATE

    kT, alpha = _KB * 300.0, 0.25505 * _EV
    out = apply_edge(ramp_set_voltage, _rep(ACTIVATION_ENERGY, "E_a", 1.21 * _EV),
                     _rep(TEMPERATURE_STATE, "temperature", 300.0),
                     constants={"alpha_F": alpha, "nu_0": 10.0, "g_r": 6.12912e9})
    assert out.space.name == "SetVoltage"
    v_star = (1.21 * _EV - kT * math.log(6.12912e-3 * 1e13 * kT / alpha)) / alpha
    np.testing.assert_allclose(float(out.data), v_star - 0.5772156649015329 * kT / alpha, rtol=1e-10)
    np.testing.assert_allclose(float(out.data), 2.40, atol=2e-3)
    np.testing.assert_allclose(math.pi * kT / (math.sqrt(6) * alpha), 0.130, atol=1e-3)


def test_zero_bias_retention_in_the_canonical_time_unit():
    """tau = exp(E_a / k_B T) / nu_0: 1.157 eV (the KMC model's WS2 barrier) at
    300 K and 1e13 Hz is 2.73e6 s, about 32 days, returned in ps."""
    from omai.analog_device_metrology.operator.edges import zero_bias_retention
    from omai.materials.operator.nodes import ACTIVATION_ENERGY
    from omai.thermal_transport.operator.nodes import TEMPERATURE_STATE

    out = apply_edge(zero_bias_retention, _rep(ACTIVATION_ENERGY, "E_a", 1.157 * _EV),
                     _rep(TEMPERATURE_STATE, "temperature", 300.0), constants={"nu_0": 10.0})
    assert out.space.name == "RetentionTime"
    want_s = np.exp(1.157 * _EV / (_KB * 300.0)) / 1e13
    np.testing.assert_allclose(float(out.data) * 1e-12, want_s, rtol=1e-10)
    np.testing.assert_allclose(want_s / 86400.0, 31.6, atol=0.1)


def test_committed_store_holds_records_268_to_271():
    """Records 268-269 add SetVoltage and RetentionTime; 270-271 their edges."""
    from omai.analog_device_metrology.operator import EDGES, NODES

    lines = (_REPO / "map" / "log.jsonl").read_text().splitlines()
    assert len(lines) >= 271
    recs = [json.loads(line) for line in lines[267:271]]
    assert [r["op"] for r in recs] == ["add_node"] * 2 + ["add_edge"] * 2
    assert [r["payload"]["uid"] for r in recs[:2]] == [node_id(s) for s in NODES[9:11]]
    assert [r["payload"]["uid"] for r in recs[2:]] == [edge_id(op, node_id) for op in EDGES[8:10]]
