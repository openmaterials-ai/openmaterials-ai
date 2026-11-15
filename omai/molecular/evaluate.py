"""Evaluator of rrho_ideal_gas_heat_capacity and its quasi-RRHO variant: the
ideal-gas Cp(T) of one gas-phase species.

cp_table sums the quantum harmonic Cv of each normal mode and adds the external
terms of an ideal gas: 3R/2 translation, rotation 0 (atom), R (linear) or 3R/2
(nonlinear), and R for Cp - Cv. The external term is therefore 5R/2 for an
atom, 7R/2 for a linear molecule and 4R for a nonlinear one. Three curves come
back:

- ``harmonic``: every mode a quantum harmonic oscillator.
- ``qrrho``: each mode's Cv interpolated toward the free-rotor limit R/2 with
  the weight w = 1 / (1 + (nu0/nu)^4), nu0 = 50 cm^-1 by default (the xtb
  default rotor cutoff). This is the temperature derivative of the quasi-RRHO
  enthalpy of Li, Gomes, Sharada, Bell and Head-Gordon, J. Phys. Chem. C 119,
  1840 (2015), H = w H_vib + (1 - w) RT/2. The weight depends on the frequency
  only, not on T, so dH/dT = w Cv_vib + (1 - w) R/2 term by term. The damping
  function is the one Grimme introduced for the entropy, Chem. Eur. J. 18,
  9955 (2012). Soft torsions then count as hindered rotors. nu0 is a
  condition of every qRRHO value.
- ``classical``: the equipartition limit (n_modes + c_ext) R, the value an
  unquantized force field gives.

Moved from MaterialsCodeGraph. The nonlinear arithmetic is unchanged, so the
nonlinear curves reproduce the platform's values. The platform added 4R for
every species. An atom now takes 5R/2 and a linear molecule 7R/2.

Frequencies are wavenumbers in cm^-1, as MolecularFrequency serves them. A mode
at or below 0 cm^-1 is refused, never inverted or dropped: thermochemistry on a
saddle point has no meaning.
"""
from __future__ import annotations

import math
from collections.abc import Sequence

# R = N_A k_B, exact in the SI since 2019; J/(mol K).
R_J_PER_MOLK = 8.31446261815324
# h c / k_B in cm K (second radiation constant c_2, CODATA 2018).
_HC_OVER_K_CMK = 1.438776877

# External term c_ext of Cp in units of R, per geometry: 3/2 translation, the
# rotation and 1 for Cp - Cv.
EXTERNAL_CP_OVER_R = {"atom": 2.5, "linear": 3.5, "nonlinear": 4.0}

__all__ = ["EXTERNAL_CP_OVER_R", "R_J_PER_MOLK", "cp_table"]


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
             geometry: str, nu0_cm: float = 50.0) -> dict:
    """Ideal-gas Cp(T) of one gas-phase species from its normal modes.

    ``geometry`` is "atom" (no modes), "linear" (3N-5 internal modes) or
    "nonlinear" (3N-6), and is a condition of every value. ``frequencies_cm``
    are the internal modes in cm^-1. Returns ``temperatures_K``,
    ``harmonic_J_per_molK``, ``qrrho_J_per_molK``, ``classical_J_per_molK``
    (one value per temperature) and ``n_modes``. ValueError for an unknown
    geometry, an atom with modes, a mode at or below 0 cm^-1 or a
    non-positive temperature.
    """
    if geometry not in EXTERNAL_CP_OVER_R:
        raise ValueError(f"geometry must be one of {sorted(EXTERNAL_CP_OVER_R)}, got {geometry!r}")
    if geometry == "atom" and len(frequencies_cm):
        raise ValueError(f"an atom has no normal modes, got {len(frequencies_cm)}")
    external = EXTERNAL_CP_OVER_R[geometry]
    n_modes = len(frequencies_cm)
    temps = list(temperatures_K)
    for t in temps:
        if t <= 0:
            raise ValueError(f"temperature must be positive, got {t}")

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
