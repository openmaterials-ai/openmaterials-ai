"""Result renderers: a typed stage result -> a map evidence instance.

Moved here from MCG so the rendering rule lives once, beside the identity it is
rendered against.

The bytes these functions emit are the ones the PLATFORM SERVED. The move in
0.1.0 took MCG's Python ``render.py`` as its source, but the records the
platform actually served were rendered by the worker's TypeScript renderer
(``platform/worker/src/services/record.ts``, ``kappaInstanceFrom``), and the
two differ. 0.1.2 makes these functions reproduce the worker's bytes, because
the served record is the truth a consumer verifies against:

- ``run_ref`` is OPTIONAL. A public share page deliberately carries no run
  identity, so the served ``source.ref`` is the bare provider
  ("materialscodegraph") and the ``detail`` names no run. Passing a
  ``run_ref`` keeps the older, run-identified form for a caller that wants it.
- ``uncertainty`` is emitted only for a spread strictly greater than zero. A
  single-seed run reports ``kappa_std = 0``, which is not a claim of
  exactness, so the key is ABSENT and the detail prints "+/- None".

The one deliberate change is the INPUT type. MCG passed its own pydantic
result models (KappaResult, MolecularThermoResult, ReactionThermoResult) and
read the map version off its own manifest loader; neither exists here. Each
renderer now takes a plain mapping (a dict, or any object exposing the same
fields via attributes: a dataclass, a pydantic model, a SimpleNamespace) with
exactly the fields the old model carried, listed per function below, and the
map version is passed in explicitly. A caller holding the old pydantic object
passes it directly; a caller holding parsed JSON passes the dict.

Every instance pins the map version it was rendered against in source.detail,
per the commons' provenance rule.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# 1 eV = 96.48533212331 kJ/mol (CODATA 2018: N_A * e, exact SI constants).
KJ_PER_MOL_PER_EV = 96.48533212331

# KappaResult.method -> map node (only the methods the map models today).
# The two BTE solvers (bte_rta / bte_direct_inverse) map onto the commons' own
# bte_solver nodes. Consumers mirroring this table (the MCG worker's KAPPA_NODE)
# read it from here.
KAPPA_NODE = {
    "hnemd": "ThermalConductivity[transport_model=hnemd]",
    "green_kubo": "ThermalConductivity[transport_model=green_kubo]",
    "bte_rta": "ThermalConductivity[bte_solver=rta]",
    "bte_direct_inverse": "ThermalConductivity[bte_solver=direct_inverse]",
}

# The map version stamped when a caller names none. An instance must state what
# it was rendered against; "unknown" says so plainly instead of implying a pin.
UNKNOWN_MAP_VERSION = "unknown"

# Who holds the bytes and mints the citation. The worker's MIRROR_PROVIDER.
MIRROR_PROVIDER = "materialscodegraph"


@dataclass
class Source:
    """Where an evidence value came from."""

    kind: str  # "simulation" | "measurement"
    ref: str
    detail: str

    def to_json_dict(self) -> dict:
        return {"kind": self.kind, "ref": self.ref, "detail": self.detail}


@dataclass
class Instance:
    """One evidence value, the docs/data/instances/*.json shape."""

    variable: str
    material: str
    conditions: dict
    units: str
    source: Source
    value: float | None = None
    uncertainty: float | None = None
    #: The raw run artifact this instance is evidenced by, for nodes with no
    #: single scalar (a DOS, a force-constant file, a linewidth table).
    artifact: str | None = None

    def filename(self) -> str:
        """``<material>-<variable>-<ref>.json``, the map's kebab convention."""
        return (f"{slugify(self.material)}-{slugify(self.variable)}-"
                f"{slugify(self.source.ref)}.json")

    def to_json_dict(self) -> dict:
        """Plain dict in the map's key order.

        ``value``, ``uncertainty`` and ``artifact`` are omitted when None, so
        the document is byte-identical to the served one and gains no key it
        never had.
        """
        d: dict = {
            "variable": self.variable,
            "material": self.material,
            "conditions": self.conditions,
        }
        if self.value is not None:
            d["value"] = self.value
        d["units"] = self.units
        # Omitted when there is no spread to report, matching the served
        # records (the worker spreads the key only for a positive std). A
        # `"uncertainty": null` would be a different document.
        if self.uncertainty is not None:
            d["uncertainty"] = self.uncertainty
        if self.artifact is not None:
            d["artifact"] = self.artifact
        d["source"] = self.source.to_json_dict()
        return d


def slugify(text: str) -> str:
    """Lowercase kebab: non-alphanumeric runs collapse to single hyphens."""
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


def kj_per_mol_to_ev(kj_per_mol: float) -> float:
    """Molar energy (kJ/mol) to energy per event (eV)."""
    return kj_per_mol / KJ_PER_MOL_PER_EV


def provenance(run_ref: str | None = None, what: str = "", *,
               map_version: str = UNKNOWN_MAP_VERSION) -> Source:
    """The source block every rendered instance carries.

    ``what`` is the sentence fragment naming the quantity, ending in "from a",
    which this completes with the map version pin and, when a ``run_ref`` is
    given, the run reference.

    With NO ``run_ref`` (the default, and what the platform serves) the ref is
    the bare provider and the detail names no run: a public share page carries
    no run identity. With one, both fields identify the run.
    """
    if run_ref is None:
        return Source(
            kind="simulation",
            ref=MIRROR_PROVIDER,
            detail=f"{what} MaterialsCodeGraph run; "
                   f"rendered against openmaterials map version {map_version}.",
        )
    return Source(
        kind="simulation",
        ref=f"{MIRROR_PROVIDER}-{slugify(run_ref)}",
        detail=f"{what} MaterialsCodeGraph run {run_ref}; "
               f"rendered against openmaterials map version {map_version}.",
    )


def _get(result, name, default=None):
    """One field of a result, whether it is a mapping or an object."""
    if isinstance(result, dict):
        return result.get(name, default)
    return getattr(result, name, default)


def render_kappa(result, *, run_ref: str | None = None,
                 potential: str | None = None,
                 map_version: str = UNKNOWN_MAP_VERSION) -> Instance:
    """Bulk thermal conductivity onto the method-specific map node.

    ``result`` carries ``method``, ``material_name``, ``temperature_K``,
    ``n_seeds``, ``code``, ``kappa_W_per_mK`` and ``kappa_std_W_per_mK`` (the
    fields of MCG's KappaResult).

    Raises KeyError for a method the map does not model (e.g. nemd): silently
    rerouting a method to the wrong node would be a provenance lie.
    """
    method = _get(result, "method")
    material_name = _get(result, "material_name")
    temperature_K = _get(result, "temperature_K")
    kappa = _get(result, "kappa_W_per_mK")
    kappa_std = _get(result, "kappa_std_W_per_mK")
    node = KAPPA_NODE[method]
    conditions: dict = {
        "T": f"{temperature_K:g} K",
        "method": method,
        "n_seeds": _get(result, "n_seeds"),
        # The engine that ACTUALLY ran (GPUMD for hnemd/gk, ASE for the
        # bulk_kappa fallback). Defaults to "GPUMD", so an older kappa.json with
        # no `code` field still renders code="GPUMD".
        "code": _get(result, "code", "GPUMD") or "GPUMD",
    }
    if potential:
        conditions["potential"] = potential
    # A spread of 0 (a single-seed run computed none) is not exactness: the
    # key is dropped and the detail says "None", which is what was served.
    has_std = isinstance(kappa_std, (int, float)) and not isinstance(
        kappa_std, bool) and kappa_std > 0
    std_text = f"{kappa_std}" if has_std else "None"
    return Instance(
        variable=node,
        material=material_name,
        conditions=conditions,
        value=kappa,
        units="W/(m K)",
        uncertainty=kappa_std if has_std else None,
        source=provenance(
            run_ref,
            f"Bulk {material_name} kappa ({method.upper()}, "
            f"{kappa} +/- {std_text} W/(m K) "
            f"at {temperature_K:g} K, {_get(result, 'n_seeds')} seed(s)) from a",
            map_version=map_version,
        ),
    )


def render_molar_cp(result, *, run_ref: str | None = None, at_K: float = 300.0,
                    material_label: str | None = None,
                    map_version: str = UNKNOWN_MAP_VERSION) -> Instance:
    """Gas-phase harmonic molar heat capacity at one grid temperature.

    ``result`` carries ``cp_temperatures_K``, ``cp_harmonic_J_per_molK``,
    ``molecule_name`` and ``n_imaginary`` (MCG's MolecularThermoResult).
    """
    grid = list(_get(result, "cp_temperatures_K") or [])
    molecule_name = _get(result, "molecule_name")
    try:
        i = grid.index(at_K)
    except ValueError:
        raise ValueError(
            f"{at_K} K is not on the Cp grid "
            f"({grid[0]}..{grid[-1]} K); "
            "pick a grid temperature: interpolating silently would misstate "
            "what was computed") from None
    cp = _get(result, "cp_harmonic_J_per_molK")[i]
    n_imaginary = _get(result, "n_imaginary")
    return Instance(
        variable="MolarHeatCapacity",
        material=material_label or molecule_name,
        conditions={
            "T": f"{at_K:g} K",
            "phase": "gas",
            "approximation": "harmonic (RRHO)",
            "model": "GFN2-xTB",
            "n_imaginary": n_imaginary,
        },
        value=cp,
        units="J/(K mol)",
        uncertainty=None,
        source=provenance(
            run_ref,
            f"Gas-phase harmonic molar heat capacity of {molecule_name} "
            f"at {at_K:g} K ({cp} J/(K mol), GFN2-xTB, "
            f"{n_imaginary} imaginary modes) from a",
            map_version=map_version,
        ),
    )


def render_reaction_energy(result, *, run_ref: str | None = None,
                           material: str = "",
                           reaction: str | None = None,
                           map_version: str = UNKNOWN_MAP_VERSION) -> Instance:
    """Reaction enthalpy dH(298 K) in eV per reaction event.

    The map's plain-energy convention; the molar figure rides in conditions.
    ``result`` carries ``dh298_kJ_per_mol``, ``de_elec_kJ_per_mol`` and
    ``reaction_name`` (MCG's ReactionThermoResult).
    """
    dh298 = _get(result, "dh298_kJ_per_mol")
    reaction_name = _get(result, "reaction_name")
    dh_ev = round(kj_per_mol_to_ev(dh298), 6)
    return Instance(
        variable="ReactionEnergy",
        material=material,
        conditions={
            "T": "298.15 K",
            "reaction": reaction or reaction_name,
            "normalization": "per_reaction_event",
            "quantity": "reaction enthalpy dH(298 K)",
            "dh298_kJ_per_mol": dh298,
            "de_elec_kJ_per_mol": _get(result, "de_elec_kJ_per_mol"),
            "model": "GFN2-xTB",
            "phase": "gas",
        },
        value=dh_ev,
        units="eV",
        uncertainty=None,
        source=provenance(
            run_ref,
            f"Reaction enthalpy dH(298 K) of {reaction or reaction_name} "
            f"({dh298} kJ/mol = {dh_ev} eV per reaction "
            "event, GFN2-xTB) from a",
            map_version=map_version,
        ),
    )
