# Local analog-device, Arrhenius and Nernst-Einstein proofs

This tranche adds two `local` bindings, `analog-device-metrology` and `arrhenius-ionic-transport`, over Mathlib with no Physlib source, in `lean/bridge/OMAIDeviceMetrology.lean` and `lean/bridge/OMAIMaterialsTransport.lean`. Nine operator formulas become local compiled subjects; four closed-form definitions stay unbound because a theorem restating them would prove nothing.

## Cited theorems

| Operator | Theorem | Statement |
| --- | --- | --- |
| apply_conductance_drift | `driftConductance_rereference` | Drifting to `t_1` and re-referencing gives the same conductance at `t_2` as drifting directly. |
| | `driftConductance_logSlope` | `d log G / d log t_d = -nu` at every time, for `G_0 != 0`. |
| emit_thermionic_conductance | `thermionicConductance_eq_zeroBiasSlope` | The catalog `G` is the zero-bias slope of the Richardson-Dushman current. |
| | `thermionicConductance_ideality` | With ideality `n` the slope is `G/n` for `I_s (exp(q V/(n k T)) - 1)` and `G` for `I_s exp(q V/(n k T))(1 - exp(-q V/(k T)))`. |
| | `thermionic_barrier_two_temperatures` | `Phi_Bn = k_B log((G_1/T_1)/(G_2/T_2))/(1/T_2 - 1/T_1)`. |
| zero_bias_retention | `retentionTime_mean_exit` | The mean of the exit time with density `M k exp(-M k t)` is `tau_ret / M`. |
| | `retention_barrier_two_temperatures` | `E_m = k_B log(tau_1/tau_2)/(1/T_1 - 1/T_2)`, independent of `nu_0`. |
| ramp_set_voltage | `ramp_expectedHops` | `int_0^V g_r rate = N_lead(V) - g_r k_B T/(alpha_F tau_ret)`. |
| | `leadingHops_eq_exp` | `N_lead(V) = exp((V - V*)/b)`, `b = k_B T/alpha_F`, so `N_lead(V*) = 1`. |
| | `ramp_meanSetVoltage` | The first-hop law with survival `exp(-N_lead)` has density `(1/b) e^{x} exp(-e^{x})` and mean `V* - gamma b`, the catalog value (through `gamma = -int_0^inf log t e^{-t} dt`). |
| propagate_programming_error | `programmingError_eq_cells` | The catalog form equals `c sqrt(sum_i (w_max/(W-1) + |w_i|)^2/2)/sum_i |w_i|`. |
| | `programmingError_strictAntiOn` | Strictly decreasing in `W` on `(1, inf)`. |
| | `tendsto_programmingError` | Tends to `c sqrt(S_2/2)/S_1` as `W -> inf`. |
| | `programmingError_gt` | Exceeds `c/sqrt(2 n_w)` for every kernel of `n_w` nonzero weights and every `W > 1`. |
| dissipate_pulse_energy | `pulseEnergy_bracket` | For monotone `G` during the pulse, `int_0^t_p V_p^2 G dt` lies between the catalog energies at the initial and final conductance. |
| contract_device_conductance | `deviceConductance_series_le` | `A/sum_i(l_i/sigma_i) <= ` the catalog conductance with the length-averaged conductivity. |
| fit_arrhenius | `arrhenius_wls_recovers_activation` | Weighted least squares of `log D` on `1/T` gives `E_a = -k_B slope` exactly on Arrhenius data, any positive weights, two or more distinct temperatures. |
| compute_ionic_conductivity | `ionicConductivity_arrhenius` | `d log(sigma T)/d(1/T) = -E_a/k_B` and `d log sigma/d(1/T) = -(E_a - k_B T)/k_B`. |

Supporting lemmas `leadingHops_hasDerivAt` and `wlsSlope_affine` are not cited. While writing the module, the unused-variable linter showed that the log-slope theorem needs no positive time and the mean-exit theorem no positive temperature; those hypotheses were removed, and the log-slope theorem needs only `G_0 != 0`. The strict decrease of the programming error needs only `n_w >= 0`.

## Definitions with nothing to prove

`contract_conductance_window` (`W = G_c/G_min`), `contract_state_coefficient_of_variation` (`c = sigma_G/G_c`), `schottky_mott_barrier` (`Phi_Bn = Phi_W - chi`) and `contract_diffusivity` (`D = slope/(2d)`) are recorded with the reason "A closed-form definition with nothing non-obvious to prove". `compute_carrier_density` and `compute_configurational_energy` are external selectors with nothing algebraic to prove.

## Catalog defects found

None in these two domains. The catalog descriptions claim a Gumbel standard deviation `pi k_B T/(sqrt(6) alpha_F)` and an N-hop mean shift `(k_B T/alpha_F)(psi(N) + gamma)`; these are not proved and are listed as remaining obligations, not defects.

## Coverage

| Measure | Before (ef98abd) | After |
| --- | ---: | ---: |
| Operator formulas proved | 36 / 127 | 45 / 127 |
| Physlib-anchored | 24 | 24 |
| Local | 12 | 21 |
| Bindings | 36 | 38 |
| Local relations | 4 | 6 |

## Prose for site and paper

Lean page and README. Analog-device metrology and solid-state transport have no Physlib model, so their formulas are proved locally over Mathlib. The thermionic conductance is the zero-bias slope of the Richardson-Dushman current, and the barrier follows from two temperatures; the retention time is the mean exit time of a constant-rate escape; the ramp set voltage is the Gumbel mean of the first hop, which needs the Euler-Mascheroni constant as `-Gamma'(1)`; the programming error decreases with the conductance window and never falls below `c/sqrt(2 n_w)`. Weighted least squares on Arrhenius data recovers the activation energy exactly, and `sigma T`, not `sigma`, carries the diffusion barrier in a Nernst-Einstein conductivity.

Paper, Verification paragraph, after the composites sentence. Nine analog-device and solid-state transport formulas are proved locally: the drift law is independent of its reference time, the thermionic conductance is the zero-bias slope of the Richardson-Dushman current and the retention time the mean exit time of an Arrhenius escape, the ramp set voltage is the mean of a minimum-Gumbel first-hop law, the programming error exceeds `c/sqrt(2 n_w)` for any kernel, and a weighted Arrhenius regression recovers the activation energy exactly. Four closed-form definitions in these domains carry no theorem.

llms.txt, formula bridge line. Add: local proofs for analog-device metrology (drift, thermionic emission, retention, ramp set voltage, programming error, pulse energy, series conductance) and for Arrhenius diffusion and Nernst-Einstein conduction.
