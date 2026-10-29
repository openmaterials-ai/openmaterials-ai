"""Compiler-backed reviewed endpoint provenance; not automatic formula semantics."""
import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_BASELINE_CONTRACTS = (
    "semantic-formula-contract.json",
    "continuum-formula-contract.json",
    "harmonic-ensemble-formula-contract.json",
    "harmonic-sums-formula-contract.json",
)
_SPEC = importlib.util.spec_from_file_location(
    "bridge_verify_contracts_test", _ROOT / "lean/bridge/verify_contracts.py",
)
assert _SPEC is not None and _SPEC.loader is not None
_VERIFY = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_VERIFY)


@pytest.fixture
def package_and_contract(tmp_path):
    package = tmp_path / "repo/lean/bridge"
    package.mkdir(parents=True)
    (package / ".lake").mkdir()
    (package / "lakefile.toml").write_text(
        '[[lean_lib]]\nname = "ActualBridge"\nroots = ["ActualUmbrella"]\n',
    )
    (package / "ActualDefinition.lean").write_text("namespace Actual\ndef endpoint := 1\n")
    contract = {
        "source_path": "lean/bridge/ActualDefinition.lean",
        "operators": [{"id": "test_operator", "lean_definition": "Actual.endpoint"}],
    }
    return package, contract


def _write_contract(tmp_path, contract):
    path = tmp_path / "test-formula-contract.json"
    path.write_text(json.dumps(contract))
    return path


def test_probe_uses_configured_library_and_forces_bounded_compiler(
    tmp_path, monkeypatch, package_and_contract,
):
    package, contract = package_and_contract
    # The definition source differs from the proof source and lies in a nested module.
    (package / "Nested").mkdir()
    (package / "Nested/Endpoint.lean").write_text("namespace Actual\ndef endpoint := 1\n")
    contract["operators"][0]["definition_source_path"] = "lean/bridge/Nested/Endpoint.lean"
    contract["nodes"] = [{"id": "associated_input"}]
    monkeypatch.setenv("LEAN_NUM_THREADS", "900")
    monkeypatch.setenv("MATHLIB_NO_CACHE_ON_UPDATE", "0")
    monkeypatch.delenv("OMAI_LEAN_PROBE_TIMEOUT", raising=False)
    probes = []

    def compiler(command, **kwargs):
        assert command[:5] == ["lake", "--no-build", "env", "lean", "-j2"]
        assert kwargs["cwd"] == package
        assert kwargs["timeout"] == 120
        assert kwargs["env"]["LEAN_NUM_THREADS"] == "2"
        assert kwargs["env"]["MATHLIB_NO_CACHE_ON_UPDATE"] == "1"
        probe = Path(command[-1])
        probes.append(probe)
        source = probe.read_text()
        assert source.startswith("import ActualUmbrella\nimport Lean\n")
        assert "(`Actual.endpoint, `Nested.Endpoint)" in source
        assert "import Nested.Endpoint" not in source
        return subprocess.CompletedProcess(command, 0, "OMAI_CONTRACT_NAMES_OK|1\n", "")

    monkeypatch.setattr(_VERIFY.subprocess, "run", compiler)
    path = _write_contract(tmp_path, contract)
    assert _VERIFY.verify_compiled_contract_names([path], package) == [
        {"name": "Actual.endpoint", "module": "Nested.Endpoint"},
    ]
    assert len(probes) == 1 and not probes[0].exists()


def test_probe_timeout_override_reaches_the_compiler(tmp_path, monkeypatch, package_and_contract):
    package, contract = package_and_contract
    monkeypatch.setenv("OMAI_LEAN_PROBE_TIMEOUT", " 600 ")
    seen = []

    def compiler(command, **kwargs):
        seen.append(kwargs["timeout"])
        return subprocess.CompletedProcess(command, 0, "OMAI_CONTRACT_NAMES_OK|1\n", "")

    monkeypatch.setattr(_VERIFY.subprocess, "run", compiler)
    _VERIFY.verify_compiled_contract_names([_write_contract(tmp_path, contract)], package)
    assert seen == [600]
    monkeypatch.delenv("OMAI_LEAN_PROBE_TIMEOUT")
    assert _VERIFY._probe_timeout() == 120


@pytest.mark.parametrize("value", ["", "0", "-5", "300.5", "soon"])
def test_probe_timeout_rejects_non_positive_or_non_integer_values(
    value, tmp_path, monkeypatch, package_and_contract,
):
    package, contract = package_and_contract
    monkeypatch.setenv("OMAI_LEAN_PROBE_TIMEOUT", value)
    monkeypatch.setattr(_VERIFY.subprocess, "run", lambda *args, **kwargs: pytest.fail("compiled"))
    if value.strip() == "":
        assert _VERIFY._probe_timeout() == 120
        return
    with pytest.raises(ValueError, match="OMAI_LEAN_PROBE_TIMEOUT must be a positive integer"):
        _VERIFY.verify_compiled_contract_names([_write_contract(tmp_path, contract)], package)


@pytest.mark.parametrize("name", [
    "Actual.endpoint\nrun_cmd IO.println \"injected\"", "Actual.endpoint;", "`Actual.endpoint",
    "Actual.«endpoint»", "Actual.endpoint--comment", "Actual..endpoint", "endpoint", "", None,
])
def test_rejects_unsafe_or_unqualified_names_before_compiling(
    name, tmp_path, monkeypatch, package_and_contract,
):
    package, contract = package_and_contract
    contract["operators"][0]["lean_definition"] = name
    monkeypatch.setattr(_VERIFY.subprocess, "run", lambda *args, **kwargs: pytest.fail("compiled"))
    with pytest.raises(ValueError, match="contract Lean definition"):
        _VERIFY.verify_compiled_contract_names([_write_contract(tmp_path, contract)], package)


@pytest.mark.parametrize("source", [
    "/tmp/Outside.lean", "lean/bridge/../bridge/ActualDefinition.lean",
    "lean/bridge/../../Outside.lean", "lean//bridge/ActualDefinition.lean",
    "lean/bridge/./ActualDefinition.lean", "lean\\bridge\\ActualDefinition.lean",
    "lean/bridge/ActualDefinition.lean\nimport Evil", "lean/bridge/Missing.lean", "", None,
])
def test_rejects_unsafe_or_missing_definition_paths_before_compiling(
    source, tmp_path, monkeypatch, package_and_contract,
):
    package, contract = package_and_contract
    contract["operators"][0]["definition_source_path"] = source
    monkeypatch.setattr(_VERIFY.subprocess, "run", lambda *args, **kwargs: pytest.fail("compiled"))
    with pytest.raises(ValueError, match="source"):
        _VERIFY.verify_compiled_contract_names([_write_contract(tmp_path, contract)], package)


@pytest.mark.parametrize("inside", [False, True])
def test_rejects_symlink_escape_or_module_alias_before_compiling(
    tmp_path, monkeypatch, package_and_contract, inside,
):
    package, contract = package_and_contract
    target = package / "ActualDefinition.lean" if inside else tmp_path / "Outside.lean"
    if not inside:
        target.write_text("def endpoint := 1\n")
    (package / "Escape.lean").symlink_to(target)
    contract["operators"][0]["definition_source_path"] = "lean/bridge/Escape.lean"
    monkeypatch.setattr(_VERIFY.subprocess, "run", lambda *args, **kwargs: pytest.fail("compiled"))
    with pytest.raises(ValueError, match="source"):
        _VERIFY.verify_compiled_contract_names([_write_contract(tmp_path, contract)], package)


@pytest.mark.parametrize("roots", ['["Root\\nimport Evil"]', '[]', '"Root"'])
def test_rejects_unsafe_or_empty_configured_imports(
    roots, tmp_path, monkeypatch, package_and_contract,
):
    package, contract = package_and_contract
    (package / "lakefile.toml").write_text(f'[[lean_lib]]\nname = "Actual"\nroots = {roots}\n')
    monkeypatch.setattr(_VERIFY.subprocess, "run", lambda *args, **kwargs: pytest.fail("compiled"))
    with pytest.raises(ValueError, match="Lean library"):
        _VERIFY.verify_compiled_contract_names([_write_contract(tmp_path, contract)], package)


@pytest.mark.parametrize("contracts", [[], [{"source_path": "lean/bridge/ActualDefinition.lean"}]])
def test_rejects_empty_contract_input(contracts, tmp_path, package_and_contract):
    package, _ = package_and_contract
    paths = [_write_contract(tmp_path, contract) for contract in contracts]
    with pytest.raises(ValueError, match="no reviewed formula contracts|no endpoints"):
        _VERIFY.verify_compiled_contract_names(paths, package)


@pytest.mark.parametrize("output", ["", "OMAI_CONTRACT_NAMES_OK|2", "OMAI_CONTRACT_NAMES_OK|1\n" * 2])
def test_requires_exact_compiler_completion(tmp_path, monkeypatch, package_and_contract, output):
    package, contract = package_and_contract
    monkeypatch.setattr(
        _VERIFY.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess([], 0, output, ""),
    )
    with pytest.raises(ValueError, match="completion marker"):
        _VERIFY.verify_compiled_contract_names([_write_contract(tmp_path, contract)], package)


def test_compiler_timeout_cleans_probe_and_fails_closed(tmp_path, monkeypatch, package_and_contract):
    package, contract = package_and_contract

    def compiler(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(_VERIFY.subprocess, "run", compiler)
    with pytest.raises(ValueError, match="could not complete"):
        _VERIFY.verify_compiled_contract_names([_write_contract(tmp_path, contract)], package)
    assert not list((package / ".lake").glob("contract-names-*"))


@pytest.fixture(scope="module")
def compiled_package():
    configured = os.environ.get("PHYSLIB_BRIDGE_PACKAGE")
    if not configured:
        pytest.skip("PHYSLIB_BRIDGE_PACKAGE not set to an already-built Lean package")
    return Path(configured).resolve()


def test_real_compiler_accepts_all_baseline_contract_names_and_modules(compiled_package):
    # These four reviewed contracts require only the existing umbrella build;
    # the package audit also checks new contracts after integration.
    paths = [compiled_package / name for name in _BASELINE_CONTRACTS]
    verified = _VERIFY.verify_compiled_contract_names(paths, compiled_package)
    assert len(verified) == 12
    assert {"name": "OMAI.PhyslibBridge.harmonicFreeEnergy",
            "module": "OMAIPhyslibSemantics"} in verified
    assert {"name": "OMAI.PhyslibBridge.harmonicHeatCapacity",
            "module": "OMAIPhyslibHarmonicEnsemble"} in verified


def test_real_compiler_rejects_invented_namespace(compiled_package, tmp_path):
    contract = json.loads((compiled_package / "semantic-formula-contract.json").read_text())
    contract["operators"][0]["lean_definition"] = "InventedOMAI.PhyslibBridge.harmonicEntropy"
    with pytest.raises(ValueError, match="Contract declaration is absent: InventedOMAI"):
        _VERIFY.verify_compiled_contract_names([_write_contract(tmp_path, contract)], compiled_package)


def test_real_compiler_rejects_wrong_defining_module(compiled_package, tmp_path):
    contract = json.loads((compiled_package / "semantic-formula-contract.json").read_text())
    contract["operators"][0]["definition_source_path"] = "lean/bridge/OMAIPhyslibContinuum.lean"
    with pytest.raises(ValueError, match="belongs to OMAIPhyslibSemantics, not OMAIPhyslibContinuum"):
        _VERIFY.verify_compiled_contract_names([_write_contract(tmp_path, contract)], compiled_package)
