"""Conductance relaxation physics and external benchmark contracts.

All numerical inputs here are synthetic. They are not literature instances,
device calibrations, or empirical conformance targets.
"""
from __future__ import annotations

import numpy as np
import pytest

from omai.analog_device_metrology.operator import EDGES, NODES
from omai.analog_device_metrology.operator import edges as E
from omai.analog_device_metrology.operator import nodes as N
from omai.operator.identity import edge_id, edge_identity, node_id, node_identity
from omai.representation.executor import ExternalSolveRequired, apply_edge, operator_form_spec
from omai.representation.instance import Representation


def _rep(space, symbol, data):
    return Representation(space_adapter_spec=operator_form_spec(space),
                          observable_name=symbol, data=np.asarray(data), is_operator=True)


def test_trap_tangent_matches_a_direct_derivative_in_seconds():
    """The executed result is ps; the independent derivative uses seconds."""
    tau_s, amplitude, equilibrium = 10.0, 2.0, 1e-9
    initial = equilibrium * np.exp(amplitude)
    out = apply_edge(
        E.subthreshold_conductance_tangent_time,
        _rep(N.INTERFACE_TRAP_RELAXATION_TIME, "tau_it", tau_s * 1e12),
        _rep(N.CONDUCTANCE_STATE, "G_c", initial),
        constants={"G_eq": equilibrium},
    )
    assert out.space.name == "ConductanceRelaxationTime"

    def conductance(time_s):
        return equilibrium * np.exp(amplitude * np.exp(-time_s / tau_s))

    dt_s = 1e-4
    slope = (conductance(dt_s) - conductance(-dt_s)) / (2 * dt_s)
    tangent_s = float(out.data) * 1e-12
    np.testing.assert_allclose(tangent_s, -initial / slope, rtol=1e-8)
    np.testing.assert_allclose(tangent_s, 5.0, rtol=1e-12)

    # An equilibrium-baseline tangent and an actual raw-G 1/e crossing differ.
    excess_tangent_s = -(initial - equilibrium) / slope
    np.testing.assert_allclose(excess_tangent_s, 4.3233235838, rtol=1e-8)
    crossing_s = -tau_s * np.log(1 - 1 / amplitude)
    np.testing.assert_allclose(conductance(crossing_s), initial / np.e, rtol=1e-12)
    assert not np.isclose(crossing_s, tangent_s)
    assert not np.isclose(excess_tangent_s, tangent_s)

    # A single occupation mode already has a growing local tangent time.
    later = tau_s
    later_slope = (conductance(later + dt_s) - conductance(later - dt_s)) / (2 * dt_s)
    np.testing.assert_allclose(-conductance(later) / later_slope,
                               tangent_s * np.e, rtol=1e-8)


def test_trap_tangent_is_invariant_under_common_conductance_scaling():
    results = []
    for scale in (1e-9, 1e-6, 1.0):
        out = apply_edge(
            E.subthreshold_conductance_tangent_time,
            _rep(N.INTERFACE_TRAP_RELAXATION_TIME, "tau_it", 10e12),
            _rep(N.CONDUCTANCE_STATE, "G_c", scale * np.exp(2)),
            constants={"G_eq": scale},
        )
        results.append(float(out.data))
    np.testing.assert_allclose(results, [5e12] * 3, rtol=1e-12)


def test_relaxation_nodes_are_distinct_from_zero_bias_survival():
    from omai.operator.dimensions import TIME

    spaces = (N.CONDUCTANCE_RELAXATION_TIME, N.INTERFACE_TRAP_RELAXATION_TIME,
              N.RETENTION_TIME)
    assert len({node_id(s) for s in spaces}) == 3
    assert all(s.fields[0].dimension == TIME for s in spaces)
    assert E.zero_bias_retention.outputs == (N.RETENTION_TIME,)
    assert E.subthreshold_conductance_tangent_time.inputs == (
        N.INTERFACE_TRAP_RELAXATION_TIME, N.CONDUCTANCE_STATE)
    assert E.subthreshold_conductance_tangent_time.schemes == {
        "criterion": "tangent_to_zero", "regime": "subthreshold_single_mode"}


def test_classifier_needs_external_evaluation_not_a_scalar_shortcut():
    from omai.operator.dimensions import DIMENSIONLESS

    op = E.evaluate_reservoir_classification
    assert op.inputs == (N.CONDUCTANCE_STATE,)
    assert op.outputs == (N.CLASSIFICATION_ACCURACY,)
    assert N.CLASSIFICATION_ACCURACY.fields[0].dimension == DIMENSIONLESS
    assert not op.is_executable_in_sympy
    with pytest.raises(ExternalSolveRequired):
        apply_edge(op, _rep(N.CONDUCTANCE_STATE, "G_c", 1e-9))


def test_new_contribution_connects_through_existing_conductance_only():
    """The five additions satisfy gates without changing the old map."""
    from omai.gates import validate_contribution
    from omai.genesis import _formula_srepr

    records = [{"op": "add_node", "payload": {
        "uid": node_id(s), "identity": node_identity(s), "meta": {"name": s.name}}}
        for s in NODES[11:]]
    records += [{"op": "add_edge", "payload": {
        "uid": edge_id(op, node_id), "identity": edge_identity(op, node_id),
        "meta": {"name": op.name, "schemes": op.schemes,
                 "formula_srepr": _formula_srepr(op.formula)}}} for op in EDGES[10:]]
    current = {"nodes": {node_id(N.CONDUCTANCE_STATE): {
        "uid": node_id(N.CONDUCTANCE_STATE), "identity": node_identity(N.CONDUCTANCE_STATE),
        "meta": {}}}, "edges": {}}
    assert len(records) == 5
    assert validate_contribution(records, current) == []


def test_relaxation_and_classifier_proof_status_is_explicit():
    from omai.lean_roadmap import _classify

    assert _classify(E.subthreshold_conductance_tangent_time)[0] == "special function"
    assert _classify(E.evaluate_reservoir_classification)[0] == "opaque code output"
