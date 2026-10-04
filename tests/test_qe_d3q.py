"""The qe-d3q representation (D3Q and thermal2 on Quantum ESPRESSO 7.5) and the
qe BulkModulus row (ev.x)."""

import math

from omai.map_data import DOMAINS, build_codes
from omai.representation.adapter import representation_to_operator
from omai.representation.credits import CODE_CREDITS
from omai.representation.units import UNITS, conversion_factor
from omai.thermal_transport.representation.phono3py import (
    PHONO3PY_FORCE_CONSTANTS_3,
    PHONO3PY_LINEWIDTH,
)
from omai.thermal_transport.representation.qe import QE_FORCE_CONSTANTS_2
from omai.thermal_transport.representation.qe_d3q import (
    QE_D3Q_FORCE_CONSTANTS_2,
    QE_D3Q_FORCE_CONSTANTS_3,
    QE_D3Q_LINEWIDTH,
)


def test_representation_covers_the_five_d3q_nodes_with_registered_units():
    codes = build_codes(DOMAINS)
    assert set(codes["qe-d3q"]) == {
        "ForceConstants[order=2]", "ForceConstants[order=3]",
        "Linewidth[channel=anharmonic_3ph]",
        "ThermalConductivity[bte_solver=rta]",
        "ThermalConductivity[bte_solver=direct_inverse]"}
    for entry in codes["qe-d3q"].values():
        assert entry["unit"] in UNITS


def test_credits_name_both_method_papers_and_the_dual_license():
    cr = CODE_CREDITS["qe-d3q"]
    assert cr["doi"] == "10.1103/PhysRevB.87.214303"
    assert "10.1103/PhysRevB.88.045430" in cr["citation"]
    assert "GPL-2.0" in cr["license"] and "CeCILL-2.1" in cr["license"]
    assert cr["url"] == "https://github.com/anharmonic/d3q"


def test_units_follow_qe_and_the_linewidth_is_the_hwhm():
    # mat2R (thermal2's format, not flfrc) shares the qe representation's Ry/bohr^2.
    assert QE_D3Q_FORCE_CONSTANTS_2.observable_units == QE_FORCE_CONSTANTS_2.observable_units
    # Ry/bohr^3 to the canonical eV/A^3 (CODATA Ry and bohr).
    assert math.isclose(conversion_factor("Ry_per_bohr3", "eV_per_A3"),
                        13.605693122994 / 0.529177210903**3, rel_tol=1e-12)
    assert QE_D3Q_FORCE_CONSTANTS_3.declared_unit("phi") == "Ry_per_bohr3"
    assert representation_to_operator(PHONO3PY_FORCE_CONSTANTS_3, "phi") == 1.0
    # HWHM in cm^-1: canonical imag_self_energy like phono3py, no factor of 2.
    assert QE_D3Q_LINEWIDTH.observable_normalizations == PHONO3PY_LINEWIDTH.observable_normalizations == {}
    assert UNITS["inverse_cm"].dimension == UNITS["linear_THz"].dimension


def test_qe_bulk_modulus_row_names_ev_x_and_no_elastic_row():
    qe = build_codes(DOMAINS)["qe"]
    assert qe["BulkModulus"]["unit"] == "kbar"
    assert qe["BulkModulus"]["api"].startswith("ev.x")
    assert "ElasticConstants" not in qe
