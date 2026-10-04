"""Formula symbols of the analog-device-metrology nodes, registered with the
core vocabulary when the operator package is imported. Edge helper operands are
dimensioned Parameters, not registered here."""
from __future__ import annotations

from omai.operator.vocabulary import register_space_symbols

register_space_symbols({
    "ConductanceState": {"G_c"},
    "ConductanceWindow": {"W_G"},
    "ConductanceDriftExponent": {r"\nu_{drift}"},
    "StateCoefficientOfVariation": {"c_G"},
    "DotProductError": {r"\epsilon_{dot}"},
})
