"""openmaterials-ai's own evaluator of compute_harmonic_migration_prefactor
(omai.materials.evaluate): the library is the code that ran.

  operator Space                           omai function                                       unit
  ---------------------------------------  --------------------------------------------------  ----------
  MigrationPrefactor[method=harmonic_tst]  omai.materials.evaluate.harmonic_migration_prefactor  linear THz

The normal modes come from another code (a finite-difference Hessian of a
potential); the Vineyard ratio and its validity checks come from this function,
so a record credits both.
"""
from __future__ import annotations

from omai.materials.operator.edges import compute_harmonic_migration_prefactor
from omai.materials.operator.nodes import MIGRATION_PREFACTOR
from omai.representation.adapter import (
    OperatorRepresentationSpec,
    SpaceRepresentationSpec,
)

OMAI_MIGRATION_PREFACTOR = SpaceRepresentationSpec(
    space=MIGRATION_PREFACTOR,
    representation_name="openmaterials-ai",
    observable_units={"nu_star": "linear_THz"},
    code_api={"nu_star": "omai.materials.evaluate.harmonic_migration_prefactor(freqs_min_THz, freqs_saddle_THz, floor_THz, projected=..., residual_force_eV_per_A=(min, saddle), translational_THz=..., eigenvalue_noise_THz2=...)"},
    notes=(
        "The Vineyard ratio nu* of the real modes at the minimum and the saddle, "
        "a sum of logarithms, in linear THz from cyclic inputs; the classical "
        "high-temperature limit, with no zero-point or Wigner correction. It "
        "refuses a minimum with an imaginary or soft mode, a saddle without "
        "exactly one imaginary mode, real counts that do not differ by one, "
        "projected translations above half the imaginary-mode floor, and a "
        "residual force (ase fmax) above 0.05 eV/A by default, a convention that "
        "does not guarantee stationarity for soft modes. projected and the "
        "residual forces are required. A subset value (projected=False) "
        "approximates the full ratio. With the eigenvalue noise it returns "
        "ln_nu_star_error_bound, an upper bound on |delta ln nu*| valid to all "
        "orders when every eigenvalue moves by at most eps, "
        "which excludes finite-difference truncation, anharmonicity, the "
        "residual force and the subset approximation. The floor, M and the atom "
        "set, the residual forces and the bound are conditions of every value."
    ),
)

OMAI_COMPUTE_HARMONIC_MIGRATION_PREFACTOR = OperatorRepresentationSpec(
    operator=compute_harmonic_migration_prefactor,
    representation_name="openmaterials-ai",
    discretization_choices={
        "imaginary_floor": "floor_THz, the band within which a mode counts as soft; a condition of the value.",
        "stationarity": "max_residual_force_eV_per_A = 0.05 eV/A by default, a keyword of the function and a condition of the value.",
    },
    notes="harmonic_migration_prefactor returns the value, the mode counts, the imaginary mode and the crossover temperature in one call.",
)
