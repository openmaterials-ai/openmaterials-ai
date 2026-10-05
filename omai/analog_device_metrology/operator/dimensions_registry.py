"""Dimensions of the analog-device-metrology field symbols, registered with the
dimensional gate when the operator package is imported. Edge Parameters carry
their own dimensions."""
from __future__ import annotations

from omai.operator.dimcheck import register_symbol_dimensions
from omai.operator.dimensions import (
    CONDUCTANCE,
    DIMENSIONLESS,
    ELECTRIC_CHARGE,
    ENERGY,
    TIME,
    VOLTAGE,
)

register_symbol_dimensions({
    "G_c": CONDUCTANCE,
    "W_G": DIMENSIONLESS,
    "c_G": DIMENSIONLESS,
    r"\nu_{drift}": DIMENSIONLESS,
    r"\epsilon_{dot}": DIMENSIONLESS,
    r"\Phi_{Bn}": ENERGY,
    r"\Phi_{W}": ENERGY,
    r"\chi_{s}": ENERGY,
    "E_{pulse}": ENERGY,
    "V_{set}": VOLTAGE,
    r"\tau_{ret}": TIME,
    "q_e": ELECTRIC_CHARGE,
})
