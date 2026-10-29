module

public import Mathlib.Analysis.SpecialFunctions.Pow.Continuity
public import Mathlib.Analysis.Calculus.Deriv.Inverse
public import Mathlib.Analysis.Calculus.InverseFunctionTheorem.Deriv
public import Mathlib.MeasureTheory.Integral.IntervalIntegral.FundThmCalculus
public import Mathlib.Topology.Order.IntermediateValue
public import Mathlib.Tactic

/-!
# Cure kinetics of a thermoset

The catalog's isothermal Kamal-Sourour cure time is the integral
`t(alpha) = int_{alpha0}^{alpha} da / ((1 - a)^n (k1 + k2 a^m))` with
`k_i = A_i exp(-E_i / (N_A k_B T))`, and its DiBenedetto relation gives the glass transition
temperature `T_g(alpha) = T_g0 + alpha lambda (T_ginf - T_g0) / (1 - (1 - lambda) alpha)`.
Physlib has no polymer-cure model, so these results use Mathlib only and identify no
Physlib declaration.

The cure time increases strictly with conversion below full cure and its derivative is the
reciprocal Kamal rate. Near every interior cure time there is one inverse `alpha(t)` that
solves the Kamal rate law `d alpha / dt = (k1 + k2 alpha^m)(1 - alpha)^n` at every time of a
neighbourhood, and every continuous local inverse solves it. The DiBenedetto relation maps
`[0, 1]` strictly increasingly onto `[T_g0, T_ginf]` for `lambda > 0` and `T_g0 < T_ginf`,
and for `0 < lambda < 1` it lies strictly below the linear interpolation inside the interval.
-/

@[expose] public section

noncomputable section

open Real Set Filter MeasureTheory intervalIntegral
open scoped Topology

namespace OMAI.PhyslibBridge.CureKinetics

/-! ## Catalog transcriptions -/

/-- The reviewed catalog expression of `kamal_cure_conversion`: the isothermal cure time to
reach conversion `alpha` from `alpha0` at temperature `T`, with Arrhenius prefactors `A1`,
`A2`, activation energies `E1`, `E2` per mole, reaction orders `m`, `n`, Avogadro's number
`NA` and Boltzmann's constant `kB`. This definition alone is not a physical proof. -/
def kamalCureTime (T A1 E1 A2 E2 m n NA kB alpha0 alpha : ℝ) : ℝ :=
  ∫ a in alpha0..alpha, 1 / ((1 - a) ^ n *
    (A1 * exp (-E1 / (NA * T * kB)) + A2 * a ^ m * exp (-E2 / (NA * T * kB))))

/-- The Kamal-Sourour cure rate `(k1 + k2 a^m)(1 - a)^n`. -/
def kamalRate (T A1 E1 A2 E2 m n NA kB a : ℝ) : ℝ :=
  (A1 * exp (-E1 / (NA * T * kB)) + A2 * a ^ m * exp (-E2 / (NA * T * kB))) * (1 - a) ^ n

/-- The reviewed catalog expression of `dibenedetto_glass_transition` in the
Pascault-Williams form, with input conversion `alpha` and parameters `Tg0`, `TgInf` and
`lam`. This definition alone is not a physical proof. -/
def diBenedetto (alpha Tg0 TgInf lam : ℝ) : ℝ :=
  Tg0 + alpha * lam * (-Tg0 + TgInf) / (-alpha * (1 - lam) + 1)

/-! ## Kamal-Sourour cure -/

section Kamal

variable {T A1 E1 A2 E2 m n NA kB alpha0 : ℝ}

/-- Admissible Kamal parameters: nonnegative prefactors, autocatalytic order and initial
conversion, and either a positive noncatalytic rate (which includes pure `n`th-order
kinetics, `A2 = 0`) or a positive initial conversion with a positive autocatalytic rate. Any
real order `n` is admissible, since `1 - a > 0` below full cure. -/
structure KamalAdmissible (A1 A2 m alpha0 : ℝ) : Prop where
  A1_nonneg : 0 ≤ A1
  A2_nonneg : 0 ≤ A2
  m_nonneg : 0 ≤ m
  alpha0_nonneg : 0 ≤ alpha0
  start : 0 < A1 ∨ (0 < alpha0 ∧ 0 < A2)

private theorem rateFactor_pos (h : KamalAdmissible A1 A2 m alpha0) {a : ℝ}
    (ha : alpha0 ≤ a) :
    0 < A1 * exp (-E1 / (NA * T * kB)) + A2 * a ^ m * exp (-E2 / (NA * T * kB)) := by
  have ha0 : 0 ≤ a := h.alpha0_nonneg.trans ha
  have h1 : 0 ≤ A1 * exp (-E1 / (NA * T * kB)) := mul_nonneg h.A1_nonneg (exp_pos _).le
  rcases h.start with hA1 | ⟨hα, hA2⟩
  · have : 0 < A1 * exp (-E1 / (NA * T * kB)) := mul_pos hA1 (exp_pos _)
    have h2 : 0 ≤ A2 * a ^ m * exp (-E2 / (NA * T * kB)) :=
      mul_nonneg (mul_nonneg h.A2_nonneg (rpow_nonneg ha0 _)) (exp_pos _).le
    linarith
  · have hapos : 0 < a := hα.trans_le ha
    have h2 : 0 < A2 * a ^ m * exp (-E2 / (NA * T * kB)) :=
      mul_pos (mul_pos hA2 (rpow_pos_of_pos hapos _)) (exp_pos _)
    linarith

/-- The Kamal rate is positive between the initial conversion and full cure. -/
theorem kamalRate_pos (h : KamalAdmissible A1 A2 m alpha0) {a : ℝ} (ha : alpha0 ≤ a)
    (ha1 : a < 1) : 0 < kamalRate T A1 E1 A2 E2 m n NA kB a := by
  unfold kamalRate
  exact mul_pos (rateFactor_pos h ha) (rpow_pos_of_pos (by linarith) _)

private theorem integrand_eq (a : ℝ) :
    1 / ((1 - a) ^ n * (A1 * exp (-E1 / (NA * T * kB)) + A2 * a ^ m * exp (-E2 / (NA * T * kB))))
      = 1 / kamalRate T A1 E1 A2 E2 m n NA kB a := by
  unfold kamalRate; rw [mul_comm]

private theorem integrand_continuousOn (h : KamalAdmissible A1 A2 m alpha0) {b : ℝ}
    (hb : b < 1) :
    ContinuousOn (fun a => 1 / ((1 - a) ^ n *
      (A1 * exp (-E1 / (NA * T * kB)) + A2 * a ^ m * exp (-E2 / (NA * T * kB))))) (Icc alpha0 b) := by
  have hcm : Continuous fun a : ℝ => a ^ m := continuous_rpow_const h.m_nonneg
  have hcn : ContinuousOn (fun a : ℝ => (1 - a) ^ n) (Icc alpha0 b) := fun a ha =>
    ((by fun_prop : Continuous fun a : ℝ => 1 - a).continuousAt.rpow_const
      (Or.inl (sub_pos.mpr (lt_of_le_of_lt ha.2 hb)).ne')).continuousWithinAt
  have hcr : Continuous fun a : ℝ =>
      A1 * exp (-E1 / (NA * T * kB)) + A2 * a ^ m * exp (-E2 / (NA * T * kB)) := by fun_prop
  refine ContinuousOn.div continuousOn_const (hcn.mul hcr.continuousOn) ?_
  intro a ha
  exact (mul_pos (rpow_pos_of_pos (by linarith [ha.2]) _) (rateFactor_pos h ha.1)).ne'

/-- The catalog's cure time increases strictly with conversion between the initial
conversion and full cure. -/
theorem kamalCureTime_strictMonoOn (h : KamalAdmissible A1 A2 m alpha0) :
    StrictMonoOn (kamalCureTime T A1 E1 A2 E2 m n NA kB alpha0) (Ico alpha0 1) := by
  intro x hx y hy hxy
  unfold kamalCureTime
  have hint : ∀ b, b < 1 → ∀ c ∈ Icc alpha0 b, IntervalIntegrable (fun a => 1 / ((1 - a) ^ n *
      (A1 * exp (-E1 / (NA * T * kB)) + A2 * a ^ m * exp (-E2 / (NA * T * kB))))) volume alpha0 c :=
    fun b hb c hc => ((integrand_continuousOn h hb).mono (Icc_subset_Icc le_rfl hc.2)).intervalIntegrable_of_Icc hc.1
  have hxi := hint y hy.2 x ⟨hx.1, hxy.le⟩
  have hyi := hint y hy.2 y ⟨hy.1, le_rfl⟩
  rw [← sub_pos, integral_interval_sub_left hyi hxi]
  refine intervalIntegral_pos_of_pos_on ?_ (fun a ha => ?_) hxy
  · exact ((integrand_continuousOn h hy.2).mono (Icc_subset_Icc hx.1 le_rfl)).intervalIntegrable_of_Icc hxy.le
  · rw [integrand_eq]
    exact one_div_pos.mpr (kamalRate_pos h (hx.1.trans ha.1.le) (ha.2.trans hy.2))

/-- Above the initial conversion and below full cure, the catalog's cure time is strictly
differentiable with derivative `1 / rate`, the reciprocal Kamal rate. -/
theorem kamalCureTime_hasStrictDerivAt (h : KamalAdmissible A1 A2 m alpha0) {alpha : ℝ}
    (ha : alpha ∈ Ioo alpha0 1) :
    HasStrictDerivAt (kamalCureTime T A1 E1 A2 E2 m n NA kB alpha0)
      (1 / kamalRate T A1 E1 A2 E2 m n NA kB alpha) alpha := by
  obtain ⟨b, hab, hb1⟩ := exists_between ha.2
  have hcont := integrand_continuousOn (T := T) (E1 := E1) (E2 := E2) (n := n) (NA := NA)
    (kB := kB) h hb1
  have hopen : ContinuousOn (fun a => 1 / ((1 - a) ^ n *
      (A1 * exp (-E1 / (NA * T * kB)) + A2 * a ^ m * exp (-E2 / (NA * T * kB))))) (Ioo alpha0 b) :=
    hcont.mono Ioo_subset_Icc_self
  have hmem : alpha ∈ Ioo alpha0 b := ⟨ha.1, hab⟩
  have hat := hopen.continuousAt (Ioo_mem_nhds hmem.1 hmem.2)
  have hderiv := integral_hasStrictDerivAt_right
    ((hcont.mono (Icc_subset_Icc le_rfl hab.le)).intervalIntegrable_of_Icc ha.1.le)
    (hopen.stronglyMeasurableAtFilter isOpen_Ioo alpha hmem) hat
  rw [integrand_eq] at hderiv
  exact hderiv

/-- Above the initial conversion and below full cure, the catalog's cure time has derivative
`1 / rate`, the reciprocal Kamal rate. -/
theorem kamalCureTime_hasDerivAt (h : KamalAdmissible A1 A2 m alpha0) {alpha : ℝ}
    (ha : alpha ∈ Ioo alpha0 1) :
    HasDerivAt (kamalCureTime T A1 E1 A2 E2 m n NA kB alpha0)
      (1 / kamalRate T A1 E1 A2 E2 m n NA kB alpha) alpha :=
  (kamalCureTime_hasStrictDerivAt h ha).hasDerivAt

/-- Every continuous local inverse `alpha(t)` of the catalog's cure time solves the
Kamal-Sourour rate law `d alpha / dt = (k1 + k2 alpha^m)(1 - alpha)^n`. -/
theorem kamal_inverse_solves_rate_law (h : KamalAdmissible A1 A2 m alpha0) {g : ℝ → ℝ}
    {s : ℝ} (hg : ContinuousAt g s) (hgs : g s ∈ Ioo alpha0 1)
    (hinv : ∀ᶠ y in 𝓝 s, kamalCureTime T A1 E1 A2 E2 m n NA kB alpha0 (g y) = y) :
    HasDerivAt g (kamalRate T A1 E1 A2 E2 m n NA kB (g s)) s := by
  have hr := kamalRate_pos (T := T) (E1 := E1) (E2 := E2) (n := n) (NA := NA) (kB := kB) h
    hgs.1.le hgs.2
  have := HasDerivAt.of_local_left_inverse hg (kamalCureTime_hasDerivAt h hgs)
    (one_div_pos.mpr hr).ne' hinv
  simpa [one_div, inv_inv] using this

/-- Near every cure time strictly between the initial conversion and full cure there is one
inverse `alpha(t)` of the catalog's cure time, taking that time back to `alpha`, that solves
the Kamal-Sourour rate law `d alpha / dt = (k1 + k2 alpha^m)(1 - alpha)^n` at every time of a
neighbourhood. -/
theorem kamal_inverse_exists (h : KamalAdmissible A1 A2 m alpha0) {alpha : ℝ}
    (ha : alpha ∈ Ioo alpha0 1) :
    ∃ g : ℝ → ℝ, g (kamalCureTime T A1 E1 A2 E2 m n NA kB alpha0 alpha) = alpha ∧
      ∀ᶠ s in 𝓝 (kamalCureTime T A1 E1 A2 E2 m n NA kB alpha0 alpha),
        kamalCureTime T A1 E1 A2 E2 m n NA kB alpha0 (g s) = s ∧
        HasDerivAt g (kamalRate T A1 E1 A2 E2 m n NA kB (g s)) s := by
  have hs := kamalCureTime_hasStrictDerivAt (T := T) (E1 := E1) (E2 := E2) (n := n) (NA := NA)
    (kB := kB) h ha
  have hr := kamalRate_pos (T := T) (E1 := E1) (E2 := E2) (n := n) (NA := NA) (kB := kB) h
    ha.1.le ha.2
  have hne : 1 / kamalRate T A1 E1 A2 E2 m n NA kB alpha ≠ 0 := (one_div_pos.mpr hr).ne'
  have hF := hs.hasStrictFDerivAt_equiv hne
  set t := kamalCureTime T A1 E1 A2 E2 m n NA kB alpha0
  let Φ := hF.toOpenPartialHomeomorph t
  have hgα : Φ.symm (t alpha) = alpha := hF.localInverse_apply_image
  have htgt : t alpha ∈ Φ.target := hF.image_mem_toOpenPartialHomeomorph_target
  refine ⟨Φ.symm, hgα, ?_⟩
  have hIoo : ∀ᶠ s in 𝓝 (t alpha), Φ.symm s ∈ Ioo alpha0 1 := by
    have := (Φ.continuousAt_symm htgt).tendsto
    rw [hgα] at this
    exact this (Ioo_mem_nhds ha.1 ha.2)
  filter_upwards [Φ.open_target.mem_nhds htgt, hIoo] with s hs_tgt hs_Ioo
  refine ⟨Φ.right_inv hs_tgt, ?_⟩
  exact kamal_inverse_solves_rate_law h (Φ.continuousAt_symm hs_tgt) hs_Ioo
    (by filter_upwards [Φ.open_target.mem_nhds hs_tgt] with y hy; exact Φ.right_inv hy)

end Kamal

/-! ## DiBenedetto relation -/

section DiBenedetto

variable {Tg0 TgInf lam : ℝ}

private theorem dibDenom_pos (hlam : 0 < lam) {a : ℝ} (ha : a ∈ Icc (0 : ℝ) 1) :
    0 < -a * (1 - lam) + 1 := by
  rcases eq_or_lt_of_le ha.2 with h | h
  · subst h; linarith
  · nlinarith [mul_nonneg ha.1 hlam.le]

private theorem diBenedetto_sub (hlam : 0 < lam) {a : ℝ} (ha : a ∈ Icc (0 : ℝ) 1) :
    diBenedetto a Tg0 TgInf lam - Tg0 = (TgInf - Tg0) * (lam * a / (-a * (1 - lam) + 1)) := by
  have := dibDenom_pos hlam ha
  unfold diBenedetto
  field_simp
  ring

/-- The catalog's DiBenedetto glass transition temperature increases strictly with
conversion on `[0, 1]` when `lam > 0` and the fully cured value exceeds the uncured one. -/
theorem diBenedetto_strictMonoOn (hlam : 0 < lam) (hT : Tg0 < TgInf) :
    StrictMonoOn (fun a => diBenedetto a Tg0 TgInf lam) (Icc 0 1) := by
  intro a ha b hb hab
  have hDa := dibDenom_pos hlam ha
  have hDb := dibDenom_pos hlam hb
  have h1 := diBenedetto_sub (Tg0 := Tg0) (TgInf := TgInf) hlam ha
  have h2 := diBenedetto_sub (Tg0 := Tg0) (TgInf := TgInf) hlam hb
  have hlt : lam * a / (-a * (1 - lam) + 1) < lam * b / (-b * (1 - lam) + 1) := by
    rw [div_lt_div_iff₀ hDa hDb]
    nlinarith [mul_pos hlam (sub_pos.mpr hab)]
  have : diBenedetto a Tg0 TgInf lam - Tg0 < diBenedetto b Tg0 TgInf lam - Tg0 := by
    rw [h1, h2]; exact mul_lt_mul_of_pos_left hlt (sub_pos.mpr hT)
  simpa using this

/-- For `lam > 0` the catalog's DiBenedetto relation maps conversions `[0, 1]` one to one
onto `[Tg0, TgInf]`. -/
theorem diBenedetto_bijOn (hlam : 0 < lam) (hT : Tg0 < TgInf) :
    BijOn (fun a => diBenedetto a Tg0 TgInf lam) (Icc 0 1) (Icc Tg0 TgInf) := by
  have h0 : diBenedetto 0 Tg0 TgInf lam = Tg0 := by simp [diBenedetto]
  have h1 : diBenedetto 1 Tg0 TgInf lam = TgInf := by
    unfold diBenedetto
    rw [show -(1 : ℝ) * (1 - lam) + 1 = lam by ring, one_mul,
      mul_div_cancel_left₀ _ hlam.ne']
    ring
  have hmono := diBenedetto_strictMonoOn hlam hT
  have hcont : ContinuousOn (fun a => diBenedetto a Tg0 TgInf lam) (Icc 0 1) := by
    intro a ha
    unfold diBenedetto
    exact (continuousAt_const.add ((by fun_prop : ContinuousAt
      (fun a : ℝ => a * lam * (-Tg0 + TgInf)) a).div (by fun_prop)
      (dibDenom_pos hlam ha).ne')).continuousWithinAt
  refine ⟨fun a ha => ?_, hmono.injOn, fun y hy => ?_⟩
  · have := hmono.monotoneOn ⟨le_rfl, zero_le_one⟩ ha ha.1
    have := hmono.monotoneOn ha ⟨zero_le_one, le_rfl⟩ ha.2
    simp only [h0, h1] at *
    exact ⟨by assumption, by assumption⟩
  · have := intermediate_value_Icc zero_le_one hcont
    simp only [h0, h1] at this
    exact this hy

/-- For `0 < lam < 1` and `Tg0 < TgInf` the catalog's DiBenedetto relation lies strictly
below the linear interpolation at every conversion strictly between 0 and 1. -/
theorem diBenedetto_lt_linear (hlam : 0 < lam) (hlam1 : lam < 1) (hT : Tg0 < TgInf)
    {a : ℝ} (ha : a ∈ Ioo (0 : ℝ) 1) :
    diBenedetto a Tg0 TgInf lam < Tg0 + a * (TgInf - Tg0) := by
  have ha' : a ∈ Icc (0 : ℝ) 1 := ⟨ha.1.le, ha.2.le⟩
  have hD := dibDenom_pos hlam ha'
  have h := diBenedetto_sub (Tg0 := Tg0) (TgInf := TgInf) hlam ha'
  have hlt : lam * a / (-a * (1 - lam) + 1) < a := by
    rw [div_lt_iff₀ hD]
    nlinarith [mul_pos (mul_pos ha.1 (sub_pos.mpr hlam1)) (sub_pos.mpr ha.2)]
  nlinarith [mul_lt_mul_of_pos_left hlt (sub_pos.mpr hT)]

end DiBenedetto

end OMAI.PhyslibBridge.CureKinetics
