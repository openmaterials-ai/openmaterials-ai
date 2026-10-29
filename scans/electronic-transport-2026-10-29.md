# Electronic transport, carrier statistics and static dielectric proofs

This batch binds six catalog operators of the electronic_transport domain, all opaque code outputs, through four Lean modules: `lean/bridge/OMAIPhyslibElectronicTransport.lean` (Physlib-anchored, three operators), `lean/bridge/OMAIElectronicStatistics.lean` (local, two operators), `lean/bridge/OMAIStaticDielectric.lean` (local, one operator) and the support module `lean/bridge/OMAISommerfeldTransport.lean` (Mathlib only, no catalog endpoint, cited from the transport binding). Every bound operator is interpreted, not transcribed: the catalog formula names a code's output, so each binding states the definition it proves about and the conditions under which that definition is the code's quantity. The Lean sources came from `origin/feat/electronic-transport` unchanged; this batch adds the contracts, bindings, tests, registration and prose.

## Boltzmann transport (binding `boltzmann-electronic-transport`, conditional)

| Operator | Lean definition | Cited theorems |
| --- | --- | --- |
| `compute_electronic_conductivity` | `boltzmannConductivity` (interpreted: `sigma = e^2 L_0`) | `exists_boltzmann_thermoelectricMaterial`, `figureOfMerit_lt_mahanSofo`, `Sommerfeld.wiedemannFranz_constantTransport` |
| `compute_seebeck` | `boltzmannSeebeck` (interpreted: `S = -(L_1/L_0)/(e T)`) | `exists_boltzmann_thermoelectricMaterial`, `figureOfMerit_lt_mahanSofo`, `Sommerfeld.wiedemannFranz_constantTransport` |
| `compute_electronic_thermal_conductivity` | `boltzmannKappaE` (interpreted: `kappa_e = (L_2 - L_1^2/L_0)/T`) | `boltzmannKappaE_nonneg_and_eq_zero_iff`, `exists_boltzmann_thermoelectricMaterial`, `figureOfMerit_lt_mahanSofo`, `Sommerfeld.sommerfeld_moments`, `Sommerfeld.wiedemannFranz_constantTransport` |

The three producers are read as BoltzTraP2's Onsager coefficients on a finite energy grid, `L_k = sum_b w_b (E_b - mu)^k` with `w_b >= 0` the diagonal transport distribution times the Fermi window times the bin width. At `T > 0`, `kappa_e >= 0` with equality exactly when every state with nonzero weight has one energy (the variance identity `L_0 L_2 - L_1^2 = (1/2) sum_{b,c} w_b w_c (E_b - E_c)^2`). With `L_0 > 0`, `e != 0`, `T > 0` and any `kappa_l > 0` the coefficients are the fields of Physlib's `ThermoelectricMaterial`, which is the Physlib anchor (structure, `figureOfMerit`, `figureOfMerit_eq`). With `L_0 L_2 - L_1^2 > 0` and `L_1 != 0`, every such material has `zT < L_1^2/(L_0 L_2 - L_1^2)` and the bound is approached as `kappa_l -> 0`. The Sommerfeld module proves the Fermi-window moments 1, 0 and `pi^2/3` (through `sum (-1)^(n+1)/n^2 = pi^2/12` from Mathlib's Bernoulli cosine series and the Gamma integral), so for an energy-independent transport distribution the same three formulas give `S = 0` and `kappa_e = (pi^2/3)(k_B/e)^2 sigma T`.

Kept uncited: the private algebra `lagrange`, `kinetic_zero_nonneg`, `kinetic_two_nonneg`, `variance_nonneg` and `figureOfMerit_closed`; in the Sommerfeld module `fermiWindow_neg`, `integral_fermiWindow`, `integral_mul_fermiWindow`, `integral_sq_mul_fermiWindow` and `kineticIntegral_eq`, which feed `sommerfeld_moments`.

## Carrier statistics (binding `electronic-carrier-statistics`, local)

| Operator | Lean definition | Cited theorems |
| --- | --- | --- |
| `compute_carrier_mobility` | `boltzmannMobility` (interpreted: `c sum_k w_k (sum_i 1/tau_{k,i})^-1`) | `boltzmannMobility_le_matthiessen` |
| `compute_electronic_dos` | `electronicDOS` (interpreted: `sum_b g_b delta(E - E_b)` against a test function) | `exists_unique_fermiLevel` |

With `c > 0`, `w_k >= 0` and every `tau_{k,i} > 0`, the mobility with state-by-state additive rates is at most the Matthiessen combination `(sum_i 1/mu_i)^-1` of the single-mechanism mobilities (Cauchy-Schwarz in the form of `sq_sum_div_le_sum_sq_div`). At `k_B T > 0`, for levels with degeneracies `g_b > 0`, the electron count is continuous and strictly increasing from 0 to `sum_b g_b`, so every count strictly between fixes exactly one chemical potential (intermediate value theorem plus strict monotonicity). Kept uncited: `combinedTime_le` (support) and `electronCount_eq_dos` (a simp restatement).

## Static dielectric tensor (binding `static-dielectric-ionic-response`, local)

| Operator | Lean definition | Cited theorems |
| --- | --- | --- |
| `compute_static_dielectric` | `staticDielectric` (interpreted: `eps_inf + c Z^T D^-1 Z` on the optical coordinates) | `staticDielectric_sub_posSemidef`, `lyddaneSachsTeller` |

With `D` positive definite and `c > 0`, `eps_0 - eps_inf` is positive semidefinite and vanishes along `u` exactly when `Z u = 0`. Along `u` with `u eps_inf u > 0`, `det(D + c (Z u)(Z u)^T/(u eps_inf u))/det(D) = (u eps_0 u)/(u eps_inf u)` by the matrix determinant lemma, and the determinants are the products of the eigenvalues, the longitudinal and transverse squared frequencies. Kept uncited: `row_mul_col` and `quad_ionic`.

## Hypotheses

All statements are over exact reals; none certifies a floating-point adapter. The transport window must have nonnegative weights, which holds for diagonal tensor components only. `e != 0` and `T > 0` are needed for the Physlib material; the Mahan-Sofo bound needs a window whose weighted energies are not all equal and `L_1 != 0`. The dielectric statements need the optical dynamical matrix to be positive definite, so the acoustic translations must be projected out and the crystal must have no imaginary Gamma mode; the consistency of that restriction with `Z u` rests on charge neutrality of the Born charges. The Fermi-level statement needs `k_B T > 0`; at `T = 0` any chemical potential in a gap gives the same count.

## Unbound

- Every operator of the electronic_transport domain is bound after this batch (three Physlib-anchored, three local). The domain's gap reason is reworded for the nodes and local rows that still carry it.
- `apply_nac_correction` stays a recorded catalog defect (its q dependence cancels). The dielectric module uses the Gonze-Lee form instead and says so.

## Catalog issues found

- `compute_static_dielectric` lists `Frequency` as its phonon input, but the ionic term needs the Gamma-point eigenvectors as well as the frequencies (the mode-oscillator strengths `Z^T e_m`); the interpretation uses the dynamical matrix `D`, which carries both. The formula is opaque, so this is a description issue, not a formula defect.
- The catalog description of `compute_electronic_thermal_conductivity` already flags amset's kappa unit as unconfirmed; the binding's unit sentence repeats that the unit conversion is outside the theorems.

## Coverage

| Measure | Before (8cc4874) | After this batch |
| --- | ---: | ---: |
| Operators proved | 56 / 133 | 62 / 133 |
| Physlib-anchored operators | 24 | 27 |
| Local operators | 32 | 35 |
| Nodes proved | 49 | 55 |
| Local relations | 8 | 10 |

The `md-phonon-spectrum` batch of the same day takes the totals to 69 operators (29 anchored, 40 local) and 61 nodes.

## Review notes on the Lean sources

Nothing in the four files looked overstated. Two places deserve a reader's attention. `OMAIPhyslibElectronicTransport.lean` lines 14 to 15 describe `w_b` as "the transport distribution times the Fermi window"; the nonnegativity hypothesis makes this the diagonal component, which the binding states. `OMAIStaticDielectric.lean` lines 13 to 14 call `D` the dynamical matrix "on the optical coordinates (positive definite, the acoustic translations projected out)"; the file does not say that `Z u` must be orthogonal to the translations for the restriction to be consistent, which holds under charge neutrality of the Born charges and is stated in the binding's conditions.

## Prose for site and paper

For `docs/llms.txt`: Boltzmann electronic transport, anchored to Physlib's thermoelectric material: the conductivity, Seebeck coefficient and electronic thermal conductivity read as Onsager moments of a nonnegative transport window have `kappa_e >= 0`, fill a Physlib material for any lattice conductivity, and keep the figure of merit below the Mahan-Sofo bound; for a flat transport distribution the Fermi-window moments give the Sommerfeld Lorenz number. Local proofs: the Boltzmann mobility with additive rates is at most its Matthiessen combination; a finite level set fixes a unique Fermi level at `k_B T > 0`; the static dielectric tensor has a positive semidefinite ionic term and obeys the generalized Lyddane-Sachs-Teller relation.

For the paper (Lean layer paragraph): The electronic transport producers are opaque code outputs, so each gets an interpreted definition. The conductivity, Seebeck coefficient and electronic thermal conductivity are BoltzTraP2's Onsager moments of a nonnegative transport window; the electronic thermal conductivity is nonnegative and vanishes exactly for a one-energy window, the coefficients fill a Physlib thermoelectric material for any lattice conductivity, and its figure of merit lies strictly below the Mahan-Sofo bound, approached as the lattice conductivity vanishes; for an energy-independent transport distribution the Fermi-window moments give the Sommerfeld Lorenz number. Local theorems bound the mobility by its Matthiessen combination, fix a unique Fermi level for a finite level set at positive temperature, and give the static dielectric tensor a positive semidefinite ionic term and the generalized Lyddane-Sachs-Teller relation.
