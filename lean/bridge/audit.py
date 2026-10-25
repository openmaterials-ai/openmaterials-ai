"""Audit every new public theorem's transitive axioms after a real Lake build.

Writes evidence only when the exact compiled source/configuration bytes remain
unchanged, the library target is up to date, and only standard logical axioms
occur. The local build record is provenance, not a signed attestation.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run() -> dict:
    lean_sources = sorted(ROOT.glob("*.lean"))
    contracts = sorted(ROOT.glob("*-formula-contract.json"))
    required_contracts = {
        "semantic-formula-contract.json", "continuum-formula-contract.json",
        "harmonic-ensemble-formula-contract.json", "harmonic-sums-formula-contract.json",
        "harmonic-product-formula-contract.json", "harmonic-density-formula-contract.json",
        "joint-density-formula-contract.json",
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
    probe = ROOT / ".lake" / "AxiomAudit.lean"
    # Enumerate the compiled environment, not a source regex: attributes,
    # sections, generated helpers and future names cannot evade the audit.
    # This is the same native Lean API used by `#print axioms`.
    probe.write_text('''import OMAIPhyslibBridge
import Lean
open Lean Elab Command
run_cmd do
  let env ← getEnv
  for (name, info) in env.constants.toList do
    if (`OMAI.PhyslibBridge).isPrefixOf name then
      let axioms ← collectAxioms name
      let kind := if info.isTheorem then "theorem" else "definition"
      logInfo m!"OMAI_AXIOMS|{kind}|{name}|{String.intercalate "," (axioms.toList.map Name.toString)}"
''')
    result = subprocess.run(["lake", "env", "lean", str(probe)], cwd=ROOT,
                            check=True, text=True, capture_output=True)
    text = result.stdout + result.stderr
    outputs = re.findall(r"OMAI_AXIOMS\|(theorem|definition)\|([^|\s]+)\|([^\n]*)", text)
    by_name = {name: sorted(part.strip() for part in axioms.split(",") if part.strip())
               for _kind, name, axioms in outputs}
    theorem_count = sum(kind == "theorem" for kind, _name, _axioms in outputs)
    if not theorem_count or len(outputs) != len(by_name):
        raise ValueError("axiom audit output is empty or duplicates declarations: " + text)
    for name, axioms in by_name.items():
        if set(axioms) - ALLOWED_AXIOMS:
            raise ValueError(f"unapproved transitive axioms in {name}: {axioms}")
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
                "axiom_audit": {"status": "passed", "theorem_count": theorem_count,
                                "declaration_count": len(by_name),
                                "allowed_axioms": sorted(ALLOWED_AXIOMS),
                                "declarations": by_name},
                "scope": "ISQ dimension encodings and explicitly stated bridge theorems; not numerical-code validation"}
    (ROOT / "build-evidence.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(f"Axiom audit passed for {theorem_count} theorems / {len(by_name)} declarations")
    return evidence


if __name__ == "__main__":
    run()
