# OMAI–Physlib formula mapping report

Reviewed 2026-10-25. These changes add formula mappings, proofs, and documentation
to OMAI. They do not change Physlib, MCG, or mapengine, run simulations, or deploy
the website.

## Source revisions

- OMAI base/current upstream: `5628fd068c033fe764d971c54c15a92d553b1c14`.
- Physlib: `8ddcc004043c5b537e4225fa763121c176b62a4a`, with Lean 4.35.0.
  Both remote heads were rechecked before delivery.
- The historical `lean/` package retains Physlib
  `a74414af9cf713084dd59943fa706980cb7573de` and Lean 4.31.0. Its proof sources,
  generators, dependency pins, and recorded scientific evidence are unchanged.
  The current package is built and checked separately.

## Coverage

| Coverage | Result |
|---|---:|
| Catalog inventory | 129 quantities / 127 operators |
| Reviewed correspondence groups | 16 |
| Quantities with a correspondence | 21 / 129 |
| Operators with a correspondence | 10 / 127 |
| Compiled Physlib binding groups | 3 |
| Source-only binding groups | 13 |
| Quantities in compiled binding groups | 4 / 129 |
| Operators in compiled binding groups | 3 / 127 |
| ISQ dimension fields encoded | 126 / 131, across 124 / 129 nodes |
| Opaque fields excluded | 5 |

Relations are classified separately from proof status: one exact-definition,
ten conditional, and five conceptual groups. A correspondence is **not**
necessarily a proved equivalence. The inventory includes eight source/no-input
operators omitted from graph links. All 13 OMAI domains were inspected; each
unmatched formula has a reason explaining the gap in the reviewed source.

Compiled bindings cover scalar power factor, isotropically interpreted total
thermal conductivity, and scalar/isotropic zT. Their ten supporting theorems
include upstream positivity and monotonicity results and explicit isotropic
tensor embeddings. Four additional harmonic theorems establish positive
arguments and the closed-form identity `F = U - T*S`. This identity does **not**
identify the formulas with an oscillator ensemble and is not counted among the
three compiled Physlib bindings.

The build audit covers 281 definitions/theorems, including 145 theorem
declarations: 126 dimension witnesses, fourteen user-written semantic/domain
theorems, and five Lean-generated helpers. The only permitted axioms are
`propext`, `Classical.choice`, and `Quot.sound`; `sorryAx` and custom axioms are
rejected. This is a reproducible local build record, not external certification.

## Review and fixes

AI-agent reviewers assigned principal software, principal HPC, and mathematics
roles shared findings and cross-reviewed the changes. An independent final
mathematics agent checked the claims against their sources and proofs. These
are agent reviews, not external human certification.

The review found and resolved these issues:

- The historical website renderer dropped array-valued crosswalk entries.
- Graph-derived inventories omitted zero-input operators. The resolver read the
  wrong graph key, leaving operator UIDs null.
- Regeneration could silently update a reviewed mapping after its scientific
  endpoint changed. It now rejects changed UIDs and formula hashes until review.
- Compiled claims now require matching proof, configuration, and endpoint hashes,
  pinned dependencies, and a successful compiled-environment axiom audit.
- Generic ensemble definitions do not identify per-mode harmonic formulas.
  The records specify cell/molar bases, energy references, positivity, and tensor
  conventions. Stored linear THz requires `omega_SI = 2*pi*10^12*nu_THz`.
- The historical SI-to-SI scale theorem does not prove that all stored values
  are in SI units.
- The source-line audit checked only the last component of a declaration name.
  A new compiled audit checks the full name and its defining module. This checks
  references; it does not turn source-only mappings into formula proofs.

The six-formula semantic contract pins the reviewed OMAI formulas and exact Lean
source bytes. It detects changes; it is not an automatic SymPy-to-Lean translator.

## Validation

- Full offline Python suite: **2,624 passed, 99 skipped, 1 deselected**.
  The live API acceptance test was excluded. Optional data/dependency checks
  retain their existing guards. No simulation or paid compute was launched.
- The installed wheel passed registry/record checks and formula lookup in an
  isolated interpreter outside the checkout, without `docs/data`.
- The current Lean package passed `lake build --wfail`, the transitive axiom
  audit, and a reproducibility check using only the required cached imports.
- The pinned Physlib source audit and build-record checks passed. Generated
  outputs match the committed package and website data.
- The compiled source audit checked all 27 declaration names across nine modules.
  Twenty-five focused tests passed, including rejection of a nonexistent
  namespace and a wrong defining module.
- Fourteen focused dimension/site checks, document regeneration checks, and
  twelve JS logic tests passed. All changed inline scripts parse.
- Thirteen baseline identity/lineage contract hashes are unchanged. Scientific
  node/operator definitions, the map ledger, graph/version fields, and canonical
  vectors are unchanged. Resolver metadata now reports the correct existing UIDs.
- Specification HTML and PDF were regenerated. Updates also cover the map,
  historical verified layer, bridge inventory, guide, machine-readable
  references, and README.
- Browser policy denied localhost navigation, so visual interaction was
  **not verified**. Static, link, syntax, and presentation-logic checks passed.

The current package's CI workflow builds Lean, audits axioms, compares generated
build records, checks source pins, and runs bridge/semantic-contract tests.
Historical CI is separate. The results above are from local checks, not remote CI.

## Reproduction

```sh
python -m omai.physlib_dimensions
python -m omai.formula_bindings --check --physlib-path /path/to/pinned/physlib
python -m omai.formula_bindings --check --lean-package lean/bridge
python -m pytest tests/test_formula_bindings.py tests/test_physlib_dimensions.py tests/test_physlib_semantic_contract.py -q
bash lean/bridge/check.sh
node --test docs/lean/lib.test.js docs/lean/bridge/lib.test.js
```

The [build record](https://github.com/openmaterials-ai/openmaterials-ai/blob/1a382762b5eb6f0a82bdfe3c18eda3f94a720b44/lean/bridge/build-evidence.json),
[formula/source contract](https://github.com/openmaterials-ai/openmaterials-ai/blob/1a382762b5eb6f0a82bdfe3c18eda3f94a720b44/lean/bridge/semantic-formula-contract.json),
and [mapping records](https://github.com/openmaterials-ai/openmaterials-ai/blob/837a09a7408a592d285742419fdc144f4d1ea88c/omai/data/formula_bindings.json)
list dependency pins, assumptions, remaining proofs, and build results.
OMAI defines formulas, MCG handles operations, and mapengine performs computation.

## Remaining scientific work

Construct and evaluate the countably infinite harmonic oscillator ensemble;
prove partition summability and energy integrability; justify temperature derivatives;
identify entropy, energy, heat capacity, and their temperature derivatives;
and apply the actual mesh and normalization conventions. Generic ensemble links
remain candidates until these steps are proved.

Transport, QHA, CALPHAD, empirical device, composite, and cure-model gaps require
more than matching names or dimensions.
