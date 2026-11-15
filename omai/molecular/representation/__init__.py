"""Per-code adapter specs for the molecular domain.

Four representations: orca (molecular quantum chemistry, the map's first
molecular code), openmm (classical force-field MD, a new engine class), xtb
(GFN2-xTB normal modes, IR intensities and reaction enthalpies) and
openmaterials-ai (the commons' own RRHO evaluator of the ideal-gas heat
capacity). orca and openmm also attach specs to pre-existing nodes
(TotalEnergy, Forces, Temperature, Pressure, Trajectory). build_codes
discovers every SpaceRepresentationSpec module-level object in this package.
"""

from omai.molecular.representation.orca import (
    ORCA_TOTAL_ENERGY,
    ORCA_FORCES,
    ORCA_HOMO_LUMO_GAP,
    ORCA_REACTION_BARRIER,
    ORCA_COMPUTE_HOMO_LUMO_GAP,
    ORCA_COMPUTE_REACTION_BARRIER,
    ORCA_COMPUTE_BOND_DISSOCIATION,
)
from omai.molecular.representation.openmm import (
    OPENMM_TRAJECTORY,
    OPENMM_TEMPERATURE,
    OPENMM_PRESSURE,
    OPENMM_TOTAL_ENERGY,
)
from omai.molecular.representation.xtb import (
    XTB_MOLECULAR_FREQUENCY,
    XTB_INFRARED_INTENSITY,
    XTB_MOLECULAR_REACTION_ENTHALPY,
    XTB_COMPUTE_MOLECULAR_FREQUENCIES,
    XTB_COMPUTE_INFRARED_INTENSITIES,
    XTB_COMPUTE_MOLECULAR_REACTION_ENTHALPY,
)
from omai.molecular.representation.openmaterials_ai import (
    OMAI_IDEAL_GAS_MOLAR_HEAT_CAPACITY_P,
    OMAI_IDEAL_GAS_MOLAR_HEAT_CAPACITY_P_QRRHO,
    OMAI_RRHO_IDEAL_GAS_HEAT_CAPACITY,
    OMAI_RRHO_IDEAL_GAS_HEAT_CAPACITY_QRRHO,
)

__all__ = [
    "ORCA_TOTAL_ENERGY",
    "ORCA_FORCES",
    "ORCA_HOMO_LUMO_GAP",
    "ORCA_REACTION_BARRIER",
    "ORCA_COMPUTE_HOMO_LUMO_GAP",
    "ORCA_COMPUTE_REACTION_BARRIER",
    "ORCA_COMPUTE_BOND_DISSOCIATION",
    "OPENMM_TRAJECTORY",
    "OPENMM_TEMPERATURE",
    "OPENMM_PRESSURE",
    "OPENMM_TOTAL_ENERGY",
    "XTB_MOLECULAR_FREQUENCY",
    "XTB_INFRARED_INTENSITY",
    "XTB_MOLECULAR_REACTION_ENTHALPY",
    "XTB_COMPUTE_MOLECULAR_FREQUENCIES",
    "XTB_COMPUTE_INFRARED_INTENSITIES",
    "XTB_COMPUTE_MOLECULAR_REACTION_ENTHALPY",
    "OMAI_IDEAL_GAS_MOLAR_HEAT_CAPACITY_P",
    "OMAI_IDEAL_GAS_MOLAR_HEAT_CAPACITY_P_QRRHO",
    "OMAI_RRHO_IDEAL_GAS_HEAT_CAPACITY",
    "OMAI_RRHO_IDEAL_GAS_HEAT_CAPACITY_QRRHO",
]
