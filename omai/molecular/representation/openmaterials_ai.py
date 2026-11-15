"""openmaterials-ai's own evaluator of rrho_ideal_gas_heat_capacity
(omai.molecular.evaluate): the library is the code that ran.

  operator Space                                   omai function                     unit
  -----------------------------------------------  --------------------------------  ---------
  IdealGasMolarHeatCapacityP                       omai.molecular.evaluate.cp_table  J/(K mol)
  IdealGasMolarHeatCapacityP[approximation=qrrho]  omai.molecular.evaluate.cp_table  J/(K mol)

The modes come from another code (xtb, ORCA); the Cp(T) curves come from this
function, so a record credits both.
"""
from __future__ import annotations

from omai.molecular.operator.edges import (
    rrho_ideal_gas_heat_capacity,
    rrho_ideal_gas_heat_capacity_qrrho,
)
from omai.molecular.operator.nodes import (
    IDEAL_GAS_MOLAR_HEAT_CAPACITY_P,
    IDEAL_GAS_MOLAR_HEAT_CAPACITY_P_QRRHO,
)
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
        "or 4R (nonlinear). The geometry is a condition of every value. The key "
        "harmonic_J_per_molK of cp_table. Imaginary modes are refused."
    ),
)

OMAI_IDEAL_GAS_MOLAR_HEAT_CAPACITY_P_QRRHO = SpaceRepresentationSpec(
    space=IDEAL_GAS_MOLAR_HEAT_CAPACITY_P_QRRHO,
    representation_name="openmaterials-ai",
    observable_units={"cp_mol": "J_per_K_per_mol"},
    code_api={"cp_mol": "omai.molecular.evaluate.cp_table(frequencies_cm, temperatures_K, geometry=..., nu0_cm=50.0)"},
    notes=(
        "rrho_ideal_gas_heat_capacity[approximation=qrrho] evaluated per "
        "temperature, the key qrrho_J_per_molK of cp_table. The rotor cutoff "
        "nu0_cm and the geometry are conditions of every value. Imaginary "
        "modes are refused."
    ),
)

OMAI_RRHO_IDEAL_GAS_HEAT_CAPACITY = OperatorRepresentationSpec(
    operator=rrho_ideal_gas_heat_capacity,
    representation_name="openmaterials-ai",
    notes="The harmonic curve of cp_table, which returns both approximations in one call.",
)

OMAI_RRHO_IDEAL_GAS_HEAT_CAPACITY_QRRHO = OperatorRepresentationSpec(
    operator=rrho_ideal_gas_heat_capacity_qrrho,
    representation_name="openmaterials-ai",
    discretization_choices={
        "rotor_cutoff": "nu0_cm = 50 cm^-1 by default (the xtb default), a keyword of cp_table and a condition of the value.",
    },
    notes="The qrrho curve of cp_table, which returns both approximations in one call.",
)
