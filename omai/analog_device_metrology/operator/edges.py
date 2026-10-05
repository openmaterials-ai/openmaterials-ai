r"""Operators (edges) of the analog-device-metrology domain.

Eight closed forms the dimensional gate proves and apply_edge runs. Each operand
is a typed input's field symbol, a dimensioned Parameter on the edge or a
universal constant (k_B, q_e). As everywhere on the map, validity statements are
documented, not enforced by apply_edge.

  contract_device_conductance  ElectricalConductivity[carrier=electronic]
                               -> ConductanceState    G = sigma A / L
  contract_conductance_window  ConductanceState -> ConductanceWindow  W = G_c / G_min
  contract_state_coefficient_of_variation
                               ConductanceState -> StateCoefficientOfVariation
                                                       c = sigma_G / G_c
  apply_conductance_drift      ConductanceDriftExponent -> ConductanceState
                                                       G = G_0 (t_d / t_{d,0})^(-nu)
  propagate_programming_error  StateCoefficientOfVariation, ConductanceWindow
                               -> DotProductError     (programming error only)
  emit_thermionic_conductance  SchottkyBarrierHeight[band_carrier=electron], Temperature
                               -> ConductanceState
                               G = P_th T q_e / k_B exp(-Phi_Bn / (k_B T))
  schottky_mott_barrier        WorkFunction, ElectronAffinity
                               -> SchottkyBarrierHeight[band_carrier=electron]
                                                       Phi_Bn = Phi_W - chi
  dissipate_pulse_energy       ConductanceState -> ProgrammingPulseEnergy
                                                       E = V_p^2 G t_p

contract_device_conductance connects the domain to the map through the
electronic conductivity; the other nodes are one or two edges from ConductanceState.
"""
from __future__ import annotations

import sympy as sp

from omai.analog_device_metrology.operator.nodes import (
    CONDUCTANCE_DRIFT_EXPONENT,
    CONDUCTANCE_STATE,
    CONDUCTANCE_WINDOW,
    DOT_PRODUCT_ERROR,
    ELECTRON_AFFINITY,
    PROGRAMMING_PULSE_ENERGY,
    SCHOTTKY_BARRIER_HEIGHT,
    STATE_COEFFICIENT_OF_VARIATION,
    WORK_FUNCTION,
)
from omai.electronic_transport.operator.nodes import (
    ELECTRICAL_CONDUCTIVITY_ELECTRONIC,
)
from omai.operator.dimensions import (
    CONDUCTANCE,
    CURRENT_PER_TEMPERATURE_SQUARED,
    DIMENSIONLESS,
    LENGTH,
    LENGTH_SQUARED,
    TIME,
    VOLTAGE,
)
from omai.operator.operator import Operator, Parameter
from omai.thermal_transport.operator.nodes import TEMPERATURE_STATE

_G_c = sp.Symbol("G_c")                       # ConductanceState
_W_G = sp.Symbol("W_G")                       # ConductanceWindow
_c_G = sp.Symbol("c_G")                       # StateCoefficientOfVariation
_nu_drift = sp.Symbol(r"\nu_{drift}")         # ConductanceDriftExponent
_eps_dot = sp.Symbol(r"\epsilon_{dot}")       # DotProductError
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

# Kernel moments over the nonzero weights: count n_w, largest magnitude w_max,
# S_1 = sum |w_i|, S_2 = sum w_i^2.
_n_w = sp.Symbol("n_w")
_w_max = sp.Symbol("w_max")
_S_1 = sp.Symbol("S_1")
_S_2 = sp.Symbol("S_2")

propagate_programming_error = Operator(
    name="propagate_programming_error",
    inputs=(STATE_COEFFICIENT_OF_VARIATION, CONDUCTANCE_WINDOW),
    outputs=(DOT_PRODUCT_ERROR,),
    parameters=(Parameter("n_w", DIMENSIONLESS), Parameter("w_max", DIMENSIONLESS),
                Parameter("S_1", DIMENSIONLESS), Parameter("S_2", DIMENSIONLESS)),
    formula=sp.Eq(_eps_dot, _c_G * sp.sqrt(
        (_n_w * _w_max**2 / (_W_G - 1)**2 + 2 * _w_max * _S_1 / (_W_G - 1) + _S_2) / 2) / _S_1),
    description=(
        "Dot-product error from programming error alone, for one architecture: "
        "one cell per nonzero weight, positive and negative weights on two "
        "column groups, the affine mapping G_i = G_min + (G_max - G_min) |w_i| / "
        "w_max (the largest |w| at G_max), the nominal G_min subtracted per "
        "active cell (no reference column), binary inputs uniform over patterns "
        "(E[x^2] = 1/2), reads at the verify voltage and temperature, and a "
        "level-independent, unbiased coefficient of variation c of each cell "
        "about its target, independent between cells. W is the window "
        "G_max/G_min of this mapping. Then eps = c sqrt(sum_i (1/r + |w_i|)^2 / "
        "2) / sum |w_i| over the nonzero weights, r = (W - 1) / w_max, written "
        "with the count n_w, the largest weight w_max and the power sums S_1 = "
        "sum |w_i| and S_2 = sum w_i^2 of the kernel (a real kernel has S_1 <= "
        "n_w w_max, S_2 <= w_max S_1 and S_1^2 <= n_w S_2). Read noise, drift, "
        "reads away from the verify voltage, wire IR drop, sneak paths, readout "
        "quantization and offset, "
        "and correlated errors are not included; independent sources add in "
        "quadrature."
    ),
)

_Phi_Bn = sp.Symbol(r"\Phi_{Bn}")            # SchottkyBarrierHeight[band_carrier=electron]
_Phi_W = sp.Symbol(r"\Phi_{W}")              # WorkFunction
_chi_s = sp.Symbol(r"\chi_{s}")              # ElectronAffinity
_E_pulse = sp.Symbol("E_{pulse}")            # ProgrammingPulseEnergy
_kB = sp.Symbol("k_B")
_T = sp.Symbol("T")                           # Temperature
_q_e = sp.Symbol("q_e")                       # elementary charge
_P_th = sp.Symbol("P_th")                     # thermionic prefactor A_c A*
_V_p = sp.Symbol("V_p")                       # pulse amplitude
_t_p = sp.Symbol("t_p")                       # pulse width

emit_thermionic_conductance = Operator(
    name="emit_thermionic_conductance",
    inputs=(SCHOTTKY_BARRIER_HEIGHT, TEMPERATURE_STATE),
    outputs=(CONDUCTANCE_STATE,),
    parameters=(Parameter("P_th", CURRENT_PER_TEMPERATURE_SQUARED),),
    formula=sp.Eq(_G_c, _P_th * _T * _q_e / _kB * sp.exp(-_Phi_Bn / (_kB * _T))),
    description=(
        "Zero-bias conductance of one Schottky contact by thermionic emission of "
        "electrons, G = P_th T^2 (q_e / k_B T) exp(-Phi_Bn / k_B T), the V -> 0 "
        "slope of I = P_th T^2 exp(-Phi_Bn / k_B T) (exp(q_e V / k_B T) - 1). "
        "Units: Phi_Bn in joules (the map's energy unit; an eV number read as "
        "joules gives G = 0), T in kelvin, P_th = A_c A* (contact area times "
        "effective Richardson constant) in A K^-2, G in siemens. Valid for "
        "emission over the barrier without field or thermionic-field tunnelling, "
        "ideality factor 1 (I = I_s (exp(q_e V / n k_B T) - 1) gives G / n; in "
        "the form I_s exp(q_e V / n k_B T) (1 - exp(-q_e V / k_B T)) n drops out "
        "and G holds), "
        "Phi_Bn much larger than k_B T, and a device this contact limits; two "
        "identical back-to-back contacts in series give G / 2. Phi_Bn is the "
        "effective barrier at zero applied bias: the built-in field lowers it by "
        "the image force even then, and a low-bias Arrhenius fit returns this "
        "value, not the flat-band barrier. The T^2 prefactor is the "
        "three-dimensional Richardson law; injection into a 2D channel follows a "
        "T^{3/2} law with a per-width prefactor P_th cannot express, and fitting "
        "one law to data from the other shifts the barrier by about k_B T / 2. G "
        "is a small-signal conductance for |V| much smaller than k_B T / q_e, not "
        "the chord conductance at a programming pulse, so it does not feed "
        "dissipate_pulse_energy."
    ),
)

schottky_mott_barrier = Operator(
    name="schottky_mott_barrier",
    inputs=(WORK_FUNCTION, ELECTRON_AFFINITY),
    outputs=(SCHOTTKY_BARRIER_HEIGHT,),
    formula=sp.Eq(_Phi_Bn, _Phi_W - _chi_s),
    description=(
        "Schottky-Mott limit of the electron barrier, Phi_Bn = Phi_W - chi: the "
        "contact metal's work function minus the semiconductor's electron "
        "affinity, all in joules. The work function must be the metal's: a "
        "semiconductor's own work function minus its affinity is E_C - E_F, not a "
        "barrier. Valid for an ideal interface without Fermi-level pinning, "
        "interface dipoles or interface states; metals deposited on 2D "
        "semiconductors usually pin, so measured barriers depart from it, while "
        "transferred van der Waals contacts approach it. The hole barrier is the "
        "quasiparticle gap minus this value."
    ),
)

dissipate_pulse_energy = Operator(
    name="dissipate_pulse_energy",
    inputs=(CONDUCTANCE_STATE,),
    outputs=(PROGRAMMING_PULSE_ENERGY,),
    parameters=(Parameter("V_p", VOLTAGE), Parameter("t_p", TIME)),
    formula=sp.Eq(_E_pulse, _V_p**2 * _G_c * _t_p),
    description=(
        "Energy dissipated by a rectangular programming pulse of amplitude V_p "
        "(volts) and width t_p, E = V_p^2 G t_p in joules, with t_p in the map's "
        "canonical time unit, 1 ps (1 ms is 1e9; a width in seconds gives an "
        "energy 1e12 too small). G is the chord conductance I(V_p) / V_p at the "
        "pulse amplitude: a low-bias read conductance or the zero-bias thermionic "
        "conductance of a Schottky device differs from it by orders of magnitude. "
        "Valid when G changes little during the pulse (Delta G / G much smaller "
        "than 1). For a switching pulse E lies between V_p^2 G_before t_p and "
        "V_p^2 G_after t_p; their mean holds only for G linear in time. The "
        "energy dissipated charging and discharging "
        "the device and wiring capacitance (C V_p^2 per pulse) and the energy of "
        "the drive electronics are not included."
    ),
)

EDGES: tuple[Operator, ...] = (
    contract_device_conductance,
    contract_conductance_window,
    contract_state_coefficient_of_variation,
    apply_conductance_drift,
    propagate_programming_error,
    emit_thermionic_conductance,
    schottky_mott_barrier,
    dissipate_pulse_energy,
)
