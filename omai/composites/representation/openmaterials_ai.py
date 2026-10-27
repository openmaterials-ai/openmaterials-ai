"""openmaterials-ai's own evaluators of the Nan effective-medium edges
(omai.composites.evaluate): the library is the code that ran.

  operator Space                                                 omai function
  -------------------------------------------------------------  ----------------------------------------
  ThermalConductivity[effective_medium=nan,orientation=random]   omai.composites.evaluate.nan_kappa_random
  ThermalConductivity[effective_medium=nan,orientation=aligned]  ...evaluate.nan_kappa_aligned (al33)

A reference implementation of the map's own closed forms, so a value it
produces checks the edge's arithmetic, not agreement between independent codes.
"""
from __future__ import annotations

from omai.composites.operator.nodes import (
    EFFECTIVE_CONDUCTIVITY_ALIGNED,
    EFFECTIVE_CONDUCTIVITY_RANDOM,
)
from omai.representation.adapter import SpaceRepresentationSpec

OMAI_NAN_RANDOM = SpaceRepresentationSpec(
    space=EFFECTIVE_CONDUCTIVITY_RANDOM,
    representation_name="openmaterials-ai",
    observable_units={"kappa_c": "W_per_m_per_K"},
    code_api={"kappa_c": "omai.composites.evaluate.nan_kappa_random"},
    notes=(
        "nan_effective_kappa in closed form, the interface a per-direction "
        "series film across each full inclusion dimension (the 2004 form); "
        "inputs are the record conditions, the Kapitza radius km / G derived."
    ),
)

OMAI_NAN_ALIGNED = SpaceRepresentationSpec(
    space=EFFECTIVE_CONDUCTIVITY_ALIGNED,
    representation_name="openmaterials-ai",
    observable_units={"kappa_c": "W_per_m_per_K"},
    code_api={"kappa_c": "omai.composites.evaluate.nan_kappa_aligned"},
    notes=(
        "nan_effective_kappa_aligned's declared value al33, along the "
        "spheroid's polar axis 3 (the fiber axis, the platelet normal); al11, "
        "perpendicular to it (the platelet plane), is the edge's auxiliary "
        "formula (aligned_tensor_components), not this node's value."
    ),
)
