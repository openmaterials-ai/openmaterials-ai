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

Each input carries the id it was pinned with; the generator RECOMPUTES the id
and refuses to write when the two disagree. A changed id is a defect in the
canonicalization, never a reason to regenerate.

Run: ``python -m omai.tools.gen_vectors``
"""

from __future__ import annotations

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

# The map version the render vectors are stamped against: the commons pin the
# kaldo fixture and MCG's worker tests already carry.
_MAP_VERSION = "9802d9e854c915eb47d867575730a556ab7f4a565e392bf5b29da58338f08434"


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
    return out


# The renderer inputs. Two producers are represented, because both exist:
#
# - The PLATFORM form (no run_ref): what the MCG worker serves. The ref is the
#   bare provider and the detail names no run, because a public share page
#   carries no run identity. `kappa_served_proof` is the Cut 1 proof record's
#   own result, and the vector asserts the rendered bytes equal the ones
#   stored for run_74cdf438f9e64a9bb90a.
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
    # The served proof record's own result: these exact bytes are stored for
    # run_74cdf438f9e64a9bb90a. std is 0 (single seed), so uncertainty is
    # absent and the detail prints "+/- None".
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


def generate() -> dict[str, str]:
    """The vector files as ``{filename: text}``, without writing anything."""
    inputs = json.loads(_INPUTS.read_text())
    return {
        "lineage_ids.json": _dump(build_lineage_ids(inputs)),
        "records.json": _dump(build_records(inputs)),
        "render.json": _dump(build_render()),
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
