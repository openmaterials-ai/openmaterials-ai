# Local quasiharmonic bridge

This batch adds compiled, conditional interpretations of the five quasiharmonic operators `compute_qha_gibbs`, `compute_heat_capacity_p`, `compute_thermal_expansion`, `compute_bulk_modulus_qha` and `contract_thermal_gruneisen`, with their outputs `QHAGibbsEnergy`, `HeatCapacityConstantP`, `ThermalExpansion`, `BulkModulus` and `ThermalGruneisen`. It changes no scientific identity or formula. It uses [Physlib 9b583cb6ef6e9cc537c4d4b786b508de1abbcf42](https://github.com/leanprover-community/physlib/tree/9b583cb6ef6e9cc537c4d4b786b508de1abbcf42) with Lean 4.35.0, the same pin as the Cp and thermal Gruneisen batches. No earlier Lean source or contract changed.

`contract_molar_volume` (V_m = N_A V_cell) is left as a gap on purpose. It is a definition, and a theorem restating it would prove nothing.

## Result and interpretation

The catalog writes the five producers as opaque functions: G^qha(E_tot, S, omega), C_P^qha(G), alpha^qha(G), K^qha(E_tot, S, omega) and gamma^qha(gamma_G, omega). The [endpoint module](../lean/bridge/OMAIPhyslibQHA.lean) gives each a definition that reads only the Gibbs surface or the supplied mode data:

```text
G(T,p)      = inf over V in window I of  F(T,V) + p V
C_P         = -T (d2G/dT2)_p
alpha_V     = (dV/dT)_p / V,   V = (dG/dp)_T
K_T         = V (d2F/dV2)_T  at  V = (dG/dp)_T
gamma_th    = sum_i gamma_i c_i / sum_i c_i,   c_i = Physlib canonical heat capacity of oscillator i
```

F is the actual molar Helmholtz surface of the static-plus-harmonic Physlib ensembles used by the Cp batch. A compiler-backed closure test checks that none of these definitions reaches the branch structures, `expansion`, `bulk`, `cp`, the model free energy or the mode-weighted Gamma that the theorems equate them with.

The [support module](../lean/bridge/OMAIPhyslibGibbsBranch.lean) introduces a two-parameter equilibrium family V(T,p): differentiable near the evaluation point, inside the model domain, F_V(T,V) + p = 0 throughout a neighborhood, and F_VV > 0 at the point. The C1 implicit-function theorem of Mathlib constructs such a family through every stable stationary point. Strict monotonicity of F_V on a box where F_VV > 0, together with the mean value theorem, shows that for every half-width up to a model-dependent bound the family volume is the unique minimizer of F(T,V) + pV on the window, at every (T,p) near the point. The envelope relations (dG/dT)_p = F_T and (dG/dp)_T = V and the compressibility (dV/dp)_T = -1/F_VV follow.

The endpoint theorems, for a window that selects the family:

| Theorem | Statement |
| --- | --- |
| `harmonic_static_qhaGibbs_window` | unique minimizer in every narrow window; windowed G = F(T,V(T,p)) + pV(T,p) near the point |
| `harmonic_static_qhaGibbs_entropy` | (dG/dT)_p = -(N_A/N_q) S_Physlib at the selected volume |
| `harmonic_static_qhaGibbs_volume` | (dG/dp)_T = V |
| `harmonic_static_qhaHeatCapacityP_eq_omai` | -T G_TT = actual molar enthalpy derivative = C_V + T V alpha_V^2 K_T, all from the same G |
| `harmonic_static_qhaHeatCapacityP_gt_iff` | C_V < C_P if and only if alpha_V is nonzero |
| `harmonic_static_qhaThermalExpansion_eq_omai` | alpha_V from G = path expansion = -F_TV / (V F_VV) |
| `harmonic_static_qhaThermalExpansion_pos_iff` | alpha_V > 0 if and only if the mode-weighted Gamma > 0 |
| `harmonic_static_qhaBulkModulus_eq_omai` | V F_VV = -V / (dV/dp)_T from G, and K_T > 0 |
| `harmonic_static_qhaThermalGruneisen_eq_omai` | contraction of the derivative-defined gamma_i = alpha_V K_T / C_V_vol from G |
| `qhaThermalGruneisen_mem_Icc` | for T > 0 the contraction lies between any bounds of the gamma_i |

The [witness module](../lean/bridge/OMAIPhyslibQHAWitness.lean) builds the family with the implicit-function theorem on the signed-rate models of the thermal Gruneisen witness at T = 1 K, p = 0 and V = A, for every positive molar scale A and q count n. On every narrow window around A the positive rates give alpha_V > 0, K_T > 0, C_P > C_V and a contracted Gamma strictly between 1 and 2. The negative rates give alpha_V < 0, K_T > 0, C_P > C_V and Gamma < 0. The constant-frequency control gives alpha_V = 0, C_P = C_V exactly and Gamma = 0. A literal instance with A = 3 and two q points is included. These are exact model examples, not material fits.

## What is not verified

Static-energy, phonon and geometry producers are interpreted inputs. Numerical volume scans, EOS fits (Vinet, Birch-Murnaghan), polynomial and finite-difference derivatives, minimizers and the Phonopy QHA code are not verified. The theorems state what such a producer computes on an exact model, not that a given code does.

The minimization is local. A window wide enough to reach another local minimum can select another branch. Global minimization over all volumes, first-order transitions, phase coexistence, mechanically unstable branches and the T = 0 limit are outside scope.

FC3 (Maradudin-Fein) and finite-difference mode Gruneisen producers, including `compute_gruneisen`, are not shown to equal the derivative-defined gamma_i. Phonopy `gruneisen_temperature` is a fitted quotient and does not consume mode parameters. The `Gruneisen` node remains a gap.

Zero or imaginary modes, Gamma-point acoustic modes, nonuniform or symmetry-reduced q quadrature, q meshes that change with volume, temperature-dependent spectra, anharmonic, electronic and magnetic free energies and anisotropic strain remain outside scope. The adiabatic modulus K_S = K_T C_P/C_V is a different quantity from the K_T output.

## Coverage

| Measure | Before | After |
| --- | ---: | ---: |
| Operator formulas with compiled bridges | 15 / 127 | 20 / 127 |
| Nodes compiled | 16 | 19 |
| Bindings | 23 | 28 |
| Compiled bridges | 18 | 23 |
| Conditional relations | 18 | 23 |
| Contract name pairs | 15 | 20 |
| Audited declarations | 1012 | 1103 |

Upstream declarations referenced stay at 33 in 9 modules: the new bindings cite `CanonicalEnsemble.helmholtzFreeEnergy`, `thermodynamicEntropy`, `meanEnergyT`, `heatCapacity` and `HarmonicOscillator.eigenValue`, all already referenced.

## Verification

| Check | Result |
| --- | --- |
| `lake build --wfail` | passed, 3897 jobs |
| `lean/bridge/audit.py` | passed, 804 theorems / 1103 declarations, only `propext`, `Classical.choice`, `Quot.sound` |
| `python -m omai.formula_bindings --check --physlib-path ... --lean-package lean/bridge` | passed |
| `docs/lean/bridge/lib.test.js` (node 22) | 14 / 14 passed |
| Bridge test files without compiler | 311 passed, 38 skipped (compiler-gated) |

The compiler-backed results and the full suite are recorded in the commit report.

## Prose for site and paper

For the bridge page and the guide: "The local quasiharmonic bridge defines the five QHA producers as functions of the Gibbs surface G(T,p) = inf_V [F(T,V) + pV] of the static-plus-harmonic Physlib ensembles: G itself, C_P = -T (d2G/dT2)_p, alpha_V = (dV/dT)_p/V with V = (dG/dp)_T, the curvature modulus V (d2F/dV2)_T at that volume, and the heat-capacity-weighted mean of mode Gruneisen parameters. On a local stable equilibrium family and every sufficiently narrow volume window, the family volume is the unique minimizer, (dG/dT)_p is minus the actual entropy, C_P is the actual enthalpy derivative and equals C_V + T V alpha_V^2 K_T, alpha_V = -F_TV/(V F_VV), K_T = -V/(dV/dp)_T > 0, and the contraction of the derivative-defined mode parameters equals alpha_V K_T/C_V_vol. Numerical volume scans, EOS fits, minimizers, FC3 and finite-difference Gruneisen producers and Phonopy are not verified."

For `docs/llms.txt`, the formula-bridge line can read: "mapping coverage and gaps, including conditional static-plus-harmonic Cp, thermal Gruneisen and local quasiharmonic Gibbs, C_P, expansion, modulus and Gamma-contraction bridges; compiled model proofs do not verify numerical producers".

For the paper section on the bridge (after the thermal Gruneisen paragraph): "A further batch covers the quasiharmonic producers. The Gibbs energy is the infimum of F(T,V) + pV over a volume window, with F the molar Helmholtz surface of the same ensembles. The C1 implicit-function theorem gives a two-parameter equilibrium family V(T,p) through every stable stationary point, and on every narrow window that family is the unique minimizer. The envelope relations then identify (dG/dT)_p with minus the actual entropy and (dG/dp)_T with V. C_P = -T (d2G/dT2)_p equals the enthalpy derivative of the Cp batch, so C_P = C_V + T V alpha_V^2 K_T holds with all three response quantities read off one Gibbs surface, and C_P > C_V exactly when alpha_V is nonzero. The heat-capacity-weighted contraction of derivative-defined mode Gruneisen parameters equals alpha_V K_T/C_V_vol. Exact witnesses realize positive, negative and zero expansion. Operator coverage rises from 15 to 20 of 127."

For the README coverage sentence: "20 of 127 operator formulas have compiled, conditional Physlib bridges."
