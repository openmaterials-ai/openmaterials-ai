"""Checks an installed wheel, run outside the source tree (the CI job `wheel`;
pytest does not collect it): with no docs/data/ beside the package, the
registry the wheel ships resolves the committed Si configuration uid and its
former uid, and the binding model check refuses an unlisted private uid on
both writers, a SetVoltage calibration included. The wheel ships the site's
private-evidence predicate, docs/assets/private-members.js, byte for byte."""
import json
import tempfile
from importlib import resources
from pathlib import Path

import omai.evidence as ev
from omai.lineages import LineageError, record_light, record_simulation, unregistered_for

SI = "7b5e77b1062f0997037cb9fd490d9edb8fce8099c4f700db334aa8afb8af22be"
SI_FORMER = "55bf22ca81868867402ac4ce50a830f91da84c805990c37c3bdafe3b93a69143"
TERSOFF = "52a93e90596829c57d54eef091de6215f1fac7ca15d57eac7568ddfdda26adfb"
PRIVATE = "2" * 64

assert "site-packages" in ev.__file__, ev.__file__
assert ev.default_roots() == [ev.REGISTRY], ev.default_roots()
for pin in (SI, SI_FORMER, "sha256:" + SI):
    record_light(lineage={"template": "kaldo", "conditions": {"potential_sha256": TERSOFF},
                          "material": {"name": "Si", "configuration": pin}})
private = {"template": "kaldo", "conditions": {"potential_sha256": PRIVATE}}
try:
    record_light(lineage=private)
except LineageError:
    pass
else:
    raise SystemExit("an unlisted private model uid was accepted")
record = record_light(lineage=private, unregistered=[{"kind": "model", "uid": PRIVATE}])
assert ev.private_reasons(record) == [
    {"field": "unregistered", "kind": "model"},
    {"field": "conditions.potential_sha256", "kind": "model"}]
assert json.loads(ev.REGISTRY.read_text())["citation_keys"]["SetVoltage"] == ["calibration_sha256"]
predicate = resources.files("omai").joinpath("data", "private-members.js")
site = Path(__file__).resolve().parents[1] / "docs" / "assets" / "private-members.js"
assert predicate.read_bytes() == site.read_bytes(), predicate
print("installed wheel ok:", ev.REGISTRY)

# The strict writer, on the live map the wheel builds: a SetVoltage record
# citing a calibration no registry holds is refused unless it is listed.
calibration = {"node": "SetVoltage", "material": {"name": "fixture"},
               "conditions": {"calibration_sha256": PRIVATE}}
artifacts = [{"path": "r.json", "bytes": 1, "sha256": "a" * 64, "role": "result"}]
with tempfile.TemporaryDirectory() as sim_dir:
    try:
        record_simulation(lineage=calibration, execution={"code": "fixture"},
                          artifacts=artifacts, sim_dir=sim_dir)
    except LineageError as exc:
        assert "never registered" in str(exc), exc
    else:
        raise SystemExit("an unlisted calibration was accepted")
    declared = unregistered_for(calibration)
    assert declared == [{"kind": "model", "uid": PRIVATE}], declared
    path = record_simulation(lineage=calibration, execution={"code": "fixture"},
                             artifacts=artifacts, sim_dir=sim_dir, unregistered=declared)
    assert json.loads(open(path).read())["unregistered"] == declared
print("installed wheel ok: record_simulation")

# Current formula correspondences are package resources: they must not
# disappear when the source checkout's docs/data directory is absent.
from omai.formula_bindings import (
    formula_bindings_for, formula_bindings_for_physlib, physlib_declaration_index,
)

formula_rows = formula_bindings_for("PowerFactor", kind="node")
assert formula_rows, "installed wheel lost its reviewed formula bridge"
assert all(row["evidence"]["kind"] in ("source_correspondence", "compiled_bridge")
           for row in formula_rows)
assert formula_bindings_for("contract_power_factor", kind="operator")
source = formula_rows[0]["sources"][0]
reverse_rows = formula_bindings_for_physlib(declaration=source["name"], module=source["module"])
assert formula_rows[0] in reverse_rows
assert any(row["name"] == source["name"] for row in physlib_declaration_index())
print("installed wheel ok: bidirectional formula bridge resources")

cp_rows = formula_bindings_for("contract_heat_capacity_p_identity", kind="operator")
assert len(cp_rows) == 1 and cp_rows[0]["id"] == "harmonic-static-cp-identity"
assert cp_rows[0]["evidence"]["kind"] == "compiled_bridge"
assert {(row["kind"], row["id"]) for row in cp_rows[0]["evidence"]["proved_targets"]} == {
    ("operator", "contract_heat_capacity_p_identity"), ("node", "HeatCapacityConstantP"),
}
assert cp_rows[0] in formula_bindings_for_physlib(
    declaration="CanonicalEnsemble.meanEnergyT",
    module="Physlib.StatisticalMechanics.CanonicalEnsemble.Lemmas",
)
assert all(row["id"] != "harmonic-static-cp-identity"
           for row in formula_bindings_for("compute_heat_capacity_p", kind="operator"))
print("installed wheel ok: conditional Cp identity, not its numerical sibling")

gamma_rows = formula_bindings_for("contract_thermal_gruneisen_identity", kind="operator")
assert len(gamma_rows) == 1 and gamma_rows[0]["id"] == "harmonic-static-thermal-gruneisen-identity"
assert gamma_rows[0]["evidence"]["kind"] == "compiled_bridge"
assert {(row["kind"], row["id"]) for row in gamma_rows[0]["evidence"]["proved_targets"]} == {
    ("operator", "contract_thermal_gruneisen_identity"), ("node", "ThermalGruneisen"),
}
for declaration, module in (
    ("CanonicalEnsemble.helmholtzFreeEnergy", "Physlib.StatisticalMechanics.CanonicalEnsemble.Basic"),
    ("CanonicalEnsemble.meanEnergy", "Physlib.StatisticalMechanics.CanonicalEnsemble.Basic"),
    ("CanonicalEnsemble.meanEnergyT", "Physlib.StatisticalMechanics.CanonicalEnsemble.Lemmas"),
    ("CanonicalEnsemble.heatCapacity", "Physlib.StatisticalMechanics.CanonicalEnsemble.Lemmas"),
):
    assert gamma_rows[0] in formula_bindings_for_physlib(declaration=declaration, module=module)
for sibling in ("compute_gruneisen", "contract_molar_volume"):
    assert formula_bindings_for(sibling, kind="operator") == []
assert all(row["id"] != "harmonic-static-thermal-gruneisen-identity"
           for row in formula_bindings_for("contract_thermal_gruneisen", kind="operator"))
assert formula_bindings_for("Gruneisen", kind="node") == []
print("installed wheel ok: thermal Gruneisen identity, not its siblings")

qha_expected = {
    "compute_qha_gibbs": ("harmonic-qha-gibbs-energy", "QHAGibbsEnergy"),
    "compute_heat_capacity_p": ("harmonic-qha-heat-capacity-p", "HeatCapacityConstantP"),
    "compute_thermal_expansion": ("harmonic-qha-thermal-expansion", "ThermalExpansion"),
    "compute_bulk_modulus_qha": ("harmonic-qha-bulk-modulus", None),
    "contract_thermal_gruneisen": ("harmonic-qha-thermal-gruneisen-contraction", "ThermalGruneisen"),
}
for operator, (binding_id, output) in qha_expected.items():
    qha_rows = formula_bindings_for(operator, kind="operator")
    assert [row["id"] for row in qha_rows] == [binding_id], operator
    assert qha_rows[0]["evidence"]["kind"] == "compiled_bridge"
    assert qha_rows[0]["evidence"]["module"] == "OMAIPhyslibQHA"
    expected_subjects = {("operator", operator)} | ({("node", output)} if output else set())
    assert {(row["kind"], row["id"]) for row in qha_rows[0]["evidence"]["proved_targets"]} == expected_subjects
    assert qha_rows[0] in formula_bindings_for_physlib(
        declaration="CanonicalEnsemble.helmholtzFreeEnergy",
        module="Physlib.StatisticalMechanics.CanonicalEnsemble.Basic",
    )
print("installed wheel ok: local quasiharmonic producers, not mode-Gruneisen producers")

lattice = {
    "compute_dynamical_matrix": ("crystal-dynamical-matrix", "conditional"),
    "compute_dispersion": ("crystal-phonon-dispersion", "conditional"),
    "compute_group_velocity": ("crystal-group-velocity", "conditional"),
    "contract_kappa[bte_solver=rta]": ("canonical-rta-thermal-conductivity", "conditional"),
    "compute_participation_ratio": ("participation-ratio-bounds", "local"),
}
for operator, (binding_id, relation) in lattice.items():
    rows = formula_bindings_for(operator, kind="operator")
    assert [row["id"] for row in rows] == [binding_id], operator
    assert rows[0]["relation"] == relation and rows[0]["evidence"]["kind"] == "compiled_bridge"
    assert (relation == "local") == (rows[0]["sources"] == [])
crystal_rows = formula_bindings_for_physlib(
    declaration="Physlib.CondensedMatter.Crystal", module="Physlib.CondensedMatter.Crystal.Basic")
assert {"crystal-dynamical-matrix", "crystal-phonon-dispersion", "crystal-group-velocity"} <= {
    row["id"] for row in crystal_rows}
for unbound in ("apply_nac_correction", "solve_bte[bte_solver=direct_inverse]",
                "contract_kappa[bte_solver=direct_inverse]", "contract_cumulative_kappa[wrt=omega]",
                "contract_cumulative_kappa[wrt=mfp]", "identity_dm", "sum_linewidths",
                "solve_bte[bte_solver=rta]"):
    assert formula_bindings_for(unbound, kind="operator") == []
print("installed wheel ok: lattice dynamics on Physlib crystals, catalog transport defects unbound")
