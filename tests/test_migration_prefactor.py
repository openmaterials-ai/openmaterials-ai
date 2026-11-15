"""MigrationPrefactor[method=harmonic_tst], its opaque edge, its evaluator and
its representations.

The evaluator cases follow the validity contract in omai.materials.evaluate:
the Vineyard ratio over real modes, refusals for spectra that are not a minimum
and a first-order saddle, for noisy translations and for frames above the
residual-force bound, ValueError for inputs of the wrong type, shape or range,
a log-sum that survives products a double cannot hold, and an error bound that
covers the true shift to all orders.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from omai.evidence import _DATA_DIR, release_files
from omai.map_data import DOMAINS, build_codes, build_graph_dict
from omai.materials.evaluate import (
    CROSSOVER_K_PER_THZ,
    classify_modes,
    harmonic_migration_prefactor,
)
from omai.materials.operator.edges import EDGES, compute_harmonic_migration_prefactor
from omai.materials.operator.nodes import MIGRATION_BARRIER, MIGRATION_PREFACTOR, NODES
from omai.materials.operator.shared_primitives import POTENTIAL, STRUCTURE
from omai.operator.dimensions import FREQUENCY
from omai.operator.identity import edge_id, edge_identity, node_id, node_identity
from omai.operator.registry import LABEL_KEYS, QUANTITY_TAGS, quantity_tag_for
from omai.semantics import ALIASES

_ROOT = Path(__file__).resolve().parents[1]
NAME = "MigrationPrefactor[method=harmonic_tst]"
NODE_UID = "3f183436e87ac559173db2903a5ab531c8b131473d8c1e8852e6c12f51c4a969"
EDGE_UID = "a3cec28c097e24dd055e3f28317935cc60de0a3d548dd023464b53e94e7def26"
MIGRATION_BARRIER_UID = "c59c8d2bc372392cff55803e7b8b742878dac82f3ab7623bd267acd006d23d07"


def hmp(fm, fs, floor=0.05, **kw):
    """The evaluator on a subset Hessian with stationary frames, unless overridden."""
    kw.setdefault("projected", False)
    kw.setdefault("residual_force_eV_per_A", (0.01, 0.01))
    return harmonic_migration_prefactor(fm, fs, floor, **kw)


# --------------------------------------------------------------------------
# Node, edge and identity
# --------------------------------------------------------------------------

def test_node_is_a_labeled_frequency_in_the_diffusion_tier():
    assert MIGRATION_PREFACTOR in NODES
    assert MIGRATION_PREFACTOR.name == NAME
    assert dict(MIGRATION_PREFACTOR.labels) == {"method": "harmonic_tst"}
    assert "harmonic_tst" in LABEL_KEYS["method"]
    assert MIGRATION_PREFACTOR.tier == "Diffusion"
    (field,) = MIGRATION_PREFACTOR.fields
    assert field.name == "nu_star" and field.dimension == FREQUENCY and tuple(field.indices) == ()
    assert quantity_tag_for(NAME) == "migration_prefactor" and "migration_prefactor" in QUANTITY_TAGS


def test_every_base_uid_is_unchanged_and_the_new_uids_are_pinned():
    base = json.loads((_ROOT / "tests" / "fixtures" / "migration_prefactor_base_uids.json").read_text())
    nodes = {s.name: node_id(s) for d in DOMAINS for s in d.nodes}
    edges = {o.name: edge_id(o, node_id) for d in DOMAINS for o in d.edges}
    assert {n: nodes.get(n) for n in base["nodes"]} == base["nodes"]
    assert {e: edges.get(e) for e in base["edges"]} == base["edges"]
    assert set(nodes) - set(base["nodes"]) == {NAME}
    assert set(edges) - set(base["edges"]) == {"compute_harmonic_migration_prefactor"}
    assert nodes[NAME] == NODE_UID and edges["compute_harmonic_migration_prefactor"] == EDGE_UID
    assert base["nodes"]["MigrationBarrier"] == MIGRATION_BARRIER_UID


def test_edge_is_opaque_over_potential_and_structure():
    op = compute_harmonic_migration_prefactor
    assert op in EDGES
    assert tuple(op.inputs) == (POTENTIAL, STRUCTURE)
    assert tuple(op.outputs) == (MIGRATION_PREFACTOR,)
    assert dict(op.schemes) == {"method": "harmonic_tst"}
    assert op.is_executable_in_sympy is False
    # No frequency node is an input: the stable-lattice Frequency admits no
    # imaginary mode, and MolecularFrequency is the finite-molecule node.
    assert not {"Frequency", "MolecularFrequency"} & {s.name for s in op.inputs}


def test_graph_links_the_new_node_from_potential_and_structure():
    graph = build_graph_dict(DOMAINS)
    assert NAME in {n["id"] for n in graph["nodes"]}
    links = [l for l in graph["links"] if l.get("target") == NAME]
    assert {l["source"] for l in links} == {"Potential", "Structure"}


def test_text_uses_nu_star_and_states_the_validity_limits():
    for text in (MIGRATION_PREFACTOR.description, compute_harmonic_migration_prefactor.description,
                 QUANTITY_TAGS["migration_prefactor"]):
        assert "nu*" in text and "nu_0" not in text
        assert "zero-point" in text and "Wigner" in text
    assert "nu* exp(-E_m" in MIGRATION_BARRIER.description and "nu_0" not in MIGRATION_BARRIER.description
    assert NAME in MIGRATION_BARRIER.description
    assert "Wert-Zener" in MIGRATION_PREFACTOR.description
    assert "approximates the full ratio" in MIGRATION_PREFACTOR.description


def test_semantic_aliases_point_at_the_node_and_edge():
    for alias in ("migration-prefactor", "vineyard-prefactor", "hop-prefactor"):
        assert NAME in ALIASES[alias]
    assert "compute_harmonic_migration_prefactor" in ALIASES["vineyard-prefactor"]
    assert "hop-attempt-frequency" not in ALIASES


def test_store_records_follow_the_thermochemistry_contributions_and_pass_the_gates():
    """Records 388-390: the node, its edge, then MigrationBarrier's description
    edit. No supersede, so no existing uid moves. The node and edge pass the
    contribution gates against the pre-existing Potential and Structure."""
    from omai.gates import validate_contribution

    lines = (_ROOT / "map" / "log.jsonl").read_text().splitlines()
    recs = [json.loads(line) for line in lines[387:390]]
    assert [(r["seq"], r["op"]) for r in recs] == [
        (388, "add_node"), (389, "add_edge"), (390, "edit_meta")]
    assert recs[0]["payload"]["uid"] == NODE_UID
    assert recs[1]["payload"]["uid"] == EDGE_UID
    assert recs[2]["payload"]["uid"] == MIGRATION_BARRIER_UID
    assert set(recs[2]["payload"]["meta"]) == {"description"}
    assert "nu* exp(-E_m" in recs[2]["payload"]["meta"]["description"]

    records = [
        {"op": "add_node", "payload": {"uid": node_id(MIGRATION_PREFACTOR),
                                       "identity": node_identity(MIGRATION_PREFACTOR),
                                       "meta": {"name": NAME}}},
        {"op": "add_edge", "payload": {"uid": edge_id(compute_harmonic_migration_prefactor, node_id),
                                       "identity": edge_identity(compute_harmonic_migration_prefactor, node_id),
                                       "meta": {"name": compute_harmonic_migration_prefactor.name,
                                                "schemes": compute_harmonic_migration_prefactor.schemes}}},
    ]
    current = {"nodes": {}, "edges": {}}
    for s in (POTENTIAL, STRUCTURE):
        current["nodes"][node_id(s)] = {"uid": node_id(s), "identity": node_identity(s), "meta": {}}
    assert validate_contribution(records, current) == []


# --------------------------------------------------------------------------
# Representations and the ase release
# --------------------------------------------------------------------------

def test_openmaterials_ai_covers_the_prefactor_in_linear_thz():
    codes = build_codes(DOMAINS)
    entry = codes["openmaterials-ai"][NAME]
    assert entry["unit"] == "linear_THz"
    assert entry["api"].startswith("omai.materials.evaluate.harmonic_migration_prefactor(")


def test_ase_covers_the_migration_barrier_and_keeps_its_other_nodes():
    codes = build_codes(DOMAINS)
    assert {"MigrationBarrier", "Structure", "Potential", "Trajectory"} <= set(codes["ase"])
    assert codes["ase"]["MigrationBarrier"]["unit"] == "ev"
    assert "ase.mep.NEB" in codes["ase"]["MigrationBarrier"]["api"]
    assert NAME not in codes["ase"]


def test_ase_3_26_0_is_a_registered_release():
    doc = release_files(_DATA_DIR)["ase"]
    (row,) = doc["releases"]
    assert row["version"] == "3.26.0" and row["tag"] == "3.26.0"
    assert row["commit"] == "6c965f46a9449cbea275a6cc11fefb82da7df4bf"
    assert row["spdx"] == "LGPL-2.1-or-later" and row["released"] == "2025-08-12"


# --------------------------------------------------------------------------
# Evaluator: values
# --------------------------------------------------------------------------

def test_crossover_constant():
    assert abs(CROSSOVER_K_PER_THZ - 7.6382) < 1e-4


def test_one_mode_returns_that_mode():
    out = hmp([5.0], [-1.0])
    assert out["reason"] is None
    assert math.isclose(out["nu_star_THz"], 5.0, rel_tol=1e-12)
    assert out["modes_min"] == {"imaginary": 0, "soft": 0, "real": 1}
    assert out["modes_saddle"] == {"imaginary": 1, "soft": 0, "real": 0}
    assert out["imaginary_THz"] == -1.0
    assert math.isclose(out["crossover_temperature_K"], CROSSOVER_K_PER_THZ)
    assert out["ln_nu_star_error_bound"] is None


def test_golden_ratio_of_products():
    out = hmp([2.0, 3.0, 5.0], [-1.0, 4.0, 6.0])
    assert math.isclose(out["nu_star_THz"], 30.0 / 24.0, rel_tol=1e-12)
    assert math.isclose(out["ln_nu_star_THz"], math.log(1.25), rel_tol=1e-12)


def test_a_projected_run_takes_its_translations():
    out = hmp([2.0, 3.0, 5.0], [-1.0, 4.0, 6.0], projected=True,
              translational_THz=[(0.01, -0.02, 0.0), (0.0, 0.015, -0.01)])
    assert math.isclose(out["nu_star_THz"], 1.25, rel_tol=1e-12)


def test_angular_inputs_scale_the_result_by_two_pi():
    cyc_min, cyc_sad = [2.0, 3.0, 5.0], [-1.0, 4.0, 6.0]
    two_pi = 2.0 * math.pi
    cyc = hmp(cyc_min, cyc_sad)["nu_star_THz"]
    ang = hmp([two_pi * x for x in cyc_min], [two_pi * x for x in cyc_sad])["nu_star_THz"]
    assert math.isclose(ang / cyc, two_pi, rel_tol=1e-12)


def test_log_sum_survives_an_overflowing_product():
    fm = [20.0] * 400
    fs = [-3.0] + [20.0] * 399
    assert math.isinf(math.prod(fm))
    assert math.isclose(hmp(fm, fs)["nu_star_THz"], 20.0, rel_tol=1e-12)


def test_log_sum_survives_an_underflowing_product():
    fm = [0.1] * 400
    fs = [-3.0] + [0.1] * 399
    assert math.prod(fm) == 0.0
    assert math.isclose(hmp(fm, fs)["nu_star_THz"], 0.1, rel_tol=1e-12)


@pytest.mark.parametrize("fm, fs, side", [
    ([100.0] * 400, [-3.0] + [0.06] * 399, "overflows"),
    ([0.06] * 400, [-3.0] + [100.0] * 399, "underflows"),
])
def test_a_result_outside_the_double_range_is_refused(fm, fs, side):
    out = hmp(fm, fs)
    assert out["nu_star_THz"] is None and side in out["reason"]
    assert out["imaginary_THz"] is None and out["crossover_temperature_K"] is None


def test_the_determinant_form_agrees_on_random_hessians():
    """Independent check: nu* = (1/2 pi) sqrt(det D_min / |det D_sad / lambda_imag|)
    for mass-weighted Hessians D in angular THz^2, the modes from numpy's
    eigenvalues converted to cyclic THz."""
    rng = np.random.default_rng(1957)
    for n in (3, 9, 24):
        for _ in range(5):
            q1, _ = np.linalg.qr(rng.normal(size=(n, n)))
            q2, _ = np.linalg.qr(rng.normal(size=(n, n)))
            d_min = q1 @ np.diag(rng.uniform(4.0, 900.0, n)) @ q1.T
            lam_s = np.concatenate([[-rng.uniform(4.0, 400.0)], rng.uniform(4.0, 900.0, n - 1)])
            d_sad = q2 @ np.diag(lam_s) @ q2.T
            cyc = lambda lam: [math.copysign(math.sqrt(abs(x)), x) / (2 * math.pi) for x in lam]
            lam_min, lam_sad = np.linalg.eigvalsh(d_min), np.linalg.eigvalsh(d_sad)
            out = hmp(cyc(lam_min), cyc(lam_sad))
            sign_m, logdet_m = np.linalg.slogdet(d_min)
            sign_s, logdet_s = np.linalg.slogdet(d_sad)
            lam_imag = lam_sad[0]
            assert sign_m > 0 and sign_s < 0 and lam_imag < 0
            ln_ref = 0.5 * (logdet_m - (logdet_s - math.log(abs(lam_imag)))) - math.log(2 * math.pi)
            assert math.isclose(out["ln_nu_star_THz"], ln_ref, rel_tol=1e-9, abs_tol=1e-9)


# --------------------------------------------------------------------------
# Evaluator: the error bound
# --------------------------------------------------------------------------

def test_error_bound_sums_the_larger_one_sided_shift_of_each_mode():
    """Each real mode contributes 0.5 * -log1p(-eps/lambda), its falling-side
    shift, which exceeds the rising-side 0.5 * log1p(eps/lambda)."""
    eps, lams = 1e-3, (0.01, 100.0, 100.0)
    out = hmp([0.1, 10.0], [-1.0, 10.0], eigenvalue_noise_THz2=eps)
    expected = 0.5 * sum(-math.log1p(-eps / lam) for lam in lams)
    assert math.isclose(out["ln_nu_star_error_bound"], expected, rel_tol=1e-12)
    assert expected > 0.5 * sum(math.log1p(eps / lam) for lam in lams)


def test_error_bound_covers_the_worst_shift_near_the_floor():
    """Shift every real eigenvalue lambda = nu^2 by at most eps and recompute
    ln nu* = (1/2) sum ln lambda_min - (1/2) sum ln lambda_sad directly: the
    bound must cover the largest shift. A shifted soft mode may fall below the
    floor, so the shift is recomputed here, not through the evaluator."""
    lam_min, lam_sad = [0.06 ** 2, 3.0 ** 2, 7.0 ** 2], [4.0 ** 2, 6.0 ** 2]
    # Below floor^2 = 0.0025 and the smallest real lambda 0.0036, so accepted,
    # though lowering 0.0036 by eps puts that mode under the floor.
    eps = 0.002
    out = hmp([0.06, 3.0, 7.0], [-1.0, 4.0, 6.0], eigenvalue_noise_THz2=eps)
    bound = out["ln_nu_star_error_bound"]

    def ln_nu(dm, ds):
        return 0.5 * (sum(math.log(l + d) for l, d in zip(lam_min, dm))
                      - sum(math.log(l + d) for l, d in zip(lam_sad, ds)))

    ref = ln_nu([0.0] * 3, [0.0] * 2)
    assert math.isclose(ref, out["ln_nu_star_THz"], rel_tol=1e-12)
    corners = [ln_nu([-eps] * 3, [eps] * 2), ln_nu([eps] * 3, [-eps] * 2)]
    rng = np.random.default_rng(7)
    sampled = [ln_nu(rng.uniform(-eps, eps, 3), rng.uniform(-eps, eps, 2)) for _ in range(500)]
    worst = max(abs(v - ref) for v in corners + sampled)
    assert 0.0 < worst <= bound * (1 + 1e-12)
    # The softest mode dominates: the corner that lowers it comes close to the bound.
    assert worst > 0.8 * bound


def test_error_bound_covers_float32_six_digit_rounding_of_the_hessians():
    rng = np.random.default_rng(20261115)
    n = 12

    def hessian(eigs):
        q, _ = np.linalg.qr(rng.normal(size=(n, n)))
        return q @ np.diag(eigs) @ q.T

    def freqs(d):
        return [math.copysign(math.sqrt(abs(x)), x) for x in np.linalg.eigvalsh(d)]

    def rounded(d):
        return np.array([[float(f"{np.float32(x):.6g}") for x in row] for row in d])

    d_min = hessian(rng.uniform(0.6, 15.0, n) ** 2)
    d_sad = hessian(np.concatenate([[-1.5 ** 2], rng.uniform(0.6, 15.0, n - 1) ** 2]))
    r_min, r_sad = rounded(d_min), rounded(d_sad)
    # Weyl: no eigenvalue moves by more than the spectral norm of the change.
    eps = max(np.linalg.norm(r_min - d_min, 2), np.linalg.norm(r_sad - d_sad, 2))
    exact = hmp(freqs(d_min), freqs(d_sad))
    noisy = hmp(freqs(r_min), freqs(r_sad), eigenvalue_noise_THz2=eps)
    shift = abs(noisy["ln_nu_star_THz"] - exact["ln_nu_star_THz"])
    assert 0.0 < shift <= noisy["ln_nu_star_error_bound"]


@pytest.mark.parametrize("eps, needles", [
    (0.0025, ["floor squared"]),  # equals 0.05**2 up to rounding
    (0.003, ["floor squared"]),
    (5.0, ["floor squared", "smallest real eigenvalue", "imaginary eigenvalue"]),
])
def test_noise_that_could_move_a_mode_across_the_floor_is_refused(eps, needles):
    out = hmp([2.0, 3.0], [-1.0, 4.0], eigenvalue_noise_THz2=eps)
    assert out["nu_star_THz"] is None and out["ln_nu_star_error_bound"] is None
    for needle in needles:
        assert needle in out["reason"]
    assert out["imaginary_THz"] is None and out["crossover_temperature_K"] is None


# --------------------------------------------------------------------------
# Evaluator: refusals with a reason
# --------------------------------------------------------------------------

@pytest.mark.parametrize("fm, fs, needle", [
    ([-2.0, 5.0], [-1.0], "not a minimum"),
    ([0.01, 5.0], [-1.0], "not a minimum"),
    ([5.0], [3.0], "not a first-order saddle"),
    ([5.0, 6.0], [-1.0, -2.0, 4.0], "not a first-order saddle"),
    ([5.0, 6.0], [-1.0, 0.0, 4.0], "not a first-order saddle"),
    ([5.0, 6.0, 7.0], [-1.0, 4.0, 5.0, 6.0], "must differ by one"),
    ([], [], "not a first-order saddle"),
    ([], [-1.0], "must differ by one"),
])
def test_spectra_that_are_not_a_minimum_and_a_saddle_are_refused(fm, fs, needle):
    out = hmp(fm, fs)
    assert out["nu_star_THz"] is None and out["ln_nu_star_THz"] is None
    assert needle in out["reason"]
    assert out["imaginary_THz"] is None and out["crossover_temperature_K"] is None


def test_noisy_translations_are_refused():
    ok = hmp([5.0], [-1.0], projected=True, translational_THz=[(0.02, -0.025, 0.0), (0.0, 0.0, 0.0)])
    assert ok["reason"] is None
    out = hmp([5.0], [-1.0], projected=True, translational_THz=[(0.0, 0.0, 0.0), (0.02, -0.03, 0.0)])
    assert out["nu_star_THz"] is None and "translational mode" in out["reason"]
    assert out["imaginary_THz"] is None and out["crossover_temperature_K"] is None


def test_a_frame_above_the_residual_force_bound_is_refused():
    assert hmp([5.0], [-1.0], residual_force_eV_per_A=(0.01, 0.05))["reason"] is None
    out = hmp([5.0], [-1.0], residual_force_eV_per_A=(0.03, 0.2))
    assert out["nu_star_THz"] is None and "not accepted as a stationary point" in out["reason"]
    assert out["imaginary_THz"] is None and out["crossover_temperature_K"] is None
    tight = hmp([5.0], [-1.0], residual_force_eV_per_A=(0.03, 0.03), max_residual_force_eV_per_A=0.02)
    assert "not accepted as a stationary point" in tight["reason"]


def test_signed_zero_and_the_floor_itself_count_as_soft():
    assert classify_modes([-0.0, 0.0, 0.05, -0.05], 0.05) == {"imaginary": 0, "soft": 4, "real": 0}
    assert classify_modes([0.0500001, -0.0500001], 0.05) == {"imaginary": 1, "soft": 0, "real": 1}


# --------------------------------------------------------------------------
# Evaluator: the required arguments, and ValueError for bad inputs
# --------------------------------------------------------------------------

def test_projected_and_the_residual_forces_have_no_default():
    with pytest.raises(TypeError):
        harmonic_migration_prefactor([5.0], [-1.0], 0.05, residual_force_eV_per_A=(0.01, 0.01))
    with pytest.raises(TypeError):
        harmonic_migration_prefactor([5.0], [-1.0], 0.05, projected=False)


@pytest.mark.parametrize("fm, fs, floor, kw", [
    # projected must be a bool, and decides whether translations are passed
    ([5.0], [-1.0], 0.05, dict(projected=1)),
    ([5.0], [-1.0], 0.05, dict(projected="True")),
    ([5.0], [-1.0], 0.05, dict(projected=None)),
    ([5.0], [-1.0], 0.05, dict(projected=True)),
    ([5.0], [-1.0], 0.05, dict(projected=True, translational_THz=[(0.0, 0.0, 0.0)])),
    ([5.0], [-1.0], 0.05, dict(projected=True, translational_THz=[(0.0, 0.0), (0.0, 0.0, 0.0)])),
    ([5.0], [-1.0], 0.05, dict(projected=True, translational_THz=[0.0, 0.0])),
    ([5.0], [-1.0], 0.05, dict(projected=True, translational_THz=[(0.0, math.nan, 0.0), (0.0, 0.0, 0.0)])),
    ([5.0], [-1.0], 0.05, dict(projected=True, translational_THz=7)),
    ([5.0], [-1.0], 0.05, dict(translational_THz=[(0.0, 0.0, 0.0), (0.0, 0.0, 0.0)])),
    # mode lists: one-dimensional, finite, real
    ("5.0", [-1.0], 0.05, {}),
    (b"5", [-1.0], 0.05, {}),
    ([True, 5.0], [-1.0], 0.05, {}),
    ([5.0 + 0j], [-1.0], 0.05, {}),
    ([[5.0, 6.0]], [-1.0], 0.05, {}),
    ([[5.0], [6.0, 7.0]], [-1.0], 0.05, {}),
    (np.array([[5.0]]), [-1.0], 0.05, {}),
    (5.0, [-1.0], 0.05, {}),
    ([5.0, math.nan], [-1.0, math.nan], 0.05, {}),
    ([math.inf], [-1.0], 0.05, {}),
    ([5.0], [-math.inf], 0.05, {}),
    ([10 ** 400], [-1.0], 0.05, {}),
    ([5.0], ["-1.0"], 0.05, {}),
    # floor: finite and positive real
    ([5.0], [-1.0], -0.05, {}),
    ([5.0], [-1.0], 0.0, {}),
    ([5.0], [-1.0], math.nan, {}),
    ([5.0], [-1.0], math.inf, {}),
    ([5.0], [-1.0], True, {}),
    ([5.0], [-1.0], "0.05", {}),
    ([5.0], [-1.0], 0.05 + 0j, {}),
    ([5.0], [-1.0], 10 ** 400, {}),
    # residual forces: two nonnegative finite reals
    ([5.0], [-1.0], 0.05, dict(residual_force_eV_per_A=(0.01,))),
    ([5.0], [-1.0], 0.05, dict(residual_force_eV_per_A=(-0.01, 0.01))),
    ([5.0], [-1.0], 0.05, dict(residual_force_eV_per_A=(math.nan, 0.01))),
    ([5.0], [-1.0], 0.05, dict(residual_force_eV_per_A=0.01)),
    ([5.0], [-1.0], 0.05, dict(max_residual_force_eV_per_A=0.0)),
    # eigenvalue noise: a finite nonnegative real
    ([5.0], [-1.0], 0.05, dict(eigenvalue_noise_THz2=-1e-6)),
    ([5.0], [-1.0], 0.05, dict(eigenvalue_noise_THz2=math.nan)),
    ([5.0], [-1.0], 0.05, dict(eigenvalue_noise_THz2=1e-6j)),
    ([5.0], [-1.0], 0.05, dict(eigenvalue_noise_THz2=False)),
])
def test_bad_inputs_raise_value_error(fm, fs, floor, kw):
    with pytest.raises(ValueError):
        hmp(fm, fs, floor, **kw)
