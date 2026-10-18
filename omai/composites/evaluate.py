"""Evaluators of the Nan effective-medium edges: one function per node.

nan_kappa_random evaluates nan_effective_kappa; nan_kappa_aligned evaluates
nan_effective_kappa_aligned's declared value, al33. Both use
the interface as a per-direction series film across each full inclusion
dimension, kc_ii = k_ii / (1 + 2 R k_ii / d_i) with R = 1/G (Nan et al.,
Appl. Phys. Lett. 85, 3549 (2004)), in the mixing formulas of Nan et al.,
J. Appl. Phys. 81, 6692 (1997), exactly as the map's edges write them.
aligned_tensor_components also returns al11, the edge's auxiliary formula,
which is not a node value.

Inputs are the conditions a composite record carries (NAN_KEYS): matrix and
filler conductivities in W/(m K), the filler's equatorial and polar
dimensions in um, the interface conductance in MW/(m^2 K) and the volume
fraction. The orientation is the node's, never an input; the Kapitza radius
is km / G, derived; a kapitza_radius_nm that disagrees with it is refused.
"""
from __future__ import annotations

import math

NAN_KEYS = ("km_W_per_mK", "k11_W_per_mK", "k33_W_per_mK", "d1_um", "d3_um",
            "G_MW_per_m2K", "f")


def _depolarization_factors(aspect_ratio: float) -> tuple[float, float]:
    """(L11, L33) of a spheroid with polar axis 3 and aspect ratio p = d3/d1,
    as the edge depolarization_factors writes them; 2 L11 + L33 = 1. Sphere (1/3,
    1/3), long fiber (1/2, 0), thin disk (0, 1)."""
    p = aspect_ratio
    if not (math.isfinite(p) and p > 0):
        raise ValueError(f"aspect ratio must be positive and finite, got {p}")
    # ponytail: the closed forms cancel as e -> 0 (about 1e-7 relative at
    # |p - 1| = 1e-9); a series in e would remove it if a near-sphere matters.
    if abs(p - 1.0) < 1e-9:
        return (1.0 / 3.0, 1.0 / 3.0)
    if p > 1.0:  # prolate (fiber)
        e = math.sqrt(1.0 - 1.0 / (p * p))
        l33 = ((1.0 - e * e) / e**3) * (math.atanh(e) - e)
    else:        # oblate (platelet)
        e = math.sqrt(1.0 / (p * p) - 1.0)
        l33 = ((1.0 + e * e) / e**3) * (e - math.atan(e))
    return ((1.0 - l33) / 2.0, l33)


def _terms(params: dict) -> tuple[float, float, float, float, float, float]:
    """km, f, and (beta, L) per principal axis; ValueError on a non-finite or
    negative input, a non-positive km, dimension or G, or f outside [0, 1);
    KeyError on a missing key."""
    p = {k: float(params[k]) for k in NAN_KEYS}
    bad = [k for k, v in p.items() if not math.isfinite(v) or v < 0]
    if bad:
        raise ValueError(f"{', '.join(bad)} must be finite and non-negative, got {p}")
    for key in ("km_W_per_mK", "d1_um", "d3_um", "G_MW_per_m2K"):
        if p[key] == 0:
            raise ValueError(f"{key} must be positive")
    if not p["f"] < 1.0:
        raise ValueError(f"volume fraction must be in [0, 1), got {p['f']}")
    a_k = params.get("kapitza_radius_nm")
    derived = 1e3 * p["km_W_per_mK"] / p["G_MW_per_m2K"]
    if a_k is not None and not math.isclose(float(a_k), derived, rel_tol=1e-9):
        raise ValueError(f"kapitza_radius_nm {a_k} is not km / G = {derived} nm")
    km, f = p["km_W_per_mK"], p["f"]
    r = 1.0 / (p["G_MW_per_m2K"] * 1e6)       # interface resistance, m^2 K / W
    d1, d3 = p["d1_um"] * 1e-6, p["d3_um"] * 1e-6
    l11, l33 = _depolarization_factors(p["d3_um"] / p["d1_um"])
    kc11 = p["k11_W_per_mK"] / (1.0 + 2.0 * r * p["k11_W_per_mK"] / d1)
    kc33 = p["k33_W_per_mK"] / (1.0 + 2.0 * r * p["k33_W_per_mK"] / d3)
    b11 = (kc11 - km) / (km + l11 * (kc11 - km))
    b33 = (kc33 - km) / (km + l33 * (kc33 - km))
    return km, f, b11, l11, b33, l33


def nan_kappa_random(params: dict) -> float:
    """Effective conductivity in W/(m K) for randomly oriented filler, the
    value of ThermalConductivity[effective_medium=nan,orientation=random]."""
    km, f, b11, l11, b33, l33 = _terms(params)
    return km * (3.0 + f * (2.0 * b11 * (1.0 - l11) + b33 * (1.0 - l33))) \
        / (3.0 - f * (2.0 * b11 * l11 + b33 * l33))


def aligned_tensor_components(params: dict) -> dict[str, float]:
    """The perfectly aligned composite's tensor diagonal in W/(m K): al33
    along the spheroid's polar axis 3 (the fiber axis, the platelet normal;
    the node's value) and al11 perpendicular to it (the platelet plane; the
    edge's auxiliary formula, not a node value)."""
    km, f, b11, l11, b33, l33 = _terms(params)
    return {"al11": km * (1.0 + f * b11 * (1.0 - l11)) / (1.0 - f * b11 * l11),
            "al33": km * (1.0 + f * b33 * (1.0 - l33)) / (1.0 - f * b33 * l33)}


def nan_kappa_aligned(params: dict) -> float:
    """Effective conductivity al33 in W/(m K) along the spheroid's polar axis
    3 (the fiber axis, the platelet normal) for perfectly aligned filler, the
    value of
    ThermalConductivity[effective_medium=nan,orientation=aligned]."""
    return aligned_tensor_components(params)["al33"]
