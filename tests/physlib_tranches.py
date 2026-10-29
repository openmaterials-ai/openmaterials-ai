"""Reviewed proof tranches of the Lean bridge that landed after the thermal Gruneisen tranche.

Each tranche test pins its own scope exactly. The global ledgers (required contracts,
contract-name pairs, proof subjects, binding ids, module order and coverage) change with
every later tranche, so they are kept here once: a new tranche appends one entry and
updates ``GLOBAL_COVERAGE`` instead of editing every earlier test. Entries are frozen
review pins, in landing order.
"""
from __future__ import annotations

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
        "pairs": tuple({"name": "OMAI.PhyslibBridge.Response." + name, "module": "OMAIPhyslibQHA"} for name in (
            "qhaBulkModulus", "qhaGibbsEnergy", "qhaHeatCapacityP", "qhaThermalExpansion",
            "qhaThermalGruneisen")),
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
        "pairs": tuple({"name": "OMAI.PhyslibBridge.Elasticity." + name, "module": "OMAIElasticity"} for name in (
            "eosBulk", "poissonRatio", "voigtBulk", "voigtShear", "youngsModulus")),
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
        "pairs": tuple(
            [{"name": "OMAI.PhyslibBridge.Composites." + name, "module": "OMAICompositeConductivity"}
             for name in ("depolarization", "hasselmanJohnson", "nanAligned", "nanRandom")]
            + [{"name": "OMAI.PhyslibBridge.CureKinetics." + name, "module": "OMAICureKinetics"}
               for name in ("diBenedetto", "kamalCureTime")]),
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
        "pairs": (
            {"name": "OMAI.PhyslibBridge.Lattice.DispersionRelation", "module": "OMAIPhyslibLatticeDynamics"},
            {"name": "OMAI.PhyslibBridge.Lattice.ForceConstants.dynamicalMatrix",
             "module": "OMAIPhyslibLatticeDynamics"},
            {"name": "OMAI.PhyslibBridge.Lattice.catalogGroupVelocity", "module": "OMAIPhyslibGroupVelocity"},
            {"name": "OMAI.PhyslibBridge.Lattice.modeContractedKappa", "module": "OMAIPhyslibKappaContraction"},
            {"name": "OMAI.PhyslibBridge.Lattice.participationRatio", "module": "OMAIPhyslibParticipationRatio"}),
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
        "pairs": tuple(
            [{"name": "OMAI.PhyslibBridge.DeviceMetrology." + name, "module": "OMAIDeviceMetrology"}
             for name in ("deviceConductance", "driftConductance", "programmingError", "pulseEnergy",
                          "rampSetVoltage", "retentionTime", "thermionicConductance")]
            + [{"name": "OMAI.PhyslibBridge.MaterialsTransport." + name, "module": "OMAIMaterialsTransport"}
               for name in ("arrheniusDiffusivity", "ionicConductivity")]),
        "modules": ("OMAIDeviceMetrology", "OMAIMaterialsTransport"),
    },
)

# The one frozen global coverage ledger of the published bindings.
GLOBAL_COVERAGE = {
    "nodes_total": 136, "nodes_mapped": 33, "operators_total": 133, "operators_mapped": 24,
    "nodes_local": 16, "operators_local": 21, "bindings_total": 38, "source_correspondences": 5,
    "compiled_bridges": 33, "nodes_compiled": 21, "nodes_compiled_outputs": 20,
    "nodes_compiled_interpretations": 1, "operators_compiled": 24,
    "operators_compiled_local": 21, "nodes_compiled_local": 17, "operators_proved": 45,
    "nodes_proved": 38, "upstream_declarations_referenced": 36,
    "upstream_modules_referenced": 10,
    "relations": {"exact_definition": 1, "conditional": 27, "conceptual": 4, "local": 6},
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
