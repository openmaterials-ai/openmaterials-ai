"""Reviewed proof tranches of the Lean bridge that landed after the thermal Gruneisen tranche.

Each tranche test pins its own scope exactly. The global ledgers (required contracts,
proof subjects, binding ids, module order and coverage) change with every later tranche,
so they are kept here once: a new tranche appends one entry and updates
``GLOBAL_COVERAGE`` instead of editing every earlier test. Entries are frozen review
pins, in landing order. The contract-name pairs are read from each tranche's contract
files, which declare them (issue 188, item 9); each tranche's own test file still pins
its reviewed names literally.
"""
from __future__ import annotations

import json
from pathlib import Path

from omai.formula_bindings import catalog_inventory

_INVENTORY = catalog_inventory()

TRANCHES = (
    {
        "name": "qha",
        "contracts": ("qha-formula-contract.json",),
        "bindings": frozenset({
            "harmonic-qha-bulk-modulus", "harmonic-qha-gibbs-energy", "harmonic-qha-heat-capacity-p",
            "harmonic-qha-thermal-expansion", "harmonic-qha-thermal-gruneisen-contraction"}),
        "subjects": frozenset({
            ("node", "HeatCapacityConstantP"), ("node", "QHAGibbsEnergy"), ("node", "ThermalExpansion"),
            ("node", "ThermalGruneisen"), ("operator", "compute_bulk_modulus_qha"),
            ("operator", "compute_heat_capacity_p"), ("operator", "compute_qha_gibbs"),
            ("operator", "compute_thermal_expansion"), ("operator", "contract_thermal_gruneisen")}),
        "modules": ("OMAIPhyslibGibbsBranch", "OMAIPhyslibQHA", "OMAIPhyslibQHAWitness"),
    },
    {
        "name": "elasticity",
        "contracts": ("elasticity-formula-contract.json",),
        "bindings": frozenset({"linear-elasticity-voigt-moduli"}),
        "subjects": frozenset({
            ("node", "BulkModulus"), ("node", "PoissonRatio"), ("node", "ShearModulus"),
            ("node", "YoungsModulus"), ("operator", "compute_bulk_modulus_eos"),
            ("operator", "contract_bulk_modulus"), ("operator", "contract_poisson_ratio"),
            ("operator", "contract_shear_modulus"), ("operator", "contract_youngs_modulus")}),
        "modules": ("OMAIElasticity",),
    },
    {
        "name": "composites-cure",
        "contracts": ("composites-formula-contract.json", "cure-kinetics-formula-contract.json"),
        "bindings": frozenset({"composite-effective-medium", "thermoset-cure-kinetics"}),
        "subjects": frozenset({
            ("node", "CureConversion"), ("node", "DepolarizationFactor"),
            ("node", "GlassTransitionTemperature"),
            ("node", "ThermalConductivity[effective_medium=nan,orientation=aligned]"),
            ("node", "ThermalConductivity[effective_medium=nan,orientation=random]"),
            ("operator", "depolarization_factors"), ("operator", "dibenedetto_glass_transition"),
            ("operator", "hasselman_johnson"), ("operator", "kamal_cure_conversion"),
            ("operator", "nan_effective_kappa"), ("operator", "nan_effective_kappa_aligned")}),
        "modules": ("OMAICompositeConductivity", "OMAICureKinetics"),
    },
    {
        "name": "phonon",
        "contracts": ("phonon-structure-formula-contract.json",),
        "bindings": frozenset({
            "canonical-rta-thermal-conductivity", "crystal-dynamical-matrix", "crystal-group-velocity",
            "crystal-phonon-dispersion", "participation-ratio-bounds"}),
        "subjects": frozenset({
            ("node", "BareDynamicalMatrix"), ("node", "GroupVelocity"), ("node", "ParticipationRatio"),
            ("node", "ThermalConductivity[bte_solver=rta]"), ("operator", "compute_dispersion"),
            ("operator", "compute_dynamical_matrix"), ("operator", "compute_group_velocity"),
            ("operator", "compute_participation_ratio"), ("operator", "contract_kappa[bte_solver=rta]")}),
        "modules": ("OMAIPhyslibLatticeDynamics", "OMAIPhyslibPhononDispersion", "OMAIPhyslibGroupVelocity",
                    "OMAIPhyslibLatticeWitness", "OMAIPhyslibKappaContraction", "OMAIPhyslibRTAConductivity",
                    "OMAIPhyslibParticipationRatio"),
    },
    {
        "name": "devices-materials",
        "contracts": ("device-metrology-formula-contract.json", "materials-transport-formula-contract.json"),
        "bindings": frozenset({"analog-device-metrology", "arrhenius-ionic-transport"}),
        "subjects": frozenset({
            ("node", "ActivationEnergy"), ("node", "ConductanceState"), ("node", "DotProductError"),
            ("node", "ElectricalConductivity[carrier=ionic]"), ("node", "ProgrammingPulseEnergy"),
            ("node", "RetentionTime"), ("node", "SetVoltage"),
            ("operator", "apply_conductance_drift"), ("operator", "compute_ionic_conductivity"),
            ("operator", "contract_device_conductance"), ("operator", "dissipate_pulse_energy"),
            ("operator", "emit_thermionic_conductance"), ("operator", "fit_arrhenius"),
            ("operator", "propagate_programming_error"), ("operator", "ramp_set_voltage"),
            ("operator", "zero_bias_retention")}),
        "modules": ("OMAIDeviceMetrology", "OMAIMaterialsTransport"),
    },
    {
        "name": "thermochem-stability",
        "contracts": ("stability-formula-contract.json", "thermochemistry-formula-contract.json"),
        "bindings": frozenset({"dft-stability-energy-differences", "calphad-binary-equilibrium"}),
        "subjects": frozenset({
            ("node", "AdsorptionEnergy"), ("node", "EnergyAboveHull"), ("node", "GrainBoundaryEnergy"),
            ("node", "SurfaceEnergy"), ("node", "Voltage"),
            ("operator", "compute_adsorption_energy"), ("operator", "compute_energy_above_hull"),
            ("operator", "compute_grain_boundary_energy"), ("operator", "compute_intercalation_voltage"),
            ("operator", "compute_surface_energy"), ("operator", "compute_reaction_energy"),
            ("node", "ReactionEnergy"),
            ("node", "CalphadMolarEntropy"), ("node", "ChemicalPotential"), ("node", "MolarEnthalpy"),
            ("node", "MolarGibbsEnergy"), ("node", "PhaseFraction"), ("node", "TransitionTemperature"),
            ("operator", "compute_calphad_entropy"), ("operator", "compute_chemical_potentials"),
            ("operator", "compute_molar_enthalpy"), ("operator", "compute_phase_fractions"),
            ("operator", "compute_transition_temperature"), ("operator", "solve_equilibrium")}),
        "modules": ("OMAIStabilityEnergies", "OMAICalphad"),
    },
    {
        "name": "atomistic-derivatives",
        "contracts": ("dft-derivatives-formula-contract.json", "force-constants-formula-contract.json",
                      "elastic-constants-formula-contract.json", "molecular-modes-formula-contract.json"),
        "bindings": frozenset({
            "cell-stress-rotation-balance", "finite-displacement-force-constants",
            "force-constant-sum-rules", "hellmann-feynman-force-balance",
            "hyperelastic-elastic-constants", "molecular-normal-modes"}),
        "subjects": frozenset({
            ("node", "ElasticConstants"), ("node", "ForceConstants[order=2]"),
            ("node", "ForceConstants[order=3]"), ("node", "Forces"), ("node", "MolecularFrequency"),
            ("node", "Stress"), ("operator", "compute_elastic_constants"),
            ("operator", "compute_fc2_finite_displacement"), ("operator", "compute_force_constants[order=2]"),
            ("operator", "compute_force_constants[order=3]"), ("operator", "compute_forces_hf"),
            ("operator", "compute_molecular_frequencies"), ("operator", "compute_stress_cell")}),
        "modules": ("OMAIAtomisticDerivatives", "OMAICellElasticity", "OMAIMolecularModes"),
    },
    {
        "name": "electronic-transport",
        "contracts": ("electronic-transport-formula-contract.json", "carrier-statistics-formula-contract.json",
                      "static-dielectric-formula-contract.json"),
        "bindings": frozenset({"boltzmann-electronic-transport", "electronic-carrier-statistics",
                               "static-dielectric-ionic-response"}),
        "subjects": frozenset({
            ("node", "CarrierMobility"), ("node", "ElectricalConductivity[carrier=electronic]"),
            ("node", "ElectronicDOS"), ("node", "ElectronicThermalConductivity"), ("node", "SeebeckCoefficient"),
            ("node", "StaticDielectricTensor"),
            ("operator", "compute_carrier_mobility"), ("operator", "compute_electronic_conductivity"),
            ("operator", "compute_electronic_dos"), ("operator", "compute_electronic_thermal_conductivity"),
            ("operator", "compute_seebeck"), ("operator", "compute_static_dielectric")}),
        "modules": ("OMAISommerfeldTransport", "OMAIPhyslibElectronicTransport", "OMAIElectronicStatistics",
                    "OMAIStaticDielectric"),
    },
    {
        "name": "md-phonon-spectrum",
        "contracts": ("md-correlations-formula-contract.json", "vacf-spectrum-formula-contract.json",
                      "phonon-spectrum-formula-contract.json"),
        "bindings": frozenset({"md-correlation-estimators", "vacf-spectrum-lorentzian-limit",
                               "crystal-dos-landauer-conductance"}),
        "subjects": frozenset({
            ("node", "HeatCurrentACF"), ("node", "MeanSquaredDisplacement"), ("node", "PhononDOS"),
            ("node", "ThermalConductance[transport_model=landauer]"),
            ("node", "ThermalConductivity[transport_model=green_kubo]"), ("node", "VelocityAutocorrelation"),
            ("operator", "autocorrelate_heat_current"), ("operator", "compute_conductance[transport_model=landauer]"),
            ("operator", "compute_dos"), ("operator", "compute_msd"),
            ("operator", "compute_velocity_autocorrelation"),
            ("operator", "contract_kappa[transport_model=green_kubo]"), ("operator", "fourier_to_dos")}),
        "modules": ("OMAIMDCorrelations", "OMAIVACFSpectrum", "OMAIPhyslibPhononSpectrum"),
    },
)

# The one frozen global coverage ledger of the published bindings; the totals come from the
# live inventory.
_BRIDGE = Path(__file__).resolve().parent.parent / "lean" / "bridge"


def _contract_pairs(contracts: tuple[str, ...]) -> tuple[dict, ...]:
    """The (lean_definition, module) pairs the tranche's contract files declare.

    A missing contract file contributes no pairs instead of aborting import:
    the owning tranche's own tests report the absence ("integration pending"),
    and the contract-name audit comparison fails on the shortfall.
    """
    pairs = set()
    for name in contracts:
        if not (_BRIDGE / name).is_file():
            continue
        contract = json.loads((_BRIDGE / name).read_text())
        for endpoint in [*contract.get("operators", []), *contract.get("nodes", [])]:
            if "lean_definition" in endpoint:
                source = endpoint.get("definition_source_path", contract["source_path"])
                module = ".".join(Path(source).relative_to("lean/bridge").with_suffix("").parts)
                pairs.add((endpoint["lean_definition"], module))
    return tuple({"name": name, "module": module} for name, module in sorted(pairs))


for _tranche in TRANCHES:
    _tranche["pairs"] = _contract_pairs(_tranche["contracts"])

GLOBAL_COVERAGE = {
    "nodes_total": len(_INVENTORY["nodes"]), "nodes_mapped": 35,
    "operators_total": len(_INVENTORY["operators"]), "operators_mapped": 29,
    "nodes_local": 38, "operators_local": 48, "bindings_total": 52, "source_correspondences": 5,
    "compiled_bridges": 47, "nodes_compiled": 26, "nodes_compiled_outputs": 25,
    "nodes_compiled_interpretations": 1, "operators_compiled": 29, "operators_compiled_local": 48,
    "nodes_compiled_local": 42, "operators_proved": 77, "nodes_proved": 68,
    "upstream_declarations_referenced": 36, "upstream_modules_referenced": 10,
    "relations": {"exact_definition": 1, "conditional": 29, "conceptual": 4, "local": 18},
}


def _after(name: str | None) -> tuple[dict, ...]:
    names = [tranche["name"] for tranche in TRANCHES]
    return TRANCHES if name is None else TRANCHES[names.index(name) + 1:]


def contracts_after(name: str | None = None) -> frozenset[str]:
    return frozenset(c for tranche in _after(name) for c in tranche["contracts"])


def bindings_after(name: str | None = None) -> frozenset[str]:
    return frozenset().union(*(tranche["bindings"] for tranche in _after(name)))


def subjects_after(name: str | None = None) -> frozenset[tuple[str, str]]:
    return frozenset().union(*(tranche["subjects"] for tranche in _after(name)))


def pairs_after(name: str | None = None) -> list[dict]:
    return [dict(pair) for tranche in _after(name) for pair in tranche["pairs"]]


def modules_after(name: str | None = None) -> list[str]:
    return [module for tranche in _after(name) for module in tranche["modules"]]
