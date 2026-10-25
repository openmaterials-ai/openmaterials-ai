# OMAI–Physlib formula bridge: reviewed delivery

Reviewed 2026-10-25. This is OMAI-only formula/metadata work, not a simulation,
Physlib contribution, downstream repair, or live website deployment.

## Source boundaries

- OMAI base/current upstream: `5628fd068c033fe764d971c54c15a92d553b1c14`.
- Physlib current source: `8ddcc004043c5b537e4225fa763121c176b62a4a`;
  current bridge toolchain Lean 4.35.0. Both remote heads were rechecked before delivery.
- Historical `lean/` package retains Physlib `a74414af9cf713084dd59943fa706980cb7573de`
  and Lean 4.31.0. Historical proof sources, generators, dependency pins and
  recorded scientific evidence are unchanged. Their results do not validate the
  current package.

## Coverage and precise claims

| Coverage axis | Result |
|---|---:|
| Catalog inventory | 129 quantities / 127 actual operators |
| Reviewed correspondence groups | 16 |
| Quantities with a correspondence | 21 / 129 |
| Operators with a correspondence | 10 / 127 |
| Compiled Physlib binding groups | 3 |
| Source-only binding groups | 13 |
| ISQ dimension fields encoded | 126 / 131, across 124 / 129 nodes |
| Opaque fields explicitly excluded | 5 |

Relations are separately classified: one exact-definition, ten conditional,
and five conceptual groups. Referenced/mapped coverage is **not** proved coverage.
The inventory includes eight source/no-input operators that graph links omit.
All 13 OMAI domains were inspected; unmatched formulas carry explicit bounded
source-audit gap reasons instead of speculative matches.

Compiled bindings cover scalar power factor, isotropically interpreted total
thermal conductivity, and scalar/isotropic zT. Their ten supporting theorems
include upstream positivity/monotonicity transfer and explicit tensor embedding.
Four additional harmonic theorems establish physical argument validity and the
closed-form identity `F = U - T*S`. The latter is **not** an oscillator-ensemble
identification and is not counted among the three compiled Physlib bindings.

Current build evidence audits 281 definitions/theorems, including 145 theorem
declarations: 126 dimension witnesses, fourteen user-written semantic/domain
theorems, and five Lean-generated helpers. Only standard logical axioms
`propext`, `Classical.choice`, and `Quot.sound` are permitted. No `sorryAx` or
custom unapproved axiom is accepted. This is reproducible local provenance,
not a signed external attestation.

## Collaborating review and fixes

Principal software, principal HPC, and mathematics AI-agent reviewers shared
findings and cross-reviewed the implementation; an independent final mathematical
review approved the scoped source/evidence claims. These are assigned agent
review roles, not claims of external human certification.

Resolved issues include:

- Historical website renderer dropped every array-valued crosswalk entry.
- Graph-derived inventories omitted zero-input operators; resolver operator UIDs
  were null because it read the wrong graph key.
- Reviewed source mappings must pin the original scientific UID/formula hash;
  regeneration now refuses changed endpoints until explicit re-review.
- Compiled claims require matching complete local proof/config/endpoint hashes,
  frozen dependencies and the successful full compiled-environment axiom audit.
- Generic ensemble definitions cannot establish per-mode harmonic identification.
  Stored linear THz requires `omega_SI = 2*pi*10^12*nu_THz`; cell/molar bases,
  energy references, positivity and tensor conventions remain explicit.
- Historical SI-to-SI scale evidence does not prove all stored numbers are SI.

The six-formula semantic endpoint contract binds manually reviewed OMAI formulas
and exact Lean source bytes. It detects drift; it is not a general automatic
SymPy-to-Lean translator.

## Validation

- Full offline Python suite: **2,624 passed, 97 skipped, 1 deselected**.
  Live API acceptance was excluded; optional data/dependency checks retain
  their existing guards. No simulation or paid compute was launched.
- Installed wheel, isolated interpreter outside checkout: registry/record
  checks and package-owned formula lookup passed without `docs/data`.
- Current Lean package: `lake build --wfail` and complete transitive axiom audit
  passed; selected-cache reproducibility check passed.
- Pinned Physlib declaration/source audit and strict compiled-provenance
  validation passed. Generator outputs match committed package/site data.
- Fourteen focused dimension/site checks, document regeneration checks and
  twelve JS logic tests passed. All changed inline scripts parse.
- Thirteen baseline identity/lineage contract hashes unchanged. No scientific
  node/operator definitions, map ledger, graph/version fields or canonical
  vectors changed. Resolver metadata now reports already-existing correct UIDs.
- Specification HTML and PDF regenerated; website map, verified layer, current
  bridge inventory, guide, machine-readable references and README updated.
- Browser localhost navigation was denied by browser policy. Visual interaction
  was **not verified**; static, link, syntax and presentation-logic checks passed.

The independent current CI lane builds/audits Lean, compares deterministic
build evidence, checks source pins and runs the bridge/semantic-contract tests.
Historical CI remains separate. Local passes are not claims about remote CI.

## Reproduction

```sh
python -m omai.physlib_dimensions
python -m omai.formula_bindings --check --physlib-path /path/to/pinned/physlib
python -m pytest tests/test_formula_bindings.py tests/test_physlib_dimensions.py tests/test_physlib_semantic_contract.py -q
bash lean/bridge/check.sh
node --test docs/lean/lib.test.js docs/lean/bridge/lib.test.js
```

See `lean/bridge/build-evidence.json`, `semantic-formula-contract.json`, and the
packaged/site `formula_bindings.json` for machine-readable pins, assumptions,
obligations and evidence. Scientific identity remains owned by OMAI, computation
by mapengine, and operations by MCG.

## Remaining scientific work

Construct and evaluate the countably infinite harmonic oscillator ensemble;
prove partition summability, energy integrability and derivative interchange;
identify entropy/energy/heat capacity and their temperature derivatives; lift
through the actual mesh and normalization conventions. Existing generic
ensemble links remain candidates until those obligations are discharged.
Transport, QHA, CALPHAD, empirical device, composite and cure-model gaps must not
be filled merely by matching names or dimensions.
