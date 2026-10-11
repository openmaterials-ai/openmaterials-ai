r"""Symbol dimensions of the cure-kinetics formulas, so the gate proves both edges.

The registry is global, so the domain claims no generic names: the conversion,
time, fitted constants, and reaction orders carry a cure subscript, the
DiBenedetto parameter a DiB one, the integration dummy is \alpha', and the gas
constant is written N_A k_B (both registered by thermal transport).
"""
from __future__ import annotations

from omai.operator.dimcheck import register_symbol_dimensions
from omai.operator.dimensions import (
    DIMENSIONLESS,
    ENERGY_PER_MOLE,
    FREQUENCY,
    TEMPERATURE,
    TIME,
)

register_symbol_dimensions({
    r"\alpha_{cure}": DIMENSIONLESS,
    r"\alpha_{0,cure}": DIMENSIONLESS,
    r"\alpha'": DIMENSIONLESS,
    "t_{cure}": TIME,
    "A_{1,cure}": FREQUENCY,
    "A_{2,cure}": FREQUENCY,
    "E_{1,cure}": ENERGY_PER_MOLE,
    "E_{2,cure}": ENERGY_PER_MOLE,
    "m_{cure}": DIMENSIONLESS,
    "n_{cure}": DIMENSIONLESS,
    "T_g": TEMPERATURE,
    "T_{g0}": TEMPERATURE,
    r"T_{g\infty}": TEMPERATURE,
    r"\lambda_{DiB}": DIMENSIONLESS,
})
