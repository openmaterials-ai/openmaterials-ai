"""Formula symbols of the cure-kinetics nodes (T, N_A, k_B are generic constants)."""
from __future__ import annotations

from omai.operator.vocabulary import register_space_symbols

register_space_symbols({
    "CureConversion": {
        r"\alpha_{cure}", r"\alpha_{0,cure}", "t_{cure}", "A_{1,cure}", "A_{2,cure}",
        "E_{1,cure}", "E_{2,cure}", "m_{cure}", "n_{cure}"},
    "GlassTransitionTemperature": {"T_g", "T_{g0}", r"T_{g\infty}", r"\lambda_{DiB}"},
})
