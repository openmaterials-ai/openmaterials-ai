"""The cure-kinetics Domain descriptor."""
from __future__ import annotations

from omai.cure_kinetics import representation as ck_rep
from omai.cure_kinetics.operator import EDGES, NODES
from omai.map_data import Domain

SYMBOLS: dict[str, str] = {
    "CureConversion": r"\alpha",
    "GlassTransitionTemperature": r"T_g",
}

CURE_KINETICS = Domain(
    name="cure_kinetics",
    nodes=NODES,
    edges=EDGES,
    symbols=SYMBOLS,
    param_promotions=(),
    tiers=(
        (
            "Cure kinetics",
            "Cure of a thermosetting resin: the degree of cure (measured, or "
            "Kamal-Sourour kinetics over an isothermal hold) and the glass "
            "transition temperature it sets (DiBenedetto relation).",
        ),
    ),
    representation_package=ck_rep,
)
