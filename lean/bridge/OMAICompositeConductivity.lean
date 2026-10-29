module

public import Mathlib.Analysis.SpecialFunctions.Artanh
public import Mathlib.Analysis.SpecialFunctions.Trigonometric.ArctanDeriv
public import Mathlib.Analysis.SpecialFunctions.Log.Deriv
public import Mathlib.Analysis.SpecialFunctions.Pow.Real
public import Mathlib.MeasureTheory.Integral.IntervalIntegral.FundThmCalculus
public import Mathlib.MeasureTheory.Integral.DominatedConvergence
public import Mathlib.Tactic

/-!
# Effective thermal conductivity of filled composites

The catalog computes the polar depolarization factor `L33(p)` of a spheroidal inclusion
with aspect ratio `p = d3/d1`, the Nan effective conductivity of randomly oriented and of
aligned filler with an interfacial (Kapitza) series film, and the Hasselman-Johnson
conductivity of spheres. Physlib has no effective-medium model, so these results use
Mathlib only and identify no Physlib declaration.

Both closed-form branches of `L33` and the sphere value equal one integral,
`L33(p) = int_0^1 t^2 / (t^2 + p^2 (1 - t^2)) dt`. From it, `0 < L33 < 1`, `L33` decreases
strictly with `p`, the three catalog branches join continuously at the sphere `p = 1`,
`L33 -> 0` for long needles and `L33 -> 1` for thin disks.

For every spheroid shape and volume fraction the random Nan conductivity exceeds the matrix
value by `km f (2 b11 + b33) / (3 - f (2 L11 b11 + L33 b33))` with a positive denominator, so
filler whose Kapitza-corrected conductivities both exceed the matrix raises it. For spheres
both Nan formulas reduce to Maxwell-Garnett with the Kapitza-corrected filler conductivity
`kc = k / (1 + 2 k / (G d))`, which tends to `k` without interface resistance, and the
random value lies between the matrix value and `kc`. The aligned (axial) Nan conductivity
decreases strictly with `L33` and lies strictly between the series and parallel (Wiener)
mixtures, so at fixed `d3` it increases strictly with the aspect ratio. The
Hasselman-Johnson formula is Maxwell-Garnett at `d = 2 a`, with `a` the sphere radius and `d`
the catalog's full particle dimension; it exceeds the matrix conductivity exactly above the
critical radius `a_c = (k_m / G) * k / (k - k_m)`.
-/

@[expose] public section

noncomputable section

open Real Set Filter MeasureTheory intervalIntegral
open scoped Topology Interval

namespace OMAI.PhyslibBridge.Composites

/-! ## Catalog transcriptions -/

/-- The reviewed catalog expression of `depolarization_factors`: the polar depolarization
factor `L33` of a spheroid with aspect ratio `p = d3/d1`, the sphere value `1/3` at `p = 1`,
an `atanh` branch for prolate `p > 1` and an `atan` branch otherwise. This definition alone
is not a physical proof. -/
def depolarization (p : ℝ) : ℝ :=
  if p = 1 then 1 / 3
  else if 1 < p then
    (-√(1 - 1 / p ^ 2) + artanh (√(1 - 1 / p ^ 2))) / (p ^ 2 * (1 - 1 / p ^ 2) ^ ((3 : ℝ) / 2))
  else
    (√(-1 + 1 / p ^ 2) - arctan (√(-1 + 1 / p ^ 2))) / (p ^ 2 * (-1 + 1 / p ^ 2) ^ ((3 : ℝ) / 2))

/-- The catalog's interface-corrected (Kapitza) filler conductivity
`k / (1 + 2 k / (G d))` along a direction of particle dimension `d`. -/
def kapitzaCorrected (k G d : ℝ) : ℝ := k / (1 + 2 * k / (G * d))

/-- The catalog's Nan term `beta = (kc - km) / (L (kc - km) + km)`. -/
def nanBeta (km kc L : ℝ) : ℝ := (-km + kc) / (L * (-km + kc) + km)

/-- The reviewed catalog expression of `nan_effective_kappa` (randomly oriented filler),
with inputs matrix conductivity `km`, filler conductivities `k11`, `k33` and dimensions
`d1`, `d3`, interface conductance `G`, volume fraction `f` and depolarization factors
`L11`, `L33`. This definition alone is not a physical proof. -/
def nanRandom (km k11 k33 d1 d3 G f L11 L33 : ℝ) : ℝ :=
  km * (f * (2 * (1 - L11) * nanBeta km (kapitzaCorrected k11 G d1) L11 +
      (1 - L33) * nanBeta km (kapitzaCorrected k33 G d3) L33) + 3) /
    (-f * (2 * L11 * nanBeta km (kapitzaCorrected k11 G d1) L11 +
      L33 * nanBeta km (kapitzaCorrected k33 G d3) L33) + 3)

/-- The reviewed catalog expression of `nan_effective_kappa_aligned`, the axial component of
the aligned-filler conductivity, with inputs `km`, filler `k33` and `d3`, `G`, `f` and `L33`.
This definition alone is not a physical proof. -/
def nanAligned (km k33 d3 G f L33 : ℝ) : ℝ :=
  km * (f * (1 - L33) * nanBeta km (kapitzaCorrected k33 G d3) L33 + 1) /
    (-L33 * f * nanBeta km (kapitzaCorrected k33 G d3) L33 + 1)

/-- The reviewed catalog expression of `hasselman_johnson` for spheres of radius `a`, with
inputs `km`, filler `k33` and `a`, `G` and `f`. This definition alone is not a physical
proof. -/
def hasselmanJohnson (km k33 a G f : ℝ) : ℝ :=
  km * (2 * f * (-km + (1 - km / (G * a)) * k33) + 2 * km + (1 + 2 * km / (G * a)) * k33) /
    (-f * (-km + (1 - km / (G * a)) * k33) + 2 * km + (1 + 2 * km / (G * a)) * k33)

/-- The Maxwell-Garnett conductivity of spheres of conductivity `kp` at volume fraction `f`
in a matrix of conductivity `km`. A reference model, not a catalog operator. -/
def maxwellGarnett (km kp f : ℝ) : ℝ :=
  km * (kp + 2 * km + 2 * f * (kp - km)) / (kp + 2 * km - f * (kp - km))

/-- The critical sphere radius at which a Hasselman-Johnson filler of conductivity `kp`
leaves the matrix conductivity unchanged. -/
def criticalRadius (km kp G : ℝ) : ℝ := km / G * (kp / (kp - km))

/-! ## The depolarization factor as an integral -/

/-- The integrand of the depolarization integral. -/
def depolIntegrand (p t : ℝ) : ℝ := t ^ 2 / (t ^ 2 + p ^ 2 * (1 - t ^ 2))

theorem depolDenom_pos {p t : ℝ} (hp : 0 < p) (ht : t ∈ Icc (0 : ℝ) 1) :
    0 < t ^ 2 + p ^ 2 * (1 - t ^ 2) := by
  obtain ⟨h0, h1⟩ := ht
  have ht2 : t ^ 2 ≤ 1 := by nlinarith
  have h1t : 0 ≤ 1 - t ^ 2 := by linarith
  rcases le_or_gt p 1 with hp1 | hp1
  · have hp2 : p ^ 2 ≤ 1 := by nlinarith
    nlinarith [mul_nonneg (sq_nonneg t) (sub_nonneg.mpr hp2), pow_pos hp 2]
  · have hp2 : 1 ≤ p ^ 2 := by nlinarith
    nlinarith [mul_nonneg (sub_nonneg.mpr hp2) h1t]

private theorem depolIntegrand_continuousAt {p t : ℝ}
    (hd : t ^ 2 + p ^ 2 * (1 - t ^ 2) ≠ 0) : ContinuousAt (depolIntegrand p) t := by
  unfold depolIntegrand
  exact ContinuousAt.div (by fun_prop) (by fun_prop) hd

private theorem depolIntegrand_continuousAt_param {p t : ℝ}
    (hd : t ^ 2 + p ^ 2 * (1 - t ^ 2) ≠ 0) : ContinuousAt (fun q => depolIntegrand q t) p := by
  unfold depolIntegrand
  exact ContinuousAt.div (by fun_prop) (by fun_prop) hd

private theorem depolIntegrand_continuousOn {p : ℝ} (hp : 0 < p) :
    ContinuousOn (depolIntegrand p) (Icc 0 1) := fun _ ht =>
  (depolIntegrand_continuousAt (depolDenom_pos hp ht).ne').continuousWithinAt

private theorem depolIntegrand_intervalIntegrable {p : ℝ} (hp : 0 < p) :
    IntervalIntegrable (depolIntegrand p) volume 0 1 :=
  (depolIntegrand_continuousOn hp).intervalIntegrable_of_Icc zero_le_one

private theorem hasDerivAt_artanh {x : ℝ} (hx : x ∈ Ioo (-1 : ℝ) 1) :
    HasDerivAt artanh (1 / (1 - x ^ 2)) x := by
  obtain ⟨h1, h2⟩ := hx
  have hp : 0 < 1 + x := by linarith
  have hm : 0 < 1 - x := by linarith
  have hlog : HasDerivAt (fun y => 1 / 2 * (log (1 + y) - log (1 - y)))
      (1 / 2 * (1 / (1 + x) - (-1) / (1 - x))) x := by
    have ha : HasDerivAt (fun y => 1 + y) 1 x := by
      simpa using (hasDerivAt_id x).const_add 1
    have hb : HasDerivAt (fun y => 1 - y) (-1) x := by
      simpa using (hasDerivAt_id x).const_sub 1
    have := ((ha.log hp.ne').sub (hb.log hm.ne')).const_mul (1 / 2)
    simpa [div_eq_mul_inv] using this
  have heq : (fun y => 1 / 2 * (log (1 + y) - log (1 - y))) =ᶠ[𝓝 x] artanh := by
    filter_upwards [Ioo_mem_nhds h1 h2] with y hy
    obtain ⟨hy1, hy2⟩ := hy
    rw [artanh_eq_half_log ⟨hy1.le, hy2.le⟩, log_div (by linarith) (by linarith)]
  refine (hlog.congr_of_eventuallyEq heq.symm).congr_deriv ?_
  have hx2 : 1 - x ^ 2 ≠ 0 := by nlinarith
  have hp' := hp.ne'
  have hm' := hm.ne'
  field_simp
  ring

private theorem rpow_three_halves {x : ℝ} (hx : 0 ≤ x) : x ^ ((3 : ℝ) / 2) = √x ^ 3 := by
  rw [sqrt_eq_rpow, ← rpow_natCast, ← rpow_mul hx]
  norm_num

/-- The derivative `(1 - c e / e) / (1 - p^2)` of `(t - h (e t) / e) / (1 - p^2)` is the
depolarization integrand when `c = h' (e t) = p^2 / (t^2 + p^2 (1 - t^2))`. -/
private theorem antiderivative_deriv {p e t c : ℝ} (he : 0 < e)
    (hc : 1 - p ^ 2 ≠ 0) (hd : 0 < t ^ 2 + p ^ 2 * (1 - t ^ 2))
    (hcval : c = p ^ 2 / (t ^ 2 + p ^ 2 * (1 - t ^ 2))) :
    (1 - c * e / e) / (1 - p ^ 2) = depolIntegrand p t := by
  rw [hcval]
  unfold depolIntegrand
  have := hd.ne'
  have := he.ne'
  field_simp
  ring

/-- Both closed-form branches of the catalog depolarization factor and its sphere value
equal `int_0^1 t^2 / (t^2 + p^2 (1 - t^2)) dt` for every positive aspect ratio. -/
theorem depolarization_eq_integral {p : ℝ} (hp : 0 < p) :
    depolarization p = ∫ t in (0 : ℝ)..1, depolIntegrand p t := by
  rcases lt_trichotomy p 1 with hlt | heq | hgt
  · -- oblate: the arctangent branch
    have hp1 : p ≠ 1 := hlt.ne
    have hnot : ¬ 1 < p := not_lt.mpr hlt.le
    have hu0 : 0 < -1 + 1 / p ^ 2 := by
      have : 1 < 1 / p ^ 2 := by
        rw [lt_div_iff₀ (by positivity)]; nlinarith
      linarith
    set e := √(-1 + 1 / p ^ 2) with he
    have he0 : 0 < e := sqrt_pos.mpr hu0
    have hee : e ^ 2 = -1 + 1 / p ^ 2 := sq_sqrt hu0.le
    have hc : 1 - p ^ 2 = p ^ 2 * e ^ 2 := by
      rw [hee]; field_simp; ring
    have hcne : 1 - p ^ 2 ≠ 0 := by nlinarith
    let F : ℝ → ℝ := fun t => (t - arctan (e * t) / e) / (1 - p ^ 2)
    have hF : ∀ t ∈ uIcc (0 : ℝ) 1, HasDerivAt F (depolIntegrand p t) t := by
      intro t ht
      rw [uIcc_of_le zero_le_one] at ht
      have hd := depolDenom_pos hp ht
      have hlin : HasDerivAt (fun t : ℝ => e * t) e t := by
        simpa using (hasDerivAt_id t).const_mul e
      have h1 : HasDerivAt (fun t => arctan (e * t)) (1 / (1 + (e * t) ^ 2) * e) t :=
        (hasDerivAt_arctan (e * t)).comp t hlin
      have h2 := ((hasDerivAt_id t).sub (h1.div_const e)).div_const (1 - p ^ 2)
      refine h2.congr_deriv (antiderivative_deriv he0 hcne hd ?_)
      have hden : 1 + (e * t) ^ 2 = (t ^ 2 + p ^ 2 * (1 - t ^ 2)) / p ^ 2 := by
        rw [mul_pow, hee]; field_simp; ring
      rw [hden, one_div_div]
    rw [integral_eq_sub_of_hasDerivAt hF (depolIntegrand_intervalIntegrable hp)]
    have hF1 : F 1 - F 0 = (e - arctan e) / (p ^ 2 * e ^ 3) := by
      simp only [F, mul_one, mul_zero, arctan_zero, zero_div, sub_zero]
      rw [hc]
      field_simp
    rw [hF1]
    simp only [depolarization, hp1, hnot, ↓reduceIte]
    rw [rpow_three_halves hu0.le, ← he]
  · -- the sphere
    subst heq
    have hI : ∀ t ∈ uIcc (0 : ℝ) 1,
        HasDerivAt (fun t : ℝ => t ^ 3 / 3) (depolIntegrand 1 t) t := by
      intro t _
      refine ((hasDerivAt_pow 3 t).div_const 3).congr_deriv ?_
      unfold depolIntegrand
      field_simp
      ring
    rw [integral_eq_sub_of_hasDerivAt hI (depolIntegrand_intervalIntegrable one_pos)]
    simp [depolarization]
  · -- prolate: the artanh branch
    have hp1 : p ≠ 1 := hgt.ne'
    have hpinv : 0 < 1 / p ^ 2 := by positivity
    have hu0 : 0 < 1 - 1 / p ^ 2 := by
      have : 1 / p ^ 2 < 1 := by
        rw [div_lt_one (by positivity)]; nlinarith
      linarith
    have hu1 : 1 - 1 / p ^ 2 < 1 := by linarith
    set e := √(1 - 1 / p ^ 2) with he
    have he0 : 0 < e := sqrt_pos.mpr hu0
    have hee : e ^ 2 = 1 - 1 / p ^ 2 := sq_sqrt hu0.le
    have he1 : e < 1 := by
      rw [he, sqrt_lt' one_pos]; simpa using hu1
    have hc : 1 - p ^ 2 = -(p ^ 2 * e ^ 2) := by
      rw [hee]; field_simp; ring
    have hcne : 1 - p ^ 2 ≠ 0 := by nlinarith
    let F : ℝ → ℝ := fun t => (t - artanh (e * t) / e) / (1 - p ^ 2)
    have hF : ∀ t ∈ uIcc (0 : ℝ) 1, HasDerivAt F (depolIntegrand p t) t := by
      intro t ht
      rw [uIcc_of_le zero_le_one] at ht
      have hd := depolDenom_pos hp ht
      have het : e * t ∈ Ioo (-1 : ℝ) 1 := by
        constructor
        · nlinarith [ht.1]
        · nlinarith [ht.2]
      have hlin : HasDerivAt (fun t : ℝ => e * t) e t := by
        simpa using (hasDerivAt_id t).const_mul e
      have h1 : HasDerivAt (fun t => artanh (e * t)) (1 / (1 - (e * t) ^ 2) * e) t :=
        (hasDerivAt_artanh het).comp t hlin
      have h2 := ((hasDerivAt_id t).sub (h1.div_const e)).div_const (1 - p ^ 2)
      refine h2.congr_deriv (antiderivative_deriv he0 hcne hd ?_)
      have hden : 1 - (e * t) ^ 2 = (t ^ 2 + p ^ 2 * (1 - t ^ 2)) / p ^ 2 := by
        rw [mul_pow, hee]; field_simp; ring
      rw [hden, one_div_div]
    rw [integral_eq_sub_of_hasDerivAt hF (depolIntegrand_intervalIntegrable hp)]
    have hF1 : F 1 - F 0 = (-e + artanh e) / (p ^ 2 * e ^ 3) := by
      simp only [F, mul_one, mul_zero, artanh_zero, zero_div, sub_zero]
      rw [hc]
      field_simp
      ring
    rw [hF1]
    simp only [depolarization, hp1, hgt, ↓reduceIte]
    rw [rpow_three_halves hu0.le, ← he]

private theorem depolIntegrand_le_one {p t : ℝ} (hp : 0 < p) (ht : t ∈ Icc (0 : ℝ) 1) :
    depolIntegrand p t ≤ 1 := by
  unfold depolIntegrand
  rw [div_le_one (depolDenom_pos hp ht)]
  have h1 : 0 ≤ 1 - t ^ 2 := by nlinarith [ht.1, ht.2]
  nlinarith [mul_nonneg (sq_nonneg p) h1]

private theorem depolIntegrand_nonneg {p t : ℝ} (hp : 0 < p) (ht : t ∈ Icc (0 : ℝ) 1) :
    0 ≤ depolIntegrand p t :=
  div_nonneg (sq_nonneg t) (depolDenom_pos hp ht).le

/-- The catalog depolarization factor lies strictly between 0 and 1 for every positive
aspect ratio. -/
theorem depolarization_mem_Ioo {p : ℝ} (hp : 0 < p) : depolarization p ∈ Ioo (0 : ℝ) 1 := by
  rw [depolarization_eq_integral hp]
  constructor
  · refine intervalIntegral_pos_of_pos_on
      ((depolIntegrand_continuousOn hp).intervalIntegrable_of_Icc zero_le_one) ?_ zero_lt_one
    intro t ht
    exact div_pos (pow_pos ht.1 2) (depolDenom_pos hp ⟨ht.1.le, ht.2.le⟩)
  · have h := integral_lt_integral_of_continuousOn_of_le_of_exists_lt (f := depolIntegrand p)
      (g := fun _ => (1 : ℝ)) zero_lt_one (depolIntegrand_continuousOn hp) continuousOn_const
      (fun t ht => depolIntegrand_le_one hp ⟨ht.1.le, ht.2⟩)
      ⟨0, ⟨le_rfl, zero_le_one⟩, by simp [depolIntegrand]⟩
    simpa using h

/-- The catalog depolarization factor decreases strictly with the aspect ratio. -/
theorem depolarization_strictAntiOn : StrictAntiOn depolarization (Ioi 0) := by
  intro p hp q hq hpq
  simp only [mem_Ioi] at hp hq
  rw [depolarization_eq_integral hp, depolarization_eq_integral hq]
  refine integral_lt_integral_of_continuousOn_of_le_of_exists_lt zero_lt_one
    (depolIntegrand_continuousOn hq) (depolIntegrand_continuousOn hp) ?_ ?_
  · intro t ht
    unfold depolIntegrand
    refine div_le_div_of_nonneg_left (sq_nonneg t) (depolDenom_pos hp ⟨ht.1.le, ht.2⟩) ?_
    have h1 : 0 ≤ 1 - t ^ 2 := by nlinarith [ht.1, ht.2]
    nlinarith [mul_le_mul_of_nonneg_right (pow_le_pow_left₀ hp.le hpq.le 2) h1]
  · refine ⟨1 / 2, ⟨by norm_num, by norm_num⟩, ?_⟩
    unfold depolIntegrand
    refine div_lt_div_of_pos_left (by norm_num) (depolDenom_pos hp ⟨by norm_num, by norm_num⟩) ?_
    nlinarith [mul_lt_mul_of_pos_left hpq hp, mul_lt_mul_of_pos_left hpq hq]

private theorem ae_mem_Ioo :
    ∀ᵐ t ∂(volume : Measure ℝ), t ∈ Ι (0 : ℝ) 1 → t ∈ Ioo (0 : ℝ) 1 := by
  have h1 : ∀ᵐ t ∂(volume : Measure ℝ), t ≠ 1 := by
    rw [ae_iff]; simp
  filter_upwards [h1] with t ht htI
  rw [uIoc_of_le zero_le_one] at htI
  exact ⟨htI.1, lt_of_le_of_ne htI.2 ht⟩

private theorem depol_dominated {l : Filter ℝ} [l.IsCountablyGenerated] {g : ℝ → ℝ}
    (hl : ∀ᶠ p in l, 0 < p)
    (hlim : ∀ t ∈ Ioo (0 : ℝ) 1, Tendsto (fun p => depolIntegrand p t) l (𝓝 (g t))) :
    Tendsto (fun p => ∫ t in (0 : ℝ)..1, depolIntegrand p t) l
      (𝓝 (∫ t in (0 : ℝ)..1, g t)) := by
  refine tendsto_integral_filter_of_dominated_convergence (fun _ => (1 : ℝ)) ?_ ?_
    intervalIntegrable_const ?_
  · filter_upwards [hl] with p hp
    exact ((depolIntegrand_continuousOn hp).mono (by
      rw [uIoc_of_le zero_le_one]; exact Ioc_subset_Icc_self)).aestronglyMeasurable
        measurableSet_uIoc
  · filter_upwards [hl] with p hp
    refine Eventually.of_forall fun t ht => ?_
    rw [uIoc_of_le zero_le_one] at ht
    have hmem : t ∈ Icc (0 : ℝ) 1 := ⟨ht.1.le, ht.2⟩
    rw [Real.norm_of_nonneg (depolIntegrand_nonneg hp hmem)]
    exact depolIntegrand_le_one hp hmem
  · filter_upwards [ae_mem_Ioo] with t ht htI
    exact hlim t (ht htI)

/-- The three catalog branches of the depolarization factor join continuously: the factor
is continuous on all positive aspect ratios, through the sphere `p = 1`. -/
theorem depolarization_continuousOn : ContinuousOn depolarization (Ioi 0) := by
  intro p₀ hp₀
  simp only [mem_Ioi] at hp₀
  have heq : (fun p => ∫ t in (0 : ℝ)..1, depolIntegrand p t) =ᶠ[𝓝 p₀] depolarization := by
    filter_upwards [Ioi_mem_nhds hp₀] with p hp
    exact (depolarization_eq_integral hp).symm
  have hcont : Tendsto (fun p => ∫ t in (0 : ℝ)..1, depolIntegrand p t) (𝓝 p₀)
      (𝓝 (∫ t in (0 : ℝ)..1, depolIntegrand p₀ t)) := by
    refine depol_dominated (Ioi_mem_nhds hp₀) fun t ht => ?_
    have hd := depolDenom_pos hp₀ ⟨ht.1.le, ht.2.le⟩
    exact (depolIntegrand_continuousAt_param hd.ne').tendsto
  rw [← depolarization_eq_integral hp₀] at hcont
  exact (show ContinuousAt depolarization p₀ from hcont.congr' heq).continuousWithinAt

/-- In particular the factor tends to the sphere value `1/3` as the aspect ratio tends to 1
from either side. -/
theorem tendsto_depolarization_sphere :
    Tendsto depolarization (𝓝[≠] 1) (𝓝 (1 / 3)) := by
  have h := (depolarization_continuousOn.continuousAt (Ioi_mem_nhds one_pos)).tendsto
  have h1 : depolarization 1 = 1 / 3 := by simp [depolarization]
  rw [h1] at h
  exact h.mono_left nhdsWithin_le_nhds

/-- Long needles have a vanishing polar depolarization factor. -/
theorem tendsto_depolarization_atTop : Tendsto depolarization atTop (𝓝 0) := by
  have h := depol_dominated (l := atTop) (g := fun _ => (0 : ℝ)) (eventually_gt_atTop 0)
    (fun t ht => by
      have hc : 0 < 1 - t ^ 2 := by nlinarith [ht.1, ht.2]
      have hden : Tendsto (fun p : ℝ => t ^ 2 + p ^ 2 * (1 - t ^ 2)) atTop atTop := by
        refine tendsto_atTop_add_const_left _ _ ?_
        exact (tendsto_pow_atTop two_ne_zero).atTop_mul_const hc
      exact hden.const_div_atTop _ |>.congr fun p => rfl)
  simp only [intervalIntegral.integral_zero] at h
  refine h.congr' ?_
  filter_upwards [eventually_gt_atTop 0] with p hp
  exact (depolarization_eq_integral hp).symm

/-- Thin disks have a polar depolarization factor that tends to 1. -/
theorem tendsto_depolarization_zero : Tendsto depolarization (𝓝[>] 0) (𝓝 1) := by
  have h := depol_dominated (l := 𝓝[>] 0) (g := fun _ => (1 : ℝ)) self_mem_nhdsWithin
    (fun t ht => by
      have ht2 : 0 < t ^ 2 := pow_pos ht.1 2
      have hc : ContinuousAt (fun p : ℝ => depolIntegrand p t) 0 :=
        depolIntegrand_continuousAt_param (by simpa using ht2.ne')
      have h0 : depolIntegrand 0 t = 1 := by
        unfold depolIntegrand; simp [ht2.ne']
      rw [← h0]
      exact hc.tendsto.mono_left nhdsWithin_le_nhds)
  simp only [intervalIntegral.integral_const, sub_zero, smul_eq_mul, mul_one] at h
  refine h.congr' ?_
  filter_upwards [self_mem_nhdsWithin] with p hp
  exact (depolarization_eq_integral hp).symm

/-! ## Maxwell-Garnett and the Kapitza-corrected filler -/

/-- Without interface resistance the Kapitza-corrected filler conductivity is the bulk
filler conductivity. -/
theorem tendsto_kapitzaCorrected (k d : ℝ) (hd : 0 < d) :
    Tendsto (fun G => kapitzaCorrected k G d) atTop (𝓝 k) := by
  have h : Tendsto (fun G : ℝ => 1 + 2 * k / (G * d)) atTop (𝓝 1) := by
    have : Tendsto (fun G : ℝ => 2 * k / (G * d)) atTop (𝓝 0) :=
      tendsto_const_nhds.div_atTop (tendsto_id.atTop_mul_const hd)
    simpa using this.const_add 1
  have h2 : Tendsto (fun G => k / (1 + 2 * k / (G * d))) atTop (𝓝 (k / 1)) :=
    tendsto_const_nhds.div h one_ne_zero
  rw [div_one] at h2
  exact h2

theorem kapitzaCorrected_pos {k G d : ℝ} (hk : 0 < k) (hG : 0 < G) (hd : 0 < d) :
    0 < kapitzaCorrected k G d := by
  unfold kapitzaCorrected; positivity

private theorem maxwellDenom_pos {km kp f : ℝ} (hm : 0 < km) (hp : 0 < kp)
    (hf : f ∈ Icc (0 : ℝ) 1) : 0 < kp + 2 * km - f * (kp - km) := by
  nlinarith [hf.1, hf.2]

private theorem maxwellGarnett_sub {km kp f : ℝ} (hm : 0 < km) (hp : 0 < kp)
    (hf : f ∈ Icc (0 : ℝ) 1) :
    maxwellGarnett km kp f - km = 3 * km * f * (kp - km) / (kp + 2 * km - f * (kp - km)) := by
  have hD := maxwellDenom_pos hm hp hf
  unfold maxwellGarnett
  rw [eq_div_iff hD.ne', sub_mul, div_mul_cancel₀ _ hD.ne']
  ring

/-- With a filler more conductive than the matrix, the Maxwell-Garnett conductivity
increases strictly with the volume fraction on `[0, 1]`. -/
theorem maxwellGarnett_strictMonoOn {km kp : ℝ} (hm : 0 < km) (hp : km < kp) :
    StrictMonoOn (maxwellGarnett km kp) (Icc 0 1) := by
  intro f hf g hg hfg
  have hp0 : 0 < kp := hm.trans hp
  have hDf := maxwellDenom_pos hm hp0 hf
  have hDg := maxwellDenom_pos hm hp0 hg
  have h1 := maxwellGarnett_sub hm hp0 hf
  have h2 := maxwellGarnett_sub hm hp0 hg
  have : maxwellGarnett km kp f - km < maxwellGarnett km kp g - km := by
    rw [h1, h2, div_lt_div_iff₀ hDf hDg]
    nlinarith [mul_pos (mul_pos hm (sub_pos.mpr hp)) (sub_pos.mpr hfg),
      mul_pos (mul_pos hm (sub_pos.mpr hp)) (add_pos hp0 (mul_pos two_pos hm))]
  linarith

/-- With a filler less conductive than the matrix, the Maxwell-Garnett conductivity
decreases strictly with the volume fraction on `[0, 1]`. -/
theorem maxwellGarnett_strictAntiOn {km kp : ℝ} (hm : 0 < km) (hp0 : 0 < kp) (hp : kp < km) :
    StrictAntiOn (maxwellGarnett km kp) (Icc 0 1) := by
  intro f hf g hg hfg
  have hDf := maxwellDenom_pos hm hp0 hf
  have hDg := maxwellDenom_pos hm hp0 hg
  have h1 := maxwellGarnett_sub hm hp0 hf
  have h2 := maxwellGarnett_sub hm hp0 hg
  have : maxwellGarnett km kp g - km < maxwellGarnett km kp f - km := by
    rw [h1, h2, div_lt_div_iff₀ hDg hDf]
    nlinarith [mul_pos (mul_pos hm (sub_pos.mpr hp)) (sub_pos.mpr hfg),
      mul_pos (mul_pos hm (sub_pos.mpr hp)) (add_pos hp0 (mul_pos two_pos hm))]
  linarith

/-- The Maxwell-Garnett conductivity exceeds the matrix value exactly when the filler is
more conductive than the matrix, for every positive volume fraction. -/
theorem maxwellGarnett_gt_iff {km kp f : ℝ} (hm : 0 < km) (hp : 0 < kp)
    (hf : f ∈ Ioc (0 : ℝ) 1) : km < maxwellGarnett km kp f ↔ km < kp := by
  have hf' : f ∈ Icc (0 : ℝ) 1 := ⟨hf.1.le, hf.2⟩
  have hD := maxwellDenom_pos hm hp hf'
  rw [← sub_pos, maxwellGarnett_sub hm hp hf', div_pos_iff_of_pos_right hD]
  constructor
  · intro h
    by_contra hle
    have : 3 * km * f * (kp - km) ≤ 0 :=
      mul_nonpos_of_nonneg_of_nonpos (by have := hf.1; positivity) (by linarith [not_lt.mp hle])
    linarith
  · intro h
    have := hf.1
    positivity

theorem maxwellGarnett_eq_iff {km kp f : ℝ} (hm : 0 < km) (hp : 0 < kp)
    (hf : f ∈ Ioc (0 : ℝ) 1) : maxwellGarnett km kp f = km ↔ kp = km := by
  have hf' : f ∈ Icc (0 : ℝ) 1 := ⟨hf.1.le, hf.2⟩
  have hD := maxwellDenom_pos hm hp hf'
  rw [← sub_eq_zero, maxwellGarnett_sub hm hp hf', div_eq_zero_iff]
  have hf0 := hf.1
  constructor
  · rintro (h | h)
    · have : 3 * km * f ≠ 0 := by positivity
      rcases mul_eq_zero.mp h with h' | h'
      · exact absurd h' this
      · linarith
    · exact absurd h hD.ne'
  · intro h; left; rw [h]; ring

/-! ## Every shape: the sign of the random Nan enhancement -/

private theorem nanDenom_pos {km c L : ℝ} (hm : 0 < km) (hc : 0 < c)
    (hL : L ∈ Icc (0 : ℝ) 1) : 0 < L * (-km + c) + km := by
  rcases eq_or_lt_of_le hL.1 with h | h
  · subst h; simpa using hm
  · nlinarith [mul_pos h hc, mul_nonneg (sub_nonneg.mpr hL.2) hm.le]

private theorem mul_nanBeta_lt_one {km c L : ℝ} (hm : 0 < km) (hc : 0 < c)
    (hL : L ∈ Icc (0 : ℝ) 1) : L * nanBeta km c L < 1 := by
  have hB := nanDenom_pos hm hc hL
  unfold nanBeta
  rw [mul_div_assoc', div_lt_one hB]
  linarith

private theorem nanBeta_pos_iff {km c L : ℝ} (hm : 0 < km) (hc : 0 < c)
    (hL : L ∈ Icc (0 : ℝ) 1) : 0 < nanBeta km c L ↔ km < c := by
  unfold nanBeta
  rw [lt_div_iff₀ (nanDenom_pos hm hc hL), zero_mul]
  constructor <;> intro h <;> linarith

private theorem nanBeta_neg_iff {km c L : ℝ} (hm : 0 < km) (hc : 0 < c)
    (hL : L ∈ Icc (0 : ℝ) 1) : nanBeta km c L < 0 ↔ c < km := by
  unfold nanBeta
  rw [div_lt_iff₀ (nanDenom_pos hm hc hL), zero_mul]
  constructor <;> intro h <;> linarith

/-- For every spheroid shape (`L11`, `L33` in `[0, 1]`) and volume fraction in `[0, 1]`, the
catalog's random Nan conductivity exceeds the matrix value by
`km f (2 b11 + b33) / (3 - f (2 L11 b11 + L33 b33))`, where `b_ii` are the catalog's Nan
terms of the Kapitza-corrected filler conductivities, and the denominator is positive
because `L b < 1` for each direction. -/
theorem nanRandom_sub_matrix {km k11 k33 d1 d3 G f L11 L33 : ℝ} (hm : 0 < km) (hk11 : 0 < k11)
    (hk33 : 0 < k33) (hd1 : 0 < d1) (hd3 : 0 < d3) (hG : 0 < G) (hf : f ∈ Icc (0 : ℝ) 1)
    (hL11 : L11 ∈ Icc (0 : ℝ) 1) (hL33 : L33 ∈ Icc (0 : ℝ) 1) :
    0 < 3 - f * (2 * L11 * nanBeta km (kapitzaCorrected k11 G d1) L11 +
        L33 * nanBeta km (kapitzaCorrected k33 G d3) L33) ∧
      nanRandom km k11 k33 d1 d3 G f L11 L33 - km =
        km * f * (2 * nanBeta km (kapitzaCorrected k11 G d1) L11 +
            nanBeta km (kapitzaCorrected k33 G d3) L33) /
          (3 - f * (2 * L11 * nanBeta km (kapitzaCorrected k11 G d1) L11 +
            L33 * nanBeta km (kapitzaCorrected k33 G d3) L33)) := by
  have h1 := mul_nanBeta_lt_one hm (kapitzaCorrected_pos hk11 hG hd1) hL11
  have h3 := mul_nanBeta_lt_one hm (kapitzaCorrected_pos hk33 hG hd3) hL33
  unfold nanRandom
  set b1 := nanBeta km (kapitzaCorrected k11 G d1) L11
  set b3 := nanBeta km (kapitzaCorrected k33 G d3) L33
  have hS : 2 * L11 * b1 + L33 * b3 < 3 := by nlinarith
  have hD : 0 < 3 - f * (2 * L11 * b1 + L33 * b3) := by
    rcases le_or_gt (2 * L11 * b1 + L33 * b3) 0 with hneg | hpos
    · nlinarith [mul_nonpos_of_nonneg_of_nonpos hf.1 hneg]
    · nlinarith [mul_le_of_le_one_left hpos.le hf.2]
  refine ⟨hD, ?_⟩
  rw [eq_div_iff hD.ne',
    show -f * (2 * L11 * b1 + L33 * b3) + 3 = 3 - f * (2 * L11 * b1 + L33 * b3) by ring,
    sub_mul, div_mul_cancel₀ _ hD.ne']
  ring

/-- For every spheroid shape the catalog's random Nan conductivity exceeds the matrix value
exactly when `2 b11 + b33 > 0`, at every volume fraction in `(0, 1]`. -/
theorem nanRandom_gt_iff {km k11 k33 d1 d3 G f L11 L33 : ℝ} (hm : 0 < km) (hk11 : 0 < k11)
    (hk33 : 0 < k33) (hd1 : 0 < d1) (hd3 : 0 < d3) (hG : 0 < G) (hf : f ∈ Ioc (0 : ℝ) 1)
    (hL11 : L11 ∈ Icc (0 : ℝ) 1) (hL33 : L33 ∈ Icc (0 : ℝ) 1) :
    km < nanRandom km k11 k33 d1 d3 G f L11 L33 ↔
      0 < 2 * nanBeta km (kapitzaCorrected k11 G d1) L11 +
        nanBeta km (kapitzaCorrected k33 G d3) L33 := by
  obtain ⟨hD, hsub⟩ := nanRandom_sub_matrix hm hk11 hk33 hd1 hd3 hG ⟨hf.1.le, hf.2⟩ hL11 hL33
  rw [← sub_pos, hsub, div_pos_iff_of_pos_right hD, mul_pos_iff_of_pos_left (mul_pos hm hf.1)]

/-- For every spheroid shape, filler whose Kapitza-corrected conductivities both exceed the
matrix value raises the catalog's random Nan conductivity above it, and filler whose
corrected conductivities both fall below it lowers it, at every volume fraction in `(0, 1]`. -/
theorem nanRandom_sign {km k11 k33 d1 d3 G f L11 L33 : ℝ} (hm : 0 < km) (hk11 : 0 < k11)
    (hk33 : 0 < k33) (hd1 : 0 < d1) (hd3 : 0 < d3) (hG : 0 < G) (hf : f ∈ Ioc (0 : ℝ) 1)
    (hL11 : L11 ∈ Icc (0 : ℝ) 1) (hL33 : L33 ∈ Icc (0 : ℝ) 1) :
    (km < kapitzaCorrected k11 G d1 → km < kapitzaCorrected k33 G d3 →
        km < nanRandom km k11 k33 d1 d3 G f L11 L33) ∧
      (kapitzaCorrected k11 G d1 < km → kapitzaCorrected k33 G d3 < km →
        nanRandom km k11 k33 d1 d3 G f L11 L33 < km) := by
  have hc1 := kapitzaCorrected_pos hk11 hG hd1
  have hc3 := kapitzaCorrected_pos hk33 hG hd3
  obtain ⟨hD, hsub⟩ := nanRandom_sub_matrix hm hk11 hk33 hd1 hd3 hG ⟨hf.1.le, hf.2⟩ hL11 hL33
  have hkf : 0 < km * f := mul_pos hm hf.1
  constructor
  · intro h1 h3
    have b1 := (nanBeta_pos_iff hm hc1 hL11).mpr h1
    have b3 := (nanBeta_pos_iff hm hc3 hL33).mpr h3
    rw [← sub_pos, hsub]
    exact div_pos (mul_pos hkf (by linarith)) hD
  · intro h1 h3
    have b1 := (nanBeta_neg_iff hm hc1 hL11).mpr h1
    have b3 := (nanBeta_neg_iff hm hc3 hL33).mpr h3
    rw [← sub_neg, hsub]
    exact div_neg_of_neg_of_pos (mul_neg_of_pos_of_neg hkf (by linarith)) hD

/-! ## Spheres: Nan and Hasselman-Johnson reduce to Maxwell-Garnett -/

private theorem nanBeta_third {km c : ℝ} (h : c + 2 * km ≠ 0) :
    nanBeta km c (1 / 3) = 3 * (c - km) / (c + 2 * km) := by
  unfold nanBeta
  rw [div_eq_div_iff (by rw [show 1 / 3 * (-km + c) + km = (c + 2 * km) / 3 by ring]; positivity) h]
  ring

/-- For isotropic spheres (`L11 = L33 = 1/3`, `k11 = k33 = k`, `d1 = d3 = d`) the catalog's
random-orientation Nan conductivity is Maxwell-Garnett with the Kapitza-corrected filler
conductivity, at every volume fraction. -/
theorem nanRandom_sphere {km k d G f : ℝ} (hm : 0 < km) (hk : 0 < k) (hd : 0 < d)
    (hG : 0 < G) :
    nanRandom km k k d d G f (1 / 3) (1 / 3) =
      maxwellGarnett km (kapitzaCorrected k G d) f := by
  have hc := kapitzaCorrected_pos hk hG hd
  set c := kapitzaCorrected k G d
  have hc2 : c + 2 * km ≠ 0 := by positivity
  unfold nanRandom maxwellGarnett
  rw [nanBeta_third hc2]
  have hden : -f * (2 * (1 / 3) * (3 * (c - km) / (c + 2 * km)) +
      1 / 3 * (3 * (c - km) / (c + 2 * km))) + 3 =
      3 * (c + 2 * km - f * (c - km)) / (c + 2 * km) := by
    rw [eq_div_iff hc2]; field_simp; ring
  have hnum : km * (f * (2 * (1 - 1 / 3) * (3 * (c - km) / (c + 2 * km)) +
      (1 - 1 / 3) * (3 * (c - km) / (c + 2 * km))) + 3) =
      3 * (km * (c + 2 * km + 2 * f * (c - km))) / (c + 2 * km) := by
    rw [eq_div_iff hc2]; field_simp; ring
  rw [hden, hnum, div_div_div_cancel_right₀ hc2, mul_div_mul_left _ _ three_ne_zero]

/-- For aligned spheres (`L33 = 1/3`) the catalog's aligned Nan conductivity is the same
Maxwell-Garnett value, at every volume fraction. -/
theorem nanAligned_sphere {km k d G f : ℝ} (hm : 0 < km) (hk : 0 < k) (hd : 0 < d)
    (hG : 0 < G) :
    nanAligned km k d G f (1 / 3) = maxwellGarnett km (kapitzaCorrected k G d) f := by
  have hc := kapitzaCorrected_pos hk hG hd
  set c := kapitzaCorrected k G d
  have hc2 : c + 2 * km ≠ 0 := by positivity
  unfold nanAligned maxwellGarnett
  rw [nanBeta_third hc2]
  have hden : -(1 / 3) * f * (3 * (c - km) / (c + 2 * km)) + 1 =
      (c + 2 * km - f * (c - km)) / (c + 2 * km) := by
    rw [eq_div_iff hc2]; field_simp; ring
  have hnum : km * (f * (1 - 1 / 3) * (3 * (c - km) / (c + 2 * km)) + 1) =
      km * (c + 2 * km + 2 * f * (c - km)) / (c + 2 * km) := by
    rw [eq_div_iff hc2]; field_simp; ring
  rw [hden, hnum, div_div_div_cancel_right₀ hc2]

/-- For spheres the catalog's random Nan conductivity lies between the matrix value and the
Kapitza-corrected filler conductivity for every volume fraction in `[0, 1]`. -/
theorem nanRandom_sphere_between {km k d G f : ℝ} (hm : 0 < km) (hk : 0 < k) (hd : 0 < d)
    (hG : 0 < G) (hf : f ∈ Icc (0 : ℝ) 1) :
    min km (kapitzaCorrected k G d) ≤ nanRandom km k k d d G f (1 / 3) (1 / 3) ∧
      nanRandom km k k d d G f (1 / 3) (1 / 3) ≤ max km (kapitzaCorrected k G d) := by
  rw [nanRandom_sphere hm hk hd hG]
  have hc := kapitzaCorrected_pos hk hG hd
  set c := kapitzaCorrected k G d
  have hc2 : c + 2 * km ≠ 0 := by positivity
  have h0 : maxwellGarnett km c 0 = km := by
    unfold maxwellGarnett
    rw [div_eq_iff (by simpa using hc2)]; ring
  have h1 : maxwellGarnett km c 1 = c := by
    unfold maxwellGarnett
    rw [div_eq_iff (by nlinarith)]; ring
  rcases lt_trichotomy km c with hlt | heq | hgt
  · have hmono := maxwellGarnett_strictMonoOn hm hlt
    have a := hmono.monotoneOn ⟨le_rfl, zero_le_one⟩ hf hf.1
    have b := hmono.monotoneOn hf ⟨zero_le_one, le_rfl⟩ hf.2
    rw [h0] at a; rw [h1] at b
    exact ⟨(min_le_left _ _).trans a, b.trans (le_max_right _ _)⟩
  · rw [← heq]
    have : maxwellGarnett km km f = km := by
      unfold maxwellGarnett
      rw [div_eq_iff (by nlinarith)]; ring
    rw [this]; simp
  · have hanti := maxwellGarnett_strictAntiOn hm hc hgt
    have a := hanti.antitoneOn ⟨le_rfl, zero_le_one⟩ hf hf.1
    have b := hanti.antitoneOn hf ⟨zero_le_one, le_rfl⟩ hf.2
    rw [h0] at a; rw [h1] at b
    exact ⟨(min_le_right _ _).trans b, a.trans (le_max_left _ _)⟩

/-- Without interface resistance the catalog's random Nan conductivity of spheres tends to
the Maxwell-Garnett value of the bulk filler. -/
theorem tendsto_nanRandom_sphere {km k d f : ℝ} (hm : 0 < km) (hk : 0 < k) (hd : 0 < d)
    (hf : f ∈ Icc (0 : ℝ) 1) :
    Tendsto (fun G => nanRandom km k k d d G f (1 / 3) (1 / 3)) atTop
      (𝓝 (maxwellGarnett km k f)) := by
  have hcont : ContinuousAt (fun x => maxwellGarnett km x f) k := by
    unfold maxwellGarnett
    exact (by fun_prop : ContinuousAt (fun x => km * (x + 2 * km + 2 * f * (x - km))) k).div
      (by fun_prop) (maxwellDenom_pos hm hk hf).ne'
  have h := hcont.tendsto.comp (tendsto_kapitzaCorrected k d hd)
  refine h.congr' ?_
  filter_upwards [eventually_gt_atTop 0] with G hG
  exact (nanRandom_sphere hm hk hd hG).symm

/-- The catalog's Hasselman-Johnson conductivity of spheres of radius `a` is Maxwell-Garnett
with the Kapitza-corrected filler conductivity for particle dimension `d = 2 a`, at every
volume fraction. -/
theorem hasselmanJohnson_eq_maxwellGarnett {km k a G f : ℝ} (hk : 0 < k) (ha : 0 < a)
    (hG : 0 < G) :
    hasselmanJohnson km k a G f = maxwellGarnett km (kapitzaCorrected k G (2 * a)) f := by
  have hGa : G * a ≠ 0 := by positivity
  have hs : 1 + k / (G * a) ≠ 0 := by positivity
  have hkc : kapitzaCorrected k G (2 * a) = k / (1 + k / (G * a)) := by
    unfold kapitzaCorrected
    rw [show G * (2 * a) = 2 * (G * a) by ring, mul_div_mul_left _ _ two_ne_zero]
  rw [hkc]
  unfold hasselmanJohnson maxwellGarnett
  have hnum : km * (2 * f * (-km + (1 - km / (G * a)) * k) + 2 * km + (1 + 2 * km / (G * a)) * k) =
      (1 + k / (G * a)) *
        (km * (k / (1 + k / (G * a)) + 2 * km + 2 * f * (k / (1 + k / (G * a)) - km))) := by
    field_simp; ring
  have hden : -f * (-km + (1 - km / (G * a)) * k) + 2 * km + (1 + 2 * km / (G * a)) * k =
      (1 + k / (G * a)) *
        (k / (1 + k / (G * a)) + 2 * km - f * (k / (1 + k / (G * a)) - km)) := by
    field_simp; ring
  rw [hnum, hden, mul_div_mul_left _ _ hs]

/-- For spheres of radius `a` the catalog's random Nan conductivity with particle dimension
`d = 2 a` equals its Hasselman-Johnson conductivity. -/
theorem nanRandom_sphere_eq_hasselmanJohnson {km k a G f : ℝ} (hm : 0 < km) (hk : 0 < k)
    (ha : 0 < a) (hG : 0 < G) :
    nanRandom km k k (2 * a) (2 * a) G f (1 / 3) (1 / 3) = hasselmanJohnson km k a G f := by
  rw [nanRandom_sphere hm hk (by positivity) hG, hasselmanJohnson_eq_maxwellGarnett hk ha hG]

/-- The catalog's Hasselman-Johnson conductivity exceeds the matrix conductivity exactly when
the sphere radius exceeds the critical radius `(km / G) * kp / (kp - km)`, and equals it
exactly at that radius, for a filler more conductive than the matrix and any positive
volume fraction. -/
theorem hasselmanJohnson_critical_radius {km kp a G f : ℝ} (hm : 0 < km) (hkp : km < kp)
    (ha : 0 < a) (hG : 0 < G) (hf : f ∈ Ioc (0 : ℝ) 1) :
    (km < hasselmanJohnson km kp a G f ↔ criticalRadius km kp G < a) ∧
      (hasselmanJohnson km kp a G f = km ↔ a = criticalRadius km kp G) := by
  have hp : 0 < kp := hm.trans hkp
  have hc := kapitzaCorrected_pos hp hG (by positivity : 0 < 2 * a)
  have hsub : 0 < kp - km := sub_pos.mpr hkp
  rw [hasselmanJohnson_eq_maxwellGarnett hp ha hG, maxwellGarnett_gt_iff hm hc hf,
    maxwellGarnett_eq_iff hm hc hf]
  have hkc : kapitzaCorrected kp G (2 * a) = kp * G * a / (G * a + kp) := by
    unfold kapitzaCorrected
    rw [div_eq_div_iff (by positivity) (by positivity)]
    field_simp
  have hac : criticalRadius km kp G = km * kp / (G * (kp - km)) := by
    unfold criticalRadius
    rw [div_mul_div_comm]
  rw [hkc, hac]
  constructor
  · rw [lt_div_iff₀ (by positivity), div_lt_iff₀ (by positivity)]
    constructor <;> intro h <;> nlinarith
  · rw [div_eq_iff (by positivity), eq_div_iff (by positivity)]
    constructor <;> intro h <;> nlinarith

/-! ## Aligned filler: between the series and parallel mixtures -/

private theorem alignedDenom_pos {km c f L : ℝ} (hm : 0 < km) (hc : 0 < c)
    (hf : f ∈ Icc (0 : ℝ) 1) (hL : L ∈ Icc (0 : ℝ) 1) :
    0 < km + L * (c - km) * (1 - f) := by
  have hw0 : 0 ≤ L * (1 - f) := mul_nonneg hL.1 (by linarith [hf.2])
  have hw1 : L * (1 - f) ≤ 1 := by nlinarith [hL.1, hL.2, hf.1, hf.2]
  rcases le_total km c with h | h
  · nlinarith [mul_nonneg hw0 (sub_nonneg.mpr h)]
  · nlinarith [mul_nonneg (sub_nonneg.mpr hw1) (sub_nonneg.mpr h)]

private theorem nanAligned_closed {km k d G f L : ℝ} (hm : 0 < km) (hk : 0 < k) (hd : 0 < d)
    (hG : 0 < G) (hf : f ∈ Icc (0 : ℝ) 1) (hL : L ∈ Icc (0 : ℝ) 1) :
    nanAligned km k d G f L =
      km + km * f * (kapitzaCorrected k G d - km) /
        (km + L * (kapitzaCorrected k G d - km) * (1 - f)) := by
  have hc := kapitzaCorrected_pos hk hG hd
  set c := kapitzaCorrected k G d
  have hD := alignedDenom_pos hm hc hf hL
  have hB : 0 < L * (-km + c) + km := by
    have := alignedDenom_pos hm hc ⟨le_rfl, zero_le_one⟩ hL
    linarith
  unfold nanAligned nanBeta
  rw [← show kapitzaCorrected k G d = c from rfl]
  set β := (-km + c) / (L * (-km + c) + km) with hβdef
  have hβ : β * (L * (-km + c) + km) = -km + c := div_mul_cancel₀ _ hB.ne'
  have hden : -L * f * β + 1 = (km + L * (c - km) * (1 - f)) / (L * (-km + c) + km) := by
    rw [eq_div_iff hB.ne']
    linear_combination (-L * f) * hβ
  have hnum : f * (1 - L) * β + 1 =
      (km + L * (c - km) * (1 - f) + f * (c - km)) / (L * (-km + c) + km) := by
    rw [eq_div_iff hB.ne']
    linear_combination (f * (1 - L)) * hβ
  rw [hden, hnum, mul_div_assoc', div_div_div_cancel_right₀ hB.ne', add_div' _ _ _ hD.ne']
  congr 1
  ring

private theorem nanAligned_needle {km k d G f : ℝ} (hm : 0 < km) (hk : 0 < k) (hd : 0 < d)
    (hG : 0 < G) (hf : f ∈ Icc (0 : ℝ) 1) :
    nanAligned km k d G f 0 = (1 - f) * km + f * kapitzaCorrected k G d := by
  rw [nanAligned_closed hm hk hd hG hf ⟨le_rfl, zero_le_one⟩]
  simp only [zero_mul, add_zero]
  rw [mul_assoc, mul_div_cancel_left₀ _ hm.ne']
  ring

private theorem nanAligned_disk {km k d G f : ℝ} (hm : 0 < km) (hk : 0 < k) (hd : 0 < d)
    (hG : 0 < G) (hf : f ∈ Icc (0 : ℝ) 1) :
    nanAligned km k d G f 1 = 1 / ((1 - f) / km + f / kapitzaCorrected k G d) := by
  have hc := kapitzaCorrected_pos hk hG hd
  have hD := alignedDenom_pos hm hc hf ⟨zero_le_one, le_rfl⟩
  rw [nanAligned_closed hm hk hd hG hf ⟨zero_le_one, le_rfl⟩]
  set c := kapitzaCorrected k G d
  have hs : 0 < (1 - f) * c + km * f := by nlinarith [hf.1, hf.2]
  rw [div_add_div _ _ hm.ne' hc.ne', one_div_div, add_div' _ _ _ hD.ne',
    div_eq_div_iff hD.ne' hs.ne']
  ring

/-- The catalog's aligned Nan conductivity decreases strictly with the polar depolarization
factor on `[0, 1]` whenever the Kapitza-corrected filler differs from the matrix and the
fraction is strictly between 0 and 1. -/
theorem nanAligned_strictAntiOn {km k d G f : ℝ} (hm : 0 < km) (hk : 0 < k) (hd : 0 < d)
    (hG : 0 < G) (hf : f ∈ Ioo (0 : ℝ) 1) (hne : kapitzaCorrected k G d ≠ km) :
    StrictAntiOn (nanAligned km k d G f) (Icc 0 1) := by
  have hf' : f ∈ Icc (0 : ℝ) 1 := ⟨hf.1.le, hf.2.le⟩
  have hc := kapitzaCorrected_pos hk hG hd
  intro L hL L' hL' hLL
  rw [nanAligned_closed hm hk hd hG hf' hL, nanAligned_closed hm hk hd hG hf' hL']
  set c := kapitzaCorrected k G d
  have hD := alignedDenom_pos hm hc hf' hL
  have hD' := alignedDenom_pos hm hc hf' hL'
  have hΔ : 0 < (c - km) ^ 2 := by
    have : c - km ≠ 0 := sub_ne_zero.mpr hne
    positivity
  suffices h : km * f * (c - km) / (km + L' * (c - km) * (1 - f)) <
      km * f * (c - km) / (km + L * (c - km) * (1 - f)) by linarith
  rw [div_lt_div_iff₀ hD' hD]
  have hpos : 0 < km * f * (1 - f) * (L' - L) * (c - km) ^ 2 := by
    have := hf.1; have := hf.2
    have : 0 < 1 - f := by linarith
    have : 0 < L' - L := by linarith
    positivity
  nlinarith

/-- For a polar depolarization factor and a volume fraction strictly between 0 and 1 and a
Kapitza-corrected filler conductivity different from the matrix, the catalog's aligned Nan
conductivity lies strictly between the series mixture `1 / ((1 - f)/km + f/kc)` and the
parallel mixture `(1 - f) km + f kc` (the Wiener bounds). -/
theorem nanAligned_strict_wiener {km k d G f L : ℝ} (hm : 0 < km) (hk : 0 < k) (hd : 0 < d)
    (hG : 0 < G) (hf : f ∈ Ioo (0 : ℝ) 1) (hL : L ∈ Ioo (0 : ℝ) 1)
    (hne : kapitzaCorrected k G d ≠ km) :
    1 / ((1 - f) / km + f / kapitzaCorrected k G d) < nanAligned km k d G f L ∧
      nanAligned km k d G f L < (1 - f) * km + f * kapitzaCorrected k G d := by
  have hanti := nanAligned_strictAntiOn hm hk hd hG hf hne
  have hf' : f ∈ Icc (0 : ℝ) 1 := ⟨hf.1.le, hf.2.le⟩
  have hL' : L ∈ Icc (0 : ℝ) 1 := ⟨hL.1.le, hL.2.le⟩
  refine ⟨?_, ?_⟩
  · rw [← nanAligned_disk hm hk hd hG hf']
    exact hanti hL' ⟨zero_le_one, le_rfl⟩ hL.2
  · rw [← nanAligned_needle hm hk hd hG hf']
    exact hanti ⟨le_rfl, zero_le_one⟩ hL' hL.1

/-- With the filler's axial dimension `d` (`d3`), and so its Kapitza correction, held fixed,
the catalog's aligned Nan conductivity along the alignment axis increases strictly with the
spheroid aspect ratio `p`, through the depolarization factor `L33(p)`. -/
theorem nanAligned_strictMonoOn_aspect {km k d G f : ℝ} (hm : 0 < km) (hk : 0 < k)
    (hd : 0 < d) (hG : 0 < G) (hf : f ∈ Ioo (0 : ℝ) 1) (hne : kapitzaCorrected k G d ≠ km) :
    StrictMonoOn (fun p => nanAligned km k d G f (depolarization p)) (Ioi 0) := by
  intro p hp q hq hpq
  have hmem : ∀ x ∈ Ioi (0 : ℝ), depolarization x ∈ Icc (0 : ℝ) 1 := fun x hx =>
    Ioo_subset_Icc_self (depolarization_mem_Ioo hx)
  exact nanAligned_strictAntiOn hm hk hd hG hf hne (hmem q hq) (hmem p hp)
    (depolarization_strictAntiOn hp hq hpq)

end OMAI.PhyslibBridge.Composites
