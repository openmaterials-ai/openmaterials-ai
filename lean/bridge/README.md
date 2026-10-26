# Current Physlib bridge

This independent Lean 4.35 package pins Physlib
`8ddcc004043c5b537e4225fa763121c176b62a4a`. The historical Lean 4.31 package in
the parent directory is unchanged and builds separately.

- `OMAIPhyslibDimensions.lean`: generated native seven-base ISQ encodings for
  every dimension-bearing catalog field, including promoted parameters. Opaque
  dimensions are omitted. These **dimension witnesses** do not establish unit
  conversions, model adequacy, formula equality, or numerical-code correctness.
- `OMAIPhyslibSemantics.lean`: scalar and isotropic thermoelectric formulas and
  harmonic closed-form consistency, under the documented model, normalization,
  frequency, and operating-point assumptions.
- `OMAIPhyslibHarmonicEnsemble.lean`: the full Nat-spectrum oscillator ensemble,
  partition and energy sums, finiteness and integrability, and identification of
  the OMAI F/U/S/C formulas. Fixed-spectrum derivatives and the sinh form of heat
  capacity are proved on the positive-temperature domain.
- `OMAIPhyslibHarmonicSums.lean`: four finite uniform-q molar contractions of the
  proved single-mode quantities, with exactly `3*N_atoms` branches. These are
  normalized sums, not a construction of a joint product ensemble.
- `OMAIPhyslibHarmonicProduct.lean`: the heterogeneous full-Nat joint ensemble,
  partition factorization, actual F/U/S/C, and the four molar endpoints. Its
  rectangular occupation reindexing preserves the measure and Hamiltonian.
- `OMAIPhyslibHarmonicDensity.lean` and `OMAIPhyslibJointDensity.lean`: volumetric
  heat capacity with positive primitive-cell volume, its molar relation, and
  the same formula from the actual joint ensemble. Exact real unit lemmas do
  not certify floating-point conversion code.
- `OMAIPhyslibContinuum.lean`: absolute-temperature round trips and beta unit
  scaling; signed three-dimensional inviscid stress and pressure contraction.
- `*-formula-contract.json`: separately reviewed OMAI endpoint identities and
  source hashes. New proofs do not rewrite the historical six-formula contract.
- `build-evidence.json`: source and configuration hashes, pinned dependencies,
  and the transitive axiom audit from a build with warnings treated as errors.
  This is a reproducible local build record, not external certification.

Use the project environment (Python 3.11 or newer). From the repository root:

```sh
python3 -m omai.physlib_dimensions
python3 -m pytest tests/test_physlib_dimensions.py -q
bash lean/bridge/check.sh
python3 -m omai.formula_bindings --check --lean-package lean/bridge
```

Use `bash lean/bridge/check.sh --no-cache` when the matching cache is already
present. Set `PYTHON` to the environment interpreter if `python3` is older.
`check.sh` disables Mathlib's full-cache post-update hook and requests
only external imports reachable from the bridge. It builds only this library,
then audits every public theorem and rejects any transitive axiom outside
`propext`, `Classical.choice`, `Quot.sound` (in particular `sorryAx`).

The source-reference audit builds the mapped Physlib modules and checks each
fully qualified declaration name and defining module in Lean's compiled
environment. This validates references, not OMAI formula equivalence. It does
not add to the bridge's theorem or mapping counts. The read-only
`--physlib-path /path/to/pinned/physlib` option checks the pinned files and
declaration lines without compiling Lean.

The operator layer is unit-free. Canonical numeric frequency representations use
linear THz; the harmonic symbolic angular frequency requires
`omega_SI = 2*pi*10^12*nu_linear_THz`. Dimension equality does not prove that
factor. Harmonic molar results use moles of primitive cells, not CALPHAD's moles
of atoms. Every mode must have strictly positive frequency; an unmodified Gamma
grid with zero acoustic modes does not meet the premises. This package contains formulas and proofs; operations remain in MCG
and computation in mapengine.

The package audit checks each Lean endpoint definition named in the reviewed
contracts against its fully qualified name and actual defining module. A product
proof can refer to an unchanged endpoint in the earlier sum module. The audit
records these name/module pairs and hashes its validation scripts; these checks
establish provenance, not scientific interpretation.
