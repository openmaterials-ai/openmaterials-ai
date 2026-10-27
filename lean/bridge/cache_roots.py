"""List cached imports needed by the bridge and its source-reference audit."""
import json
from pathlib import Path
import re

# Roots accepted by the pinned Mathlib Cache.IO.isPartOfMathlibCache. Other
# packages (notably Physlib and QuantumInfo) must be traversed and built locally.
CACHED_ROOTS = {
    "Mathlib", "Batteries", "BatteriesRecycling", "Aesop", "Cli", "ImportGraph",
    "LeanSearchClient", "Plausible", "Qq", "ProofWidgets", "Archive",
    "Counterexamples", "Wanted", "MathlibTest", "Requests", "OpenAIClient",
    "Reap", "Canonical", "Duper", "Auto", "PremiseSelection", "Hammer",
}


def cache_roots(root: Path) -> list[str]:
    packages = root / ".lake/packages"
    search = [root, *sorted(path for path in packages.iterdir() if path.is_dir())]
    seen: set[str] = set()
    cached: set[str] = set()

    def visit(module: str) -> None:
        if module in seen or module.split(".")[0] in {"Lean", "Init", "Std"}:
            return
        seen.add(module)
        if module.split(".")[0] in CACHED_ROOTS:
            cached.add(module)
            return
        path = next((base / (module.replace(".", "/") + ".lean") for base in search
                     if (base / (module.replace(".", "/") + ".lean")).exists()), None)
        if path is None:
            raise FileNotFoundError(f"missing bridge import: {module}")
        for match in re.finditer(r"^\s*(?:public\s+)?(?:meta\s+)?import\s+(\S+)",
                                 path.read_text(), re.MULTILINE):
            visit(match[1])

    visit("OMAIPhyslibBridge")
    seeds = json.loads((root.parents[1] / "omai/data/physlib_formula_seeds.json").read_text())
    for binding in seeds["bindings"]:
        for source in binding["sources"]:
            visit(source["module"])
    return sorted(cached)


if __name__ == "__main__":
    print("\n".join(cache_roots(Path(__file__).resolve().parent)))
