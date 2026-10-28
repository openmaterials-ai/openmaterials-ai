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
)

# The one frozen global coverage ledger of the published bindings.
GLOBAL_COVERAGE = {
    "nodes_total": 129, "nodes_mapped": 30, "operators_total": 127, "operators_mapped": 20,
    "nodes_local": 3, "operators_local": 5, "bindings_total": 29, "source_correspondences": 5,
    "compiled_bridges": 24, "nodes_compiled": 18, "nodes_compiled_outputs": 17,
    "nodes_compiled_interpretations": 1, "operators_compiled": 20, "operators_compiled_local": 5,
    "nodes_compiled_local": 4, "operators_proved": 25, "nodes_proved": 22,
    "upstream_declarations_referenced": 33, "upstream_modules_referenced": 9,
    "relations": {"exact_definition": 1, "conditional": 23, "conceptual": 4, "local": 1},
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
