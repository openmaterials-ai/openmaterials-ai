# Local atomistic-derivative proofs

This batch proves, over Mathlib, statements about seven catalog formulas that are derivatives of one energy: Hellmann-Feynman forces, the cell stress, the second- and third-order force constants, the finite-displacement force constant, the elastic constants, and the molecular normal-mode frequencies. Physlib has no model of an interatomic potential, a deformed cell or a molecular energy surface, so all six bindings are `local`: they cite no Physlib declaration and are counted apart from the Physlib-anchored results. No catalog formula, description or identity is changed.

## Results

| Binding | Operators | Cited theorems |
| --- | --- | --- |
| `hellmann-feynman-force-balance` | `compute_forces_hf` | `hfForce_sum_eq_zero`: for an energy invariant under rigid translations, `sum_i F_{i alpha} = 0`. `hfForce_torque_eq_zero`: for an energy invariant under rotations in the `(alpha, beta)` plane, `sum_i (R_{i alpha} F_{i beta} - R_{i beta} F_{i alpha}) = 0`. `pairEnergy_force`: the two-atom energy `abs(R_1 - R_0)^2` meets both hypotheses with force 2. |
| `cell-stress-rotation-balance` | `compute_stress_cell` | `cellStress_rotation_balance`: for a cell energy of the deformation gradient invariant under rotations, `sum_b sigma_{alpha b} F_{beta b} = sum_b sigma_{beta b} F_{alpha b}`; at `F = 1` the stress is symmetric. |
| `force-constant-sum-rules` | `compute_force_constants[order=2]`, `[order=3]` | `forceConstant2_sum_eq_zero` and `forceConstant3_sum_eq_zero`: the acoustic sum rules from translation invariance alone. `forceConstant3_symm`: full permutation symmetry for a potential `C^3` at the reference. `pairEnergy_forceConstant2`: the pair energy has `Phi2 = -2` between the atoms. |
| `finite-displacement-force-constants` | `compute_fc2_finite_displacement` | `centralDifference_error`: the central difference of the force is within `M h^2 / 6` of `-dF_j/du_i`, with `M` bounding the third derivative of the force along the displacement. |
| `hyperelastic-elastic-constants` | `compute_elastic_constants` | `elasticConstants_symmetries`: at a stress-free reference, for a rotation-invariant energy `C^2` there, `C_abcd = C_cdab = C_bacd = C_abdc`. `voigt_pos_of_stable_reference`: such constants that store positive energy for every nonzero symmetric strain give positive Voigt moduli and a Poisson ratio in `(-1, 1/2)`. |
| `molecular-normal-modes` | `compute_molecular_frequencies` | `molecularFrequencies_of_isLocalMin`: at a local minimum of a `C^2` potential with positive masses every mass-weighted Hessian eigenvalue is nonnegative, so no mode is serialized negative and each squared frequency is its eigenvalue. `massWeightedHessian_translation`: the mass-weighted rigid translations of a translation-invariant potential are zero modes. |

Each cited theorem uses every named hypothesis. Without translation invariance the forces and force constants need not balance; without rotation invariance the torque and the stress balance fail; without `C^3` the mixed third derivatives need not commute; without differentiability of the force the catalog value is Mathlib's junk zero and the central-difference bound fails; at a pre-stressed reference the minor symmetries fail by residual-stress terms; without a local minimum the Hessian can have a negative eigenvalue. The sum rules need no smoothness hypothesis because Mathlib's derivative is zero where it does not exist.

Two corrections to the brief. The central-difference error is of order `h^2` only when the force is three times differentiable along the displacement, which needs a four times differentiable potential, not a three times differentiable one. The molecular result covers the translational zero modes and the absence of imaginary modes at a minimum; the rotational zero modes and the `3N - 6` count are not proved.

## Catalog defect

`compute_gruneisen` computes `-sum_{i,j} Phi3[i,j,k,R,R'] / (6 omega^2)`: it contracts the third-order force constants over two Cartesian indices only, with no eigenvectors, masses, Bloch phases or atomic positions, and leaves `k`, `R` and `R'` free on the right-hand side while the left-hand side depends on `(q, nu)`. The Maradudin-Fein form is `gamma_{q nu} = -(1/(6 omega_{q nu}^2)) sum Phi_{alpha beta gamma}(0 kappa, l' kappa', l'' kappa'') e*_{alpha kappa}(q nu) e_{beta kappa'}(q nu) exp(i q . R_{l'}) r_gamma(l'' kappa'') / sqrt(M_kappa M_kappa')`. The operator stays a gap with this reason.

## Coverage

| Measure | Before (5855543) | After |
| --- | ---: | ---: |
| Operator formulas proved | 36 / 127 | 43 / 127 |
| Physlib-anchored | 24 | 24 |
| Local | 12 | 19 |
| Nodes proved | 31 | 37 |
| Bindings | 36 | 42 |
| Local relations | 4 | 10 |

## Prose for site and paper

Home page and Lean page: 43 of 127 operator formulas carry a compiled proof, 24 anchored to Physlib and 19 as local proofs over Mathlib.

Paper, after the lattice-dynamics paragraph: The catalog's forces, cell stress, force constants, finite-displacement force constants, elastic constants and molecular frequencies are derivatives of one energy, and local proofs state what that structure implies. Invariance under rigid translations makes the forces sum to zero and gives the acoustic sum rules of the second- and third-order force constants; invariance under rotations in a plane makes the torque vanish, which holds for an isolated molecule but not for atoms rotated inside a fixed periodic lattice. The central-difference estimate of a force constant is within `M h^2 / 6` of the derivative, with `M` bounding the third derivative of the force along the displacement. Rotation invariance of a cell energy of the deformation gradient balances the compressive-positive stress, which is symmetric at the reference cell; at a stress-free reference the elastic constants have the major symmetry and both minor symmetries, so a stable reference has positive Voigt moduli and a Poisson ratio in (-1, 1/2). At a local minimum of a molecular potential the mass-weighted Hessian has no negative eigenvalue, the catalog's `n_imaginary = 0` diagnostic. The catalog's mode Gruneisen formula is defective: it contracts the third-order force constants over two indices only and leaves three free.

`docs/llms.txt`, formula bridge entry: add "local proofs for the derivatives of an atomistic or cell energy (force balance, acoustic sum rules, central-difference error, stress balance, elastic-constant symmetries, molecular modes at a minimum); the mode Gruneisen formula is recorded as a catalog defect".
