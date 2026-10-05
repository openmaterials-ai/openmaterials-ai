r"""Operator nodes of the analog-device-metrology domain.

The conductance family of analog resistive devices (memristors, memtransistors):
the programmed conductance, the conductance window, the drift exponent, the
per-level spread and the error of an analog dot product; the contact barrier
that sets a Schottky device's conductance with the work function and electron
affinity that set the barrier; the energy of a programming pulse; and the set
voltage and retention time of a device switched by vacancy hops. The domain
is definitional: it holds the quantities and the closed forms that relate them.
No code representation attaches yet; two measured work functions do.

Node ids are plain names, except where a label changes the quantity: the
electron Schottky barrier is SchottkyBarrierHeight[band_carrier=electron] (the hole
barrier differs; the two sum to the gap). Protocol, read bias, gate bias and
state ride in an instance's conditions, not in the node identity.

  Node                         tag                             dimension
  ---------------------------  ------------------------------  -------------
  ConductanceState             conductance_state               CONDUCTANCE
  ConductanceWindow            conductance_window              DIMENSIONLESS
  ConductanceDriftExponent     conductance_drift_exponent      DIMENSIONLESS
  StateCoefficientOfVariation  state_coefficient_of_variation  DIMENSIONLESS
  DotProductError              dot_product_error               DIMENSIONLESS
  SchottkyBarrierHeight[band_carrier=electron]
                               schottky_barrier_height         ENERGY
  WorkFunction                 work_function                   ENERGY
  ElectronAffinity             electron_affinity               ENERGY
  ProgrammingPulseEnergy       programming_pulse_energy        ENERGY
  SetVoltage                   set_voltage                     VOLTAGE
  RetentionTime                retention_time                  TIME

CONDUCTANCE (the siemens, M^-1 L^-2 T^3 I^2) differs from the per-length
ELECTRICAL_CONDUCTIVITY (S/m) by one length axis, the same conductance versus
conductivity split the map draws for heat (THERMAL_CONDUCTANCE versus
THERMAL_CONDUCTIVITY); tag and dimension both keep them apart. A value is
recorded in a unit whose magnitude survives the six-decimal identity rounding
(a 1 nS conductance in canonical siemens rounds to 0); the unit for such values
is added with the first instance that needs it.
"""
from __future__ import annotations

from omai.operator.dimensions import CONDUCTANCE, DIMENSIONLESS, ENERGY, TIME, VOLTAGE
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

SCHOTTKY_BARRIER_HEIGHT = ObservableSpace(
    name="SchottkyBarrierHeight[band_carrier=electron]",
    fields=(Field("Phi_Bn", ENERGY, indices=()),),
    labels={"band_carrier": "electron"},
    tier=_TIER,
    description=(
        "Electron Schottky barrier height Phi_Bn: the barrier for electron "
        "injection from a metal contact into a semiconductor, from the metal "
        "Fermi level to the conduction-band edge at the interface. ENERGY. The "
        "hole barrier is another quantity (the two sum to the quasiparticle "
        "gap). The contact metal and semiconductor, the device state and gate "
        "voltage, whether the value is the flat-band barrier or the effective "
        "barrier at zero applied bias, and the extraction (thermionic Arrhenius "
        "fit with its bias, temperature range, Richardson exponent and A*; C-V; "
        "internal photoemission or band alignment) ride in instance conditions."
    ),
)

WORK_FUNCTION = ObservableSpace(
    name="WorkFunction",
    fields=(Field("Phi_W", ENERGY, indices=()),),
    tier=_TIER,
    description=(
        "Work function Phi_W of a surface: the minimum energy to move an electron "
        "from the Fermi level to the vacuum level just outside the surface. ENERGY. "
        "The surface (a contact metal, or a semiconductor with its doping, "
        "thickness and treatment), its termination and the method (photoemission "
        "secondary-electron cutoff, Kelvin probe) ride in instance conditions. A "
        "Schottky-Mott barrier needs the contact metal's value."
    ),
)

ELECTRON_AFFINITY = ObservableSpace(
    name="ElectronAffinity",
    fields=(Field("chi_s", ENERGY, indices=()),),
    tier=_TIER,
    description=(
        "Electron affinity chi: the energy released when an electron moves from "
        "the vacuum level into the lowest unoccupied state. For a semiconductor "
        "or insulator surface chi = E_vac - E_CBM, which depends on the surface; "
        "for a molecule E(N) - E(N+1), vertical or adiabatic. ENERGY. The "
        "system, its surface or termination, thickness or layer count, and the "
        "method ride in instance conditions. Relations through a gap need the "
        "quasiparticle gap, not the optical gap."
    ),
)

PROGRAMMING_PULSE_ENERGY = ObservableSpace(
    name="ProgrammingPulseEnergy",
    fields=(Field("E_pulse", ENERGY, indices=()),),
    tier=_TIER,
    description=(
        "Electrical energy dissipated in a device by one programming voltage "
        "pulse (not an optical pulse energy). ENERGY. The terminal pulsed (drain "
        "or gate), the pulse amplitude, width and shape, the device state before "
        "and after the pulse and whether capacitive charging is included ride in "
        "instance conditions."
    ),
)

SET_VOLTAGE = ObservableSpace(
    name="SetVoltage",
    fields=(Field("V_set", VOLTAGE, indices=()),),
    tier=_TIER,
    description=(
        "Set voltage of a resistive device: the applied voltage at which a "
        "monotonically increasing drive first switches it to the "
        "low-resistance state, as the mean over devices or over cycles of one "
        "device. VOLTAGE. The drive (a linear ramp with its rate, or a pulse "
        "staircase with its pulse width, step and rest), the driven terminal "
        "and the other terminals' biases, the switching criterion, the "
        "temperature and the number of devices or cycles ride in instance "
        "conditions; the spread rides in the uncertainty."
    ),
)

RETENTION_TIME = ObservableSpace(
    name="RetentionTime",
    fields=(Field("tau_ret", TIME, indices=()),),
    tier=_TIER,
    description=(
        "Retention time of a programmed state: the 1/e lifetime of its "
        "conductance change at zero bias, so an exponential decay loses a "
        "fraction f in -tau ln(1 - f). TIME. The state, the storage bias and "
        "temperature and the decay law fitted ride in instance conditions; a "
        "power-law relaxation belongs on ConductanceDriftExponent."
    ),
)

NODES: tuple[Space, ...] = (
    CONDUCTANCE_STATE,
    CONDUCTANCE_WINDOW,
    CONDUCTANCE_DRIFT_EXPONENT,
    STATE_COEFFICIENT_OF_VARIATION,
    DOT_PRODUCT_ERROR,
    SCHOTTKY_BARRIER_HEIGHT,
    WORK_FUNCTION,
    ELECTRON_AFFINITY,
    PROGRAMMING_PULSE_ENERGY,
    SET_VOLTAGE,
    RETENTION_TIME,
)
