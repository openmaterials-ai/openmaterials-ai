"""Edges of the cure-kinetics domain; each carries its method as a scheme.

  kamal_cure_conversion        : (Temperature,)    -> CureConversion              method=kamal_sourour
  dibenedetto_glass_transition : (CureConversion,) -> GlassTransitionTemperature  method=dibenedetto_pascault_williams
"""
from __future__ import annotations

import sympy as sp

from omai.cure_kinetics.operator.nodes import (
    CURE_CONVERSION,
    GLASS_TRANSITION_TEMPERATURE,
)
from omai.operator.operator import Operator
from omai.thermal_transport.operator.nodes import TEMPERATURE_STATE

_T = sp.Symbol("T", positive=True)
_N_A = sp.Symbol("N_A", positive=True)
_kB = sp.Symbol("k_B", positive=True)  # R = N_A k_B
_A1 = sp.Symbol("A_{1,cure}", nonnegative=True)  # A_1 = 0: pure autocatalysis, needs alpha_0 > 0
_A2 = sp.Symbol("A_{2,cure}", positive=True)
_E1 = sp.Symbol("E_{1,cure}", positive=True)
_E2 = sp.Symbol("E_{2,cure}", positive=True)
_m, _n = sp.symbols("m_{cure} n_{cure}", nonnegative=True)  # reaction orders
_t = sp.Symbol("t_{cure}", nonnegative=True)
_alpha = sp.Symbol(r"\alpha_{cure}", nonnegative=True)
_alpha0 = sp.Symbol(r"\alpha_{0,cure}", nonnegative=True)
_a = sp.Symbol(r"\alpha'", nonnegative=True)  # integration dummy

_k1 = _A1 * sp.exp(-_E1 / (_N_A * _kB * _T))
_k2 = _A2 * sp.exp(-_E2 / (_N_A * _kB * _T))

kamal_cure_conversion = Operator(
    name="kamal_cure_conversion",
    inputs=(TEMPERATURE_STATE,),
    outputs=(CURE_CONVERSION,),
    schemes={"method": "kamal_sourour"},
    formula=sp.Eq(_t, sp.Integral(
        1 / ((_k1 + _k2 * _a**_m) * (1 - _a)**_n), (_a, _alpha0, _alpha))),
    is_executable_in_sympy_override=False,
    description=(
        "Isothermal Kamal-Sourour cure in the single-(1 - alpha)^n form: d alpha/dt "
        "= (k_1 + k_2 alpha^m)(1 - alpha)^n, k_i = A_i exp(-E_i / (R T)), R = N_A "
        "k_B (Kamal and Sourour, Polym. Eng. Sci. 13, 59 (1973), "
        "doi:10.1002/pen.760130110). Separate exponents on the two terms, a "
        "temperature-dependent maximum conversion, and diffusion factors are other "
        "models. At constant T the law separates: t_cure = integral from alpha_0 to "
        "alpha of d alpha' / rate(alpha'), implicit in alpha, so not "
        "sympy-executable; the dimensional gate proves both sides are a time. "
        "A_1 = 0 (pure autocatalysis) needs alpha_0 > 0. With no diffusion control "
        "and constants fit to data before vitrification, the value loses validity "
        "near and past vitrification, where diffusion control slows the real "
        "cure; constants fit across vitrification absorb the slowdown and say "
        "nothing outside the fit window."
    ),
)

_Tg = sp.Symbol("T_g", positive=True)
_Tg0 = sp.Symbol("T_{g0}", positive=True)
_Tginf = sp.Symbol(r"T_{g\infty}", positive=True)
_lam = sp.Symbol(r"\lambda_{DiB}", positive=True)

dibenedetto_glass_transition = Operator(
    name="dibenedetto_glass_transition",
    inputs=(CURE_CONVERSION,),
    outputs=(GLASS_TRANSITION_TEMPERATURE,),
    schemes={"method": "dibenedetto_pascault_williams"},
    formula=sp.Eq(_Tg, _Tg0 + (_Tginf - _Tg0) * _lam * _alpha / (1 - (1 - _lam) * _alpha)),
    description=(
        "DiBenedetto relation, Pascault-Williams form: (T_g - T_g0) / (T_g_inf - "
        "T_g0) = lambda alpha / (1 - (1 - lambda) alpha) (DiBenedetto, J. Polym. "
        "Sci. B 25, 1949 (1987), doi:10.1002/polb.1987.090250914; Pascault and "
        "Williams, J. Polym. Sci. B 28, 85 (1990), doi:10.1002/polb.1990.090280107). "
        "T_g0 (uncured), T_g_inf (fully cured), and lambda (identified with "
        "Delta C_p_inf / Delta C_p0) ride in conditions. Takes any degree of cure, "
        "measured or computed; alpha = 0 gives T_g0 and alpha = 1 gives T_g_inf "
        "for any lambda."
    ),
)

EDGES: tuple[Operator, ...] = (kamal_cure_conversion, dibenedetto_glass_transition)
