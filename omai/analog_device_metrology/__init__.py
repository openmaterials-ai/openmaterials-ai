"""The analog-device-metrology domain: the conductance family of analog
resistive devices (memristors, memtransistors).

A definitional domain: fourteen quantities (the programmed conductance, the
conductance window, the drift exponent, the per-level spread, the error of an
analog dot product on a crossbar of such cells, the Schottky barrier height, the
work function, the electron affinity, the energy of a programming pulse, the set
voltage, retention time, conductance and interface-trap relaxation times, and
benchmark-qualified classification accuracy), eleven closed forms the dimensional
gate proves, and one external classification operator whose dimensions are not
proved by the gate. ConductanceState carries the
CONDUCTANCE dimension (the siemens), kept apart from the per-length electrical
conductivity by tag and dimension, and connects the domain to the map through
contract_device_conductance from ElectricalConductivity[carrier=electronic]. One
code representation attaches, ngspice on ConductanceState and DotProductError;
two measured values do, the work functions of pristine and oxygen-plasma-treated
MoS2 (Hou et al. 2025).
"""
