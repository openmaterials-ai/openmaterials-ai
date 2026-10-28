module

public import OMAIPhyslibResponseCalculus
public import Mathlib.Analysis.Calculus.ImplicitContDiff
public import Mathlib.Analysis.Calculus.Deriv.MeanValue

/-!
# Local Gibbs minimization of a Helmholtz surface

A two-parameter equilibrium family V(T, p) of a C² Helmholtz surface F(T, V) is differentiable
near a base point, solves F_V + p = 0 there and has positive isothermal curvature at the base
point. On every sufficiently narrow volume window around the base volume, the family is the
unique minimizer of V ↦ F(T, V) + pV. The temperature and pressure derivatives of
F(T, V(T, p)) + pV(T, p) are F_T and V (envelope relations), and (∂V/∂p)_T = -1/F_VV. The
implicit-function theorem constructs such a family from any stable stationary point. Nothing
here identifies a numerical volume scan, EOS fit or minimizer.
-/

@[expose] public section

noncomputable section
open Filter Set
open scoped Topology ContDiff

namespace OMAI.PhyslibBridge.Response

/-- A local two-parameter equilibrium family V(T, p) of a Helmholtz surface. -/
structure GibbsBranchAt (F : Surface) (D : Set (ℝ × ℝ)) (x₀ : ℝ × ℝ) where
  volume : ℝ × ℝ → ℝ
  differentiable : ∀ᶠ x in 𝓝 x₀, DifferentiableAt ℝ volume x
  in_domain : ∀ᶠ x in 𝓝 x₀, (x.1, volume x) ∈ D
  equilibrium : ∀ᶠ x in 𝓝 x₀, FV F (x.1, volume x) + x.2 = 0
  stable : 0 < FVV F (x₀.1, volume x₀)

namespace GibbsBranchAt

variable {F : Surface} {D : Set (ℝ × ℝ)} {t₀ p₀ : ℝ}

/-- F(T, V(T, p)) + p V(T, p) along the family. -/
def gibbs (B : GibbsBranchAt F D (t₀, p₀)) (x : ℝ × ℝ) : ℝ :=
  F (x.1, B.volume x) + x.2 * B.volume x

theorem tendsto_isobar : Tendsto (fun s : ℝ => (s, p₀)) (𝓝 t₀) (𝓝 (t₀, p₀)) :=
  (continuous_id.prodMk continuous_const).tendsto t₀

theorem tendsto_isotherm : Tendsto (fun q : ℝ => (t₀, q)) (𝓝 p₀) (𝓝 (t₀, p₀)) :=
  (continuous_const.prodMk continuous_id).tendsto p₀

theorem isobar_hasDerivAt (B : GibbsBranchAt F D (t₀, p₀)) :
    HasDerivAt (fun s => B.volume (s, p₀)) (fderiv ℝ B.volume (t₀, p₀) (1, 0)) t₀ :=
  B.differentiable.self_of_nhds.hasFDerivAt.comp_hasDerivAt t₀
    ((hasDerivAt_id t₀).prodMk (hasDerivAt_const t₀ p₀))

/-- The constant-pressure path through the base point is a stable branch of the existing
one-parameter response calculus. -/
def isobar (B : GibbsBranchAt F D (t₀, p₀)) : StableBranchAt F D p₀ t₀ where
  volume s := B.volume (s, p₀)
  slope := fderiv ℝ B.volume (t₀, p₀) (1, 0)
  volume_deriv := B.isobar_hasDerivAt
  in_domain := B.in_domain.self_of_nhds
  eventually_in_domain := tendsto_isobar.eventually B.in_domain
  equilibrium := tendsto_isobar.eventually B.equilibrium
  equilibrium_at := B.equilibrium.self_of_nhds
  stable := B.stable

theorem isobar_volume (B : GibbsBranchAt F D (t₀, p₀)) (s : ℝ) :
    B.isobar.volume s = B.volume (s, p₀) := rfl

/-- On every window of half-width at most ε₀ around the base volume, and for every (T, p) near
the base point, the family volume lies in the window and is the unique minimizer there of
V ↦ F(T, V) + pV. -/
theorem window_strictMin (B : GibbsBranchAt F D (t₀, p₀)) (hD : IsOpen D)
    (hF : ContDiffOn ℝ 2 F D) :
    ∃ ε₀ > 0, ∀ ε, 0 < ε → ε ≤ ε₀ → ∀ᶠ x in 𝓝 (t₀, p₀),
      B.volume x ∈ Ioo (B.volume (t₀, p₀) - ε) (B.volume (t₀, p₀) + ε) ∧
      ∀ w ∈ Ioo (B.volume (t₀, p₀) - ε) (B.volume (t₀, p₀) + ε), w ≠ B.volume x →
        B.gibbs x < F (x.1, w) + x.2 * w := by
  set v₀ := B.volume (t₀, p₀) with hv₀
  have hx0 : (t₀, v₀) ∈ D := B.in_domain.self_of_nhds
  have hcont : ContinuousOn (fun y => FVV F y) D := by
    have h1 : ContDiffOn ℝ 1 (fun y => fderiv ℝ F y) D := hF.fderiv_of_isOpen hD (by norm_num)
    have h2 := h1.continuousOn_fderiv_of_isOpen hD le_rfl
    exact (h2.clm_apply continuousOn_const).clm_apply continuousOn_const
  have hnear : ∀ᶠ y in 𝓝 (t₀, v₀), y ∈ D ∧ 0 < FVV F y :=
    Filter.Eventually.and (hD.mem_nhds hx0) ((hcont.continuousAt (hD.mem_nhds hx0)).eventually
      (lt_mem_nhds B.stable))
  obtain ⟨ε₀, hε₀, hball⟩ := Metric.eventually_nhds_iff_ball.mp hnear
  refine ⟨ε₀, hε₀, fun ε hε hεle => ?_⟩
  have hcV : ContinuousAt B.volume (t₀, p₀) := B.differentiable.self_of_nhds.continuousAt
  have hV : ∀ᶠ x in 𝓝 (t₀, p₀), B.volume x ∈ Ioo (v₀ - ε) (v₀ + ε) :=
    hcV.eventually (Ioo_mem_nhds (by linarith) (by linarith))
  have hT : ∀ᶠ x in 𝓝 (t₀, p₀), x.1 ∈ Metric.ball t₀ ε₀ :=
    continuous_fst.continuousAt.eventually (Metric.ball_mem_nhds _ hε₀)
  filter_upwards [hV, hT, B.equilibrium] with x hxV hxT hxeq
  refine ⟨hxV, fun w hw hne => ?_⟩
  set I := Ioo (v₀ - ε₀) (v₀ + ε₀) with hI
  have hsub : Ioo (v₀ - ε) (v₀ + ε) ⊆ I :=
    Ioo_subset_Ioo (by linarith) (by linarith)
  have hbox : ∀ u ∈ I, (x.1, u) ∈ D ∧ 0 < FVV F (x.1, u) := by
    intro u hu
    apply hball
    rw [← ball_prod_same]
    exact ⟨hxT, by rw [Real.ball_eq_Ioo]; exact hu⟩
  set V := B.volume x with hVdef
  let g : ℝ → ℝ := fun u => F (x.1, u) + x.2 * u
  let g' : ℝ → ℝ := fun u => FV F (x.1, u) + x.2
  have hg : ∀ u ∈ I, HasDerivAt g (g' u) u := by
    intro u hu
    have h := (volume_hasDerivAt (hF.contDiffAt (hD.mem_nhds (hbox u hu).1))).fun_add
      ((hasDerivAt_id u).const_mul x.2)
    simp only [mul_one, id_eq] at h
    exact h
  have hg' : ∀ u ∈ I, HasDerivAt g' (FVV F (x.1, u)) u := by
    intro u hu
    exact (partial_volume_hasDerivAt (hF.contDiffAt (hD.mem_nhds (hbox u hu).1)) (0, 1)).add_const x.2
  have hmono : StrictMonoOn g' I := by
    refine strictMonoOn_of_deriv_pos (convex_Ioo _ _)
      (fun u hu => (hg' u hu).continuousAt.continuousWithinAt) ?_
    intro u hu
    rw [interior_Ioo] at hu
    rw [(hg' u hu).deriv]
    exact (hbox u hu).2
  have hVI : V ∈ I := hsub hxV
  have hwI : w ∈ I := hsub hw
  have hg'V : g' V = 0 := hxeq
  have hcont_g : ∀ a b, a ∈ I → b ∈ I → ContinuousOn g (Icc a b) := by
    intro a b ha hb u hu
    exact (hg u ((ordConnected_Ioo).out ha hb hu)).continuousAt.continuousWithinAt
  change g V < g w
  rcases lt_or_gt_of_ne hne with hlt | hgt
  · obtain ⟨c, hc, hcs⟩ := exists_hasDerivAt_eq_slope g g' hlt (hcont_g w V hwI hVI)
      (fun u hu => hg u ((ordConnected_Ioo).out hwI hVI (Ioo_subset_Icc_self hu)))
    have hcI : c ∈ I := (ordConnected_Ioo).out hwI hVI (Ioo_subset_Icc_self hc)
    have hneg : g' c < 0 := hg'V ▸ hmono hcI hVI hc.2
    rw [hcs] at hneg
    have hpos : 0 < V - w := sub_pos.mpr hlt
    have := (div_neg_iff.mp hneg)
    rcases this with ⟨_, h⟩ | ⟨h, _⟩
    · linarith
    · linarith
  · obtain ⟨c, hc, hcs⟩ := exists_hasDerivAt_eq_slope g g' hgt (hcont_g V w hVI hwI)
      (fun u hu => hg u ((ordConnected_Ioo).out hVI hwI (Ioo_subset_Icc_self hu)))
    have hcI : c ∈ I := (ordConnected_Ioo).out hVI hwI (Ioo_subset_Icc_self hc)
    have hpos : 0 < g' c := hg'V ▸ hmono hVI hcI hc.1
    rw [hcs] at hpos
    have hden : 0 < w - V := sub_pos.mpr hgt
    have := (div_pos_iff.mp hpos)
    rcases this with ⟨h, _⟩ | ⟨_, h⟩
    · linarith
    · linarith

/-- Envelope relation in temperature: (∂G/∂T)_p = F_T at the family volume. -/
theorem gibbs_temperature_hasDerivAt (B : GibbsBranchAt F D (t₀, p₀)) (hD : IsOpen D)
    (hF : ContDiffOn ℝ 2 F D) :
    ∀ᶠ x in 𝓝 (t₀, p₀),
      HasDerivAt (fun s => B.gibbs (s, x.2)) (FT F (x.1, B.volume x)) x.1 := by
  filter_upwards [B.differentiable, B.in_domain, B.equilibrium] with x hd hin heq
  obtain ⟨t, p⟩ := x
  have hW : HasDerivAt (fun s => B.volume (s, p)) (fderiv ℝ B.volume (t, p) (1, 0)) t :=
    hd.hasFDerivAt.comp_hasDerivAt t ((hasDerivAt_id t).prodMk (hasDerivAt_const t p))
  have hFx := hF.contDiffAt (hD.mem_nhds hin)
  have h := (surface_along_hasDerivAt hFx hW).fun_add (hW.const_mul p)
  have heq' : FV F (t, B.volume (t, p)) + p = 0 := heq
  show HasDerivAt (fun s => F (s, B.volume (s, p)) + p * B.volume (s, p))
    (FT F (t, B.volume (t, p))) t
  refine h.congr_deriv ?_
  linear_combination (fderiv ℝ B.volume (t, p) (1, 0)) * heq'

/-- Envelope relation in pressure: (∂G/∂p)_T = V. -/
theorem gibbs_pressure_hasDerivAt (B : GibbsBranchAt F D (t₀, p₀)) (hD : IsOpen D)
    (hF : ContDiffOn ℝ 2 F D) :
    ∀ᶠ x in 𝓝 (t₀, p₀), HasDerivAt (fun q => B.gibbs (x.1, q)) (B.volume x) x.2 := by
  filter_upwards [B.differentiable, B.in_domain, B.equilibrium] with x hd hin heq
  obtain ⟨t, p⟩ := x
  set b := fderiv ℝ B.volume (t, p) (0, 1)
  have hW : HasDerivAt (fun q => B.volume (t, q)) b p :=
    hd.hasFDerivAt.comp_hasDerivAt p ((hasDerivAt_const p t).prodMk (hasDerivAt_id p))
  have hFx := hF.contDiffAt (hD.mem_nhds hin)
  have hFq : HasDerivAt (fun q => F (t, B.volume (t, q)))
      (fderiv ℝ F (t, B.volume (t, p)) (0, b)) p :=
    (hFx.differentiableAt (by norm_num)).hasFDerivAt.comp_hasDerivAt p
      ((hasDerivAt_const p t).prodMk hW)
  have hlin : fderiv ℝ F (t, B.volume (t, p)) (0, b) = b * FV F (t, B.volume (t, p)) := by
    have hv : ((0 : ℝ), b) = b • ((0, 1) : ℝ × ℝ) := by ext <;> simp
    rw [hv, map_smul, smul_eq_mul]
    rfl
  have h := hFq.fun_add ((hasDerivAt_id p).fun_mul hW)
  rw [hlin] at h
  have heq' : FV F (t, B.volume (t, p)) + p = 0 := heq
  show HasDerivAt (fun q => F (t, B.volume (t, q)) + q * B.volume (t, q)) (B.volume (t, p)) p
  refine h.congr_deriv ?_
  simp only [id_eq, one_mul]
  linear_combination b * heq'

/-- Isothermal compressibility of the family: (∂V/∂p)_T = -1/F_VV at the base point. -/
theorem isotherm_hasDerivAt (B : GibbsBranchAt F D (t₀, p₀)) (hD : IsOpen D)
    (hF : ContDiffOn ℝ 2 F D) :
    HasDerivAt (fun q => B.volume (t₀, q)) (-1 / FVV F (t₀, B.volume (t₀, p₀))) p₀ := by
  set b := fderiv ℝ B.volume (t₀, p₀) (0, 1)
  have hW : HasDerivAt (fun q => B.volume (t₀, q)) b p₀ :=
    B.differentiable.self_of_nhds.hasFDerivAt.comp_hasDerivAt p₀
      ((hasDerivAt_const p₀ t₀).prodMk (hasDerivAt_id p₀))
  have hFx := hF.contDiffAt (hD.mem_nhds B.in_domain.self_of_nhds)
  have hP := (partial_hasFDerivAt hFx (0, 1)).comp_hasDerivAt p₀
    ((hasDerivAt_const p₀ t₀).prodMk hW)
  have hlin : ((ContinuousLinearMap.apply ℝ ℝ ((0 : ℝ), (1 : ℝ))).comp
      (fderiv ℝ (fderiv ℝ F) (t₀, B.volume (t₀, p₀)))) (0, b) =
        b * FVV F (t₀, B.volume (t₀, p₀)) := by
    have hv : ((0 : ℝ), b) = b • ((0, 1) : ℝ × ℝ) := by ext <;> simp
    rw [hv, map_smul, smul_eq_mul]
    rfl
  rw [hlin] at hP
  have hz : HasDerivAt (fun _ : ℝ => (0 : ℝ)) (b * FVV F (t₀, B.volume (t₀, p₀)) + 1) p₀ := by
    have h := hP.add (hasDerivAt_id p₀)
    refine h.congr_of_eventuallyEq ?_
    filter_upwards [tendsto_isotherm.eventually B.equilibrium] with q hq
    exact hq.symm
  have hb : b * FVV F (t₀, B.volume (t₀, p₀)) + 1 = 0 := hz.unique (hasDerivAt_const p₀ 0)
  have hne := B.stable.ne'
  have : b = -1 / FVV F (t₀, B.volume (t₀, p₀)) := by
    field_simp
    linarith
  rw [← this]
  exact hW

/-- Temperature derivative of F_T along the isobar, before any equilibrium substitution. -/
theorem isobar_FT_hasDerivAt (B : GibbsBranchAt F D (t₀, p₀)) (hD : IsOpen D)
    (hF : ContDiffOn ℝ 2 F D) :
    HasDerivAt (fun s => FT F (s, B.volume (s, p₀)))
      (FTT F (t₀, B.volume (t₀, p₀)) + B.isobar.slope * mixedTV F (t₀, B.volume (t₀, p₀))) t₀ := by
  have hFx := hF.contDiffAt (hD.mem_nhds B.in_domain.self_of_nhds)
  have h := partial_along_hasDerivAt hFx B.isobar.volume_deriv (1, 0)
  simp only [isobar_volume] at h
  rw [mixed_symmetric hFx] at h
  exact h

end GibbsBranchAt

/-- The implicit-function theorem gives a two-parameter equilibrium family through every stable
stationary point of V ↦ F(T, V) + pV. -/
theorem exists_gibbsBranchAt (F : Surface) (D : Set (ℝ × ℝ)) (t v p : ℝ)
    (hD : IsOpen D) (hF : ContDiffOn ℝ 2 F D) (hx : (t, v) ∈ D)
    (heq : FV F (t, v) + p = 0) (hs : 0 < FVV F (t, v)) :
    ∃ B : GibbsBranchAt F D (t, p), B.volume (t, p) = v := by
  let f : (ℝ × ℝ) × ℝ → ℝ := fun y => FV F (y.1.1, y.2) + y.1.2
  let u : (ℝ × ℝ) × ℝ := ((t, p), v)
  have hFx := hF.contDiffAt (hD.mem_nhds hx)
  have hFV1 : ContDiffAt ℝ 1 (fun y => FV F y) (t, v) :=
    (partial_contDiffOn hF hD (0, 1)).contDiffAt (hD.mem_nhds hx)
  have hπ : ContDiffAt ℝ 1 (fun y : (ℝ × ℝ) × ℝ => (y.1.1, y.2)) u := by fun_prop
  have hf : ContDiffAt ℝ 1 f u := by
    have h1 := hFV1.comp u hπ
    have h2 : ContDiffAt ℝ 1 (fun y : (ℝ × ℝ) × ℝ => y.1.2) u := by fun_prop
    exact h1.add h2
  let A := fderiv ℝ f u
  have hline : HasDerivAt (fun w : ℝ => f ((t, p), w)) (A (0, 1)) v :=
    (hf.differentiableAt (by norm_num)).hasFDerivAt.comp_hasDerivAt v
      ((hasDerivAt_const v (t, p)).prodMk (hasDerivAt_id v))
  have hline' : HasDerivAt (fun w : ℝ => f ((t, p), w)) (FVV F (t, v)) v :=
    (partial_volume_hasDerivAt hFx (0, 1)).add_const p
  have hA : A (0, 1) = FVV F (t, v) := hline.unique hline'
  let L : ℝ →L[ℝ] ℝ := A ∘L ContinuousLinearMap.inr ℝ (ℝ × ℝ) ℝ
  have hL (x : ℝ) : L x = x * L 1 := by
    simpa only [smul_eq_mul, mul_one] using L.map_smul x (1 : ℝ)
  have hL1 : L 1 = FVV F (t, v) := hA
  have hL1ne : L 1 ≠ 0 := by rw [hL1]; exact hs.ne'
  have hLi : L.IsInvertible := by
    apply ContinuousLinearMap.IsInvertible.of_inverse
      (g := (L 1)⁻¹ • ContinuousLinearMap.id ℝ ℝ)
    · apply ContinuousLinearMap.ext
      intro x
      simp only [ContinuousLinearMap.comp_apply, smul_apply,
        ContinuousLinearMap.id_apply, smul_eq_mul]
      rw [hL]
      field_simp
    · apply ContinuousLinearMap.ext
      intro x
      simp only [ContinuousLinearMap.comp_apply, smul_apply,
        ContinuousLinearMap.id_apply, smul_eq_mul]
      rw [hL x]
      field_simp
  have hpn : (1 : ℕ∞ω) ≠ 0 := one_ne_zero
  let ψ := hf.implicitFunction hpn hLi
  have hψ0 : ψ (t, p) = v := hf.implicitFunction_apply_self hpn hLi
  have hψeq : ∀ᶠ x in 𝓝 (t, p), f (x, ψ x) = f u := hf.eventually_apply_implicitFunction hpn hLi
  have hψC : ContDiffAt ℝ 1 ψ (t, p) := hf.contDiffAt_implicitFunction hpn hLi
  have hfu : f u = 0 := heq
  have hcont : ContinuousAt (fun x : ℝ × ℝ => (x.1, ψ x)) (t, p) :=
    continuous_fst.continuousAt.prodMk hψC.continuousAt
  have hmem : D ∈ 𝓝 ((t, p).1, ψ (t, p)) := by
    rw [hψ0]
    exact hD.mem_nhds hx
  refine ⟨{ volume := ψ
            differentiable := (hψC.eventually (by simp)).mono fun x hx =>
              hx.differentiableAt (by norm_num)
            in_domain := hcont.preimage_mem_nhds hmem
            equilibrium := hψeq.mono fun x hx => by
              rw [hfu] at hx
              exact hx
            stable := by
              change 0 < FVV F (t, ψ (t, p))
              rw [hψ0]
              exact hs }, hψ0⟩

end OMAI.PhyslibBridge.Response
