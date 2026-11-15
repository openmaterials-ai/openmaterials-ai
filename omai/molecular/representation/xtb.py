r"""xtb (GFN2-xTB) adapter specs over the molecular nodes.

xtb (grimme-lab/xtb, LGPL-3.0) is the semiempirical extended tight-binding
program behind the GFN family of methods. One `xtb <geom> --ohess tight --gfn 2`
run optimizes a single conformer in the gas phase, builds the Hessian at the
optimized geometry and writes the normal modes with their IR intensities
(`g98.out`, `vibspectrum`) and a THERMO block with the RRHO enthalpy at the
requested temperature.

  operator Space              xtb artifact                                  native -> served
  --------------------------  --------------------------------------------  ----------------
  MolecularFrequency          g98.out "Frequencies --" lines                cm^-1
  InfraredIntensity           g98.out "IR Inten    --" lines                km/mol
  MolecularReactionEnthalpy   "TOTAL ENERGY" + RRHO terms per species       Eh -> kJ/mol

IdealGasMolarHeatCapacityP is not xtb's: the Cp(T) curves a record carries are
computed from these modes by the commons' own evaluator
(omai.molecular.evaluate.cp_table, the openmaterials-ai representation), so the
record credits the code that computed the number.

The two older xtb specs (MolarHeatCapacity in thermal_transport,
ReactionEnergy in stability) stay registered for the committed July 2026
records and are not re-keyed; new records land on the molecular nodes here.
"""
from __future__ import annotations

from omai.molecular.operator.edges import (
    compute_infrared_intensities,
    compute_molecular_frequencies,
    compute_molecular_reaction_enthalpy,
)
from omai.molecular.operator.nodes import (
    INFRARED_INTENSITY,
    MOLECULAR_FREQUENCY,
    MOLECULAR_REACTION_ENTHALPY,
)
from omai.representation.adapter import (
    OperatorRepresentationSpec,
    SpaceRepresentationSpec,
)

XTB_MOLECULAR_FREQUENCY = SpaceRepresentationSpec(
    space=MOLECULAR_FREQUENCY,
    representation_name="xtb",
    observable_units={"nu_mol": "inverse_cm"},
    code_api={"nu_mol": "xtb <geom> --ohess tight --gfn 2: the 'Frequencies --' lines of g98.out, cm^-1"},
    notes=(
        "The 3N-6 (3N-5 for a linear molecule) internal normal modes at the "
        "optimized geometry, in cm^-1, from the Gaussian-98 format file g98.out "
        "(three modes per block). xtb projects out the rigid translations and "
        "rotations before it writes g98.out. An imaginary mode is printed "
        "negative and n_imaginary is the saddle-order diagnostic; a converged "
        "minimum has 0. Single conformer, gas phase: both are conditions of a "
        "value."
    ),
)

XTB_INFRARED_INTENSITY = SpaceRepresentationSpec(
    space=INFRARED_INTENSITY,
    representation_name="xtb",
    observable_units={"ir_int": "km_per_mol"},
    code_api={"ir_int": "xtb <geom> --ohess tight --gfn 2: the 'IR Inten    --' lines of g98.out, km/mol"},
    notes=(
        "Per-mode IR intensities in km/mol from the GFN2-xTB dipole derivatives "
        "along each normal mode, written beside the frequencies in g98.out (and "
        "in vibspectrum), so the mode index m of InfraredIntensity and "
        "MolecularFrequency is the same."
    ),
)

XTB_MOLECULAR_REACTION_ENTHALPY = SpaceRepresentationSpec(
    space=MOLECULAR_REACTION_ENTHALPY,
    representation_name="xtb",
    observable_units={"dh_r": "kJ_per_mol"},
    code_api={"dh_r": "xtb <geom> --ohess tight --gfn 2 per species: 'TOTAL ENERGY' (Eh) plus the RRHO enthalpy of the g98.out modes; dH = sum(s_i H_i), 1 Eh = 2625.4996394799 kJ/mol"},
    notes=(
        "Each species is optimized and its Hessian built in one --ohess run. "
        "H_i is its electronic TOTAL ENERGY plus the zero-point and thermal "
        "enthalpy of its g98.out modes and the external term c_H RT, the terms "
        "of compute_molecular_reaction_enthalpy, at 298.15 K unless a "
        "condition states another. The THERMO block's TOTAL ENTHALPY is not "
        "used: xtb inverts small imaginary modes there, where this node "
        "refuses a species with any mode at or below 0 cm^-1. The reaction "
        "enthalpy is the signed stoichiometric sum, converted at 1 Eh = "
        "2625.4996394799 kJ/mol (CODATA 2018). The reaction must balance in "
        "atoms and charge. Single conformer per species and gas phase, both "
        "conditions of a value."
    ),
)

_XTB_METHOD_CHOICES = {
    "hamiltonian": "GFN2-xTB (--gfn 2).",
    "optimization": "--ohess tight: optimize to the tight convergence level, then the Hessian at that geometry.",
    "conformers": "one conformer per species, as given; no conformer search.",
    "phase": "gas; no implicit solvation.",
}

XTB_COMPUTE_MOLECULAR_FREQUENCIES = OperatorRepresentationSpec(
    operator=compute_molecular_frequencies,
    representation_name="xtb",
    discretization_choices=_XTB_METHOD_CHOICES,
    notes="Numerical Hessian from analytic GFN2-xTB gradients at the --ohess optimized geometry.",
)

XTB_COMPUTE_INFRARED_INTENSITIES = OperatorRepresentationSpec(
    operator=compute_infrared_intensities,
    representation_name="xtb",
    discretization_choices=_XTB_METHOD_CHOICES,
    notes="Dipole derivatives along the normal modes of the same --ohess run, so each intensity sits on its MolecularFrequency mode.",
)

XTB_COMPUTE_MOLECULAR_REACTION_ENTHALPY = OperatorRepresentationSpec(
    operator=compute_molecular_reaction_enthalpy,
    representation_name="xtb",
    discretization_choices=_XTB_METHOD_CHOICES,
    notes="One --ohess run per species; the stoichiometric sum of the RRHO enthalpies built from its energy and modes.",
)
