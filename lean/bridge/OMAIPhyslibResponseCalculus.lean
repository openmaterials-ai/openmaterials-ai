module

public import Mathlib.Analysis.Calculus.FDeriv.Symmetric
public import Mathlib.Analysis.Calculus.ContDiff.RCLike
public import Mathlib.Analysis.Calculus.ImplicitFunction.Bivariate
public import Mathlib.Analysis.Calculus.Deriv.Prod
public import Mathlib.Tactic

/-!
# Local scalar response calculus

This module proves identities for a twice differentiable real potential. It does
not identify that potential with a physical model. The harmonic volume module
supplies that separate identification. Pressure is minus the volume derivative;
all equilibrium equations below hold in a neighborhood, not merely at one point.
-/

@[expose] public section

noncomputable section
open Filter
open scoped Topology

namespace OMAI.PhyslibBridge.Response

abbrev Surface := ℝ × ℝ → ℝ

def FT (F : Surface) (x : ℝ × ℝ) : ℝ := fderiv ℝ F x (1, 0)
def FV (F : Surface) (x : ℝ × ℝ) : ℝ := fderiv ℝ F x (0, 1)
def FTT (F : Surface) (x : ℝ × ℝ) : ℝ :=
  fderiv ℝ (fderiv ℝ F) x (1, 0) (1, 0)
def FVV (F : Surface) (x : ℝ × ℝ) : ℝ :=
  fderiv ℝ (fderiv ℝ F) x (0, 1) (0, 1)
def mixedTV (F : Surface) (x : ℝ × ℝ) : ℝ :=
  fderiv ℝ (fderiv ℝ F) x (1, 0) (0, 1)

def internalEnergy (F : Surface) (x : ℝ × ℝ) : ℝ := F x - x.1 * FT F x
def cv (F : Surface) (x : ℝ × ℝ) : ℝ := -x.1 * FTT F x
def bulk (F : Surface) (x : ℝ × ℝ) : ℝ := x.2 * FVV F x
def expansion (V : ℝ → ℝ) (t : ℝ) : ℝ := deriv V t / V t
/-- An enthalpy derivative, not a definition by the Cp−Cv identity. -/
def cp (F : Surface) (p : ℝ) (V : ℝ → ℝ) (t : ℝ) : ℝ :=
  deriv (fun s => internalEnergy F (s, V s) + p * V s) t

/-- Local equilibrium data with an independently differentiable volume path. -/
structure StableBranchAt (F : Surface) (D : Set (ℝ × ℝ)) (p t₀ : ℝ) where
  volume : ℝ → ℝ
  slope : ℝ
  volume_deriv : HasDerivAt volume slope t₀
  in_domain : (t₀, volume t₀) ∈ D
  eventually_in_domain : ∀ᶠ t in 𝓝 t₀, (t, volume t) ∈ D
  equilibrium : ∀ᶠ t in 𝓝 t₀, FV F (t, volume t) + p = 0
  equilibrium_at : FV F (t₀, volume t₀) + p = 0
  stable : 0 < FVV F (t₀, volume t₀)

theorem linear_one_pair (L : (ℝ × ℝ) →L[ℝ] ℝ) (a : ℝ) :
    L (1, a) = L (1, 0) + a * L (0, 1) := by
  have h : (1, a) = (1, 0) + a • ((0, 1) : ℝ × ℝ) := by ext <;> simp
  rw [h, map_add, map_smul]
  rfl

theorem hessian_one_pair (H : (ℝ × ℝ) →L[ℝ] (ℝ × ℝ) →L[ℝ] ℝ)
    (a : ℝ) (w : ℝ × ℝ) :
    H (1, a) w = H (1, 0) w + a * H (0, 1) w := by
  have h : (1, a) = (1, 0) + a • ((0, 1) : ℝ × ℝ) := by ext <;> simp
  rw [h, map_add, map_smul]
  rfl

/-- Derivative of a fixed coordinate evaluation of the gradient. -/
theorem partial_hasFDerivAt {F : Surface} {x : ℝ × ℝ}
    (hF : ContDiffAt ℝ 2 F x) (w : ℝ × ℝ) :
    HasFDerivAt (fun y => fderiv ℝ F y w)
      ((ContinuousLinearMap.apply ℝ ℝ w).comp (fderiv ℝ (fderiv ℝ F) x)) x := by
  exact (ContinuousLinearMap.apply ℝ ℝ w).hasFDerivAt.comp x
    ((hF.fderiv_right (m := 1) (by norm_num)).differentiableAt one_ne_zero).hasFDerivAt

theorem surface_along_hasDerivAt {F : Surface} {V : ℝ → ℝ} {t a : ℝ}
    (hF : ContDiffAt ℝ 2 F (t, V t)) (hV : HasDerivAt V a t) :
    HasDerivAt (fun s => F (s, V s)) (FT F (t, V t) + a * FV F (t, V t)) t := by
  have h := (hF.differentiableAt (by norm_num)).hasFDerivAt.comp_hasDerivAt t
    ((hasDerivAt_id t).prodMk hV)
  change HasDerivAt (fun s => F (s, V s)) (fderiv ℝ F (t, V t) (1, a)) t at h
  rw [linear_one_pair] at h
  exact h

theorem partial_along_hasDerivAt {F : Surface} {V : ℝ → ℝ} {t a : ℝ}
    (hF : ContDiffAt ℝ 2 F (t, V t)) (hV : HasDerivAt V a t) (w : ℝ × ℝ) :
    HasDerivAt (fun s => fderiv ℝ F (s, V s) w)
      (fderiv ℝ (fderiv ℝ F) (t, V t) (1, 0) w +
        a * fderiv ℝ (fderiv ℝ F) (t, V t) (0, 1) w) t := by
  have h := (partial_hasFDerivAt hF w).comp_hasDerivAt t ((hasDerivAt_id t).prodMk hV)
  change HasDerivAt (fun s => fderiv ℝ F (s, V s) w)
    (fderiv ℝ (fderiv ℝ F) (t, V t) (1, a) w) t at h
  rw [hessian_one_pair] at h
  exact h

/-- Mixed partial symmetry is derived from C², never a model-data assumption. -/
theorem mixed_symmetric {F : Surface} {x : ℝ × ℝ} (hF : ContDiffAt ℝ 2 F x) :
    fderiv ℝ (fderiv ℝ F) x (0, 1) (1, 0) = mixedTV F x := by
  exact (hF.isSymmSndFDerivAt (by simp)).eq (0, 1) (1, 0)

/-- Differentiating the neighborhood equilibrium equation determines the slope. -/
theorem StableBranchAt.equilibrium_derivative {F : Surface} {D : Set (ℝ × ℝ)}
    {p t : ℝ} (B : StableBranchAt F D p t) (hF : ContDiffAt ℝ 2 F (t, B.volume t)) :
    mixedTV F (t, B.volume t) + B.slope * FVV F (t, B.volume t) = 0 := by
  have hd : HasDerivAt (fun s => FV F (s, B.volume s) + p)
      (mixedTV F (t, B.volume t) + B.slope * FVV F (t, B.volume t)) t :=
    (partial_along_hasDerivAt hF B.volume_deriv (0, 1)).add_const p
  have hz : HasDerivAt (fun _ : ℝ => (0 : ℝ))
      (mixedTV F (t, B.volume t) + B.slope * FVV F (t, B.volume t)) t :=
    hd.congr_of_eventuallyEq (by
      filter_upwards [B.equilibrium] with s hs
      exact hs.symm)
  exact hz.unique (hasDerivAt_const t 0)

/-- The enthalpy derivative before substituting the equilibrium slope relation. -/
theorem StableBranchAt.cp_eq {F : Surface} {D : Set (ℝ × ℝ)} {p t : ℝ}
    (B : StableBranchAt F D p t) (hF : ContDiffAt ℝ 2 F (t, B.volume t)) :
    cp F p B.volume t = cv F (t, B.volume t) -
      t * B.slope * mixedTV F (t, B.volume t) := by
  have hFT : HasDerivAt (fun s => FT F (s, B.volume s))
      (FTT F (t, B.volume t) + B.slope * mixedTV F (t, B.volume t)) t := by
    simpa only [FT, FTT, mixed_symmetric hF] using
      partial_along_hasDerivAt hF B.volume_deriv (1, 0)
  have hd := ((surface_along_hasDerivAt hF B.volume_deriv).fun_sub
    ((hasDerivAt_id t).mul hFT)).fun_add (B.volume_deriv.const_mul p)
  simp only [Pi.mul_apply, id_eq] at hd
  have heq := B.equilibrium_at
  have hv : FV F (t, B.volume t) = -p := by linarith
  change deriv (fun s => F (s, B.volume s) - s * FT F (s, B.volume s) +
    p * B.volume s) t = _
  rw [hd.deriv]
  simp only [cv, hv, one_mul]
  ring

/-- Local constant-pressure response identity for a generic smooth potential. -/
theorem cp_sub_cv (F : Surface) (D : Set (ℝ × ℝ)) (p t : ℝ)
    (hD : IsOpen D) (hF : ContDiffOn ℝ 2 F D)
    (hpos : ∀ x ∈ D, 0 < x.1 ∧ 0 < x.2) (B : StableBranchAt F D p t) :
    cp F p B.volume t - cv F (t, B.volume t) =
      t * B.volume t * (expansion B.volume t)^2 * bulk F (t, B.volume t) := by
  have hFx := hF.contDiffAt (hD.mem_nhds B.in_domain)
  have hEq := B.equilibrium_derivative hFx
  have hMix : mixedTV F (t, B.volume t) = -B.slope * FVV F (t, B.volume t) := by
    linarith
  have hV : B.volume t ≠ 0 := ne_of_gt (hpos _ B.in_domain).2
  rw [B.cp_eq hFx, hMix]
  simp only [expansion, B.volume_deriv.deriv, bulk]
  field_simp [hV]
  ring

/-- Stability and positive temperature make the response correction nonnegative. -/
theorem cp_ge_cv (F : Surface) (D : Set (ℝ × ℝ)) (p t : ℝ)
    (hD : IsOpen D) (hF : ContDiffOn ℝ 2 F D)
    (hpos : ∀ x ∈ D, 0 < x.1 ∧ 0 < x.2) (B : StableBranchAt F D p t) :
    cv F (t, B.volume t) ≤ cp F p B.volume t := by
  obtain ⟨hT, hV⟩ := hpos _ B.in_domain
  have hK : 0 < bulk F (t, B.volume t) := mul_pos hV B.stable
  have hgap : 0 ≤ cp F p B.volume t - cv F (t, B.volume t) := by
    rw [cp_sub_cv F D p t hD hF hpos B]
    positivity
  linarith

/-- The temperature coordinate derivative is the ordinary slice derivative. -/
theorem FT_eq_deriv {F : Surface} {t v : ℝ} (hF : ContDiffAt ℝ 2 F (t, v)) :
    FT F (t, v) = deriv (fun s => F (s, v)) t := by
  have h := surface_along_hasDerivAt hF (hasDerivAt_const t v)
  simpa only [zero_mul, add_zero] using h.deriv.symm

/-- A fixed-temperature volume slice has the volume coordinate derivative. -/
theorem volume_hasDerivAt {F : Surface} {t v : ℝ} (hF : ContDiffAt ℝ 2 F (t, v)) :
    HasDerivAt (fun w => F (t, w)) (FV F (t, v)) v :=
  (hF.differentiableAt (by norm_num)).hasFDerivAt.comp_hasDerivAt v
    ((hasDerivAt_const v t).prodMk (hasDerivAt_id v))

/-- The volume coordinate derivative is the ordinary slice derivative. -/
theorem FV_eq_deriv {F : Surface} {t v : ℝ} (hF : ContDiffAt ℝ 2 F (t, v)) :
    FV F (t, v) = deriv (fun w => F (t, w)) v := by
  have h := (hF.differentiableAt (by norm_num)).hasFDerivAt.comp_hasDerivAt v
    ((hasDerivAt_const v t).prodMk (hasDerivAt_id v))
  exact h.deriv.symm

/-- Fixed-volume derivative of potential-derived internal energy. -/
theorem internalEnergy_temperature_hasDerivAt {F : Surface} {t v : ℝ}
    (hF : ContDiffAt ℝ 2 F (t, v)) :
    HasDerivAt (fun s => internalEnergy F (s, v)) (cv F (t, v)) t := by
  have hf : HasDerivAt (fun s => F (s, v)) (FT F (t, v)) t := by
    simpa only [zero_mul, add_zero] using
      surface_along_hasDerivAt hF (hasDerivAt_const t v)
  have hft : HasDerivAt (fun s => FT F (s, v)) (FTT F (t, v)) t := by
    simpa only [FT, FTT, zero_mul, add_zero] using
      partial_along_hasDerivAt hF (hasDerivAt_const t v) (1, 0)
  have hd := hf.fun_sub ((hasDerivAt_id t).mul hft)
  simp only [Pi.mul_apply, id_eq, one_mul] at hd
  convert hd using 1
  · rfl
  · unfold cv
    ring

/-- A coordinate partial is C¹ on an open C² domain. -/
theorem partial_contDiffOn {F : Surface} {D : Set (ℝ × ℝ)}
    (hF : ContDiffOn ℝ 2 F D) (hD : IsOpen D) (w : ℝ × ℝ) :
    ContDiffOn ℝ 1 (fun x => fderiv ℝ F x w) D :=
  (ContinuousLinearMap.apply ℝ ℝ w).contDiff.comp_contDiffOn
    (hF.fderiv_of_isOpen hD (m := 1) (by norm_num))

/-- Ordinary volume derivative of a coordinate partial. -/
theorem partial_volume_hasDerivAt {F : Surface} {t v : ℝ}
    (hF : ContDiffAt ℝ 2 F (t, v)) (w : ℝ × ℝ) :
    HasDerivAt (fun u => fderiv ℝ F (t, u) w)
      (fderiv ℝ (fderiv ℝ F) (t, v) (0, 1) w) v := by
  exact (partial_hasFDerivAt hF w).comp_hasDerivAt v
    ((hasDerivAt_const v t).prodMk (hasDerivAt_id v))

theorem FVV_eq_deriv_FV {F : Surface} {t v : ℝ}
    (hF : ContDiffAt ℝ 2 F (t, v)) :
    FVV F (t, v) = deriv (fun u => FV F (t, u)) v :=
  (partial_volume_hasDerivAt hF (0, 1)).deriv.symm

theorem mixedTV_eq_deriv_FV {F : Surface} {t v : ℝ}
    (hF : ContDiffAt ℝ 2 F (t, v)) :
    mixedTV F (t, v) = deriv (fun s => FV F (s, v)) t := by
  have h := partial_along_hasDerivAt hF (hasDerivAt_const t v) (0, 1)
  simpa only [zero_mul, add_zero, mixedTV, FV] using h.deriv.symm

/-- Relate the Fréchet Hessian coordinate to the iterated ordinary volume derivative. -/
theorem FVV_eq_deriv_deriv_volume {F : Surface} {D : Set (ℝ × ℝ)}
    (hD : IsOpen D) (hF : ContDiffOn ℝ 2 F D) {t v : ℝ} (hx : (t, v) ∈ D) :
    FVV F (t, v) = deriv (deriv (fun u => F (t, u))) v := by
  have heq : (fun u => FV F (t, u)) =ᶠ[𝓝 v]
      (fun u => deriv (fun z => F (t, z)) u) := by
    filter_upwards [(hD.preimage (continuous_const.prodMk continuous_id)).mem_nhds hx] with u hu
    exact FV_eq_deriv (hF.contDiffAt (hD.mem_nhds hu))
  exact (FVV_eq_deriv_FV (hF.contDiffAt (hD.mem_nhds hx))).trans heq.deriv_eq

/-- The real scalar implicit-function theorem with its actual first derivative. -/
theorem exists_scalar_implicit_branch
    (g : ℝ × ℝ → ℝ) (t v : ℝ)
    (hC : ContDiffAt ℝ 1 g (t, v)) (h0 : g (t, v) = 0)
    (hv : fderiv ℝ g (t, v) (0, 1) ≠ 0) :
    ∃ u : ℝ → ℝ, u t = v ∧
      HasDerivAt u (-(fderiv ℝ g (t, v) (1, 0)) /
        (fderiv ℝ g (t, v) (0, 1))) t ∧
      ContinuousAt u t ∧ (∀ᶠ s in 𝓝 t, g (s, u s) = 0) := by
  let A := fderiv ℝ g (t, v)
  let B : ℝ →L[ℝ] ℝ := A ∘L ContinuousLinearMap.inr ℝ ℝ ℝ
  have hB (x : ℝ) : B x = x * B 1 := by
    simpa only [smul_eq_mul, mul_one] using B.map_smul x (1 : ℝ)
  have hB1 : B 1 ≠ 0 := by simpa [B, A] using hv
  have hBi : B.IsInvertible := by
    apply ContinuousLinearMap.IsInvertible.of_inverse
      (g := (B 1)⁻¹ • ContinuousLinearMap.id ℝ ℝ)
    · apply ContinuousLinearMap.ext
      intro x
      simp only [ContinuousLinearMap.comp_apply, smul_apply,
        ContinuousLinearMap.id_apply, smul_eq_mul]
      rw [hB]
      field_simp
    · apply ContinuousLinearMap.ext
      intro x
      simp only [ContinuousLinearMap.comp_apply, smul_apply,
        ContinuousLinearMap.id_apply, smul_eq_mul]
      rw [hB x]
      field_simp
  have hBinv (x : ℝ) : B.inverse x = x / B 1 := by
    apply hBi.inverse_apply_eq.mpr
    rw [hB]
    field_simp
  have hg : HasStrictFDerivAt g A (t, v) :=
    hC.hasStrictFDerivAt (by norm_num)
  let u := hg.implicitFunctionOfProdDomain hBi
  have hut : u t = v := by
    exact (hg.eventually_apply_eq_iff_implicitFunctionOfProdDomain hBi).self_of_nhds.mp rfl
  have hu : HasDerivAt u (-(A (1, 0)) / A (0, 1)) t := by
    have hu' := (hg.hasStrictFDerivAt_implicitFunctionOfProdDomain hBi).hasFDerivAt.hasDerivAt
    change HasDerivAt u ((-B.inverse ∘L (A ∘L ContinuousLinearMap.inl ℝ ℝ ℝ)) 1) t at hu'
    simpa [hBinv, B, neg_div] using hu'
  refine ⟨u, hut, hu, hu.continuousAt, ?_⟩
  simpa only [h0] using hg.eventually_apply_implicitFunctionOfProdDomain hBi


/-- A stable stationary state determines a local constant-pressure branch.
The branch and its slope are constructed by the implicit-function theorem. -/
theorem exists_stableBranchAt (F : Surface) (D : Set (ℝ × ℝ)) (p t v : ℝ)
    (hD : IsOpen D) (hF : ContDiffOn ℝ 2 F D) (hx : (t, v) ∈ D)
    (heq : FV F (t, v) + p = 0) (hs : 0 < FVV F (t, v)) :
    ∃ B : StableBranchAt F D p t,
      B.volume t = v ∧ B.slope = -mixedTV F (t, v) / FVV F (t, v) := by
  let g : Surface := fun x => FV F x + p
  have hFx := hF.contDiffAt (hD.mem_nhds hx)
  have hC : ContDiffAt ℝ 1 g (t, v) :=
    ((partial_contDiffOn hF hD (0, 1)).contDiffAt (hD.mem_nhds hx)).add contDiffAt_const
  have hdg : HasFDerivAt g
      ((ContinuousLinearMap.apply ℝ ℝ (0, 1)).comp (fderiv ℝ (fderiv ℝ F) (t, v))) (t, v) :=
    (partial_hasFDerivAt hFx (0, 1)).add_const p
  have hdv : fderiv ℝ g (t, v) (0, 1) = FVV F (t, v) := by rw [hdg.fderiv]; rfl
  have hdt : fderiv ℝ g (t, v) (1, 0) = mixedTV F (t, v) := by rw [hdg.fderiv]; rfl
  obtain ⟨u, hut, hu, huc, hueq⟩ := exists_scalar_implicit_branch g t v hC heq
    (by rw [hdv]; exact hs.ne')
  rw [hdt, hdv] at hu
  have hxin : (t, u t) ∈ D := by simpa only [hut] using hx
  let B : StableBranchAt F D p t :=
    { volume := u
      slope := -mixedTV F (t, v) / FVV F (t, v)
      volume_deriv := hu
      in_domain := hxin
      eventually_in_domain := (continuousAt_id.prodMk huc).preimage_mem_nhds (hD.mem_nhds hxin)
      equilibrium := hueq
      equilibrium_at := by simpa only [hut] using heq
      stable := by simpa only [hut] using hs }
  exact ⟨B, hut, rfl⟩

end OMAI.PhyslibBridge.Response
