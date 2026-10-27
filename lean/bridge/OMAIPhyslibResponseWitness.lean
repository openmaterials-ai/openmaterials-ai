module

public import OMAIPhyslibHarmonicVolume

/-!
# Nontrivial local response models

The witness uses three distinct positive oscillator frequencies, a genuine
static-energy factor, and an implicitly constructed equilibrium branch. It is
an exact toy model, not a fitted material or numerical minimizer validation.
-/

@[expose] public section

noncomputable section
open Constants Temperature QuantumMechanics.OneDimension Filter
open scoped BigOperators Topology Classical

namespace OMAI.PhyslibBridge.Response

/-- A three-mode primitive cell, with an arbitrary fixed positive molar scale. -/
abbrev witnessReference (A : ℝ) (hA : 0 < A) : HarmonicModeGrid where
  qCount := 1
  qCount_pos := by norm_num
  atomCount := 1
  atomCount_pos := by norm_num
  avogadro := A
  avogadro_pos := hA
  oscillator := fun _ b =>
    { m := 1
      ω := (b.val : ℝ) + 1
      hω := by positivity
      hm := by norm_num }

def exponentialOmega (b : Fin 3) (v : ℝ) : ℝ :=
  ((b.val : ℝ) + 1) * Real.exp (1 - v)

theorem exponentialOmega_pos (b : Fin 3) (v : ℝ) : 0 < exponentialOmega b v := by
  unfold exponentialOmega
  positivity

theorem exponentialOmega_hasDerivAt (b : Fin 3) (v : ℝ) :
    HasDerivAt (exponentialOmega b) (-exponentialOmega b v) v := by
  have h := (((hasDerivAt_const v (1 : ℝ)).sub (hasDerivAt_id v)).exp).const_mul
    ((b.val : ℝ) + 1)
  convert h using 1
  · rfl
  · simp [exponentialOmega]

abbrev exponentialFamily (A : ℝ) (hA : 0 < A) (E : ℝ → ℝ) (hE : ContDiff ℝ 2 E) :
    HarmonicVolumeModel where
  reference := witnessReference A hA
  J := Set.Ioi 0
  open_J := isOpen_Ioi
  positive_J := fun _ h => h
  omega := fun _ b => exponentialOmega b
  omega_pos := fun _ b v _ => exponentialOmega_pos b v
  omega_C2 := fun _ b => (show ContDiff ℝ 2 (exponentialOmega b) from by
    unfold exponentialOmega
    fun_prop).contDiffOn
  staticEnergy := E
  staticEnergy_C2 := hE.contDiffOn

/-- Unit-scale, zero-static auxiliary family defining the cell free energy. -/
abbrev baseModel : HarmonicVolumeModel := exponentialFamily 1 (by norm_num) (fun _ => 0) contDiff_const

def baseF : Surface := baseModel.freeEnergy
def baseU : Surface := baseModel.internalEnergy
def baseCv : Surface := baseModel.cv

theorem base_domain {t v : ℝ} (ht : 0 < t) (hv : 0 < v) : (t, v) ∈ baseModel.domain := by
  simpa [baseModel, exponentialFamily, witnessReference, HarmonicVolumeModel.domain] using And.intro ht hv

theorem baseF_eq_sum (t v : ℝ) :
    baseF (t, v) = ∑ b : Fin 3, harmonicFreeEnergy ℏ kB (exponentialOmega b v) t := by
  simp [baseF, baseModel, exponentialFamily, witnessReference,
    HarmonicVolumeModel.freeEnergy, uniformMolarContraction]

theorem baseU_eq_sum (t v : ℝ) :
    baseU (t, v) = ∑ b : Fin 3, harmonicInternalEnergy ℏ kB (exponentialOmega b v) t := by
  simp [baseU, baseModel, exponentialFamily, witnessReference,
    HarmonicVolumeModel.internalEnergy, uniformMolarContraction]

theorem baseF_contDiffAt {t v : ℝ} (ht : 0 < t) (hv : 0 < v) :
    ContDiffAt ℝ 2 baseF (t, v) := baseModel.freeEnergy_contDiffAt (base_domain ht hv)

theorem base_volume_hasDerivAt {t v : ℝ} (ht : 0 < t) (_hv : 0 < v) :
    HasDerivAt (fun w => baseF (t, w)) (-baseU (t, v)) v := by
  have hi (b : Fin 3) : HasDerivAt (fun w => harmonicFreeEnergy ℏ kB (exponentialOmega b w) t)
      (-harmonicInternalEnergy ℏ kB (exponentialOmega b v) t) v := by
    have h := (harmonicFreeEnergy_frequency_hasDerivAt ℏ_pos kB_pos
      (exponentialOmega_pos b v) ht).comp v (exponentialOmega_hasDerivAt b v)
    convert h using 1
    · rfl
    · field_simp [(exponentialOmega_pos b v).ne']
  have hs := HasDerivAt.fun_sum (u := Finset.univ) (fun b _ => hi b)
  simpa only [baseF_eq_sum, baseU_eq_sum, Finset.sum_neg_distrib] using hs

theorem base_FV {t v : ℝ} (ht : 0 < t) (hv : 0 < v) :
    FV baseF (t, v) = -baseU (t, v) := by
  rw [FV_eq_deriv (baseF_contDiffAt ht hv)]
  exact (base_volume_hasDerivAt ht hv).deriv

theorem base_mixedTV : mixedTV baseF (1, 1) = -baseCv (1, 1) := by
  rw [mixedTV_eq_deriv_FV (baseF_contDiffAt (by norm_num) (by norm_num))]
  have heq : (fun t => FV baseF (t, 1)) =ᶠ[𝓝 (1 : ℝ)] (fun t => -baseU (t, 1)) := by
    filter_upwards [isOpen_Ioi.mem_nhds (by norm_num : (1 : ℝ) ∈ Set.Ioi 0)] with t ht
    exact base_FV ht (by norm_num)
  rw [heq.deriv_eq]
  exact (baseModel.internalEnergy_temperature_hasDerivAt
    (base_domain (by norm_num) (by norm_num))).neg.deriv

theorem baseCv_pos : 0 < baseCv (1, 1) :=
  baseModel.cv_pos (base_domain (by norm_num) (by norm_num))

def referenceSlope : ℝ := FV baseF (1, 1)
def referenceCurvature : ℝ := FVV baseF (1, 1)
def staticStiffness : ℝ := 1 + |referenceCurvature|
def witnessStatic (v : ℝ) : ℝ :=
  -referenceSlope * (v - 1) + (staticStiffness / 2) * (v - 1)^2

theorem witnessStatic_contDiff : ContDiff ℝ 2 witnessStatic := by
  unfold witnessStatic
  fun_prop

abbrev nonzeroModel (A : ℝ) (hA : 0 < A) : HarmonicVolumeModel :=
  exponentialFamily A hA witnessStatic witnessStatic_contDiff

theorem exponentialFamily_freeEnergy (A : ℝ) (hA : 0 < A) (E : ℝ → ℝ)
    (hE : ContDiff ℝ 2 E) (t V : ℝ) :
    (exponentialFamily A hA E hE).freeEnergy (t, V) =
      molarLift A (fun s v => E v + baseF (s, v)) t V := by
  simp [HarmonicVolumeModel.freeEnergy, uniformMolarContraction, exponentialFamily,
    witnessReference, baseF_eq_sum, molarLift]
  ring

theorem nonzero_domain {A t v : ℝ} (hA : 0 < A) (ht : 0 < t) (hv : 0 < v) :
    (t, A * v) ∈ (nonzeroModel A hA).domain := by
  simpa [nonzeroModel, exponentialFamily, witnessReference, HarmonicVolumeModel.domain,
    hA.ne'] using And.intro ht hv

theorem witnessStatic_hasDerivAt (v : ℝ) :
    HasDerivAt witnessStatic (-referenceSlope + staticStiffness * (v - 1)) v := by
  have h := (((hasDerivAt_id v).sub_const 1).const_mul (-referenceSlope)).fun_add
    ((((hasDerivAt_id v).sub_const 1).pow 2).const_mul (staticStiffness / 2))
  convert h using 1
  · ext w
    rfl
  · dsimp
    ring

def cellWithStatic (t v : ℝ) : ℝ := witnessStatic v + baseF (t, v)

theorem cellWithStatic_hasDerivAt {t v : ℝ} (ht : 0 < t) (hv : 0 < v) :
    HasDerivAt (cellWithStatic t)
      (-referenceSlope + staticStiffness * (v - 1) + FV baseF (t, v)) v :=
  (witnessStatic_hasDerivAt v).fun_add (volume_hasDerivAt (baseF_contDiffAt ht hv))

theorem cellWithStatic_contDiffAt {t v : ℝ} (ht : 0 < t) (hv : 0 < v) :
    ContDiffAt ℝ 2 (cellWithStatic t) v :=
  witnessStatic_contDiff.contDiffAt.add ((baseF_contDiffAt ht hv).comp v (by fun_prop))

theorem nonzero_FV_scaled {A t v : ℝ} (hA : 0 < A) (ht : 0 < t) (hv : 0 < v) :
    FV (nonzeroModel A hA).freeEnergy (t, A * v) =
      -referenceSlope + staticStiffness * (v - 1) + FV baseF (t, v) := by
  have hfun : (fun W => (nonzeroModel A hA).freeEnergy (t, W)) = molarLift A cellWithStatic t := by
    funext W
    exact exponentialFamily_freeEnergy A hA witnessStatic witnessStatic_contDiff t W
  rw [FV_eq_deriv ((nonzeroModel A hA).freeEnergy_contDiffAt (nonzero_domain hA ht hv)), hfun]
  exact (molarLift_volume_hasDerivAt hA (cellWithStatic_hasDerivAt ht hv)).deriv

theorem nonzero_FV_reference {A : ℝ} (hA : 0 < A) :
    FV (nonzeroModel A hA).freeEnergy (1, A) = 0 := by
  simpa [referenceSlope] using nonzero_FV_scaled hA (by norm_num : (0 : ℝ) < 1) (by norm_num : (0 : ℝ) < 1)

theorem cellWithStatic_second :
    deriv (deriv (cellWithStatic 1)) 1 = staticStiffness + referenceCurvature := by
  have heq : deriv (cellWithStatic 1) =ᶠ[𝓝 (1 : ℝ)]
      (fun v => -referenceSlope + staticStiffness * (v - 1) + FV baseF (1, v)) := by
    filter_upwards [isOpen_Ioi.mem_nhds (by norm_num : (1 : ℝ) ∈ Set.Ioi 0)] with v hv
    exact (cellWithStatic_hasDerivAt (by norm_num) hv).deriv
  rw [heq.deriv_eq]
  have hl : HasDerivAt (fun v => -referenceSlope + staticStiffness * (v - 1)) staticStiffness 1 := by
    simpa only [mul_one, id_eq] using (((hasDerivAt_id (1 : ℝ)).sub_const 1).const_mul staticStiffness).const_add (-referenceSlope)
  exact (hl.fun_add (partial_volume_hasDerivAt (baseF_contDiffAt (by norm_num) (by norm_num)) (0, 1))).deriv

theorem nonzero_FVV_reference {A : ℝ} (hA : 0 < A) :
    FVV (nonzeroModel A hA).freeEnergy (1, A) =
      (staticStiffness + referenceCurvature) / A := by
  have hx : (1, A) ∈ (nonzeroModel A hA).domain := by
    simpa only [mul_one] using nonzero_domain hA (by norm_num : (0 : ℝ) < 1) (by norm_num : (0 : ℝ) < 1)
  rw [FVV_eq_deriv_deriv_volume (nonzeroModel A hA).domain_isOpen
    (nonzeroModel A hA).freeEnergy_contDiffOn hx]
  have hfun : (fun W => (nonzeroModel A hA).freeEnergy (1, W)) = molarLift A cellWithStatic 1 := by
    funext W
    exact exponentialFamily_freeEnergy A hA witnessStatic witnessStatic_contDiff 1 W
  rw [hfun]
  have h := molarLift_volume_second_deriv (A := A) (t := 1) (v := 1) (f := cellWithStatic)
    hA (cellWithStatic_contDiffAt (by norm_num) (by norm_num))
  simpa only [mul_one, cellWithStatic_second] using h

theorem nonzero_mixed_reference {A : ℝ} (hA : 0 < A) :
    mixedTV (nonzeroModel A hA).freeEnergy (1, A) = -baseCv (1, 1) := by
  have hx : (1, A) ∈ (nonzeroModel A hA).domain := by
    simpa only [mul_one] using nonzero_domain hA (by norm_num : (0 : ℝ) < 1) (by norm_num : (0 : ℝ) < 1)
  rw [mixedTV_eq_deriv_FV ((nonzeroModel A hA).freeEnergy_contDiffAt hx)]
  have heq : (fun t => FV (nonzeroModel A hA).freeEnergy (t, A)) =ᶠ[𝓝 (1 : ℝ)]
      (fun t => -referenceSlope + FV baseF (t, 1)) := by
    filter_upwards [isOpen_Ioi.mem_nhds (by norm_num : (1 : ℝ) ∈ Set.Ioi 0)] with t ht
    simpa only [mul_one, sub_self, mul_zero, add_zero] using nonzero_FV_scaled (v := 1) hA ht (by norm_num)
  rw [heq.deriv_eq]
  have hd : HasDerivAt (fun t => -referenceSlope + FV baseF (t, 1)) (mixedTV baseF (1, 1)) 1 := by
    simpa only [zero_mul, add_zero, FV, mixedTV] using
      (partial_along_hasDerivAt (baseF_contDiffAt (by norm_num) (by norm_num))
        (hasDerivAt_const (1 : ℝ) (1 : ℝ)) (0, 1)).const_add (-referenceSlope)
  rw [hd.deriv, base_mixedTV]

theorem reference_totalCurvature_pos : 0 < staticStiffness + referenceCurvature := by
  have h := neg_le_abs referenceCurvature
  unfold staticStiffness
  linarith

theorem nonzero_curvature_pos {A : ℝ} (hA : 0 < A) :
    0 < FVV (nonzeroModel A hA).freeEnergy (1, A) := by
  rw [nonzero_FVV_reference hA]
  exact div_pos reference_totalCurvature_pos hA

/-- The selected actual family has a genuinely volume-sensitive heterogeneous spectrum. -/
theorem nonzeroModel_heterogeneous (A : ℝ) (hA : 0 < A) (v : ℝ) :
    ∃ q b₀ b₁, (nonzeroModel A hA).omega q b₀ v < (nonzeroModel A hA).omega q b₁ v := by
  refine ⟨⟨0, by simp⟩, ⟨0, by simp⟩, ⟨1, by simp⟩, ?_⟩
  have h := Real.exp_pos (1 - v)
  norm_num [nonzeroModel, exponentialFamily, exponentialOmega]
  linarith

theorem exponentialOmega_deriv_neg (b : Fin 3) (v : ℝ) : deriv (exponentialOmega b) v < 0 := by
  rw [(exponentialOmega_hasDerivAt b v).deriv]
  exact neg_neg_of_pos (exponentialOmega_pos b v)

/-- An actual heterogeneous static-plus-harmonic family has a stable local
constant-pressure branch with strictly positive expansion and Cp greater than Cv. -/
theorem nonzero_expansion_witness (A : ℝ) (hA : 0 < A) :
    ∃ B : StableBranchAt (nonzeroModel A hA).freeEnergy (nonzeroModel A hA).domain 0 1,
      B.volume 1 = A ∧ 0 < expansion B.volume 1 ∧
        (nonzeroModel A hA).cv (1, A) < (nonzeroModel A hA).actualCp 0 B.volume 1 := by
  let M := nonzeroModel A hA
  have hx : (1, A) ∈ M.domain := by
    simpa only [mul_one] using nonzero_domain hA (by norm_num : (0 : ℝ) < 1) (by norm_num : (0 : ℝ) < 1)
  obtain ⟨B, hB, hs⟩ := exists_stableBranchAt M.freeEnergy M.domain 0 1 A
    M.domain_isOpen M.freeEnergy_contDiffOn hx
    (by simpa only [add_zero] using nonzero_FV_reference hA) (nonzero_curvature_pos hA)
  have hslope : 0 < B.slope := by
    rw [hs, nonzero_mixed_reference hA, neg_neg]
    exact div_pos baseCv_pos (nonzero_curvature_pos hA)
  have ha : 0 < expansion B.volume 1 := by
    unfold expansion
    rw [B.volume_deriv.deriv, hB]
    exact div_pos hslope hA
  have hv : 0 < B.volume 1 := by simpa only [hB] using hA
  have hk : 0 < bulk M.freeEnergy (1, B.volume 1) := mul_pos hv B.stable
  have hgap : 0 < M.actualCp 0 B.volume 1 - M.cv (1, B.volume 1) := by
    rw [M.actualCp_sub_cv 0 1 B]
    positivity
  rw [hB] at hgap
  exact ⟨B, hB, ha, sub_pos.mp hgap⟩


/-- A constant-frequency control with a strictly convex static energy. -/
abbrev zeroModel (A : ℝ) (hA : 0 < A) : HarmonicVolumeModel where
  reference := witnessReference A hA
  J := Set.Ioi 0
  open_J := isOpen_Ioi
  positive_J := fun _ h => h
  omega := fun _ b _ => (b.val : ℝ) + 1
  omega_pos := fun _ _ _ _ => by positivity
  omega_C2 := fun _ _ => contDiff_const.contDiffOn
  staticEnergy := fun v => (v - 1)^2 / 2
  staticEnergy_C2 := (show ContDiff ℝ 2 (fun v : ℝ => (v - 1)^2 / 2) from by fun_prop).contDiffOn

def zeroThermalSum (t : ℝ) : ℝ :=
  ∑ b : Fin 3, harmonicFreeEnergy ℏ kB ((b.val : ℝ) + 1) t

theorem zero_freeEnergy (A : ℝ) (hA : 0 < A) (t V : ℝ) :
    (zeroModel A hA).freeEnergy (t, V) =
      A * ((V / A - 1)^2 / 2) + A * zeroThermalSum t := by
  simp [zeroModel, witnessReference, HarmonicVolumeModel.freeEnergy,
    uniformMolarContraction, zeroThermalSum]

theorem zero_domain {A t V : ℝ} (hA : 0 < A) (ht : 0 < t) (hV : 0 < V) :
    (t, V) ∈ (zeroModel A hA).domain := ⟨ht, div_pos hV hA⟩

theorem zero_FV (A : ℝ) (hA : 0 < A) {t V : ℝ} (ht : 0 < t) (hV : 0 < V) :
    FV (zeroModel A hA).freeEnergy (t, V) = V / A - 1 := by
  rw [FV_eq_deriv ((zeroModel A hA).freeEnergy_contDiffAt (zero_domain hA ht hV))]
  have hfun : (fun W => (zeroModel A hA).freeEnergy (t, W)) =
      (fun W => A * ((W / A - 1)^2 / 2) + A * zeroThermalSum t) := by
    funext W
    exact zero_freeEnergy A hA t W
  rw [hfun]
  have hd := ((((((hasDerivAt_id V).div_const A).sub_const 1).pow 2).div_const 2).const_mul A).add_const
    (A * zeroThermalSum t)
  have h : HasDerivAt (fun W => A * ((W / A - 1)^2 / 2) + A * zeroThermalSum t)
      (V / A - 1) V := by
    convert hd using 1
    · ext W
      rfl
    · dsimp
      field_simp [hA.ne']
  exact h.deriv

theorem zero_FVV_reference {A : ℝ} (hA : 0 < A) :
    FVV (zeroModel A hA).freeEnergy (1, A) = 1 / A := by
  rw [FVV_eq_deriv_FV ((zeroModel A hA).freeEnergy_contDiffAt (zero_domain hA (by norm_num) hA))]
  have heq : (fun V => FV (zeroModel A hA).freeEnergy (1, V)) =ᶠ[𝓝 A]
      (fun V => V / A - 1) := by
    filter_upwards [isOpen_Ioi.mem_nhds hA] with V hV
    exact zero_FV A hA (by norm_num) hV
  rw [heq.deriv_eq]
  exact (((hasDerivAt_id A).div_const A).sub_const 1).deriv

/-- A separate actual stable constant-frequency family has no expansion correction. -/
theorem zero_response_control (A : ℝ) (hA : 0 < A) :
    ∃ B : StableBranchAt (zeroModel A hA).freeEnergy (zeroModel A hA).domain 0 1,
      B.volume 1 = A ∧ expansion B.volume 1 = 0 ∧
        (zeroModel A hA).actualCp 0 B.volume 1 = (zeroModel A hA).cv (1, A) := by
  let M := zeroModel A hA
  let B : StableBranchAt M.freeEnergy M.domain 0 1 :=
    { volume := fun _ => A
      slope := 0
      volume_deriv := hasDerivAt_const 1 A
      in_domain := zero_domain hA (by norm_num) hA
      eventually_in_domain := by
        filter_upwards [isOpen_Ioi.mem_nhds (by norm_num : (1 : ℝ) ∈ Set.Ioi 0)] with t ht
        exact zero_domain hA ht hA
      equilibrium := by
        filter_upwards [isOpen_Ioi.mem_nhds (by norm_num : (1 : ℝ) ∈ Set.Ioi 0)] with t ht
        simpa [hA.ne'] using zero_FV A hA ht hA
      equilibrium_at := by simpa [hA.ne'] using zero_FV A hA (by norm_num : (0 : ℝ) < 1) hA
      stable := by rw [zero_FVV_reference hA]; exact div_pos zero_lt_one hA }
  have ha : expansion B.volume 1 = 0 := by
    unfold expansion
    rw [B.volume_deriv.deriv]
    change (0 : ℝ) / A = 0
    exact zero_div A
  have hgap := M.actualCp_sub_cv 0 1 B
  rw [ha] at hgap
  have heq : M.actualCp 0 B.volume 1 = M.cv (1, A) := by
    apply sub_eq_zero.mp
    simpa using hgap
  exact ⟨B, rfl, ha, heq⟩

end OMAI.PhyslibBridge.Response
