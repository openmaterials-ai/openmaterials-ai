"""GPUMD adapter spec for the composites domain.

One row: InterfaceConductance[transport_model=nemd] from direct two-reservoir
NEMD across one interface. The representation's other rows are in
omai.thermal_transport.representation.gpumd.
"""
from __future__ import annotations

from omai.composites.operator.nodes import INTERFACE_CONDUCTANCE_NEMD
from omai.representation.adapter import SpaceRepresentationSpec

GPUMD_INTERFACE_CONDUCTANCE_NEMD = SpaceRepresentationSpec(
    space=INTERFACE_CONDUCTANCE_NEMD,
    representation_name="gpumd",
    code_api={
        "G_int": "run.in: ensemble heat_lan <T> <T_coup> <delta_T> <label_source> <label_sink> "
                 "+ compute 0 <sample_interval> <output_interval> temperature  →  compute.out"
    },
    notes=(
        "G = q_int / Delta_T_int. q_int is the mean of |dE_source/dt| and "
        "|dE_sink/dt| over the steady-state window divided by the cross-section "
        "A (2A when a periodic cell carries the heat both ways); E_source and "
        "E_sink are the last two compute.out columns, the energies (eV) the "
        "source and sink thermostats have exchanged, accumulated with opposite "
        "signs. Delta_T_int is the jump at the interface plane of the per-group "
        "temperature profile (the compute.out group columns, K), from linear "
        "fits on each side. This is not GPUMD's documented whole-system NEMD "
        "conductance G = (Q/S)/Delta_T between the two thermostats. The source "
        "runs at T + delta_T and the sink at T - delta_T, so the applied "
        "difference is 2 delta_T. heat_nhc and heat_bdp are the same mechanism "
        "with Nose-Hoover chain and Bussi-Donadio-Parrinello thermostats."
    ),
)
