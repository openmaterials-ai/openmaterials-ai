"""Check reviewed endpoint names in the already-built OMAI Lean library.

This validates full declaration names and defining modules, not the scientific
meaning of a formula. The caller must separately require the complete contract
set, check reviewed hashes, build the library, and audit its transitive axioms.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import tomllib
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

_IDENTIFIER = r"(?:[^\W\d]|_)[\w']*(?:\.(?:[^\W\d]|_)[\w']*)*"
_TIMEOUT_SECONDS = 120


def _identifier(value: object, label: str) -> str:
    # Ordinary dotted names (including Unicode and primes) only. Never splice
    # quoted identifiers, commands, comments or control characters into Lean.
    if not isinstance(value, str) or not re.fullmatch(_IDENTIFIER, value):
        raise ValueError(f"unsupported {label}: {value!r}")
    return value


def _relative_path(value: object, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError(f"invalid {label}: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value or value == ".":
        raise ValueError(f"invalid {label}: {value!r}")
    return path


def _library_configuration(package: Path) -> tuple[list[str], list[Path]]:
    config = tomllib.loads((package / "lakefile.toml").read_text())
    libraries = config.get("lean_lib", [])
    if not isinstance(libraries, list) or not libraries:
        raise ValueError("no configured Lean library to validate contract names")
    imports: set[str] = set()
    source_roots: set[Path] = set()
    for library in libraries:
        if not isinstance(library, dict):
            raise ValueError("invalid Lean library configuration")
        name = _identifier(library.get("name"), "Lean library name")
        roots = library.get("roots", [name])
        if not isinstance(roots, list) or not roots:
            raise ValueError(f"no import roots configured for Lean library {name}")
        imports.update(_identifier(root, "Lean library root") for root in roots)
        source_directory = library.get("srcDir", config.get("srcDir", "."))
        source_root = package if source_directory == "." else (
            package / _relative_path(source_directory, "Lean library source directory")
        ).resolve()
        if not source_root.is_relative_to(package) or not source_root.is_dir():
            raise ValueError("Lean library source directory is outside the package or missing")
        source_roots.add(source_root)
    return sorted(imports), sorted(source_roots)


def _source_module(value: object, package: Path, source_roots: list[Path]) -> str:
    relative = _relative_path(value, "contract definition source path")
    # Reviewed contracts use repository-relative paths; this package lives at
    # lean/bridge. Resolve before opening so a symlink cannot escape the package.
    source = package.parents[1] / relative
    resolved = source.resolve()
    if (source != resolved or not resolved.is_relative_to(package)
            or source.suffix != ".lean" or not source.is_file()):
        raise ValueError(f"contract definition source must be a Lean file in the package: {value!r}")
    modules = {
        ".".join(source.relative_to(root).with_suffix("").parts)
        for root in source_roots if source.is_relative_to(root)
    }
    if len(modules) != 1:
        raise ValueError(f"contract definition source has no unambiguous configured module: {value!r}")
    return _identifier(modules.pop(), "contract definition module")


def verify_compiled_contract_names(
    contract_paths: Iterable[Path], lean_package: Path,
) -> list[dict[str, str]]:
    """Return unique validated name/module pairs, or raise ``ValueError``.

    Imports come from ``lean_lib`` roots in lakefile.toml, not contract metadata.
    Each operator must name a definition; optional names on node endpoints are
    also checked. ``definition_source_path`` overrides contract ``source_path``.
    No build or evidence update is performed. Run after the caller's successful
    umbrella build. The compiler probe has a 120-second limit and two threads.
    """
    package = Path(lean_package).resolve()
    imports, source_roots = _library_configuration(package)
    paths = list(contract_paths)
    if not paths:
        raise ValueError("no reviewed formula contracts supplied")
    declarations: set[tuple[str, str]] = set()
    for path in paths:
        contract = json.loads(Path(path).read_text())
        if not isinstance(contract, dict):
            raise ValueError(f"invalid reviewed formula contract: {path}")
        _source_module(contract.get("source_path"), package, source_roots)
        endpoint_count = 0
        for category in ("operators", "nodes"):
            rows = contract.get(category, [])
            if not isinstance(rows, list):
                raise ValueError(f"invalid {category} in reviewed formula contract: {path}")
            endpoint_count += len(rows)
            for row in rows:
                if not isinstance(row, dict):
                    raise ValueError(f"invalid endpoint in reviewed formula contract: {path}")
                if category == "nodes" and "lean_definition" not in row:
                    continue
                name = _identifier(row.get("lean_definition"), "contract Lean definition")
                if "." not in name:
                    raise ValueError(f"contract Lean definition must be fully qualified: {name!r}")
                module = _source_module(
                    row.get("definition_source_path", contract["source_path"]), package, source_roots,
                )
                declarations.add((name, module))
        if not endpoint_count:
            raise ValueError(f"reviewed formula contract contains no endpoints: {path}")
    if not declarations:
        raise ValueError("reviewed formula contracts contain no Lean definitions")
    expected = sorted(declarations)
    pairs = ",\n    ".join(f"(`{name}, `{module})" for name, module in expected)
    probe_source = "\n".join("import " + module for module in imports) + "\n" + """import Lean
open Lean Elab Command
run_cmd do
  let env ← getEnv
  let expected : List (Name × Name) := [
    """ + pairs + """
  ]
  for (name, expectedModule) in expected do
    unless env.contains name do
      throwError m!"Contract declaration is absent: {name}"
    let some index := env.getModuleIdxFor? name
      | throwError m!"Contract declaration has no defining module: {name}"
    let actualModule := env.header.moduleNames[index.toNat]!
    unless actualModule == expectedModule do
      throwError m!"Contract declaration {name} belongs to {actualModule}, not {expectedModule}"
  logInfo m!"OMAI_CONTRACT_NAMES_OK|{expected.length}"
"""
    environment = os.environ.copy()
    environment["LEAN_NUM_THREADS"] = "2"
    environment["MATHLIB_NO_CACHE_ON_UPDATE"] = "1"
    scratch = package / ".lake"
    if not scratch.is_dir():
        raise ValueError("Lean package is not built: .lake directory is missing")
    with tempfile.TemporaryDirectory(prefix="contract-names-", dir=scratch) as directory:
        probe = Path(directory) / "ContractNames.lean"
        probe.write_text(probe_source)
        try:
            result = subprocess.run(
                ["lake", "--no-build", "env", "lean", "-j2", str(probe)],
                cwd=package, text=True, capture_output=True, env=environment,
                timeout=_TIMEOUT_SECONDS, check=False,
            )
        except (subprocess.TimeoutExpired, OSError) as error:
            raise ValueError("compiled contract name/module audit could not complete") from error
    output = result.stdout + result.stderr
    if result.returncode:
        raise ValueError("compiled contract name/module audit failed:\n" + output)
    if re.findall(r"OMAI_CONTRACT_NAMES_OK\|(\d+)", output) != [str(len(expected))]:
        raise ValueError("compiled contract name/module audit returned no unique completion marker")
    return [{"name": name, "module": module} for name, module in expected]


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    verified = verify_compiled_contract_names(sorted(root.glob("*-formula-contract.json")), root)
    print(f"Validated {len(verified)} compiled contract name/module pairs (provenance only)")
