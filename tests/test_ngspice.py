"""The ngspice representation (circuit simulation) on the analog-device-metrology nodes."""

from omai.evidence import code_releases
from omai.map_data import DOMAINS, build_codes
from omai.representation.credits import CODE_CREDITS
from omai.representation.units import UNITS


def test_representation_covers_conductance_state_and_dot_product_error():
    codes = build_codes(DOMAINS)
    assert set(codes["ngspice"]) == {"ConductanceState", "DotProductError"}
    assert codes["ngspice"]["ConductanceState"]["unit"] == "siemens"
    assert codes["ngspice"]["DotProductError"]["unit"] == "dimensionless"
    for entry in codes["ngspice"].values():
        assert entry["unit"] in UNITS


def test_credits_and_the_release_row_read_at_ngspice_47():
    cr = CODE_CREDITS["ngspice"]
    assert cr["name"] == "ngspice" and cr["doi"] is None
    assert cr["license"].startswith("BSD-3-Clause AND ")
    assert "ngspice-47" in cr["license_source"]
    (row,) = code_releases()["ngspice"]["releases"]
    assert row["spdx"] == cr["license"]
    assert row["version"] == "47" and row["tag"] == "ngspice-47"
    assert row["commit"] == "a80f6e3e95d51534905b1f23410a951802666656"
    assert row["released"] == "2026-08-11"
