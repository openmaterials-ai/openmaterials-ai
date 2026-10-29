"""Thermal Gruneisen integration, scope, provenance and anti-circularity regressions.

Frozen literals are reviewed pins, not regenerated expectations. Synthetic unit
fixtures exercise metadata guards only; they are never published as proof
evidence. Integration tests fail, never skip, while the reviewed gamma artifacts
are absent. Compiler probes consume an already-built package selected with
PHYSLIB_BRIDGE_PACKAGE and never run the canonical audit or its writer.
"""

from __future__ import annotations

import copy
import functools
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import tomllib
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest

from omai.formula_bindings import (
    _check_compiled_evidence,
    build_formula_bindings,
    catalog_inventory,
    compiled_targets,
    formula_bindings_for,
    formula_bindings_for_physlib,
    validate_formula_bindings,
)
from omai.operator.identity import canonical_json
from physlib_tranches import (
    GLOBAL_COVERAGE, bindings_after, contracts_after, modules_after, pairs_after, subjects_after,
)

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "lean/bridge"
REVISION = "9b583cb6ef6e9cc537c4d4b786b508de1abbcf42"
OLD_REVISION = "8ddcc004043c5b537e4225fa763121c176b62a4a"
PREVIOUS_REVISIONS = (OLD_REVISION, "d70acc20677320d37b38e602e331e900466b704d")
TOOLCHAIN = "leanprover/lean4:v4.35.0"

# Reviewed Cp tranche (unchanged by this tranche).
CP_BINDING_ID = "harmonic-static-cp-identity"
CP_CONTRACT_NAME = "response-formula-contract.json"
CP_MODULE = "OMAIPhyslibHarmonicResponse"
CP_DEFINITION = "OMAI.PhyslibBridge.Response.heatCapacityPIdentity"
CP_SUBJECTS = {("operator", "contract_heat_capacity_p_identity"), ("node", "HeatCapacityConstantP")}
BASELINE_OPERATORS = frozenset({
    "compute_entropy", "compute_free_energy", "compute_heat_capacity",
    "compute_internal_energy", "contract_molar_entropy", "contract_molar_free_energy",
    "contract_molar_heat_capacity", "contract_molar_internal_energy",
    "contract_power_factor", "contract_pressure", "contract_volumetric_heat_capacity",
    "contract_zt", "sum_thermal_conductivity",
})
BASELINE_NODES = frozenset({
    "Entropy", "HeatCapacity", "HelmholtzFreeEnergy", "InternalEnergy",
    "MolarEntropy", "MolarHeatCapacity", "MolarHelmholtzFreeEnergy", "MolarInternalEnergy",
    "PowerFactor", "Pressure", "Temperature", "ThermalConductivity[contribution=total]",
    "VolumetricHeatCapacity", "ZT",
})
LEGACY_CONTRACT_HASHES = {
    "semantic-formula-contract.json": "21002241bb9dae2d674df0ede26cf7f0804823591675bcb4099142e7a5d1b123",
    "continuum-formula-contract.json": "b5fb4368abccaac9fcde8b6ccb6dfd55402f14f1a9537e898645484ba69b2e8f",
    "harmonic-ensemble-formula-contract.json": "787bff6c81de388b2631c77b044b394a03c8562c744493931f09db60e8f663ab",
    "harmonic-sums-formula-contract.json": "c897e8de5d7c1b7211f95e0cd599479c87a738de946be683bd5ab3ae78be1699",
    "harmonic-product-formula-contract.json": "adffdaa7139f3d919eb1ea058130fb502ad0d6e2e375bf2465ce47abf472d995",
    "harmonic-density-formula-contract.json": "b3f5f43df5ae50417ec309a996dcdbbef311fcac9bd4bb72957f45da28533ba8",
    "joint-density-formula-contract.json": "f5a5bb01044f479cf9770573121442a84117af1a84a6976d5ede0765256dfd04"
}
BASELINE_BINDINGS = frozenset(
    ['absolute-temperature',
     'abstract-crystal-structure',
     'classical-harmonic-frequency',
     'classical-harmonic-potential-force',
     'continuum-stress-sign',
     'harmonic-joint-molar-ensemble',
     'harmonic-joint-volumetric-heat-capacity',
     'harmonic-mode-entropy',
     'harmonic-mode-free-energy',
     'harmonic-mode-heat-capacity',
     'harmonic-mode-internal-energy',
     'harmonic-molar-entropy',
     'harmonic-molar-free-energy',
     'harmonic-molar-heat-capacity',
     'harmonic-molar-internal-energy',
     'harmonic-volumetric-heat-capacity',
     'thermodynamic-pressure',
     'thermoelectric-figure-of-merit',
     'thermoelectric-input-coefficients',
     'thermoelectric-power-factor',
     'thermoelectric-total-conductivity']
)
BASELINE_PAIRS = [{'module': 'OMAIPhyslibSemantics', 'name': 'OMAI.PhyslibBridge.figureOfMerit'},
 {'module': 'OMAIPhyslibSemantics', 'name': 'OMAI.PhyslibBridge.harmonicEntropy'},
 {'module': 'OMAIPhyslibSemantics', 'name': 'OMAI.PhyslibBridge.harmonicFreeEnergy'},
 {'module': 'OMAIPhyslibHarmonicEnsemble', 'name': 'OMAI.PhyslibBridge.harmonicHeatCapacity'},
 {'module': 'OMAIPhyslibSemantics', 'name': 'OMAI.PhyslibBridge.harmonicInternalEnergy'},
 {'module': 'OMAIPhyslibHarmonicSums', 'name': 'OMAI.PhyslibBridge.harmonicMolarEntropy'},
 {'module': 'OMAIPhyslibHarmonicSums', 'name': 'OMAI.PhyslibBridge.harmonicMolarFreeEnergy'},
 {'module': 'OMAIPhyslibHarmonicSums',
  'name': 'OMAI.PhyslibBridge.harmonicMolarHeatCapacity'},
 {'module': 'OMAIPhyslibHarmonicSums',
  'name': 'OMAI.PhyslibBridge.harmonicMolarInternalEnergy'},
 {'module': 'OMAIPhyslibHarmonicDensity',
  'name': 'OMAI.PhyslibBridge.harmonicVolumetricHeatCapacity'},
 {'module': 'OMAIPhyslibSemantics', 'name': 'OMAI.PhyslibBridge.powerFactor'},
 {'module': 'OMAIPhyslibContinuum', 'name': 'OMAI.PhyslibBridge.pressureFromStress'},
 {'module': 'OMAIPhyslibSemantics', 'name': 'OMAI.PhyslibBridge.totalThermalConductivity'}]
BASELINE_SUBJECTS = ({("operator", name) for name in BASELINE_OPERATORS}
                     | {("node", name) for name in BASELINE_NODES})
CP_ERA_CONTRACTS = frozenset(LEGACY_CONTRACT_HASHES) | {CP_CONTRACT_NAME}
CATALOG_ID_SHA = "7f60064e1533914c046b01c7b8723281def520baae4247b452e867f578c2ce8b"

# Frozen thermal Gruneisen tranche.
GAMMA_BINDING_ID = "harmonic-static-thermal-gruneisen-identity"
GAMMA_CONTRACT_NAME = "thermal-gruneisen-formula-contract.json"
GAMMA_ERA_CONTRACTS = CP_ERA_CONTRACTS | {GAMMA_CONTRACT_NAME}
# Later tranches add their own required contracts; gamma scope is unchanged (tests/physlib_tranches.py).
REQUIRED_CONTRACTS = GAMMA_ERA_CONTRACTS | contracts_after()
SUPPORT_MODULE = "OMAIPhyslibModeGruneisen"
GAMMA_MODULE = "OMAIPhyslibThermalGruneisen"
WITNESS_MODULE = "OMAIPhyslibGruneisenWitness"
SUPPORT_SOURCE = "lean/bridge/OMAIPhyslibModeGruneisen.lean"
GAMMA_SOURCE = "lean/bridge/OMAIPhyslibThermalGruneisen.lean"
WITNESS_SOURCE = "lean/bridge/OMAIPhyslibGruneisenWitness.lean"
GAMMA_NEW_SOURCES = frozenset({SUPPORT_SOURCE, GAMMA_SOURCE, WITNESS_SOURCE})
GAMMA_DEFINITION = "OMAI.PhyslibBridge.Response.thermalGruneisenIdentity"
GAMMA_THEOREM = "OMAI.PhyslibBridge.Response.harmonic_static_thermalGruneisen_eq_omai"
GAMMA_FINAL_THEOREMS = frozenset({GAMMA_THEOREM})
GAMMA_WITNESS_THEOREMS = frozenset("OMAI.PhyslibBridge.GruneisenWitness." + name for name in (
    "rate_branch",
    "rate_modeGruneisen",
    "positive_modeGruneisen_injective",
    "einsteinWeight_two_lt_one",
    "einsteinWeight_three_lt_two",
    "positive_weightedGruneisen_bounds",
    "negative_weightedGruneisen_neg",
    "positive_gamma_witness",
    "negative_gamma_witness",
    "zeroModel_weightedGruneisen",
    "zero_gamma_control",
    "positive_gamma_witness_nonunit",
))
SUPPORT_ROOTS = ("OMAI.PhyslibBridge.HarmonicVolumeModel.modeGruneisen",
                 "OMAI.PhyslibBridge.HarmonicVolumeModel.modeHeatCapacity",
                 "OMAI.PhyslibBridge.HarmonicVolumeModel.weightedGruneisen")
GAMMA_OPERATOR = "contract_thermal_gruneisen_identity"
GAMMA_OPERATOR_UID = "1348e12defce337587f9c2b152a3a1c88f9d27ec8cc48fc30167aebadd907043"
GAMMA_FORMULA_SHA = "d84872a220cba0af3fed426df7df8137e40c15bf547cdb3a4132d5e20af18f23"
GAMMA_LATEX = r"\gamma_{th} = \frac{K \alpha_{V}}{C_V^{vol}}"
GAMMA_INPUTS = ["ThermalExpansion", "BulkModulus", "VolumetricHeatCapacity"]
GAMMA_OUTPUT = "ThermalGruneisen"
GAMMA_OUTPUT_UID = "22b1bd519d50d93fd24a919e021bab85aff246464a66a08f8274558834983985"
GAMMA_ASSOCIATIONS = {
    "ThermalExpansion": "9b42f8aebb6099cdcd910a272a92208881b598688bac7830c3ae0a412152473e",
    "BulkModulus": "c0a13e64c02811f49b951271c894373267937676e0c657fc9ef09fac72558ced",
    "VolumetricHeatCapacity": "29e324b97f31cdb7d3cd8ef6aec5668fff111fd7ee96bd19dd0426b8728c1d47",
}
GRUNEISEN_UID = "a62ac1eae1e972a0b265a14f8a2af5610deb61eb0c883b7668ac4a64313b3b75"
FREQUENCY_UID = "fa262448f625b62f5a8c6934518bb8ddc5d3a5a5ce69203b3e2f6b10b21cc4b8"
GAMMA_SUBJECTS = {("operator", GAMMA_OPERATOR), ("node", GAMMA_OUTPUT)}
GAMMA_PAIR = {"name": GAMMA_DEFINITION, "module": GAMMA_MODULE}
CP_PAIR = {"name": CP_DEFINITION, "module": CP_MODULE}
EXPECTED_PAIRS = sorted([*BASELINE_PAIRS, CP_PAIR, GAMMA_PAIR], key=lambda row: (row["name"], row["module"]))
LATER_BINDINGS = bindings_after()
LATER_SUBJECTS = subjects_after()
CURRENT_PAIRS = sorted([*EXPECTED_PAIRS, *pairs_after()], key=lambda row: (row["name"], row["module"]))
LATER_MODULES = modules_after()
GAMMA_SOURCES = sorted([
    ("Physlib.StatisticalMechanics.CanonicalEnsemble.Basic", "CanonicalEnsemble.helmholtzFreeEnergy", "def", 680),
    ("Physlib.StatisticalMechanics.CanonicalEnsemble.Basic", "CanonicalEnsemble.meanEnergy", "def", 519),
    ("Physlib.StatisticalMechanics.CanonicalEnsemble.Lemmas", "CanonicalEnsemble.heatCapacity", "def", 417),
    ("Physlib.StatisticalMechanics.CanonicalEnsemble.Lemmas", "CanonicalEnsemble.meanEnergyT", "def", 409),
])
EXPECTED_COVERAGE = {
    "nodes_total": 136,
    "operators_total": 133,
    "operators_compiled": 15,
    "operators_mapped": 15,
    "nodes_compiled": 16,
    "nodes_compiled_outputs": 15,
    "nodes_compiled_interpretations": 1,
    "nodes_mapped": 29,
    "bindings_total": 23,
    "compiled_bridges": 18,
    "source_correspondences": 5,
    "upstream_declarations_referenced": 33,
    "upstream_modules_referenced": 9,
    "relations": {"exact_definition": 1, "conditional": 18, "conceptual": 4, "local": 0},
}
# Real payload after every later tranche; gamma-only synthetic checks keep EXPECTED_COVERAGE.
CURRENT_COVERAGE = GLOBAL_COVERAGE
CP_PRESERVED = {
    "lean/bridge/OMAIPhyslibHarmonicResponse.lean": "1914f2a738ae2ffaa4b35cfce04dc3a880f2d67cbf89a4ff47c7f15ec8a5f9b0",
    "lean/bridge/OMAIPhyslibHarmonicVolume.lean": "23effa45ca48c083307f32391413ab30d819db78cbee14bf6c9e62fdacb9dca5",
    "lean/bridge/OMAIPhyslibResponseCalculus.lean": "aaa0404cc1d8df8b0a437bb24c46fdb97269def69b6f6caece73947dd4ac7b12",
    "lean/bridge/OMAIPhyslibResponseUnits.lean": "c6dbff78f7335254cd12667e9bb991f1389834c3fae0036a7c50b04088a516b1",
    "lean/bridge/OMAIPhyslibResponseWitness.lean": "6dba4f1ca76e9f3dd694e0445908d0928e84a1ce58ae076019aa76cd6a30d9e7",
    "lean/bridge/OMAIPhyslibStaticEnsemble.lean": "5d949848a8253d234f8058391b3641ec3ce1aa5671653293581d403851742f9e",
    "lean/bridge/response-formula-contract.json": "f4f446f1967c45ccf508f42232e070d468121b0967459f93fc0c496210adf353",
}
PREVIOUS_ROOT_IMPORTS = [
    "OMAIPhyslibDimensions",
    "OMAIPhyslibSemantics",
    "OMAIPhyslibContinuum",
    "OMAIPhyslibHarmonicEnsemble",
    "OMAIPhyslibHarmonicSums",
    "OMAIPhyslibHarmonicProduct",
    "OMAIPhyslibHarmonicDensity",
    "OMAIPhyslibJointDensity",
    "OMAIPhyslibStaticEnsemble",
    "OMAIPhyslibResponseUnits",
    "OMAIPhyslibResponseCalculus",
    "OMAIPhyslibHarmonicVolume",
    "OMAIPhyslibResponseWitness",
    "OMAIPhyslibHarmonicResponse"
]
PREVIOUS_GLOBS = [
    "OMAIPhyslibBridge",
    "OMAIPhyslibDimensions",
    "OMAIPhyslibSemantics",
    "OMAIPhyslibContinuum",
    "OMAIPhyslibHarmonicEnsemble",
    "OMAIPhyslibHarmonicSums",
    "OMAIPhyslibHarmonicProduct",
    "OMAIPhyslibHarmonicDensity",
    "OMAIPhyslibJointDensity",
    "OMAIPhyslibStaticEnsemble",
    "OMAIPhyslibResponseUnits",
    "OMAIPhyslibResponseCalculus",
    "OMAIPhyslibHarmonicVolume",
    "OMAIPhyslibResponseWitness",
    "OMAIPhyslibHarmonicResponse"
]
CP_CONVENTION_KEYS = ["admissibility", "component_scope", "frequency_convention", "held_fixed", "model_scope", "normalization_basis", "qpoint_weighting", "reference_energy", "unit_embedding"]

# Frozen reviewed binding prose; change it only with scientific review.
GAMMA_STATEMENT = (
    "For the static-plus-harmonic Physlib ensemble on a local stable constant-pressure "
    "branch, the heat-capacity-weighted mean of mode Gruneisen parameters, defined from the "
    "volume derivatives of the mode frequencies and weighted by the actual canonical mode "
    "heat capacities, equals the OMAI identity alpha_V*K/C_V_vol. Expansion, isothermal bulk "
    "modulus and volumetric heat capacity must belong to the same free-energy surface, "
    "temperature and equilibrium volume."
)
GAMMA_CONDITIONS = [
    "Use the same finite family of full Nat harmonic occupation ensembles as the Cp binding: product counting measure, unweighted oscillator energies, dof=0 and phase-space unit=1, with static energy N_q*E_0(v) attached through an actual singleton ensemble before molar normalization.",
    "Temperature T and primitive-cell volume v are positive. Every frequency is positive and C2 on an open positive-volume domain. Static energy E_0(v) is C2, arbitrary signed, and independent of temperature. No mode may have zero or imaginary frequency; an unmodified Gamma-centred grid with zero acoustic modes does not satisfy the premises.",
    "Keep masses, composition, atom and q counts, reduced-q labels, uniform q weights and the Avogadro scale fixed, with one q mesh at every volume. Frequencies depend on volume only. Each labelled branch must be followed continuously through band crossings; sorted band order is not sufficient.",
    "Define the mode Gruneisen parameter as gamma_i(v)=-v*omega_i_prime(v)/omega_i(v) from the volume family itself. Define Gamma(T,v)=sum_i gamma_i*c_i/sum_i c_i, where c_i is the actual derivative-defined canonical heat capacity of mode i at fixed v. Gamma does not use expansion, bulk modulus, the branch, the free energy or the quotient alpha_V*K/C_V_vol.",
    "Evaluate Gamma, expansion, bulk modulus and volumetric heat capacity at the same temperature and at the branch volume v_B=V_m/N_A, per the same primitive cell that carries E_0(v) and the phonon grid. Supplied static energies, volumes and phonons must refer to that one cell.",
    "The supplied volume path is differentiable at the evaluation temperature and satisfies domain membership and F_V+p_ext=0 throughout a neighborhood, with constant external pressure. Require F_VV>0 at the evaluation point. A pointwise stationarity equation alone is insufficient.",
    "Interpret ThermalExpansion as the volumetric coefficient V_m_prime/V_m along that path, BulkModulus as the isothermal modulus V_m*F_VV at the same temperature, and VolumetricHeatCapacity as sum(c)/(N_q*v) at fixed v, equal to C_V_mol/V_m. Linear expansion, adiabatic or elastic moduli, static-only curvature and constant-pressure capacities are not these inputs.",
    "Use the volumetric form only. The molar form alpha_V*K*V_m/C_V_mol is equivalent only with V_m and C_V_mol per mole of the same primitive cells. An adiabatic modulus paired with C_V_vol gives Gamma*(1+alpha_V*Gamma*T), not Gamma.",
    "Supporting result, not a separate subject: at every point of the model domain, without a branch, the temperature derivative of pressure at fixed volume equals Gamma*C_V_vol.",
    "Gamma, every gamma_i and alpha_V may be negative or zero. No statement is made at T=0, where Gamma is a limit of a ratio of vanishing capacities.",
    "Embed model values coherently in SI: T in K, E_0 in J per primitive cell, v in m^3, V_m in m^3/mol, alpha_V in 1/K, isothermal bulk modulus in Pa and C_V_vol in J/(m^3 K). Convert Angstrom^3 by 10^-30, serving GPa by 10^9 and eV by 1.602176634e-19 J/eV. These exact-real interpretations do not certify floating-point adapters."
]
GAMMA_CONVENTIONS = {
    "model_scope": "Local hydrostatic static-plus-independent-harmonic canonical model with volume-dependent positive frequencies and no independent temperature dependence of the spectrum. Gamma is the heat-capacity-weighted mean of derivative-defined mode Gruneisen parameters. This is an OMAI model-specific extension of actual Physlib ensembles, not an upstream Gruneisen theorem or a numerical QHA solver proof.",
    "component_scope": "Finite uniform-q grid with all 3*N_atoms branches, continuously labelled branches and fixed reduced-q labels; one scalar volume coordinate along a hydrostatic path. Electronic, magnetic, configurational and anisotropic strain contributions are excluded.",
    "normalization_basis": "One primitive cell carries E_0(v), the volume coordinate and the phonon grid. Molar means per mole of those primitive cells and volumetric means per primitive-cell volume. Gamma, alpha_V, K and C_V_vol are intensive: the Avogadro scale and N_q cancel, and the identity uses the volumetric form only.",
    "frequency_convention": "Angular SI frequency with exact upstream hbar and kB in the heat-capacity weights. Stored linear THz requires omega_SI=2*pi*10^12*nu_THz. Mode Gruneisen parameters are logarithmic derivatives and do not depend on a constant frequency scale; the weights do.",
    "unit_embedding": "Coherent SI: alpha_V in 1/K, isothermal bulk modulus in Pa, C_V_vol in J/(m^3 K), primitive-cell v in m^3 and V_m in m^3/mol; Gamma and gamma_i are dimensionless. Use a common numeric-unit embedding, not raw mixed serving values.",
    "held_fixed": "Composition, masses, q labels and weights, the q mesh, the Avogadro scale and the static-energy and frequency functions are fixed. gamma_i and C_V_vol are taken at fixed v; the bulk modulus at fixed temperature; the expansion along the locally constant-pressure path.",
    "admissibility": "T>0, v>0, omega>0, N_A>0, N_q>0 and local positive isothermal curvature on the branch. Gamma, gamma_i and alpha_V are sign-free. Totalized values outside the model domain or at T=0 have no asserted physical interpretation.",
    "reference_energy": "All oscillator zero-point energies remain and shift the equilibrium volume and bulk modulus. The signed temperature-independent static energy enters the actual Hamiltonian and is not silently removed; neither contributes to the mixed temperature-volume derivative.",
    "qpoint_weighting": "Uniform full-grid q averaging with the same mesh at every volume; varying primitive volume does not change reduced-q labels or introduce fractional oscillator copies. Symmetry-reduced, tetrahedron or other nonuniform weights are outside this definition."
}
GAMMA_OBLIGATIONS = [
    "Static-energy, phonon, geometry, thermal-expansion, bulk-modulus and heat-capacity producers are interpreted inputs, not verified implementations. The theorem does not validate EOS fits, minimizers, finite-difference or polyfit derivatives, or the numerical QHA producers compute_thermal_expansion, compute_bulk_modulus_qha, compute_qha_gibbs and compute_heat_capacity_p.",
    "No claim is made about FC3 (Maradudin-Fein) or finite-difference mode Gruneisen producers, including compute_gruneisen. They estimate frequency volume derivatives at a reference volume and are not shown to equal the derivative-defined gamma_i used here.",
    "Phonopy PhonopyQHA.gruneisen_temperature evaluates a fitted alpha_V*B_T*V/C_V quotient with a finite-difference expansion, a polynomial C_V fit and zero fallbacks. It does not consume mode Gruneisen parameters and is not independent evidence for agreement with the mode-weighted Gamma.",
    "The opaque weighted contraction contract_thermal_gruneisen is not covered; it needs its own reviewed interpretation.",
    "The equilibrium branch and the common-potential input interpretation remain explicit local hypotheses. Compiled witnesses establish realizable model examples, including distinct mode Gruneisen parameters and a constant-frequency zero-response control with a single q point; they do not certify any material or numerical volume scan.",
    "Zero or imaginary modes, Gamma-point acoustic modes, nonuniform or symmetry-reduced q quadrature, q meshes that change with volume, the thermodynamic limit, independent temperature-dependent spectra, intermode coupling, anisotropic strain and tensor Gruneisen parameters, electronic or magnetic free energies, phase coexistence and mechanically unstable branches remain outside scope."
]

# Frozen reviewed contract prose; change it only with scientific review.
GAMMA_CONTRACT_SCOPE = (
    "Reviewed OMAI formula endpoint and exact Lean proof source. Hash and compiled-name "
    "checks detect drift and provenance errors; they are not automatic symbolic translation "
    "or numerical validation."
)
GAMMA_CONTRACT_INTERPRETATIONS = [
    (
        "Use the same finite family of full Nat harmonic occupation ensembles as the Cp "
        "binding: product counting measure, unweighted oscillator energies, dof=0 and "
        "phase-space unit=1, with static energy N_q*E_0(v) attached through an actual "
        "singleton ensemble before molar normalization."
    ),
    (
        "Temperature T and primitive-cell volume v are positive. Every frequency is positive "
        "and C2 on an open positive-volume domain. Static energy E_0(v) is C2, arbitrary "
        "signed, and independent of temperature. No mode may have zero or imaginary "
        "frequency; an unmodified Gamma-centred grid with zero acoustic modes does not "
        "satisfy the premises."
    ),
    (
        "Keep masses, composition, atom and q counts, reduced-q labels, uniform q weights and "
        "the Avogadro scale fixed, with one q mesh at every volume. Frequencies depend on "
        "volume only. Each labelled branch must be followed continuously through band "
        "crossings; sorted band order is not sufficient."
    ),
    (
        "Define the mode Gruneisen parameter as gamma_i(v)=-v*omega_i_prime(v)/omega_i(v) "
        "from the volume family itself. Define Gamma(T,v)=sum_i gamma_i*c_i/sum_i c_i, where "
        "c_i is the actual derivative-defined canonical heat capacity of mode i at fixed v. "
        "Gamma does not use expansion, bulk modulus, the branch, the free energy or the "
        "quotient alpha_V*K/C_V_vol."
    ),
    (
        "Evaluate Gamma, expansion, bulk modulus and volumetric heat capacity at the same "
        "temperature and at the branch volume v_B=V_m/N_A, per the same primitive cell that "
        "carries E_0(v) and the phonon grid. Supplied static energies, volumes and phonons "
        "must refer to that one cell."
    ),
    (
        "The supplied volume path is differentiable at the evaluation temperature and "
        "satisfies domain membership and F_V+p_ext=0 throughout a neighborhood, with constant "
        "external pressure. Require F_VV>0 at the evaluation point. A pointwise stationarity "
        "equation alone is insufficient."
    ),
    (
        "Interpret ThermalExpansion as the volumetric coefficient V_m_prime/V_m along that "
        "path, BulkModulus as the isothermal modulus V_m*F_VV at the same temperature, and "
        "VolumetricHeatCapacity as sum(c)/(N_q*v) at fixed v, equal to C_V_mol/V_m. Linear "
        "expansion, adiabatic or elastic moduli, static-only curvature and constant-pressure "
        "capacities are not these inputs."
    ),
    (
        "Use the volumetric form only. The molar form alpha_V*K*V_m/C_V_mol is equivalent "
        "only with V_m and C_V_mol per mole of the same primitive cells. An adiabatic modulus "
        "paired with C_V_vol gives Gamma*(1+alpha_V*Gamma*T), not Gamma."
    ),
    (
        "Supporting result, not a separate subject: at every point of the model domain, "
        "without a branch, the temperature derivative of pressure at fixed volume equals "
        "Gamma*C_V_vol."
    ),
    (
        "Gamma, every gamma_i and alpha_V may be negative or zero. No statement is made at "
        "T=0, where Gamma is a limit of a ratio of vanishing capacities."
    ),
    (
        "Embed model values coherently in SI: T in K, E_0 in J per primitive cell, v in m^3, "
        "V_m in m^3/mol, alpha_V in 1/K, isothermal bulk modulus in Pa and C_V_vol in J/(m^3 "
        "K). Convert Angstrom^3 by 10^-30, serving GPa by 10^9 and eV by 1.602176634e-19 "
        "J/eV. These exact-real interpretations do not certify floating-point adapters."
    ),
    (
        "Only contract_thermal_gruneisen_identity and its ThermalGruneisen output are proof "
        "subjects. ThermalExpansion, BulkModulus and VolumetricHeatCapacity are input "
        "associations. Support, witness, fixed-volume and Mie-Gruneisen results do not "
        "certify the opaque contract_thermal_gruneisen contraction, FC3, finite-difference or "
        "Phonopy Gruneisen estimators, or numerical QHA producers."
    ),
]

# Anti-circularity: forbidden and required constants in the closures of the Gamma definitions.
FORBIDDEN_EXACT = frozenset({
    *("OMAI.PhyslibBridge.Response." + name for name in (
        "FT", "FV", "FTT", "FVV", "mixedTV", "internalEnergy", "cv", "bulk", "expansion", "cp",
        "StableBranchAt", "thermalGruneisenIdentity", "heatCapacityPIdentity")),
    *("OMAI.PhyslibBridge.HarmonicVolumeModel." + name for name in (
        "freeEnergy", "cellFreeEnergy", "internalEnergy", "entropy", "cv", "actualMolarInternalEnergy",
        "actualCp", "staticEnergy", "staticEnergy_C2", "ensembleAt")),
    "OMAI.PhyslibBridge.molarLift",
    "OMAI.PhyslibBridge.staticHarmonicGridEnsemble",
    "OMAI.PhyslibBridge.staticEnergyEnsemble",
    "OMAI.PhyslibBridge.harmonicGridEnsemble",
    "OMAI.PhyslibBridge.harmonicVolumetricHeatCapacity",
})
FORBIDDEN_PREFIXES = ("OMAI.PhyslibBridge.Response.StableBranchAt.",)
RESPONSE_PREFIX = "OMAI.PhyslibBridge.Response."
REQUIRED_IN_WEIGHTED = frozenset({
    "CanonicalEnsemble.heatCapacity",
    "OMAI.PhyslibBridge.harmonicEnsemble",
    "OMAI.PhyslibBridge.HarmonicVolumeModel.gridAt",
    "OMAI.PhyslibBridge.HarmonicVolumeModel.omega",
    "OMAI.PhyslibBridge.HarmonicVolumeModel.modeGruneisen",
    "deriv",
})
REQUIRED_IN_MODE = frozenset({"OMAI.PhyslibBridge.HarmonicVolumeModel.omega", "deriv"})
# Reviewed allowlist of reachable non-theorem bridge constants. Any extension needs
# review: a new helper fails here until it is added.
ALLOWED_OMAI_CLOSURE = frozenset({
    *("OMAI.PhyslibBridge.HarmonicVolumeModel" + suffix for suffix in (
        "", ".mk", ".reference", ".J", ".omega", ".omega_pos", ".gridAt",
        ".modeGruneisen", ".modeHeatCapacity", ".weightedGruneisen")),
    *("OMAI.PhyslibBridge.HarmonicModeGrid" + suffix for suffix in (
        "", ".mk", ".qCount", ".qCount_pos", ".atomCount", ".atomCount_pos",
        ".avogadro", ".avogadro_pos", ".oscillator")),
    "OMAI.PhyslibBridge.harmonicEnsemble",
})
EXPECTED_HEADS = "|".join([
    "4", "Real", "OMAI.PhyslibBridge.HarmonicVolumeModel.weightedGruneisen", GAMMA_DEFINITION,
    ",".join(["OMAI.PhyslibBridge.Response.expansion", "OMAI.PhyslibBridge.Response.bulk",
              "OMAI.PhyslibBridge.harmonicVolumetricHeatCapacity"]),
])
FORBIDDEN_TEXT = re.compile(
    r"MUST agree|law_contract_thermal_gruneisen_identity"
    r"|gruneisen_temperature[^.]*(?:produces|computes)[^.]*weighted", re.IGNORECASE)
_CONTRACT_KEYS = {"schema_version", "scope", "source_path", "source_sha256", "operators", "nodes",
                  "interpretations"}
_IMPORT = re.compile(r"^\s*(?:public\s+)?(?:meta\s+)?import\s+(?:all\s+)?(\S+)", re.MULTILINE)
BACKTICK = chr(96)


def _load_json(path):
    return json.loads(Path(path).read_text())


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, PACKAGE / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

@functools.lru_cache(maxsize=1)
def _inventory():
    return catalog_inventory()


def _subjects(payload):
    return {
        (target["kind"], target["id"])
        for binding in payload["bindings"]
        for target in compiled_targets(binding, payload["inventory"])
    }


def _binding(payload, binding_id):
    rows = [row for row in payload["bindings"] if row["id"] == binding_id]
    assert len(rows) == 1, f"integration pending: expected exactly one reviewed {binding_id} binding"
    return rows[0]


def _gamma_binding(payload):
    return _binding(payload, GAMMA_BINDING_ID)


def _explicit(binding):
    rows = binding["evidence"].get("proved_targets", [])
    return [(row["kind"], row["id"]) for row in rows]


def _assert_gamma_scope(payload):
    binding = _gamma_binding(payload)
    assert binding["relation"] == "conditional"
    assert binding["evidence"]["kind"] == "compiled_bridge"
    explicit = _explicit(binding)
    assert len(explicit) == 2 and set(explicit) == GAMMA_SUBJECTS, "gamma proof scope broadened"
    cp = _explicit(_binding(payload, CP_BINDING_ID))
    assert len(cp) == 2 and set(cp) == CP_SUBJECTS, "Cp proof scope broadened"
    assert _subjects(payload) == BASELINE_SUBJECTS | CP_SUBJECTS | GAMMA_SUBJECTS, "unique proof subjects changed"
    assert {row["id"] for row in payload["bindings"]} == BASELINE_BINDINGS | {CP_BINDING_ID, GAMMA_BINDING_ID}
    coverage = payload["coverage"]
    assert {key: coverage[key] for key in EXPECTED_COVERAGE} == EXPECTED_COVERAGE


def _assert_gamma_current_scope(payload):
    """Real-payload ledger after the later quasiharmonic tranche; the gamma scope is unchanged."""
    binding = _gamma_binding(payload)
    assert binding["relation"] == "conditional"
    assert binding["evidence"]["kind"] == "compiled_bridge"
    explicit = _explicit(binding)
    assert len(explicit) == 2 and set(explicit) == GAMMA_SUBJECTS, "gamma proof scope broadened"
    cp = _explicit(_binding(payload, CP_BINDING_ID))
    assert len(cp) == 2 and set(cp) == CP_SUBJECTS, "Cp proof scope broadened"
    assert _subjects(payload) == BASELINE_SUBJECTS | CP_SUBJECTS | GAMMA_SUBJECTS | LATER_SUBJECTS
    assert {row["id"] for row in payload["bindings"]} == (
        BASELINE_BINDINGS | {CP_BINDING_ID, GAMMA_BINDING_ID} | LATER_BINDINGS)
    coverage = payload["coverage"]
    assert {key: coverage[key] for key in CURRENT_COVERAGE} == CURRENT_COVERAGE


def _assert_gamma_contract(contract, root=ROOT):
    assert set(contract) <= _CONTRACT_KEYS
    assert contract["schema_version"] == 1
    assert contract["source_path"] == GAMMA_SOURCE
    assert contract["source_sha256"] == _digest(root / GAMMA_SOURCE)
    assert isinstance(contract.get("scope"), str) and contract["scope"]
    interpretations = contract.get("interpretations")
    assert isinstance(interpretations, list) and interpretations
    assert all(isinstance(row, str) and row for row in interpretations)
    assert len(contract["operators"]) == 1
    operator = contract["operators"][0]
    assert set(operator) <= {"id", "uid", "formula_sha256", "formula_latex", "lean_definition",
                             "definition_source_path"}
    assert (operator["id"], operator["uid"], operator["formula_sha256"]) == (
        GAMMA_OPERATOR, GAMMA_OPERATOR_UID, GAMMA_FORMULA_SHA)
    assert operator["formula_latex"] == GAMMA_LATEX
    assert operator["lean_definition"] == GAMMA_DEFINITION
    assert operator.get("definition_source_path", GAMMA_SOURCE) == GAMMA_SOURCE
    assert len(contract["nodes"]) == 1
    node = contract["nodes"][0]
    assert set(node) <= {"id", "uid", "lean_definition"}
    assert (node["id"], node["uid"]) == (GAMMA_OUTPUT, GAMMA_OUTPUT_UID)
    assert node.get("lean_definition", GAMMA_DEFINITION) == GAMMA_DEFINITION


def _target(kind, name):
    rows = _inventory()["operators" if kind == "operator" else "nodes"]
    row = next(row for row in rows if row["id"] == name)
    target = {"kind": kind, "id": name, "uid": row["uid"]}
    if kind == "operator":
        target["formula_sha256"] = row["formula_sha256"]
    return target


def _synthetic_gamma_seeds():
    """Reviewed seeds plus a metadata-only gamma binding; never proof evidence."""
    seeds = _load_json(ROOT / "omai/data/physlib_formula_seeds.json")
    cp = _binding(seeds, CP_BINDING_ID)
    seeds["bindings"] = [row for row in seeds["bindings"]
                         if row["id"] in BASELINE_BINDINGS or row["id"] == CP_BINDING_ID]
    gamma = copy.deepcopy(cp)
    gamma["id"] = GAMMA_BINDING_ID
    gamma["statement"] = "Synthetic metadata-only fixture; not proof evidence."
    gamma["targets"] = [_target("operator", GAMMA_OPERATOR), _target("node", GAMMA_OUTPUT),
                        *(_target("node", name) for name in GAMMA_INPUTS)]
    gamma["sources"] = [row for row in cp["sources"]
                        if (row["module"], row["name"], row["kind"], row["line"]) in set(GAMMA_SOURCES)]
    assert len(gamma["sources"]) == len(GAMMA_SOURCES)
    gamma["evidence"] = {
        **copy.deepcopy(cp["evidence"]), "module": GAMMA_MODULE, "source_path": GAMMA_SOURCE,
        "source_sha256": "0" * 64, "declarations": sorted(GAMMA_FINAL_THEOREMS),
        "proved_targets": [{"kind": kind, "id": name} for kind, name in sorted(GAMMA_SUBJECTS)],
    }
    seeds["bindings"].append(gamma)
    return seeds


def _seed_binding(seeds, binding_id=GAMMA_BINDING_ID):
    return next(row for row in seeds["bindings"] if row["id"] == binding_id)


def _write_contract(directory, contract):
    path = directory / "mutated-formula-contract.json"
    path.write_text(json.dumps(contract))
    return path


def _binding_text(statement, conditions, conventions, obligations):
    return [statement, *conditions, *conventions.values(), *obligations]


def _lean_imports(path):
    return _IMPORT.findall(Path(path).read_text())


def _bridge_import_closure(module):
    seen, stack = set(), [module]
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        seen.add(name)
        path = PACKAGE / (name + ".lean")
        if path.is_file():
            stack.extend(item for item in _lean_imports(path) if item.startswith("OMAIPhyslib"))
    return seen - {module}


@pytest.fixture(scope="module")
def gamma_payload():
    payload = build_formula_bindings()
    _gamma_binding(payload)  # Missing final artifacts fail, never skip or xfail.
    return payload


@pytest.fixture(scope="module")
def gamma_contract():
    path = PACKAGE / GAMMA_CONTRACT_NAME
    assert path.is_file(), "integration pending: reviewed thermal Gruneisen contract is absent"
    return _load_json(path)


@pytest.fixture
def gamma_synthetic_contract(tmp_path):
    root = tmp_path / "repo"
    source = root / GAMMA_SOURCE
    source.parent.mkdir(parents=True)
    source.write_text("-- Synthetic source bytes for contract-guard tests, not a Lean proof.\n")
    contract = {
        "schema_version": 1, "scope": "synthetic contract-guard fixture",
        "source_path": GAMMA_SOURCE, "source_sha256": _digest(source),
        "operators": [{"id": GAMMA_OPERATOR, "uid": GAMMA_OPERATOR_UID, "formula_sha256": GAMMA_FORMULA_SHA,
                       "formula_latex": GAMMA_LATEX, "lean_definition": GAMMA_DEFINITION}],
        "nodes": [{"id": GAMMA_OUTPUT, "uid": GAMMA_OUTPUT_UID}],
        "interpretations": ["synthetic fixture"],
    }
    return SimpleNamespace(root=root, contract=contract)


@pytest.fixture
def gamma_evidence_copy(tmp_path, gamma_payload):
    """Recorded snapshot of the real gamma evidence for consumer mutations."""
    binding = copy.deepcopy(_gamma_binding(gamma_payload))
    record_path = Path(binding["evidence"]["build_record"])
    record = _load_json(ROOT / record_path)
    target_root = tmp_path / "repo"
    for relative, digest in record["sources"].items():
        source = ROOT / relative
        assert source.resolve().is_relative_to(PACKAGE.resolve())
        assert _digest(source) == digest, f"recorded input changed during test: {relative}"
        destination = target_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    target_record = target_root / record_path
    target_record.write_text(json.dumps(record))
    data = SimpleNamespace(root=target_root, binding=binding, upstream=copy.deepcopy(gamma_payload["upstream"]),
                           record=record, record_path=target_record)
    _check_compiled_evidence(data.binding, data.upstream, data.root)
    return data


def test_gamma_unit_catalog_pins():
    inventory = catalog_inventory()
    operators = {row["id"]: row for row in inventory["operators"]}
    nodes = {row["id"]: row for row in inventory["nodes"]}
    row = operators[GAMMA_OPERATOR]
    assert (row["uid"], row["formula_sha256"]) == (GAMMA_OPERATOR_UID, GAMMA_FORMULA_SHA)
    assert row["formula_latex"] == GAMMA_LATEX
    assert row["inputs"] == GAMMA_INPUTS and row["outputs"] == [GAMMA_OUTPUT]
    assert nodes[GAMMA_OUTPUT]["uid"] == GAMMA_OUTPUT_UID
    assert {name: nodes[name]["uid"] for name in GAMMA_ASSOCIATIONS} == GAMMA_ASSOCIATIONS
    assert (nodes["Gruneisen"]["uid"], nodes["Frequency"]["uid"]) == (GRUNEISEN_UID, FREQUENCY_UID)
    projection = {
        "nodes": [{key: row[key] for key in ("id", "uid")} for row in inventory["nodes"]],
        "operators": [{key: row[key] for key in ("id", "uid", "formula_sha256")}
                      for row in inventory["operators"]],
    }
    assert hashlib.sha256(canonical_json(projection).encode()).hexdigest() == CATALOG_ID_SHA


@pytest.mark.parametrize("relative,digest", sorted(CP_PRESERVED.items()))
def test_gamma_unit_cp_preserved_bytes(relative, digest):
    assert _digest(ROOT / relative) == digest


def test_gamma_unit_scope_ledger_accepts_synthetic():
    _assert_gamma_scope(build_formula_bindings(_synthetic_gamma_seeds()))


@pytest.mark.parametrize("kind,name", [
    ("operator", "contract_thermal_gruneisen"), ("operator", "compute_gruneisen"),
    ("operator", "contract_molar_volume"), ("operator", "compute_thermal_expansion"),
    ("operator", "compute_bulk_modulus_qha"), ("operator", "compute_qha_gibbs"),
    ("operator", "compute_heat_capacity_p"), ("node", "Gruneisen"), ("node", "ThermalExpansion"),
    ("node", "BulkModulus"), ("node", "VolumetricHeatCapacity"), ("node", "MolarVolume"),
    ("node", "CellVolume"), ("node", "Frequency"), ("node", "HeatCapacity"), ("node", "Temperature"),
])
def test_gamma_unit_scope_guard_rejects_extra_subjects(kind, name):
    seeds = _synthetic_gamma_seeds()
    binding = _seed_binding(seeds)
    if not any(row["kind"] == kind and row["id"] == name for row in binding["targets"]):
        binding["targets"].append(_target(kind, name))
    binding["evidence"]["proved_targets"].append({"kind": kind, "id": name})
    with pytest.raises(AssertionError, match="gamma proof scope broadened"):
        _assert_gamma_scope(build_formula_bindings(seeds))


def test_gamma_unit_associations_do_not_become_subjects():
    seeds = _synthetic_gamma_seeds()
    _seed_binding(seeds)["targets"].extend([_target("node", "Gruneisen"), _target("node", "Frequency")])
    payload = build_formula_bindings(seeds)
    assert _subjects(payload) == BASELINE_SUBJECTS | CP_SUBJECTS | GAMMA_SUBJECTS
    coverage = payload["coverage"]
    # Frequency is already referenced by classical-harmonic-frequency; only Gruneisen is new.
    assert {key: coverage[key] for key in EXPECTED_COVERAGE} == {**EXPECTED_COVERAGE, "nodes_mapped": 30}


def test_gamma_unit_second_route_is_depth_not_new_output():
    seeds = _synthetic_gamma_seeds()
    second = copy.deepcopy(_seed_binding(seeds))
    second["id"] = "synthetic-second-thermal-gruneisen-route"
    second["targets"] = [_target("operator", "contract_thermal_gruneisen"), _target("node", GAMMA_OUTPUT),
                         _target("node", "Gruneisen"), _target("node", "Frequency")]
    second["evidence"]["proved_targets"] = [{"kind": "node", "id": GAMMA_OUTPUT},
                                            {"kind": "operator", "id": "contract_thermal_gruneisen"}]
    seeds["bindings"].append(second)
    payload = build_formula_bindings(seeds)
    coverage = payload["coverage"]
    assert {key: coverage[key] for key in EXPECTED_COVERAGE} == {
        **EXPECTED_COVERAGE, "operators_compiled": 16, "operators_mapped": 16, "nodes_mapped": 30,
        "bindings_total": 24, "compiled_bridges": 19,
        "relations": {"exact_definition": 1, "conditional": 19, "conceptual": 4, "local": 0},
    }
    with pytest.raises(AssertionError, match="unique proof subjects changed"):
        _assert_gamma_scope(payload)


@pytest.mark.parametrize("field", ["operator_uid", "formula_sha256", "output_uid", "association_uid"])
def test_gamma_unit_generator_refuses_stale_pin(field):
    seeds = _synthetic_gamma_seeds()
    targets = _seed_binding(seeds)["targets"]
    if field == "operator_uid":
        targets[0]["uid"] = "0" * 64
    elif field == "formula_sha256":
        targets[0]["formula_sha256"] = "0" * 64
    elif field == "output_uid":
        targets[1]["uid"] = "0" * 64
    else:
        targets[2]["uid"] = "0" * 64
    with pytest.raises(ValueError, match="reviewed .*stale"):
        build_formula_bindings(seeds)


def test_gamma_unit_contract_guard_accepts_synthetic(gamma_synthetic_contract):
    _assert_gamma_contract(gamma_synthetic_contract.contract, gamma_synthetic_contract.root)


@pytest.mark.parametrize("mutation", [
    "operator_uid", "formula_sha", "node_uid", "definition", "source", "source_hash",
    "definition_source", "extra_operator", "extra_node", "formula_latex", "extra_node_gruneisen",
    "extra_node_input",
])
def test_gamma_unit_contract_guard_rejects_endpoint_drift(gamma_synthetic_contract, mutation):
    contract = copy.deepcopy(gamma_synthetic_contract.contract)
    operator = contract["operators"][0]
    if mutation == "operator_uid":
        operator["uid"] = "0" * 64
    elif mutation == "formula_sha":
        operator["formula_sha256"] = "0" * 64
    elif mutation == "node_uid":
        contract["nodes"][0]["uid"] = "0" * 64
    elif mutation == "definition":
        operator["lean_definition"] = CP_DEFINITION
    elif mutation == "source":
        contract["source_path"] = "lean/bridge/OMAIPhyslibHarmonicResponse.lean"
    elif mutation == "source_hash":
        contract["source_sha256"] = "0" * 64
    elif mutation == "definition_source":
        operator["definition_source_path"] = "lean/bridge/OMAIPhyslibContinuum.lean"
    elif mutation == "extra_operator":
        contract["operators"].append({**operator, "id": "contract_thermal_gruneisen"})
    elif mutation == "extra_node":
        contract["nodes"].append({"id": "Temperature", "uid": "0" * 64})
    elif mutation == "formula_latex":
        operator["formula_latex"] = r"\gamma_{th} = \frac{\alpha_{V} K}{C_V^{vol}}"
    elif mutation == "extra_node_gruneisen":
        contract["nodes"].append({"id": "Gruneisen", "uid": GRUNEISEN_UID})
    elif mutation == "extra_node_input":
        contract["nodes"].append({"id": "ThermalExpansion", "uid": GAMMA_ASSOCIATIONS["ThermalExpansion"]})
    else:
        raise AssertionError(mutation)
    with pytest.raises(AssertionError):
        _assert_gamma_contract(contract, gamma_synthetic_contract.root)


class _ReachedCompiler(Exception):
    """Sentinel: the temporary pre-build gate passed; no compiler/writer ran."""


def _temporary_required_contract_gate(tmp_path, monkeypatch, missing=None):
    module = _load_module("gamma_required_contract_gate", "audit.py")
    root = tmp_path / "repo"
    package = root / "lean/bridge"
    package.mkdir(parents=True)
    # Contents are deliberately synthetic: only the missing-file preflight is exercised.
    for name in REQUIRED_CONTRACTS - {missing}:
        (package / name).write_text("{}")
    for name in ("lean-toolchain", "lakefile.toml", "lake-manifest.json", "audit.py", "verify_contracts.py"):
        (package / name).write_text("synthetic pre-build fixture\n")
    monkeypatch.setattr(module, "ROOT", package)
    monkeypatch.setattr(module, "REPO", root)

    def stop_before_compiler(*args, **kwargs):
        raise _ReachedCompiler("no compiler or audit writer executed")

    monkeypatch.setattr(module, "subprocess", SimpleNamespace(run=stop_before_compiler))
    return module, package


def test_gamma_unit_required_contract_preflight_reaches_sentinel_when_complete(tmp_path, monkeypatch):
    module, package = _temporary_required_contract_gate(tmp_path, monkeypatch)
    with pytest.raises(_ReachedCompiler):
        module.run()
    assert not (package / "build-evidence.json").exists()


def test_gamma_unit_audit_requires_gamma_contract(tmp_path, monkeypatch):
    module, package = _temporary_required_contract_gate(tmp_path, monkeypatch, GAMMA_CONTRACT_NAME)
    with pytest.raises(ValueError, match=r"reviewed formula contracts are missing:.*"
                       + re.escape(GAMMA_CONTRACT_NAME)):
        module.run()
    assert not (package / "build-evidence.json").exists()


def test_gamma_unit_frozen_binding_text_is_ascii_and_scoped():
    texts = _binding_text(GAMMA_STATEMENT, GAMMA_CONDITIONS, GAMMA_CONVENTIONS, GAMMA_OBLIGATIONS)
    assert all(isinstance(text, str) and text and text.isascii() for text in texts)
    assert len(GAMMA_CONDITIONS) == len(set(GAMMA_CONDITIONS)) == 11
    assert sorted(GAMMA_CONVENTIONS) == CP_CONVENTION_KEYS
    assert len(GAMMA_OBLIGATIONS) == len(set(GAMMA_OBLIGATIONS)) == 6
    assert not any(FORBIDDEN_TEXT.search(text) for text in texts)
    obligations = "\n".join(GAMMA_OBLIGATIONS)
    for phrase in ("Maradudin-Fein", "finite-difference", "compute_gruneisen", "gruneisen_temperature",
                   "contract_thermal_gruneisen ", "compute_thermal_expansion", "Zero or imaginary modes"):
        assert phrase in obligations, phrase


def test_gamma_integration_contract_is_exact(gamma_contract):
    _assert_gamma_contract(gamma_contract)
    # Whole reviewed contract, including its prose scope and interpretations.
    assert gamma_contract == {
        "schema_version": 1,
        "scope": GAMMA_CONTRACT_SCOPE,
        "source_path": GAMMA_SOURCE,
        "source_sha256": _digest(ROOT / GAMMA_SOURCE),
        "operators": [{"id": GAMMA_OPERATOR, "uid": GAMMA_OPERATOR_UID, "formula_sha256": GAMMA_FORMULA_SHA,
                       "formula_latex": GAMMA_LATEX, "lean_definition": GAMMA_DEFINITION}],
        "nodes": [{"id": GAMMA_OUTPUT, "uid": GAMMA_OUTPUT_UID}],
        "interpretations": GAMMA_CONTRACT_INTERPRETATIONS,
    }
    prose = [GAMMA_CONTRACT_SCOPE, *GAMMA_CONTRACT_INTERPRETATIONS]
    assert all(text.isascii() for text in prose)
    assert not any(FORBIDDEN_TEXT.search(text) for text in prose)


def test_gamma_integration_scope_and_evidence(gamma_payload):
    _assert_gamma_current_scope(gamma_payload)
    binding = _gamma_binding(gamma_payload)
    # The generator orders targets by (kind, id); compare against that exact canonical order.
    assert [(row["kind"], row["id"], row["uid"], row.get("formula_sha256")) for row in binding["targets"]] == sorted([
        ("operator", GAMMA_OPERATOR, GAMMA_OPERATOR_UID, GAMMA_FORMULA_SHA),
        ("node", GAMMA_OUTPUT, GAMMA_OUTPUT_UID, None),
        *(("node", name, uid, None) for name, uid in GAMMA_ASSOCIATIONS.items()),
    ], key=lambda target: (target[0], target[1]))
    assert sorted((row["module"], row["name"], row["kind"], row["line"]) for row in binding["sources"]) \
        == GAMMA_SOURCES
    evidence = binding["evidence"]
    assert evidence["kind"] == "compiled_bridge"
    assert evidence["module"] == GAMMA_MODULE and evidence["source_path"] == GAMMA_SOURCE
    assert evidence["source_sha256"] == _digest(ROOT / GAMMA_SOURCE)
    assert evidence["build_record"] == "lean/bridge/build-evidence.json"
    assert evidence["declarations"] == sorted(GAMMA_FINAL_THEOREMS)
    assert not GAMMA_WITNESS_THEOREMS.intersection(evidence["declarations"])


def test_gamma_integration_binding_text_exact(gamma_payload):
    binding = _gamma_binding(gamma_payload)
    assert binding["statement"] == GAMMA_STATEMENT
    assert binding["conditions"] == GAMMA_CONDITIONS
    assert binding["conventions"] == GAMMA_CONVENTIONS
    assert binding["remaining_obligations"] == GAMMA_OBLIGATIONS
    texts = _binding_text(binding["statement"], binding["conditions"], binding["conventions"],
                          binding["remaining_obligations"])
    assert all(text.isascii() for text in texts)
    assert not any(FORBIDDEN_TEXT.search(text) for text in texts)


@pytest.mark.parametrize("operator", ["compute_gruneisen", "contract_molar_volume"])
def test_gamma_integration_sibling_gaps(gamma_payload, operator):
    assert formula_bindings_for(operator, kind="operator") == []


@pytest.mark.parametrize("operator", ["contract_thermal_gruneisen", "compute_heat_capacity_p"])
def test_gamma_integration_siblings_only_in_qha_tranche(gamma_payload, operator):
    rows = formula_bindings_for(operator, kind="operator")
    assert len(rows) == 1 and rows[0]["id"] in LATER_BINDINGS
    assert rows[0]["id"] != GAMMA_BINDING_ID


def test_gamma_integration_exact_lookups(gamma_payload):
    assert formula_bindings_for("Gruneisen", kind="node") == []
    assert sorted(row["id"] for row in formula_bindings_for(GAMMA_OUTPUT, kind="node")) == [
        "harmonic-qha-thermal-gruneisen-contraction", GAMMA_BINDING_ID]
    assert [row["id"] for row in formula_bindings_for(GAMMA_OPERATOR, kind="operator")] == [GAMMA_BINDING_ID]


def test_gamma_integration_record_covers_sources(gamma_payload, gamma_contract):
    validate_formula_bindings(gamma_payload, check_catalog=True, proof_root=ROOT)
    record = _load_json(PACKAGE / "build-evidence.json")
    assert record["upstream_revision"] == gamma_payload["upstream"]["revision"] == REVISION
    tracked = GAMMA_NEW_SOURCES | {"lean/bridge/" + GAMMA_CONTRACT_NAME}
    assert tracked <= record["sources"].keys()
    assert {path: record["sources"][path] for path in tracked} == {path: _digest(ROOT / path) for path in tracked}
    assert {"lean/bridge/" + name for name in REQUIRED_CONTRACTS} <= record["sources"].keys()
    assert record["contract_name_audit"] == {"status": "passed", "pair_count": len(CURRENT_PAIRS),
                                             "pairs": CURRENT_PAIRS}
    audit = record["axiom_audit"]
    assert {SUPPORT_MODULE, GAMMA_MODULE, WITNESS_MODULE} <= set(audit["source_modules"])
    declarations = audit["declarations"]
    assert GAMMA_FINAL_THEOREMS | GAMMA_WITNESS_THEOREMS <= declarations.keys()
    for name in sorted(GAMMA_FINAL_THEOREMS | GAMMA_WITNESS_THEOREMS):
        assert set(declarations[name]) <= {"propext", "Classical.choice", "Quot.sound"}, name


GAMMA_RECORD_MUTATIONS = [
    *(f"source_bytes:{path}" for path in sorted(GAMMA_NEW_SOURCES | {"lean/bridge/" + GAMMA_CONTRACT_NAME})),
    *(f"record_revision:{revision}" for revision in PREVIOUS_REVISIONS),
    *(f"dependency_revision:{revision}" for revision in PREVIOUS_REVISIONS),
    "missing_gamma_source_hash", "binding_source_hash", "missing_gamma_pair", "wrong_pair_count",
    "unapproved_axiom", "missing_advertised_declaration",
]


@pytest.mark.parametrize("mutation", GAMMA_RECORD_MUTATIONS)
def test_gamma_record_consumer_refuses_drift(gamma_evidence_copy, mutation):
    data = gamma_evidence_copy
    record = data.record
    kind, _, value = mutation.partition(":")
    if kind == "source_bytes":
        path = data.root / value
        path.write_bytes(path.read_bytes() + b"\n")
    elif kind == "record_revision":
        record["upstream_revision"] = value
    elif kind == "dependency_revision":
        record["dependencies"]["physlib"] = value
    elif kind == "missing_gamma_source_hash":
        del record["sources"][GAMMA_SOURCE]
    elif kind == "binding_source_hash":
        data.binding["evidence"]["source_sha256"] = "0" * 64
    elif kind == "missing_gamma_pair":
        record["contract_name_audit"]["pairs"].remove(GAMMA_PAIR)
        record["contract_name_audit"]["pair_count"] -= 1
    elif kind == "wrong_pair_count":
        record["contract_name_audit"]["pair_count"] += 1
    elif kind == "unapproved_axiom":
        record["axiom_audit"]["declarations"][GAMMA_THEOREM].append("sorryAx")
    elif kind == "missing_advertised_declaration":
        del record["axiom_audit"]["declarations"][GAMMA_THEOREM]
        record["axiom_audit"]["declaration_count"] -= 1
    else:
        raise AssertionError(mutation)
    data.record_path.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        _check_compiled_evidence(data.binding, data.upstream, data.root)


def test_gamma_integration_reproducibility_and_exact_reverse_lookup(gamma_payload, tmp_path, monkeypatch):
    text = json.dumps(gamma_payload, indent=2, ensure_ascii=False) + "\n"
    assert (ROOT / "omai/data/formula_bindings.json").read_text() == text
    assert (ROOT / "docs/data/formula_bindings.json").read_text() == text
    assert build_formula_bindings() == gamma_payload
    binding = _gamma_binding(gamma_payload)
    monkeypatch.chdir(tmp_path)
    assert formula_bindings_for(GAMMA_OPERATOR, kind="operator") == [binding]
    for source in binding["sources"]:
        rows = formula_bindings_for_physlib(declaration=source["name"], module=source["module"])
        assert binding in rows


def test_gamma_integration_import_structure():
    for relative in sorted(GAMMA_NEW_SOURCES):
        assert (ROOT / relative).is_file(), f"integration pending: {relative} is absent"
    assert sorted(_lean_imports(ROOT / SUPPORT_SOURCE)) == ["OMAIPhyslibHarmonicVolume", "OMAIPhyslibJointDensity"]
    assert _lean_imports(ROOT / GAMMA_SOURCE) == [SUPPORT_MODULE]
    witness = set(_lean_imports(ROOT / WITNESS_SOURCE))
    assert "OMAIPhyslibResponseWitness" in witness and witness & {SUPPORT_MODULE, GAMMA_MODULE}
    assert witness <= {SUPPORT_MODULE, GAMMA_MODULE, "OMAIPhyslibResponseWitness"}
    assert not {GAMMA_MODULE, WITNESS_MODULE} & _bridge_import_closure(SUPPORT_MODULE)
    importers = {path.stem for path in PACKAGE.glob("*.lean") if GAMMA_MODULE in _lean_imports(path)}
    assert "OMAIPhyslibBridge" in importers and importers <= {"OMAIPhyslibBridge", WITNESS_MODULE}
    assert _lean_imports(PACKAGE / "OMAIPhyslibBridge.lean") == [
        *PREVIOUS_ROOT_IMPORTS, SUPPORT_MODULE, GAMMA_MODULE, WITNESS_MODULE, *LATER_MODULES]
    lakefile = tomllib.loads((PACKAGE / "lakefile.toml").read_text())
    assert [row["name"] for row in lakefile["lean_lib"]] == ["OMAIPhyslibBridge"]
    assert lakefile["lean_lib"][0]["globs"] == [
        *PREVIOUS_GLOBS, SUPPORT_MODULE, GAMMA_MODULE, WITNESS_MODULE, *LATER_MODULES]


def _configured_compiled_package():
    configured = os.environ.get("PHYSLIB_BRIDGE_PACKAGE")
    if not configured:
        pytest.skip("optional real-compiler check: set PHYSLIB_BRIDGE_PACKAGE to the built package")
    package = Path(configured).resolve()
    manifest = _load_json(package / "lake-manifest.json")
    assert next(p["rev"] for p in manifest["packages"]
                if p["name"].lower() == "physlib") == REVISION, "wrong compiled-package pin"
    assert (package / "lean-toolchain").read_text().strip() == TOOLCHAIN
    return package


@pytest.fixture(scope="module")
def gamma_compiled_package(gamma_contract):
    # First require the real frozen artifact; optional compiler opt-in must not
    # hide an absent gamma contract behind an environment-based skip.
    return _configured_compiled_package()


def _verify_strict(paths, package):
    """Use the real existing verifier; add warnings-as-errors to its real command."""
    verifier = _load_module("gamma_strict_contract_verifier", "verify_contracts.py")
    real_run = subprocess.run

    def strict_run(command, **kwargs):
        assert command[:5] == ["lake", "--no-build", "env", "lean", "-j2"]
        assert kwargs["env"]["LEAN_NUM_THREADS"] == "2"
        assert kwargs["env"]["MATHLIB_NO_CACHE_ON_UPDATE"] == "1"
        assert kwargs["timeout"] == 120
        return real_run([*command[:5], "-DwarningAsError=true", *command[5:]], **kwargs)

    verifier.subprocess = SimpleNamespace(run=strict_run, TimeoutExpired=subprocess.TimeoutExpired)
    return verifier.verify_compiled_contract_names(paths, package)


def _run_scope_lean(package, directory, source, *arguments):
    """Real isolated compile/probe, with the fixture path added inside Lake's env."""
    assert source.resolve().is_relative_to(directory.resolve())
    environment = os.environ.copy()
    environment.update(LEAN_NUM_THREADS="2", MATHLIB_NO_CACHE_ON_UPDATE="1")
    command = [
        "lake", "--no-build", "env", "bash", "-c",
        'export LEAN_PATH="$1${LEAN_PATH:+:$LEAN_PATH}"; shift; '
        'exec lean -j2 -DwarningAsError=true "$@"',
        "response-audit-fixture", str(directory), f"--root={directory}",
        *arguments, str(source),
    ]
    return subprocess.run(command, cwd=package, env=environment, text=True,
                          capture_output=True, timeout=120, check=False)


def _check_lean_source(package, tmp_path, text, stem):
    # No private-build search paths: these tests consume the selected canonical package.
    with TemporaryDirectory(prefix="gamma-probe-", dir=tmp_path) as temporary:
        directory = Path(temporary)
        source = directory / f"{stem}.lean"
        source.write_text(text)
        return _run_scope_lean(package, directory, source)


def test_gamma_real_final_endpoint(gamma_compiled_package):
    package = gamma_compiled_package
    assert _verify_strict([package / GAMMA_CONTRACT_NAME], package) == [GAMMA_PAIR]
    assert _verify_strict([package / name for name in sorted(GAMMA_ERA_CONTRACTS)], package) == EXPECTED_PAIRS


@pytest.mark.parametrize("mutation,diagnostic", [
    ("namespace", "Contract declaration is absent: InventedOMAI"),
    ("owner", "belongs to OMAIPhyslibThermalGruneisen, not OMAIPhyslibContinuum"),
])
def test_gamma_real_final_provenance_negatives(gamma_compiled_package, gamma_contract, tmp_path,
                                               mutation, diagnostic):
    contract = copy.deepcopy(gamma_contract)
    if mutation == "namespace":
        contract["operators"][0]["lean_definition"] = "InventedOMAI.Response.thermalGruneisenIdentity"
    else:
        contract["operators"][0]["definition_source_path"] = "lean/bridge/OMAIPhyslibContinuum.lean"
    with pytest.raises(ValueError, match=diagnostic):
        _verify_strict([_write_contract(tmp_path, contract)], gamma_compiled_package)


def test_gamma_real_witness_and_support_ownership(gamma_compiled_package, tmp_path):
    # Temporary name-provenance probes, not additional reviewed contracts or bindings.
    for source_path, names, module in (
        (WITNESS_SOURCE, sorted(GAMMA_WITNESS_THEOREMS), WITNESS_MODULE),
        (SUPPORT_SOURCE, sorted(SUPPORT_ROOTS), SUPPORT_MODULE),
    ):
        contract = {"source_path": source_path,
                    "nodes": [{"id": "gamma-name-probe", "lean_definition": name} for name in names]}
        pairs = _verify_strict([_write_contract(tmp_path, contract)], gamma_compiled_package)
        assert pairs == [{"name": name, "module": module} for name in names]


_CLOSURE_PROBE = """import OMAIPhyslibBridge
import Lean
open Lean Elab Command Meta

namespace OMAIGammaProbe

def kindOf : ConstantInfo → String
  | .defnInfo _ => "def"
  | .thmInfo _ => "thm"
  | .inductInfo _ => "induct"
  | .ctorInfo _ => "ctor"
  | .recInfo _ => "rec"
  | .axiomInfo _ => "axiom"
  | .opaqueInfo _ => "opaque"
  | .quotInfo _ => "quot"

/-- Bridge definitions expand through type and value, bridge theorems through
their statement only; foreign constants are recorded but never expanded. -/
def usedNames (info : ConstantInfo) : Array Name :=
  match info with
  | .defnInfo val => info.type.getUsedConstants ++ val.value.getUsedConstants
  | .opaqueInfo val => info.type.getUsedConstants ++ val.value.getUsedConstants
  | .inductInfo val => info.type.getUsedConstants ++ val.ctors.toArray
  | _ => info.type.getUsedConstants

def closure (env : Environment) (roots : List Name) : Array Name := Id.run do
  let mut seen : NameSet := {}
  let mut order : Array Name := #[]
  let mut stack := roots
  for _ in [0:1000000] do
    match stack with
    | [] => break
    | name :: rest =>
      stack := rest
      if seen.contains name then
        continue
      seen := seen.insert name
      order := order.push name
      if (__BRIDGE__).isPrefixOf name then
        if let some info := env.find? name then
          for used in usedNames info do
            if !seen.contains used then
              stack := used :: stack
  return order

end OMAIGammaProbe

open OMAI.PhyslibBridge OMAI.PhyslibBridge.Response Constants Temperature in
theorem OMAIGammaProbe.frozenEndpointShape (M : HarmonicVolumeModel) (p : ℝ) (T : Temperature)
    (B : StableBranchAt M.freeEnergy M.domain p (T : ℝ)) :
    M.weightedGruneisen T (B.volume (T : ℝ) / M.reference.avogadro) B.in_domain.2 =
      thermalGruneisenIdentity (expansion B.volume (T : ℝ))
        (bulk M.freeEnergy ((T : ℝ), B.volume (T : ℝ)))
        (harmonicVolumetricHeatCapacity
          (M.gridAt (B.volume (T : ℝ) / M.reference.avogadro) B.in_domain.2)
          (M.primitiveCellVolumeAt (B.volume (T : ℝ) / M.reference.avogadro) B.in_domain.2) T) :=
  harmonic_static_thermalGruneisen_eq_omai M p T B

run_cmd do
  let env := (← getEnv).setExporting false
  let roots : List Name := [__ROOTS__]
  let sentinels : List Name := [__SENTINELS__]
  for sentinel in sentinels do
    logInfo m!"OMAI_GAMMA_SENTINEL|{sentinel}|{if env.contains sentinel then "present" else "missing"}"
  for root in roots do
    let some info := env.find? root
      | throwError m!"Missing gamma support root: {root}"
    let owner := match env.getModuleIdxFor? root with
      | some index => toString (env.header.moduleNames[index.toNat]!)
      | none => "none"
    logInfo m!"OMAI_GAMMA_ROOT|{root}|{OMAIGammaProbe.kindOf info}|{owner}"
    for name in OMAIGammaProbe.closure env [root] do
      let kind := match env.find? name with
        | some found => OMAIGammaProbe.kindOf found
        | none => "missing"
      logInfo m!"OMAI_GAMMA_CLOSURE|{root}|{name}|{kind}"
  for name in OMAIGammaProbe.closure env [__CONTROL__] do
    logInfo m!"OMAI_GAMMA_CONTROL|{name}"
  let some actual := env.find? __THEOREM__
    | throwError "Missing frozen thermal Gruneisen endpoint theorem"
  let some frozen := env.find? __FROZEN__
    | throwError "Missing frozen statement probe"
  logInfo m!"OMAI_GAMMA_SHAPE|{if actual.type == frozen.type then "exact" else "differs"}"
  let heads ← liftTermElabM <| forallTelescope actual.type fun binders body => do
    let some (ty, lhs, rhs) := body.eq?
      | return s!"{binders.size}|not-an-equality"
    let arguments := rhs.getAppArgs.toList.map fun argument =>
      toString (argument.getAppFn.constName?.getD Name.anonymous)
    return s!"{binders.size}|{ty.constName?.getD Name.anonymous}|{lhs.getAppFn.constName?.getD Name.anonymous}|{rhs.getAppFn.constName?.getD Name.anonymous}|{String.intercalate "," arguments}"
  logInfo m!"OMAI_GAMMA_HEADS|{heads}"
  logInfo m!"OMAI_GAMMA_CLOSURE_OK|{roots.length}"
"""


def _closure_probe_source():
    """Deliberately non-module (like the axiom audit): reads full imported values."""
    names = lambda items: ", ".join(BACKTICK + name for name in items)  # noqa: E731
    return (_CLOSURE_PROBE
            .replace("__BRIDGE__", BACKTICK + "OMAI.PhyslibBridge")
            .replace("__ROOTS__", names(SUPPORT_ROOTS))
            .replace("__SENTINELS__", names(sorted(FORBIDDEN_EXACT | REQUIRED_IN_WEIGHTED | REQUIRED_IN_MODE)))
            .replace("__CONTROL__", BACKTICK + "OMAI.PhyslibBridge.Response.bulk")
            .replace("__THEOREM__", BACKTICK + GAMMA_THEOREM)
            .replace("__FROZEN__", BACKTICK + "OMAIGammaProbe.frozenEndpointShape"))


def test_gamma_real_anti_circularity_closure(gamma_compiled_package, tmp_path):
    result = _check_lean_source(gamma_compiled_package, tmp_path, _closure_probe_source(), "GammaClosureProbe")
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert re.findall(r"OMAI_GAMMA_CLOSURE_OK\|(\d+)", output) == [str(len(SUPPORT_ROOTS))]
    sentinels = dict(re.findall(r"OMAI_GAMMA_SENTINEL\|([^|\s]+)\|(present|missing)", output))
    expected_sentinels = FORBIDDEN_EXACT | REQUIRED_IN_WEIGHTED | REQUIRED_IN_MODE
    assert sentinels == {name: "present" for name in expected_sentinels}, "sentinel typo or missing constant"
    roots = {name: (kind, owner) for name, kind, owner
             in re.findall(r"OMAI_GAMMA_ROOT\|([^|\s]+)\|(\w+)\|([^|\s]+)", output)}
    assert roots == {name: ("def", SUPPORT_MODULE) for name in SUPPORT_ROOTS}
    closures = {}
    for root, name, kind in re.findall(r"OMAI_GAMMA_CLOSURE\|([^|\s]+)\|([^|\s]+)\|(\w+)", output):
        closures.setdefault(root, {})[name] = kind
    assert set(closures) == set(SUPPORT_ROOTS)
    for root in SUPPORT_ROOTS:
        reached = closures[root]
        forbidden = sorted(
            name for name, kind in reached.items()
            if name in FORBIDDEN_EXACT or name.startswith(FORBIDDEN_PREFIXES)
            or (name.startswith(RESPONSE_PREFIX) and kind != "thm"))
        assert not forbidden, (root, forbidden)
        bridge = {name for name, kind in reached.items()
                  if name.startswith("OMAI.PhyslibBridge.") and kind != "thm"}
        assert bridge <= ALLOWED_OMAI_CLOSURE, (root, sorted(bridge - ALLOWED_OMAI_CLOSURE))
    assert REQUIRED_IN_WEIGHTED <= closures["OMAI.PhyslibBridge.HarmonicVolumeModel.weightedGruneisen"].keys()
    assert REQUIRED_IN_MODE <= closures["OMAI.PhyslibBridge.HarmonicVolumeModel.modeGruneisen"].keys()
    # Positive control: the walker does see the response quantities it forbids.
    assert "OMAI.PhyslibBridge.Response.FVV" in re.findall(r"OMAI_GAMMA_CONTROL\|([^|\s]+)", output)
    assert re.findall(r"OMAI_GAMMA_SHAPE\|(\w+)", output) == ["exact"]
    assert re.findall(r"OMAI_GAMMA_HEADS\|(\S+)", output) == [EXPECTED_HEADS]


def _typed_gamma_consumer_source():
    """Public typed consumer of the frozen endpoint and witnesses (frozen signatures)."""
    return """module
import OMAIPhyslibBridge
set_option autoImplicit false
open OMAI.PhyslibBridge OMAI.PhyslibBridge.Response OMAI.PhyslibBridge.GruneisenWitness

example (alpha K Cvol : ℝ) : thermalGruneisenIdentity alpha K Cvol = alpha * K / Cvol := rfl

example (M : HarmonicVolumeModel) (p : ℝ) (T : Temperature)
    (B : StableBranchAt M.freeEnergy M.domain p (T : ℝ)) :
    M.weightedGruneisen T (B.volume (T : ℝ) / M.reference.avogadro) B.in_domain.2 =
      thermalGruneisenIdentity (expansion B.volume (T : ℝ))
        (bulk M.freeEnergy ((T : ℝ), B.volume (T : ℝ)))
        (harmonicVolumetricHeatCapacity
          (M.gridAt (B.volume (T : ℝ) / M.reference.avogadro) B.in_domain.2)
          (M.primitiveCellVolumeAt (B.volume (T : ℝ) / M.reference.avogadro) B.in_domain.2) T) :=
  harmonic_static_thermalGruneisen_eq_omai M p T B

example (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n) (q : Fin n) (b : Fin 3) (v : ℝ) :
    (rateModel positiveRates A hA n hn).modeGruneisen q b v = positiveRates b * v :=
  rate_modeGruneisen positiveRates A hA n hn q b v

example (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n) (q : Fin n) :
    Function.Injective fun b : Fin 3 => (rateModel positiveRates A hA n hn).modeGruneisen q b 1 :=
  positive_modeGruneisen_injective A hA n hn q

example : (2 : ℝ) ^ 2 * Real.exp 2 / (Real.exp 2 - 1) ^ 2 < 1 ^ 2 * Real.exp 1 / (Real.exp 1 - 1) ^ 2 :=
  einsteinWeight_two_lt_one

example : (3 : ℝ) ^ 2 * Real.exp 3 / (Real.exp 3 - 1) ^ 2 < 2 ^ 2 * Real.exp 2 / (Real.exp 2 - 1) ^ 2 :=
  einsteinWeight_three_lt_two

example (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n) :
    1 < (rateModel positiveRates A hA n hn).weightedGruneisen witnessTemperature 1
        (one_mem_J positiveRates A hA n hn) ∧
      (rateModel positiveRates A hA n hn).weightedGruneisen witnessTemperature 1
        (one_mem_J positiveRates A hA n hn) < 2 :=
  positive_weightedGruneisen_bounds A hA n hn

example (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n) :
    (rateModel negativeRates A hA n hn).weightedGruneisen witnessTemperature 1
      (one_mem_J negativeRates A hA n hn) < 0 :=
  negative_weightedGruneisen_neg A hA n hn

example (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n) :
    ∃ B : StableBranchAt (rateModel positiveRates A hA n hn).freeEnergy
        (rateModel positiveRates A hA n hn).domain 0 (witnessTemperature : ℝ),
      B.volume (witnessTemperature : ℝ) = A ∧
        1 < (rateModel positiveRates A hA n hn).weightedGruneisen witnessTemperature
          (B.volume (witnessTemperature : ℝ) / A) B.in_domain.2 ∧
        (rateModel positiveRates A hA n hn).weightedGruneisen witnessTemperature
          (B.volume (witnessTemperature : ℝ) / A) B.in_domain.2 < 2 ∧
        0 < expansion B.volume (witnessTemperature : ℝ) :=
  positive_gamma_witness A hA n hn

example (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n) :
    ∃ B : StableBranchAt (rateModel negativeRates A hA n hn).freeEnergy
        (rateModel negativeRates A hA n hn).domain 0 (witnessTemperature : ℝ),
      B.volume (witnessTemperature : ℝ) = A ∧
        (rateModel negativeRates A hA n hn).weightedGruneisen witnessTemperature
          (B.volume (witnessTemperature : ℝ) / A) B.in_domain.2 < 0 ∧
        expansion B.volume (witnessTemperature : ℝ) < 0 :=
  negative_gamma_witness A hA n hn

example (A : ℝ) (hA : 0 < A) :
    ∃ B : StableBranchAt (zeroModel A hA).freeEnergy (zeroModel A hA).domain 0 1,
      B.volume 1 = A ∧ expansion B.volume 1 = 0 ∧
        ∀ (T : Temperature) (v : ℝ) (hv : v ∈ (zeroModel A hA).J),
          (zeroModel A hA).weightedGruneisen T v hv = 0 :=
  zero_gamma_control A hA

example :
    ∃ B : StableBranchAt (rateModel positiveRates 3 (by norm_num) 2 (by norm_num)).freeEnergy
        (rateModel positiveRates 3 (by norm_num) 2 (by norm_num)).domain 0 (witnessTemperature : ℝ),
      B.volume (witnessTemperature : ℝ) = 3 ∧
        1 < (rateModel positiveRates 3 (by norm_num) 2 (by norm_num)).weightedGruneisen
          witnessTemperature (B.volume (witnessTemperature : ℝ) / 3) B.in_domain.2 ∧
        (rateModel positiveRates 3 (by norm_num) 2 (by norm_num)).weightedGruneisen
          witnessTemperature (B.volume (witnessTemperature : ℝ) / 3) B.in_domain.2 < 2 ∧
        0 < expansion B.volume (witnessTemperature : ℝ) :=
  positive_gamma_witness_nonunit
"""


def _typed_gamma_negative_source(case):
    header = ("module\nimport OMAIPhyslibBridge\nset_option autoImplicit false\n"
              "open OMAI.PhyslibBridge OMAI.PhyslibBridge.Response\n\n")
    extra = ""
    bulk = "bulk M.freeEnergy ((T : ℝ), B.volume (T : ℝ))"
    capacity = ("harmonicVolumetricHeatCapacity\n"
                "          (M.gridAt (B.volume (T : ℝ) / M.reference.avogadro) B.in_domain.2)\n"
                "          (M.primitiveCellVolumeAt (B.volume (T : ℝ) / M.reference.avogadro) B.in_domain.2) T")
    if case == "molar_capacity":
        capacity = "M.cv ((T : ℝ), B.volume (T : ℝ))"
    elif case == "fvv_bulk":
        bulk = "FVV M.freeEnergy ((T : ℝ), B.volume (T : ℝ))"
    elif case == "free_cell_volume":
        extra = " (Vc : PrimitiveCellVolume)"
        capacity = ("harmonicVolumetricHeatCapacity\n"
                    "          (M.gridAt (B.volume (T : ℝ) / M.reference.avogadro) B.in_domain.2) Vc T")
    else:
        raise AssertionError(case)
    return header + (
        "example (M : HarmonicVolumeModel) (p : ℝ) (T : Temperature)" + extra + "\n"
        "    (B : StableBranchAt M.freeEnergy M.domain p (T : ℝ)) :\n"
        "    M.weightedGruneisen T (B.volume (T : ℝ) / M.reference.avogadro) B.in_domain.2 =\n"
        "      thermalGruneisenIdentity (expansion B.volume (T : ℝ))\n"
        "        (" + bulk + ")\n"
        "        (" + capacity + ") :=\n"
        "  harmonic_static_thermalGruneisen_eq_omai M p T B\n")


def test_gamma_real_typed_endpoint_and_witnesses(gamma_compiled_package, tmp_path):
    result = _check_lean_source(gamma_compiled_package, tmp_path, _typed_gamma_consumer_source(),
                                "GammaTypedConsumer")
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("case", ["molar_capacity", "fvv_bulk", "free_cell_volume"])
def test_gamma_real_typed_basis_negatives(gamma_compiled_package, tmp_path, case):
    result = _check_lean_source(gamma_compiled_package, tmp_path, _typed_gamma_negative_source(case),
                                "GammaTypedNegative")
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "type mismatch" in output.lower(), output
    assert "harmonic_static_thermalGruneisen_eq_omai" in output, output
    assert not any(message in output.lower()
                   for message in ("unknown module", "unknown identifier", "unknown constant")), output
