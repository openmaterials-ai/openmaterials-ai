# Local quasiharmonic bridge

This batch adds compiled, conditional interpretations of the five quasiharmonic operators `compute_qha_gibbs`, `compute_heat_capacity_p`, `compute_thermal_expansion`, `compute_bulk_modulus_qha` and `contract_thermal_gruneisen`. The proof subjects are the five operators and the outputs `QHAGibbsEnergy`, `HeatCapacityConstantP`, `ThermalExpansion` and `ThermalGruneisen`. `BulkModulus` is an output association only, because the catalog defines that node as the Voigt average of the elastic tensor. The batch changes no scientific identity or formula and uses [Physlib 9b583cb6ef6e9cc537c4d4b786b508de1abbcf42](https://github.com/leanprover-community/physlib/tree/9b583cb6ef6e9cc537c4d4b786b508de1abbcf42) with Lean 4.35.0, the same pin as the Cp and thermal Gruneisen batches. It is rebased on the single-package cleanup (602c0d1). No earlier Lean source or contract changed.

`contract_molar_volume` (V_m = N_A V_cell) is left as a gap on purpose. It is a definition, and a theorem restating it would prove nothing.

## Result and interpretation

The catalog writes the five producers as opaque functions: G^qha(E_tot, S, omega), C_P^qha(G), alpha^qha(G), K^qha(E_tot, S, omega) and gamma^qha(gamma_G, omega). The [endpoint module](../lean/bridge/OMAIPhyslibQHA.lean) defines them as follows:

```text
G(T,p)      = inf over V in window I of  F(T,V) + p V
C_P         = -T (d2G/dT2)_p
alpha_V     = (dV/dT)_p / V,   V = (dG/dp)_T
K_T         = V (d2F/dV2)_T  at  V = (dG/dp)_T      (the mirror of the Phonopy EOS B0)
gamma_th    = sum_i gamma_i c_i / sum_i c_i,   c_i = Physlib canonical heat capacity of oscillator i
```

F is the actual molar Helmholtz surface of the static-plus-harmonic Physlib ensembles used by the Cp batch. The producers read G for V, alpha_V and C_P, and the curvature F_VV at the volume dG/dp for K_T. A compiler-backed closure test checks that no producer definition reaches the branch structures, `expansion`, `bulk`, `cp`, the model free energy, the mode-weighted Gamma or any private helper. That check is syntactic. For K_T and the Gamma contraction it shows only a different spelling of V F_VV and of the existing weighted mean, not an independent route.

The [support module](../lean/bridge/OMAIPhyslibGibbsBranch.lean) introduces a two-parameter equilibrium family V(T,p): differentiable near the evaluation point, inside the model domain, F_V(T,V) + p = 0 throughout a neighborhood, and F_VV > 0 at the point. The C1 implicit-function theorem of Mathlib constructs such a family through every stable stationary point. On any open volume interval inside the domain where F(T,.) is strictly convex, a stationary point of F(T,V) + pV is its unique minimizer, by strict monotonicity of F_V and the mean value theorem. The envelope relations (dG/dT)_p = F_T and (dG/dp)_T = V and the compressibility (dV/dp)_T = -1/F_VV follow.

The cited theorems, for a window that selects the family:

| Theorem | Statement |
| --- | --- |
| `harmonic_static_qhaGibbs_convex_window` | on any open interval (a,b) containing V(T,p), inside the domain, with F_VV(T,.) > 0 for all T near the point: V is the unique minimizer and the windowed G equals F(T,V) + pV near the point |
| `harmonic_static_qhaGibbs_entropy` | (dG/dT)_p = -(N_A/N_q) times the Physlib thermodynamic entropy of the ensemble at the selected volume |
| `harmonic_static_qhaGibbs_volume` | (dG/dp)_T = V |
| `harmonic_static_qhaHeatCapacityP_eq_omai` | -T G_TT = actual molar enthalpy derivative = C_V + T V alpha_V^2 K_T, all from the same G |
| `harmonic_static_qhaHeatCapacityP_eq_entropy_slope` | -T G_TT = C_V + T (dV/dT)_p (dS/dV)_T, with the Maxwell relation (dS/dV)_T = -F_TV = alpha_V K_T |
| `harmonic_static_qhaHeatCapacityP_gt_iff` | C_V < C_P if and only if alpha_V is nonzero |
| `harmonic_static_qhaThermalExpansion_eq_omai` | alpha_V from G = path expansion = -F_TV / (V F_VV) |
| `harmonic_static_qhaThermalExpansion_pos_iff` | alpha_V > 0 if and only if the mode-weighted Gamma > 0 |
| `harmonic_static_qhaBulkModulus_eq_omai` | V F_VV at the volume dG/dp = -V / (dV/dp)_T from G alone |
| `harmonic_static_qhaThermalGruneisen_eq_omai` | contraction of the derivative-defined gamma_i = alpha_V K_T / C_V_vol, with alpha_V and K_T from G |
| `HarmonicVolumeModel.freeEnergy_eq_actual` | (cited by the expansion and modulus bindings) the model surface F is (N_A/N_q) times the Physlib Helmholtz free energy of the ensemble |

The Gamma contraction is the existing mode-weighted Gamma spelled over supplied mode data, so its theorem is a corollary of the thermal Gruneisen identity (3f970d6). What is new is the interpretation of the opaque producer and the Gibbs-surface reading of alpha_V and K_T. K_T > 0 is the stability premise F_VV > 0 and is not claimed as a result. The small-window theorem `harmonic_static_qhaGibbs_window`, the weighted-mean bounds `qhaThermalGruneisen_mem_Icc` and the unfolding `qhaBulkModulus_eq_bulk` are proved but not cited.

The [witness module](../lean/bridge/OMAIPhyslibQHAWitness.lean) builds the family with the implicit-function theorem on the signed-rate models of the thermal Gruneisen witness at T = 1 K, p = 0 and V = A, for every positive molar scale A and q count n. On every narrow window around A the positive rates give alpha_V > 0, C_P > C_V and a contracted Gamma strictly between 1 and 2. The negative rates give alpha_V < 0, C_P > C_V and Gamma < 0. The constant-frequency control gives alpha_V = 0, C_P = C_V exactly and Gamma = 0. A literal instance with A = 3 and two q points is included. These are exact model examples, not material fits.

## Conditions a producer must meet

A scan certifies its own window by the convexity of F + pV across the scanned interval, and the selected volume must lie strictly inside the scanned range; EOS extrapolation beyond the scanned volumes is not covered. The modulus is taken along the model's single hydrostatic volume coordinate: a fixed-shape lattice scan of a non-cubic crystal gives a fixed-shape modulus, and a shape-relaxed path a Reuss-type modulus. The J/mol embedding uses N_A = 6.02214076e23 mol^-1; G and C_P scale with it, while alpha_V, K_T and Gamma do not. The weights use Physlib's CODATA hbar 1.054571817e-34 J s and exact kB.

A producer must reject any imaginary mode at every scanned volume, not only at the selected one. Gamma-point acoustic modes are excluded; a shifted mesh without the Gamma point meets the premises. For polar materials the Born charges and eps_inf of the nonanalytic correction must be recomputed at every volume. The static energy E(V) and the phonon free energy must refer to the same cell at every volume.

The theorems hold for any T > 0 with F_VV > 0, including temperatures where the quasiharmonic approximation is physically unreliable, such as strong anharmonicity near melting or soft-mode transitions. They are statements about the model, not about its adequacy.

## What is not verified

Static-energy, phonon and geometry producers are interpreted inputs. Numerical volume scans, EOS fits (Vinet, Birch-Murnaghan), polynomial and finite-difference derivatives, minimizers and the Phonopy QHA code are not verified. The catalog default `polyfit_enthalpy_derivative` (Phonopy `heat_capacity_P_polyfit`) evaluates C_V(V_eq) + T (dV/dT)_p (dS/dV)_T with polynomial fits; the theorem proves that expression equals -T G_TT on the exact model, not that the fits reproduce it. The finite-difference sibling `heat_capacity_P_numerical` is not verified either.

The minimization is local. A window that reaches another local minimum can select another branch. Global minimization over all volumes, first-order transitions, phase coexistence, mechanically unstable branches and the T = 0 limit are outside scope.

FC3 (Maradudin-Fein) and finite-difference mode Gruneisen producers, including `compute_gruneisen`, are not shown to equal the derivative-defined gamma_i, and gammas evaluated at the reference geometry differ from gammas at the selected volume. Phonopy `gruneisen_temperature` is a fitted quotient and does not consume mode parameters. The `Gruneisen` node remains a gap.

Nonuniform or symmetry-reduced q quadrature, q meshes that change with volume, temperature-dependent spectra, anharmonic, electronic and magnetic free energies and anisotropic strain remain outside scope. The adiabatic modulus K_S = K_T C_P/C_V is a different quantity from the K_T output.

## Coverage

| Measure | Before (602c0d1) | After |
| --- | ---: | ---: |
| Operator formulas with compiled bridges | 15 / 127 | 20 / 127 |
| Nodes compiled | 16 | 18 |
| Nodes mapped | 29 | 30 |
| Bindings | 23 | 28 |
| Compiled bridges | 18 | 23 |
| Conditional relations | 18 | 23 |
| Contract name pairs | 15 | 20 |
| Audited theorems / declarations | 608 / 886 | 691 / 990 |

Upstream declarations referenced stay at 33 in 9 modules: the new bindings cite `CanonicalEnsemble.helmholtzFreeEnergy`, `thermodynamicEntropy`, `meanEnergyT`, `heatCapacity` and `HarmonicOscillator.eigenValue`, all already referenced. The roadmap marks the five QHA rows proven; all five are rated "na" (external code outputs), and their reasons now say that a compiled bridge proves statements about an interpreted definition of them under stated conditions.

## Verification

| Check | Result |
| --- | --- |
| `lake build --wfail` | passed, 3897 jobs |
| `lean/bridge/audit.py` | passed, 691 theorems / 990 declarations, only `propext`, `Classical.choice`, `Quot.sound` |
| `python -m omai.formula_bindings --check --physlib-path ... --lean-package lean/bridge` | passed |

The test results are recorded in the commit report.

## Prose for site and paper

For the bridge page and the guide: "The local quasiharmonic bridge defines the five QHA producers from the Gibbs surface G(T,p) = inf_V [F(T,V) + pV] of the static-plus-harmonic Physlib ensembles: G itself, C_P = -T (d2G/dT2)_p, alpha_V = (dV/dT)_p/V with V = (dG/dp)_T, the curvature modulus V (d2F/dV2)_T at that volume, and the heat-capacity-weighted mean of mode Gruneisen parameters. On a local stable equilibrium family and any volume window across which F + pV is convex, the family volume is the unique minimizer, (dG/dT)_p is -(N_A/N_q) times the ensemble entropy, C_P is the actual enthalpy derivative and equals both C_V + T V alpha_V^2 K_T and C_V + T (dV/dT)_p (dS/dV)_T, alpha_V = -F_TV/(V F_VV), and K_T = -V/(dV/dp)_T. The Gamma contraction of the derivative-defined mode parameters equals alpha_V K_T/C_V_vol, a corollary of the thermal Gruneisen identity. Numerical volume scans, EOS fits, minimizers, FC3 and finite-difference Gruneisen producers and Phonopy are not verified."

For `docs/llms.txt`, the formula-bridge line can read: "mapping coverage and gaps, including conditional static-plus-harmonic Cp, thermal Gruneisen and local quasiharmonic Gibbs, C_P, expansion, modulus and Gamma-contraction bridges; compiled model proofs do not verify numerical producers".

For the paper section on the bridge (after the thermal Gruneisen paragraph): "A further batch covers the quasiharmonic producers. The Gibbs energy is the infimum of F(T,V) + pV over a volume window, with F the molar Helmholtz surface of the same ensembles. The C1 implicit-function theorem gives a two-parameter equilibrium family V(T,p) through every stable stationary point, and on any window across which F + pV is convex that family is the unique minimizer, so a volume scan certifies its own window. The envelope relations identify (dG/dT)_p with -(N_A/N_q) times the ensemble entropy and (dG/dp)_T with V. C_P = -T (d2G/dT2)_p equals the enthalpy derivative of the Cp batch and C_V + T (dV/dT)_p (dS/dV)_T, the form evaluated by the default polyfit estimator, with the Maxwell relation (dS/dV)_T = -F_TV = alpha_V K_T. C_P > C_V exactly when alpha_V is nonzero. The modulus V F_VV at the selected volume equals -V/(dV/dp)_T read off G. Exact witnesses realize positive, negative and zero expansion. Operator coverage rises from 15 to 20 of 127."

For the README coverage sentence: "20 of 127 operator formulas have compiled, conditional Physlib bridges."
