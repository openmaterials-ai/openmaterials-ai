# Historical Lean export (physlib)

This package retains the reviewed Physlib revision
`a74414af9cf713084dd59943fa706980cb7573de` and Lean 4.31.0. It is a
compatibility target, not the current upstream API. The additive
[current formula bridge](bridge/README.md) uses its own dependency pins and
build evidence; the historical proofs do not validate that newer package.

`lean/` is a standalone lake package (`openmaterials`, library `OpenMaterials`)
holding the map's generated proof layer. It depends on
[physlib](https://github.com/leanprover-community/physlib) (the successor of
PhysLean), pinned by rev in `lakefile.toml`, on toolchain
`leanprover/lean4:v4.31.0` (`lean-toolchain`). Mathlib comes in transitively
through physlib and is fetched from the mathlib build cache.

Generated modules (do not edit by hand; regenerate with
`python -m omai.map_data`, or the individual exporters):

- `OpenMaterials.lean` (Tier 1, `omai.physlean_export`): each node is a physlib
  `Dimension`; each theorem states that an edge's output dimension equals the
  product of its input dimensions, proved by extensionality plus `simp` with
  physlib's `*_mul` lemmas.
- `OpenMaterialsDimensions.lean` (Tier 1 companion, `omai.physlean_export`):
  the map's full seven-base dimension vector (`Dimension7`: M, L, T, Th, N, I,
  J) with its own ext lemma and Mul instance, covering exactly the nodes the
  physlib bridge omits, Mathlib only.
- `OpenMaterialsIdentities.lean` (Tier 2, `omai.lean_identities`): the
  executable identities as real-valued composition theorems, Mathlib only
  (`ring` / `field_simp`).
- `OpenMaterialsUnits.lean` (`omai.lean_units`): the units bridge, anchoring
  the map's SI-canonical convention against physlib's `UnitChoices.dimScale`.

The historical units theorem proves the generic SI-to-SI scale identity.
It does **not** establish that all stored OMAI values are SI numbers: canonical
representations include linear THz and angstrom-derived units. See the current
bridge's explicit unit and angular-frequency interpretation requirements.

**Verified.** The package builds against physlib with zero errors and zero
sorries. `tests/test_physlean_export.py` re-checks every Tier 1 identity in
Python so a regression fails fast even without a Lean toolchain.

To build:

```
cd lean
lake exe cache get   # fetch the mathlib build cache (first build only)
lake build
```

or `bash lean/check.sh` (pass `--no-cache` to skip the cache fetch, e.g. in CI
with a warm `.lake`).

Scope (Tier 1): the dimensional layer only. Nodes whose dimension uses
amount-of-substance (mole), current, or luminous intensity are omitted from
this historical physlib bridge, since its pinned `Dimension` has five bases
(length, time, mass, charge, temperature). Current Physlib already provides
the seven-base `ISQDimensionBase`, used by `bridge/`; no upstream dimension
extension is needed. Historically omitted nodes are covered by the Mathlib-only seven-base module
`OpenMaterialsDimensions.lean` instead.
