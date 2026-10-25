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
- `build-evidence.json`: source and configuration hashes, pinned dependencies,
  and the transitive axiom audit from a build with warnings treated as errors.
  This is a reproducible local build record, not external certification.

From the repository root:

```sh
python3 -m omai.physlib_dimensions
python3 -m pytest tests/test_physlib_dimensions.py -q
bash lean/bridge/check.sh
python3 -m omai.formula_bindings --check --lean-package lean/bridge
```

Use `bash lean/bridge/check.sh --no-cache` when the matching cache is already
present. `check.sh` disables Mathlib's full-cache post-update hook and requests
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
of atoms. This package contains formulas and proofs; operations remain in MCG
and computation in mapengine.
