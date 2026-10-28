# Local stability and CALPHAD equilibrium proofs

This batch adds two `local` bindings for eleven catalog operators: five energy differences of the stability domain in `lean/bridge/OMAIStabilityEnergies.lean` and six CALPHAD equilibrium outputs of the thermochemistry domain in `lean/bridge/OMAICalphad.lean`. Physlib has no model of convex hulls, slab supercells or assessed Gibbs-energy databases, so both modules use Mathlib only and cite no Physlib declaration. Most of these producers are opaque code outputs in the catalog; each gets an interpreted definition stated in its binding's conditions and contract. A first version was revised after independent mathematical and materials-science reviews; the changes are listed at the end.

## Stability (binding `dft-stability-energy-differences`)

| Operator | Lean definition | Cited theorems |
| --- | --- | --- |
| `compute_energy_above_hull` | `energyAboveHull` (interpreted: distance above the lower convex hull of the competing set) | `energyAboveHull_formationEnergy_reference_independent`, `energyAboveHull_affine_invariant`, `energyAboveHull_eq_zero_of_supporting` |
| `compute_adsorption_energy` | `adsorptionEnergy` (transcribed) | `adsorptionEnergy_offset_invariant_iff` |
| `compute_intercalation_voltage` | `intercalationVoltage` (transcribed) | `intercalationVoltage_offset_invariant_iff`, `intercalationVoltage_eq_mean_ocv` |
| `compute_surface_energy` | `surfaceEnergy` (transcribed) | `surfaceEnergy_thickness_independent_iff` |
| `compute_grain_boundary_energy` | `grainBoundaryEnergy` (transcribed, the same function, `grainBoundaryEnergy_eq_surfaceEnergy`) | `surfaceEnergy_thickness_independent_iff` |

The hull distance of per-atom formation energies `(E_j - sum_a n_ja mu_a)/N_j` with atomic fractions `n_ja/N_j` is the same for every reference set `mu`; more generally it does not change when every competing entry is shifted by the same affine function of composition. An affine function of composition below every competitor that touches the entry certifies a zero distance. The adsorption energy and the average voltage are unchanged by every per-element energy offset exactly when the cells conserve atoms. The average voltage is the mean of the open-circuit profile `-(E'(x) - mu)/q` over the ion content for a cell energy continuous on `[0, n]` and differentiable off a countable set, which admits a multi-plateau hull profile. For slab energies `N e + c` and a nonzero area, the surface and grain-boundary energies are thickness independent exactly when the bulk reference equals `e`, are `c/(2A)` then, and grow without bound otherwise.

Kept uncited: `energyAboveHull_nonneg` and `energyAboveHull_mono_competitors` (direct consequences of the definition), the general offset lemma `combination_offset_invariant_iff`, the rfl identity `grainBoundaryEnergy_eq_surfaceEnergy`, and `reactionEnergy_reference_independent_iff`, which proves the corrected reaction-energy formula and is referenced from that operator's gap reason.

## CALPHAD equilibrium (binding `calphad-binary-equilibrium`)

| Operator | Lean definition | Cited theorems |
| --- | --- | --- |
| `solve_equilibrium` | `equilibriumGibbs` (interpreted: least energy of any finite phase mixture at the overall composition) | `equilibriumGibbs_isConvexEnvelope`, `equilibriumGibbsT_concaveOn` |
| `compute_molar_enthalpy` | `molarEnthalpy` (interpreted: `G - T dG/dT`, right derivative) | `equilibrium_enthalpy_monotoneOn` |
| `compute_calphad_entropy` | `calphadEntropy` (interpreted: `-dG/dT`, right derivative) | `equilibrium_entropy_monotoneOn` |
| `compute_chemical_potentials` | `chemicalPotentials` (interpreted: binary tangent intercepts of the equilibrium envelope) | `commonTangent_of_isLocalMin` |
| `compute_phase_fractions` | `leverFractions` (interpreted: lever rule) | `leverFractions_unique_and_bounds` |
| `compute_transition_temperature` | `transitionTemperature` (interpreted for unary and congruent transitions) | `transitionTemperature_unique` |

For a binary system the equilibrium molar Gibbs energy is the convex envelope of the phase Gibbs curves on `[0, 1]`: convex, below every phase curve, and above every convex function below them; the phase set need not be finite and the infimum need not be attained. If every phase's Gibbs function is concave in temperature, the equilibrium Gibbs energy at any fixed composition is concave in temperature (an infimum of concave mixture energies over a temperature-independent set of mixtures), so the equilibrium entropy and, at nonnegative temperature, the enthalpy, both with the right temperature derivative, are nondecreasing through every phase transition: the equilibrium heat capacity, latent heats included, is nonnegative. At a two-phase minimum with interior compositions both differentiable phase curves share the common tangent, so the chemical potentials agree. Mass balance fixes the phase fractions to the lever rule, in `[0, 1]` exactly when `x1 <= x <= x2`. For a unary system or a congruent transformation, a Gibbs-energy difference that changes sign on `[T1, T2]` with a positive entropy difference has one transition temperature, phase alpha stable below and phase beta above.

Kept uncited as support: `equilibriumGibbs_convexOn`, `equilibriumGibbs_le`, `le_equilibriumGibbs_of_convex`, `calphadEntropy_monotoneOn`, `molarEnthalpy_monotoneOn`.

Hypotheses were checked by dropping them. `Nonempty P` and `x in [0, 1]` were removed from the temperature-concavity theorem (with no admissible mixture the interpreted energy is the constant 0, which is concave), `Nonempty P` from the composition-convexity theorem, `0 < n` from the mean-voltage theorem, and `0 < A` became `A != 0` in the thickness theorem.

## Unbound

- Definitions with nothing to prove: `compute_formation_energy` (per-atom `(E - sum_a n_a mu_a)/N`; its references drop out of the hull distance) and `contract_gibbs_hts` (`G = H - T S`).
- Catalog defect: `compute_reaction_energy`, recorded in its gap reason with the correct formula.

## Catalog issues found

- `compute_reaction_energy` applies signed formula-unit coefficients to per-atom formation energies. For 2 Li + 1/2 O2 -> Li2O it gives -2.0616 eV, and -1.6616 eV with mu_Li shifted by 0.3 eV, against the true -6.1848 eV. The reaction energy is `sum_i nu_i N_i Delta H_f,i`, with `N_i` the atoms per reduced formula unit, per reaction as balanced (divide by the atoms of the reaction for eV/atom). The `ReactionEnergy` node excludes the SISSO dGf(T) cousin, but its only representation computes from GibbsComputedEntry dGf(T); the edge should state which quantity it consumes.
- `compute_intercalation_voltage` hard-codes one electron per ion (`n_ion q_e`); for an ion of valence z the transferred charge is `n z e` (Mg, Ca, Zn, Al).
- `compute_transition_temperature` is a boundary locus (liquidus, solidus, solvus where a phase fraction reaches 0 or 1). For an alloy the equal-Gibbs-energy temperature at one composition is T0, a different quantity: an ideal lens at x = 0.5 has T0 = 1250.0 K, solidus 1219.5 K and liquidus 1279.1 K. Only the unary and congruent cases are covered.
- The `EnergyAboveHull` node says the distance is zero exactly for the ground state; it is zero for every entry on the lower convex hull.
- `compute_surface_energy` and `compute_grain_boundary_energy` do not state that the bulk reference must be the slab's own bulk energy per unit (otherwise the value grows linearly with thickness), that the surface form needs a stoichiometric slab with two equivalent terminations, or that the grain-boundary 2A form needs a fully periodic bicrystal.

## Coverage

| Measure | Before (5855543) | After |
| --- | ---: | ---: |
| Operators proved | 36 / 127 | 47 / 127 |
| Physlib-anchored operators | 24 | 24 |
| Local operators | 12 | 23 |
| Nodes proved | 31 | 42 |
| Local relations | 4 | 6 |

## Changes after review

The first version cited Gibbs-Helmholtz and the product-rule identity dH/dT = T dS/dT for the enthalpy and entropy producers, and Gibbs-Duhem for the chemical potentials; all three were obvious calculus and are removed. The enthalpy and entropy producers now rest on concavity of the equilibrium Gibbs energy in temperature. The transition-temperature interpretation is restricted to unary and congruent transformations; the reaction energy is a catalog defect, not a proof subject; the composition envelope adds its minorant leg; the mean-voltage theorem admits kinks; the hull theorem is stated for formation energies directly; and the conditions name the correction-class, competing-set, valence, slab and adsorption caveats.

## Prose for site and paper

For `docs/llms.txt`: Stability and CALPHAD (local proofs over Mathlib): the interpreted energy above the hull of per-atom formation energies does not depend on the elemental references; adsorption and intercalation energies are unchanged by per-element offsets exactly when they balance atoms; the average intercalation voltage is the mean open-circuit voltage, plateaus included; slab surface and grain-boundary energies are thickness independent only with a consistent bulk reference; the binary equilibrium Gibbs energy is the convex envelope of the phase curves, concave in temperature when the phases are, so entropy and enthalpy rise through every transition; common tangent, lever rule and a unique unary or congruent transition temperature. The catalog's reaction-energy formula is a recorded defect.

For the paper (Lean layer paragraph): The stability energy differences and the CALPHAD equilibrium outputs are covered by local theorems over Mathlib, since Physlib has no model of convex hulls, slabs or assessed databases. The interpreted energy above the hull of per-atom formation energies does not depend on the elemental reference energies; adsorption and intercalation energies are independent of per-element energy offsets exactly when they balance atoms; the average intercalation voltage is the mean of the open-circuit profile, kinks included; and slab surface and grain-boundary energies are independent of thickness exactly when the bulk reference equals the slab slope. For a binary system the equilibrium molar Gibbs energy is the convex envelope of the phase Gibbs curves; when every phase's Gibbs function is concave in temperature it is concave in temperature at fixed composition, so the equilibrium entropy and enthalpy do not decrease through a phase transition; the chemical potentials agree across a two-phase minimum, the phase fractions follow the lever rule, and a unary or congruent transition with positive entropy change has a unique transition temperature. The formation energy and G = H - T S are definitions; the catalog's reaction-energy formula applies formula-unit coefficients to per-atom formation energies and is recorded as a defect.
