"""Dimensions of the analog-device-metrology field symbols, registered with the
dimensional gate when the operator package is imported. Edge Parameters carry
their own dimensions."""
from __future__ import annotations

from omai.operator.dimcheck import register_symbol_dimensions
from omai.operator.dimensions import CONDUCTANCE, DIMENSIONLESS

register_symbol_dimensions({
    "G_c": CONDUCTANCE,
    "W_G": DIMENSIONLESS,
    "c_G": DIMENSIONLESS,
    r"\nu_{drift}": DIMENSIONLESS,
    r"\epsilon_{dot}": DIMENSIONLESS,
})
