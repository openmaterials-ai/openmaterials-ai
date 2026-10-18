"""The cure-kinetics evaluators (omai.cure_kinetics.evaluate) against the map's
own edges, and the openmaterials-ai representation that registers them.

Every parameter set below is a SYNTHETIC test input: round numbers chosen to
cover the regimes (first order, autocatalytic, pure autocatalysis, a large m
with an induction period, n < 1), not a fit to any resin.
"""
from __future__ import annotations

import hashlib
import math

import pytest
import sympy as sp

from omai.cure_kinetics.evaluate import cure_conversion, glass_transition_temperature
from omai.cure_kinetics.operator.edges import (
    dibenedetto_glass_transition,
    kamal_cure_conversion,
)
from omai.map_data import DOMAINS, build_codes
from omai.render import KINETICS_HASH_KEYS, _sha256, canonical_params

R = 8.31446261815324  # N_A k_B, exact
N_A, K_B = 6.02214076e23, 1.380649e-23

SYNTHETIC = {
    "first_and_autocatalytic": dict(a1_pref_per_s=1e3, e1_J_per_mol=5e4,
                                    a2_pref_per_s=1e5, e2_J_per_mol=5e4, m=1.0, n=1.5),
    "orders_half_and_two": dict(a1_pref_per_s=1e4, e1_J_per_mol=5e4,
                                a2_pref_per_s=1e6, e2_J_per_mol=5.5e4, m=0.5, n=2.0),
    "pure_autocatalysis": dict(a1_pref_per_s=0.0, e1_J_per_mol=5e4,
                               a2_pref_per_s=1e5, e2_J_per_mol=5e4, m=1.0, n=1.0),
    "induction": dict(a1_pref_per_s=1e4, e1_J_per_mol=6e4,
                      a2_pref_per_s=1e8, e2_J_per_mol=6e4, m=2.5, n=1.5),
    "order_below_one": dict(a1_pref_per_s=1e3, e1_J_per_mol=5e4,
                            a2_pref_per_s=1e4, e2_J_per_mol=5e4, m=1.0, n=0.7),
}
_KEYS = ("a1_pref_per_s", "e1_J_per_mol", "a2_pref_per_s", "e2_J_per_mol", "m", "n")

# The rate law read off the edge itself: its formula is t = integral of
# d alpha' / rate(alpha'), so the integrand is 1 / rate.
_INTEGRAND = kamal_cure_conversion.formula.rhs.function
_KS = {s.name: s for s in _INTEGRAND.free_symbols}
_RATE = sp.lambdify(
    [_KS[n] for n in ("A_{1,cure}", "E_{1,cure}", "A_{2,cure}", "E_{2,cure}",
                      "m_{cure}", "n_{cure}", "T", "\\alpha'")],
    (1 / _INTEGRAND).subs({_KS["N_A"]: N_A, _KS["k_B"]: K_B}), "math")
_DIB = dibenedetto_glass_transition.formula.rhs
_DS = {s.name: s for s in _DIB.free_symbols}
_TG = sp.lambdify([_DS[n] for n in ("T_{g0}", "T_{g\\infty}", "\\lambda_{DiB}", "\\alpha_{cure}")],
                  _DIB, "math")


def _k(a_pref, e, temperature_K):
    return a_pref * math.exp(-e / (R * temperature_K))


def _rk4(p, temperature_K, hold_s, a0, n_steps=64000):
    """Fixed-step classical RK4 on the edge's rate, at a step count where its
    error is far below the tolerance."""
    args = [p[k] for k in _KEYS] + [temperature_K]

    def rate(a):
        return _RATE(*args, min(max(a, 0.0), 1.0 - 1e-12))

    dt, a = hold_s / n_steps, a0
    for _ in range(n_steps):
        r1 = rate(a)
        r2 = rate(a + 0.5 * dt * r1)
        r3 = rate(a + 0.5 * dt * r2)
        r4 = rate(a + dt * r3)
        a = min(a + dt / 6.0 * (r1 + 2 * r2 + 2 * r3 + r4), 1.0)
    return a


@pytest.mark.parametrize("name", sorted(SYNTHETIC))
@pytest.mark.parametrize("temperature_K,hold_s", [(330.0, 3600.0), (360.0, 1800.0)])
def test_agrees_with_rk4_on_the_edge_rate(name, temperature_K, hold_s):
    p = SYNTHETIC[name]
    got = cure_conversion(p, temperature_K, hold_s, 1e-4)
    assert 0.0 < got < 1.0
    assert abs(got - _rk4(p, temperature_K, hold_s, 1e-4)) < 1e-9


def test_first_order_limit():
    # m = 0, n = 1: d alpha/dt = (k1 + k2)(1 - alpha), so alpha = 1 - (1 - alpha_0) e^(-k t).
    p = dict(a1_pref_per_s=1e3, e1_J_per_mol=5e4, a2_pref_per_s=2e3,
             e2_J_per_mol=5.5e4, m=0.0, n=1.0)
    k = _k(1e3, 5e4, 350.0) + _k(2e3, 5.5e4, 350.0)
    for a0 in (0.0, 1e-4, 0.3):
        for t in (1.0, 600.0, 7200.0):
            exact = 1.0 - (1.0 - a0) * math.exp(-k * t)
            assert abs(cure_conversion(p, 350.0, t, a0) - exact) < 1e-12


@pytest.mark.parametrize("p,temperature_K", [
    (dict(a1_pref_per_s=1e3, e1_J_per_mol=5e4, a2_pref_per_s=1e5, e2_J_per_mol=5e4, m=1.0, n=1.0), 360.0),
    # k1 / k2 = 1e-27: the start from alpha = 0 is set by k_2 alpha^m, not by alpha alone.
    (dict(a1_pref_per_s=1e-30, e1_J_per_mol=0.0, a2_pref_per_s=1e-3, e2_J_per_mol=0.0, m=1.0, n=1.0), 300.0),
])
def test_autocatalytic_closed_form_from_zero(p, temperature_K):
    # m = 1, n = 1 separates by partial fractions:
    # t = [ln((k1 + k2 a) / (k1 + k2 a0)) - ln((1 - a) / (1 - a0))] / (k1 + k2).
    k1 = _k(p["a1_pref_per_s"], p["e1_J_per_mol"], temperature_K)
    k2 = _k(p["a2_pref_per_s"], p["e2_J_per_mol"], temperature_K)
    for a0 in (0.0, 1e-4):
        for a in (0.01, 0.5, 0.99):
            t = (math.log((k1 + k2 * a) / (k1 + k2 * a0))
                 - math.log((1 - a) / (1 - a0))) / (k1 + k2)
            assert abs(cure_conversion(p, temperature_K, t, a0) - a) < 1e-12
    # A hold too short to reach the start point: alpha = k1 t.
    assert cure_conversion(p, temperature_K, 1e-30, 0.0) == pytest.approx(k1 * 1e-30, rel=1e-12)


def test_order_below_one_completes_in_finite_time():
    # k2 = 0, m = 0: (1 - a)^(1 - n) = (1 - a0)^(1 - n) - (1 - n) k1 t until a = 1.
    n, a0 = 0.5, 1e-4
    p = dict(a1_pref_per_s=1e3, e1_J_per_mol=5e4, a2_pref_per_s=0.0,
             e2_J_per_mol=5e4, m=0.0, n=n)
    k1 = _k(1e3, 5e4, 360.0)
    t_full = (1 - a0) ** (1 - n) / ((1 - n) * k1)
    for f in (0.3, 0.9, 0.999):
        exact = 1 - ((1 - a0) ** (1 - n) - (1 - n) * k1 * f * t_full) ** (1 / (1 - n))
        assert abs(cure_conversion(p, 360.0, f * t_full, a0) - exact) < 1e-12
    assert cure_conversion(p, 360.0, 1.5 * t_full, a0) == 1.0


def test_edges_of_the_domain():
    p = SYNTHETIC["pure_autocatalysis"]
    assert cure_conversion(p, 360.0, 3600.0, 0.0) == 0.0  # k1 = 0 from alpha = 0: no reaction
    assert cure_conversion(p, 360.0, 0.0, 0.25) == 0.25
    # n = 1.5 approaches full cure algebraically: d(1 - a)/dt -> -k (1 - a)^n with
    # k = k1 + k2, so 1 - a -> ((n - 1) k t)^(-1 / (n - 1)) at long times.
    k = _k(1e3, 5e4, 360.0) + _k(1e5, 5e4, 360.0)
    gap = 1.0 - cure_conversion(SYNTHETIC["first_and_autocatalytic"], 360.0, 1e9, 1e-4)
    assert gap == pytest.approx((0.5 * k * 1e9) ** -2, rel=1e-3)
    # n = 1 approaches it exponentially and reads 1.0 once 1 - a is below float resolution.
    assert cure_conversion(dict(p, a1_pref_per_s=1e3), 360.0, 1e5, 1e-4) == 1.0


@pytest.mark.parametrize("bad", [
    dict(temperature_K=0.0), dict(hold_time_s=-1.0), dict(alpha_0=1.0), dict(alpha_0=-0.1),
    dict(kinetics={"a1_pref_per_s": -1.0}), dict(kinetics={"m": float("inf")}),
    dict(kinetics={"e2_J_per_mol": float("nan")}),
])
def test_refuses_bad_inputs(bad):
    args = dict(kinetics=SYNTHETIC["first_and_autocatalytic"], temperature_K=360.0,
                hold_time_s=10.0, alpha_0=1e-4)
    args.update({k: v for k, v in bad.items() if k != "kinetics"})
    args["kinetics"] = args["kinetics"] | bad.get("kinetics", {})
    with pytest.raises(ValueError):
        cure_conversion(**args)


def test_refuses_a_missing_key():
    p = {k: v for k, v in SYNTHETIC["first_and_autocatalytic"].items() if k != "n"}
    with pytest.raises(KeyError):
        cure_conversion(p, 360.0, 10.0, 1e-4)


@pytest.mark.parametrize("key,value", [("l_order", 1.7), ("amax_per_K", 0.02), ("bmax", 7.9)])
def test_other_rate_laws_are_refused(key, value):
    with pytest.raises(ValueError, match=key):
        cure_conversion(SYNTHETIC["first_and_autocatalytic"] | {key: value}, 360.0, 60.0, 1e-4)


def test_dibenedetto_follows_the_edge():
    tg = dict(tg0_K=250.0, tg_inf_K=450.0, lam=0.5)
    assert glass_transition_temperature(tg, 0.0) == 250.0
    assert glass_transition_temperature(tg, 1.0) == pytest.approx(450.0, abs=1e-12)
    # 250 + 200 * 0.5 * 0.5 / (1 - 0.5 * 0.5) = 250 + 50 / 0.75
    assert glass_transition_temperature(tg, 0.5) == pytest.approx(250.0 + 50.0 / 0.75, abs=1e-12)
    for a in (0.1, 0.37, 0.8):
        assert glass_transition_temperature(tg, a) == pytest.approx(_TG(250.0, 450.0, 0.5, a), rel=1e-15)
    for bad_tg, bad_a in ((tg, 1.01), (tg | {"lam": 0.0}, 0.5), (tg | {"tg0_K": float("inf")}, 0.5)):
        with pytest.raises(ValueError):
            glass_transition_temperature(bad_tg, bad_a)


def test_canonical_bytes():
    p = dict(a1_pref_per_s=1000, e1_J_per_mol=5e4, a2_pref_per_s=1e5,
             e2_J_per_mol=5e4, m=1, n=1.5, l_order=None, source="not hashed")
    blob = (b'{"a1_pref_per_s":1000.0,"a2_pref_per_s":100000.0,"e1_J_per_mol":50000.0,'
            b'"e2_J_per_mol":50000.0,"m":1.0,"n":1.5}')
    assert canonical_params(p, KINETICS_HASH_KEYS) == blob
    assert _sha256(p, KINETICS_HASH_KEYS) == hashlib.sha256(blob).hexdigest()


def test_registered_as_the_code_openmaterials_ai():
    entry = build_codes(DOMAINS)["openmaterials-ai"]
    assert set(entry) == {"CureConversion", "GlassTransitionTemperature"}
    assert entry["CureConversion"]["api"] == "omai.cure_kinetics.evaluate.cure_conversion"
    assert entry["GlassTransitionTemperature"]["unit"] == "kelvin"


def test_a_subnormal_first_rate_does_not_raise():
    # k1 / k2 underflows to 0; the start point uses log(k1) - log(k2).
    p = dict(a1_pref_per_s=1e-320, e1_J_per_mol=0.0, a2_pref_per_s=1e5,
             e2_J_per_mol=0.0, m=1.0, n=1.0)
    assert 0.0 <= cure_conversion(p, 300.0, 3600.0, 0.0) <= 1.0
