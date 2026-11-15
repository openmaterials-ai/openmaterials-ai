"""Evaluator of compute_harmonic_migration_prefactor: the classical harmonic
transition-state-theory (Vineyard) prefactor of one hop from the normal modes
of its minimum and its first-order saddle.

Vineyard, J. Phys. Chem. Solids 3, 121 (1957):

    nu* = prod_{i=1..n} nu_i(min) / prod_{j=1..n-1} nu_j(saddle)

over the real modes, the saddle's one imaginary mode excluded. With every atom
displaced, bulk or slab, the three rigid translations are zero modes; they are
projected out (``projected=True``) and n = 3N - 3. With a listed subset of M
atoms displaced and the rest held, nothing is projected (``projected=False``)
and n = 3M: the value approximates the full ratio, and the saddle order is
checked only within that subspace. n factors over n - 1 leave one frequency
factor, so the cyclic or angular convention of the inputs carries into the
result: angular inputs give 2 pi nu*. The inputs are cyclic, in linear THz,
imaginary modes serialized negative, and so is the result.

The value is the classical high-temperature limit: it holds for k_B T >> h nu_i
over the modes that change between the minimum and the saddle. Zero-point and
Wigner tunnelling corrections are excluded. Tunnelling dominates below the
crossover temperature h |nu_imag| / (2 pi k_B), so being above it is necessary,
not sufficient.

The validity contract is the evaluator's, and none of it is opt-in:

- every input is a one-dimensional sequence of finite real numbers, or a finite
  real scalar (ValueError otherwise, also for str, bytes, bool and complex);
- the minimum has no imaginary and no soft mode, the saddle exactly one
  imaginary mode and no soft one, and the saddle one real mode fewer than the
  minimum (imaginary below -floor, soft within floor of zero, both bounds
  inclusive, real above floor);
- with ``projected=True`` the three residual translational frequencies of each
  frame are required and must stay at or below half the floor, else the forces
  are too noisy for the softest modes; with ``projected=False`` none may be
  passed;
- the residual force of each frame is required: the largest per-atom force norm
  over the free atoms, the ase fmax convention. A frame above
  ``max_residual_force_eV_per_A`` (0.05 eV/A by default) is refused. The bound
  is a convention and does not guarantee stationarity for soft modes: a 2 THz
  mode of a 32 amu atom has a force constant of about 0.52 eV/A^2, so 0.05
  eV/A leaves it displaced by about 0.1 A;
- ln nu* is a sum of logarithms, and a value outside the double range, on
  either side, is refused rather than rounded to 0 or inf.

``eigenvalue_noise_THz2`` is eps, a bound on every |delta lambda| of the
squared cyclic frequencies lambda = nu^2 (linear THz^2), for example from
Weyl's inequality and the norm of the Hessian's error. Then
``ln_nu_star_error_bound`` = 0.5 sum -log1p(-eps / lambda) over the real modes
of both spectra is an upper bound on |delta ln nu*|, exact per mode and valid to
all orders when every |delta lambda| <= eps: each mode's term is the larger of
its two one-sided shifts, since -log1p(-x) >= log1p(x). It is computed in log
space so nothing underflows. An accepted eps can still push a near-floor real
mode under the floor, and the bound still holds, because eps < min lambda keeps
every shifted lambda positive. The imaginary mode does not enter the ratio, so it
does not enter the bound. eps at or above floor^2, the smallest real lambda or
|lambda_imag|, compared within a relative 1e-12 so that floor**2 itself is
refused despite rounding, is refused: eps at or above min lambda or
|lambda_imag| could move a mode through zero, and eps at or above floor^2 could
move one from zero to the floor.
The bound excludes finite-difference truncation, anharmonicity, the residual
force and the subset approximation.

A refusal returns ``nu_star_THz`` None with the reason, never a number, and its
``imaginary_THz`` and ``crossover_temperature_K`` are None.
"""
from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

__all__ = [
    "CROSSOVER_K_PER_THZ",
    "DEFAULT_MAX_RESIDUAL_FORCE_EV_PER_A",
    "classify_modes",
    "harmonic_migration_prefactor",
]

#: h / (2 pi k_B) in K per linear THz: the crossover temperature of a barrier
#: whose imaginary mode is |nu| THz is |nu| times this, about 7.6382 K/THz.
#: Exact SI h and k_B.
CROSSOVER_K_PER_THZ = 6.62607015e-34 * 1e12 / (2.0 * math.pi * 1.380649e-23)

#: Largest residual force on either frame, eV/A, for which the frame is
#: accepted as stationary. A convention, not a guarantee for soft modes.
DEFAULT_MAX_RESIDUAL_FORCE_EV_PER_A = 0.05

# ln of the largest finite double and of the smallest positive normal double.
_LN_MAX = math.log(1.7976931348623157e308)
_LN_MIN = math.log(2.2250738585072014e-308)

_REAL = (int, float, np.integer, np.floating)

# Relative tolerance of the noise thresholds: 0.05 * 0.05 rounds to
# 0.0025000000000000005, and eps = 0.0025 must still count as floor**2.
_THRESHOLD_RTOL = 1e-12


def _at_or_above(value: float, threshold: float) -> bool:
    return value >= threshold or math.isclose(value, threshold, rel_tol=_THRESHOLD_RTOL)


def _real_scalar(name: str, value) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, _REAL):
        raise ValueError(f"{name} must be a real number, got {type(value).__name__}")
    try:
        v = float(value)
    except OverflowError as exc:  # an int beyond the double range
        raise ValueError(f"{name} is outside the range of a double") from exc
    if not math.isfinite(v):
        raise ValueError(f"{name} must be finite, got {v!r}")
    return v


def _real_vector(name: str, values) -> list[float]:
    """A one-dimensional sequence of finite real numbers, as floats."""
    if isinstance(values, (str, bytes, bytearray)):
        raise ValueError(f"{name} must be a one-dimensional sequence of real numbers, "
                         f"got {type(values).__name__}")
    try:
        arr = np.asarray(values, dtype=object)
    except Exception as exc:  # ragged nesting and the like
        raise ValueError(f"{name} is not a one-dimensional sequence: {exc}") from exc
    if arr.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional, got ndim {arr.ndim}")
    return [_real_scalar(f"{name}[{i}]", x) for i, x in enumerate(arr)]


def _positive(name: str, value) -> float:
    v = _real_scalar(name, value)
    if v <= 0.0:
        raise ValueError(f"{name} must be positive, got {v!r}")
    return v


def classify_modes(freqs_THz, floor_THz) -> dict:
    """Counts of imaginary (below -floor), soft (within floor of zero, both
    bounds inclusive) and real (above floor) modes."""
    floor = _positive("floor_THz", floor_THz)
    f = _real_vector("freqs_THz", freqs_THz)
    return {
        "imaginary": sum(1 for x in f if x < -floor),
        "soft": sum(1 for x in f if abs(x) <= floor),
        "real": sum(1 for x in f if x > floor),
    }


def harmonic_migration_prefactor(
    freqs_min_THz: Sequence[float],
    freqs_saddle_THz: Sequence[float],
    floor_THz: float,
    *,
    projected: bool,
    residual_force_eV_per_A: Sequence[float],
    translational_THz: Sequence[Sequence[float]] | None = None,
    max_residual_force_eV_per_A: float = DEFAULT_MAX_RESIDUAL_FORCE_EV_PER_A,
    eigenvalue_noise_THz2: float | None = None,
) -> dict:
    """The harmonic migration prefactor nu* (linear THz) of a minimum and a
    first-order saddle, or the reason it is undefined.

    ``freqs_min_THz`` and ``freqs_saddle_THz`` are the cyclic normal-mode
    frequencies in linear THz, imaginary negative. ``projected`` says whether
    every atom was displaced and the rigid translations projected out (True)
    or a subset was displaced with nothing projected (False). It has no
    default. ``residual_force_eV_per_A`` is the largest per-atom force norm
    over the free atoms of the minimum and of the saddle frame (ase fmax).
    ``translational_THz`` is two triples, the residual translational
    frequencies of the minimum and of the saddle, required when projected and
    refused otherwise. ``eigenvalue_noise_THz2`` is eps, a bound on every
    |delta (nu^2)| in linear THz^2.

    Returns ``nu_star_THz``, ``ln_nu_star_THz`` (ln of nu* in THz),
    ``ln_nu_star_error_bound`` (an upper bound on |delta ln nu*|, None
    without eps), ``modes_min`` and
    ``modes_saddle`` (classify_modes counts), ``imaginary_THz``,
    ``crossover_temperature_K`` and ``reason`` (None when defined). ValueError
    for an input of the wrong type, shape or range.
    """
    if not isinstance(projected, (bool, np.bool_)):
        raise ValueError(f"projected must be True or False, got {type(projected).__name__}")
    projected = bool(projected)
    floor = _positive("floor_THz", floor_THz)
    fm = _real_vector("freqs_min_THz", freqs_min_THz)
    fs = _real_vector("freqs_saddle_THz", freqs_saddle_THz)
    forces = _real_vector("residual_force_eV_per_A", residual_force_eV_per_A)
    if len(forces) != 2 or min(forces) < 0.0:
        raise ValueError(
            "residual_force_eV_per_A must be two nonnegative values, the minimum's and the "
            f"saddle's, got {residual_force_eV_per_A!r}")
    max_force = _positive("max_residual_force_eV_per_A", max_residual_force_eV_per_A)
    if projected:
        if translational_THz is None:
            raise ValueError("projected=True requires translational_THz: three residual "
                             "translational frequencies for each frame")
        try:
            frames = list(translational_THz)
        except TypeError as exc:
            raise ValueError("translational_THz must be two triples, the minimum's and the "
                             "saddle's") from exc
        if isinstance(translational_THz, (str, bytes, bytearray)) or len(frames) != 2:
            raise ValueError("translational_THz must be two triples, the minimum's and the saddle's")
        trans = [_real_vector(f"translational_THz[{k}]", t) for k, t in enumerate(frames)]
        if any(len(t) != 3 for t in trans):
            raise ValueError("translational_THz must hold three frequencies for each frame")
    elif translational_THz is not None:
        raise ValueError("projected=False projects nothing, so translational_THz must not be passed")
    else:
        trans = []
    eps = None
    if eigenvalue_noise_THz2 is not None:
        eps = _real_scalar("eigenvalue_noise_THz2", eigenvalue_noise_THz2)
        if eps < 0.0:
            raise ValueError(f"eigenvalue_noise_THz2 must be nonnegative, got {eps!r}")

    cm = classify_modes(fm, floor)
    cs = classify_modes(fs, floor)
    out = {
        "nu_star_THz": None,
        "ln_nu_star_THz": None,
        "ln_nu_star_error_bound": None,
        "modes_min": cm,
        "modes_saddle": cs,
        "imaginary_THz": None,
        "crossover_temperature_K": None,
        "reason": None,
    }

    def refuse(reasons: list[str]) -> dict:
        out["reason"] = "; ".join(reasons)
        return out

    reasons = []
    if cm["imaginary"] or cm["soft"]:
        reasons.append(
            f"the first structure is not a minimum: {cm['imaginary']} imaginary and "
            f"{cm['soft']} soft mode(s) within {floor} THz of zero")
    if cs["imaginary"] != 1 or cs["soft"]:
        reasons.append(
            f"the second structure is not a first-order saddle: {cs['imaginary']} "
            f"imaginary and {cs['soft']} soft mode(s)")
    if not reasons and cm["real"] != cs["real"] + 1:
        reasons.append(
            f"{cm['real']} real modes at the minimum and {cs['real']} at the saddle; "
            "they must differ by one")
    noise = max((abs(x) for t in trans for x in t), default=0.0)
    if noise > 0.5 * floor:
        reasons.append(
            f"a translational mode is {noise:.3g} THz, above half the {floor} THz floor: "
            "the forces are too noisy for the softest modes")
    if max(forces) > max_force:
        reasons.append(
            f"the residual forces are {forces[0]:.3g} eV/A (minimum) and {forces[1]:.3g} "
            f"eV/A (saddle), above {max_force} eV/A: a frame is not accepted as a stationary point")
    if reasons:
        return refuse(reasons)

    real_min = [x for x in fm if x > floor]
    real_sad = [x for x in fs if x > floor]
    imag = next(x for x in fs if x < -floor)
    if eps is not None:
        lam_real = [x * x for x in real_min + real_sad]
        lam_imag = imag * imag
        eps_reasons = []
        if _at_or_above(eps, floor * floor):
            eps_reasons.append(f"the eigenvalue noise {eps:.3g} THz^2 is at or above the floor squared")
        if lam_real and _at_or_above(eps, min(lam_real)):
            eps_reasons.append(f"the eigenvalue noise {eps:.3g} THz^2 is at or above the smallest real eigenvalue")
        if _at_or_above(eps, lam_imag):
            eps_reasons.append(f"the eigenvalue noise {eps:.3g} THz^2 is at or above the imaginary eigenvalue's magnitude")
        if eps_reasons:
            return refuse(eps_reasons + ["a mode could cross the floor or zero"])
        bound = 0.5 * math.fsum(-math.log1p(-eps / lam) for lam in lam_real)
        if not math.isfinite(bound):
            return refuse([f"the error bound of ln nu* is not finite ({bound!r})"])
    ln_nu = math.fsum(math.log(x) for x in real_min) - math.fsum(math.log(x) for x in real_sad)
    if not _LN_MIN <= ln_nu <= _LN_MAX:
        side = "underflows" if ln_nu < _LN_MIN else "overflows"
        return refuse([f"ln nu* = {ln_nu:.6g} (THz) {side} a double: check the units and the mode lists"])
    out["ln_nu_star_THz"] = ln_nu
    out["nu_star_THz"] = math.exp(ln_nu)
    out["imaginary_THz"] = imag
    out["crossover_temperature_K"] = abs(imag) * CROSSOVER_K_PER_THZ
    if eps is not None:
        out["ln_nu_star_error_bound"] = bound
    return out
