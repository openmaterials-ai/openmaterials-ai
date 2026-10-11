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

import hashlib
import json
from pathlib import Path

import pytest

from omai.lineages import canonical_id, lineage_id
from omai.render import (
    render_composite_kappa,
    render_cure_conversion,
    render_glass_transition,
    render_interface_conductance,
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
    "render_composite_kappa": render_composite_kappa,
    "render_interface_conductance": render_interface_conductance,
    "render_cure_conversion": render_cure_conversion,
    "render_glass_transition": render_glass_transition,
}


def _load(name: str):
    return json.loads((VECTORS / name).read_text())


LINEAGE_VECTORS = _load("lineage_ids.json")
RECORD_VECTORS = _load("records.json")
RENDER_VECTORS = _load("render.json")
CONFIGURATION_VECTORS = _load("configurations.json")
MODEL_VECTORS = {v["name"]: v for v in _load("models.json")}
RELEASE_VECTORS = _load("releases.json")


# --- 1. the committed files equal a fresh generation ------------------------

@pytest.mark.parametrize("name", ["lineage_ids.json", "records.json",
                                  "render.json", "configurations.json",
                                  "models.json", "releases.json",
                                  "private.json", "overlay.json"])
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


def test_the_0_2_fields_do_not_change_the_record_id():
    with_fields = next(e for e in RECORD_VECTORS
                       if e["name"] == "omai:safe_light_with_unregistered_and_versions")["record"]
    light = next(e for e in RECORD_VECTORS
                 if e["name"] == "mcg:safe_light")["record"]
    assert {"unregistered", "lineage_version", "overlay_version"} <= set(with_fields)
    assert with_fields["id"] == light["id"]


@pytest.mark.parametrize("vector", RENDER_VECTORS,
                         ids=[v["name"] for v in RENDER_VECTORS])
def test_render_vector_reproduces_through_the_public_renderer(vector):
    renderer = RENDERERS[vector["function"]]
    instance = renderer(vector["result"], map_version=vector["map_version"],
                        **vector["kwargs"])
    assert instance.to_json_dict() == vector["instance"]
    assert instance.filename() == vector["filename"]


# Display unit -> registered unit, for the units the renderers emit.
_RENDER_UNITS = {"W/(m K)": "W_per_m_per_K", "J/(K mol)": "J_per_K_per_mol",
                 "eV": "ev", "MW/(m^2 K)": "MW_per_m2_k",
                 "dimensionless": "dimensionless", "K": "kelvin"}


def test_every_rendered_variable_is_a_node_in_the_units_of_its_dimension():
    from omai.map_data import DOMAINS, build_graph_dict
    from omai.representation.units import UNITS

    nodes = {n["id"] for n in build_graph_dict(DOMAINS)["nodes"]}
    dims = {s.name: s.fields[0].dimension for d in DOMAINS for s in d.nodes}
    for v in RENDER_VECTORS:
        inst = v["instance"]
        assert inst["variable"] in nodes, v["name"]
        unit = UNITS[_RENDER_UNITS[inst["units"]]]
        assert unit.dimension == dims[inst["variable"]], v["name"]


def test_the_composite_vector_is_the_nan_edge_at_its_conditions():
    import sympy as sp

    from omai.composites.operator.edges import depolarization_factors, nan_effective_kappa

    for v in (v for v in RENDER_VECTORS if v["function"] == "render_composite_kappa"):
        c = v["instance"]["conditions"]
        l33 = float(depolarization_factors.formula.rhs.subs(
            sp.Symbol("p", positive=True), c["d3_um"] / c["d1_um"]))
        value = float(nan_effective_kappa.formula.rhs.subs({
            sp.Symbol("k_m", positive=True): c["km_W_per_mK"],
            sp.IndexedBase("k_f")[1, 1]: c["k11_W_per_mK"],
            sp.IndexedBase("k_f")[3, 3]: c["k33_W_per_mK"],
            sp.Symbol("G_{int}", positive=True): c["G_MW_per_m2K"] * 1e6,
            sp.Symbol("d_1", positive=True): c["d1_um"] * 1e-6,
            sp.Symbol("d_3", positive=True): c["d3_um"] * 1e-6,
            sp.Symbol("f_{vol}", nonnegative=True): c["f"],
            sp.Symbol("L_{11}"): (1 - l33) / 2,
            sp.Symbol("L_{33}"): l33,
        }))
        # The commons conformance tolerance for this node.
        assert abs(value - v["instance"]["value"]) < 0.001, v["name"]


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


# The served proof record is production evidence: its bytes are pinned so a
# wording change can never rewrite them (the renderer's text is tested below).
PROOF_RECORD_SHA256 = "cc97bebc0b1e20bd3aa529b7ea5a93d059145342fa6d76a9130d6d7404432546"


def test_the_served_proof_record_bytes_are_pinned():
    data = (Path(__file__).resolve().parents[1] / "omai" / "tools" / "proof-record-903616ec.json").read_bytes()
    assert hashlib.sha256(data).hexdigest() == PROOF_RECORD_SHA256


def test_the_renderer_reproduces_the_served_proof_instance():
    """The renderer's output equals the served proof record's result in every
    field but the detail text, which 0.2.0 rewords.

    0.1.0 and 0.1.1 lacked this comparison: the renderers came from MCG's
    Python render.py, but the platform served records rendered by the worker's
    TypeScript renderer, and the two disagreed on source.ref, source.detail and
    the uncertainty key. records.json keeps the served bytes; source.detail sits
    outside the record id, so the rewording moves no id.
    """
    proof = next(e for e in RECORD_VECTORS
                 if e["name"] == "mcg:cut1_proof_run_903616ec")["record"]
    served = proof["results"][0]
    case = next(v for v in RENDER_VECTORS if v["name"] == "kappa_served_proof")
    live = render_kappa(case["result"], map_version=case["map_version"],
                        **case["kwargs"]).to_json_dict()
    assert "uncertainty" not in served  # std 0 is no spread
    for rendered in (case["instance"], live):
        assert set(rendered) == set(served)
        for key in ("variable", "material", "conditions", "value", "units"):
            assert rendered[key] == served[key], key
        assert {**rendered["source"], "detail": ""} == {**served["source"], "detail": ""}
        assert rendered["source"]["detail"] == (
            "Bulk Si kappa (BTE_RTA, 97.93 W/(m K) at 300 K, 1 seed(s)) from a "
            "MaterialsCodeGraph run; rendered against openmaterials graph "
            f"version {case['map_version']}.")


def test_the_proof_record_vector_is_real_production_bytes():
    # A vector set built only from shapes this repository invents cannot catch
    # a producer/schema mismatch; this one is what the platform served.
    proof = next(e for e in RECORD_VECTORS
                 if e["name"] == "mcg:cut1_proof_run_903616ec")["record"]
    assert proof["id"] == lineage_id(proof["lineage"])
    rows = proof["execution"]["registry"]
    assert rows and all(isinstance(r, dict) for r in rows)
    assert {"id", "name", "spdx", "license_source", "source",
            "version"} == set(rows[0])


def test_all_three_pinned_sources_are_represented():
    sources = {v["name"].split(":", 1)[0] for v in LINEAGE_VECTORS}
    assert sources == {"commons", "mcg", "kaldo"}
    # The four commons conformance targets, every MCG number vector, the kaldo
    # fixture. A shrinking vector set is a weakening contract.
    counts = {s: sum(1 for v in LINEAGE_VECTORS
                     if v["name"].startswith(s + ":")) for s in sources}
    assert counts == {"commons": 4, "mcg": 27, "kaldo": 1}


# --- configuration uids (Python only: the canonical JSON needs spglib) ------

@pytest.mark.parametrize("vector", CONFIGURATION_VECTORS,
                         ids=[v["name"] for v in CONFIGURATION_VECTORS])
def test_configuration_vector_is_the_committed_record(vector):
    import hashlib

    record = json.loads((VECTORS.parents[1] / vector["source"]).read_text())
    assert vector["structure"] == record["structure"]
    assert vector["canonical_uid"] == record["canonical"]["uid"]
    digest = hashlib.sha256(vector["canonical_json"].encode("utf-8")).hexdigest()
    assert digest == vector["canonical_uid"]


# --- model uids --------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(MODEL_VECTORS))
def test_model_vector_reproduces_through_model_uid(name):
    import hashlib

    from omai.evidence import model_uid

    vector = MODEL_VECTORS[name]
    for f in vector["files"]:
        data = f["content"].encode("utf-8")
        assert (f["sha256"], f["bytes"]) == (hashlib.sha256(data).hexdigest(), len(data))
    digests = [f["sha256"] for f in vector["files"] if f["role"] == "model"]
    assert model_uid(digests) == vector["uid"]
    if len(digests) == 1:
        assert vector["uid"] == digests[0]
    else:
        manifest = vector["manifest_json"].encode("utf-8")
        assert hashlib.sha256(manifest).hexdigest() == vector["uid"]


def test_a_training_state_companion_leaves_the_model_uid_unchanged():
    one = MODEL_VECTORS["one_file"]
    companion = MODEL_VECTORS["one_file_with_training_state"]
    assert {f["role"] for f in companion["files"]} == {"model", "training_state"}
    assert companion["uid"] == one["uid"]


# --- the release check -------------------------------------------------------

@pytest.mark.parametrize("case", RELEASE_VECTORS["cases"],
                         ids=[c["name"] for c in RELEASE_VECTORS["cases"]])
def test_release_case_reproduces_through_release_check(case):
    from omai.lineages import release_check

    assert release_check(case["execution"], RELEASE_VECTORS["codes"]) == case["unresolved"]


def test_registered_releases_are_append_only():
    # The frozen release_codes are a past state of the registry: every
    # release and alias they hold is still registered, in the same order.
    from omai.evidence import _DATA_DIR, code_releases

    live = code_releases([_DATA_DIR])
    frozen = json.loads(gen_vectors._INPUTS.read_text())["release_codes"]
    for code, entry in frozen.items():
        assert live[code]["releases"][:len(entry["releases"])] == entry["releases"], code
        assert set(entry["aliases"]) <= set(live[code]["aliases"]), code


def test_the_overlay_vector_reproduces_through_overlay_version(tmp_path):
    from omai.overlays import overlay_version

    vector = _load("overlay.json")
    for path, text in vector["files"].items():
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_bytes(text.encode("utf-8"))
    assert overlay_version(tmp_path) == vector["overlay_version"]
