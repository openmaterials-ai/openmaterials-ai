module

public import Mathlib.Analysis.SpecialFunctions.ImproperIntegrals
public import Mathlib.MeasureTheory.Integral.PeakFunction
public import Mathlib.MeasureTheory.Integral.ExpDecay
public import Mathlib.Analysis.SpecialFunctions.Trigonometric.Deriv
public import Mathlib.Tactic

/-!
# Vibrational density of states from the velocity autocorrelation

The catalog's `fourier_to_dos` reads the vibrational density of states off the velocity
autocorrelation by the cosine transform `g(omega) = (1/pi) int_0^infinity cos(omega tau) Cv(tau)
d tau`. Physlib has no model of a molecular dynamics trajectory, so these are local theorems over
Mathlib.

For the autocorrelation of lifetime-broadened modes,
`Cv(tau) = sum_m A_m exp(-Gamma_m tau) cos(omega_m tau)` with every `Gamma_m > 0`, the catalog
transform is a sum of Lorentzians of half-width `Gamma_m` centred at `+omega_m` and `-omega_m`,
each with weight `A_m / 2`. Its integral over all frequencies is `Cv(0)` for every set of
linewidths, and as the linewidths shrink to zero it converges, against every integrable test
function continuous at the mode frequencies, to the delta sum `sum_m (A_m / 2)
(delta(omega - omega_m) + delta(omega + omega_m))`: the harmonic delta-sum density of states with
mode weights `A_m`. No statement is made about a finite trajectory, a window function, or
whether the weights `A_m` are equal.
-/

@[expose] public section

noncomputable section

open Real MeasureTheory Filter Set Finset
open scoped Topology

namespace OMAI.PhyslibBridge.VACFSpectrum

/-- The reviewed catalog expression of `fourier_to_dos`,
`g(omega) = int_0^infinity cos(omega tau) Cv(tau) d tau / pi`. This definition alone is not a
physical proof. -/
def catalogFourierDOS (Cv : ℝ → ℝ) (omega : ℝ) : ℝ :=
  (∫ tau in Ioi 0, cos (omega * tau) * Cv tau) / π

/-- The velocity autocorrelation of lifetime-broadened modes with amplitudes `A`, half-widths
`Gamma` and frequencies `w`. -/
def dampedVACF {M : ℕ} (A Gamma w : Fin M → ℝ) (tau : ℝ) : ℝ :=
  ∑ m, A m * exp (-Gamma m * tau) * cos (w m * tau)

/-- The normalized Lorentzian of half-width `Gamma` at detuning `x`. -/
def lorentzian (Gamma x : ℝ) : ℝ := Gamma / (π * (Gamma ^ 2 + x ^ 2))

theorem integrableOn_exp_neg_mul_cos {G : ℝ} (hG : 0 < G) (b : ℝ) :
    IntegrableOn (fun t => exp (-G * t) * cos (b * t)) (Ioi 0) := by
  refine (exp_neg_integrableOn_Ioi 0 hG).mono' ?_ ?_
  · exact (by fun_prop : Continuous fun t => exp (-G * t) * cos (b * t)).aestronglyMeasurable
  · refine (ae_restrict_iff' measurableSet_Ioi).2 (Eventually.of_forall fun t _ => ?_)
    rw [norm_mul, Real.norm_of_nonneg (exp_pos _).le]
    exact mul_le_of_le_one_right (exp_pos _).le (abs_cos_le_one _)

theorem integral_exp_neg_mul_cos {G : ℝ} (hG : 0 < G) (a : ℝ) :
    ∫ tau in Ioi 0, exp (-G * tau) * cos (a * tau) = G / (G ^ 2 + a ^ 2) := by
  have hden : 0 < G ^ 2 + a ^ 2 := by positivity
  set F : ℝ → ℝ := fun t => exp (-G * t) * (a * sin (a * t) - G * cos (a * t)) / (G ^ 2 + a ^ 2)
  have hFc : Continuous F := by fun_prop
  have hderiv : ∀ t ∈ Ioi (0 : ℝ), HasDerivAt F (exp (-G * t) * cos (a * t)) t := by
    intro t _
    have h1 : HasDerivAt (fun t => exp (-G * t)) (exp (-G * t) * (-G)) t := by
      simpa using ((hasDerivAt_id t).const_mul (-G)).exp
    have hs : HasDerivAt (fun t => sin (a * t)) (cos (a * t) * a) t := by
      simpa using ((hasDerivAt_id t).const_mul a).sin
    have hc : HasDerivAt (fun t => cos (a * t)) (-sin (a * t) * a) t := by
      simpa using ((hasDerivAt_id t).const_mul a).cos
    have := ((h1.mul ((hs.const_mul a).sub (hc.const_mul G))).div_const (G ^ 2 + a ^ 2))
    convert this using 1
    rw [eq_div_iff hden.ne']
    simp only [Pi.sub_apply]
    ring
  have hlim : Tendsto F atTop (𝓝 0) := by
    have he : Tendsto (fun t => exp (-G * t)) atTop (𝓝 0) := by
      refine (tendsto_exp_neg_atTop_nhds_zero.comp (tendsto_id.const_mul_atTop hG)).congr fun t => ?_
      simp [neg_mul]
    have hb : IsBoundedUnder (· ≤ ·) atTop
        (norm ∘ fun t => (a * sin (a * t) - G * cos (a * t)) / (G ^ 2 + a ^ 2)) := by
      refine isBoundedUnder_of ⟨(|a| + |G|) / (G ^ 2 + a ^ 2), fun t => ?_⟩
      simp only [Function.comp, Real.norm_eq_abs, abs_div, abs_of_pos hden]
      refine div_le_div_of_nonneg_right ?_ hden.le
      calc |a * sin (a * t) - G * cos (a * t)| ≤ |a * sin (a * t)| + |G * cos (a * t)| :=
            abs_sub _ _
        _ ≤ |a| + |G| := by
          rw [abs_mul, abs_mul]
          exact add_le_add (mul_le_of_le_one_right (abs_nonneg _) (abs_sin_le_one _))
            (mul_le_of_le_one_right (abs_nonneg _) (abs_cos_le_one _))
    refine (he.zero_mul_isBoundedUnder_le hb).congr fun t => ?_
    simp only [F]
    ring
  rw [integral_Ioi_of_hasDerivAt_of_tendsto hFc.continuousWithinAt hderiv
    (integrableOn_exp_neg_mul_cos hG a) hlim]
  simp only [F, mul_zero, exp_zero, sin_zero, cos_zero]
  field_simp
  ring

theorem cos_mul_dampedVACF {M : ℕ} (A Gamma w : Fin M → ℝ) (omega tau : ℝ) :
    cos (omega * tau) * dampedVACF A Gamma w tau =
      ∑ m, A m / 2 * (exp (-Gamma m * tau) * cos ((omega - w m) * tau) +
        exp (-Gamma m * tau) * cos ((omega + w m) * tau)) := by
  unfold dampedVACF
  rw [mul_sum]
  refine sum_congr rfl fun m _ => ?_
  rw [sub_mul, add_mul, cos_sub, cos_add]
  ring

/-- For lifetime-broadened modes the catalog transform is a sum of Lorentzians of half-width
`Gamma_m` at `+omega_m` and `-omega_m`, each with weight `A_m / 2`. -/
theorem catalogFourierDOS_damped {M : ℕ} (A Gamma w : Fin M → ℝ) (hG : ∀ m, 0 < Gamma m)
    (omega : ℝ) :
    catalogFourierDOS (dampedVACF A Gamma w) omega =
      ∑ m, A m / 2 * (lorentzian (Gamma m) (omega - w m) + lorentzian (Gamma m) (omega + w m)) := by
  unfold catalogFourierDOS
  simp only [cos_mul_dampedVACF]
  rw [integral_finsetSum]
  swap
  · intro m _
    exact ((integrableOn_exp_neg_mul_cos (hG m) _).add (integrableOn_exp_neg_mul_cos (hG m) _)).const_mul _
  rw [sum_div]
  refine sum_congr rfl fun m _ => ?_
  rw [integral_const_mul, integral_add (integrableOn_exp_neg_mul_cos (hG m) _)
    (integrableOn_exp_neg_mul_cos (hG m) _),
    integral_exp_neg_mul_cos (hG m), integral_exp_neg_mul_cos (hG m)]
  unfold lorentzian
  have h1 : 0 < Gamma m ^ 2 + (omega - w m) ^ 2 := by have := hG m; positivity
  have h2 : 0 < Gamma m ^ 2 + (omega + w m) ^ 2 := by have := hG m; positivity
  field_simp

theorem integral_lorentzian {G : ℝ} (hG : 0 < G) (c : ℝ) :
    ∫ x, lorentzian G (x - c) = 1 := by
  rw [integral_sub_right_eq_self (fun x => lorentzian G x) c]
  have h : (fun x => lorentzian G x) = fun x => (π * G)⁻¹ * (1 + (G⁻¹ * x) ^ 2)⁻¹ := by
    funext x
    unfold lorentzian
    field_simp
  rw [h, integral_const_mul, integral_univ_inv_one_add_mul_sq, abs_inv, abs_of_pos hG]
  field_simp

theorem integrable_lorentzian {G : ℝ} (hG : 0 < G) (c : ℝ) :
    Integrable fun x => lorentzian G (x - c) := by
  have h : (fun x => lorentzian G x) = fun x => (π * G)⁻¹ * (1 + (G⁻¹ * x) ^ 2)⁻¹ := by
    funext x
    unfold lorentzian
    field_simp
  have : Integrable fun x => lorentzian G x := by
    rw [h]; exact (integrable_inv_one_add_mul_sq (inv_ne_zero hG.ne')).const_mul _
  exact this.comp_sub_right c

/-- The catalog density of states of lifetime-broadened modes integrates to the zero-lag
autocorrelation `Cv(0) = sum_m A_m` for every set of positive linewidths. -/
theorem integral_catalogFourierDOS_damped {M : ℕ} (A Gamma w : Fin M → ℝ)
    (hG : ∀ m, 0 < Gamma m) :
    ∫ omega, catalogFourierDOS (dampedVACF A Gamma w) omega = dampedVACF A Gamma w 0 := by
  simp only [catalogFourierDOS_damped A Gamma w hG]
  rw [integral_finsetSum]
  swap
  · intro m _
    exact ((integrable_lorentzian (hG m) _).add (by
      simpa [sub_neg_eq_add] using integrable_lorentzian (hG m) (-w m))).const_mul _
  unfold dampedVACF
  refine sum_congr rfl fun m _ => ?_
  rw [integral_const_mul, integral_add (integrable_lorentzian (hG m) _)
    (by simpa [sub_neg_eq_add] using integrable_lorentzian (hG m) (-w m)),
    integral_lorentzian (hG m)]
  have := integral_lorentzian (hG m) (-w m)
  simp only [sub_neg_eq_add] at this
  rw [this]
  simp only [mul_zero, exp_zero, cos_zero, mul_one]
  ring

/-- The unit Lorentzian profile `1 / (pi (1 + x^2))`. -/
def unitLorentzian (x : ℝ) : ℝ := 1 / (π * (1 + x ^ 2))

theorem lorentzian_eq_scaled {G : ℝ} (hG : 0 < G) (x0 x : ℝ) :
    lorentzian G (x - x0) = G⁻¹ ^ Module.finrank ℝ ℝ * unitLorentzian (G⁻¹ • (x0 - x)) := by
  simp only [Module.finrank_self, pow_one, smul_eq_mul, lorentzian, unitLorentzian]
  field_simp
  ring

theorem unitLorentzian_peak :
    (∀ x, 0 ≤ unitLorentzian x) ∧ (∫ x, unitLorentzian x = 1) ∧
      Tendsto (fun x : ℝ => ‖x‖ ^ Module.finrank ℝ ℝ * unitLorentzian x) (Bornology.cobounded ℝ)
        (𝓝 0) := by
  refine ⟨fun x => by unfold unitLorentzian; positivity, ?_, ?_⟩
  · have h : unitLorentzian = fun x => π⁻¹ * (1 + x ^ 2)⁻¹ := by
      funext x; unfold unitLorentzian; field_simp
    rw [h, integral_const_mul, integral_univ_inv_one_add_sq]
    field_simp
  · simp only [Module.finrank_self, pow_one]
    have hr : Tendsto (fun r : ℝ => r / (π * (1 + r ^ 2))) atTop (𝓝 0) := by
      have hcont : Continuous fun u : ℝ => u / (π * (u ^ 2 + 1)) :=
        continuous_id.div (by fun_prop) fun u => by positivity
      have hc : Tendsto (fun u : ℝ => u / (π * (u ^ 2 + 1))) (𝓝 0) (𝓝 (0 / (π * (0 ^ 2 + 1)))) :=
        hcont.continuousAt.tendsto
      simp only [zero_div] at hc
      refine (hc.comp tendsto_inv_atTop_zero).congr' ?_
      filter_upwards [eventually_gt_atTop 0] with r hr
      simp only [Function.comp]
      field_simp
    have := hr.comp (tendsto_norm_cobounded_atTop (E := ℝ))
    refine this.congr fun x => ?_
    simp only [Function.comp, unitLorentzian, Real.norm_eq_abs, sq_abs]
    ring

/-- As the linewidths `s gamma_m` shrink to zero, the catalog density of states of
lifetime-broadened modes converges, against every integrable test function continuous at the
mode frequencies, to the delta sum `sum_m (A_m / 2) (phi(omega_m) + phi(-omega_m))`. -/
theorem tendsto_catalogFourierDOS_zero_linewidth {M : ℕ} (A gamma w : Fin M → ℝ)
    (hg : ∀ m, 0 < gamma m) {phi : ℝ → ℝ} (hphi : Integrable phi)
    (hc : ∀ m, ContinuousAt phi (w m) ∧ ContinuousAt phi (-w m)) :
    Tendsto (fun s : ℝ => ∫ omega, catalogFourierDOS (dampedVACF A (s • gamma) w) omega * phi omega)
      (𝓝[>] 0) (𝓝 (∑ m, A m / 2 * (phi (w m) + phi (-w m)))) := by
  obtain ⟨hnn, hone, hdecay⟩ := unitLorentzian_peak
  have hpeak : ∀ (x0 : ℝ) (g : ℝ) (hg : 0 < g), ContinuousAt phi x0 →
      Tendsto (fun s : ℝ => ∫ x, lorentzian (s * g) (x - x0) * phi x) (𝓝[>] 0) (𝓝 (phi x0)) := by
    intro x0 g hg hcont
    have hbase := tendsto_integral_comp_smul_smul_of_integrable' (μ := volume) hnn hone hdecay
      hphi hcont
    have hc : Tendsto (fun s : ℝ => (s * g)⁻¹) (𝓝[>] 0) atTop := by
      have : Tendsto (fun s : ℝ => s * g) (𝓝[>] 0) (𝓝[>] 0) := by
        refine tendsto_nhdsWithin_iff.2 ⟨?_, ?_⟩
        · have h0 : Tendsto (fun s : ℝ => s * g) (𝓝 0) (𝓝 0) := by
            simpa using ((by fun_prop : Continuous fun s : ℝ => s * g).tendsto (0 : ℝ))
          exact h0.mono_left nhdsWithin_le_nhds
        · filter_upwards [self_mem_nhdsWithin] with s (hs : 0 < s) using mul_pos hs hg
      exact tendsto_inv_nhdsGT_zero.comp this
    refine (hbase.comp hc).congr' ?_
    filter_upwards [self_mem_nhdsWithin] with s (hs : 0 < s)
    simp only [Function.comp]
    refine integral_congr_ae (Eventually.of_forall fun x => ?_)
    simp only [smul_eq_mul]
    rw [lorentzian_eq_scaled (mul_pos hs hg) x0 x, smul_eq_mul]
  have hint : ∀ (s : ℝ), 0 < s → ∀ m (x0 : ℝ),
      Integrable fun x => lorentzian (s * gamma m) (x - x0) * phi x := by
    intro s hs m x0
    have h1 : 0 < s * gamma m := mul_pos hs (hg m)
    have hcont : Continuous fun x => lorentzian (s * gamma m) (x - x0) := by
      unfold lorentzian
      exact continuous_const.div (by fun_prop) fun x => by positivity
    refine hphi.bdd_mul (c := (s * gamma m)⁻¹ / π) hcont.aestronglyMeasurable ?_
    refine Eventually.of_forall fun x => ?_
    unfold lorentzian
    rw [Real.norm_of_nonneg (by positivity)]
    have hd : π * (s * gamma m) ^ 2 ≤ π * ((s * gamma m) ^ 2 + (x - x0) ^ 2) := by
      nlinarith [sq_nonneg (x - x0), pi_pos]
    calc s * gamma m / (π * ((s * gamma m) ^ 2 + (x - x0) ^ 2))
        ≤ s * gamma m / (π * (s * gamma m) ^ 2) :=
          div_le_div_of_nonneg_left h1.le (by positivity) hd
      _ = (s * gamma m)⁻¹ / π := by field_simp
  have hsum : ∀ᶠ s in 𝓝[>] (0 : ℝ),
      ∫ omega, catalogFourierDOS (dampedVACF A (s • gamma) w) omega * phi omega =
        ∑ m, A m / 2 * ((∫ x, lorentzian (s * gamma m) (x - w m) * phi x) +
          ∫ x, lorentzian (s * gamma m) (x - -w m) * phi x) := by
    filter_upwards [self_mem_nhdsWithin] with s (hs : 0 < s)
    have hG : ∀ m, 0 < (s • gamma) m := fun m => by simpa using mul_pos hs (hg m)
    have hpt : ∀ omega, catalogFourierDOS (dampedVACF A (s • gamma) w) omega * phi omega =
        ∑ m, A m / 2 * (lorentzian (s * gamma m) (omega - w m) * phi omega +
          lorentzian (s * gamma m) (omega - -w m) * phi omega) := by
      intro omega
      rw [catalogFourierDOS_damped A (s • gamma) w hG, sum_mul]
      refine sum_congr rfl fun m _ => ?_
      simp only [Pi.smul_apply, smul_eq_mul, sub_neg_eq_add]
      ring
    simp only [hpt]
    rw [integral_finsetSum]
    swap
    · intro m _
      exact ((hint s hs m (w m)).add (hint s hs m (-w m))).const_mul (A m / 2)
    refine sum_congr rfl fun m _ => ?_
    rw [integral_const_mul, integral_add (hint s hs m _) (hint s hs m _)]
  refine Tendsto.congr' (EventuallyEq.symm hsum) ?_
  refine tendsto_finsetSum _ fun m _ => ?_
  exact ((hpeak (w m) (gamma m) (hg m) (hc m).1).add
    (hpeak (-w m) (gamma m) (hg m) (hc m).2)).const_mul _

end OMAI.PhyslibBridge.VACFSpectrum
