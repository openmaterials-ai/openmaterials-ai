# Local analog-device, Arrhenius and Nernst-Einstein proofs

This tranche adds two `local` bindings, `analog-device-metrology` and `arrhenius-ionic-transport`, over Mathlib with no Physlib source, in `lean/bridge/OMAIDeviceMetrology.lean` and `lean/bridge/OMAIMaterialsTransport.lean`. Nine operator formulas become local compiled subjects. Independent mathematician and device-physicist reviews of the first version (15370b7) found every statement true but four operators resting on obvious results; each now has a theorem with content tied to a claim of the catalog, and the obvious results stay in the modules uncited.

## Cited theorems

| Operator | Theorem | Statement |
| --- | --- | --- |
| apply_conductance_drift | `drift_law_unique` | Every continuous positive drift law `G_0 phi(t/t_0)` independent of the reference time is `G_0 (t/t_0)^(-nu)` for some `nu` (multiplicative Cauchy equation). |
| emit_thermionic_conductance | `thermionic_wrongLaw_barrier` | `T^(3/2)` data inverted with the catalog's `T^2` law from `T_1 < T_2` give `Phi - k_B T_eff/2`, `T_eff = log(T_2/T_1)/(1/T_1 - 1/T_2)`, with `T_1 < T_eff < T_2`. |
| zero_bias_retention | `retention_symmetric_relaxation` | Every solution of `p' = (1 - p)/tau - p/tau` is `1/2 + (p(0) - 1/2) exp(-2t/tau)`: relaxation to one half with time constant `tau/2`. |
| ramp_set_voltage | `ramp_expectedHops` | `int_0^V g_r rate = N_lead(V) - g_r k_B T/(alpha_F tau_0)`, `tau_0 = exp(E_m/(k_B T))/nu_0` of the unprogrammed state. |
| | `ramp_meanSetVoltage` | The first-hop law with survival `exp(-N_lead)` has density of mass one, integrable first moment, and mean `V* - gamma b` (through `gamma = -Gamma'(1)`). |
| propagate_programming_error | `programmingError_gt` | Exceeds `c/sqrt(2 n_w)` for every kernel of `n_w` nonzero weights and every `W > 1` (Cauchy-Schwarz). |
| dissipate_pulse_energy | `pulseEnergy_bracket` | For monotone `G` during the pulse, `int V_p^2 G dt` lies between the catalog energies at the initial and final conductance. |
| contract_device_conductance | `deviceConductance_series_le` | `A/sum(l_i/sigma_i) <=` the catalog conductance with the length-averaged conductivity. |
| fit_arrhenius | `wlsSlope_minimizes` | The weighted least-squares slope and intercept minimize the weighted sum of squared residuals over all lines. |
| | `arrhenius_wls_recovers_activation` | On exact Arrhenius data the slope gives `E_a = -k_B slope` for any positive weights and two or more distinct temperatures (an exact-data identity). |
| compute_ionic_conductivity | `ionic_wls_apparent_activation` | Fitting `log sigma` against `1/T` returns `E_a - k_B T_eff` with `T_lo <= T_eff <= T_hi`, any positive weights. |

Kept uncited as support: `driftConductance_rereference`, `driftConductance_logSlope` (needs `G_0 != 0` and `0 < t_{d,0}`), `thermionicConductance_eq_zeroBiasSlope`, `thermionicConductance_ideality`, `thermionic_barrier_two_temperatures`, `retentionTime_mean_exit`, `retention_barrier_two_temperatures`, `leadingHops_hasDerivAt`, `leadingHops_eq_exp`, `programmingError_eq_cells`, `programmingError_strictAntiOn`, `tendsto_programmingError`, `wlsSlope_affine`, `wlsSlope_log_mem`, `ionicConductivity_arrhenius`. The programming-error closed form equals the per-cell sum of the catalog description; no derivation from the stochastic cell model is claimed.

## Unbound

`contract_conductance_window`, `contract_state_coefficient_of_variation` and `contract_diffusivity` are definitions with nothing non-obvious to prove. `schottky_mott_barrier` is unbound because its validity (no Fermi-level pinning, no interface dipole; pinning factors near 0.1 for Si, GaAs and MoS2) cannot be established algebraically. `compute_carrier_density` and `compute_configurational_energy` are external selectors.

## Catalog defects found (not edited)

- WorkFunction does not distinguish a metal from a semiconductor, so the two MoS2 WorkFunction instances can compose into a SchottkyBarrierHeight through schottky_mott_barrier.
- ConductanceState is the chord conductance, but emit_thermionic_conductance writes a small-signal zero-bias slope into it.
- The units "cm^2/s" and "eV" used by the pymatgen-analysis-diffusion and mat-diffusion-analysis representations are not registered.
- The catalog's canonical ps and THz with joules, siemens and volts are not a coherent embedding: V_p^2 G t_p in V^2 S ps is a picojoule.

## Coverage

| Measure | Before (5855543) | After |
| --- | ---: | ---: |
| Operator formulas proved | 36 / 127 | 45 / 127 |
| Physlib-anchored | 24 | 24 |
| Local | 12 | 21 |
| Bindings | 36 | 38 |

## Prose for site and paper

Lean page and README. Analog-device metrology and solid-state transport have no Physlib model, so their formulas are proved locally over Mathlib. The catalog's power-law drift is the only continuous drift law independent of its reference time; inverting two-dimensional thermionic data with the three-dimensional Richardson law shifts the barrier by k_B T_eff/2 with T_eff between the two temperatures; symmetric two-site retention relaxes to one half in tau/2; the ramp set voltage is the mean of a Gumbel first-hop law, which needs the Euler-Mascheroni constant as -Gamma'(1); the programming error never falls below c/sqrt(2 n_w). The weighted Arrhenius fit is the least-squares line and recovers the activation energy on exact data, and fitting sigma instead of sigma T underestimates it by k_B T_eff.

Paper, Verification paragraph, after the composites sentence. Nine analog-device and solid-state transport formulas are proved locally: the drift power law is characterized by reference-time independence, a wrong-dimension Richardson inversion shifts the barrier by k_B T_eff/2, symmetric retention relaxes in tau/2, the ramp set voltage is the mean of a minimum-Gumbel first-hop law, the programming error exceeds c/sqrt(2 n_w) for any kernel, and an Arrhenius fit of sigma rather than sigma T returns E_a - k_B T_eff. Three closed-form definitions in these domains carry no theorem, and the Schottky-Mott limit is unbound because pinning cannot be excluded algebraically.

llms.txt, formula bridge line. Add: local proofs for analog-device metrology (drift-law uniqueness, thermionic barrier extraction bias, symmetric retention relaxation, ramp set voltage, programming-error floor, pulse energy, series conductance) and for Arrhenius fitting and Nernst-Einstein conduction.
