"""The analog-device-metrology Domain descriptor."""
from __future__ import annotations

from omai.analog_device_metrology import representation as adm_rep
from omai.analog_device_metrology.operator import EDGES, NODES
from omai.map_data import Domain

SYMBOLS: dict[str, str] = {
    "ConductanceState": r"G_c",
    "ConductanceWindow": r"W_G",
    "ConductanceDriftExponent": r"\nu_{drift}",
    "StateCoefficientOfVariation": r"c_G",
}

ANALOG_DEVICE_METROLOGY = Domain(
    name="analog_device_metrology",
    nodes=NODES,
    edges=EDGES,
    symbols=SYMBOLS,
    param_promotions=(),
    tiers=(
        (
            "Analog device metrology",
            "The conductance family of analog resistive devices (memristors, "
            "memtransistors): the programmed conductance, the conductance window "
            "(on/off ratio and LTP/LTD windows under their protocols), the drift "
            "exponent and the per-level spread."
        ),
    ),
    representation_package=adm_rep,
)
