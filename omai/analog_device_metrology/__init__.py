"""The analog-device-metrology domain: the conductance family of analog
resistive devices (memristors, memtransistors).

A definitional domain: four quantities (the programmed conductance, the
conductance window, the drift exponent, the per-level spread) and four closed
forms the dimensional gate proves. ConductanceState carries the CONDUCTANCE dimension (the siemens), kept
apart from the per-length electrical conductivity by tag and dimension, and
connects the domain to the map through contract_device_conductance from
ElectricalConductivity[carrier=electronic]. No code representation and no
measured value attach yet.
"""
