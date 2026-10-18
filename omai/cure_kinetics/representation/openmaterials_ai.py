"""openmaterials-ai's own evaluators of the cure-kinetics edges
(omai.cure_kinetics.evaluate): the library is the code that ran.

  operator Space               omai function                                     unit
  ---------------------------  ------------------------------------------------  -------------
  CureConversion               omai.cure_kinetics.evaluate.cure_conversion       dimensionless
  GlassTransitionTemperature   ...evaluate.glass_transition_temperature          kelvin

A reference implementation of the map's own edges, so a value it produces
checks the edge's arithmetic, not agreement between independent codes.
"""
from __future__ import annotations

from omai.cure_kinetics.operator.nodes import (
    CURE_CONVERSION,
    GLASS_TRANSITION_TEMPERATURE,
)
from omai.representation.adapter import SpaceRepresentationSpec

OMAI_CURE_CONVERSION = SpaceRepresentationSpec(
    space=CURE_CONVERSION,
    representation_name="openmaterials-ai",
    observable_units={"alpha": "dimensionless"},
    code_api={"alpha": "omai.cure_kinetics.evaluate.cure_conversion"},
    notes=(
        "kamal_cure_conversion evaluated as its own integral, t = integral of "
        "d alpha / rate from alpha_0, solved for alpha: Gauss-Legendre "
        "quadrature in s = ln(alpha / (1 - alpha)) and a safeguarded Newton "
        "root, so no time step enters the value. The single (1 - alpha)^n "
        "Kamal-Sourour form only; other rate laws are refused."
    ),
)

OMAI_GLASS_TRANSITION_TEMPERATURE = SpaceRepresentationSpec(
    space=GLASS_TRANSITION_TEMPERATURE,
    representation_name="openmaterials-ai",
    observable_units={"T_g": "kelvin"},
    code_api={"T_g": "omai.cure_kinetics.evaluate.glass_transition_temperature"},
    notes="dibenedetto_glass_transition evaluated in closed form.",
)
