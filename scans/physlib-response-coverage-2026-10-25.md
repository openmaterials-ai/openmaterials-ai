# Local constant-pressure heat-capacity bridge

This batch adds a compiled, conditional interpretation of the existing `contract_heat_capacity_p_identity` operator and its `HeatCapacityConstantP` output. It changes no scientific identity or formula and verifies no numerical QHA producer.

The independent bridge uses [Physlib d70acc20677320d37b38e602e331e900466b704d](https://github.com/leanprover-community/physlib/tree/d70acc20677320d37b38e602e331e900466b704d) with Lean 4.35.0. The historical Lean 4.31 package and earlier proof contracts remain unchanged.

## Result and interpretation

The [endpoint proof](../lean/bridge/OMAIPhyslibHarmonicResponse.lean) identifies the catalog expression with an independently defined response of a volume-parameterized family of canonical ensembles:

```text
Cp = d[U_mol(T, Vm(T)) + p*Vm(T)]/dT
Cp - Cv = T*Vm*alpha_V^2*K_T
alpha_V = Vm′/Vm,   K_T = Vm*F_VV
```

The [actual volume family](../lean/bridge/OMAIPhyslibHarmonicVolume.lean) uses a finite, fixed uniform reduced-q grid, full Nat oscillator occupations, positive frequencies and temperature, and a primitive-cell molar basis. Frequency curves are C2 functions of positive cell volume; the signed C2 static energy has no independent temperature dependence. The [singleton static factor](../lean/bridge/OMAIPhyslibStaticEnsemble.lean) contributes `Nq*E0` before external `NA/Nq` normalization. Zero-point terms are retained.

The [local calculus](../lean/bridge/OMAIPhyslibResponseCalculus.lean) derives mixed symmetry and differentiates neighborhood equilibrium. Positive isothermal curvature is required at the evaluation state. Cp, Cv, expansion, volume and bulk modulus must refer to the same potential and branch; a tuple of unrelated producer values does not meet that interpretation. The [coordinate lemmas](../lean/bridge/OMAIPhyslibResponseUnits.lean) and model specialization give `F_mol(T,V)=NA*f_cell(T,V/NA)`, with no extra NA factor in pressure or bulk modulus.

The [witness module](../lean/bridge/OMAIPhyslibResponseWitness.lean) proves two actual-model examples for every positive molar scale. A heterogeneous exponential spectrum and fixed quadratic static energy admit an IFT-constructed branch with positive expansion and actual Cp greater than Cv at the reference state. A separate constant-frequency model has zero expansion and Cp equal to Cv. These are exact toy models, not material fits; the general result is Cp greater than or equal to Cv, not a universal strict gap.

The [reviewed endpoint contract](../lean/bridge/response-formula-contract.json) and [binding ledger](../omai/data/formula_bindings.json) retain the local, scalar, same-model hypotheses and exact-real SI interpretations. Numerical QHA/EOS fits, minimizers, finite-difference or polynomial derivatives, input producers, independently defined thermal Gruneisen agreement, zero/imaginary modes, explicit-temperature spectra, nonuniform q, phase coexistence and thermodynamic limits are not verified. Neither MCG nor mapengine is changed.

## Coverage

| Measure | Count |
| --- | ---: |
| Existing operator formulas with compiled bridges | 14 / 127 |
| Formula-output quantities covered | 14 |
| Separate retained Temperature interpretation | 1 |
| Quantities referenced, including inputs/concepts | 28 / 129 |
| Binding groups | 22: 17 compiled, 5 source-only |
| Referenced upstream declarations / modules | 33 / 9 |

Only one operator/output proof pair is added. All 13 prior operator subjects remain; supporting static, calculus, unit and witness results do not inflate that count. The numerical `compute_heat_capacity_p` route and Gruneisen producers remain gaps. Bidirectional navigation is reference lookup, not an inverse formula.

## Evidence and checks

The [current build record](../lean/bridge/build-evidence.json) binds all 28 source/configuration/contract inputs. The complete build passed 3,889 jobs. Its strengthened axiom audit covers all 15 bridge source modules with full private import visibility, selecting module-owned declarations together with the bridge namespace. It records 563 theorem declarations and 821 total kernel declarations, including generated/private helpers; these are not counts of new formulas or authored proofs. Only `propext`, `Classical.choice` and `Quot.sound` are allowed. A repeat produced byte-identical evidence. All 14 endpoint-definition/module pairs were checked.

Local checks:

- 157 response tests passed, none skipped: seven typed canonical consumers, two intended type-mismatch negatives, five real compiler audit-scope cases, contract deletion and evidence-tampering guards, exact proof-subject scope and preservation checks. See [the test source](../tests/test_physlib_response_contract.py).
- 69 retained targeted tests passed with compiler/reference checks enabled.
- Full offline regression: 2,830 passed, 96 skipped, one live API test deliberately deselected.
- All 41 site tests passed, including the actual Cp identity/output route and refusal to badge its numerical sibling.
- A fresh installed wheel passed outside the checkout, including forward/reverse Cp lookup and the unproved numerical sibling.
- Package/site binding JSONs are byte-identical. The 129-node/127-operator inventory and all 31 retained scientific/historical baseline files are unchanged.
- HTML and the 64-page PDF were regenerated; the new PDF discussion and equation were visually inspected. Interactive browser verification of this snapshot was not performed.

These are local results. Remote CI, publication and live deployment are separate states; this report does not claim a merge or deployment. The build record is reproducible provenance, not a signed attestation or certification of physical-model adequacy or numerical implementation.

From the repository root, with development dependencies installed and Python 3.11 or newer:

```sh
bash lean/bridge/check.sh
python -m omai.formula_bindings --check --physlib-path lean/bridge/.lake/packages/physlib --lean-package lean/bridge
PHYSLIB_BRIDGE_PACKAGE=lean/bridge python -m pytest tests/test_physlib_response_contract.py -q -W error
python -m pytest -q -k "not test_golden_acceptance"
```
