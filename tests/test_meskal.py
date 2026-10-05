"""The meskal representation (MESKAL, differentiable lattice thermal transport in JAX)."""

from omai.evidence import code_releases
from omai.map_data import DOMAINS, build_codes
from omai.representation.credits import CODE_CREDITS
from omai.representation.units import UNITS
from omai.thermal_transport.representation.kaldo import (
    KALDO_FREQUENCY,
    KALDO_GROUP_VELOCITY,
    KALDO_HEAT_CAPACITY,
    KALDO_ISOTOPIC_LINEWIDTH,
    KALDO_LINEWIDTH,
)
from omai.thermal_transport.representation.meskal import (
    MESKAL_FREQUENCY,
    MESKAL_GROUP_VELOCITY,
    MESKAL_HEAT_CAPACITY,
    MESKAL_ISOTOPIC_LINEWIDTH,
    MESKAL_LINEWIDTH,
)


def test_representation_covers_the_meskal_nodes_with_registered_units():
    codes = build_codes(DOMAINS)
    assert set(codes["meskal"]) == {
        "Potential", "ForceConstants[order=3]", "DynamicalMatrix", "Frequency",
        "GroupVelocity", "HeatCapacity", "IsotopeAbundances",
        "Linewidth[channel=anharmonic_3ph]", "Linewidth[channel=isotope]",
        "Linewidth[channel=boundary]", "MeanFreeDisplacement[bte_solver=rta]",
        "MeanFreeDisplacement[bte_solver=direct_inverse]",
        "ThermalConductivity[bte_solver=rta]",
        "ThermalConductivity[bte_solver=direct_inverse]",
        "ThermalConductivity[transport_model=qhgk]", "ModalDiffusivity",
        "PhononTransmission", "ThermalConductance[transport_model=landauer]"}
    for entry in codes["meskal"].values():
        assert entry["unit"] is None or entry["unit"] in UNITS
    assert "ForceConstants[order=2]" not in codes["meskal"]  # supercell_fc2 is mass-weighted


def test_credits_and_the_release_row_carry_bsd_3_clause_at_v1_1_0():
    cr = CODE_CREDITS["meskal"]
    assert cr["name"] == "MESKAL" and cr["license"] == "BSD-3-Clause" and cr["doi"] is None
    assert "v1.1.0" in cr["license_source"]
    (row,) = code_releases()["meskal"]["releases"]
    assert row["spdx"] == "BSD-3-Clause" and row["version"] == "1.1.0" and row["tag"] == "v1.1.0"
    assert row["commit"] == "d97531d0cccb8a9950782534801973082f0642d1"


def test_conventions_follow_kaldo():
    # gamma is kALDo's bandwidth: FWHM in rad/ps, twice the imaginary self-energy.
    for a, b in ((MESKAL_LINEWIDTH, KALDO_LINEWIDTH),
                 (MESKAL_ISOTOPIC_LINEWIDTH, KALDO_ISOTOPIC_LINEWIDTH)):
        assert a.observable_units == b.observable_units
        assert a.observable_normalizations == b.observable_normalizations
    for a, b in ((MESKAL_FREQUENCY, KALDO_FREQUENCY), (MESKAL_GROUP_VELOCITY, KALDO_GROUP_VELOCITY),
                 (MESKAL_HEAT_CAPACITY, KALDO_HEAT_CAPACITY)):
        assert a.observable_units == b.observable_units
