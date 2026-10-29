# Molecular-dynamics correlation, VACF spectrum and phonon-spectrum proofs

This batch binds seven catalog operators of the thermal_transport domain through three Lean modules: `lean/bridge/OMAIMDCorrelations.lean` (local, four operators), `lean/bridge/OMAIVACFSpectrum.lean` (local, one operator) and `lean/bridge/OMAIPhyslibPhononSpectrum.lean` (Physlib-anchored, two operators). Every bound formula is transcribed from the catalog; the theorems add hypotheses (periodic records, damped-cosine autocorrelations, a finite Physlib crystal) under which the transcribed formula has the stated property. The Lean sources came from `origin/feat/md-correlation-transport` unchanged; this batch adds the contracts, bindings, tests, registration and prose.

## Molecular-dynamics estimators (binding `md-correlation-estimators`, local)

| Operator | Lean definition | Cited theorems |
| --- | --- | --- |
| `compute_velocity_autocorrelation` | `catalogVACF` (transcribed) | `catalogMSD_eq_vacf` |
| `compute_msd` | `catalogMSD` (transcribed) | `catalogMSD_eq_vacf` |
| `autocorrelate_heat_current` | `catalogHeatACF` (transcribed) | `greenKubo_symm_eq_helfand`, `catalogHeatACF_eq_invDFT` |
| `contract_kappa[transport_model=green_kubo]` | `greenKubo` (transcribed) | `greenKubo_symm_eq_helfand` |

For a velocity record periodic over the origin window and positions advanced by `dt` times the stored velocity, the catalog MSD is `dt^2 [tau Cv(0) + 2 sum_{k=1}^{tau-1} (tau - k) Cv(k)]` in terms of the catalog VACF. For a periodic heat current with the Helfand moment advanced by `dt` times the current, the symmetrized Green-Kubo conductivity at `tau_max = m dt`, with the integral of the sampled autocorrelation taken as the integral of its piecewise-linear interpolant (the trapezoid rule, proved for either sign of `dt`), is `V (Lambda(m + 1) - Lambda(m - 1))/(4 k_B T^2 dt)`. For a periodic current the origin-averaged autocorrelation is the inverse discrete Fourier transform of `conj(F J_a) F J_b/n_lag` on `ZMod n_lag`.

Kept uncited as support: `sum_Icc_eq_sum_range`, `sum_range_shift_periodic`, `sum_Icc_shift_periodic`, `increment_eq_sum`, `double_sum_by_lag`, `increment_product_sum`, `linearInterp_eqOn`, `integral_linearInterp_piece`, `trapezoid_sum`, `integral_linearInterp_of_pos`, `integral_linearInterp`, `helfandMoment_eq`, `helfandMoment_succ_sub`, `catalogHeatACF_zero_comm` and the general correlation theorem `sum_conj_mul_shift_eq_invDFT`.

## VACF spectrum (binding `vacf-spectrum-lorentzian-limit`, local)

| Operator | Lean definition | Cited theorems |
| --- | --- | --- |
| `fourier_to_dos` | `catalogFourierDOS` (transcribed) | `catalogFourierDOS_damped`, `integral_catalogFourierDOS_damped`, `tendsto_catalogFourierDOS_zero_linewidth` |

For `Cv(tau) = sum_m A_m exp(-Gamma_m tau) cos(omega_m tau)` with every `Gamma_m > 0`, the catalog transform is `sum_m (A_m/2)[L(Gamma_m, omega - omega_m) + L(Gamma_m, omega + omega_m)]`, integrates to `Cv(0)` for every set of linewidths, and converges weakly (against integrable test functions continuous at `+-omega_m`) to `sum_m (A_m/2)(delta(omega - omega_m) + delta(omega + omega_m))` as the linewidths vanish, through Mathlib's peak-function theorem. Kept uncited: `integrableOn_exp_neg_mul_cos`, `integral_exp_neg_mul_cos`, `cos_mul_dampedVACF`, `integral_lorentzian`, `integrable_lorentzian`, `lorentzian_eq_scaled` and `unitLorentzian_peak`.

## Phonon spectrum (binding `crystal-dos-landauer-conductance`, conditional)

| Operator | Lean definition | Cited theorems |
| --- | --- | --- |
| `compute_dos` | `catalogDOS` (transcribed as a measure) | `crystalDOS_sum_rules` |
| `compute_conductance[transport_model=landauer]` | `catalogLandauer` (transcribed) | `landauerWeight_eq_heatCapacity`, `catalogLandauer_eq_heatCapacity`, `catalogLandauer_unit_transmission` |

On a finite Born-von Karman crystal of Physlib sites (the `Crystal` structure, as in the lattice-dynamics bindings), with frequencies the nonnegative square roots of the eigenvalues of the catalog dynamical matrix at every character of the translations, the density of states has total weight `3 N_cell` and, for stable force constants and positive masses, second moment `sum_i Phi_ii(0)/M_i`, by character orthogonality on the traces. The Landauer weight `hbar omega dn_BE/dT` at `omega > 0`, `T > 0` is the derivative-defined canonical heat capacity of the Physlib quantum oscillator with Physlib's `hbar` and `k_B` (the Physlib anchor, through `harmonic_heatCapacity_eq_omai` of the harmonic-ensemble module), so the conductance is the transmission-weighted spectral integral of that heat capacity; with unit transmission it is `pi^2 k_B^2 T/(3 (2 pi hbar))`, from `int_0^infinity x^2 e^x/(e^x - 1)^2 dx = pi^2/3` (the series `sum n e^{-n x}` and `zeta(2)`). Kept uncited: `integral_catalogDOS`, `sum_trace_dynamicalMatrix`, `landauerWeight_eq`, `boseKernel_eq_tsum`, `integral_sq_mul_exp_neg`, `integral_boseKernel`, `landauerWeight_eq_boseKernel`, and `catalogLandauer_unit_transmission_physlib`, which restates the unit-transmission value with Physlib's `h = 2 pi hbar` by `rfl`.

## Hypotheses

The molecular-dynamics identities assume records periodic with period `n_lag` (the circular correlation of the FFT route); a linear correlator over `n_lag + tau_max` samples is not periodic, and its end corrections are not bounded. They assume `r(t + 1) = r(t) + dt v(t)` and `G(t + 1) = G(t) + dt J(t)`, exact for finite-difference velocities of unwrapped positions and off by the integrator's `dt^2 F/(2m)` term for velocity-Verlet velocities. Nothing is claimed about ensemble averages, ergodicity, finite-trajectory bias or convergence. The Green-Kubo identity holds for every real `dt`, `k_B` and `T` (both sides vanish at zero), so the physical ranges are not hypotheses. The spectrum theorems need every linewidth positive and the damped-cosine form as an input model. The second-moment sum rule needs `Stable` force constants (energy never negative) and positive masses; the total-weight rule needs neither. The Landauer integrand identity does not establish integrability for an arbitrary transmission; the unit-transmission value is proved with the explicit Bose integral.

## Unbound

- `compute_heat_current`: catalog defect, recorded in its gap reason (below). `OMAIMDCorrelations` takes the current as an input record and proves nothing about its producer.
- `contract_diffusivity`: `D = slope/(2d)`, a definition with nothing non-obvious to prove, already recorded.
- The other thermal_transport operators keep their gap reasons; the catalog defects of the non-analytic correction, the linearized-BTE collision matrix and the cumulative conductivities are unchanged.

## Catalog issues found

- `compute_heat_current` condenses the Irving-Kirkwood current to one atom: the virial term `(1/2) sum_i r_{i,alpha} F_{i,alpha} v_{i,alpha}/V_cell` multiplies each atom's total force by its own absolute position on the same Cartesian index. It changes with the choice of origin (a shift by `a` adds `a_alpha sum_i F_{i,alpha} v_{i,alpha}/(2 V_cell)`, the rate of change of the kinetic energy along `alpha`) and with the periodic image, and it drops the off-diagonal stress components. The description's pair form `(1/2) sum_{i != j} r_{ij,alpha} (F_ij . v_i)` with `r_ij = r_i - r_j` is right, equivalently `sum_i sum_beta W_{i,alpha beta} v_{i,beta}` with the per-atom virial `W_{i,alpha beta} = (1/2) sum_{j != i} r_{ij,alpha} F_{ij,beta}` (Fan et al., Phys. Rev. B 92, 094301, 2015, for many-body potentials). Recorded as a gap reason starting with "Catalog defect."
- `fourier_to_dos` is normalized to `Cv(0)` over all frequencies and `Cv(0)/2` on `omega > 0`, in the units of `Cv`; it is proportional to, not equal to, a density of states normalized to the mode count, and the common `(2/pi) int cos Cv/Cv(0)` convention differs by `2/Cv(0)`. A normalization note, not a defect.
- `compute_dos` describes Gaussian or tetrahedron smearing (`dos_broadening`), which the delta-sum formula does not show; the measure transcription is of the formula.

## Coverage

| Measure | Before (after the electronic batch) | After this batch |
| --- | ---: | ---: |
| Operators proved | 62 / 133 | 69 / 133 |
| Physlib-anchored operators | 27 | 29 |
| Local operators | 35 | 40 |
| Nodes proved | 55 | 61 |
| Local relations | 10 | 12 |

Against `8cc4874` (origin/main before both batches, with the thermochem tranche of PR 189): 56 operators (24 anchored, 32 local) and 49 nodes.

These counts are at the branch base 8cc4874, before the merge with main. The merged ledger reads 76 of 133 operator formulas proved, 29 citing Physlib declarations and 47 local, 52 bindings.

## Review notes on the Lean sources

`OMAIMDCorrelations.lean` lines 16 to 17 call the periodic-record hypothesis "the periodic-padding assumption of FFT correlators"; FFT correlators that zero-pad are not circular, so the hypothesis is the circular (unpadded) estimator, which the binding says. `OMAIVACFSpectrum.lean` lines 9 to 12 present the catalog transform as "the vibrational density of states"; the theorems show it is `Cv(0)/2`-normalized on the positive half-line, so it is proportional to one, which the binding states. `OMAIPhyslibPhononSpectrum.lean` line 3 says "total weight 3 per unit-cell site": the theorem gives `3 * card C.UnitCell`, three per unit-cell site as stated. Nothing looked overstated.

## Prose for site and paper

For `docs/llms.txt`: molecular-dynamics estimators (local proofs over Mathlib): for records periodic over the origin window the catalog MSD is the Green-Kubo sum of the catalog VACF, the trapezoid Green-Kubo conductivity is the central-difference Einstein-Helfand estimator, and the origin-averaged heat-current autocorrelation is the inverse DFT of the cross spectrum; the VACF cosine transform of damped modes is a sum of Lorentzians that integrates to `Cv(0)` and tends to the harmonic delta sum. Physlib-anchored: the phonon density of states on a Physlib crystal obeys its count and second-moment sum rules, and the Landauer weight is the Physlib oscillator heat capacity, so unit transmission gives the conductance quantum `pi^2 k_B^2 T/(3h)`. The MD heat-current formula is a recorded defect.

For the paper (Lean layer paragraph): The molecular-dynamics estimators are transcribed and proved as discrete identities for records periodic over the origin window: the mean squared displacement is the Green-Kubo sum of the velocity autocorrelation, the trapezoid Green-Kubo conductivity is the central-difference Einstein-Helfand estimator, and the origin-averaged heat-current autocorrelation is the inverse discrete Fourier transform of the cross spectrum; the cosine transform of a sum of damped cosines is a sum of Lorentzians that integrates to the zero-lag value and tends weakly to the harmonic delta sum as the linewidths vanish. On a finite Born-von Karman crystal of Physlib sites the catalog density of states has total weight `3 N_cell` and second moment `sum_i Phi_ii(0)/M_i`, and the Landauer weight is the Physlib oscillator heat capacity, so unit transmission gives the conductance quantum. The catalog's heat-current formula multiplies each atom's total force by its own absolute position and is recorded as a defect.
