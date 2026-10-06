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
    "DotProductError": r"\epsilon_{dot}",
    "SchottkyBarrierHeight[band_carrier=electron]": r"\Phi_{Bn}",
    "WorkFunction": r"\Phi_{W}",
    "ElectronAffinity": r"\chi_{s}",
    "ProgrammingPulseEnergy": r"E_{pulse}",
    "SetVoltage": r"V_{set}",
    "RetentionTime": r"\tau_{ret}",
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
            "exponent, the per-level spread, the error of an analog dot product on "
            "a crossbar of such cells, the Schottky barrier with the work function "
            "and electron affinity that set it, the energy of a programming "
            "pulse, and the set voltage and retention time of a device switched "
            "by a defect hop."
        ),
    ),
    representation_package=adm_rep,
)
