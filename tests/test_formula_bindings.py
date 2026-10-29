"""Check formula mappings against catalog IDs, pinned sources, and build records."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import jsonschema
import pytest

from omai.formula_bindings import (
    build_formula_bindings,
    catalog_inventory,
    compiled_targets,
    formula_bindings_for,
    formula_bindings_for_physlib,
    physlib_declaration_index,
    validate_formula_bindings,
    verify_source_references,
    verify_compiled_source_names,
)
from omai.map_data import DOMAINS, build_graph_dict
from omai.operator.identity import edge_id, formula_fingerprint, node_id
from omai.semantics import build_semantics, physlib_for, resolve

_ROOT = Path(__file__).resolve().parents[1]
_PACKAGE = _ROOT / "omai/data/formula_bindings.json"
_SITE = _ROOT / "docs/data/formula_bindings.json"


@pytest.fixture(scope="module")
def payload():
    return build_formula_bindings()


@pytest.fixture
def one_binding():
    """Synthetic conditional source row for validator mutation tests."""
    conventions = {key: "Not applicable to this scalar test fixture." for key in (
        "model_scope", "component_scope", "normalization_basis", "frequency_convention",
        "unit_embedding", "held_fixed", "admissibility", "reference_energy", "qpoint_weighting",
    )}
    seeds = {
        "schema_version": 1,
        "upstream": {
            "repository": "https://github.com/leanprover-community/physlib",
            "revision": "8ddcc004043c5b537e4225fa763121c176b62a4a",
            "lean_toolchain": "leanprover/lean4:v4.35.0",
        },
        "bindings": [{
            "id": "scalar-power-factor-test",
            "targets": [{"kind": "node", "id": "PowerFactor"},
                        {"kind": "operator", "id": "contract_power_factor"}],
            "relation": "conditional",
            "statement": "Scalar PF = sigma * S^2 under the same operating point.",
            "sources": [{"module": "Physlib.CondensedMatter.Thermoelectric.Basic",
                         "name": "CondensedMatter.ThermoelectricMaterial.powerFactor",
                         "kind": "def", "line": 125}],
            "conditions": ["Identify scalar fields at the same operating point."],
            "conventions": conventions,
            "remaining_obligations": ["Compile a model-specific field interpretation."],
            "evidence": {"kind": "source_correspondence"},
        }],
        "gap_reasons": {"domains": {}, "nodes": {}, "operators": {}},
    }
    inventory = catalog_inventory()
    lookup = {(kind, row["id"]): row for kind, key in (("node", "nodes"), ("operator", "operators"))
              for row in inventory[key]}
    for target in seeds["bindings"][0]["targets"]:
        row = lookup[(target["kind"], target["id"])]
        target["uid"] = row["uid"]
        if target["kind"] == "operator":
            target["formula_sha256"] = row["formula_sha256"]
    return build_formula_bindings(seeds)


def test_complete_inventory_uses_actual_domains_not_graph_links(payload):
    nodes = {row["id"]: row for row in payload["inventory"]["nodes"]}
    operators = {row["id"]: row for row in payload["inventory"]["operators"]}
    graph = build_graph_dict(DOMAINS)
    assert {name: row["uid"] for name, row in nodes.items()} == {
        row["id"]: row["uid"] for row in graph["nodes"]}
    actual = {op.name: op for domain in DOMAINS for op in domain.edges}
    assert len(nodes) == 136
    assert len(operators) == 133
    assert set(operators) == set(actual)
    for name, op in actual.items():
        assert operators[name]["uid"] == edge_id(op, node_id)
        assert operators[name]["formula_sha256"] == hashlib.sha256(
            formula_fingerprint(op.formula).encode()).hexdigest()
    assert "contract_molar_volume" in operators
    assert "provide_temperature" in operators
    assert "provide_CellVolume" not in operators
    assert all(row["reason"] for row in operators.values())
    assert all(row["reason"] for row in nodes.values())


def test_generated_package_and_site_match_and_are_deterministic(payload):
    expected = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    assert _PACKAGE.read_text() == expected
    assert _SITE.read_text() == expected
    assert build_formula_bindings() == payload
    validate_formula_bindings(payload, check_catalog=True, proof_root=_ROOT)


def test_packaged_lookup_is_independent_of_working_directory_and_caller_mutation(payload, tmp_path, monkeypatch):
    binding = payload["bindings"][0]
    target = binding["targets"][0]
    monkeypatch.chdir(tmp_path)
    rows = formula_bindings_for(target["id"], kind=target["kind"])
    assert binding in rows
    rows[0]["statement"] = "caller mutation"
    assert all(row["statement"] != "caller mutation" for row in formula_bindings_for(target["id"]))
    assert formula_bindings_for("NoSuchNode") == []
    with pytest.raises(ValueError, match="kind"):
        formula_bindings_for(target["id"], kind="execution")


def test_reverse_lookup_matches_exact_names_modules_and_returns_full_records(payload, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    declarations = physlib_declaration_index()
    assert len(declarations) == payload["coverage"]["upstream_declarations_referenced"]
    for source in declarations:
        expected = [binding for binding in payload["bindings"]
                    if any(s["name"] == source["name"] and s["module"] == source["module"]
                           for s in binding["sources"])]
        actual = formula_bindings_for_physlib(declaration=source["name"], module=source["module"])
        assert actual == expected
        assert source["binding_ids"] == sorted(binding["id"] for binding in expected)
        assert all(binding["conditions"] or binding["relation"] != "conditional" for binding in actual)
        assert len({binding["id"] for binding in actual}) == len(actual)
    module = declarations[0]["module"]
    expected = [binding for binding in payload["bindings"]
                if any(source["module"] == module for source in binding["sources"])]
    assert formula_bindings_for_physlib(module=module) == expected
    assert formula_bindings_for_physlib(module=module + ".Missing") == []
    assert formula_bindings_for_physlib(declaration=declarations[0]["name"].split(".")[-1]) == []
    assert formula_bindings_for_physlib(declaration=declarations[0]["name"], module="Physlib.Other") == []
    changed = formula_bindings_for_physlib(module=module)
    changed[0]["conditions"].append("caller mutation")
    assert all("caller mutation" not in row["conditions"] for row in formula_bindings_for_physlib(module=module))
    with pytest.raises(ValueError, match="declaration or module"):
        formula_bindings_for_physlib()


def test_reverse_index_deduplicates_references_and_rejects_conflicting_source_metadata(one_binding):
    other = copy.deepcopy(one_binding["bindings"][0])
    other["id"] = "another-reference"
    one_binding["bindings"].append(other)
    rows = physlib_declaration_index(one_binding)
    assert len(rows) == 1
    assert rows[0]["binding_ids"] == ["another-reference", "scalar-power-factor-test"]
    other["sources"][0]["line"] += 1
    with pytest.raises(ValueError, match="inconsistent metadata"):
        physlib_declaration_index(one_binding)


def test_compiled_subjects_exclude_input_associations(payload):
    total = next(binding for binding in payload["bindings"]
                 if binding["id"] == "thermoelectric-total-conductivity")
    proved = compiled_targets(total, payload["inventory"])
    lattice_input = {"kind": "node", "id": "ThermalConductivity[bte_solver=direct_inverse]"}
    assert any(target["id"] == lattice_input["id"] for target in total["targets"])
    assert lattice_input not in proved
    assert all(target in [{"kind": t["kind"], "id": t["id"]} for t in total["targets"]]
               for target in proved)
    assert any(target["kind"] == "operator" for target in proved)
    anchored = {(target["kind"], target["id"]) for binding in payload["bindings"]
                if binding["relation"] != "local"
                for target in compiled_targets(binding, payload["inventory"])}
    subjects = {(target["kind"], target["id"]) for binding in payload["bindings"]
                for target in compiled_targets(binding, payload["inventory"])}
    assert payload["coverage"]["nodes_compiled"] == sum(kind == "node" for kind, _ in anchored)
    assert payload["coverage"]["operators_compiled"] == sum(kind == "operator" for kind, _ in anchored)
    assert payload["coverage"]["nodes_proved"] == sum(kind == "node" for kind, _ in subjects)
    assert payload["coverage"]["operators_proved"] == sum(kind == "operator" for kind, _ in subjects)


def test_second_compiled_proof_does_not_inflate_unique_coverage():
    """A stronger model proof can add evidence without adding catalog subjects."""
    seeds = json.loads((_ROOT / "omai/data/physlib_formula_seeds.json").read_text())
    before = build_formula_bindings(seeds)
    additional = copy.deepcopy(next(row for row in seeds["bindings"]
                                    if row["id"] == "harmonic-molar-heat-capacity"))
    additional["id"] = "duplicate-compiled-scope-test"
    seeds["bindings"].append(additional)
    after = build_formula_bindings(seeds)
    assert after["coverage"]["compiled_bridges"] == before["coverage"]["compiled_bridges"] + 1
    assert after["coverage"]["bindings_total"] == before["coverage"]["bindings_total"] + 1
    for key in ("nodes_compiled", "nodes_compiled_outputs", "nodes_compiled_interpretations",
                "operators_compiled", "nodes_mapped", "operators_mapped",
                "upstream_declarations_referenced", "upstream_modules_referenced"):
        assert after["coverage"][key] == before["coverage"][key], key
    row = next(op for op in after["inventory"]["operators"]
               if op["id"] == "contract_molar_heat_capacity")
    assert "duplicate-compiled-scope-test" in row["binding_ids"]
    validate_formula_bindings(after, check_catalog=True)


def test_resolver_enrichment_preserves_legacy_and_operator_uids(payload):
    graph = build_graph_dict(DOMAINS)
    semantics = build_semantics(graph)
    node_hit = next(row for row in resolve("Temperature", semantics) if row["id"] == "Temperature")
    assert node_hit["physlib"] == physlib_for("Temperature")
    link_uids = {link["op"]: link["uid"] for link in graph["links"] if link.get("kind") != "param"}
    for row in semantics:
        if row["kind"] == "edge" and row["id"] in link_uids:
            assert row["uid"] == link_uids[row["id"]]
    hits = resolve("contract_power_factor", semantics)
    hit = next(row for row in hits if row["id"] == "contract_power_factor")
    assert hit["formal_bindings"] == formula_bindings_for("contract_power_factor", kind="operator")
    assert hit["score"] == 0.9
    assert hit["why"] == "exact label"
    assert "physlib" not in hit


@pytest.mark.parametrize("mutation,match", [
    (lambda p: p["bindings"].append(copy.deepcopy(p["bindings"][0])), "duplicate binding ID"),
    (lambda p: p["bindings"][0]["targets"][0].update(uid="0" * 64), "stale target UID"),
    (lambda p: p["bindings"][0].update(conditions=[]), "requires explicit conditions"),
    (lambda p: p["bindings"][0].update(remaining_obligations=[]), "remaining bridge obligations"),
    (lambda p: p["bindings"][0]["sources"][0].update(source_url="https://example.com"), "pinned upstream"),
    (lambda p: p["coverage"].update(compiled_bridges=5), "coverage counts"),
])
def test_invalid_claims_are_rejected(one_binding, mutation, match):
    mutation(one_binding)
    with pytest.raises(ValueError, match=match):
        validate_formula_bindings(one_binding)


def test_unrecognized_proof_flags_are_rejected(one_binding):
    one_binding["bindings"][0]["evidence"]["verified"] = True
    with pytest.raises(jsonschema.ValidationError):
        validate_formula_bindings(one_binding)


def test_self_consistent_but_stale_inventory_fails_live_catalog_check(one_binding):
    target = next(target for target in one_binding["bindings"][0]["targets"] if target["kind"] == "operator")
    target["formula_sha256"] = "0" * 64
    row = next(row for row in one_binding["inventory"]["operators"] if row["id"] == target["id"])
    row["formula_sha256"] = "0" * 64
    validate_formula_bindings(one_binding)
    with pytest.raises(ValueError, match="stale live catalog"):
        validate_formula_bindings(one_binding, check_catalog=True)


def test_generator_refuses_to_reapprove_a_changed_live_formula(one_binding, monkeypatch):
    live = catalog_inventory()
    target = next(row for row in live["operators"] if row["id"] == "contract_power_factor")
    target["formula_sha256"] = "0" * 64
    monkeypatch.setattr("omai.formula_bindings.catalog_inventory", lambda: live)
    with pytest.raises(ValueError, match="reviewed formula fingerprint missing or stale"):
        build_formula_bindings(one_binding)


def test_generator_requires_reviewed_identity_pins(one_binding):
    del one_binding["bindings"][0]["targets"][0]["uid"]
    with pytest.raises(ValueError, match="reviewed target UID missing or stale"):
        build_formula_bindings(one_binding)


def test_compiled_evidence_requires_exact_source_and_successful_build(one_binding, tmp_path):
    source = tmp_path / "lean/bridge/Test.lean"
    source.parent.mkdir(parents=True)
    source.write_text("namespace Test\ntheorem example : True := True.intro\nend Test\n")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    binding = one_binding["bindings"][0]
    binding["evidence"] = {
        "kind": "compiled_bridge", "module": "Test", "declarations": ["Test.example"],
        "source_path": "lean/bridge/Test.lean", "source_sha256": digest,
        "build_record": "lean/bridge/build-evidence.json",
    }
    one_binding["coverage"]["compiled_bridges"] = 1
    one_binding["coverage"]["source_correspondences"] = 0
    one_binding["coverage"]["nodes_compiled"] = 1
    one_binding["coverage"]["nodes_compiled_outputs"] = 1
    one_binding["coverage"]["operators_compiled"] = 1
    one_binding["coverage"]["operators_proved"] = 1
    one_binding["coverage"]["nodes_proved"] = 1
    record = source.parent / "build-evidence.json"
    revision = one_binding["upstream"]["revision"]
    (source.parent / "lean-toolchain").write_text(one_binding["upstream"]["lean_toolchain"])
    (source.parent / "lakefile.toml").write_text('name = "Test"\n')
    (source.parent / "lake-manifest.json").write_text(json.dumps({
        "packages": [{"name": "physlib", "rev": revision}],
    }))
    (source.parent / "semantic-formula-contract.json").write_text("{}\n")
    for filename in ("audit.py", "verify_contracts.py"):
        (source.parent / filename).write_text("# synthetic audit dependency fixture")
    hashes = {str(path.relative_to(tmp_path)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in source.parent.iterdir() if path.is_file()}
    successful = {
        "status": "passed", "command": "lake build --wfail",
        "upstream_revision": revision,
        "lean_toolchain": one_binding["upstream"]["lean_toolchain"],
        "sources": hashes, "dependencies": {"physlib": revision},
        "contract_name_audit": {"status": "passed", "pairs": [], "pair_count": 0},
        "axiom_audit": {"status": "passed", "theorem_count": 1, "declaration_count": 1,
                        "allowed_axioms": ["propext", "Classical.choice", "Quot.sound"],
                        "declarations": {"Test.example": []}},
    }
    record.write_text(json.dumps(successful))
    validate_formula_bindings(one_binding, proof_root=tmp_path)
    missing_names = copy.deepcopy(successful)
    del missing_names["contract_name_audit"]
    record.write_text(json.dumps(missing_names))
    with pytest.raises(ValueError, match="contract name/module audit"):
        validate_formula_bindings(one_binding, proof_root=tmp_path)
    wrong_names = copy.deepcopy(successful)
    wrong_names["contract_name_audit"]["pairs"] = [{"name": "Forged.name", "module": "Test"}]
    record.write_text(json.dumps(wrong_names))
    with pytest.raises(ValueError, match="contract name/module audit"):
        validate_formula_bindings(one_binding, proof_root=tmp_path)
    record.write_text(json.dumps(successful))
    source.write_text(source.read_text() + "-- unverified edit\n")
    with pytest.raises(ValueError, match="source hash mismatch"):
        validate_formula_bindings(one_binding, proof_root=tmp_path)
    source.write_text("namespace Test\ntheorem example : True := True.intro\nend Test\n")
    stale = json.loads(record.read_text())
    stale["upstream_revision"] = "0" * 40
    record.write_text(json.dumps(stale))
    with pytest.raises(ValueError, match="matching successful bridge build"):
        validate_formula_bindings(one_binding, proof_root=tmp_path)
    record.write_text(json.dumps(successful))
    (source.parent / "lakefile.toml").write_text('name = "Changed"\n')
    with pytest.raises(ValueError, match="dependency hash mismatch"):
        validate_formula_bindings(one_binding, proof_root=tmp_path)
    (source.parent / "lakefile.toml").write_text('name = "Test"\n')
    failed_audit = copy.deepcopy(successful)
    failed_audit["axiom_audit"]["declarations"]["Test.example"] = ["sorryAx"]
    record.write_text(json.dumps(failed_audit))
    with pytest.raises(ValueError, match="approved-axiom audit"):
        validate_formula_bindings(one_binding, proof_root=tmp_path)
    del failed_audit["axiom_audit"]
    record.write_text(json.dumps(failed_audit))
    with pytest.raises(ValueError, match="approved-axiom audit"):
        validate_formula_bindings(one_binding, proof_root=tmp_path)


def test_source_audit_rejects_wrong_revision_and_shifted_declaration(one_binding, tmp_path, monkeypatch):
    source = one_binding["bindings"][0]["sources"][0]
    path = tmp_path / (source["module"].replace(".", "/") + ".lean")
    path.parent.mkdir(parents=True)
    path.write_text("\n" * 124 + "noncomputable def powerFactor : Real := 0\n")
    def git_result(args, **kwargs):
        output = ""
        if "rev-parse" in args:
            output = one_binding["upstream"]["revision"] + "\n"
        if "ls-tree" in args:
            output = str(path.relative_to(tmp_path)) + "\n"
        return SimpleNamespace(stdout=output)
    monkeypatch.setattr("omai.formula_bindings.subprocess.run", git_result)
    verify_source_references(one_binding, tmp_path)
    path.write_text("\n" + path.read_text())
    with pytest.raises(ValueError, match="declaration/line mismatch"):
        verify_source_references(one_binding, tmp_path)
    monkeypatch.setattr("omai.formula_bindings.subprocess.run", lambda *a, **k: SimpleNamespace(stdout="0" * 40))
    with pytest.raises(ValueError, match="clone revision"):
        verify_source_references(one_binding, tmp_path)


def test_current_source_references(payload):
    path = os.environ.get("PHYSLIB_BRIDGE_PATH")
    if not path:
        pytest.skip("PHYSLIB_BRIDGE_PATH not set to the pinned current Physlib source")
    verify_source_references(payload, Path(path))


def test_compiled_source_names_and_modules(payload):
    package = os.environ.get("PHYSLIB_BRIDGE_PACKAGE")
    if not package:
        pytest.skip("PHYSLIB_BRIDGE_PACKAGE not set to the pinned Lean package")
    verify_compiled_source_names(payload, Path(package))


def test_compiled_source_audit_rejects_nonexistent_namespace(payload):
    package = os.environ.get("PHYSLIB_BRIDGE_PACKAGE")
    if not package:
        pytest.skip("PHYSLIB_BRIDGE_PACKAGE not set to the pinned Lean package")
    mutated = copy.deepcopy(payload)
    source = mutated["bindings"][0]["sources"][0]
    source["name"] = "NonexistentReviewNamespace." + source["name"].rsplit(".", 1)[-1]
    # The source file and leaf-name line still match; the compiled name must not.
    verify_source_references(mutated, Path(package) / ".lake/packages/physlib")
    with pytest.raises(ValueError, match="Source declaration is absent"):
        verify_compiled_source_names(mutated, Path(package))


def test_compiled_source_audit_rejects_wrong_defining_module(payload, monkeypatch):
    package = os.environ.get("PHYSLIB_BRIDGE_PACKAGE")
    if not package:
        pytest.skip("PHYSLIB_BRIDGE_PACKAGE not set to the pinned Lean package")
    mutated = copy.deepcopy(payload)
    source = next(source for binding in mutated["bindings"] for source in binding["sources"]
                  if source["name"] == "Temperature")
    source["module"] = "Physlib.CondensedMatter.Thermoelectric.Basic"
    # Isolate the compiled ownership check from the earlier file/line check.
    monkeypatch.setattr("omai.formula_bindings.verify_source_references", lambda *_: None)
    with pytest.raises(ValueError, match="belongs to .* not"):
        verify_compiled_source_names(mutated, Path(package))


def test_retained_schema_v1_coverage_remains_readable(one_binding):
    original_fields = {"nodes_total", "nodes_mapped", "operators_total", "operators_mapped",
                       "bindings_total", "source_correspondences", "compiled_bridges", "relations"}
    one_binding["coverage"] = {key: value for key, value in one_binding["coverage"].items()
                               if key in original_fields}
    validate_formula_bindings(one_binding)
    one_binding["coverage"]["operators_compiled"] = 1
    one_binding["coverage"]["operators_proved"] = 1
    one_binding["coverage"]["nodes_proved"] = 1
    with pytest.raises(ValueError, match="coverage counts"):
        validate_formula_bindings(one_binding)
