"""List only external cached imports reachable from this bridge's Lean roots."""
from pathlib import Path
import re


def cache_roots(root: Path) -> list[str]:
    packages = root / ".lake/packages"
    search = [root, *sorted(path for path in packages.iterdir() if path.is_dir())]
    seen: set[str] = set()
    cached: set[str] = set()

    def visit(module: str) -> None:
        if module in seen or module.split(".")[0] in {"Lean", "Init", "Std"}:
            return
        seen.add(module)
        if module.split(".")[0] not in {"OMAIPhyslibBridge", "OMAIPhyslibDimensions",
                                       "OMAIPhyslibSemantics", "Physlib"}:
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
    return sorted(cached)


if __name__ == "__main__":
    print("\n".join(cache_roots(Path(__file__).resolve().parent)))
