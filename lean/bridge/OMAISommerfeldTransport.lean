module

public import Mathlib.Analysis.SpecialFunctions.Gamma.Basic
public import Mathlib.Analysis.SpecificLimits.Normed
public import Mathlib.Analysis.PSeries
public import Mathlib.MeasureTheory.Integral.DominatedConvergence
public import Mathlib.MeasureTheory.Integral.IntegralEqImproper
public import Mathlib.MeasureTheory.Measure.Lebesgue.Integral
public import Mathlib.MeasureTheory.Group.Integral
public import Mathlib.MeasureTheory.Measure.Haar.NormedSpace
public import Mathlib.NumberTheory.ZetaValues
public import Mathlib.Tactic

/-!
# The Sommerfeld moments of the Fermi window

For an energy-independent transport distribution the Onsager kinetic integrals reduce to the
moments of the Fermi window `-df/dx = e^x / (1 + e^x)^2`, with `x = (E - mu) / (k_B T)`. Its
zeroth moment is 1, its first vanishes by symmetry, and its second is `pi^2 / 3`, obtained here
from the alternating series `sum (-1)^(n+1) / n^2 = pi^2 / 12`. These moments give the exact
Wiedemann-Franz law for such a distribution: no thermopower and the Sommerfeld Lorenz number
`pi^2 k_B^2 / (3 e^2)`.
-/

@[expose] public section

noncomputable section

open Real MeasureTheory Set Filter Topology

namespace OMAI.PhyslibBridge.Sommerfeld

/-- The Fermi window `-df/dx = e^x / (1 + e^x)^2` of the Fermi function `1 / (1 + e^x)`, in
units of `k_B T`. -/
def fermiWindow (x : ℝ) : ℝ := exp x / (1 + exp x) ^ 2

private theorem alternating_inv_sq :
    HasSum (fun n : ℕ => (-1 : ℝ) ^ (n + 1) * 2 / (n : ℝ) ^ 2) (π ^ 2 / 6) := by
  have h := hasSum_one_div_nat_pow_mul_cos (k := 1) one_ne_zero
    (x := 1 / 2) ⟨by norm_num, by norm_num⟩
  have hB : (Polynomial.map (algebraMap ℚ ℝ) (Polynomial.bernoulli 2)).eval (1 / 2 : ℝ) =
      -1 / 12 := by
    rw [Polynomial.eval_map]
    simp only [Polynomial.bernoulli, Finset.sum_range_succ, Finset.sum_range_zero,
      Polynomial.eval₂_add, Polynomial.eval₂_monomial, zero_add]
    rw [_root_.bernoulli_one, bernoulli_eq_bernoulli'_of_ne_one zero_ne_one, bernoulli'_zero,
      bernoulli_eq_bernoulli'_of_ne_one (by decide : 2 ≠ 1), bernoulli'_two]
    norm_num
  rw [hB] at h
  have hcos : ∀ n : ℕ, cos (2 * π * n * (1 / 2)) = (-1) ^ n := fun n => by
    rw [show 2 * π * n * (1 / 2) = n * π by ring, cos_nat_mul_pi]
  simp only [hcos] at h
  convert h.mul_left (-2) using 1
  · funext n
    rw [pow_succ]
    ring
  · norm_num
    ring

theorem fermiWindow_neg (x : ℝ) : fermiWindow (-x) = fermiWindow x := by
  unfold fermiWindow
  rw [exp_neg]
  have h := exp_pos x
  field_simp
  ring

private theorem fermiWindow_eq_exp_neg (x : ℝ) :
    fermiWindow x = exp (-x) / (1 + exp (-x)) ^ 2 := by
  rw [← fermiWindow_neg, fermiWindow]

private theorem fermiWindow_nonneg (x : ℝ) : 0 ≤ fermiWindow x := by
  unfold fermiWindow; positivity

/-- The series `x^2 e^x / (1 + e^x)^2 = sum (-1)^(n+1) n x^2 e^(-n x)` for `x > 0`. -/
private def seriesTerm (n : ℕ) (x : ℝ) : ℝ := (-1) ^ (n + 1) * n * (x ^ 2 * exp (-(n * x)))

private theorem hasSum_seriesTerm {x : ℝ} (hx : 0 < x) :
    HasSum (fun n => seriesTerm n x) (x ^ 2 * fermiWindow x) := by
  have hr : ‖-exp (-x)‖ < 1 := by
    rw [norm_neg, Real.norm_eq_abs, abs_of_pos (exp_pos _), Real.exp_lt_one_iff]; linarith
  have h := (hasSum_coe_mul_geometric_of_norm_lt_one hr).mul_left (-x ^ 2)
  rw [fermiWindow_eq_exp_neg]
  convert h using 1
  · funext n
    unfold seriesTerm
    have hp : (-exp (-x)) ^ n = (-1) ^ n * exp (-(n * x)) := by
      rw [neg_eq_neg_one_mul, mul_pow, ← Real.exp_nat_mul]
      congr 2
      ring
    rw [hp, pow_succ]
    ring
  · ring

private theorem integral_sq_mul_exp_neg {n : ℕ} (hn : 0 < n) :
    ∫ x in Ioi (0 : ℝ), x ^ 2 * exp (-(n * x)) = 2 / (n : ℝ) ^ 3 := by
  have h := integral_rpow_mul_exp_neg_mul_Ioi (a := 3) (r := n) (by norm_num)
    (by exact_mod_cast hn)
  rw [show (3 : ℝ) - 1 = 2 by norm_num, show (3 : ℝ) = (2 : ℕ) + 1 by norm_num,
    Real.Gamma_nat_eq_factorial] at h
  have hcongr : ∫ x in Ioi (0 : ℝ), x ^ 2 * exp (-(n * x)) =
      ∫ x in Ioi (0 : ℝ), x ^ (2 : ℝ) * exp (-(n * x)) := by
    refine setIntegral_congr_fun measurableSet_Ioi fun x hx => ?_
    rw [show (2 : ℝ) = (2 : ℕ) by norm_num, rpow_natCast]
  rw [hcongr, h, show ((2 : ℕ) : ℝ) + 1 = (3 : ℕ) by norm_num, rpow_natCast]
  simp [Nat.factorial]
  ring

private theorem integral_seriesTerm (n : ℕ) :
    ∫ x in Ioi (0 : ℝ), seriesTerm n x = (-1 : ℝ) ^ (n + 1) * 2 / (n : ℝ) ^ 2 := by
  rcases Nat.eq_zero_or_pos n with rfl | hn
  · simp [seriesTerm]
  unfold seriesTerm
  rw [integral_const_mul, integral_sq_mul_exp_neg hn]
  have : (n : ℝ) ≠ 0 := by exact_mod_cast hn.ne'
  field_simp

private theorem integral_norm_seriesTerm (n : ℕ) :
    ∫ x in Ioi (0 : ℝ), ‖seriesTerm n x‖ = 2 / (n : ℝ) ^ 2 := by
  rcases Nat.eq_zero_or_pos n with rfl | hn
  · simp [seriesTerm]
  have hpt : ∀ x, ‖seriesTerm n x‖ = n * (x ^ 2 * exp (-(n * x))) := fun x => by
    unfold seriesTerm
    rw [norm_mul, norm_mul, norm_pow, norm_neg, norm_one, one_pow, one_mul, Real.norm_natCast,
      Real.norm_of_nonneg (by positivity)]
  simp_rw [hpt]
  rw [integral_const_mul, integral_sq_mul_exp_neg hn]
  have : (n : ℝ) ≠ 0 := by exact_mod_cast hn.ne'
  field_simp

private theorem integrable_seriesTerm (n : ℕ) : IntegrableOn (seriesTerm n) (Ioi 0) := by
  rcases Nat.eq_zero_or_pos n with rfl | hn
  · have h0 : seriesTerm 0 = 0 := by funext x; simp [seriesTerm]
    rw [h0]
    exact integrableOn_zero
  apply Integrable.of_integral_ne_zero
  rw [integral_seriesTerm]
  have : (n : ℝ) ≠ 0 := by exact_mod_cast hn.ne'
  exact div_ne_zero (mul_ne_zero (pow_ne_zero _ (by norm_num)) two_ne_zero) (pow_ne_zero _ this)

private theorem integral_sq_mul_fermiWindow_Ioi :
    ∫ x in Ioi (0 : ℝ), x ^ 2 * fermiWindow x = π ^ 2 / 6 := by
  have hsum : Summable fun n : ℕ => ∫ x in Ioi (0 : ℝ), ‖seriesTerm n x‖ := by
    simp_rw [integral_norm_seriesTerm]
    exact ((Real.summable_one_div_nat_pow.mpr one_lt_two).mul_left 2).congr fun n => by ring
  have hswap := integral_tsum_of_summable_integral_norm integrable_seriesTerm hsum
  have hcongr : ∫ x in Ioi (0 : ℝ), x ^ 2 * fermiWindow x =
      ∫ x in Ioi (0 : ℝ), ∑' n, seriesTerm n x :=
    setIntegral_congr_fun measurableSet_Ioi fun x hx => (hasSum_seriesTerm hx).tsum_eq.symm
  rw [hcongr, ← hswap]
  simp_rw [integral_seriesTerm]
  exact alternating_inv_sq.tsum_eq

/-- The Fermi window is normalized, `int e^x / (1 + e^x)^2 dx = 1`. -/
theorem integral_fermiWindow : ∫ x, fermiWindow x = 1 := by
  have heven : ∀ x, fermiWindow x = fermiWindow |x| := fun x => by
    rcases le_or_gt 0 x with h | h
    · rw [abs_of_nonneg h]
    · rw [abs_of_neg h, fermiWindow_neg]
  have hderiv : ∀ x ∈ Ici (0 : ℝ), HasDerivAt (fun x => -1 / (1 + exp x)) (fermiWindow x) x := by
    intro x _
    have h1 : HasDerivAt (fun x => 1 + exp x) (exp x) x := (hasDerivAt_exp x).const_add 1
    have h2 := (h1.inv (by positivity)).neg
    convert h2 using 1
    · funext y; simp [div_eq_mul_inv]
    · unfold fermiWindow; field_simp
  have hlim : Tendsto (fun x => -1 / (1 + exp x)) atTop (𝓝 0) := by
    have : Tendsto (fun x => 1 + exp x) atTop atTop :=
      tendsto_atTop_add_const_left _ 1 tendsto_exp_atTop
    have h := (this.inv_tendsto_atTop).neg
    simp only [neg_zero] at h
    convert h using 2 with x
    simp [neg_div]
  have hint := integrableOn_Ioi_deriv_of_nonneg' hderiv (fun x _ => fermiWindow_nonneg x) hlim
  have hIoi := integral_Ioi_of_hasDerivAt_of_tendsto' hderiv hint hlim
  calc ∫ x, fermiWindow x = ∫ x, fermiWindow |x| := by simp_rw [← heven]
    _ = 2 * ∫ x in Ioi (0 : ℝ), fermiWindow x := integral_comp_abs
    _ = 1 := by rw [hIoi]; norm_num

/-- The first moment of the Fermi window vanishes by symmetry. -/
theorem integral_mul_fermiWindow : ∫ x, x * fermiWindow x = 0 := by
  have h := integral_neg_eq_self (fun x : ℝ => x * fermiWindow x) volume
  simp only [fermiWindow_neg, neg_mul, integral_neg] at h
  linarith

/-- The second moment of the Fermi window is `pi^2 / 3`. -/
theorem integral_sq_mul_fermiWindow : ∫ x, x ^ 2 * fermiWindow x = π ^ 2 / 3 := by
  have heven : ∀ x, x ^ 2 * fermiWindow x = |x| ^ 2 * fermiWindow |x| := fun x => by
    rcases le_or_gt 0 x with h | h
    · rw [abs_of_nonneg h]
    · rw [abs_of_neg h, fermiWindow_neg, neg_sq]
  calc ∫ x, x ^ 2 * fermiWindow x = ∫ x, |x| ^ 2 * fermiWindow |x| := by simp_rw [← heven]
    _ = 2 * ∫ x in Ioi (0 : ℝ), x ^ 2 * fermiWindow x :=
        integral_comp_abs (f := fun x => x ^ 2 * fermiWindow x)
    _ = π ^ 2 / 3 := by rw [integral_sq_mul_fermiWindow_Ioi]; ring

/-- The Onsager kinetic integral `K_k = int Sigma0 (E - mu)^k (-df/dE) dE` of an
energy-independent transport distribution `Sigma0`, with `-df/dE = fermiWindow ((E - mu)/kT)/kT`
and `kT = k_B T`. -/
def kineticIntegral (Sigma0 mu kT : ℝ) (k : ℕ) : ℝ :=
  ∫ E, Sigma0 * (E - mu) ^ k * (fermiWindow ((E - mu) / kT) / kT)

theorem kineticIntegral_eq (Sigma0 mu : ℝ) {kT : ℝ} (hkT : 0 < kT) (k : ℕ) :
    kineticIntegral Sigma0 mu kT k = Sigma0 * kT ^ k * ∫ x, x ^ k * fermiWindow x := by
  unfold kineticIntegral
  have hshift := integral_sub_right_eq_self (μ := (volume : Measure ℝ))
    (fun y : ℝ => Sigma0 * y ^ k * (fermiWindow (y / kT) / kT)) mu
  rw [hshift]
  have hpt : ∀ y : ℝ, Sigma0 * y ^ k * (fermiWindow (y / kT) / kT) =
      (Sigma0 * kT ^ k / kT) * ((y / kT) ^ k * fermiWindow (y / kT)) := fun y => by
    rw [div_pow]
    field_simp
  simp_rw [hpt]
  rw [integral_const_mul, Measure.integral_comp_div (fun x => x ^ k * fermiWindow x), abs_of_pos hkT,
    smul_eq_mul]
  field_simp

/-- The Sommerfeld moments of an energy-independent transport distribution:
`K_0 = Sigma0`, `K_1 = 0` and `K_2 = Sigma0 (k_B T)^2 pi^2 / 3`. -/
theorem sommerfeld_moments (Sigma0 mu : ℝ) {kT : ℝ} (hkT : 0 < kT) :
    kineticIntegral Sigma0 mu kT 0 = Sigma0 ∧ kineticIntegral Sigma0 mu kT 1 = 0 ∧
      kineticIntegral Sigma0 mu kT 2 = Sigma0 * kT ^ 2 * (π ^ 2 / 3) := by
  refine ⟨?_, ?_, ?_⟩
  · rw [kineticIntegral_eq _ _ hkT]; simp [integral_fermiWindow]
  · rw [kineticIntegral_eq _ _ hkT]; simp [integral_mul_fermiWindow]
  · rw [kineticIntegral_eq _ _ hkT, integral_sq_mul_fermiWindow]

/-- The Wiedemann-Franz law is exact for an energy-independent transport distribution: with
`sigma = e^2 K_0`, `S = -(K_1 / K_0) / (e T)` and `kappa_e = (K_2 - K_1^2 / K_0) / T`, the
thermopower vanishes and `kappa_e = (pi^2 / 3) (k_B / e)^2 sigma T`, the Sommerfeld Lorenz
number. No hypothesis on `Sigma0` is needed: `K_1 = 0`, so the Peltier correction `K_1^2 / K_0`
vanishes for every `Sigma0`, and at `Sigma0 = 0` both sides are zero. -/
theorem wiedemannFranz_constantTransport {Sigma0 e kB T : ℝ} (mu : ℝ) (he : e ≠ 0)
    (hkB : 0 < kB) (hT : 0 < T) :
    -(kineticIntegral Sigma0 mu (kB * T) 1 / kineticIntegral Sigma0 mu (kB * T) 0) / (e * T) = 0 ∧
      (kineticIntegral Sigma0 mu (kB * T) 2 -
          kineticIntegral Sigma0 mu (kB * T) 1 ^ 2 / kineticIntegral Sigma0 mu (kB * T) 0) / T =
        π ^ 2 / 3 * (kB / e) ^ 2 * (e ^ 2 * kineticIntegral Sigma0 mu (kB * T) 0) * T := by
  obtain ⟨h0, h1, h2⟩ := sommerfeld_moments Sigma0 mu (mul_pos hkB hT)
  rw [h0, h1, h2]
  refine ⟨by simp, ?_⟩
  rw [zero_pow two_ne_zero, zero_div, sub_zero]
  field_simp

end OMAI.PhyslibBridge.Sommerfeld
