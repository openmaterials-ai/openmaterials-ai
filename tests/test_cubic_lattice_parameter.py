"""CubicLatticeParameter, its relaxation edge, its QE representation and the bohr.

The node is the edge of the conventional cubic cell of a cubic crystal at the
conditions' temperature and pressure. The edge is the static-lattice
variable-cell relaxation, opaque over (Structure, Potential). The QE spec reads
the relaxed cell from the vectors, never from the printed alat, which is the
input celldm(1).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from omai.dft_ground_state.operator.edges import EDGES, relax_cubic_lattice_parameter
from omai.dft_ground_state.operator.nodes import CUBIC_LATTICE_PARAMETER, NODES
from omai.dft_ground_state.representation.qe import (
    QE_CUBIC_LATTICE_PARAMETER,
    QE_RELAX_CUBIC_LATTICE_PARAMETER,
)
from omai.map_data import DOMAINS, build_codes, build_graph_dict
from omai.materials.operator.shared_primitives import POTENTIAL, STRUCTURE
from omai.operator.dimcheck import SYMBOL_DIMENSIONS
from omai.operator.dimensions import LENGTH
from omai.operator.identity import edge_id, edge_identity, node_id, node_identity
from omai.operator.registry import QUANTITY_TAGS, quantity_tag_for
from omai.representation.units import (
    RY_PER_BOHR,
    RY_PER_BOHR2,
    RY_PER_BOHR3,
    UNITS,
    conversion_factor,
)
from omai.semantics import ALIASES

_ROOT = Path(__file__).resolve().parents[1]
NAME = "CubicLatticeParameter"
EDGE = "relax_cubic_lattice_parameter"
NODE_UID = "34444dc03b4b725e45b32fd46add68944be9111c6cc51a1d5ee4b2382c695962"
EDGE_UID = "87e9751ce081b5e0946062840a2316664290c7942bcdf8e05415e94cf9e2e3f7"
SYMBOL = r"a_{\mathrm{lat}}"


# --------------------------------------------------------------------------
# Node, edge and identity
# --------------------------------------------------------------------------

def test_node_is_one_unlabeled_length_in_the_ground_state_tier():
    assert CUBIC_LATTICE_PARAMETER in NODES
    assert CUBIC_LATTICE_PARAMETER.name == NAME
    assert dict(CUBIC_LATTICE_PARAMETER.labels) == {}
    assert CUBIC_LATTICE_PARAMETER.tier == "Ground state"
    (field,) = CUBIC_LATTICE_PARAMETER.fields
    assert field.name == "a_lat" and field.dimension == LENGTH and tuple(field.indices) == ()
    # The tag derives from the name and is identity, so the name claims cubic only.
    assert quantity_tag_for(NAME) == "cubic_lattice_parameter"
    assert "cubic_lattice_parameter" in QUANTITY_TAGS
    assert "lattice_parameter" not in QUANTITY_TAGS


def test_every_base_uid_is_unchanged_and_the_new_uids_are_pinned():
    base = json.loads((_ROOT / "tests" / "fixtures" / "cubic_lattice_parameter_base_uids.json").read_text())
    nodes = {s.name: node_id(s) for d in DOMAINS for s in d.nodes}
    edges = {o.name: edge_id(o, node_id) for d in DOMAINS for o in d.edges}
    assert {n: nodes.get(n) for n in base["nodes"]} == base["nodes"]
    assert {e: edges.get(e) for e in base["edges"]} == base["edges"]
    assert set(nodes) - set(base["nodes"]) == {NAME}
    assert set(edges) - set(base["edges"]) == {EDGE}
    assert nodes[NAME] == NODE_UID and edges[EDGE] == EDGE_UID


def test_edge_is_an_opaque_relaxation_over_structure_and_potential():
    op = relax_cubic_lattice_parameter
    assert op in EDGES
    assert tuple(op.inputs) == (STRUCTURE, POTENTIAL)
    assert tuple(op.outputs) == (CUBIC_LATTICE_PARAMETER,)
    assert dict(op.schemes) == {"method": "variable_cell_relaxation"}
    assert op.is_executable_in_sympy is False
    assert str(op.formula.lhs) == SYMBOL


def test_formula_symbol_is_a_registered_length_and_bare_a_stays_dimensionless():
    # Bare "a" is the thermal domain's dimensionless symbol, and a_0 would read
    # as the Bohr radius, so the lattice parameter has its own symbol.
    assert SYMBOL_DIMENSIONS[SYMBOL] == LENGTH
    assert SYMBOL_DIMENSIONS["a"] != LENGTH


def test_graph_links_the_new_node_from_structure_and_potential():
    graph = build_graph_dict(DOMAINS)
    assert NAME in {n["id"] for n in graph["nodes"]}
    links = [l for l in graph["links"] if l.get("target") == NAME]
    assert {l["source"] for l in links} == {"Structure", "Potential"}


def test_text_states_static_lattice_symmetry_and_the_cubic_limit():
    node = CUBIC_LATTICE_PARAMETER.description
    edge = relax_cubic_lattice_parameter.description
    tag = QUANTITY_TAGS["cubic_lattice_parameter"]
    for text in (node, edge, tag):
        assert "zero-point" in text and "thermal expansion" in text
    for text in (node, tag):
        assert "195 to 230" in text and "not cubic" in text
    # The node holds any temperature and pressure; the edge is the static value.
    assert "temperature and pressure the conditions carry" in node
    assert "stationary point" in edge and "need not be a minimum" in edge


def test_store_records_393_and_394_add_the_node_and_edge_and_pass_the_gates():
    from omai.gates import validate_contribution

    lines = (_ROOT / "map" / "log.jsonl").read_text().splitlines()
    recs = [json.loads(line) for line in lines[392:394]]
    assert len(lines) >= 394
    assert [(r["seq"], r["op"]) for r in recs] == [(393, "add_node"), (394, "add_edge")]
    assert recs[0]["payload"]["uid"] == NODE_UID
    assert recs[1]["payload"]["uid"] == EDGE_UID

    records = [
        {"op": "add_node", "payload": {"uid": node_id(CUBIC_LATTICE_PARAMETER),
                                       "identity": node_identity(CUBIC_LATTICE_PARAMETER),
                                       "meta": {"name": NAME}}},
        {"op": "add_edge", "payload": {"uid": edge_id(relax_cubic_lattice_parameter, node_id),
                                       "identity": edge_identity(relax_cubic_lattice_parameter, node_id),
                                       "meta": {"name": EDGE,
                                                "schemes": relax_cubic_lattice_parameter.schemes}}},
    ]
    current = {"nodes": {}, "edges": {}}
    for s in (STRUCTURE, POTENTIAL):
        current["nodes"][node_id(s)] = {"uid": node_id(s), "identity": node_identity(s), "meta": {}}
    assert validate_contribution(records, current) == []


def test_semantic_aliases_claim_only_the_cubic_quantity():
    assert ALIASES["cubic-lattice-parameter"] == (NAME, EDGE)
    assert ALIASES["cubic-lattice-constant"] == (NAME,)
    # A query for a lattice that is not cubic must not land on this node.
    for label, targets in ALIASES.items():
        if NAME in targets or EDGE in targets:
            assert label.startswith("cubic-"), label


# --------------------------------------------------------------------------
# QE representation and the bohr
# --------------------------------------------------------------------------

def test_qe_covers_the_node_in_bohr_from_the_final_coordinates_block():
    codes = build_codes(DOMAINS)
    entry = codes["qe"][NAME]
    assert entry["unit"] == "bohr"
    assert "Begin final coordinates" in entry["api"]
    assert QE_CUBIC_LATTICE_PARAMETER.observable_units == {"a_lat": "bohr"}


def test_qe_notes_read_the_vectors_not_the_input_alat():
    notes = QE_CUBIC_LATTICE_PARAMETER.notes
    assert "INPUT celldm(1)" in notes and "returns the starting lattice constant" in notes
    for header in ("CELL_PARAMETERS (alat= x)", "CELL_PARAMETERS (bohr)", "CELL_PARAMETERS (angstrom)"):
        assert header in notes
    assert "(V_cell N_conv / N_cell)^(1/3)" in notes and "not 4 in general" in notes
    assert "bfgs failed after" in notes and "Pulay" in notes and "195 to 230" in notes
    # The final block is printed after a failed BFGS too, so it is no evidence.
    assert "The final coordinates block alone is no evidence" in notes
    assert "exit status" in notes


def test_qe_operator_spec_names_the_relaxation_settings():
    choices = QE_RELAX_CUBIC_LATTICE_PARAMETER.discretization_choices
    assert QE_RELAX_CUBIC_LATTICE_PARAMETER.operator is relax_cubic_lattice_parameter
    assert {"calculation", "cell_dofree", "press", "press_conv_thr", "ecutwfc"} <= set(choices)
    assert "vc-relax" in choices["calculation"]


def test_bohr_is_the_qe_7_5_value_and_the_ry_per_bohr_units_keep_their_factors():
    bohr_a = 0.529177210903
    assert UNITS["bohr"].dimension == LENGTH
    assert conversion_factor("bohr", "angstrom") == bohr_a
    assert RY_PER_BOHR.to_operator == 13.605693122994 / bohr_a
    assert RY_PER_BOHR2.to_operator == 13.605693122994 / bohr_a**2
    assert RY_PER_BOHR3.to_operator == 13.605693122994 / bohr_a**3


def test_the_conventional_cell_rule_recovers_the_edge_for_p_i_and_f_cells():
    # The rule in the QE notes, a_lat = (V_cell N_conv / N_cell)^(1/3), on the
    # primitive cells of the three cubic lattices with one atom per lattice
    # point (N_conv / N_cell = 1, 2, 4) and on the two-atom diamond cell (8 / 2).
    # V_cell is the determinant of pw.x's ibrav 1, 3 and 2 vectors for edge a.
    a = 10.2631
    h = a / 2
    cells = {
        "P": (np.array([[a, 0, 0], [0, a, 0], [0, 0, a]]), 1, 1),
        "I": (np.array([[h, h, h], [-h, h, h], [-h, -h, h]]), 2, 1),
        "F": (np.array([[-h, 0, h], [0, h, h], [-h, h, 0]]), 4, 1),
        "diamond": (np.array([[-h, 0, h], [0, h, h], [-h, h, 0]]), 8, 2),
    }
    for name, (vectors, n_conv, n_cell) in cells.items():
        v_cell = abs(np.linalg.det(vectors))
        a_lat = (v_cell * n_conv / n_cell) ** (1 / 3)
        assert abs(a_lat - a) < 1e-9, name
    # A fixed factor of 4 would be wrong for the I cell by 2^(1/3).
    v_bcc = abs(np.linalg.det(cells["I"][0]))
    assert abs((4 * v_bcc) ** (1 / 3) / a - 2 ** (1 / 3)) < 1e-9
    assert abs(a * conversion_factor("bohr", "angstrom") - a * 0.529177210903) < 1e-12
