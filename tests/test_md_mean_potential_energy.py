"""The canonical mean potential energy per atom of classical MD (2026-11-02):
one contribution, records 378-379, passing the gates on the store before it.
Positions are history and never move.
"""
from __future__ import annotations

import json
from pathlib import Path

from omai.dft_ground_state.operator.nodes import TOTAL_ENERGY
from omai.gates import validate_contribution
from omai.map_data import DOMAINS, build_graph_dict
from omai.materials.operator.nodes import CONFIGURATIONAL_ENERGY
from omai.operator.dimcheck import dimensional_report
from omai.operator.identity import edge_id, node_id, node_identity
from omai.semantics import build_semantics, resolve
from omai.store import Store
from omai.thermal_transport.operator.edges import sample_mean_potential_energy
from omai.thermal_transport.operator.nodes import (
    INTERNAL_ENERGY,
    MEAN_POTENTIAL_ENERGY,
    MOLAR_INTERNAL_ENERGY,
    QUANTUM_KINETIC_ENERGY,
)
from omai.thermal_transport.representation.gpumd import GPUMD_MEAN_POTENTIAL_ENERGY

_MAP = Path(__file__).resolve().parents[1] / "map"
_SEQ_377 = "b5d3f4502be20e03212af142d2b953c29a7189ae386194c478e53e36c72e6c9e"
_SEQ_379 = "8491d0b6ad048cea62b7cdfac631632debb08a3d354bb25fb9f08191b4cedc66"
_NODE_UID = "31af780e2daebb229b18642e20d5bb48a9ad42e73a0a7689e5ab148e31eaec6f"
_EDGE_UID = "450186839ad821ee4b3973b73d4aebbb8b6ebe40e9e8cb0be20b43aca0f65329"


def _records(first: int, last: int) -> list[dict]:
    lines = (_MAP / "log.jsonl").read_text().splitlines()
    assert len(lines) >= last, "the contribution has not landed"
    return [json.loads(line) for line in lines[first - 1:last]]


def test_contribution_is_records_378_to_379():
    recs = _records(378, 379)
    assert [r["op"] for r in recs] == ["add_node", "add_edge"]
    assert [r["payload"]["uid"] for r in recs] == [
        node_id(MEAN_POTENTIAL_ENERGY),
        edge_id(sample_mean_potential_energy, node_id)]
    assert [r["payload"]["uid"] for r in recs] == [_NODE_UID, _EDGE_UID]
    assert recs[0]["prev"] == _SEQ_377
    assert recs[-1]["version"] == _SEQ_379
    contribution = [{"op": r["op"], "payload": r["payload"]} for r in recs]
    assert validate_contribution(contribution, Store(_MAP).read(_SEQ_377)) == []


def test_node_is_a_scalar_canonical_energy_with_its_own_tag():
    ident = node_identity(MEAN_POTENTIAL_ENERGY)
    assert ident == {"quantity": "mean_potential_energy",
                     "fields": [{"dimension": "M^1 L^2 T^-2", "indices": []}],
                     "gauge": "observable", "labels": {}}
    assert MEAN_POTENTIAL_ENERGY.tier == "Molecular dynamics"
    # Energies kept apart by the tag (MolarInternalEnergy is per mole).
    others = (INTERNAL_ENERGY, MOLAR_INTERNAL_ENERGY, TOTAL_ENERGY,
              CONFIGURATIONAL_ENERGY, QUANTUM_KINETIC_ENERGY)
    assert "mean_potential_energy" not in {node_identity(s)["quantity"] for s in others}


def test_edge_reads_the_potential_on_the_trajectory_per_atom():
    op = sample_mean_potential_energy
    assert [s.name for s in op.inputs] == ["Potential", "Trajectory"]
    assert op.outputs == (MEAN_POTENTIAL_ENERGY,)
    assert not op.is_executable_in_sympy
    g = build_graph_dict(DOMAINS)
    into = {(link["source"], link["op"]) for link in g["links"]
            if link["target"] == MEAN_POTENTIAL_ENERGY.name}
    assert into == {("Potential", op.name), ("Trajectory", op.name),
                    ("AtomCount", "provide_AtomCount")}
    report = dimensional_report((), (op,))
    assert report["skipped"] == [op.name]


def test_gpumd_reads_the_thermo_potential_energy_column():
    spec = GPUMD_MEAN_POTENTIAL_ENERGY
    assert spec.observable_units == {"U_bar": "ev_per_atom"}
    assert "thermo.out column 3" in spec.code_api["U_bar"]


def test_aliases_resolve():
    sem = build_semantics(build_graph_dict(DOMAINS))
    for q in ("mean potential energy", "average potential energy",
              "NVT potential energy"):
        assert resolve(q, sem)[0]["id"] == MEAN_POTENTIAL_ENERGY.name
