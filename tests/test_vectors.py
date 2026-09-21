"""The shipped golden vectors are what the library actually produces.

Two properties, both non-negotiable:

1. The committed files equal a fresh generation, byte for byte. A change in the
   canonicalization, the renderers or the generator shows up here instead of
   silently reshaping the contract mapengine and the MCG worker assert against.
2. Every vector reproduces through the PUBLIC functions (``lineage_id``,
   ``canonical_id``, the renderers), not through generator internals. A vector
   nobody can reproduce from the public API is not a contract.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from omai.lineages import canonical_id, lineage_id
from omai.render import (
    render_kappa,
    render_molar_cp,
    render_reaction_energy,
)
from omai.tools import gen_vectors

VECTORS = Path(gen_vectors.__file__).resolve().parent.parent / "vectors"

RENDERERS = {
    "render_kappa": render_kappa,
    "render_molar_cp": render_molar_cp,
    "render_reaction_energy": render_reaction_energy,
}


def _load(name: str):
    return json.loads((VECTORS / name).read_text())


LINEAGE_VECTORS = _load("lineage_ids.json")
RECORD_VECTORS = _load("records.json")
RENDER_VECTORS = _load("render.json")


# --- 1. the committed files equal a fresh generation ------------------------

@pytest.mark.parametrize("name", ["lineage_ids.json", "records.json",
                                  "render.json"])
def test_committed_vectors_equal_a_fresh_generation(name):
    fresh = gen_vectors.generate()[name]
    committed = (VECTORS / name).read_text()
    assert committed == fresh, (
        f"omai/vectors/{name} is stale or the generation drifted. Regenerate "
        f"with `python -m omai.tools.gen_vectors` ONLY after confirming no id "
        f"changed; a changed id is a defect in the canonicalization.")


def test_generation_is_deterministic():
    # Two runs in one process must agree: no clock, no set iteration order, no
    # filesystem walk leaking into the bytes.
    assert gen_vectors.generate() == gen_vectors.generate()


# --- 2. every vector reproduces through the public functions ----------------

@pytest.mark.parametrize("vector", LINEAGE_VECTORS,
                         ids=[v["name"] for v in LINEAGE_VECTORS])
def test_lineage_vector_reproduces_through_the_public_functions(vector):
    assert lineage_id(vector["lineage"]) == vector["lineage_id"]
    assert canonical_id(vector["lineage"]) == vector["canonical_id"]
    # Identity is the lineage alone: the same id with an execution block and a
    # manifest attached.
    assert vector["canonical_id_with_execution"] == vector["lineage_id"]


@pytest.mark.parametrize("vector", LINEAGE_VECTORS,
                         ids=[v["name"] for v in LINEAGE_VECTORS])
def test_canonical_json_is_the_bytes_that_hash_to_the_id(vector):
    import hashlib

    digest = hashlib.sha256(vector["canonical_json"].encode("utf-8")).hexdigest()
    assert digest == vector["lineage_id"]


@pytest.mark.parametrize("entry", RECORD_VECTORS,
                         ids=[e["name"] for e in RECORD_VECTORS])
def test_record_vector_id_is_its_lineage_id(entry):
    record = entry["record"]
    assert record["id"] == lineage_id(record["lineage"])


def test_artifacts_and_mirrors_do_not_change_the_record_id():
    heavy = next(e for e in RECORD_VECTORS
                 if e["name"] == "mcg:safe_light_with_artifacts")["record"]
    light = next(e for e in RECORD_VECTORS
                 if e["name"] == "mcg:safe_light")["record"]
    assert heavy["artifacts"] and heavy["mirrors"], "expected the heavy vector"
    assert heavy["id"] == light["id"]


@pytest.mark.parametrize("vector", RENDER_VECTORS,
                         ids=[v["name"] for v in RENDER_VECTORS])
def test_render_vector_reproduces_through_the_public_renderer(vector):
    renderer = RENDERERS[vector["function"]]
    instance = renderer(vector["result"], map_version=vector["map_version"],
                        **vector["kwargs"])
    assert instance.to_json_dict() == vector["instance"]
    assert instance.filename() == vector["filename"]


# --- the vector set is the one the consumers need ---------------------------

def test_the_packaged_kaldo_fixture_equals_the_test_fixture():
    # gen_vectors reads its own copy so it runs from an installed wheel. The
    # two must stay byte-identical, or the vectors are generated from an input
    # nobody else sees.
    packaged = Path(gen_vectors.__file__).resolve().parent / "kaldo-direct-bte-si.json"
    original = (Path(gen_vectors.__file__).resolve().parents[2] / "tests" /
                "fixtures" / "external_solve" / "kaldo-direct-bte-si.json")
    assert packaged.read_bytes() == original.read_bytes()


def test_the_generator_reads_only_files_beside_itself():
    # The property that makes `python -m omai.tools.gen_vectors` work from an
    # installed wheel: every input path sits in the package, never in the
    # repository layout around it.
    here = Path(gen_vectors.__file__).resolve().parent
    for path in (gen_vectors._INPUTS, gen_vectors._KALDO):
        assert path.parent == here, f"{path} is outside the package"
        assert path.exists()


def test_all_three_pinned_sources_are_represented():
    sources = {v["name"].split(":", 1)[0] for v in LINEAGE_VECTORS}
    assert sources == {"commons", "mcg", "kaldo"}
    # The four commons conformance targets, every MCG number vector, the kaldo
    # fixture. A shrinking vector set is a weakening contract.
    counts = {s: sum(1 for v in LINEAGE_VECTORS
                     if v["name"].startswith(s + ":")) for s in sources}
    assert counts == {"commons": 4, "mcg": 27, "kaldo": 1}
