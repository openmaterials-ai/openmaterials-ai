"""openmaterials-ai: typed operator and representation layers for computational materials science."""

# Read from the installed distribution so this can never disagree with
# pyproject.toml (it sat at 0.0.1 through the 0.1.0 release). The literal is
# the fallback for a source tree that was never installed, and is the one
# place to bump alongside pyproject.
try:  # pragma: no cover - trivial packaging branch
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _dist_version

    __version__ = _dist_version("openmaterials-ai")
except (ImportError, PackageNotFoundError):  # pragma: no cover
    __version__ = "0.1.1"
