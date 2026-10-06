"""Regenerate omai/vectors/*.json from the pinned inputs.

The vectors are the library's cross-language contract: mapengine and the MCG
worker reimplement the canonicalization in Python and TypeScript, and assert
their output against these files instead of against hand-copied constants.

Deterministic by construction: the inputs are the committed
``vector_inputs.json`` beside this script (no clock, no filesystem walk, no
network), and every id is computed by the live :mod:`omai.lineages` functions.
``tests/test_vectors.py`` regenerates and asserts byte equality with what is
committed, so a drift in the canonicalization fails the suite rather than
being silently rewritten.

The inputs were copied verbatim from the three places that already pin these
ids, never retyped:

- ``commons_conformance_targets``: the four commons conformance targets, as
  mapengine's ``adapters/tests/golden_targets.py`` holds them (themselves
  json-loaded from ``docs/data/conformance/*.json``).
- ``mcg_number_vectors``: the adversarial float/int canonicalization vectors
  from MCG's ``mcg/tests/tools/openmaterials/test_record.py`` and the identical
  set in ``platform/worker/test/record.spec.ts``.
- ``proof-record-903616ec.json``: the Cut 1 RunPod proof record as the platform
  served it, carrying the engine manifest's code rows under
  ``execution.registry``. A real served record, so the vectors describe the
  shape a producer emits and not only the shape this repository invents.
- ``kaldo-direct-bte-si.json``: the kaldo external-solve fixture, a byte copy
  of ``tests/fixtures/external_solve/kaldo-direct-bte-si.json`` kept beside
  this script so the generator runs from an installed wheel too.
  ``tests/test_vectors.py`` asserts the two copies are identical.
- ``configurations``: the committed Si configuration record's structure, the
  canonical JSON its uid hashes, and the uid. Python only: computing the
  canonical JSON needs spglib, so the generator checks the hash alone and
  ``tests/test_configurations.py`` recomputes it.
- ``release_codes``: frozen releases, fixture data: the registered releases of
  the representations the release-check cases name, as the registry held them
  when the cases were cut, copied into the vector beside them.

The private-evidence cases (``private.json``) and the fixture registry they
are checked against are defined in this file: shapes, not data.

Each input carries the id it was pinned with; the generator RECOMPUTES the id
and refuses to write when the two disagree. A changed id is a defect in the
canonicalization, never a reason to regenerate.

Run: ``python -m omai.tools.gen_vectors``
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from omai.lineages import canonical_id, lineage_id
from omai.render import (
    render_kappa,
    render_molar_cp,
    render_reaction_energy,
)

# Every input resolves relative to THIS FILE, never to a repository layout, so
# the generator runs the same from a checkout and from an installed wheel. The
# kaldo fixture is copied in beside vector_inputs.json and shipped as package
# data for exactly that reason: reading it out of tests/ would resolve under
# site-packages and fail on an installed copy.
_HERE = Path(__file__).resolve().parent
_INPUTS = _HERE / "vector_inputs.json"
_KALDO = _HERE / "kaldo-direct-bte-si.json"
# The Cut 1 RunPod proof record, exactly as the platform served it
# (run_74cdf438f9e64a9bb90a, study std_7eccab0fd6c44f699b4e). Real production
# bytes: the vector set now contains the shape a producer actually emits,
# which is what would have caught the 0.1.0 registry defect.
_PROOF_RECORD = _HERE / "proof-record-903616ec.json"
_VECTORS = _HERE.parent / "vectors"

# The lineage envelope MCG's number vectors vary: only conditions and params
# differ per vector, so the node pin stays constant and the number edges sit
# exactly where the hash reads them.
_MCG_NODE = "ThermalConductivity[transport_model=hnemd]"
_MCG_NODE_UID = "e7157a52da5eb7d2ae79e57692acc30d7e63a3a0d1c731b14da4d6ab8fd5eb88"
_MCG_MATERIAL = {"name": "Si"}

# An execution block for the "canonical_id with execution" half of every
# lineage vector. Identity is lineage-only, so this must never change an id;
# the vector records that, in the file, for every consumer to assert.
_PROBE_EXECUTION = {"code": "gpumd_hnemd", "wall_time_s": 4210.1234567,
                    "container_digest": "sha256:deadbeef"}

# The graph version the render vectors are stamped against: the commons pin the
# kaldo fixture and MCG's worker tests already carry. The vector key stays
# "map_version", the renderers' keyword.
_MAP_VERSION = "9802d9e854c915eb47d867575730a556ab7f4a565e392bf5b29da58338f08434"

# A lineage_version for the record carrying the 0.2.0 fields: the first one
# in docs/data/versions.json, whose graph half is _MAP_VERSION.
_LINEAGE_VERSION = "1a35c51f998fb466b899903b0f7e49a079d636395c281d359dcff1728fc294eb"


def _canonical_json(lineage: dict) -> str:
    """The exact bytes hashed to the lineage id.

    Recomputed through the same canonicalization the id uses, so a consumer can
    assert its own canonical JSON against this string before hashing.
    """
    from omai.lineages import _canonical_lineage

    return json.dumps(_canonical_lineage(lineage), sort_keys=True,
                      separators=(",", ":"))


def _lineage_vector(name: str, source: str, lineage: dict,
                    pinned_id: str | None) -> dict:
    """One lineage vector, with its id recomputed and checked against the pin."""
    computed = lineage_id(lineage)
    if pinned_id is not None and computed != pinned_id:
        raise SystemExit(
            f"{name}: identity drift. {source} pins {pinned_id}, "
            f"omai.lineages.lineage_id computes {computed}. The "
            f"canonicalization is wrong, never the pin: fix the code, do not "
            f"regenerate this vector.")
    return {
        "name": name,
        "source": source,
        "lineage": lineage,
        "canonical_json": _canonical_json(lineage),
        "lineage_id": computed,
        # Both canonical_id arities, so a consumer proves for itself that
        # execution and artifacts sit outside identity.
        "canonical_id": canonical_id(lineage),
        "canonical_id_with_execution": canonical_id(
            lineage, _PROBE_EXECUTION,
            [{"path": "results/kappa.json", "bytes": 16, "role": "report",
              "sha256": "2f0ed6b289619d8deeb5e1f5154d5fd64ee3609cf3581372"
                        "508d36a10ade6b39"}]),
    }


def build_lineage_ids(inputs: dict) -> list[dict]:
    """Every lineage vector, from all three pinned sources."""
    out: list[dict] = []
    for name, target in sorted(inputs["commons_conformance_targets"].items()):
        out.append(_lineage_vector(
            f"commons:{name.lower()}",
            "openmaterials commons conformance target "
            f"({target['source_file']})",
            target["lineage"], target["pinned_id"]))
    for vector in inputs["mcg_number_vectors"]:
        lineage = {"node": _MCG_NODE, "node_uid": _MCG_NODE_UID,
                   "material": dict(_MCG_MATERIAL),
                   "conditions": vector["conditions"],
                   "params": vector["params"]}
        out.append(_lineage_vector(
            f"mcg:{vector['label']}",
            "MCG test_record.py / worker record.spec.ts golden vector",
            lineage, vector["pinned_id"]))
    kaldo = json.loads(_KALDO.read_text())
    out.append(_lineage_vector(
        "kaldo:direct_bte_si",
        "omai tests/fixtures/external_solve/kaldo-direct-bte-si.json",
        kaldo["lineage"], kaldo["lineage_id"]))
    return out


def build_records(inputs: dict) -> list[dict]:
    """Full records with their ids, one per lineage vector.

    Each is the complete SimulationRecord a consumer validates against
    ``omai.schema``: the vector's lineage, an execution block, and, for the
    artifact-bearing case, a real pointer manifest and its mirrors. The id is
    the lineage id, which the artifacts and mirrors must not change.
    """
    vectors = build_lineage_ids(inputs)
    out: list[dict] = []
    for vector in vectors:
        record = {
            "id": vector["lineage_id"],
            "lineage": vector["lineage"],
            "execution": {"code": "gpumd_hnemd",
                          "code_version": "3.9.5",
                          "image_digest": "sha256:deadbeef",
                          # The engine manifest's code rows, the shape every
                          # real record carries. 0.1.0 put registry HOST
                          # strings here, which no producer emits.
                          "registry": [{
                              "id": "gpumd",
                              "name": "GPUMD",
                              "spdx": "GPL-3.0-or-later",
                              "license_source": "https://github.com/brucefan1983/GPUMD (LICENSE)",
                              "source": "https://github.com/brucefan1983/GPUMD",
                              "version": "3.9.5"}]},
            "artifacts": [],
            "mirrors": {},
            "results": [],
        }
        out.append({"name": vector["name"], "record": record})
    # One heavy record: artifacts and mirrors present, same lineage as the
    # lightweight Si vector, and therefore the SAME id. This is the vector that
    # proves location and payload sit outside identity.
    light = next(v for v in vectors if v["name"] == "mcg:safe_light")
    out.append({
        "name": "mcg:safe_light_with_artifacts",
        "record": {
            "id": light["lineage_id"],
            "lineage": light["lineage"],
            "execution": {"code": "gpumd_hnemd", "wall_time_s": 120.5},
            "artifacts": [
                {"path": "hnemd/kappa.out", "bytes": 5, "role": "series",
                 "sha256": "a04cf110bdbd4519399c9d622f423ce1e7e70701e0263f"
                           "59ccdb1884133678f3"},
                {"path": "results/kappa.json", "bytes": 16, "role": "report",
                 "sha256": "2f0ed6b289619d8deeb5e1f5154d5fd64ee3609cf35813"
                           "72508d36a10ade6b39"},
            ],
            "mirrors": {
                "hnemd/kappa.out": {
                    "url": "https://app.materialscodegraph.com/s/tok123/"
                           "artifact/hnemd/kappa.out",
                    "provider": "materialscodegraph"},
                "results/kappa.json": {
                    "url": "https://app.materialscodegraph.com/s/tok123/"
                           "artifact/results/kappa.json",
                    "provider": "materialscodegraph"},
            },
            "results": [{
                "variable": "ThermalConductivity[transport_model=hnemd]",
                "material": "Si",
                "conditions": {"T": "300 K", "method": "hnemd", "n_seeds": 4,
                               "code": "GPUMD"},
                "value": 137.5,
                "units": "W/(m K)",
                "uncertainty": 4.2,
                "simulation": light["lineage_id"],
                "source": {"kind": "simulation",
                           "ref": "materialscodegraph-run-ref-xyz",
                           "detail": "Bulk Si kappa from a MaterialsCodeGraph "
                                     "run."},
            }],
        },
    })
    # The Cut 1 proof record, verbatim production bytes. Its id must be the
    # lineage id like every other record; the generator checks that below, so
    # a copy that drifted from what was served cannot land silently.
    proof = json.loads(_PROOF_RECORD.read_text())
    computed = lineage_id(proof["lineage"])
    if computed != proof["id"]:
        raise SystemExit(
            f"proof record: stated id {proof['id']} but lineage_id computes "
            f"{computed}. The copy drifted from the served bytes; re-fetch it, "
            f"do not adjust the id.")
    out.append({"name": "mcg:cut1_proof_run_903616ec", "record": proof})
    # The 0.2.0 fields outside identity on the lightweight Si lineage: the
    # SAME id as mcg:safe_light. The listed uid is the one_file model fixture.
    out.append({
        "name": "omai:safe_light_with_unregistered_and_versions",
        "record": {
            "id": light["lineage_id"],
            "lineage": light["lineage"],
            "unregistered": [{"kind": "model", "uid": hashlib.sha256(
                b"fixture model A\n").hexdigest()}],
            "lineage_version": _LINEAGE_VERSION,
            "overlay_version": hashlib.sha256(b"fixture overlay\n").hexdigest(),
        },
    })
    return out


# The renderer inputs. Two producers are represented, because both exist:
#
# - The PLATFORM form (no run_ref): what the MCG worker serves. The ref is the
#   bare provider and the detail names no run, because a public share page
#   carries no run identity. `kappa_served_proof` is the Cut 1 proof record's
#   own result: every field equals the served one except source.detail, whose
#   text 0.2.0 changed (graph version wording, 4 significant figures).
# - The COMMONS form (with run_ref): what the committed instances under
#   docs/data/instances/ carry, e.g. "materialscodegraph-dgeba-cp300-gfn2".
#   The run refs below are the real committed ones, not invented labels.
#
# 0.1.0 shipped six cases in the commons form with INVENTED run refs
# ("run-ref-xyz"), rendered by MCG's Python renderer, which never served a
# record. Those bytes had no producer. The kappa cases are re-cut in the
# platform form (the worker is the only producer of a kappa instance); the
# molar-Cp and reaction-energy cases keep the commons form and now carry the
# run refs their committed instances actually use.
_RENDER_CASES = [
    # The served proof record's own result. std is 0 (single seed), so
    # uncertainty is absent and the detail writes no "+/-" term.
    {"name": "kappa_served_proof",
     "function": "render_kappa",
     "result": {"method": "bte_rta", "material_name": "Si",
                "temperature_K": 300, "n_seeds": 1, "code": "qe+d3q",
                "kappa_W_per_mK": 97.93078199999998,
                "kappa_std_W_per_mK": 0},
     "kwargs": {}},
    # A multi-seed run: a real spread, so uncertainty IS emitted.
    {"name": "kappa_hnemd_with_spread",
     "function": "render_kappa",
     "result": {"method": "hnemd", "material_name": "Si",
                "temperature_K": 300.0, "n_seeds": 4, "code": "GPUMD",
                "kappa_W_per_mK": 137.5, "kappa_std_W_per_mK": 4.2},
     "kwargs": {"potential": "Si-NEP"}},
    # A fractional temperature (the %g path) and a null std.
    {"name": "kappa_green_kubo_no_std",
     "function": "render_kappa",
     "result": {"method": "green_kubo", "material_name": "Si",
                "temperature_K": 301.5, "n_seeds": 1, "code": "ASE",
                "kappa_W_per_mK": 120.25, "kappa_std_W_per_mK": None},
     "kwargs": {}},
    {"name": "kappa_bte_direct_inverse",
     "function": "render_kappa",
     "result": {"method": "bte_direct_inverse", "material_name": "Si",
                "temperature_K": 300.0, "n_seeds": 1, "code": "kaldo",
                "kappa_W_per_mK": 254.46618271513248,
                "kappa_std_W_per_mK": None},
     "kwargs": {}},
    # 4 significant figures in plain decimal: 12345.6 -> "12350", and the
    # error 120.25 (an exact binary tie) rounds half up to "120.3".
    {"name": "kappa_sig4_plain_decimal_half_up",
     "function": "render_kappa",
     "result": {"method": "hnemd", "material_name": "Si",
                "temperature_K": 300.0, "n_seeds": 4, "code": "GPUMD",
                "kappa_W_per_mK": 12345.6, "kappa_std_W_per_mK": 120.25},
     "kwargs": {}},
    # 16.34999 -> "16.35", 0.41234567 -> "0.4123".
    {"name": "kappa_sig4_small_error",
     "function": "render_kappa",
     "result": {"method": "hnemd", "material_name": "Si",
                "temperature_K": 300.0, "n_seeds": 4, "code": "GPUMD",
                "kappa_W_per_mK": 16.34999, "kappa_std_W_per_mK": 0.41234567},
     "kwargs": {}},
    # The run-identified form, still available to callers that want it.
    {"name": "kappa_hnemd_with_run_ref",
     "function": "render_kappa",
     "result": {"method": "hnemd", "material_name": "Si",
                "temperature_K": 300.0, "n_seeds": 4, "code": "GPUMD",
                "kappa_W_per_mK": 137.5, "kappa_std_W_per_mK": 4.2},
     "kwargs": {"run_ref": "run_74cdf438f9e64a9bb90a"}},
    {"name": "molar_cp_dgeba",
     "function": "render_molar_cp",
     "result": {"molecule_name": "C21H24O4 (DGEBA)",
                "cp_temperatures_K": [200.0, 250.0, 300.0, 350.0],
                "cp_harmonic_J_per_molK": [301.2, 350.9, 397.7, 442.1],
                "n_imaginary": 0},
     "kwargs": {"run_ref": "dgeba-cp300-gfn2", "at_K": 300.0}},
    {"name": "reaction_energy_aniline",
     "function": "render_reaction_energy",
     "result": {"reaction_name": "glycidyl phenyl ether + aniline -> "
                                 "1-(phenylamino)-3-phenoxy-2-propanol",
                "dh298_kJ_per_mol": -106.3,
                "de_elec_kJ_per_mol": -98.4},
     "kwargs": {"run_ref": "cure-dh-gpe-aniline-gfn2",
                "material": "C9H10O2 (glycidyl phenyl ether)"}},
    {"name": "reaction_energy_methylamine",
     "function": "render_reaction_energy",
     "result": {"reaction_name": "glycidyl phenyl ether + methylamine -> "
                                 "1-(methylamino)-3-phenoxy-2-propanol",
                "dh298_kJ_per_mol": -116.1,
                "de_elec_kJ_per_mol": -107.9},
     "kwargs": {"run_ref": "cure-dh-gpe-methylamine-gfn2",
                "material": "C9H10O2 (glycidyl phenyl ether)"}},
]

_RENDERERS = {
    "render_kappa": render_kappa,
    "render_molar_cp": render_molar_cp,
    "render_reaction_energy": render_reaction_energy,
}


def build_render() -> list[dict]:
    """Renderer inputs and the instances they render to."""
    out = []
    for case in _RENDER_CASES:
        renderer = _RENDERERS[case["function"]]
        instance = renderer(case["result"], map_version=_MAP_VERSION,
                            **case["kwargs"])
        out.append({
            "name": case["name"],
            "function": case["function"],
            "result": case["result"],
            "kwargs": case["kwargs"],
            "map_version": _MAP_VERSION,
            "instance": instance.to_json_dict(),
            "filename": instance.filename(),
        })
    return out


# Model identity fixtures (omai.evidence.model_uid), with inline bytes so a
# consumer reproduces every digest. The NEP89 and Si.tersoff uids are pinned in
# their records under docs/data/models/ instead: the commons holds neither file.
_MODEL_CASES = [
    {"name": "one_file",
     "files": [("model.txt", "model", "fixture model A\n")]},
    {"name": "two_files",
     "files": [("model.snapcoeff", "model", "fixture coefficients\n"),
               ("model.snapparam", "model", "fixture parameters\n")]},
    # The same model file as one_file plus a companion outside the uid: the
    # uid must equal one_file's.
    {"name": "one_file_with_training_state",
     "files": [("model.txt", "model", "fixture model A\n"),
               ("model.restart", "training_state", "fixture training state\n")]},
]


def build_models() -> list[dict]:
    """Model uid vectors: files with inline content, their digests, the uid."""
    from omai.evidence import model_uid

    out = []
    for case in _MODEL_CASES:
        files = [{"path": path, "role": role, "content": content,
                  "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                  "bytes": len(content.encode("utf-8"))}
                 for path, role, content in case["files"]]
        digests = [f["sha256"] for f in files if f["role"] == "model"]
        vector = {"name": case["name"], "files": files, "uid": model_uid(digests)}
        if len(digests) > 1:
            # The exact bytes a several-file uid hashes.
            vector["manifest_json"] = json.dumps(
                {"files": sorted(digests)}, sort_keys=True, separators=(",", ":"))
        out.append(vector)
    return out


def build_configurations(inputs: dict) -> list[dict]:
    """Configuration uid vectors: a structure, its canonical JSON, its uid."""
    out = []
    for entry in inputs["configurations"]:
        uid = hashlib.sha256(entry["canonical_json"].encode("utf-8")).hexdigest()
        if uid != entry["pinned_uid"]:
            raise SystemExit(
                f"{entry['name']}: {entry['source_file']} pins "
                f"{entry['pinned_uid']}, its canonical JSON hashes to {uid}.")
        out.append({"name": entry["name"],
                    "source": entry["source_file"],
                    "structure": entry["structure"],
                    "canonical_json": entry["canonical_json"],
                    "canonical_uid": uid})
    return out


# Release-check report cases (omai.lineages.release_check): execution blocks
# whose registry rows the check reads, by id and version only.
_DIGEST = "sha256:" + "0" * 64
_RELEASE_CASES = [
    ("registered_version", {"registry": [{"id": "gpumd", "version": "3.9.5"}]}),
    ("registered_tag", {"registry": [{"id": "gpumd", "version": "v3.9.5"}]}),
    ("alias_of_a_representation",
     {"registry": [{"id": "quantum-espresso", "version": "qe-7.5"}]}),
    ("exact_string_only", {"registry": [
        {"id": "lammps", "version": "2025.7.22.4.0"},
        {"id": "lammps", "version": "2025.7.22"}]}),
    ("unregistered_version", {"registry": [{"id": "gpumd", "version": "v4.7"}]}),
    ("not_a_representation",
     {"registry": [{"id": "qe-d3q", "version": "q-e-7.5"}]}),
    ("no_version_with_image_digest",
     {"image_digest": _DIGEST, "registry": [{"id": "xtb", "version": None}]}),
    ("no_version_with_container_digest",
     {"container_digest": _DIGEST, "registry": [{"id": "xtb", "version": None}]}),
    ("no_version_without_digest", {"registry": [{"id": "xtb", "version": None}]}),
    ("no_version_for_a_code_with_releases",
     {"image_digest": _DIGEST, "registry": [{"id": "kaldo", "version": None}]}),
]


def build_releases(inputs: dict) -> dict:
    """Release-check cases with the frozen releases they are checked against."""
    from omai.lineages import release_check

    codes = inputs["release_codes"]
    cases = []
    for name, execution in _RELEASE_CASES:
        execution = {"code": "fixture", **execution}
        cases.append({"name": name, "execution": execution,
                      "unresolved": release_check(execution, codes)})
    return {"codes": codes, "cases": cases}


# Private-evidence cases (omai.evidence.private_reasons, mirrored by
# docs/assets/private-members.js): record shapes and the reasons each gives
# against a fixture registry. Uids are fixtures: 1 a registered model, 2 a
# model no registry holds, 3 a registered configuration, 4 its former uid,
# 5 a configuration no registry holds.
_M, _U, _C, _A, _V = ("1" * 64, "2" * 64, "3" * 64, "4" * 64, "5" * 64)
_PRIVATE_REGISTRY = {
    "citation_keys": {"Potential": ["potential_sha256", "base_potential_sha256"],
                      "SetVoltage": ["calibration_sha256"]},
    "configuration": {_C: "configurations/fixture.json",
                      _A: "configurations/fixture.json"},
    "model": {_M: "models/fixture.json"},
}


def _member(conditions=None, material=None, **top):
    lineage = {"node": "SetVoltage", "conditions": conditions or {"T_K": 300}}
    if material is not None:
        lineage["material"] = material
    return {"lineage": lineage, **top}


_PRIVATE_CASES = [
    ("public", _member()),
    ("unregistered_empty", _member(unregistered=[])),
    ("unregistered_null", _member(unregistered=None)),
    ("unregistered_string", _member(unregistered="")),
    ("unregistered_object", _member(unregistered={})),
    ("unregistered_model", _member(unregistered=[{"kind": "model", "uid": _U}])),
    ("unregistered_two_kinds", _member(unregistered=[
        {"kind": "configuration", "uid": _V}, {"kind": "model", "uid": _U}])),
    ("unregistered_malformed_entries", _member(unregistered=[
        {}, 1, {"kind": "overlay", "uid": _U}, {"kind": ["model"], "uid": _U}])),
    ("unregistered_listing_a_registered_uid",
     _member(unregistered=[{"kind": "model", "uid": _M}])),
    ("overlay_version_null", _member(overlay_version=None)),
    ("overlay_version_set", _member(overlay_version="6" * 64)),
    ("overlay_version_empty_string", _member(overlay_version="")),
    ("overlay_version_false", _member(overlay_version=False)),
    ("potential_registered", _member({"potential_sha256": _M})),
    ("potential_unregistered", _member({"potential_sha256": _U})),
    ("base_potential_unregistered",
     _member({"potential_sha256": _M, "base_potential_sha256": _U})),
    ("calibration_unregistered", _member({"calibration_sha256": _U})),
    ("calibration_listed", _member({"calibration_sha256": _U},
                                   unregistered=[{"kind": "model", "uid": _U}])),
    ("potential_prefixed", _member({"potential_sha256": "sha256:" + _M})),
    ("potential_null", _member({"potential_sha256": None})),
    ("potential_number", _member({"potential_sha256": 7})),
    ("potential_object_key", _member({"potential_sha256": "__proto__"})),
    ("not_a_citation_key", _member({"model_sha256": _U})),
    ("configuration_registered", _member(material={"name": "Si", "configuration": _C})),
    ("configuration_prefixed",
     _member(material={"name": "Si", "configuration": "sha256:" + _C})),
    ("configuration_former_uid", _member(material={"name": "Si", "configuration": _A})),
    ("configuration_unregistered",
     _member(material={"name": "Si", "configuration": _V})),
    ("configuration_null", _member(material={"name": "Si", "configuration": None})),
    ("material_name_only", _member(material="Si")),
    ("legacy_recipe", {"recipe": {"conditions": {"potential_sha256": _U}}}),
    ("conditions_not_an_object",
     {"lineage": {"conditions": ["potential_sha256"]}}),
    ("member_not_an_object", "x"),
]


def build_private() -> dict:
    """Private-evidence cases with the fixture registry they read."""
    from omai.evidence import private_reasons

    return {"registry": _PRIVATE_REGISTRY,
            "cases": [{"name": name, "member": member,
                       "reasons": private_reasons(member, _PRIVATE_REGISTRY)}
                      for name, member in _PRIVATE_CASES]}


def generate() -> dict[str, str]:
    """The vector files as ``{filename: text}``, without writing anything."""
    inputs = json.loads(_INPUTS.read_text())
    return {
        "lineage_ids.json": _dump(build_lineage_ids(inputs)),
        "records.json": _dump(build_records(inputs)),
        "render.json": _dump(build_render()),
        "configurations.json": _dump(build_configurations(inputs)),
        "models.json": _dump(build_models()),
        "releases.json": _dump(build_releases(inputs)),
        "private.json": _dump(build_private()),
    }


def _dump(payload) -> str:
    """One vector file's bytes: indented, key-sorted, newline-terminated."""
    return json.dumps(payload, indent=1, sort_keys=True,
                      ensure_ascii=True) + "\n"


def main() -> None:
    _VECTORS.mkdir(parents=True, exist_ok=True)
    for name, text in generate().items():
        (_VECTORS / name).write_text(text)
        print(f"wrote omai/vectors/{name} ({len(text)} bytes)")


if __name__ == "__main__":
    main()
