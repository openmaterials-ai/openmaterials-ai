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

end OMAI.PhyslibBridge.MaterialsTransport
