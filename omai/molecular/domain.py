"""The molecular Domain descriptor."""
from __future__ import annotations

from omai.map_data import Domain
from omai.molecular import representation as molecular_rep
from omai.molecular.operator import EDGES, NODES

SYMBOLS: dict[str, str] = {
    "HOMOLUMOGap": r"E_{gap}^{mol}",
    "ReactionBarrier[construction=neb_mep]": r"E_{barrier}",
    "BondDissociationEnergy": r"E_{BDE}",
    "MolecularFrequency": r"\nu_{\mathrm{mol}}",
    "IdealGasMolarHeatCapacityP": r"C_{p}^{\mathrm{ig}}",
    "IdealGasMolarHeatCapacityP[approximation=qrrho]": r"C_{p}^{\mathrm{qRRHO}}",
    "InfraredIntensity": r"A_{\mathrm{IR}}",
    "MolecularReactionEnthalpy": r"\Delta_{r} H",
}

MOLECULAR = Domain(
    name="molecular",
    nodes=NODES,
    edges=EDGES,
    symbols=SYMBOLS,
    param_promotions=(),
    tiers=(
        (
            "Molecular",
            "Molecular quantum chemistry and reaction energetics: orbital "
            "gaps, reaction barriers, and bond dissociation.",
        ),
    ),
    representation_package=molecular_rep,
)
