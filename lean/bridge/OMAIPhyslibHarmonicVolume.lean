module

public import OMAIPhyslibResponseCalculus
public import OMAIPhyslibStaticEnsemble
public import OMAIPhyslibResponseUnits

/-!
# A smooth volume family of actual static-plus-harmonic ensembles

The primitive inputs are positive C² frequency curves and a T-independent C²
static energy on an open positive primitive-cell volume domain. All molar
response coordinates use V = NA v. No frequency, static-energy, EOS or numerical
minimizer producer is identified by this construction.
-/

@[expose] public section

noncomputable section
open MeasureTheory Constants Temperature QuantumMechanics.OneDimension Filter
open scoped BigOperators Topology Classical

namespace OMAI.PhyslibBridge

/-- Supporting frequency derivative; it does not identify a mode-gamma producer. -/
theorem harmonicFreeEnergy_frequency_hasDerivAt
    {hbar kB omega t : ℝ}
    (hh : 0 < hbar) (hk : 0 < kB) (hw : 0 < omega) (ht : 0 < t) :
    HasDerivAt (fun w => harmonicFreeEnergy hbar kB w t)
      (harmonicInternalEnergy hbar kB omega t / omega) omega := by
  have ha : HasDerivAt (fun w => harmonicArgument hbar kB w t)
      (hbar / (kB * t)) omega := by
    simpa only [harmonicArgument, id_eq, mul_one] using ((hasDerivAt_id omega).const_mul hbar).div_const (kB * t)
  have hlog := (harmonic_log_argument_pos hh hk hw ht).ne'
  have hden := (harmonic_bose_denominator_pos hh hk hw ht).ne'
  have hd := (((hasDerivAt_id omega).const_mul hbar).div_const 2).fun_add
    ((((hasDerivAt_const omega (1 : ℝ)).sub ha.neg.exp).log hlog).const_mul (kB * t))
  convert hd using 1
  · ext w
    rfl
  · dsimp
    unfold harmonicInternalEnergy boseOccupation
    rw [Real.exp_neg]
    field_simp
    ring

theorem harmonicHeatCapacity_pos {hbar kB omega t : ℝ}
    (hh : 0 < hbar) (hk : 0 < kB) (hw : 0 < omega) (ht : 0 < t) :
    0 < harmonicHeatCapacity hbar kB omega t := by
  rw [harmonicHeatCapacity_eq_exp hh hk hw ht]
  have hd := harmonic_bose_denominator_pos hh hk hw ht
  positivity

structure HarmonicVolumeModel where
  reference : HarmonicModeGrid
  J : Set ℝ
  open_J : IsOpen J
  positive_J : J ⊆ Set.Ioi 0
  omega : Fin reference.qCount → Fin (3 * reference.atomCount) → ℝ → ℝ
  omega_pos : ∀ q b v, v ∈ J → 0 < omega q b v
  omega_C2 : ∀ q b, ContDiffOn ℝ 2 (omega q b) J
  staticEnergy : ℝ → ℝ
  staticEnergy_C2 : ContDiffOn ℝ 2 staticEnergy J

namespace HarmonicVolumeModel

def gridAt (M : HarmonicVolumeModel) (v : ℝ) (hv : v ∈ M.J) : HarmonicModeGrid :=
  { M.reference with oscillator := fun q b =>
      { M.reference.oscillator q b with
        ω := M.omega q b v
        hω := M.omega_pos q b v hv } }

def ensembleAt (M : HarmonicVolumeModel) (v : ℝ) (hv : v ∈ M.J) :=
  staticHarmonicGridEnsemble (M.gridAt v hv) (M.staticEnergy v)

def domain (M : HarmonicVolumeModel) : Set (ℝ × ℝ) :=
  {x | 0 < x.1 ∧ x.2 / M.reference.avogadro ∈ M.J}

def freeEnergy (M : HarmonicVolumeModel) (x : ℝ × ℝ) : ℝ :=
  M.reference.avogadro * M.staticEnergy (x.2 / M.reference.avogadro) +
    uniformMolarContraction M.reference fun q b =>
      harmonicFreeEnergy ℏ kB (M.omega q b (x.2 / M.reference.avogadro)) x.1

def internalEnergy (M : HarmonicVolumeModel) (x : ℝ × ℝ) : ℝ :=
  M.reference.avogadro * M.staticEnergy (x.2 / M.reference.avogadro) +
    uniformMolarContraction M.reference fun q b =>
      harmonicInternalEnergy ℏ kB (M.omega q b (x.2 / M.reference.avogadro)) x.1

def entropy (M : HarmonicVolumeModel) (x : ℝ × ℝ) : ℝ :=
  uniformMolarContraction M.reference fun q b =>
    harmonicEntropy ℏ kB (M.omega q b (x.2 / M.reference.avogadro)) x.1

def cv (M : HarmonicVolumeModel) (x : ℝ × ℝ) : ℝ :=
  uniformMolarContraction M.reference fun q b =>
    harmonicHeatCapacity ℏ kB (M.omega q b (x.2 / M.reference.avogadro)) x.1

/-- Actual molar canonical energy, totalized outside the volume domain only to
provide a real function for differentiation. No outside-domain physics is asserted. -/
def actualMolarInternalEnergy (M : HarmonicVolumeModel) (t V : ℝ) : ℝ :=
  if h : V / M.reference.avogadro ∈ M.J then
    (M.reference.avogadro / (M.reference.qCount : ℝ)) *
      (M.ensembleAt (V / M.reference.avogadro) h).meanEnergyT t
  else 0

/-- Independently defined derivative of actual molar enthalpy. -/
def actualCp (M : HarmonicVolumeModel) (p : ℝ) (V : ℝ → ℝ) (t : ℝ) : ℝ :=
  deriv (fun s => M.actualMolarInternalEnergy s (V s) + p * V s) t

theorem domain_isOpen (M : HarmonicVolumeModel) : IsOpen M.domain :=
  (isOpen_Ioi.preimage continuous_fst).inter
    (M.open_J.preimage (continuous_snd.div_const M.reference.avogadro))

theorem domain_positive (M : HarmonicVolumeModel) {x : ℝ × ℝ} (hx : x ∈ M.domain) :
    0 < x.1 ∧ 0 < x.2 := by
  refine ⟨hx.1, ?_⟩
  have h := mul_pos (M.positive_J hx.2) M.reference.avogadro_pos
  simpa only [div_mul_cancel₀ _ M.reference.avogadro_pos.ne'] using h

/-- The actual F identification includes the static energy in the Hamiltonian. -/
theorem freeEnergy_eq_actual (M : HarmonicVolumeModel) (T : Temperature)
    (hT : 0 < T.val) (V : ℝ) (hV : V / M.reference.avogadro ∈ M.J) :
    M.freeEnergy ((T : ℝ), V) = (M.reference.avogadro / (M.reference.qCount : ℝ)) *
      (M.ensembleAt (V / M.reference.avogadro) hV).helmholtzFreeEnergy T := by
  symm
  exact staticHarmonicGrid_molar_helmholtzFreeEnergy
    (M.gridAt (V / M.reference.avogadro) hV) (M.staticEnergy _) T hT

theorem internalEnergy_eq_actual (M : HarmonicVolumeModel) (T : Temperature)
    (hT : 0 < T.val) (V : ℝ) (hV : V / M.reference.avogadro ∈ M.J) :
    M.internalEnergy ((T : ℝ), V) = (M.reference.avogadro / (M.reference.qCount : ℝ)) *
      (M.ensembleAt (V / M.reference.avogadro) hV).meanEnergy T := by
  symm
  exact staticHarmonicGrid_molar_meanEnergy
    (M.gridAt (V / M.reference.avogadro) hV) (M.staticEnergy _) T hT

theorem entropy_eq_actual (M : HarmonicVolumeModel) (T : Temperature)
    (hT : 0 < T.val) (V : ℝ) (hV : V / M.reference.avogadro ∈ M.J) :
    M.entropy ((T : ℝ), V) = (M.reference.avogadro / (M.reference.qCount : ℝ)) *
      (M.ensembleAt (V / M.reference.avogadro) hV).thermodynamicEntropy T := by
  symm
  exact staticHarmonicGrid_molar_thermodynamicEntropy
    (M.gridAt (V / M.reference.avogadro) hV) (M.staticEnergy _) T hT

theorem cv_eq_actual (M : HarmonicVolumeModel) (T : Temperature)
    (hT : 0 < T.val) (V : ℝ) (hV : V / M.reference.avogadro ∈ M.J) :
    M.cv ((T : ℝ), V) = (M.reference.avogadro / (M.reference.qCount : ℝ)) *
      (M.ensembleAt (V / M.reference.avogadro) hV).heatCapacity T := by
  symm
  exact staticHarmonicGrid_molar_heatCapacity
    (M.gridAt (V / M.reference.avogadro) hV) (M.staticEnergy _) T hT

/-- The fixed-volume input remains the existing harmonic molar endpoint. -/
theorem cv_eq_harmonicMolarHeatCapacity (M : HarmonicVolumeModel) (T : Temperature)
    (V : ℝ) (hV : V / M.reference.avogadro ∈ M.J) :
    M.cv ((T : ℝ), V) = harmonicMolarHeatCapacity
      (M.gridAt (V / M.reference.avogadro) hV) T := rfl

theorem mode_freeEnergy_contDiffAt (M : HarmonicVolumeModel)
    (q : Fin M.reference.qCount) (b : Fin (3 * M.reference.atomCount))
    {x : ℝ × ℝ} (hx : x ∈ M.domain) :
    ContDiffAt ℝ 2 (fun y : ℝ × ℝ =>
      harmonicFreeEnergy ℏ kB (M.omega q b (y.2 / M.reference.avogadro)) y.1) x := by
  have hw : ContDiffAt ℝ 2 (fun y : ℝ × ℝ => M.omega q b (y.2 / M.reference.avogadro)) x :=
    ((M.omega_C2 q b).contDiffAt (M.open_J.mem_nhds hx.2)).comp x (by fun_prop)
  have ht : ContDiffAt ℝ 2 (fun y : ℝ × ℝ => y.1) x := by fun_prop
  have ha : ContDiffAt ℝ 2 (fun y : ℝ × ℝ =>
      harmonicArgument ℏ kB (M.omega q b (y.2 / M.reference.avogadro)) y.1) x :=
    (contDiffAt_const.mul hw).div (contDiffAt_const.mul ht) (mul_pos kB_pos hx.1).ne'
  have hl := (contDiffAt_const.sub ha.neg.exp).log
    (harmonic_log_argument_pos ℏ_pos kB_pos (M.omega_pos q b _ hx.2) hx.1).ne'
  exact ((contDiffAt_const.mul hw).div_const 2).add ((contDiffAt_const.mul ht).mul hl)

theorem freeEnergy_contDiffAt (M : HarmonicVolumeModel) {x : ℝ × ℝ}
    (hx : x ∈ M.domain) : ContDiffAt ℝ 2 M.freeEnergy x := by
  have he : ContDiffAt ℝ 2 (fun y : ℝ × ℝ => M.staticEnergy (y.2 / M.reference.avogadro)) x :=
    (M.staticEnergy_C2.contDiffAt (M.open_J.mem_nhds hx.2)).comp x (by fun_prop)
  have hs : ContDiffAt ℝ 2 (fun y : ℝ × ℝ => ∑ q, ∑ b,
      harmonicFreeEnergy ℏ kB (M.omega q b (y.2 / M.reference.avogadro)) y.1) x :=
    ContDiffAt.sum fun q _ => ContDiffAt.sum fun b _ => M.mode_freeEnergy_contDiffAt q b hx
  exact (contDiffAt_const.mul he).add
    ((contDiffAt_const.mul hs).div_const (M.reference.qCount : ℝ))

theorem freeEnergy_contDiffOn (M : HarmonicVolumeModel) :
    ContDiffOn ℝ 2 M.freeEnergy M.domain :=
  fun _ hx => (M.freeEnergy_contDiffAt hx).contDiffWithinAt

theorem freeEnergy_temperature_hasDerivAt (M : HarmonicVolumeModel) {t V : ℝ}
    (hx : (t, V) ∈ M.domain) :
    HasDerivAt (fun s => M.freeEnergy (s, V)) (-M.entropy (t, V)) t := by
  have hs : HasDerivAt (fun s => ∑ q, ∑ b,
      harmonicFreeEnergy ℏ kB (M.omega q b (V / M.reference.avogadro)) s)
      (∑ q, ∑ b, -harmonicEntropy ℏ kB (M.omega q b (V / M.reference.avogadro)) t) t :=
    HasDerivAt.fun_sum fun q _ => HasDerivAt.fun_sum fun b _ =>
      harmonicFreeEnergy_hasDerivAt ℏ_pos kB_pos (M.omega_pos q b _ hx.2) hx.1
  have h := (hasDerivAt_const t (M.reference.avogadro * M.staticEnergy (V / M.reference.avogadro))).fun_add
    ((hs.const_mul M.reference.avogadro).div_const (M.reference.qCount : ℝ))
  simpa only [freeEnergy, entropy, uniformMolarContraction, Finset.sum_neg_distrib,
    mul_neg, neg_div, zero_add] using h

theorem internalEnergy_temperature_hasDerivAt (M : HarmonicVolumeModel) {t V : ℝ}
    (hx : (t, V) ∈ M.domain) :
    HasDerivAt (fun s => M.internalEnergy (s, V)) (M.cv (t, V)) t := by
  have hs : HasDerivAt (fun s => ∑ q, ∑ b,
      harmonicInternalEnergy ℏ kB (M.omega q b (V / M.reference.avogadro)) s)
      (∑ q, ∑ b, harmonicHeatCapacity ℏ kB (M.omega q b (V / M.reference.avogadro)) t) t :=
    HasDerivAt.fun_sum fun q _ => HasDerivAt.fun_sum fun b _ =>
      harmonicInternalEnergy_hasDerivAt ℏ_pos kB_pos (M.omega_pos q b _ hx.2) hx.1
  have h := (hasDerivAt_const t (M.reference.avogadro * M.staticEnergy (V / M.reference.avogadro))).fun_add
    ((hs.const_mul M.reference.avogadro).div_const (M.reference.qCount : ℝ))
  simpa only [internalEnergy, cv, uniformMolarContraction, zero_add] using h

theorem freeEnergy_eq_internalEnergy_sub_temperature_entropy (M : HarmonicVolumeModel)
    {t V : ℝ} (hx : (t, V) ∈ M.domain) :
    M.freeEnergy (t, V) = M.internalEnergy (t, V) - t * M.entropy (t, V) := by
  have hf : ∀ q b,
      harmonicFreeEnergy ℏ kB (M.omega q b (V / M.reference.avogadro)) t =
      harmonicInternalEnergy ℏ kB (M.omega q b (V / M.reference.avogadro)) t -
        t * harmonicEntropy ℏ kB (M.omega q b (V / M.reference.avogadro)) t :=
    fun q b => harmonic_freeEnergy_eq_internalEnergy_sub_temperature_mul_entropy
      ℏ_pos kB_pos (M.omega_pos q b _ hx.2) hx.1
  unfold freeEnergy internalEnergy entropy uniformMolarContraction
  simp_rw [hf, Finset.sum_sub_distrib, ← Finset.mul_sum]
  ring

theorem FT_eq_neg_entropy (M : HarmonicVolumeModel) {t V : ℝ}
    (hx : (t, V) ∈ M.domain) : Response.FT M.freeEnergy (t, V) = -M.entropy (t, V) := by
  rw [Response.FT_eq_deriv (M.freeEnergy_contDiffAt hx)]
  exact (M.freeEnergy_temperature_hasDerivAt hx).deriv

theorem internalEnergy_eq_responseInternal (M : HarmonicVolumeModel) {t V : ℝ}
    (hx : (t, V) ∈ M.domain) :
    M.internalEnergy (t, V) = Response.internalEnergy M.freeEnergy (t, V) := by
  unfold Response.internalEnergy
  rw [M.FT_eq_neg_entropy hx]
  have h := M.freeEnergy_eq_internalEnergy_sub_temperature_entropy hx
  dsimp only at *
  linarith

theorem cv_eq_responseCv (M : HarmonicVolumeModel) {t V : ℝ}
    (hx : (t, V) ∈ M.domain) : M.cv (t, V) = Response.cv M.freeEnergy (t, V) := by
  have heq : (fun s => Response.internalEnergy M.freeEnergy (s, V)) =ᶠ[𝓝 t]
      (fun s => M.internalEnergy (s, V)) := by
    filter_upwards [isOpen_Ioi.mem_nhds hx.1] with s hs
    exact (M.internalEnergy_eq_responseInternal ⟨hs, hx.2⟩).symm
  exact ((M.internalEnergy_temperature_hasDerivAt hx).congr_of_eventuallyEq heq).unique
    (Response.internalEnergy_temperature_hasDerivAt (M.freeEnergy_contDiffAt hx))

theorem actualMolarInternalEnergy_eq (M : HarmonicVolumeModel) {t V : ℝ}
    (hx : (t, V) ∈ M.domain) : M.actualMolarInternalEnergy t V = M.internalEnergy (t, V) := by
  unfold actualMolarInternalEnergy
  rw [dite_eq_left hx.2]
  have ht : 0 < (Temperature.ofNNReal (Real.toNNReal t)).val := by
    simpa only [Temperature.ofNNReal_val] using Real.toNNReal_pos.mpr hx.1
  have h := M.internalEnergy_eq_actual (Temperature.ofNNReal (Real.toNNReal t)) ht V hx.2
  simpa [CanonicalEnsemble.meanEnergyT, Temperature.ofNNReal, Temperature.toReal,
    Real.toNNReal_of_nonneg hx.1.le] using h.symm

theorem actualCp_eq_responseCp (M : HarmonicVolumeModel) (p t : ℝ)
    (B : Response.StableBranchAt M.freeEnergy M.domain p t) :
    M.actualCp p B.volume t = Response.cp M.freeEnergy p B.volume t := by
  have heq : (fun s => M.actualMolarInternalEnergy s (B.volume s) + p * B.volume s) =ᶠ[𝓝 t]
      (fun s => Response.internalEnergy M.freeEnergy (s, B.volume s) + p * B.volume s) := by
    filter_upwards [B.eventually_in_domain] with s hs
    rw [M.actualMolarInternalEnergy_eq hs, M.internalEnergy_eq_responseInternal hs]
  exact heq.deriv_eq

theorem actualCp_sub_cv (M : HarmonicVolumeModel) (p t : ℝ)
    (B : Response.StableBranchAt M.freeEnergy M.domain p t) :
    M.actualCp p B.volume t - M.cv (t, B.volume t) =
      t * B.volume t * (Response.expansion B.volume t)^2 * Response.bulk M.freeEnergy (t, B.volume t) := by
  rw [M.actualCp_eq_responseCp p t B, M.cv_eq_responseCv B.in_domain]
  exact Response.cp_sub_cv M.freeEnergy M.domain p t M.domain_isOpen
    M.freeEnergy_contDiffOn (fun _ hx => M.domain_positive hx) B

theorem actualCp_ge_cv (M : HarmonicVolumeModel) (p t : ℝ)
    (B : Response.StableBranchAt M.freeEnergy M.domain p t) :
    M.cv (t, B.volume t) ≤ M.actualCp p B.volume t := by
  rw [M.actualCp_eq_responseCp p t B, M.cv_eq_responseCv B.in_domain]
  exact Response.cp_ge_cv M.freeEnergy M.domain p t M.domain_isOpen
    M.freeEnergy_contDiffOn (fun _ hx => M.domain_positive hx) B

/-- Strict positivity follows from the actual positive oscillator capacities and nonempty grid. -/
theorem cv_pos (M : HarmonicVolumeModel) {t V : ℝ} (hx : (t, V) ∈ M.domain) :
    0 < M.cv (t, V) := by
  let : NeZero M.reference.qCount := ⟨Nat.ne_of_gt M.reference.qCount_pos⟩
  let : NeZero (3 * M.reference.atomCount) := ⟨by
    have := M.reference.atomCount_pos
    omega⟩
  have hs : 0 < ∑ q, ∑ b, harmonicHeatCapacity ℏ kB
      (M.omega q b (V / M.reference.avogadro)) t :=
    Finset.sum_pos (fun q _ => Finset.sum_pos (fun b _ =>
      harmonicHeatCapacity_pos ℏ_pos kB_pos (M.omega_pos q b _ hx.2) hx.1)
      Finset.univ_nonempty) Finset.univ_nonempty
  exact div_pos (mul_pos M.reference.avogadro_pos hs) (Nat.cast_pos.mpr M.reference.qCount_pos)

/-- The same closed free energy before changing from cell to molar coordinates. -/
def cellFreeEnergy (M : HarmonicVolumeModel) (t v : ℝ) : ℝ :=
  M.staticEnergy v + (∑ q, ∑ b, harmonicFreeEnergy ℏ kB (M.omega q b v) t) /
    (M.reference.qCount : ℝ)

theorem freeEnergy_eq_molarLift (M : HarmonicVolumeModel) (t V : ℝ) :
    M.freeEnergy (t, V) = molarLift M.reference.avogadro M.cellFreeEnergy t V := by
  unfold freeEnergy cellFreeEnergy molarLift uniformMolarContraction
  ring

/-- Smoothness of the same per-cell surface, obtained by the inverse coordinate lift. -/
theorem cellFreeEnergy_contDiffAt (M : HarmonicVolumeModel) {t v : ℝ}
    (ht : 0 < t) (hv : v ∈ M.J) :
    ContDiffAt ℝ 2 (fun x : ℝ × ℝ => M.cellFreeEnergy x.1 x.2) (t, v) := by
  have hx : (t, M.reference.avogadro * v) ∈ M.domain := by
    refine ⟨ht, ?_⟩
    simpa only [mul_div_cancel_left₀ _ M.reference.avogadro_pos.ne'] using hv
  have h := ((M.freeEnergy_contDiffAt hx).comp (t, v)
    (show ContDiffAt ℝ 2 (fun x : ℝ × ℝ => (x.1, M.reference.avogadro * x.2)) (t, v) from by fun_prop)).div_const
      M.reference.avogadro
  convert h using 1
  ext x
  dsimp only [Function.comp_def]
  rw [M.freeEnergy_eq_molarLift]
  simp [molarLift, M.reference.avogadro_pos.ne']

/-- The first volume derivative, hence pressure with a minus sign, is unchanged
by coherent primitive-cell to molar coordinates. -/
theorem FV_eq_cell_deriv (M : HarmonicVolumeModel) {t v : ℝ}
    (ht : 0 < t) (hv : v ∈ M.J) :
    Response.FV M.freeEnergy (t, M.reference.avogadro * v) =
      deriv (M.cellFreeEnergy t) v := by
  have hx : (t, M.reference.avogadro * v) ∈ M.domain := by
    refine ⟨ht, ?_⟩
    simpa only [mul_div_cancel_left₀ _ M.reference.avogadro_pos.ne'] using hv
  have hfun : (fun V => M.freeEnergy (t, V)) = molarLift M.reference.avogadro M.cellFreeEnergy t := by
    funext V
    exact M.freeEnergy_eq_molarLift t V
  rw [Response.FV_eq_deriv (M.freeEnergy_contDiffAt hx), hfun,
    molarLift_volume_deriv M.reference.avogadro_pos]
  simp [M.reference.avogadro_pos.ne']

/-- The actual-model molar bulk modulus equals the per-cell curvature expression. -/
theorem bulk_eq_cell_bulk (M : HarmonicVolumeModel) {t v : ℝ}
    (ht : 0 < t) (hv : v ∈ M.J) :
    Response.bulk M.freeEnergy (t, M.reference.avogadro * v) =
      v * deriv (deriv (M.cellFreeEnergy t)) v := by
  have hx : (t, M.reference.avogadro * v) ∈ M.domain := by
    refine ⟨ht, ?_⟩
    simpa only [mul_div_cancel_left₀ _ M.reference.avogadro_pos.ne'] using hv
  have hfun : (fun V => M.freeEnergy (t, V)) = molarLift M.reference.avogadro M.cellFreeEnergy t := by
    funext V
    exact M.freeEnergy_eq_molarLift t V
  unfold Response.bulk
  rw [Response.FVV_eq_deriv_deriv_volume M.domain_isOpen M.freeEnergy_contDiffOn hx, hfun]
  exact molarLift_volume_bulk M.reference.avogadro_pos
    ((M.cellFreeEnergy_contDiffAt ht hv).comp v (by fun_prop))

end HarmonicVolumeModel
end OMAI.PhyslibBridge
