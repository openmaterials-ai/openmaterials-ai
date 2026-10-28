module

public import Mathlib.Analysis.SpecialFunctions.Log.Deriv
public import Mathlib.Tactic

/-!
# Arrhenius diffusion and Nernst-Einstein conduction

The catalog fits diffusivities to the Arrhenius law `D(T) = D_0 exp(-E_a / (T k_B))` by a
weighted regression and converts a diffusivity into an ionic conductivity with the
Nernst-Einstein relation `sigma = D e^2 n_c z^2 / (T k_B)`. Physlib has no model of
solid-state diffusion, so these results use Mathlib only and identify no Physlib
declaration.

* The weighted least-squares slope of `log D` against `1/T` returns `-E_a / k_B` exactly on
  Arrhenius data, for every choice of positive weights and at least two distinct
  temperatures.
* For an Arrhenius diffusivity and a temperature-independent carrier density, `sigma T` is
  Arrhenius with the diffusion barrier `E_a`, while `sigma` alone has the apparent
  activation energy `E_a - k_B T`.

No result validates a molecular-dynamics producer of the diffusivity or a measured
conductivity.
-/

@[expose] public section

noncomputable section

open Real Finset Filter Topology

namespace OMAI.PhyslibBridge.MaterialsTransport

/-- The reviewed catalog expression of `fit_arrhenius`, `D(T) = D_0 exp(-E_a / (T k_B))`.
This definition alone is not a physical proof. -/
def arrheniusDiffusivity (D0 Ea kB T : ℝ) : ℝ := D0 * exp (-Ea / (T * kB))

/-- The reviewed catalog expression of `compute_ionic_conductivity`,
`sigma_ion = D e_c^2 n_c z^2 / (T k_B)`, with inputs CarrierDensity, Diffusivity and
Temperature. This definition alone is not a physical proof. -/
def ionicConductivity (nc D T z ec kB : ℝ) : ℝ := D * ec ^ 2 * nc * z ^ 2 / (T * kB)

/-- The weighted least-squares slope of the points `(x_i, y_i)` with weights `w_i`. -/
def wlsSlope {n : ℕ} (w x y : Fin n → ℝ) : ℝ :=
  (∑ i, w i * (x i - (∑ j, w j * x j) / ∑ j, w j) * (y i - (∑ j, w j * y j) / ∑ j, w j)) /
    ∑ i, w i * (x i - (∑ j, w j * x j) / ∑ j, w j) ^ 2

theorem wlsSlope_affine {n : ℕ} (w x : Fin n → ℝ) (a b : ℝ) (hW : ∑ j, w j ≠ 0)
    (hD : ∑ i, w i * (x i - (∑ j, w j * x j) / ∑ j, w j) ^ 2 ≠ 0) :
    wlsSlope w x (fun i => a + b * x i) = b := by
  unfold wlsSlope
  set xbar := (∑ j, w j * x j) / ∑ j, w j
  have hy : (∑ j, w j * (a + b * x j)) / ∑ j, w j = a + b * xbar := by
    simp only [xbar, mul_add, sum_add_distrib, ← sum_mul, mul_left_comm _ b, ← mul_sum]
    field_simp
  rw [hy]
  have hnum : ∑ i, w i * (x i - xbar) * (a + b * x i - (a + b * xbar)) =
      b * ∑ i, w i * (x i - xbar) ^ 2 := by
    rw [mul_sum]; refine sum_congr rfl fun i _ => ?_; ring
  rw [hnum]
  field_simp

/-- The weighted least-squares line through `(x_i, y_i)` with weights `w_i`: its slope is
`wlsSlope w x y` and its intercept `y_bar - slope * x_bar`. No other line has a smaller weighted
sum of squared residuals. -/
theorem wlsSlope_minimizes {n : ℕ} (w x y : Fin n → ℝ) (hw : ∀ i, 0 ≤ w i) (hW : ∑ j, w j ≠ 0)
    (hD : ∑ i, w i * (x i - (∑ j, w j * x j) / ∑ j, w j) ^ 2 ≠ 0) (a b : ℝ) :
    ∑ i, w i * (y i - ((∑ j, w j * y j) / ∑ j, w j - wlsSlope w x y * ((∑ j, w j * x j) / ∑ j, w j))
        - wlsSlope w x y * x i) ^ 2 ≤
      ∑ i, w i * (y i - a - b * x i) ^ 2 := by
  set W := ∑ j, w j
  set xbar := (∑ j, w j * x j) / W
  set ybar := (∑ j, w j * y j) / W
  set D := ∑ i, w i * (x i - xbar) ^ 2
  set sl := wlsSlope w x y
  set r : Fin n → ℝ := fun i => y i - (ybar - sl * xbar) - sl * x i
  have hsx : ∑ i, w i * x i = W * xbar := by simp only [xbar]; field_simp
  have hsy : ∑ i, w i * y i = W * ybar := by simp only [ybar]; field_simp
  have hsl : sl = (∑ i, w i * (x i - xbar) * (y i - ybar)) / D := rfl
  have hN : ∑ i, w i * (x i - xbar) * (y i - ybar) = sl * D := by
    rw [hsl, div_mul_cancel₀ _ hD]
  have hr0 : ∑ i, w i * r i = 0 := by
    have : ∑ i, w i * r i = ∑ i, w i * y i - (ybar - sl * xbar) * W - sl * ∑ i, w i * x i := by
      simp only [r, W, mul_sub, sum_sub_distrib, ← sum_mul, mul_left_comm _ sl, ← mul_sum]
      ring
    rw [this, hsx, hsy]; ring
  have hr1 : ∑ i, w i * r i * x i = 0 := by
    have e1 : ∑ i, w i * r i * x i = ∑ i, w i * (x i - xbar) * (y i - ybar) - sl * D +
        xbar * ∑ i, w i * r i := by
      simp only [D, r, mul_sum, ← sum_sub_distrib, ← sum_add_distrib]
      refine sum_congr rfl fun i _ => ?_; ring
    rw [e1, hN, hr0]; ring
  set c := ybar - sl * xbar - a
  set d := sl - b
  have hexp : ∑ i, w i * (y i - a - b * x i) ^ 2 =
      ∑ i, w i * r i ^ 2 + ∑ i, w i * (c + d * x i) ^ 2 +
        2 * (c * ∑ i, w i * r i + d * ∑ i, w i * r i * x i) := by
    simp only [mul_sum, ← sum_add_distrib]
    refine sum_congr rfl fun i _ => ?_
    simp only [r, c, d]; ring
  rw [hexp, hr0, hr1]
  have : 0 ≤ ∑ i, w i * (c + d * x i) ^ 2 := sum_nonneg fun i _ => mul_nonneg (hw i) (sq_nonneg _)
  simp only [r] at this ⊢
  linarith

/-- The weighted least-squares fit of `log D` against `1/T` returns the activation energy
exactly on Arrhenius data, `E_a = -k_B * slope`, for every choice of positive weights and
at least two distinct temperatures. -/
theorem arrhenius_wls_recovers_activation {n : ℕ} (T w : Fin n → ℝ) (hT : ∀ i, 0 < T i)
    (hw : ∀ i, 0 < w i) (hdistinct : ∃ i j, T i ≠ T j) {D0 Ea kB : ℝ} (hD0 : 0 < D0)
    (hk : 0 < kB) :
    -kB * wlsSlope w (fun i => 1 / T i)
      (fun i => log (arrheniusDiffusivity D0 Ea kB (T i))) = Ea := by
  obtain ⟨i0, j0, hij⟩ := hdistinct
  have hy : (fun i => log (arrheniusDiffusivity D0 Ea kB (T i))) =
      fun i => log D0 + (-Ea / kB) * (1 / T i) := by
    funext i
    unfold arrheniusDiffusivity
    rw [log_mul hD0.ne' (exp_pos _).ne', log_exp]
    have := (hT i).ne'
    field_simp
  have hne : (univ : Finset (Fin n)).Nonempty := ⟨i0, mem_univ _⟩
  have hW : 0 < ∑ j, w j := sum_pos (fun j _ => hw j) hne
  set x : Fin n → ℝ := fun i => 1 / T i
  set xbar := (∑ j, w j * x j) / ∑ j, w j
  have hD : 0 < ∑ i, w i * (x i - xbar) ^ 2 := by
    by_contra hle
    have hle := not_lt.mp hle
    have hz : ∑ i, w i * (x i - xbar) ^ 2 = 0 :=
      le_antisymm hle (sum_nonneg fun i _ => mul_nonneg (hw i).le (sq_nonneg _))
    have hall : ∀ i, x i = xbar := by
      intro i
      have h0 := (sum_eq_zero_iff_of_nonneg (fun i _ => mul_nonneg (hw i).le (sq_nonneg _))).mp
        hz i (mem_univ i)
      have := (mul_eq_zero.mp h0).resolve_left (hw i).ne'
      have := pow_eq_zero_iff (n := 2) (by norm_num) |>.mp this
      linarith
    apply hij
    have h1 := hall i0
    have h2 := hall j0
    have heq : 1 / T i0 = 1 / T j0 := by simp only [x] at h1 h2; rw [h1, h2]
    rwa [one_div, one_div, inv_inj] at heq
  rw [hy, wlsSlope_affine w x _ _ hW.ne' hD.ne']
  field_simp

/-- For an Arrhenius diffusivity and a temperature-independent carrier density, the
catalog's ionic conductivity times temperature is Arrhenius with the diffusion barrier,
`d log(sigma T) / d(1/T) = -E_a / k_B`, while `d log(sigma) / d(1/T) = -(E_a - k_B T) / k_B`:
fitting `sigma` alone instead of `sigma T` underestimates the barrier by `k_B T`. -/
theorem ionicConductivity_arrhenius (Ea : ℝ) {nc z ec D0 kB beta : ℝ} (hnc : 0 < nc)
    (hz : z ≠ 0) (hec : ec ≠ 0) (hD0 : 0 < D0) (hk : 0 < kB) (hb : 0 < beta) :
    HasDerivAt (fun b => log (ionicConductivity nc (arrheniusDiffusivity D0 Ea kB (1 / b))
        (1 / b) z ec kB * (1 / b))) (-Ea / kB) beta ∧
      HasDerivAt (fun b => log (ionicConductivity nc (arrheniusDiffusivity D0 Ea kB (1 / b))
        (1 / b) z ec kB)) (-(Ea - kB * (1 / beta)) / kB) beta := by
  set C := D0 * ec ^ 2 * nc * z ^ 2 / kB
  have hC : 0 < C := by
    have : 0 < ec ^ 2 := by positivity
    have : 0 < z ^ 2 := by positivity
    positivity
  have hσ : ∀ b, 0 < b → ionicConductivity nc (arrheniusDiffusivity D0 Ea kB (1 / b)) (1 / b) z ec kB =
      C * b * exp (-Ea / kB * b) := by
    intro b hb'
    unfold ionicConductivity arrheniusDiffusivity
    have : -Ea / (1 / b * kB) = -Ea / kB * b := by field_simp
    rw [this]
    simp only [C]
    field_simp
  have hev : ∀ᶠ b in 𝓝 beta, 0 < b := eventually_gt_nhds hb
  constructor
  · have hf : (fun b => log (ionicConductivity nc (arrheniusDiffusivity D0 Ea kB (1 / b))
        (1 / b) z ec kB * (1 / b))) =ᶠ[𝓝 beta] fun b => log C + -Ea / kB * b := by
      filter_upwards [hev] with b hb'
      rw [hσ b hb']
      have : C * b * exp (-Ea / kB * b) * (1 / b) = C * exp (-Ea / kB * b) := by field_simp
      rw [this, log_mul hC.ne' (exp_pos _).ne', log_exp]
    have := ((hasDerivAt_id' beta).const_mul (-Ea / kB)).const_add (log C)
    exact (by simpa using this : HasDerivAt (fun b => log C + -Ea / kB * b) (-Ea / kB) beta)
      |>.congr_of_eventuallyEq hf
  · have hf : (fun b => log (ionicConductivity nc (arrheniusDiffusivity D0 Ea kB (1 / b))
        (1 / b) z ec kB)) =ᶠ[𝓝 beta] fun b => log C + log b + -Ea / kB * b := by
      filter_upwards [hev] with b hb'
      rw [hσ b hb', log_mul (by positivity) (exp_pos _).ne', log_mul hC.ne' hb'.ne', log_exp]
    have h := (((hasDerivAt_log hb.ne').const_add (log C)).add
      ((hasDerivAt_id' beta).const_mul (-Ea / kB)))
    have h' : HasDerivAt (fun b => log C + log b + -Ea / kB * b) (-(Ea - kB * (1 / beta)) / kB)
        beta := by
      convert h using 1
      field_simp
      ring
    exact h'.congr_of_eventuallyEq hf

private theorem sq_div_le_mul_log {lo hi x y : ℝ} (hlo : 0 < lo) (hx1 : lo ≤ x) (hx2 : x ≤ hi)
    (hy1 : lo ≤ y) (hy2 : y ≤ hi) :
    (x - y) ^ 2 / hi ≤ (x - y) * (log x - log y) ∧ (x - y) * (log x - log y) ≤ (x - y) ^ 2 / lo := by
  have hx : 0 < x := lt_of_lt_of_le hlo hx1
  have hy : 0 < y := lt_of_lt_of_le hlo hy1
  have hhi : 0 < hi := lt_of_lt_of_le hx hx2
  -- log(x/y) lies between 1 - y/x and x/y - 1
  have hup := log_le_sub_one_of_pos (div_pos hx hy)
  have hdn := one_sub_inv_le_log_of_pos (div_pos hx hy)
  rw [log_div hx.ne' hy.ne'] at hup hdn
  rw [inv_div] at hdn
  rcases le_total y x with hxy | hxy
  · have h0 : 0 ≤ x - y := sub_nonneg.mpr hxy
    constructor
    · calc (x - y) ^ 2 / hi ≤ (x - y) ^ 2 / x := div_le_div_of_nonneg_left (sq_nonneg _) hx hx2
        _ = (x - y) * (1 - y / x) := by field_simp
        _ ≤ (x - y) * (log x - log y) := mul_le_mul_of_nonneg_left hdn h0
    · calc (x - y) * (log x - log y) ≤ (x - y) * (x / y - 1) := mul_le_mul_of_nonneg_left hup h0
        _ = (x - y) ^ 2 / y := by field_simp
        _ ≤ (x - y) ^ 2 / lo := div_le_div_of_nonneg_left (sq_nonneg _) hlo hy1
  · have h0 : x - y ≤ 0 := sub_nonpos.mpr hxy
    constructor
    · calc (x - y) ^ 2 / hi ≤ (x - y) ^ 2 / y := div_le_div_of_nonneg_left (sq_nonneg _) hy hy2
        _ = (x - y) * (x / y - 1) := by field_simp
        _ ≤ (x - y) * (log x - log y) := mul_le_mul_of_nonpos_left hup h0
    · calc (x - y) * (log x - log y) ≤ (x - y) * (1 - y / x) := mul_le_mul_of_nonpos_left hdn h0
        _ = (x - y) ^ 2 / x := by field_simp
        _ ≤ (x - y) ^ 2 / lo := div_le_div_of_nonneg_left (sq_nonneg _) hlo hx1

/-- The weighted least-squares slope of `log x` against `x`, for positive weights and points in
`[lo, hi]` with `0 < lo`, lies between `1/hi` and `1/lo`. -/
theorem wlsSlope_log_mem {n : ℕ} (w x : Fin n → ℝ) (hw : ∀ i, 0 < w i) {lo hi : ℝ} (hlo : 0 < lo)
    (hx : ∀ i, lo ≤ x i ∧ x i ≤ hi) (hW : 0 < ∑ j, w j)
    (hD : 0 < ∑ i, w i * (x i - (∑ j, w j * x j) / ∑ j, w j) ^ 2) :
    1 / hi ≤ wlsSlope w x (fun i => log (x i)) ∧ wlsSlope w x (fun i => log (x i)) ≤ 1 / lo := by
  set W := ∑ j, w j
  set xbar := (∑ j, w j * x j) / W
  set D := ∑ i, w i * (x i - xbar) ^ 2
  have hbar1 : lo ≤ xbar := by
    rw [le_div_iff₀ hW]
    simp only [W, mul_sum]
    exact sum_le_sum fun i _ => by nlinarith [(hx i).1, hw i]
  have hbar2 : xbar ≤ hi := by
    rw [div_le_iff₀ hW]
    simp only [W, mul_sum]
    exact sum_le_sum fun i _ => by nlinarith [(hx i).2, hw i]
  have hsum0 : ∑ i, w i * (x i - xbar) = 0 := by
    simp only [mul_sub, sum_sub_distrib, ← sum_mul, xbar]; field_simp; ring
  have hN : ∑ i, w i * (x i - xbar) * (log (x i) - (∑ j, w j * log (x j)) / W) =
      ∑ i, w i * ((x i - xbar) * (log (x i) - log xbar)) := by
    have : ∀ i, w i * (x i - xbar) * (log (x i) - (∑ j, w j * log (x j)) / W) =
        w i * ((x i - xbar) * (log (x i) - log xbar)) +
          (log xbar - (∑ j, w j * log (x j)) / W) * (w i * (x i - xbar)) := fun i => by ring
    rw [sum_congr rfl fun i _ => this i, sum_add_distrib, ← mul_sum, hsum0, mul_zero, add_zero]
  have hhi : 0 < hi := lt_of_lt_of_le hlo (le_trans hbar1 hbar2)
  have hb := fun i => sq_div_le_mul_log hlo (hx i).1 (hx i).2 hbar1 hbar2
  have lower : D / hi ≤ ∑ i, w i * ((x i - xbar) * (log (x i) - log xbar)) := by
    simp only [D, sum_div]
    exact sum_le_sum fun i _ => by
      have := mul_le_mul_of_nonneg_left (hb i).1 (hw i).le; rw [mul_div_assoc]; exact this
  have upper : ∑ i, w i * ((x i - xbar) * (log (x i) - log xbar)) ≤ D / lo := by
    simp only [D, sum_div]
    exact sum_le_sum fun i _ => by
      have := mul_le_mul_of_nonneg_left (hb i).2 (hw i).le; rw [mul_div_assoc]; exact this
  unfold wlsSlope
  rw [hN]
  constructor
  · rw [le_div_iff₀ hD]; calc 1 / hi * D = D / hi := by ring
      _ ≤ _ := lower
  · rw [div_le_iff₀ hD]; calc _ ≤ D / lo := upper
      _ = 1 / lo * D := by ring

/-- Fitting the catalog's Nernst-Einstein ionic conductivity itself, rather than `sigma T`, to the
Arrhenius form by weighted least squares of `log sigma` against `1/T` returns the apparent
activation energy `E_a - k_B T_eff` for some `T_eff` in the range `[T_lo, T_hi]` of the data, for
every choice of positive weights, when the diffusivity is Arrhenius with barrier `E_a` and the
carrier density does not depend on temperature. -/
theorem ionic_wls_apparent_activation {n : ℕ} (T w : Fin n → ℝ) (hw : ∀ i, 0 < w i)
    {Tlo Thi : ℝ} (hlo : 0 < Tlo) (hT : ∀ i, Tlo ≤ T i ∧ T i ≤ Thi) (hdistinct : ∃ i j, T i ≠ T j)
    (Ea : ℝ) {nc z ec D0 kB : ℝ} (hnc : 0 < nc) (hz : z ≠ 0) (hec : ec ≠ 0) (hD0 : 0 < D0)
    (hk : 0 < kB) :
    ∃ Teff, Tlo ≤ Teff ∧ Teff ≤ Thi ∧
      -kB * wlsSlope w (fun i => 1 / T i)
        (fun i => log (ionicConductivity nc (arrheniusDiffusivity D0 Ea kB (T i)) (T i) z ec kB)) =
        Ea - kB * Teff := by
  obtain ⟨i0, j0, hij⟩ := hdistinct
  have hTpos : ∀ i, 0 < T i := fun i => lt_of_lt_of_le hlo (hT i).1
  set x : Fin n → ℝ := fun i => 1 / T i
  set C := D0 * ec ^ 2 * nc * z ^ 2 / kB
  have hC : 0 < C := by
    have : 0 < ec ^ 2 := by positivity
    have : 0 < z ^ 2 := by positivity
    positivity
  have hy : (fun i => log (ionicConductivity nc (arrheniusDiffusivity D0 Ea kB (T i)) (T i) z ec kB)) =
      fun i => log C + (-Ea / kB) * x i + log (x i) := by
    funext i
    have hTi := hTpos i
    have hσ : ionicConductivity nc (arrheniusDiffusivity D0 Ea kB (T i)) (T i) z ec kB =
        C * x i * exp (-Ea / kB * x i) := by
      unfold ionicConductivity arrheniusDiffusivity
      have : -Ea / (T i * kB) = -Ea / kB * (1 / T i) := by field_simp
      simp only [x, C]; rw [this]; field_simp
    have hxi : 0 < x i := one_div_pos.mpr hTi
    rw [hσ, log_mul (mul_pos hC hxi).ne' (exp_pos _).ne', log_mul hC.ne' hxi.ne', log_exp]
    ring
  have hne : (univ : Finset (Fin n)).Nonempty := ⟨i0, mem_univ _⟩
  have hW : 0 < ∑ j, w j := sum_pos (fun j _ => hw j) hne
  set xbar := (∑ j, w j * x j) / ∑ j, w j
  have hD : 0 < ∑ i, w i * (x i - xbar) ^ 2 := by
    by_contra hle
    have hle := not_lt.mp hle
    have hz0 : ∑ i, w i * (x i - xbar) ^ 2 = 0 :=
      le_antisymm hle (sum_nonneg fun i _ => mul_nonneg (hw i).le (sq_nonneg _))
    have hall : ∀ i, x i = xbar := by
      intro i
      have h0 := (sum_eq_zero_iff_of_nonneg (fun i _ => mul_nonneg (hw i).le (sq_nonneg _))).mp
        hz0 i (mem_univ i)
      have := (mul_eq_zero.mp h0).resolve_left (hw i).ne'
      have := pow_eq_zero_iff (n := 2) (by norm_num) |>.mp this
      linarith
    apply hij
    have heq : 1 / T i0 = 1 / T j0 := by
      have h1 := hall i0; have h2 := hall j0; simp only [x] at h1 h2; rw [h1, h2]
    rwa [one_div, one_div, inv_inj] at heq
  have hsplit : wlsSlope w x (fun i => log C + (-Ea / kB) * x i + log (x i)) =
      -Ea / kB + wlsSlope w x (fun i => log (x i)) := by
    unfold wlsSlope
    have hm : (∑ j, w j * (log C + -Ea / kB * x j + log (x j))) / ∑ j, w j =
        log C + -Ea / kB * xbar + (∑ j, w j * log (x j)) / ∑ j, w j := by
      simp only [xbar, mul_add, sum_add_distrib, ← sum_mul, mul_left_comm _ (-Ea / kB), ← mul_sum]
      field_simp
    rw [hm]
    have hnum : ∑ i, w i * (x i - xbar) * (log C + -Ea / kB * x i + log (x i) -
        (log C + -Ea / kB * xbar + (∑ j, w j * log (x j)) / ∑ j, w j)) =
        -Ea / kB * ∑ i, w i * (x i - xbar) ^ 2 +
          ∑ i, w i * (x i - xbar) * (log (x i) - (∑ j, w j * log (x j)) / ∑ j, w j) := by
      rw [mul_sum, ← sum_add_distrib]; refine sum_congr rfl fun i _ => ?_; ring
    rw [hnum, add_div, mul_div_assoc, div_self hD.ne', mul_one]
  have hxb : ∀ i, 1 / Thi ≤ x i ∧ x i ≤ 1 / Tlo := fun i =>
    ⟨one_div_le_one_div_of_le (hTpos i) (hT i).2, one_div_le_one_div_of_le hlo (hT i).1⟩
  have hThi : 0 < Thi := lt_of_lt_of_le (hTpos i0) (hT i0).2
  have hb := wlsSlope_log_mem w x hw (one_div_pos.mpr hThi) hxb hW hD
  refine ⟨wlsSlope w x (fun i => log (x i)), ?_, ?_, ?_⟩
  · simpa using hb.1
  · simpa using hb.2
  · rw [hy, hsplit]; field_simp; ring

end OMAI.PhyslibBridge.MaterialsTransport
