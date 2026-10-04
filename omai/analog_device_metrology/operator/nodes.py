r"""Operator nodes of the analog-device-metrology domain.

The conductance family of analog resistive devices (memristors, memtransistors):
the programmed conductance, the conductance window, the drift exponent and the
per-level spread. The domain
is definitional: it holds the quantities and the closed forms that relate them.
No code representation and no measured value attach yet.

Node ids are unlabeled (plain names): protocol, read bias, gate bias and state
ride in an instance's conditions, not in the node identity.

  Node                         tag                             dimension
  ---------------------------  ------------------------------  -------------
  ConductanceState             conductance_state               CONDUCTANCE
  ConductanceWindow            conductance_window              DIMENSIONLESS
  ConductanceDriftExponent     conductance_drift_exponent      DIMENSIONLESS
  StateCoefficientOfVariation  state_coefficient_of_variation  DIMENSIONLESS
  DotProductError              dot_product_error               DIMENSIONLESS

CONDUCTANCE (the siemens, M^-1 L^-2 T^3 I^2) differs from the per-length
ELECTRICAL_CONDUCTIVITY (S/m) by one length axis, the same conductance versus
conductivity split the map draws for heat (THERMAL_CONDUCTANCE versus
THERMAL_CONDUCTIVITY); tag and dimension both keep them apart. A value is
recorded in a unit whose magnitude survives the six-decimal identity rounding
(a 1 nS conductance in canonical siemens rounds to 0); the unit for such values
is added with the first instance that needs it.
"""
from __future__ import annotations

from omai.operator.dimensions import CONDUCTANCE, DIMENSIONLESS
from omai.operator.space import Field, ObservableSpace, Space

_TIER = "Analog device metrology"

CONDUCTANCE_STATE = ObservableSpace(
    name="ConductanceState",
    fields=(Field("G_c", CONDUCTANCE, indices=()),),
    tier=_TIER,
    description=(
        "Conductance state G = I/V of a two-terminal resistive device or a "
        "memtransistor channel: the analog state a multilevel cell stores. "
        "CONDUCTANCE (the siemens). For a contact-limited device G depends on the "
        "read bias and the gate bias, which ride in instance conditions with the "
        "temperature, the state and, for a drifting state, the time since "
        "programming. NOT the per-length electrical conductivity (S/m)."
    ),
)

CONDUCTANCE_WINDOW = ObservableSpace(
    name="ConductanceWindow",
    fields=(Field("W_G", DIMENSIONLESS, indices=()),),
    tier=_TIER,
    description=(
        "Conductance window W = G_max/G_min of one device: its highest over its "
        "lowest conductance under a stated protocol, both read at the same read "
        "bias, gate bias and temperature. DIMENSIONLESS. Full SET/RESET switching "
        "gives the on/off ratio of a binary switch; incremental programming "
        "(potentiation or depression trains, write-verify) gives the analog "
        "window, so the on/off ratio and the LTP and LTD windows are this node "
        "under three protocols, which ride in instance conditions with the read "
        "conditions. A ratio across gate voltages is transistor modulation, not "
        "this window."
    ),
)

CONDUCTANCE_DRIFT_EXPONENT = ObservableSpace(
    name="ConductanceDriftExponent",
    fields=(Field("nu_drift", DIMENSIONLESS, indices=()),),
    tier=_TIER,
    description=(
        "Drift exponent nu of the power-law relaxation G(t) = G(t0) (t/t0)^(-nu) of a "
        "programmed conductance, fitted for t >= t0 > 0 in the time range where "
        "the relaxation is a power law. DIMENSIONLESS. The state, the read "
        "conditions, the temperature and the fitted time range ride in instance "
        "conditions."
    ),
)

STATE_COEFFICIENT_OF_VARIATION = ObservableSpace(
    name="StateCoefficientOfVariation",
    fields=(Field("c_G", DIMENSIONLESS, indices=()),),
    tier=_TIER,
    description=(
        "Coefficient of variation c = sigma_G/mu_G of a programmed conductance level "
        "across cells (device to device) or across cycles of one cell, which an "
        "instance states in its conditions with the target level and the "
        "programming protocol. DIMENSIONLESS."
    ),
)

DOT_PRODUCT_ERROR = ObservableSpace(
    name="DotProductError",
    fields=(Field("eps_dot", DIMENSIONLESS, indices=()),),
    tier=_TIER,
    description=(
        "Error of an analog dot product computed by an array of programmed "
        "conductances: the root mean square, over the input distribution and over "
        "programmed arrays, of the analog output's error in weight units, divided "
        "by the range of the ideal outputs over the inputs. DIMENSIONLESS. The "
        "architecture (weight-to-conductance mapping, cells per weight, offset "
        "scheme, readout), the kernel, the input distribution, the read and "
        "verify conditions, the time since programming and the error sources "
        "included ride in instance conditions."
    ),
)

NODES: tuple[Space, ...] = (
    CONDUCTANCE_STATE,
    CONDUCTANCE_WINDOW,
    CONDUCTANCE_DRIFT_EXPONENT,
    STATE_COEFFICIENT_OF_VARIATION,
    DOT_PRODUCT_ERROR,
)
