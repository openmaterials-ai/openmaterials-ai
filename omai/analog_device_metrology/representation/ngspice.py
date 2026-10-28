"""ngspice adapter specs for the analog-device-metrology domain (representation ngspice).

ngspice (https://ngspice.sourceforge.io, release ngspice-47) is the open
source SPICE circuit simulator: Berkeley SPICE3f5 with XSPICE code models,
the KLU sparse solver and OSDI for compiled Verilog-A device models. It solves
the network a netlist describes (the operating point, DC sweeps, transients,
small-signal AC and noise) for whatever device models the netlist carries.
The facts below are read from the ngspice-47 user's manual and sources.

  operator Space    ngspice output                                     unit
  ----------------  -------------------------------------------------  -------------
  ConductanceState  .op: branch current of the read source over V_read  siemens
  DotProductError   .op per input pattern: the readout node voltages,   dimensionless
                    reduced against the ideal products

Conventions this module pins down:

  * The device physics is the netlist's, not ngspice's: a compact model as a
    .subckt, a behavioural B source, an XSPICE code model or an OSDI library
    compiled from Verilog-A. A value on either node is the value of that model
    in that circuit, and the model's identity rides in instance conditions.
  * ngspice reports the current of a voltage source as positive when it flows
    into the source's positive terminal, so a source driving a load reads a
    negative current: the device current is -i(vread).
  * Output precision: print and wrdata write numdgt digits after the decimal
    point (defaults 6 and 8). A reduction that subtracts nearly equal outputs
    sets numdgt=15.
  * The default matrix solver is Sparse 1.3; option klu selects KLU, which
    does not support small-signal noise analysis.

Not mapped: ConductanceWindow, StateCoefficientOfVariation and
ConductanceDriftExponent are ratios or fits over several programmed states
or reads, which the caller forms from ConductanceState values; ngspice has no
programming dynamics of its own beyond what the device model integrates.
"""

from __future__ import annotations

from omai.analog_device_metrology.operator.nodes import CONDUCTANCE_STATE, DOT_PRODUCT_ERROR
from omai.representation.adapter import SpaceRepresentationSpec

NGSPICE_CONDUCTANCE_STATE = SpaceRepresentationSpec(
    space=CONDUCTANCE_STATE,
    representation_name="ngspice",
    observable_units={"G_c": "siemens"},
    code_api={"G_c": ".op with a DC source vread at the read bias across the device; "
                     "G = -i(vread) / V_read (wrdata, or let g = -i(vread) / V_read before print: "
                     "print drops one digit of a negative number)"},
    notes=(
        "The chord conductance I/V of one device at its operating point: an "
        "operating-point analysis (.op) with a DC voltage source at the read "
        "bias across the two terminals, or across drain and source with the gate "
        "biased, and the device current read from the source branch, -i(vread) "
        "in ngspice's sign convention, divided by V_read. -i(vread) is the device "
        "current when vread's + node is on the device side and its branch "
        "carries only the device; for a memtransistor vread sits on the drain, "
        "so gate leakage stays out of the drain current. Not the small-signal "
        "dI/dV, which a central difference of two .op runs or the device's own "
        "operating-point parameters give. Read bias, gate bias, temperature "
        "(.temp or option temp) and the device state (a model parameter or an "
        "internal state node of the model) ride in instance conditions with the "
        "model's identity. The value is the device model's prediction; ngspice "
        "only solves the circuit around it."
    ),
)

NGSPICE_DOT_PRODUCT_ERROR = SpaceRepresentationSpec(
    space=DOT_PRODUCT_ERROR,
    representation_name="ngspice",
    observable_units={"eps_dot": "dimensionless"},
    code_api={"eps_dot": ".op of the array netlist per input pattern (alter or a .control "
                         "loop), wrdata of the readout node voltages at numdgt=15"},
    notes=(
        "The array read solved as a circuit: a netlist of the programmed cells, "
        "the row and column wire resistances, the input drivers and the column "
        "readout (a transimpedance amplifier per column, its op-amp as a "
        "macromodel with finite gain, offset and bias current where the netlist "
        "states them). One .op per input pattern, the pattern applied by alter "
        "or a .control loop in one session, gives each column's output voltage; "
        "a transient gives the settling. The default solver is Sparse 1.3; option "
        "klu selects KLU, under which noise analysis is not available. The output in weight units, through "
        "the caller's weight-to-conductance mapping and the readout gain, minus "
        "the ideal product W x, is the per-pattern error; its root mean square "
        "over patterns (and over programmed arrays when the netlist samples the "
        "programming error, for example with agauss parameters and one run per "
        "array), divided by the range of the ideal outputs over the inputs, is "
        "the node's value. ngspice resolves what the circuit contains: wire IR "
        "drop, sneak currents through unselected cells, the nonlinear I-V of the "
        "device model, readout gain error and offset. The mapping, the input "
        "distribution and the ideal products are the caller's and ride in "
        "instance conditions with the error sources the netlist includes. For "
        "the architecture propagate_programming_error states, with linear cells, "
        "ideal wires and readout and programming error as the only source, the "
        "sampled value converges to that edge's closed form when that error is "
        "relative, level-independent and independent per cell, as agauss(G_i, "
        "c*G_i, 1) draws it; for large c a Gaussian draw can go negative."
    ),
)
