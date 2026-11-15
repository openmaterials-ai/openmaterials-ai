"""omai.molecular.evaluate.cp_table: the RRHO evaluator of rrho_ideal_gas_heat_capacity.

Moved from MaterialsCodeGraph (mcg/tools/thermo/rrho.py). The nonlinear curves
stay bit-equal to the platform function they replace. The linear case is new:
the platform added 4R for every molecule, where a linear one takes 7R/2. The
inputs are public: the gas-phase fundamentals of H2O and CO2 from Shimanouchi
(NSRDS-NBS 39), in tests/fixtures/rrho_public_molecules.json.
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


def _cp(freqs, t, key="harmonic_J_per_molK", *, linear=False):
    return cp_table(freqs, [t], linear=linear)[key][0]


def _closed_form(freqs, t, *, linear):
    """Ideal-gas Cp written independently: each mode's Einstein term in the
    sinh form R (x/2)^2 / sinh^2(x/2), plus 3R/2 translation, R or 3R/2
    rotation and R for Cp - Cv."""
    vib = sum(_R_SI * (_C2_CM_K * nu / t / 2) ** 2 / math.sinh(_C2_CM_K * nu / t / 2) ** 2
              for nu in freqs)
    return vib + (1.5 + (1.0 if linear else 1.5) + 1.0) * _R_SI


def test_table_keys_and_mode_count():
    table = cp_table(_FREQS, [200.0, 300.0], linear=False)
    assert set(table) == {"temperatures_K", "harmonic_J_per_molK",
                          "qrrho_J_per_molK", "classical_J_per_molK", "n_modes"}
    assert table["temperatures_K"] == [200.0, 300.0]
    assert table["n_modes"] == 6


def test_matches_the_closed_form_on_water_and_co2():
    """The Shimanouchi fundamentals of H2O (nonlinear) and CO2 (linear)
    against the closed form evaluated separately."""
    d = _public()
    for name, mol in d["molecules"].items():
        table = cp_table(mol["frequencies_cm"], d["temperatures_K"], linear=mol["linear"])
        for t, cp in zip(d["temperatures_K"], table["harmonic_J_per_molK"]):
            want = _closed_form(mol["frequencies_cm"], t, linear=mol["linear"])
            assert math.isclose(cp, want, rel_tol=1e-12), (name, t)


def test_matches_the_platform_rrho():
    """Nonlinear curves are bit-equal to MaterialsCodeGraph's cp_table on the
    same inputs (the fixture holds its output). The platform treated CO2 as
    nonlinear, so its linear curves sit exactly R/2 below the platform's."""
    d = _public()
    for name, mol in d["molecules"].items():
        mcg = mol["mcg_nonlinear"]
        table = cp_table(mol["frequencies_cm"], d["temperatures_K"], linear=False)
        assert table["harmonic_J_per_molK"] == mcg["cp_harmonic_J_per_molK"], name
        assert table["qrrho_J_per_molK"] == mcg["cp_qrrho_J_per_molK"], name
        assert table["classical_J_per_molK"] == mcg["cp_classical_J_per_molK"], name
        if mol["linear"]:
            lin = cp_table(mol["frequencies_cm"], d["temperatures_K"], linear=True)
            for got, old in zip(lin["harmonic_J_per_molK"], mcg["cp_harmonic_J_per_molK"]):
                assert math.isclose(old - got, 0.5 * R, rel_tol=1e-9), name


def test_linear_rotor():
    """CO2 (3N-5 = 4 modes): the external terms are 3R/2 + R + R = 7R/2, so
    Cp -> 7R/2 as T -> 0 and (4 + 7/2) R in the classical limit."""
    assert math.isclose(_cp(_CO2, 0.1, linear=True), 3.5 * R, abs_tol=1e-8)
    assert math.isclose(_cp(_CO2, 2e5, linear=True), 7.5 * R, rel_tol=1e-4)
    table = cp_table(_CO2, [300.0, 600.0], linear=True)
    assert table["classical_J_per_molK"] == [7.5 * R, 7.5 * R]
    assert table["n_modes"] == 4
    # A nonlinear molecule with the same modes sits R/2 higher at every T.
    for t in (100.0, 300.0, 1000.0):
        assert math.isclose(_cp(_CO2, t, linear=False) - _cp(_CO2, t, linear=True),
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
    a = cp_table([40.0], [t], linear=False)["qrrho_J_per_molK"][0]
    b = cp_table([40.0], [t], linear=False, nu0_cm=100.0)["qrrho_J_per_molK"][0]
    assert b < a


def test_classical_column_is_flat():
    table = cp_table(_FREQS, [200.0, 300.0, 400.0], linear=False)
    assert table["classical_J_per_molK"] == [(len(_FREQS) + 4) * R] * 3


def test_rejects_imaginary_frequencies():
    with pytest.raises(ValueError, match="minimum"):
        cp_table([-25.0, 993.0], [298.15], linear=False)


def test_rejects_nonpositive_temperature():
    with pytest.raises(ValueError, match="temperature"):
        cp_table(_FREQS, [0.0], linear=False)


def test_linear_is_required():
    with pytest.raises(TypeError):
        cp_table(_FREQS, [300.0])  # type: ignore[call-arg]
