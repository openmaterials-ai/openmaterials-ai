# Local composites and cure-kinetics proofs

This batch adds two local proof modules over Mathlib for six catalog operators that Physlib has no model for: `depolarization_factors`, `nan_effective_kappa`, `nan_effective_kappa_aligned`, `hasselman_johnson`, `kamal_cure_conversion` and `dibenedetto_glass_transition`. Each binding has relation `local`, cites no Physlib declaration, targets only its proof subjects (the operators and their outputs) and discloses conditions and remaining obligations. No catalog formula, identity or lineage rule changes.

`contract_interface_conductance[transport_model=nemd]` (G = q/dT) is a definition and `resolve_effective_conductivity` has the formula `True`; neither receives a theorem.

Two independent reviews (a mathematician and a materials physicist) found the Lean sound. This version applies their fixes: the radius-diameter statement is corrected, the Kamal inverse solves the rate law on a neighbourhood, obvious and substitution results are no longer cited, the random Nan formula has a result for every shape, and the attribution, unit and scope statements are tightened.

## Composites

`lean/bridge/OMAICompositeConductivity.lean` transcribes the four catalog formulas. Cited theorems:

| Theorem | Statement |
| --- | --- |
| `depolarization_eq_integral` | for p > 0 the catalog's three branches equal `int_0^1 t^2/(t^2 + p^2 (1 - t^2)) dt` |
| `depolarization_mem_Ioo` | 0 < L33(p) < 1 for p > 0 |
| `depolarization_strictAntiOn` | L33 decreases strictly on p > 0 |
| `depolarization_continuousOn` | L33 is continuous on p > 0, through the sphere p = 1 |
| `tendsto_depolarization_atTop`, `tendsto_depolarization_zero` | L33 -> 0 for needles, L33 -> 1 for disks |
| `nanRandom_sub_matrix` | for every shape (L in [0, 1]) and f in [0, 1], k_c - k_m = k_m f (2 b11 + b33)/(3 - f (2 L11 b11 + L33 b33)) with a positive denominator |
| `nanRandom_gt_iff` | for every shape and f in (0, 1], k_c > k_m iff 2 b11 + b33 > 0 |
| `nanRandom_sign` | for every shape, corrected filler conductivities both above (both below) k_m give k_c above (below) k_m |
| `nanRandom_sphere`, `nanAligned_sphere` | for spheres both Nan formulas equal Maxwell-Garnett with kc = k/(1 + 2k/(G d)), at every f |
| `nanRandom_sphere_between` | for spheres the random value lies between k_m and kc for f in [0, 1] |
| `tendsto_kapitzaCorrected` | kc -> k as G -> infinity |
| `tendsto_nanRandom_sphere` | the sphere value tends to Maxwell-Garnett with the bulk filler k as G -> infinity |
| `hasselmanJohnson_eq_maxwellGarnett` | Hasselman-Johnson is Maxwell-Garnett with kc at d = 2 a_rad, at every f |
| `hasselmanJohnson_critical_radius` | for k > k_m and f in (0, 1], k_c > k_m iff a > a_c and k_c = k_m iff a = a_c, a_c = (k_m/G) k/(k - k_m) |
| `nanAligned_strictAntiOn` | for 0 < f < 1 and kc != k_m the aligned value decreases strictly in L33 on [0, 1] |
| `nanAligned_strict_wiener` | for L33 and f in (0, 1) and kc != k_m, series < aligned < parallel |
| `nanAligned_strictMonoOn_aspect` | at fixed d3, the aligned value increases strictly with the aspect ratio |

Compiled but not cited: `nanRandom_sphere_eq_hasselmanJohnson` (an identity between two catalog formulas) and `tendsto_depolarization_sphere` (a corollary of continuity). The needle and disk substitutions are private helpers of the Wiener bound, and the critical radius's comparison with the Kapitza radius is no longer stated.

## Cure kinetics

`lean/bridge/OMAICureKinetics.lean` transcribes the two catalog formulas. Cited theorems:

| Theorem | Statement |
| --- | --- |
| `kamalCureTime_strictMonoOn` | t(alpha) increases strictly on [alpha_0, 1) |
| `kamalCureTime_hasDerivAt` | t'(alpha) = 1/rate(alpha) for alpha in (alpha_0, 1) |
| `kamal_inverse_exists` | near every interior cure time one inverse alpha(t) solves d alpha/dt = rate(alpha) at every time of a neighbourhood |
| `kamal_inverse_solves_rate_law` | every continuous local inverse solves the rate law |
| `diBenedetto_strictMonoOn`, `diBenedetto_bijOn` | for lambda > 0 and T_ginf > T_g0, T_g maps [0, 1] one to one and strictly increasingly onto [T_g0, T_ginf] |
| `diBenedetto_lt_linear` | for 0 < lambda < 1 and T_g0 < T_ginf, T_g lies strictly below the linear interpolation inside (0, 1) |

Admissibility requires A_1, A_2 >= 0, m >= 0, alpha_0 >= 0, and either A_1 > 0 (which includes pure nth-order kinetics with A_2 = 0) or alpha_0 > 0 with A_2 > 0. Any real n is admissible. The rate law is solved locally near each interior time; no global solution is claimed.

## Conventions a user could get wrong

- The catalog's d_1 and d_3 are full particle dimensions (the per-direction interface convention of Nan, Liu, Lin and Li, Appl. Phys. Lett. 85, 3549 (2004)), so a sphere's d is its diameter, while Hasselman-Johnson's a_rad is its radius. The formulas agree for spheres with d = 2 a_rad. Putting the radius into d doubles the interface penalty 1/kc - 1/k = 2/(G d), from 1/(G a_rad) to 2/(G a_rad).
- Away from p = 1 the per-direction correction k/(1 + 2k/(G d)) is a slab approximation of unvalidated accuracy; Nan et al., J. Appl. Phys. 81, 6692 (1997) uses K_p/(1 + R K_p L_ii (2 + 1/p)/a_1), and the two agree only at p = 1.
- G_int = q_int/Delta T_int > 0 with the temperature drop taken in the direction of the heat flux. The factor 2 in kc counts the two interfaces a particle presents along a direction, and one G_int applies to every face.
- Axis 3 is the spheroid symmetry axis; p = d3/d1 > 1 is prolate (fibre), p < 1 oblate (platelet). k_f[1,1] is transverse to axis 3 and k_f[3,3] along it. The aligned operator is the component along the alignment axis, which is through-plane only for platelets.
- Random means isotropic three-dimensional orientation; platelets randomly oriented within a plane are covered by neither formula. Particles are monodisperse in size and shape. L11 = (1 - L33)/2 is not proved.
- f_vol is a volume fraction in [0, 1], not a mass fraction or a percentage. Conversion is a fraction, not a percentage.
- Kamal activation energies are per mole, with R = N_A k_B and T in kelvin. Isothermal Kamal values are meaningful only while T_g(alpha(t)) stays below the cure temperature.
- DiBenedetto temperatures are in kelvin, as the GlassTransitionTemperature node and evaluator store them. T_g(alpha) is taken as independent of cure path and specific to one stoichiometry.

## Catalog prose

The composites module docstrings no longer call a_K = k_m/G the crossover (the proved crossover is a_c = a_K k/(k - k_m)) and no longer say "Bruggeman-Nan". Three description fields that the map store mirrors still carry the old wording: the FillerVolumeFraction node ("the Nan result is a lower bound"), the nan_effective_kappa edge ("Bruggeman-Nan terms", Nan 1997 attribution of the interface term, "Below the Kapitza radius a_K = km/G a conductive filler LOWERS kappa_c") and the CureConversion node ("its value is an upper bound throughout the hold"). Changing them leaves catalog ids and formula fingerprints unchanged but needs edit_meta records in map/log.jsonl, a new map version; that change is left to the coordinator.

## Coverage

| Measure | Count |
| --- | ---: |
| Operators proved (Physlib-anchored plus local) | 31 / 127 |
| Physlib-anchored compiled operators | 20 |
| Local compiled operators | 11 |
| Bindings | 31 (26 compiled) |
| Axiom audit | 849 theorems, 1190 declarations |

## Prose for site and paper

Site guide or Lean page: Six formulas with no Physlib model now have local Lean proofs over Mathlib. Both branches of the spheroid depolarization factor equal one integral, which makes it lie in (0, 1), decrease with aspect ratio, join continuously at the sphere and reach the needle and disk limits. For every spheroid shape the random Nan conductivity exceeds the matrix value exactly when 2 b11 + b33 > 0, so filler whose interface-corrected conductivities exceed the matrix raises it. For spheres the Nan formulas reduce to Maxwell-Garnett, and Hasselman-Johnson is the same model written with the sphere radius: the catalog's d is a diameter, and putting the radius into d doubles the interface penalty. A Hasselman-Johnson filler raises the conductivity exactly above the critical radius (k_m/G) k/(k - k_m). Along the alignment axis the aligned conductivity lies strictly between the series and parallel mixtures. The Kamal-Sourour cure time is strictly increasing, and near every interior time an inverse solves the rate law; the DiBenedetto relation maps conversion one to one onto [T_g0, T_ginf] and lies strictly below the linear interpolation for lambda < 1.

Paper, Current formula bridge paragraph: The bridge also holds local proofs, theorems about OMAI formulas that Physlib has no model for, counted apart from the Physlib-anchored results. For filled composites, the spheroid depolarization factor equals int_0^1 t^2/(t^2 + p^2 (1 - t^2)) dt on both closed-form branches; for every shape the sign of the random Nan enhancement is that of 2 b11 + b33; the Nan and Hasselman-Johnson conductivities of spheres reduce to Maxwell-Garnett with the interface-corrected filler conductivity, with the catalog's d a diameter and Hasselman-Johnson's a_rad a radius; and the aligned conductivity lies strictly between the series and parallel mixtures. For thermoset cure, the Kamal-Sourour time integral has a local inverse near every interior time that solves the rate law there, and the DiBenedetto relation is a strictly increasing bijection of [0, 1] onto [T_g0, T_ginf] in kelvin. Measured parameters, the slab approximation of the interface term away from spheres, dilute-limit validity, percolation and diffusion-controlled cure remain outside the proofs.
