"""Audit imported bridge-source declarations and their transitive axioms after a build.

Writes evidence only when the exact compiled source/configuration bytes remain
unchanged, the library target is up to date, and only standard logical axioms
occur. The local build record is provenance, not a signed attestation.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


_IDENTIFIER = r"(?:[^\W\d]|_)[\w']*(?:\.(?:[^\W\d]|_)[\w']*)*"
_AXIOM_SCOPE = "source_modules_union_namespace_v1"
_NAMESPACE_PREFIX = "OMAI.PhyslibBridge"


def _module_names(values: list[str], label: str) -> list[str]:
    if not isinstance(values, list) or not values:
        raise ValueError(f"{label} must be a nonempty list")
    if any(not isinstance(value, str) or not re.fullmatch(_IDENTIFIER, value)
           for value in values):
        raise ValueError(f"unsupported Lean name in {label}")
    if len(values) != len(set(values)):
        raise ValueError(f"duplicate Lean name in {label}")
    return sorted(values)


def _lean_source_paths() -> list[Path]:
    sources = []
    for directory, subdirectories, filenames in os.walk(ROOT, followlinks=False):
        subdirectories[:] = sorted(name for name in subdirectories if name != ".lake")
        sources.extend(Path(directory) / name for name in filenames if name.endswith(".lean"))
    return sorted(sources)


def axiom_probe_source(*, imports: list[str], source_modules: list[str]) -> str:
    # Deliberately non-module: load all private imported kernel declarations.
    roots = _module_names(imports, "audit imports")
    modules = _module_names(source_modules, "audited source modules")
    header = "\n".join("import " + name for name in roots)
    if "Lean" not in roots:
        header += "\nimport Lean"
    body = """
open Lean Elab Command
run_cmd do
  let env := (← getEnv).setExporting false
  let sourceModules : List Name := [__SOURCE_MODULES__]
  for moduleName in sourceModules do
    let some index := env.getModuleIdx? moduleName
      | throwError m!"Missing audited source module: {moduleName}"
    let effective := env.header.modules[index.toNat]!
    unless effective.hasData && effective.importAll do
      throwError m!"Audited source module lacks full private data: {moduleName}"
    logInfo m!"OMAI_AXIOM_MODULE|{moduleName}"
  let mut selected : Nat := 0
  for (name, info) in env.constants.toList do
    let owned := match env.getModuleIdxFor? name with
      | some index => sourceModules.contains env.header.moduleNames[index.toNat]!
      | none => false
    if owned || (__NAMESPACE_PREFIX__).isPrefixOf name then
      let axioms ← collectAxioms name
      let kind := if info.isTheorem then "theorem" else "definition"
      logInfo m!"OMAI_AXIOMS|{kind}|{name}|{String.intercalate "," (axioms.toList.map Name.toString)}"
      selected := selected + 1
  logInfo m!"OMAI_AXIOM_SCOPE_OK|{sourceModules.length}|{selected}"
"""
    body = body.replace("__SOURCE_MODULES__", ", ".join(chr(96) + name for name in modules))
    body = body.replace("__NAMESPACE_PREFIX__", chr(96) + _NAMESPACE_PREFIX)
    return header + "\n" + body


def parse_axiom_output(text: str, *, source_modules: list[str]) -> dict:
    expected = _module_names(source_modules, "audited source modules")
    modules = re.findall(r"OMAI_AXIOM_MODULE\|([^|\s]+)[ \t]*$", text, re.MULTILINE)
    if (modules != expected or len(modules) != len(set(modules))
            or text.count("OMAI_AXIOM_MODULE|") != len(modules)):
        raise ValueError("axiom audit source-module markers are missing, duplicated or mismatched")
    completed = re.findall(r"OMAI_AXIOM_SCOPE_OK\|(\d+)\|(\d+)[ \t]*$", text, re.MULTILINE)
    if len(completed) != 1 or text.count("OMAI_AXIOM_SCOPE_OK|") != 1:
        raise ValueError("axiom audit lacks exactly one scope-completion marker")
    outputs = re.findall(r"OMAI_AXIOMS\|(theorem|definition)\|([^|\s]+)\|([^\n]*)", text)
    by_name = {name: sorted(part.strip() for part in axioms.split(",") if part.strip())
               for _kind, name, axioms in outputs}
    theorem_count = sum(kind == "theorem" for kind, _name, _axioms in outputs)
    if (not theorem_count or len(outputs) != len(by_name)
            or text.count("OMAI_AXIOMS|") != len(outputs)):
        raise ValueError("axiom audit output is empty, malformed or duplicates declarations")
    if tuple(map(int, completed[0])) != (len(expected), len(by_name)):
        raise ValueError("axiom audit completion counts do not match modules and declarations")
    for name, axioms in by_name.items():
        if set(axioms) - ALLOWED_AXIOMS:
            raise ValueError(f"unapproved transitive axioms in {name}: {axioms}")
    return {"status": "passed", "theorem_count": theorem_count,
            "declaration_count": len(by_name), "allowed_axioms": sorted(ALLOWED_AXIOMS),
            "declarations": dict(sorted(by_name.items())), "scope": _AXIOM_SCOPE,
            "source_modules": expected, "namespace_prefix": _NAMESPACE_PREFIX}


def run() -> dict:
    lean_sources = _lean_source_paths()
    contracts = sorted(ROOT.glob("*-formula-contract.json"))
    required_contracts = {
        "semantic-formula-contract.json", "continuum-formula-contract.json",
        "harmonic-ensemble-formula-contract.json", "harmonic-sums-formula-contract.json",
        "harmonic-product-formula-contract.json", "harmonic-density-formula-contract.json",
        "joint-density-formula-contract.json", "response-formula-contract.json",
        "thermal-gruneisen-formula-contract.json",
    }
    missing = required_contracts - {path.name for path in contracts}
    if missing:
        raise ValueError("reviewed formula contracts are missing: " + ", ".join(sorted(missing)))
    tracked = [*lean_sources, ROOT / "lean-toolchain", ROOT / "lakefile.toml",
               ROOT / "lake-manifest.json", ROOT / "audit.py", ROOT / "verify_contracts.py", *contracts]
    hashes = {str(path.relative_to(REPO)): digest(path) for path in tracked}
    subprocess.run(["lake", "--no-build", "build", "--wfail"], cwd=ROOT, check=True)
    verifier_spec = importlib.util.spec_from_file_location(
        "omai_bridge_contract_names", ROOT / "verify_contracts.py")
    verifier = importlib.util.module_from_spec(verifier_spec)
    verifier_spec.loader.exec_module(verifier)
    verified_names = verifier.verify_compiled_contract_names(contracts, ROOT)
    imports, source_roots = verifier._library_configuration(ROOT)
    source_modules = [verifier._source_module(str(path.relative_to(REPO)), ROOT, source_roots)
                      for path in lean_sources]
    probe = ROOT / ".lake" / "AxiomAudit.lean"
    probe.write_text(axiom_probe_source(imports=imports, source_modules=source_modules))
    environment = dict(os.environ)
    environment.update(LEAN_NUM_THREADS="2", MATHLIB_NO_CACHE_ON_UPDATE="1")
    result = subprocess.run(
        ["lake", "--no-build", "env", "lean", "-j2", "-DwarningAsError=true", str(probe)],
        cwd=ROOT, check=True, text=True, capture_output=True, env=environment, timeout=120)
    audit = parse_axiom_output(result.stdout + result.stderr, source_modules=source_modules)
    if any(digest(REPO / path) != sha for path, sha in hashes.items()):
        raise ValueError("bridge inputs changed during axiom audit")
    manifest = json.loads((ROOT / "lake-manifest.json").read_text())
    dependencies = {p["name"].lower(): p["rev"] for p in manifest["packages"]}
    for package in manifest["packages"]:
        directory = ROOT / ".lake" / "packages" / package["name"]
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=directory,
                                  check=True, capture_output=True, text=True).stdout.strip()
        if revision != package["rev"]:
            raise ValueError(f"dependency checkout differs from manifest: {package['name']}")
        subprocess.run(["git", "diff", "--quiet", "HEAD", "--"], cwd=directory, check=True)
    evidence = {"schema_version": 1, "status": "passed", "command": "lake build --wfail",
                "upstream_revision": dependencies["physlib"],
                "lean_toolchain": (ROOT / "lean-toolchain").read_text().strip(),
                "dependencies": dependencies, "dependency_sources_clean": True, "sources": hashes,
                "contract_name_audit": {"status": "passed", "pairs": verified_names,
                                        "pair_count": len(verified_names)},
                "axiom_audit": audit,
                "scope": "ISQ dimension encodings and explicitly stated bridge theorems; not numerical-code validation"}
    (ROOT / "build-evidence.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(f"Axiom audit passed for {audit['theorem_count']} theorems / "
          f"{audit['declaration_count']} declarations")
    return evidence


if __name__ == "__main__":
    run()
