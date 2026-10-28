# Local thermal Gruneisen bridge

This batch adds a compiled, conditional interpretation of the existing `contract_thermal_gruneisen_identity` operator and its `ThermalGruneisen` output. It changes no scientific identity or formula and verifies no mode-Gruneisen or numerical QHA producer.

The bridge now uses [Physlib 9b583cb6ef6e9cc537c4d4b786b508de1abbcf42](https://github.com/leanprover-community/physlib/tree/9b583cb6ef6e9cc537c4d4b786b508de1abbcf42) with Lean 4.35.0. A separate, dependency-only commit moved it from d70acc20: toolchain and Mathlib are unchanged, no cited module changed, and the rebuilt audit of the earlier proofs was unchanged. The historical Lean 4.31 package and earlier proof contracts remain unchanged.

## Result and interpretation

The [endpoint proof](../lean/bridge/OMAIPhyslibThermalGruneisen.lean) identifies the catalog expression with an independently defined quantity of the volume-parameterized ensemble family used for the Cp identity:

```text
gamma_i = -v*omega_i'(v)/omega_i(v)
Gamma   = sum_i gamma_i*c_i / sum_i c_i
Gamma   = alpha_V*K_T/C_V_vol
alpha_V = Vm'(T)/Vm(T),   K_T = Vm*F_VV,   C_V_vol = sum_i c_i/(N_q*v)
```

The [support module](../lean/bridge/OMAIPhyslibModeGruneisen.lean) defines each mode Gruneisen parameter from its frequency derivative and weights it by the actual Physlib canonical heat capacity c_i of that mode at the branch cell volume. Gamma uses no expansion, bulk modulus, branch or free energy; a compiler-backed test checks this dependency closure. The module also proves the fixed-volume relation (dP/dT)_V = Gamma*C_V_vol, which needs no branch; that C_V_vol equals the heat capacity of the actual static-plus-harmonic joint ensemble divided by N_q*v; that expansion and Gamma have the same sign on a stable branch; and that the per-mode heat capacity strictly decreases with frequency at fixed positive temperature.

On a local stable constant-pressure branch, every quantity is evaluated at the same temperature and branch volume, with cell volume v = Vm/N_A for one primitive cell, a fixed q mesh and a single hydrostatic path. Expansion is volumetric and the bulk modulus is isothermal; pairing an adiabatic modulus with C_V_vol would give Gamma*(1+alpha_V*Gamma*T). The weights use angular SI frequency, while mode parameters, as logarithmic derivatives, do not depend on a constant frequency scale. Every mode must have positive frequency; Gamma, gamma_i and alpha_V may be negative; nothing is stated at T = 0.

The [witness module](../lean/bridge/OMAIPhyslibGruneisenWitness.lean) proves exact model examples for every positive molar scale. With heat-capacity arguments hbar*omega/(kB*T) = 1, 2, 3 and mode parameters 1, 2, 3, a stable branch constructed with the implicit function theorem has positive expansion and 1 < Gamma < 2: every weight is positive, and the higher-frequency modes, which carry the larger mode parameters, have smaller heat-capacity weights, so Gamma stays strictly below the arithmetic mean. A negative-rate branch has negative Gamma and negative expansion; both branches hold for every q count. A constant-frequency control with one q point has Gamma and expansion equal to zero. These are exact model examples, not material fits.

The [reviewed endpoint contract](../lean/bridge/thermal-gruneisen-formula-contract.json) and [binding ledger](../omai/data/formula_bindings.json) record these local, same-model hypotheses. FC3 and finite-difference mode-Gruneisen producers, phonopy's fitted thermal-Gruneisen quotient, the opaque `contract_thermal_gruneisen` contraction, numerical QHA, input producers, zero and imaginary modes, nonuniform q, anisotropic strain, phase coexistence and thermodynamic limits are not verified. Neither MCG nor mapengine is changed.

## Coverage

| Measure | Count |
| --- | ---: |
| Existing operator formulas with compiled bridges | 15 / 127 |
| Formula-output quantities covered | 15 |
| Separate retained Temperature interpretation | 1 |
| Quantities referenced, including inputs/concepts | 29 / 129 |
| Binding groups | 23: 18 compiled, 5 source-only |
| Referenced upstream declarations / modules | 33 / 9 |

Only one operator/output proof pair is added. All 14 prior operator/output proof pairs remain. ThermalExpansion, BulkModulus and VolumetricHeatCapacity are input associations, and the support, fixed-volume and witness results do not add to the count. The opaque `contract_thermal_gruneisen` contraction, the numerical Cp route and the molar-volume operator remain gaps. Bidirectional navigation is reference lookup, not an inverse formula.

## Evidence and checks

The [current build record](../lean/bridge/build-evidence.json) binds all 32 source, configuration and contract inputs. The complete build passed 3,892 jobs. Its axiom audit imports all 18 bridge source modules with their private declarations and records 734 theorem declarations and 1,012 total kernel declarations, including generated and private helpers; these are not counts of new formulas or authored proofs. Only `propext`, `Classical.choice` and `Quot.sound` are allowed. All 15 endpoint-definition/module pairs were checked, and a repeated audit produced byte-identical evidence.

The dependency-only repin commit separately passed the full build (3,889 jobs), an unchanged audit (563 theorem declarations, 821 declarations, 14 pairs), the source-reference audit of all 33 upstream anchors, and a type-level recheck of the five classical harmonic-oscillator declarations whose module now imports changed upstream code.

Local checks:

- 241 thermal-Gruneisen and Cp response tests passed with the compiler enabled, none skipped. They include typed canonical consumers; three intended wrong-normalization negatives (molar heat capacity, F_VV in place of the bulk modulus, an unrelated cell volume); a compiler-backed check that Gamma reaches the actual Physlib heat capacity and the frequency derivative but none of the response, free-energy or branch definitions; contract-deletion and evidence-tampering guards; and exact proof-subject and preservation checks. See [the test source](../tests/test_physlib_thermal_gruneisen_contract.py).
- Full offline regression: {FULL_PASSED} passed, {FULL_SKIPPED} skipped, one live API test deliberately deselected.
- All 42 site tests passed.
- A fresh installed wheel passed outside the checkout, including lookup of the new identity and of its unproved sibling operators.
- Package and site binding records are byte-identical. The 129-node and 127-operator scientific inventory is unchanged.
- HTML and the 64-page PDF were regenerated, and the new PDF section was inspected visually. Interactive browser verification was not performed.

These are local results. Remote CI, publication and live deployment are separate states; this report does not claim a merge or deployment. The build record is reproducible provenance, not a signed attestation or a certification of physical-model adequacy or numerical implementation.

From an installed development environment with Python 3.11 or newer, run from the repository root:

```sh
bash lean/bridge/check.sh
python -m omai.formula_bindings --check --physlib-path lean/bridge/.lake/packages/physlib --lean-package lean/bridge
PHYSLIB_BRIDGE_PACKAGE=lean/bridge python -m pytest tests/test_physlib_thermal_gruneisen_contract.py tests/test_physlib_response_contract.py -q -W error
python -m pytest -q -k "not test_golden_acceptance"
```
