"""ase adapter spec for the materials domain: the climbing-image NEB migration
barrier.

The MigrationBarrier node lives in this domain, so its ase spec lives here;
build_codes merges it with the ase specs of the dft ground-state (relaxed
Structure) and thermal-transport (Potential, Trajectory) domains into the one
"ase" representation.

ase.mep.NEB relaxes a band of images between two minima under the attached
calculator. The endpoints must be minima relaxed under the same calculator and
cell. A plain band first, then the climbing image (climb=True), with the
improved-tangent method (method="improvedtangent"): the climbing image is
driven up the band to the saddle. The barrier is the climbing image's energy
minus the initial minimum's. Only a converged climbing run whose highest image
is interior gives this node; the highest image of a converged plain band
underestimates the saddle energy.
"""
from __future__ import annotations

from omai.materials.operator.nodes import MIGRATION_BARRIER
from omai.representation.adapter import SpaceRepresentationSpec

ASE_MIGRATION_BARRIER = SpaceRepresentationSpec(
    space=MIGRATION_BARRIER,
    representation_name="ase",
    observable_units={"E_m": "ev"},
    code_api={
        "E_m": "ase.mep.NEB(images, climb=True, method='improvedtangent') relaxed by an ase.optimize optimizer -> E(climbing image) - E(initial minimum)",
    },
    notes=(
        "Climbing-image nudged elastic band in ase.mep: a plain band, then the "
        "climbing image, improved tangent. E_m is the converged climbing image's "
        "energy minus the initial minimum's, eV; the reverse barrier, from the "
        "final minimum, is the same hop read in the other direction, and the "
        "direction is a condition of the value. Only a converged climbing run "
        "with an interior highest image is this node; the highest image of a "
        "converged plain band underestimates the saddle. The endpoints are "
        "minima relaxed under the same calculator and cell. The calculator (the "
        "Potential), the image count, the spring constant, the optimizer and the "
        "force tolerance fmax are conditions."
    ),
)
