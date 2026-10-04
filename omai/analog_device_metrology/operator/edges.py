r"""Operators (edges) of the analog-device-metrology domain.

Four closed forms the dimensional gate proves and apply_edge runs. Each operand
is a typed input's field symbol or a dimensioned Parameter on the edge. As
everywhere on the map, validity statements are documented, not enforced by
apply_edge.

  contract_device_conductance  ElectricalConductivity[carrier=electronic]
                               -> ConductanceState    G = sigma A / L
  contract_conductance_window  ConductanceState -> ConductanceWindow  W = G_c / G_min
  contract_state_coefficient_of_variation
                               ConductanceState -> StateCoefficientOfVariation
                                                       c = sigma_G / G_c
  apply_conductance_drift      ConductanceDriftExponent -> ConductanceState
                                                       G = G_0 (t_d / t_{d,0})^(-nu)

contract_device_conductance connects the domain to the map through the
electronic conductivity; the other three nodes are one edge from ConductanceState.
"""
from __future__ import annotations

import sympy as sp

from omai.analog_device_metrology.operator.nodes import (
    CONDUCTANCE_DRIFT_EXPONENT,
    CONDUCTANCE_STATE,
    CONDUCTANCE_WINDOW,
    STATE_COEFFICIENT_OF_VARIATION,
)
from omai.electronic_transport.operator.nodes import (
    ELECTRICAL_CONDUCTIVITY_ELECTRONIC,
)
from omai.operator.dimensions import CONDUCTANCE, LENGTH, LENGTH_SQUARED, TIME
from omai.operator.operator import Operator, Parameter

_G_c = sp.Symbol("G_c")                       # ConductanceState
_W_G = sp.Symbol("W_G")                       # ConductanceWindow
_c_G = sp.Symbol("c_G")                       # StateCoefficientOfVariation
_nu_drift = sp.Symbol(r"\nu_{drift}")         # ConductanceDriftExponent
_sigma_el = sp.Symbol(r"\sigma_{el}")         # ElectricalConductivity[electronic]
_A_g = sp.Symbol("A_g")                       # channel cross-section (LENGTH^2)
_L_g = sp.Symbol("L_g")                       # channel length (LENGTH)
_G_0 = sp.Symbol("G_0")                       # conductance at the reference time
_G_min = sp.Symbol("G_min")                   # smallest programmed conductance
_sigma_G = sp.Symbol(r"\sigma_G")             # level standard deviation
_t_d = sp.Symbol("t_d")                       # read time after programming
_t_d0 = sp.Symbol("t_{d,0}")                  # reference time

contract_device_conductance = Operator(
    name="contract_device_conductance",
    inputs=(ELECTRICAL_CONDUCTIVITY_ELECTRONIC,),
    outputs=(CONDUCTANCE_STATE,),
    parameters=(Parameter("A_g", LENGTH_SQUARED), Parameter("L_g", LENGTH)),
    formula=sp.Eq(_G_c, _sigma_el * _A_g / _L_g),
    description=(
        "Channel conductance G = sigma A / L from the electronic conductivity along "
        "the channel, the cross-section A and the length L. Valid for diffusive "
        "transport (L much longer than the carrier mean free path) in an ohmic, "
        "uniform channel with ohmic contacts; short channels approach the "
        "Landauer or contact limit. For a 2D sheet A = t W, where t is the "
        "thickness sigma was normalized by (for a slab calculation, the cell "
        "height, not the layer thickness), so sigma A = sigma_s W with sigma_s "
        "the sheet conductance. A contact-limited (Schottky) device is not "
        "described by this edge."
    ),
)

contract_conductance_window = Operator(
    name="contract_conductance_window",
    inputs=(CONDUCTANCE_STATE,),
    outputs=(CONDUCTANCE_WINDOW,),
    parameters=(Parameter("G_min", CONDUCTANCE),),
    formula=sp.Eq(_W_G, _G_c / _G_min),
    description=(
        "Conductance window W = G_max / G_min: the device's highest conductance "
        "(the input) over its lowest, under one protocol and one set of read "
        "conditions (full SET/RESET switching gives the on/off ratio)."
    ),
)

contract_state_coefficient_of_variation = Operator(
    name="contract_state_coefficient_of_variation",
    inputs=(CONDUCTANCE_STATE,),
    outputs=(STATE_COEFFICIENT_OF_VARIATION,),
    parameters=(Parameter(r"\sigma_G", CONDUCTANCE),),
    formula=sp.Eq(_c_G, _sigma_G / _G_c),
    description=(
        "Coefficient of variation c = sigma_G / mu_G of one programmed level: the "
        "level's standard deviation over its mean (the input)."
    ),
)

apply_conductance_drift = Operator(
    name="apply_conductance_drift",
    inputs=(CONDUCTANCE_DRIFT_EXPONENT,),
    outputs=(CONDUCTANCE_STATE,),
    parameters=(Parameter("G_0", CONDUCTANCE), Parameter("t_d", TIME), Parameter("t_{d,0}", TIME)),
    formula=sp.Eq(_G_c, _G_0 * (_t_d / _t_d0) ** (-_nu_drift)),
    description=(
        "Power-law drift G(t_d) = G_0 (t_d / t_{d,0})^(-nu) of a programmed "
        "conductance from its value G_0 at the reference time t_{d,0}, valid for "
        "t_d >= t_{d,0} > 0 inside the time range where the exponent was fitted "
        "(documented, not enforced). "
        "The symbolic exponent is a special-function skip at the Lean algebra "
        "tier; the dimension is proven."
    ),
)

EDGES: tuple[Operator, ...] = (
    contract_device_conductance,
    contract_conductance_window,
    contract_state_coefficient_of_variation,
    apply_conductance_drift,
)
