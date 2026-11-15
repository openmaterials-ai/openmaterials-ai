"""omai.molecular.evaluate.cp_table: the RRHO evaluator of rrho_ideal_gas_heat_capacity.

Moved from MaterialsCodeGraph. The nonlinear curves reproduce the platform's
values. The atom and linear cases are new: the platform added 4R for every
species, where an atom takes 5R/2 and a linear molecule 7R/2. The inputs are
public: the gas-phase fundamentals of H2O and CO2 from Shimanouchi
(NSRDS-NBS 39) and their NIST-JANAF heat capacities, in
tests/fixtures/rrho_public_molecules.json.
"""
from __future__ import annotations

import itertools
import json
import math
from pathlib import Path

import pytest

from omai.molecular.evaluate import R_J_PER_MOLK as R
from omai.molecular.evaluate import cp_table

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "rrho_public_molecules.json"
# R = N_A k_B and c_2 = h c / k_B (CODATA 2018), for the independent evaluation
_R_SI = 6.02214076e23 * 1.380649e-23
_C2_CM_K = 1.438776877

# six modes spanning soft torsion to C-H stretch (cm^-1)
_FREQS = [12.7, 55.0, 400.0, 993.1, 1609.5, 3027.2]


def _public():
    return json.loads(_FIXTURE.read_text())


_CO2 = _public()["molecules"]["CO2"]["frequencies_cm"]


def _cp(freqs, t, key="harmonic_J_per_molK", *, geometry="nonlinear"):
    return cp_table(freqs, [t], geometry=geometry)[key][0]


_ROTATION = {"atom": 0.0, "linear": 1.0, "nonlinear": 1.5}


def _closed_form(freqs, t, *, geometry):
    """Ideal-gas Cp written independently: each mode's Einstein term in the
    sinh form R (x/2)^2 / sinh^2(x/2), plus 3R/2 translation, 0, R or 3R/2
    rotation and R for Cp - Cv."""
    vib = sum(_R_SI * (_C2_CM_K * nu / t / 2) ** 2 / math.sinh(_C2_CM_K * nu / t / 2) ** 2
              for nu in freqs)
    return vib + (1.5 + _ROTATION[geometry] + 1.0) * _R_SI


def test_table_keys_and_mode_count():
    table = cp_table(_FREQS, [200.0, 300.0], geometry="nonlinear")
    assert set(table) == {"temperatures_K", "harmonic_J_per_molK",
                          "qrrho_J_per_molK", "classical_J_per_molK", "n_modes"}
    assert table["temperatures_K"] == [200.0, 300.0]
    assert table["n_modes"] == 6


def test_matches_the_closed_form_on_water_and_co2():
    """The Shimanouchi fundamentals of H2O (nonlinear) and CO2 (linear)
    against the closed form evaluated separately."""
    d = _public()
    for name, mol in d["molecules"].items():
        table = cp_table(mol["frequencies_cm"], d["temperatures_K"], geometry=mol["geometry"])
        for t, cp in zip(d["temperatures_K"], table["harmonic_J_per_molK"]):
            want = _closed_form(mol["frequencies_cm"], t, geometry=mol["geometry"])
            assert math.isclose(cp, want, rel_tol=1e-12), (name, t)


def _close_all(got, want, rel_tol):
    return len(got) == len(want) and all(
        math.isclose(a, b, rel_tol=rel_tol) for a, b in zip(got, want))


def test_matches_the_platform_rrho():
    """The nonlinear curves reproduce the platform's values on the same inputs
    (the fixture holds them) to 1e-15, the last-ulp spread of libm exp across
    hosts. The platform treated CO2 as nonlinear, so its linear curve sits
    exactly R/2 below the platform's."""
    d = _public()
    for name, mol in d["molecules"].items():
        old = mol["platform_nonlinear"]
        table = cp_table(mol["frequencies_cm"], d["temperatures_K"], geometry="nonlinear")
        for key in ("harmonic", "qrrho", "classical"):
            assert _close_all(table[f"{key}_J_per_molK"], old[f"cp_{key}_J_per_molK"],
                              1e-15), (name, key)
        if mol["geometry"] == "linear":
            lin = cp_table(mol["frequencies_cm"], d["temperatures_K"], geometry="linear")
            for got, was in zip(lin["harmonic_J_per_molK"], old["cp_harmonic_J_per_molK"]):
                assert math.isclose(was - got, 0.5 * R, rel_tol=1e-9), name


def test_harmonic_values_of_water_and_co2():
    """The harmonic Cp of the Shimanouchi fundamentals: H2O 33.48 J/(K mol) at
    298.15 K, CO2 37.15 at 298.15 K and 54.15 at 1000 K."""
    h2o = _public()["molecules"]["H2O"]["frequencies_cm"]
    assert _cp(h2o, 298.15) == pytest.approx(33.48, abs=0.005)
    assert _cp(_CO2, 298.15, geometry="linear") == pytest.approx(37.15, abs=0.005)
    assert _cp(_CO2, 1000.0, geometry="linear") == pytest.approx(54.15, abs=0.005)


def test_agrees_with_nist_janaf_within_half_a_percent():
    """Against the NIST-JANAF ideal-gas Cp (Chase 1998): H2O 33.590 at 298.15 K,
    CO2 37.129 at 298.15 K and 54.308 at 1000 K. The RRHO model omits
    anharmonicity, so 0.5% is its accuracy on these molecules, not a numerical
    tolerance."""
    for name, mol in _public()["molecules"].items():
        for t, ref in mol["janaf_cp_J_per_molK"].items():
            got = _cp(mol["frequencies_cm"], float(t), geometry=mol["geometry"])
            assert math.isclose(got, ref, rel_tol=5e-3), (name, t, got, ref)


def test_atom_is_five_halves_R():
    """A monatomic species has no internal modes and no rotation: Cp = 5R/2 at
    every temperature, in all three curves."""
    table = cp_table([], [10.0, 298.15, 3000.0], geometry="atom")
    for key in ("harmonic_J_per_molK", "qrrho_J_per_molK", "classical_J_per_molK"):
        assert table[key] == [2.5 * R] * 3
    assert table["n_modes"] == 0


def test_atom_with_modes_is_refused():
    with pytest.raises(ValueError, match="atom"):
        cp_table([993.0], [298.15], geometry="atom")


def test_unknown_geometry_is_refused():
    with pytest.raises(ValueError, match="geometry"):
        cp_table(_FREQS, [298.15], geometry="planar")


def test_linear_rotor():
    """CO2 (3N-5 = 4 modes): the external terms are 3R/2 + R + R = 7R/2, so
    Cp -> 7R/2 as T -> 0 and (4 + 7/2) R in the classical limit."""
    assert math.isclose(_cp(_CO2, 0.1, geometry="linear"), 3.5 * R, abs_tol=1e-8)
    assert math.isclose(_cp(_CO2, 2e5, geometry="linear"), 7.5 * R, rel_tol=1e-4)
    table = cp_table(_CO2, [300.0, 600.0], geometry="linear")
    assert table["classical_J_per_molK"] == [7.5 * R, 7.5 * R]
    assert table["n_modes"] == 4
    # A nonlinear molecule with the same modes sits R/2 higher at every T.
    for t in (100.0, 300.0, 1000.0):
        assert math.isclose(_cp(_CO2, t) - _cp(_CO2, t, geometry="linear"),
                            0.5 * R, rel_tol=1e-12)


def test_low_temperature_limit_is_4R():
    # T = 0.1 K freezes even the 12.7 cm^-1 torsion (theta ~ 18 K).
    assert math.isclose(_cp(_FREQS, 0.1), 4 * R, abs_tol=1e-8)


def test_high_temperature_limit_is_equipartition():
    assert math.isclose(_cp(_FREQS, 2e5), (len(_FREQS) + 4) * R, rel_tol=1e-4)


def test_cp_monotonic_in_temperature():
    cps = [_cp(_FREQS, t) for t in (100.0, 200.0, 300.0, 500.0, 800.0)]
    assert all(a < b for a, b in itertools.pairwise(cps))


def test_single_mode_matches_the_einstein_function():
    nu, t = 993.1, 298.15
    x = 1.438776877 * nu / t
    einstein = R * x * x * math.exp(x) / (math.exp(x) - 1.0) ** 2
    assert math.isclose(_cp([nu], t) - 4 * R, einstein, rel_tol=1e-12)


def test_qrrho_takes_a_soft_mode_toward_half_R():
    # a 12.7 cm^-1 torsion at 298 K: harmonic gives about R, qRRHO about R/2
    hard = _cp([12.7], 298.15) - 4 * R
    soft = _cp([12.7], 298.15, "qrrho_J_per_molK") - 4 * R
    assert math.isclose(hard, R, rel_tol=0.01)
    assert abs(soft - 0.5 * R) < 0.05 * R


def test_qrrho_leaves_stiff_modes_untouched():
    # the (50/1609.5)^4 rotor weight leaves a 1e-5 relative tail
    hard = _cp([1609.5], 298.15)
    soft = _cp([1609.5], 298.15, "qrrho_J_per_molK")
    assert math.isclose(hard, soft, rel_tol=1e-3)


def test_rotor_cutoff_is_a_parameter():
    t = 298.15
    a = cp_table([40.0], [t], geometry="nonlinear")["qrrho_J_per_molK"][0]
    b = cp_table([40.0], [t], geometry="nonlinear", nu0_cm=100.0)["qrrho_J_per_molK"][0]
    assert b < a


def test_classical_column_is_flat():
    table = cp_table(_FREQS, [200.0, 300.0, 400.0], geometry="nonlinear")
    assert table["classical_J_per_molK"] == [(len(_FREQS) + 4) * R] * 3


def test_rejects_imaginary_frequencies():
    """A mode at or below 0 cm^-1 is refused, never inverted or dropped."""
    for nu in (-25.0, 0.0):
        with pytest.raises(ValueError, match="minimum"):
            cp_table([nu, 993.0], [298.15], geometry="nonlinear")
    with pytest.raises(ValueError, match="minimum"):
        cp_table([-25.0, 993.0], [298.15], geometry="nonlinear")


def test_rejects_nonpositive_temperature():
    with pytest.raises(ValueError, match="temperature"):
        cp_table(_FREQS, [0.0], geometry="nonlinear")


def test_geometry_is_required():
    with pytest.raises(TypeError):
        cp_table(_FREQS, [300.0])  # type: ignore[call-arg]
