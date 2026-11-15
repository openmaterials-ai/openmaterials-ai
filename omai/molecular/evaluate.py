"""Evaluator of rrho_ideal_gas_heat_capacity: the ideal-gas Cp(T) of one molecule.

cp_table sums the quantum harmonic Cv of each normal mode and adds the external
terms of an ideal gas: 3R/2 translation, R (linear) or 3R/2 (nonlinear)
rotation, and R for Cp - Cv. A nonlinear molecule therefore adds 4R, a linear
one 7R/2. Three curves come back:

- ``harmonic``: every mode a quantum harmonic oscillator.
- ``qrrho``: each mode's Cv interpolated toward the free-rotor limit R/2 with
  the weight w = 1 / (1 + (nu0/nu)^4), nu0 = 50 cm^-1 by default (the xtb
  default rotor cutoff). Soft torsions then count as hindered rotors.
- ``classical``: the equipartition limit (n_modes + 4) R, or (n_modes + 7/2) R
  for a linear molecule, the value an unquantized force field gives.

Moved from MaterialsCodeGraph (mcg/tools/thermo/rrho.py, commit cef1c837). The
nonlinear arithmetic is unchanged, so the nonlinear curves are bit-equal to the
platform's on one host. The platform added 4R for every molecule; a linear
molecule now takes 7R/2.

Frequencies are wavenumbers in cm^-1, as MolecularFrequency serves them. A
non-positive frequency is refused: thermochemistry on a saddle point has no
meaning.
"""
from __future__ import annotations

import math
from collections.abc import Sequence

# R = N_A k_B, exact in the SI since 2019; J/(mol K).
R_J_PER_MOLK = 8.31446261815324
# h c / k_B in cm K (second radiation constant c_2, CODATA 2018).
_HC_OVER_K_CMK = 1.438776877

__all__ = ["R_J_PER_MOLK", "cp_table"]


def _mode_cv(nu_cm: float, temperature_K: float) -> float:
    """Quantum harmonic Cv of one mode, J/(mol K)."""
    x = _HC_OVER_K_CMK * nu_cm / temperature_K
    x = min(x, 500.0)  # exp guard: the contribution is already about 0 there
    ex = math.exp(-x)  # the exp(-x) form is stable for large x
    return R_J_PER_MOLK * x * x * ex / (1.0 - ex) ** 2


def _cv_vibrational(frequencies_cm: Sequence[float], temperature_K: float,
                    treatment: str, nu0_cm: float) -> float:
    if temperature_K <= 0:
        raise ValueError(f"temperature must be positive, got {temperature_K}")
    total = 0.0
    for nu in frequencies_cm:
        if nu <= 0:
            raise ValueError(
                f"non-positive frequency {nu} cm^-1: optimize to a true "
                f"minimum before thermochemistry")
        cv = _mode_cv(nu, temperature_K)
        if treatment == "qrrho":
            w = 1.0 / (1.0 + (nu0_cm / nu) ** 4)
            cv = w * cv + (1.0 - w) * 0.5 * R_J_PER_MOLK
        total += cv
    return total


def cp_table(frequencies_cm: Sequence[float], temperatures_K: Sequence[float], *,
             linear: bool, nu0_cm: float = 50.0) -> dict:
    """Ideal-gas Cp(T) of one molecule from its normal modes.

    ``frequencies_cm`` are the 3N-6 (nonlinear) or 3N-5 (linear) internal
    modes in cm^-1. Returns ``temperatures_K``, ``harmonic_J_per_molK``,
    ``qrrho_J_per_molK``, ``classical_J_per_molK`` (one value per
    temperature) and ``n_modes``. ValueError for a non-positive frequency or
    temperature.
    """
    external = 3.5 if linear else 4.0
    n_modes = len(frequencies_cm)
    temps = list(temperatures_K)

    def cp(t: float, treatment: str) -> float:
        return (_cv_vibrational(frequencies_cm, t, treatment, nu0_cm)
                + external * R_J_PER_MOLK)

    return {
        "temperatures_K": temps,
        "harmonic_J_per_molK": [cp(t, "harmonic") for t in temps],
        "qrrho_J_per_molK": [cp(t, "qrrho") for t in temps],
        "classical_J_per_molK": [(n_modes + external) * R_J_PER_MOLK for _ in temps],
        "n_modes": n_modes,
    }
