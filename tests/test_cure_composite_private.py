"""The cure and composite numerics are not in the commons.

The public package carries the cure-kinetics and Nan effective-medium nodes,
their closed-form edges and the record renderers, but no evaluator and no code
representation of those nodes.
"""
from __future__ import annotations

import hashlib
import importlib
import re
from pathlib import Path

import pytest

from omai.map_data import DOMAINS, build_codes, build_graph_dict
from omai.render import KINETICS_HASH_KEYS, _sha256, canonical_params

_REPO = Path(__file__).resolve().parents[1]
_PACKAGE = _REPO / "omai"

CURE_AND_NAN_NODES = {
    "CureConversion",
    "GlassTransitionTemperature",
    "ThermalConductivity[effective_medium=nan,orientation=random]",
    "ThermalConductivity[effective_medium=nan,orientation=aligned]",
}

# The evaluators that left the commons, by the names the 0.7.0 wheel exported.
_REMOVED_FUNCTIONS = ("cure_conversion", "glass_transition_temperature",
                      "nan_kappa_random", "nan_kappa_aligned",
                      "aligned_tensor_components")


def _wheel_files():
    """Every file the wheel packs from omai/: Python sources and package data."""
    for path in sorted(_PACKAGE.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix in (
                ".py", ".json", ".txt", ".lean", ".md"):
            yield path


def test_no_cure_or_composite_numerics_in_the_public_package():
    for module in ("omai.cure_kinetics.evaluate", "omai.composites.evaluate"):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(module)
    body = re.compile(r"^\s*def (%s)\(" % "|".join(_REMOVED_FUNCTIONS), re.M)
    pointer = re.compile(r"omai\.(cure_kinetics|composites)\.evaluate")
    for path in _wheel_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        assert not body.search(text), f"{path.relative_to(_REPO)} defines a removed evaluator"
        assert not pointer.search(text), f"{path.relative_to(_REPO)} points at a removed evaluator"


def test_cure_and_nan_nodes_stay_on_the_map_with_no_representation():
    names = {n["id"] for n in build_graph_dict(DOMAINS)["nodes"]}
    assert CURE_AND_NAN_NODES <= names
    codes = build_codes(DOMAINS)
    for code, entry in codes.items():
        assert not CURE_AND_NAN_NODES & set(entry), code
    # openmaterials-ai keeps only its own public evaluators: the ideal-gas heat
    # capacity and the harmonic migration prefactor.
    assert set(codes["openmaterials-ai"]) == {
        "IdealGasMolarHeatCapacityP", "IdealGasMolarHeatCapacityP[approximation=qrrho]",
        "MigrationPrefactor[method=harmonic_tst]"}


def test_no_representation_module_for_the_cure_and_nan_nodes():
    for domain in ("cure_kinetics", "composites"):
        modules = {p.stem for p in (_PACKAGE / domain / "representation").glob("*.py")}
        assert modules <= {"__init__", "gpumd"}, (domain, modules)


def test_canonical_bytes():
    """The renderer's kinetics hash, which stays public: stored records keep
    their ids."""
    p = dict(a1_pref_per_s=1000, e1_J_per_mol=5e4, a2_pref_per_s=1e5,
             e2_J_per_mol=5e4, m=1, n=1.5, l_order=None, source="not hashed")
    blob = (b'{"a1_pref_per_s":1000.0,"a2_pref_per_s":100000.0,"e1_J_per_mol":50000.0,'
            b'"e2_J_per_mol":50000.0,"m":1.0,"n":1.5}')
    assert canonical_params(p, KINETICS_HASH_KEYS) == blob
    assert _sha256(p, KINETICS_HASH_KEYS) == hashlib.sha256(blob).hexdigest()
