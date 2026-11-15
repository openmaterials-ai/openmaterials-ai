"""openmaterials-ai's own evaluator of rrho_ideal_gas_heat_capacity
(omai.molecular.evaluate): the library is the code that ran.

  operator Space               omai function                          unit
  ---------------------------  -------------------------------------  ---------------
  IdealGasMolarHeatCapacityP   omai.molecular.evaluate.cp_table       J/(K mol)

The modes come from another code (xtb, ORCA); the Cp(T) curves come from this
function, so a record credits both.
"""
from __future__ import annotations

from omai.molecular.operator.edges import rrho_ideal_gas_heat_capacity
from omai.molecular.operator.nodes import IDEAL_GAS_MOLAR_HEAT_CAPACITY_P
from omai.representation.adapter import (
    OperatorRepresentationSpec,
    SpaceRepresentationSpec,
)

OMAI_IDEAL_GAS_MOLAR_HEAT_CAPACITY_P = SpaceRepresentationSpec(
    space=IDEAL_GAS_MOLAR_HEAT_CAPACITY_P,
    representation_name="openmaterials-ai",
    observable_units={"cp_mol": "J_per_K_per_mol"},
    code_api={"cp_mol": "omai.molecular.evaluate.cp_table(frequencies_cm, temperatures_K, geometry=..., nu0_cm=50.0)"},
    notes=(
        "rrho_ideal_gas_heat_capacity evaluated per temperature: the quantum "
        "harmonic Cv of each internal mode plus 5R/2 (atom), 7R/2 (linear) "
        "or 4R (nonlinear). The geometry is a condition of every value. Returns the harmonic curve, the qRRHO curve (soft modes "
        "interpolated toward R/2 with the rotor cutoff nu0) and the classical "
        "limit. Imaginary modes are refused."
    ),
)

OMAI_RRHO_IDEAL_GAS_HEAT_CAPACITY = OperatorRepresentationSpec(
    operator=rrho_ideal_gas_heat_capacity,
    representation_name="openmaterials-ai",
    discretization_choices={
        "rotor_cutoff": "nu0 = 50 cm^-1 for the qrrho curve (the xtb default), a keyword of cp_table.",
    },
    notes="Both approximations come from one call: harmonic (the edge's scheme) and qrrho.",
)
