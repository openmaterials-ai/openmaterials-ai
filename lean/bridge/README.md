# Current Physlib bridge

This independent Lean 4.35 package pins Physlib
`8ddcc004043c5b537e4225fa763121c176b62a4a`. The historical Lean 4.31 package in
the parent directory remains a separate, unchanged proof lane.

- `OMAIPhyslibDimensions.lean`: generated native seven-base ISQ encodings for
  every dimension-bearing catalog field, including promoted parameters. Opaque
  dimensions are explicitly omitted. These are **dimension witnesses**, not unit
  conversions, model adequacy, formula equality or numerical-code validation.
- `OMAIPhyslibSemantics.lean`: precisely scoped scalar/isotropic thermoelectric
  interpretations and harmonic closed-form consistency. The documented model,
  normalization, frequency and operating-point assumptions remain essential.
- `build-evidence.json`: exact source/config hashes, frozen dependencies and the
  transitive axiom audit from a successful no-warning build. It is reproducible
  local provenance, not a signed proof-service attestation.

From the repository root:

```sh
python3 -m omai.physlib_dimensions
python3 -m pytest tests/test_physlib_dimensions.py -q
bash lean/bridge/check.sh
```

Use `bash lean/bridge/check.sh --no-cache` when the matching cache is already
present. `check.sh` disables Mathlib's full-cache post-update hook and requests
only external imports reachable from the bridge. It builds only this library,
then audits every public theorem and rejects any transitive axiom outside
`propext`, `Classical.choice`, `Quot.sound` (in particular `sorryAx`).

The operator layer is unit-free. Canonical numeric frequency representations use
linear THz; the harmonic symbolic angular frequency requires
`omega_SI = 2*pi*10^12*nu_linear_THz`. Dimension equality does not prove that
factor. Harmonic molar results use moles of primitive cells, not CALPHAD's moles
of atoms. No MCG or mapengine execution responsibility moves into this package.
