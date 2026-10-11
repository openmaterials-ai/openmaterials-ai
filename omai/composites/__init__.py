"""The composites (effective-medium) domain: composite effective thermal conductivity.

Domain eleven: the effective thermal conductivity of a two-phase composite (a
dispersed filler in a continuous matrix) with interfacial (Kapitza) resistance,
via Nan-type effective-medium theory (Nan et al., J. Appl. Phys. 81, 6692 (1997)),
cross-checked in the spherical limit against Hasselman-Johnson (J. Compos. Mater.
21, 508 (1987)). Eight nodes (the matrix and filler conductivities as role-labeled
inputs, the new InterfaceConductance physics and its NEMD sibling
InterfaceConductance[transport_model=nemd], the filler volume fraction, the
depolarization factors, and the random / aligned effective conductivities) and
six edges (the depolarization closed form, the Nan random and aligned mixing
formulas, the Hasselman-Johnson second producer, the resolve onto the neutral
ThermalConductivity observable, and the NEMD interface-conductance producer).
One new dimension INTERFACE_CONDUCTANCE (W/(m^2 K)) falls out of the interface
conductance.
"""
