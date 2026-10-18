"""Evaluators of the cure-kinetics edges: one function per node.

cure_conversion evaluates kamal_cure_conversion, the isothermal hold time as
the integral of d alpha / rate from alpha_0, solved for alpha. No time step
enters the value: the integral is taken in s = ln(alpha / (1 - alpha)), where
both the slow start and the approach to full cure are smooth, by 20-point
Gauss-Legendre on panels of width 1/2, and the root by safeguarded Newton.
glass_transition_temperature evaluates dibenedetto_glass_transition.

Parameter sets are read by the keys omai.render hashes into a record's
conditions (KAMAL_KEYS, TG_KEYS), so the numbers a value is computed from are
the numbers its conditions identify.
"""
from __future__ import annotations

import math

import numpy as np

from omai.render import KAMAL_KEYS, KINETICS_HASH_KEYS, TG_KEYS

# R = N_A k_B, both exact in the SI since 2019; J/(mol K).
_R_GAS = 6.02214076e23 * 1.380649e-23
# Keys of the rate laws kamal_cure_conversion does not model (a separate order
# on the k_1 term, a fitted maximum conversion).
_OTHER_LAW_KEYS = tuple(k for k in KINETICS_HASH_KEYS if k not in KAMAL_KEYS)

_NODES, _WEIGHTS = np.polynomial.legendre.leggauss(20)
_PANEL = 0.5
# At s = 40, 1 - alpha = 4.2e-18, below half an ulp of 1.0: alpha is 1.0 in
# float64 from here on, for any reaction order.
_S_FULL = 40.0


def _numbers(params: dict, keys: tuple[str, ...]) -> dict[str, float]:
    """The finite numbers of ``keys`` in a parameter set; KeyError when one is
    missing, ValueError when one is not a finite number."""
    out = {}
    for key in keys:
        value = float(params[key])
        if not math.isfinite(value):
            raise ValueError(f"{key} = {value} is not finite")
        out[key] = value
    return out


def cure_conversion(kinetics: dict, temperature_K: float, hold_time_s: float,
                    alpha_0: float) -> float:
    """Degree of cure after an isothermal hold of ``hold_time_s`` at
    ``temperature_K`` from ``alpha_0``, under d alpha/dt = (k_1 + k_2
    alpha^m)(1 - alpha)^n with k_i = A_i exp(-E_i / (R T)).

    ``kinetics`` carries KAMAL_KEYS (a1_pref_per_s, e1_J_per_mol,
    a2_pref_per_s, e2_J_per_mol, m, n); other keys are ignored. Raises
    ValueError for another rate law (l_order, amax_per_K or bmax set), a
    non-positive temperature, a negative hold, alpha_0 outside [0, 1), or
    negative constants; KeyError for a missing key. For n < 1 the cure
    completes in finite time and the value is 1.0 from then on; for n >= 1 it
    approaches 1 and reads 1.0 once 1 - alpha is below float resolution.
    """
    other = [k for k in _OTHER_LAW_KEYS if kinetics.get(k) is not None]
    if other:
        raise ValueError(
            f"{', '.join(other)} set: kamal_cure_conversion is the single "
            "(1 - alpha)^n Kamal-Sourour form only")
    p = _numbers(kinetics, KAMAL_KEYS)
    if min(p.values()) < 0:
        raise ValueError(f"negative rate-law constant in {p}")
    if not temperature_K > 0:
        raise ValueError(f"temperature must be positive, got {temperature_K}")
    if not hold_time_s >= 0:
        raise ValueError(f"hold time must be non-negative, got {hold_time_s}")
    if not 0.0 <= alpha_0 < 1.0:
        raise ValueError(f"alpha_0 must be in [0, 1), got {alpha_0}")
    k1 = p["a1_pref_per_s"] * math.exp(-p["e1_J_per_mol"] / (_R_GAS * temperature_K))
    k2 = p["a2_pref_per_s"] * math.exp(-p["e2_J_per_mol"] / (_R_GAS * temperature_K))
    m, n = p["m"], p["n"]
    r0 = k1 + (k2 if m == 0 else 0.0)  # the rate at alpha = 0
    if hold_time_s == 0 or k1 == k2 == 0 or (alpha_0 == 0 and r0 == 0):
        return float(alpha_0)   # nothing reacts

    def dt_ds(s):
        # d t / d s = alpha (1 - alpha) / rate, with 1 - alpha computed
        # without cancellation.
        a = 1.0 / (1.0 + np.exp(-s))
        gap = 1.0 / (1.0 + np.exp(s))
        return a * gap ** (1.0 - n) / (k1 + k2 * a**m)

    def time(lo: float, hi: float) -> float:
        half = 0.5 * (hi - lo)
        return float(half * np.dot(_WEIGHTS, dt_ds(lo + half * (_NODES + 1.0))))

    remaining = hold_time_s
    if alpha_0 > 0:
        lo = math.log(alpha_0 / (1.0 - alpha_0))
    else:
        # From alpha = 0 the rate starts at r0 > 0. Start where alpha < e^-40
        # and k_2 alpha^m < e^-40 k_1 (not below s = -700), so the time to
        # reach alpha is alpha / r0 to float precision.
        # ponytail: the -700 floor keeps exp finite; for k_1 below about
        # 1e-290 /s the start time is overestimated. Integrate from a
        # log-spaced start if such rates ever matter.
        lo = -_S_FULL
        if m > 0 and k2 > 0:
            lo = max(min(lo, (math.log(k1) - math.log(k2) - _S_FULL) / m), -700.0)
        remaining -= 1.0 / (1.0 + math.exp(-lo)) / r0
        if remaining <= 0:
            return r0 * hold_time_s
    while lo < _S_FULL:
        hi = min(lo + _PANEL, _S_FULL)
        dt = time(lo, hi)
        if dt >= remaining:
            # The hold ends in this panel: Newton on time(lo, s) = remaining,
            # whose derivative is dt_ds(s) > 0, kept inside [lo, hi].
            left, right, s = lo, hi, lo + (hi - lo) * remaining / dt
            for _ in range(60):
                f = time(lo, s) - remaining
                if f == 0:
                    break
                if f > 0:
                    right = s
                else:
                    left = s
                step = f / float(dt_ds(np.float64(s)))
                s_next = s - step
                if not left < s_next < right:
                    s_next = 0.5 * (left + right)
                if abs(s_next - s) <= 1e-13 * max(1.0, abs(s)):
                    s = s_next
                    break
                s = s_next
            return 1.0 / (1.0 + math.exp(-s))
        remaining -= dt
        lo = hi
    return 1.0


def glass_transition_temperature(tg: dict, conversion: float) -> float:
    """T_g in K at degree of cure ``conversion`` through the DiBenedetto
    relation, Pascault-Williams form: T_g = T_g0 + (T_g_inf - T_g0) lambda
    alpha / (1 - (1 - lambda) alpha).

    ``tg`` carries TG_KEYS (tg0_K, tg_inf_K, lam). Raises ValueError for a
    conversion outside [0, 1] or a non-positive lambda or temperature,
    KeyError for a missing key."""
    p = _numbers(tg, TG_KEYS)
    if not 0.0 <= conversion <= 1.0:
        raise ValueError(f"degree of cure {conversion} is outside [0, 1]")
    if min(p.values()) <= 0:
        raise ValueError(f"tg0_K, tg_inf_K and lam must be positive, got {p}")
    lam = p["lam"]
    return p["tg0_K"] + (p["tg_inf_K"] - p["tg0_K"]) * lam * conversion / (
        1.0 - (1.0 - lam) * conversion)
