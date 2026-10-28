# Local stability and CALPHAD equilibrium proofs

This batch adds two `local` bindings for twelve catalog operators: six energy differences of the stability domain in `lean/bridge/OMAIStabilityEnergies.lean` and six CALPHAD equilibrium outputs of the thermochemistry domain in `lean/bridge/OMAICalphad.lean`. Physlib has no model of convex hulls, slab supercells or assessed Gibbs-energy databases, so both modules use Mathlib only and cite no Physlib declaration. Most of these producers are opaque code outputs in the catalog; each gets an interpreted definition stated in its binding's conditions and contract.

## Stability (binding `dft-stability-energy-differences`)

| Operator | Lean definition | Cited theorems |
| --- | --- | --- |
| `compute_energy_above_hull` | `energyAboveHull` (interpreted: distance above the lower convex hull of the competing set) | `energyAboveHull_affine_invariant`, `energyAboveHull_mono_competitors`, `energyAboveHull_eq_zero_of_supporting` |
| `compute_reaction_energy` | `reactionEnergy` (transcribed) | `reactionEnergy_reference_independent_iff` |
| `compute_adsorption_energy` | `adsorptionEnergy` (transcribed) | `adsorptionEnergy_offset_invariant_iff` |
| `compute_intercalation_voltage` | `intercalationVoltage` (transcribed) | `intercalationVoltage_offset_invariant_iff`, `intercalationVoltage_eq_mean_ocv` |
| `compute_surface_energy` | `surfaceEnergy` (transcribed) | `surfaceEnergy_thickness_independent_iff` |
| `compute_grain_boundary_energy` | `grainBoundaryEnergy` (transcribed) | `grainBoundaryEnergy_thickness_independent_iff` |

The hull distance does not change when every competing entry's formation energy is shifted by the same affine function of composition, `h_j + c + sum_a delta_a x_ja`, which includes any change of the elemental reference energies; it can only grow when competitors are added, so a value against an incomplete competing set is a lower bound; and an affine function of composition below every competitor that touches the entry certifies a zero distance. The catalog's reaction energy over per-atom formation energies with weights `nu_i N_i` equals `sum_i nu_i E_i` for every reference set exactly when the reaction is balanced. The adsorption energy and the average voltage are unchanged by every per-element energy offset exactly when the cells conserve atoms. The average voltage is the mean of the open-circuit profile `-(E'(x) - mu)/q` over the ion content (fundamental theorem of calculus). For slab energies `N e + c`, the surface and grain-boundary energies are thickness independent exactly when the bulk reference equals `e`, are `c/(2A)` then, and grow without bound otherwise.

`energyAboveHull_nonneg` (a direct consequence of the definition) and the general offset lemma `combination_offset_invariant_iff` are kept uncited.

## CALPHAD equilibrium (binding `calphad-binary-equilibrium`)

| Operator | Lean definition | Cited theorems |
| --- | --- | --- |
| `solve_equilibrium` | `equilibriumGibbs` (interpreted: least energy of any finite phase mixture at the overall composition) | `equilibriumGibbs_convexOn`, `le_equilibriumGibbs_of_convex` |
| `compute_molar_enthalpy` | `molarEnthalpy` (interpreted: `G - T G'`) | `molarEnthalpy_calphadEntropy_heatCapacity`, `gibbs_helmholtz` |
| `compute_calphad_entropy` | `calphadEntropy` (interpreted: `-G'`) | `molarEnthalpy_calphadEntropy_heatCapacity` |
| `compute_chemical_potentials` | `chemicalPotentials` (interpreted: binary tangent intercepts) | `gibbs_duhem`, `commonTangent_of_isLocalMin` |
| `compute_phase_fractions` | `leverFractions` (interpreted: lever rule) | `leverFractions_unique_and_bounds` |
| `compute_transition_temperature` | `transitionTemperature` (interpreted: lowest temperature in a bracket where `G_beta <= G_alpha`) | `transitionTemperature_unique` |

For a binary system the equilibrium molar Gibbs energy is convex on `[0, 1]` and is the greatest convex function below every phase's Gibbs curve, its convex envelope. The enthalpy and entropy channels give the same heat capacity, `dH/dT = T dS/dT = -T G''`, and satisfy Gibbs-Helmholtz `d(G/T)/dT = -H/T^2`. The chemical potentials obey Gibbs-Duhem, and at a two-phase minimum with `x1 < x < x2` both tangents are the common chord, so the chemical potentials agree. Mass balance fixes the phase fractions to the lever rule, in `[0, 1]` exactly when `x1 <= x <= x2`. A Gibbs-energy difference that changes sign on `[T1, T2]` with a positive entropy difference has one transition temperature, phase alpha stable below and phase beta above.

Every named hypothesis was checked by dropping it. `Nonempty P` was removed from the convexity theorem (with no phases the interpreted energy is the constant 0, also convex) and `0 < n` from the mean-voltage theorem (the identity holds with the junk division at `n = 0`).

## Definitions with nothing to prove

`compute_formation_energy`, the per-atom `(E - sum_a n_a mu_a)/N`, and `contract_gibbs_hts`, `G = H - T S`, stay unbound. Their reference choice and their consistency with the other producers enter the theorems above; a theorem restating either would certify nothing.

## Catalog issues found

- `compute_reaction_energy` and the `ReactionEnergy` node mix normalizations. The node calls the result a combination of per-atom formation energies weighted by the balancing coefficients, and the edge cites rxn_network's total-eV `ComputedReaction.energy`. With per-atom formation energies the weights must be `nu_i N_i`; with formula-unit coefficients the sum is not the reaction energy and depends on the elemental references, which `reactionEnergy_reference_independent_iff` shows. The binding states the `nu_i N_i` convention as a condition.
- The `EnergyAboveHull` node says the distance is zero exactly for the ground state. It is zero for every entry on the hull, including entries on a hull facet that are not vertices; only the sufficiency of a supporting affine function is proved here.
- `compute_surface_energy` and `compute_grain_boundary_energy` do not say that the bulk reference must be the slab's own bulk energy per unit; with any other reference the value grows linearly with slab thickness.

## Coverage

| Measure | Before (ef98abd) | After |
| --- | ---: | ---: |
| Operators proved | 36 / 127 | 48 / 127 |
| Physlib-anchored operators | 24 | 24 |
| Local operators | 12 | 24 |
| Nodes proved | 31 | 43 |
| Local relations | 4 | 6 |

## Prose for site and paper

For `docs/llms.txt`: Stability and CALPHAD (local proofs over Mathlib): the interpreted energy above the hull is invariant under affine composition shifts of the formation energies, including elemental reference changes, and grows with the competing set; balanced reaction, adsorption and intercalation energies are unchanged by per-element offsets; the average intercalation voltage is the mean open-circuit voltage; slab surface and grain-boundary energies are thickness independent only with a consistent bulk reference; the binary equilibrium Gibbs energy is the convex envelope of the phase curves, with Gibbs-Duhem, common tangent, lever rule and a unique transition temperature.

For the paper (Lean layer paragraph): The stability energy differences and the CALPHAD equilibrium outputs are covered by local theorems over Mathlib, since Physlib has no model of convex hulls, slabs or assessed databases. The interpreted energy above the hull is unchanged by any affine-in-composition shift of the formation energies, so it does not depend on the elemental references, and it can only grow as competitors are added; reaction, adsorption and intercalation energies are reference independent exactly when they balance atoms; the average intercalation voltage is the mean of the open-circuit profile; and slab surface and grain-boundary energies are independent of thickness exactly when the bulk reference equals the slab slope. For a binary system the equilibrium molar Gibbs energy is the convex envelope of the phase Gibbs curves, its enthalpy and entropy channels give the same heat capacity, the chemical potentials obey Gibbs-Duhem and agree across a two-phase minimum, the phase fractions follow the lever rule, and a Gibbs-energy difference that changes sign with positive entropy difference has a unique transition temperature. The formation energy and G = H - T S are definitions and receive no theorem.
