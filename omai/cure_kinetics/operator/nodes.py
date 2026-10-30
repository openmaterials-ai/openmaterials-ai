"""Nodes of the cure-kinetics domain: cure of a thermosetting resin.

Method-neutral: a measured conversion or T_g is evidence of these nodes; the
producing edges carry their method as a scheme.
"""
from __future__ import annotations

from omai.operator.dimensions import DIMENSIONLESS, TEMPERATURE
from omai.operator.space import Field, ObservableSpace, Space

CURE_CONVERSION = ObservableSpace(
    name="CureConversion",
    fields=(Field("alpha", DIMENSIONLESS),),
    tier="Cure kinetics",
    description=(
        "Degree of cure alpha of a thermosetting resin, the reacted fraction of "
        "its reactive groups (in DSC practice, the released fraction of the "
        "total reaction heat); dimensionless, 0 (uncured) to 1 (fully cured). "
        "Method-neutral: a measured conversion is evidence of this node. The "
        "kamal_cure_conversion edge is the single-(1 - alpha)^n Kamal-Sourour "
        "form only; with no diffusion control and constants fit to data before "
        "vitrification, it overestimates the rate once diffusion control sets in "
        "near and past vitrification; no bound on the conversion is proved."
    ),
)

GLASS_TRANSITION_TEMPERATURE = ObservableSpace(
    name="GlassTransitionTemperature",
    fields=(Field("T_g", TEMPERATURE),),
    tier="Cure kinetics",
    description=(
        "Glass transition temperature T_g; Kelvin. Method-neutral: a measured "
        "T_g of any glass-forming material is evidence of this node. In a "
        "thermosetting network it rises with the degree of cure; the DiBenedetto "
        "edge maps a measured or computed degree of cure onto it."
    ),
)

NODES: tuple[Space, ...] = (CURE_CONVERSION, GLASS_TRANSITION_TEMPERATURE)
