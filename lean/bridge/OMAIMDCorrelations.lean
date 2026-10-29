module

public import Mathlib.Analysis.Fourier.ZMod
public import Mathlib.Analysis.SpecialFunctions.Integrals.Basic
public import Mathlib.Tactic

/-!
# Time-correlation estimators of molecular dynamics

The catalog estimates the velocity autocorrelation, the mean squared displacement and the
heat-current autocorrelation from a sampled trajectory by averaging over time origins
`t = 1, ..., n_lag`, and reads the diffusivity off the MSD slope and the thermal conductivity
off the Green-Kubo integral of the current autocorrelation. Physlib has no model of a molecular
dynamics trajectory, so these are local theorems over Mathlib.

For a sampled record that is periodic over the origin window (the periodic-padding assumption
of FFT correlators) and whose integrated quantity advances by `dt` times the sampled rate
(positions by `dt` times the stored velocity, the Helfand moment by `dt` times the current):

* the catalog's MSD is `dt^2 [tau Cv(0) + 2 sum_{k=1}^{tau-1} (tau - k) Cv(k)]` in terms of the
  catalog's VACF, so the Einstein slope of the MSD is the Green-Kubo sum of the VACF;
* the symmetrized Green-Kubo conductivity, with the integral of the sampled autocorrelation
  evaluated by the trapezoid rule (the exact integral of its piecewise-linear interpolant), is
  the central-difference Einstein-Helfand estimator;
* the direct origin-averaged autocorrelation is the inverse discrete Fourier transform of the
  cross spectrum, the FFT route.

No statement is made about ensemble averages, ergodicity, finite-trajectory bias or the
convergence of any estimator in the length of the trajectory.
-/

@[expose] public section

noncomputable section

open Finset

namespace OMAI.PhyslibBridge.MDCorrelations

/-- The reviewed catalog expression of `compute_velocity_autocorrelation`,
`Cv(tau) = sum_t sum_i sum_a v_ia(t) v_ia(t + tau) / (N_atoms n_lag)` over origins
`t = 1, ..., n_lag`. This definition alone is not a physical proof. -/
def catalogVACF (N n : ℕ) (v : Fin N → Fin 3 → ℕ → ℝ) (tau : ℕ) : ℝ :=
  (∑ t ∈ Icc 1 n, ∑ i, ∑ a, v i a t * v i a (t + tau)) / (N * n)

/-- The reviewed catalog expression of `compute_msd`,
`M(tau) = sum_t sum_i sum_a (r_ia(t + tau) - r_ia(t))^2 / (N_atoms n_lag)`. This definition alone
is not a physical proof. -/
def catalogMSD (N n : ℕ) (r : Fin N → Fin 3 → ℕ → ℝ) (tau : ℕ) : ℝ :=
  (∑ t ∈ Icc 1 n, ∑ i, ∑ a, (r i a (t + tau) - r i a t) ^ 2) / (N * n)

/-- The reviewed catalog expression of `autocorrelate_heat_current`,
`Jcorr_ab(tau) = sum_t J_a(t) J_b(t + tau) / n_lag`. This definition alone is not a physical
proof. -/
def catalogHeatACF (n : ℕ) (J : Fin 3 → ℕ → ℝ) (a b : Fin 3) (tau : ℕ) : ℝ :=
  (∑ t ∈ Icc 1 n, J a t * J b (t + tau)) / n

/-- The reviewed catalog expression of `contract_kappa[transport_model=green_kubo]`,
`kappa = V int_0^tau_max Jcorr(tau) d tau / (k_B T^2)`. This definition alone is not a physical
proof. -/
def greenKubo (V T kB tauMax : ℝ) (Jcorr : ℝ → ℝ) : ℝ :=
  V * (∫ tau in (0 : ℝ)..tauMax, Jcorr tau) / (kB * T ^ 2)

/-- The origin sum `sum_{t=1}^{n} x(t) y(t + k)`. -/
def lagSum (x y : ℕ → ℝ) (n k : ℕ) : ℝ := ∑ t ∈ Icc 1 n, x t * y (t + k)

/-! ## Periodic records -/

theorem sum_Icc_eq_sum_range (f : ℕ → ℝ) (n : ℕ) :
    ∑ t ∈ Icc 1 n, f t = ∑ t ∈ range n, f (t + 1) := by
  rw [← Finset.Ico_add_one_right_eq_Icc, sum_Ico_eq_sum_range]
  simp only [Nat.add_sub_cancel]
  exact sum_congr rfl fun t _ => by rw [add_comm]

theorem sum_range_shift_periodic {f : ℕ → ℝ} {n : ℕ} (hf : ∀ t, f (t + n) = f t) (s : ℕ) :
    ∑ t ∈ range n, f (t + s) = ∑ t ∈ range n, f t := by
  induction s with
  | zero => simp
  | succ s ih =>
    have h1 : ∑ t ∈ range n, f (t + (s + 1)) = ∑ t ∈ range n, f (t + 1 + s) := by
      refine sum_congr rfl fun t _ => ?_
      congr 1
      omega
    rw [h1, ← ih]
    have h2 := sum_range_succ (fun t => f (t + s)) n
    have h3 := sum_range_succ' (fun t => f (t + s)) n
    have h4 : f (n + s) = f (0 + s) := by rw [zero_add, add_comm n s, hf]
    linarith

theorem sum_Icc_shift_periodic {f : ℕ → ℝ} {n : ℕ} (hf : ∀ t, f (t + n) = f t) (s : ℕ) :
    ∑ t ∈ Icc 1 n, f (t + s) = ∑ t ∈ Icc 1 n, f t := by
  rw [sum_Icc_eq_sum_range, sum_Icc_eq_sum_range]
  have hg : ∀ t, f (t + n + 1) = f (t + 1) := fun t => by
    have := hf (t + 1)
    rwa [show t + 1 + n = t + n + 1 by omega] at this
  have := sum_range_shift_periodic (f := fun t => f (t + 1)) (n := n) hg s
  rw [← this]
  refine sum_congr rfl fun t _ => ?_
  congr 1
  omega

/-- An integrated record advanced by `dt` times the sampled rate. -/
theorem increment_eq_sum {X x : ℕ → ℝ} {dt : ℝ} (hX : ∀ t, X (t + 1) = X t + dt * x t)
    (t tau : ℕ) : X (t + tau) - X t = dt * ∑ s ∈ range tau, x (t + s) := by
  induction tau with
  | zero => simp
  | succ tau ih =>
    rw [sum_range_succ, ← add_assoc, hX, mul_add, ← ih]
    ring

/-- Pair sums over a window of `tau` lags, grouped by the lag difference. -/
theorem double_sum_by_lag (A B : ℕ → ℝ) (tau : ℕ) :
    ∑ s ∈ range tau, ∑ s' ∈ range tau, (if s ≤ s' then A (s' - s) else B (s - s')) =
      tau * A 0 + ∑ k ∈ Ico 1 tau, ((tau : ℝ) - k) * (A k + B k) := by
  induction tau with
  | zero => simp
  | succ tau ih =>
    have hrefl : ∀ C : ℕ → ℝ, ∑ s ∈ range tau, C (tau - s) = ∑ k ∈ Ico 1 (tau + 1), C k := by
      intro C
      rw [sum_Ico_eq_sum_range, Nat.add_sub_cancel, ← sum_range_reflect]
      refine sum_congr rfl fun j hj => ?_
      have := mem_range.1 hj
      congr 1
      omega
    have hcol : ∑ s ∈ range tau, (if s ≤ tau then A (tau - s) else B (s - tau)) =
        ∑ k ∈ Ico 1 (tau + 1), A k := by
      have h : ∀ s ∈ range tau, (if s ≤ tau then A (tau - s) else B (s - tau)) = A (tau - s) :=
        fun s hs => by simp [le_of_lt (mem_range.1 hs)]
      rw [sum_congr rfl h, hrefl]
    have hrow : ∑ s' ∈ range tau, (if tau ≤ s' then A (s' - tau) else B (tau - s')) =
        ∑ k ∈ Ico 1 (tau + 1), B k := by
      have h : ∀ s' ∈ range tau, (if tau ≤ s' then A (s' - tau) else B (tau - s')) = B (tau - s') :=
        fun s' hs' => by simp [not_le.2 (mem_range.1 hs')]
      rw [sum_congr rfl h, hrefl]
    rw [sum_range_succ]
    simp only [sum_range_succ (fun s' => if _ ≤ s' then _ else _)]
    rw [sum_add_distrib, ih, hcol, hrow]
    simp only [le_refl, ↓reduceIte, Nat.sub_self]
    rcases Nat.eq_zero_or_pos tau with h | h
    · subst h
      simp
    · have h1 : 1 ≤ tau := h
      have hshift : ∑ k ∈ Ico 1 tau, (((tau + 1 : ℕ) : ℝ) - k) * (A k + B k) =
          ∑ k ∈ Ico 1 tau, ((tau : ℝ) - k) * (A k + B k) + ∑ k ∈ Ico 1 tau, (A k + B k) := by
        rw [← sum_add_distrib]
        refine sum_congr rfl fun k _ => ?_
        push_cast
        ring
      rw [sum_Ico_succ_top h1 (fun k => A k), sum_Ico_succ_top h1 (fun k => B k),
        sum_Ico_succ_top h1, hshift, sum_add_distrib]
      push_cast
      ring

/-! ## The Einstein-Helfand identity -/

/-- For records periodic over the origin window, the origin-summed product of two increments
over `tau` steps is a weighted sum of the lagged correlations: the discrete form of
`<dX dY>(tau) = int_0^tau int_0^tau C(s' - s) ds ds'`. -/
theorem increment_product_sum {x y X Y : ℕ → ℝ} {n : ℕ} {dt : ℝ}
    (hX : ∀ t, X (t + 1) = X t + dt * x t) (hY : ∀ t, Y (t + 1) = Y t + dt * y t)
    (hx : ∀ t, x (t + n) = x t) (hy : ∀ t, y (t + n) = y t) (tau : ℕ) :
    ∑ t ∈ Icc 1 n, (X (t + tau) - X t) * (Y (t + tau) - Y t) =
      dt ^ 2 * (tau * lagSum x y n 0 +
        ∑ k ∈ Ico 1 tau, ((tau : ℝ) - k) * (lagSum x y n k + lagSum y x n k)) := by
  have hpair : ∀ s s', ∑ t ∈ Icc 1 n, x (t + s) * y (t + s') =
      if s ≤ s' then lagSum x y n (s' - s) else lagSum y x n (s - s') := by
    intro s s'
    split_ifs with h
    · have hf : ∀ u, x (u + n) * y (u + n + (s' - s)) = x u * y (u + (s' - s)) := fun u => by
        rw [hx, show u + n + (s' - s) = u + (s' - s) + n by omega, hy]
      have := sum_Icc_shift_periodic (f := fun u => x u * y (u + (s' - s))) (n := n) hf s
      unfold lagSum
      rw [← this]
      refine sum_congr rfl fun t _ => ?_
      congr 2
      omega
    · have hf : ∀ u, y (u + n) * x (u + n + (s - s')) = y u * x (u + (s - s')) := fun u => by
        rw [hy, show u + n + (s - s') = u + (s - s') + n by omega, hx]
      have := sum_Icc_shift_periodic (f := fun u => y u * x (u + (s - s'))) (n := n) hf s'
      unfold lagSum
      rw [← this]
      refine sum_congr rfl fun t _ => ?_
      rw [mul_comm]
      congr 2
      omega
  calc ∑ t ∈ Icc 1 n, (X (t + tau) - X t) * (Y (t + tau) - Y t)
      = ∑ t ∈ Icc 1 n, dt ^ 2 *
          ∑ s ∈ range tau, ∑ s' ∈ range tau, x (t + s) * y (t + s') := by
        refine sum_congr rfl fun t _ => ?_
        rw [increment_eq_sum hX, increment_eq_sum hY, mul_mul_mul_comm, sum_mul_sum, ← pow_two]
    _ = dt ^ 2 * ∑ s ∈ range tau, ∑ s' ∈ range tau, ∑ t ∈ Icc 1 n, x (t + s) * y (t + s') := by
        rw [← mul_sum]
        congr 1
        rw [sum_comm]
        refine sum_congr rfl fun s _ => ?_
        rw [sum_comm]
    _ = _ := by
        simp only [hpair]
        rw [double_sum_by_lag]

/-- On a velocity record periodic over the origin window, with positions advanced by `dt`
times the stored velocity, the catalog's mean squared displacement is
`dt^2 [tau Cv(0) + 2 sum_{k=1}^{tau-1} (tau - k) Cv(k)]` with `Cv` the catalog's velocity
autocorrelation: the Einstein and Green-Kubo diffusion estimators are the same function of the
trajectory. -/
theorem catalogMSD_eq_vacf {N n : ℕ} {dt : ℝ} {r v : Fin N → Fin 3 → ℕ → ℝ}
    (hr : ∀ i a t, r i a (t + 1) = r i a t + dt * v i a t)
    (hv : ∀ i a t, v i a (t + n) = v i a t) (tau : ℕ) :
    catalogMSD N n r tau = dt ^ 2 * (tau * catalogVACF N n v 0 +
      2 * ∑ k ∈ Ico 1 tau, ((tau : ℝ) - k) * catalogVACF N n v k) := by
  have hcomp : ∀ i a, ∑ t ∈ Icc 1 n, (r i a (t + tau) - r i a t) ^ 2 =
      dt ^ 2 * (tau * lagSum (v i a) (v i a) n 0 +
        2 * ∑ k ∈ Ico 1 tau, ((tau : ℝ) - k) * lagSum (v i a) (v i a) n k) := by
    intro i a
    have := increment_product_sum (hr i a) (hr i a) (hv i a) (hv i a) tau
    simp only [← sq] at this
    rw [this]
    congr 2
    rw [mul_sum]
    exact sum_congr rfl fun k _ => by ring
  have hvacf : ∀ k, (∑ t ∈ Icc 1 n, ∑ i, ∑ a, v i a t * v i a (t + k)) =
      ∑ i, ∑ a, lagSum (v i a) (v i a) n k := by
    intro k
    unfold lagSum
    rw [sum_comm]
    exact sum_congr rfl fun i _ => sum_comm
  have hmsd : (∑ t ∈ Icc 1 n, ∑ i, ∑ a, (r i a (t + tau) - r i a t) ^ 2) =
      ∑ i, ∑ a, ∑ t ∈ Icc 1 n, (r i a (t + tau) - r i a t) ^ 2 := by
    rw [sum_comm]
    exact sum_congr rfl fun i _ => sum_comm
  set L := fun (i : Fin N) (a : Fin 3) k => lagSum (v i a) (v i a) n k with hL
  have key : ∑ i, ∑ a, dt ^ 2 * (tau * L i a 0 + 2 * ∑ k ∈ Ico 1 tau, ((tau : ℝ) - k) * L i a k) =
      dt ^ 2 * (tau * ∑ i, ∑ a, L i a 0 +
        2 * ∑ k ∈ Ico 1 tau, ((tau : ℝ) - k) * ∑ i, ∑ a, L i a k) := by
    have h1 : ∑ k ∈ Ico 1 tau, ((tau : ℝ) - k) * ∑ i, ∑ a, L i a k =
        ∑ i, ∑ a, ∑ k ∈ Ico 1 tau, ((tau : ℝ) - k) * L i a k := by
      simp only [mul_sum]
      rw [sum_comm]
      exact sum_congr rfl fun i _ => sum_comm
    rw [h1]
    simp only [mul_add, sum_add_distrib, mul_sum]
  unfold catalogMSD catalogVACF
  rw [hmsd]
  simp only [hcomp, hvacf]
  change (∑ i, ∑ a, dt ^ 2 * (tau * L i a 0 + 2 * ∑ k ∈ Ico 1 tau, ((tau : ℝ) - k) * L i a k)) /
      (N * n) = dt ^ 2 * (tau * ((∑ i, ∑ a, L i a 0) / (N * n)) +
        2 * ∑ k ∈ Ico 1 tau, ((tau : ℝ) - k) * ((∑ i, ∑ a, L i a k) / (N * n)))
  rw [key]
  simp only [div_eq_mul_inv]
  have h2 : ∑ k ∈ Ico 1 tau, ((tau : ℝ) - k) * ((∑ i, ∑ a, L i a k) * ((N : ℝ) * n)⁻¹) =
      (∑ k ∈ Ico 1 tau, ((tau : ℝ) - k) * ∑ i, ∑ a, L i a k) * ((N : ℝ) * n)⁻¹ := by
    rw [sum_mul]
    exact sum_congr rfl fun k _ => by ring
  rw [h2]
  ring

/-! ## Green-Kubo and Einstein-Helfand conductivity -/

/-- The Helfand mean squared moment `sum_t (G_a(t + tau) - G_a(t)) (G_b(t + tau) - G_b(t)) / n`
of an integrated heat current `G`. -/
def helfandMoment (n : ℕ) (G : Fin 3 → ℕ → ℝ) (a b : Fin 3) (tau : ℕ) : ℝ :=
  (∑ t ∈ Icc 1 n, (G a (t + tau) - G a t) * (G b (t + tau) - G b t)) / n

/-- The piecewise-linear interpolant through the samples `c k` at the times `k dt`. -/
def linearInterp (dt : ℝ) (c : ℕ → ℝ) (s : ℝ) : ℝ :=
  c ⌊s / dt⌋₊ + (c (⌊s / dt⌋₊ + 1) - c ⌊s / dt⌋₊) * (s / dt - ⌊s / dt⌋₊)

theorem linearInterp_eqOn {dt : ℝ} (hdt : 0 < dt) (c : ℕ → ℝ) (k : ℕ) :
    Set.EqOn (linearInterp dt c) (fun s => c k + (c (k + 1) - c k) * (s / dt - k))
      (Set.Icc (k * dt) ((k + 1) * dt)) := by
  intro s hs
  have h0 : (k : ℝ) ≤ s / dt := by rw [le_div_iff₀ hdt]; exact hs.1
  have h1 : s / dt ≤ k + 1 := by rw [div_le_iff₀ hdt]; exact hs.2
  have hnn : 0 ≤ s / dt := le_trans (Nat.cast_nonneg k) h0
  rcases lt_or_eq_of_le h1 with hlt | heq
  · have hf : ⌊s / dt⌋₊ = k := (Nat.floor_eq_iff hnn).2 ⟨h0, hlt⟩
    simp only [linearInterp, hf]
  · have hf : ⌊s / dt⌋₊ = k + 1 := by
      rw [heq]; exact_mod_cast Nat.floor_natCast (k + 1)
    simp only [linearInterp]
    rw [hf, heq]
    push_cast
    ring

theorem integral_linearInterp_piece {dt : ℝ} (hdt : 0 < dt) (c : ℕ → ℝ) (k : ℕ) :
    ∫ s in (k * dt)..((k + 1) * dt), linearInterp dt c s = dt * (c k + c (k + 1)) / 2 := by
  rw [intervalIntegral.integral_congr (fun s hs => linearInterp_eqOn hdt c k
    (by rwa [Set.uIcc_of_le (by nlinarith)] at hs))]
  have hderiv : ∀ s ∈ Set.uIcc (k * dt) ((k + 1) * dt),
      HasDerivAt (fun s => c k * s + (c (k + 1) - c k) * (s ^ 2 / (2 * dt) - k * s))
        (c k + (c (k + 1) - c k) * (s / dt - k)) s := by
    intro s _
    have := (((hasDerivAt_id s).const_mul (c k)).add
      ((((hasDerivAt_pow 2 s).div_const (2 * dt)).sub
        ((hasDerivAt_id s).const_mul (k : ℝ))).const_mul (c (k + 1) - c k)))
    convert this using 1
    · ext y
      simp
    · field_simp
      push_cast
      ring
  rw [intervalIntegral.integral_eq_sub_of_hasDerivAt hderiv
    (by apply Continuous.intervalIntegrable; fun_prop)]
  field_simp
  ring

theorem trapezoid_sum (dt : ℝ) (c : ℕ → ℝ) {m : ℕ} (hm : 1 ≤ m) :
    ∑ k ∈ range m, dt * (c k + c (k + 1)) / 2 = dt * (c 0 / 2 + ∑ k ∈ Ico 1 m, c k + c m / 2) := by
  induction m, hm using Nat.le_induction with
  | base => simp; ring
  | succ m hm ih =>
    rw [sum_range_succ, ih, sum_Ico_succ_top hm]
    ring

theorem integral_linearInterp_of_pos {dt : ℝ} (hdt : 0 < dt) (c : ℕ → ℝ) {m : ℕ} (hm : 1 ≤ m) :
    ∫ s in (0 : ℝ)..(m * dt), linearInterp dt c s =
      dt * (c 0 / 2 + ∑ k ∈ Ico 1 m, c k + c m / 2) := by
  have hint : ∀ k < m, IntervalIntegrable (linearInterp dt c) MeasureTheory.volume
      ((k : ℝ) * dt) (((k + 1 : ℕ) : ℝ) * dt) := by
    intro k _
    push_cast
    apply ContinuousOn.intervalIntegrable
    rw [Set.uIcc_of_le (by nlinarith)]
    exact (Continuous.continuousOn (by fun_prop)).congr (linearInterp_eqOn hdt c k)
  have hsum := intervalIntegral.sum_integral_adjacent_intervals (a := fun k : ℕ => (k : ℝ) * dt) hint
  simp only [Nat.cast_zero, zero_mul] at hsum
  rw [← hsum, ← trapezoid_sum dt c hm]
  exact sum_congr rfl fun k _ => by rw [← integral_linearInterp_piece hdt c k]; push_cast; rfl

/-- The integral of the piecewise-linear interpolant is the trapezoid rule on the samples, for a
time step of either sign. -/
theorem integral_linearInterp (dt : ℝ) (c : ℕ → ℝ) {m : ℕ} (hm : 1 ≤ m) :
    ∫ s in (0 : ℝ)..(m * dt), linearInterp dt c s =
      dt * (c 0 / 2 + ∑ k ∈ Ico 1 m, c k + c m / 2) := by
  rcases lt_trichotomy dt 0 with hneg | hzero | hpos
  · have hflip : (fun s => linearInterp dt c s) = fun s => linearInterp (-dt) c (-s) := by
      funext s
      simp only [linearInterp, neg_div_neg_eq]
    rw [hflip, intervalIntegral.integral_comp_neg (fun s => linearInterp (-dt) c s), neg_zero,
      intervalIntegral.integral_symm, show -(m * dt) = m * -dt by ring,
      integral_linearInterp_of_pos (neg_pos.2 hneg) c hm]
    ring
  · subst hzero
    simp
  · exact integral_linearInterp_of_pos hpos c hm

theorem helfandMoment_eq {n : ℕ} {dt : ℝ} {J G : Fin 3 → ℕ → ℝ}
    (hG : ∀ a t, G a (t + 1) = G a t + dt * J a t) (hJ : ∀ a t, J a (t + n) = J a t)
    (a b : Fin 3) (tau : ℕ) :
    helfandMoment n G a b tau = dt ^ 2 * (tau * catalogHeatACF n J a b 0 +
      ∑ k ∈ Ico 1 tau, ((tau : ℝ) - k) * (catalogHeatACF n J a b k + catalogHeatACF n J b a k)) := by
  unfold helfandMoment catalogHeatACF
  rw [increment_product_sum (hG a) (hG b) (hJ a) (hJ b) tau]
  unfold lagSum
  have h : ∑ k ∈ Ico 1 tau, ((tau : ℝ) - k) * ((∑ t ∈ Icc 1 n, J a t * J b (t + k)) / n +
      (∑ t ∈ Icc 1 n, J b t * J a (t + k)) / n) =
      (∑ k ∈ Ico 1 tau, ((tau : ℝ) - k) * ((∑ t ∈ Icc 1 n, J a t * J b (t + k)) +
        (∑ t ∈ Icc 1 n, J b t * J a (t + k)))) / n := by
    rw [sum_div]
    exact sum_congr rfl fun k _ => by ring
  rw [h]
  ring

theorem helfandMoment_succ_sub {n : ℕ} {dt : ℝ} {J G : Fin 3 → ℕ → ℝ}
    (hG : ∀ a t, G a (t + 1) = G a t + dt * J a t) (hJ : ∀ a t, J a (t + n) = J a t)
    (a b : Fin 3) (tau : ℕ) :
    helfandMoment n G a b (tau + 1) - helfandMoment n G a b tau =
      dt ^ 2 * (catalogHeatACF n J a b 0 +
        ∑ k ∈ Ico 1 (tau + 1), (catalogHeatACF n J a b k + catalogHeatACF n J b a k)) := by
  rw [helfandMoment_eq hG hJ, helfandMoment_eq hG hJ]
  rcases Nat.eq_zero_or_pos tau with h | h
  · subst h; simp
  · have h1 : 1 ≤ tau := h
    rw [sum_Ico_succ_top h1, sum_Ico_succ_top h1]
    have hshift : ∑ k ∈ Ico 1 tau, (((tau + 1 : ℕ) : ℝ) - k) *
        (catalogHeatACF n J a b k + catalogHeatACF n J b a k) =
        ∑ k ∈ Ico 1 tau, ((tau : ℝ) - k) * (catalogHeatACF n J a b k + catalogHeatACF n J b a k) +
          ∑ k ∈ Ico 1 tau, (catalogHeatACF n J a b k + catalogHeatACF n J b a k) := by
      rw [← sum_add_distrib]
      exact sum_congr rfl fun k _ => by push_cast; ring
    rw [hshift]
    push_cast
    ring

theorem catalogHeatACF_zero_comm (n : ℕ) (J : Fin 3 → ℕ → ℝ) (a b : Fin 3) :
    catalogHeatACF n J a b 0 = catalogHeatACF n J b a 0 := by
  unfold catalogHeatACF
  simp only [add_zero, mul_comm]

/-- For a heat current periodic over the origin window, with the Helfand moment advanced by `dt`
times the current, the symmetrized Green-Kubo conductivity at `tau_max = m dt`, with the integral
of the sampled catalog autocorrelation evaluated by the trapezoid rule (the exact integral of its
piecewise-linear interpolant), is the central-difference Einstein-Helfand estimator
`V (Lambda(m + 1) - Lambda(m - 1)) / (4 k_B T^2 dt)`. -/
theorem greenKubo_symm_eq_helfand {n m : ℕ} {dt V T kB : ℝ} (hm : 1 ≤ m)
    {J G : Fin 3 → ℕ → ℝ} (hG : ∀ a t, G a (t + 1) = G a t + dt * J a t)
    (hJ : ∀ a t, J a (t + n) = J a t) (a b : Fin 3) :
    (greenKubo V T kB (m * dt) (linearInterp dt (catalogHeatACF n J a b)) +
        greenKubo V T kB (m * dt) (linearInterp dt (catalogHeatACF n J b a))) / 2 =
      V / (4 * kB * T ^ 2 * dt) *
        (helfandMoment n G a b (m + 1) - helfandMoment n G a b (m - 1)) := by
  obtain ⟨p, rfl⟩ : ∃ p, m = p + 1 := ⟨m - 1, by omega⟩
  have hd1 := helfandMoment_succ_sub hG hJ a b (p + 1)
  have hd0 := helfandMoment_succ_sub hG hJ a b p
  have hsplit : helfandMoment n G a b (p + 1 + 1) - helfandMoment n G a b (p + 1 - 1) =
      (helfandMoment n G a b (p + 1 + 1) - helfandMoment n G a b (p + 1)) +
        (helfandMoment n G a b (p + 1) - helfandMoment n G a b p) := by
    rw [Nat.add_sub_cancel]; ring
  rw [hsplit, hd1, hd0]
  unfold greenKubo
  rw [integral_linearInterp dt _ hm, integral_linearInterp dt _ hm,
    catalogHeatACF_zero_comm n J b a, sum_Ico_succ_top (by omega : 1 ≤ p + 1)]
  rw [show (∑ k ∈ Ico 1 (p + 1), (catalogHeatACF n J a b k + catalogHeatACF n J b a k)) =
      ∑ k ∈ Ico 1 (p + 1), catalogHeatACF n J a b k + ∑ k ∈ Ico 1 (p + 1), catalogHeatACF n J b a k
      from sum_add_distrib]
  rcases eq_or_ne dt 0 with hdt | hdt
  · subst hdt; simp
  rcases eq_or_ne kB 0 with hk | hk
  · subst hk; simp
  rcases eq_or_ne T 0 with hT | hT
  · subst hT; simp
  field_simp
  ring

/-! ## The FFT route to the autocorrelation -/

open ZMod in
/-- Correlation theorem on `ZMod n`: the origin sum of `conj (x j) y (j + tau)` is the inverse
discrete Fourier transform of the cross spectrum `conj (F x) * F y`. -/
theorem sum_conj_mul_shift_eq_invDFT {n : ℕ} [NeZero n] (x y : ZMod n → ℂ) (tau : ZMod n) :
    ∑ j, (starRingEnd ℂ) (x j) * y (j + tau) =
      𝓕⁻ (fun k => (starRingEnd ℂ) (𝓕 x k) * 𝓕 y k) tau := by
  have hy : ∀ j, y (j + tau) = (n : ℂ)⁻¹ * ∑ k, stdAddChar (k * (j + tau)) * 𝓕 y k := fun j => by
    conv_lhs => rw [← LinearEquiv.symm_apply_apply dft y]
    rw [invDFT_apply]
    simp only [smul_eq_mul]
  have hx : ∀ k, (starRingEnd ℂ) (𝓕 x k) = ∑ j, stdAddChar (j * k) * (starRingEnd ℂ) (x j) :=
    fun k => by
      rw [dft_apply, map_sum]
      refine sum_congr rfl fun j _ => ?_
      rw [smul_eq_mul, map_mul, AddChar.map_neg_eq_conj, Complex.conj_conj]
  rw [invDFT_apply]
  simp only [smul_eq_mul, hx, hy]
  simp only [mul_sum, sum_mul]
  rw [sum_comm]
  refine sum_congr rfl fun k _ => sum_congr rfl fun j _ => ?_
  rw [show k * (j + tau) = j * k + k * tau by ring, AddChar.map_add_eq_mul]
  ring

open ZMod in
/-- For a heat current periodic over the origin window, the catalog's direct origin-averaged
autocorrelation equals the FFT route: the inverse discrete Fourier transform of the cross
spectrum `conj (F J_a) F J_b / n` of one period. -/
theorem catalogHeatACF_eq_invDFT {n : ℕ} [NeZero n] {J : Fin 3 → ℕ → ℝ}
    (hJ : ∀ a t, J a (t + n) = J a t) (a b : Fin 3) (tau : ℕ) :
    (catalogHeatACF n J a b tau : ℂ) =
      𝓕⁻ (fun k => (starRingEnd ℂ) (𝓕 (fun j : ZMod n => (J a j.val : ℂ)) k) *
        𝓕 (fun j : ZMod n => (J b j.val : ℂ)) k / n) (tau : ZMod n) := by
  have hper : ∀ c t, J c t = J c (t % n) := by
    intro c t
    conv_lhs => rw [← Nat.mod_add_div t n]
    induction t / n with
    | zero => simp
    | succ q ih => rw [show t % n + n * (q + 1) = t % n + n * q + n by ring, hJ, ih]
  have hsum : ∑ t ∈ Icc 1 n, J a t * J b (t + tau) =
      ∑ j : ZMod n, J a j.val * J b ((j + (tau : ZMod n)).val) := by
    have hf : ∀ t, J a (t + n) * J b (t + n + tau) = J a t * J b (t + tau) := fun t => by
      rw [hJ, show t + n + tau = t + tau + n by omega, hJ]
    rw [sum_Icc_eq_sum_range, show (∑ t ∈ range n, J a (t + 1) * J b (t + 1 + tau)) =
      ∑ t ∈ range n, J a t * J b (t + tau) from
        sum_range_shift_periodic (f := fun t => J a t * J b (t + tau)) (n := n) hf 1]
    have hz : ∀ g : ℕ → ℝ, ∑ j : ZMod n, g j.val = ∑ t ∈ range n, g t := fun g =>
      Finset.sum_nbij (fun j : ZMod n => j.val) (fun j _ => mem_range.2 (ZMod.val_lt j))
        (fun j _ k _ h => ZMod.val_injective n h)
        (fun t ht => ⟨(t : ZMod n), mem_univ _, ZMod.val_natCast_of_lt (mem_range.1 ht)⟩)
        (fun j _ => rfl)
    rw [← hz (fun t => J a t * J b (t + tau))]
    refine sum_congr rfl fun j _ => ?_
    congr 1
    rw [ZMod.val_add, ZMod.val_natCast, Nat.add_mod_mod, ← hper]
  have hlin : (fun k => (starRingEnd ℂ) (𝓕 (fun j : ZMod n => (J a j.val : ℂ)) k) *
      𝓕 (fun j : ZMod n => (J b j.val : ℂ)) k / n) =
      (n : ℂ)⁻¹ • fun k => (starRingEnd ℂ) (𝓕 (fun j : ZMod n => (J a j.val : ℂ)) k) *
        𝓕 (fun j : ZMod n => (J b j.val : ℂ)) k := by
    ext k
    simp [div_eq_mul_inv, mul_comm]
  have key := sum_conj_mul_shift_eq_invDFT (fun j : ZMod n => (J a j.val : ℂ))
    (fun j => (J b j.val : ℂ)) (tau : ZMod n)
  simp only [Complex.conj_ofReal] at key
  rw [hlin, LinearEquiv.map_smul, Pi.smul_apply, smul_eq_mul, ← key, catalogHeatACF, hsum]
  push_cast
  ring

end OMAI.PhyslibBridge.MDCorrelations
