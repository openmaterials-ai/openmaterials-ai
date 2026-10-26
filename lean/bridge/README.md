# Current Physlib bridge

This independent Lean 4.35 package pins Physlib
`9b583cb6ef6e9cc537c4d4b786b508de1abbcf42`. The historical Lean 4.31 package in
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
- `OMAIPhyslibStaticEnsemble.lean` and `OMAIPhyslibResponseUnits.lean`: an actual
  signed static-energy singleton, F/U shifts and S/Cv invariance, with cell/molar
  derivative scalings and non-unit normalization controls.
- `OMAIPhyslibResponseCalculus.lean` and `OMAIPhyslibHarmonicVolume.lean`: local
  C2 response calculus and its identification with a volume-dependent actual
  static-plus-harmonic ensemble. Cp is an enthalpy derivative, not the desired
  response formula by definition.
- `OMAIPhyslibResponseWitness.lean` and `OMAIPhyslibHarmonicResponse.lean`: an
  explicit heterogeneous nonzero-expansion example, a separate zero-response
  control, and the catalog Cp identity and inequality. These cover one operator
  and its output, not the numerical QHA producer or its input producers.
- `OMAIPhyslibContinuum.lean`: absolute-temperature round trips and beta unit
  scaling; signed three-dimensional inviscid stress and pressure contraction.
- `*-formula-contract.json`: separately reviewed OMAI endpoint identities and
  source hashes. All eight contracts are required by the audit. New proofs do
  not rewrite the historical six-formula contract.
- `build-evidence.json`: source and configuration hashes, pinned dependencies,
  and the transitive axiom audit from a build with warnings treated as errors.
  This is a reproducible local build record, not external certification.

Use the project environment (Python 3.11 or newer). From the repository root:

```sh
python3 -m omai.physlib_dimensions
python3 -m pytest tests/test_physlib_dimensions.py -q
bash lean/bridge/check.sh
python3 -m omai.formula_bindings --check --lean-package lean/bridge
PHYSLIB_BRIDGE_PACKAGE=lean/bridge python3 -m pytest tests/test_physlib_response_contract.py -q
```

Use `bash lean/bridge/check.sh --no-cache` when the matching cache is already
present. Set `PYTHON` to the environment interpreter if `python3` is older.
`check.sh` disables Mathlib's full-cache post-update hook and requests
only external imports reachable from the bridge. It builds only this library,
then audits imported kernel declarations owned by every bridge source module,
plus the existing bridge namespace. This includes private and generated helpers.
The audit requires every source module to be reachable with full private data;
its probe deliberately uses non-module imports for that visibility. It rejects
any transitive axiom outside `propext`, `Classical.choice`, `Quot.sound`
(in particular `sorryAx`). Expanded audit counts are not counts of new formulas.

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
