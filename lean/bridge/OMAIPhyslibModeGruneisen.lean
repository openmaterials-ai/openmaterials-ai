module

public import OMAIPhyslibHarmonicVolume
public import OMAIPhyslibJointDensity

/-!
# Mode Gruneisen parameters and heat-capacity weights of a harmonic volume family

The mode parameters are derivative-defined from the volume family's own frequency curves.
The weights are the actual Physlib canonical heat capacities of the per-mode oscillators at
fixed primitive-cell volume. The weighted mean is defined independently of any free-energy
surface, equilibrium branch, expansion coefficient, bulk modulus or catalog quotient. No FC3,
finite-difference or Phonopy producer is identified by these definitions.
-/

@[expose] public section

noncomputable section

open Constants Temperature Filter
open scoped BigOperators Topology

namespace OMAI.PhyslibBridge.HarmonicVolumeModel

/-- gamma_{q,b}(v) = -v omega'(v)/omega(v) of this volume family's own frequency curve. Not an
FC3, finite-difference or Phonopy producer. -/
def modeGruneisen (M : HarmonicVolumeModel) (q : Fin M.reference.qCount)
    (b : Fin (3 * M.reference.atomCount)) (v : ℝ) : ℝ :=
  -(v * deriv (M.omega q b) v) / M.omega q b v

/-- Actual Physlib canonical (derivative-defined) heat capacity of mode (q,b) at fixed v. -/
def modeHeatCapacity (M : HarmonicVolumeModel) (T : Temperature) (v : ℝ) (hv : v ∈ M.J)
    (q : Fin M.reference.qCount) (b : Fin (3 * M.reference.atomCount)) : ℝ :=
  (harmonicEnsemble ((M.gridAt v hv).oscillator q b)).heatCapacity T

/-- Gamma(T,v) = sum gamma_i c_i / sum c_i with actual per-mode weights. No free-energy
surface, branch, expansion, bulk modulus or catalog quotient. Totalized; nothing is asserted
at T = 0. -/
def weightedGruneisen (M : HarmonicVolumeModel) (T : Temperature) (v : ℝ) (hv : v ∈ M.J) : ℝ :=
  (∑ q, ∑ b, M.modeGruneisen q b v * M.modeHeatCapacity T v hv q b) /
    ∑ q, ∑ b, M.modeHeatCapacity T v hv q b

/-- The model's own positive primitive-cell volume coordinate (not a CellVolume producer). -/
def primitiveCellVolumeAt (M : HarmonicVolumeModel) (v : ℝ) (hv : v ∈ M.J) :
    PrimitiveCellVolume := ⟨v, M.positive_J hv⟩

theorem omega_hasDerivAt (M : HarmonicVolumeModel) (q : Fin M.reference.qCount)
    (b : Fin (3 * M.reference.atomCount)) {v : ℝ} (hv : v ∈ M.J) :
    HasDerivAt (M.omega q b) (deriv (M.omega q b) v) v :=
  (((M.omega_C2 q b).contDiffAt (M.open_J.mem_nhds hv)).differentiableAt
    (by norm_num)).hasDerivAt

theorem deriv_omega_eq_modeGruneisen (M : HarmonicVolumeModel) (q : Fin M.reference.qCount)
    (b : Fin (3 * M.reference.atomCount)) {v : ℝ} (hv : v ∈ M.J) :
    deriv (M.omega q b) v = -(M.modeGruneisen q b v * M.omega q b v) / v := by
  have hv0 := (M.positive_J hv).ne'
  have hw0 := (M.omega_pos q b v hv).ne'
  unfold modeGruneisen
  field_simp

theorem modeHeatCapacity_eq_closed (M : HarmonicVolumeModel) (T : Temperature) (v : ℝ)
    (hv : v ∈ M.J) (hT : 0 < T.val) (q : Fin M.reference.qCount)
    (b : Fin (3 * M.reference.atomCount)) :
    M.modeHeatCapacity T v hv q b = harmonicHeatCapacity ℏ kB (M.omega q b v) (T : ℝ) :=
  harmonic_heatCapacity_eq_omai ((M.gridAt v hv).oscillator q b) T hT

theorem modeHeatCapacity_pos (M : HarmonicVolumeModel) (T : Temperature) (v : ℝ)
    (hv : v ∈ M.J) (hT : 0 < T.val) (q : Fin M.reference.qCount)
    (b : Fin (3 * M.reference.atomCount)) : 0 < M.modeHeatCapacity T v hv q b := by
  have hTr : 0 < (T : ℝ) := by
    change 0 < (T.val : ℝ)
    exact_mod_cast hT
  rw [M.modeHeatCapacity_eq_closed T v hv hT q b]
  exact harmonicHeatCapacity_pos ℏ_pos kB_pos (M.omega_pos q b v hv) hTr

theorem modeHeatCapacity_sum_pos (M : HarmonicVolumeModel) (T : Temperature) (v : ℝ)
    (hv : v ∈ M.J) (hT : 0 < T.val) : 0 < ∑ q, ∑ b, M.modeHeatCapacity T v hv q b := by
  let : NeZero M.reference.qCount := ⟨Nat.ne_of_gt M.reference.qCount_pos⟩
  let : NeZero (3 * M.reference.atomCount) := ⟨by
    have := M.reference.atomCount_pos
    omega⟩
  exact Finset.sum_pos (fun q _ => Finset.sum_pos (fun b _ =>
    M.modeHeatCapacity_pos T v hv hT q b) Finset.univ_nonempty) Finset.univ_nonempty

theorem weightedGruneisen_eq_closed (M : HarmonicVolumeModel) (T : Temperature) (v : ℝ)
    (hv : v ∈ M.J) (hT : 0 < T.val) :
    M.weightedGruneisen T v hv =
      (∑ q, ∑ b, M.modeGruneisen q b v * harmonicHeatCapacity ℏ kB (M.omega q b v) (T : ℝ)) /
        ∑ q, ∑ b, harmonicHeatCapacity ℏ kB (M.omega q b v) (T : ℝ) := by
  simp only [weightedGruneisen, M.modeHeatCapacity_eq_closed T v hv hT]

theorem weightedGruneisen_congr (M : HarmonicVolumeModel) (T : Temperature) {v w : ℝ}
    (h : v = w) (hv : v ∈ M.J) (hw : w ∈ M.J) :
    M.weightedGruneisen T v hv = M.weightedGruneisen T w hw := by
  subst h
  rfl

theorem volumetricCv_eq_modeSum (M : HarmonicVolumeModel) (T : Temperature) (v : ℝ)
    (hv : v ∈ M.J) :
    harmonicVolumetricHeatCapacity (M.gridAt v hv) (M.primitiveCellVolumeAt v hv) T =
      (∑ q, ∑ b, harmonicHeatCapacity ℏ kB (M.omega q b v) (T : ℝ)) /
        ((M.reference.qCount : ℝ) * v) := rfl

theorem volumetricCv_eq_actual_modes (M : HarmonicVolumeModel) (T : Temperature) (v : ℝ)
    (hv : v ∈ M.J) (hT : 0 < T.val) :
    harmonicVolumetricHeatCapacity (M.gridAt v hv) (M.primitiveCellVolumeAt v hv) T =
      (∑ q, ∑ b, M.modeHeatCapacity T v hv q b) / ((M.reference.qCount : ℝ) * v) :=
  (harmonic_volumetric_heatCapacity_eq_omai _ _ T hT).symm

theorem volumetricCv_eq_actual_ensemble (M : HarmonicVolumeModel) (T : Temperature) (v : ℝ)
    (hv : v ∈ M.J) (hT : 0 < T.val) :
    (M.ensembleAt v hv).heatCapacity T / ((M.reference.qCount : ℝ) * v) =
      harmonicVolumetricHeatCapacity (M.gridAt v hv) (M.primitiveCellVolumeAt v hv) T := by
  unfold ensembleAt
  rw [staticHarmonicGrid_heatCapacity _ _ T hT]
  exact harmonic_joint_volumetric_heatCapacity_eq_omai (M.gridAt v hv)
    (M.primitiveCellVolumeAt v hv) T hT

theorem volumetricCv_eq_cv_div_volume (M : HarmonicVolumeModel) (T : Temperature) {V : ℝ}
    (hx : ((T : ℝ), V) ∈ M.domain) :
    harmonicVolumetricHeatCapacity (M.gridAt (V / M.reference.avogadro) hx.2)
        (M.primitiveCellVolumeAt (V / M.reference.avogadro) hx.2) T =
      M.cv ((T : ℝ), V) / V := by
  rw [harmonicVolumetricHeatCapacity_eq_molar_div, M.cv_eq_harmonicMolarHeatCapacity T V hx.2]
  congr 1
  change M.reference.avogadro * (V / M.reference.avogadro) = V
  field_simp [M.reference.avogadro_pos.ne']

theorem volumetricCv_pos (M : HarmonicVolumeModel) (T : Temperature) (v : ℝ)
    (hv : v ∈ M.J) (hT : 0 < T.val) :
    0 < harmonicVolumetricHeatCapacity (M.gridAt v hv) (M.primitiveCellVolumeAt v hv) T := by
  rw [M.volumetricCv_eq_actual_modes T v hv hT]
  exact div_pos (M.modeHeatCapacity_sum_pos T v hv hT)
    (mul_pos (Nat.cast_pos.mpr M.reference.qCount_pos) (M.positive_J hv))

theorem cellFreeEnergy_volume_hasDerivAt (M : HarmonicVolumeModel) {t v : ℝ}
    (ht : 0 < t) (hv : v ∈ M.J) :
    HasDerivAt (M.cellFreeEnergy t)
      (deriv M.staticEnergy v -
        (∑ q, ∑ b, M.modeGruneisen q b v * harmonicInternalEnergy ℏ kB (M.omega q b v) t) /
          ((M.reference.qCount : ℝ) * v)) v := by
  have hv0 := (M.positive_J hv).ne'
  have hmode : ∀ q b, HasDerivAt (fun w => harmonicFreeEnergy ℏ kB (M.omega q b w) t)
      (-(M.modeGruneisen q b v * harmonicInternalEnergy ℏ kB (M.omega q b v) t) / v) v := by
    intro q b
    have hw0 := (M.omega_pos q b v hv).ne'
    have h := (harmonicFreeEnergy_frequency_hasDerivAt ℏ_pos kB_pos (M.omega_pos q b v hv)
      ht).comp v (M.omega_hasDerivAt q b hv)
    convert h using 1
    · rfl
    · rw [M.deriv_omega_eq_modeGruneisen q b hv]
      field_simp
  have hs := HasDerivAt.fun_sum (u := Finset.univ) fun q _ =>
    HasDerivAt.fun_sum (u := Finset.univ) fun b _ => hmode q b
  have hE : HasDerivAt M.staticEnergy (deriv M.staticEnergy v) v :=
    ((M.staticEnergy_C2.contDiffAt (M.open_J.mem_nhds hv)).differentiableAt
      (by norm_num)).hasDerivAt
  have h := hE.fun_add (hs.div_const (M.reference.qCount : ℝ))
  convert h using 1
  · rfl
  · simp only [neg_div, Finset.sum_neg_distrib, ← Finset.sum_div]
    ring

/-- Mode-resolved Mie-Gruneisen form of the pressure (P = -F_V): static pressure plus
sum_i gamma_i U_i/(N_q v), with zero-point energy in U_i; when all gamma_i equal a
common gamma(v), it reduces to the single-Gamma Mie-Gruneisen form with
Gamma = gamma(v). -/
theorem FV_eq_modeSum (M : HarmonicVolumeModel) {t V : ℝ} (hx : (t, V) ∈ M.domain) :
    Response.FV M.freeEnergy (t, V) =
      deriv M.staticEnergy (V / M.reference.avogadro) -
        (∑ q, ∑ b, M.modeGruneisen q b (V / M.reference.avogadro) *
            harmonicInternalEnergy ℏ kB (M.omega q b (V / M.reference.avogadro)) t) /
          ((M.reference.qCount : ℝ) * (V / M.reference.avogadro)) := by
  have ht : 0 < t := hx.1
  have hv : V / M.reference.avogadro ∈ M.J := hx.2
  have hV : M.reference.avogadro * (V / M.reference.avogadro) = V := by
    field_simp [M.reference.avogadro_pos.ne']
  have h := M.FV_eq_cell_deriv ht hv
  rw [hV] at h
  rw [h]
  exact (M.cellFreeEnergy_volume_hasDerivAt ht hv).deriv

theorem mixedTV_eq_neg_modeSum (M : HarmonicVolumeModel) {t V : ℝ}
    (hx : (t, V) ∈ M.domain) :
    Response.mixedTV M.freeEnergy (t, V) =
      -((∑ q, ∑ b, M.modeGruneisen q b (V / M.reference.avogadro) *
            harmonicHeatCapacity ℏ kB (M.omega q b (V / M.reference.avogadro)) t) /
          ((M.reference.qCount : ℝ) * (V / M.reference.avogadro))) := by
  have ht : 0 < t := hx.1
  have hv : V / M.reference.avogadro ∈ M.J := hx.2
  rw [Response.mixedTV_eq_deriv_FV (M.freeEnergy_contDiffAt hx)]
  have heq : (fun s => Response.FV M.freeEnergy (s, V)) =ᶠ[𝓝 t] (fun s =>
      deriv M.staticEnergy (V / M.reference.avogadro) -
        (∑ q, ∑ b, M.modeGruneisen q b (V / M.reference.avogadro) *
            harmonicInternalEnergy ℏ kB (M.omega q b (V / M.reference.avogadro)) s) /
          ((M.reference.qCount : ℝ) * (V / M.reference.avogadro))) := by
    filter_upwards [isOpen_Ioi.mem_nhds ht] with s hs
    exact M.FV_eq_modeSum ⟨hs, hv⟩
  rw [heq.deriv_eq]
  have hU : HasDerivAt (fun s => ∑ q, ∑ b, M.modeGruneisen q b (V / M.reference.avogadro) *
        harmonicInternalEnergy ℏ kB (M.omega q b (V / M.reference.avogadro)) s)
      (∑ q, ∑ b, M.modeGruneisen q b (V / M.reference.avogadro) *
        harmonicHeatCapacity ℏ kB (M.omega q b (V / M.reference.avogadro)) t) t :=
    HasDerivAt.fun_sum fun q _ => HasDerivAt.fun_sum fun b _ =>
      (harmonicInternalEnergy_hasDerivAt ℏ_pos kB_pos (M.omega_pos q b _ hv) ht).const_mul _
  exact ((hU.div_const ((M.reference.qCount : ℝ) * (V / M.reference.avogadro))).const_sub
    (deriv M.staticEnergy (V / M.reference.avogadro))).deriv

/-- Fixed-volume thermal-pressure coefficient (dP/dT)_V = -F_TV = Gamma C_V^vol; no branch. -/
theorem neg_mixedTV_eq_weightedGruneisen_mul_volumetricCv (M : HarmonicVolumeModel)
    (T : Temperature) {V : ℝ} (hx : ((T : ℝ), V) ∈ M.domain) :
    -Response.mixedTV M.freeEnergy ((T : ℝ), V) =
      M.weightedGruneisen T (V / M.reference.avogadro) hx.2 *
        harmonicVolumetricHeatCapacity (M.gridAt (V / M.reference.avogadro) hx.2)
          (M.primitiveCellVolumeAt (V / M.reference.avogadro) hx.2) T := by
  have hT : 0 < T.val := by
    have h : 0 < ((T.val : NNReal) : ℝ) := hx.1
    exact_mod_cast h
  have hv : V / M.reference.avogadro ∈ M.J := hx.2
  have hS := M.modeHeatCapacity_sum_pos T _ hv hT
  simp only [M.modeHeatCapacity_eq_closed T _ hv hT] at hS
  have hn : (0 : ℝ) < M.reference.qCount := Nat.cast_pos.mpr M.reference.qCount_pos
  have hv0 : 0 < V / M.reference.avogadro := M.positive_J hv
  rw [M.mixedTV_eq_neg_modeSum hx, neg_neg, M.weightedGruneisen_eq_closed T _ hv hT,
    M.volumetricCv_eq_modeSum T _ hv]
  rw [div_mul_div_comm, mul_comm (∑ q, ∑ b, M.modeGruneisen q b (V / M.reference.avogadro) *
      harmonicHeatCapacity ℏ kB (M.omega q b (V / M.reference.avogadro)) (T : ℝ)),
    mul_div_mul_left _ _ hS.ne']

/-- Division-free branch form: alpha_V K_T = Gamma C_V^vol at the same T and branch volume. -/
theorem expansion_mul_bulk_eq_weightedGruneisen_mul_volumetricCv (M : HarmonicVolumeModel)
    (p : ℝ) (T : Temperature) (B : Response.StableBranchAt M.freeEnergy M.domain p (T : ℝ)) :
    Response.expansion B.volume (T : ℝ) *
        Response.bulk M.freeEnergy ((T : ℝ), B.volume (T : ℝ)) =
      M.weightedGruneisen T (B.volume (T : ℝ) / M.reference.avogadro) B.in_domain.2 *
        harmonicVolumetricHeatCapacity
          (M.gridAt (B.volume (T : ℝ) / M.reference.avogadro) B.in_domain.2)
          (M.primitiveCellVolumeAt (B.volume (T : ℝ) / M.reference.avogadro) B.in_domain.2)
          T := by
  have hE := B.equilibrium_derivative (M.freeEnergy_contDiffAt B.in_domain)
  have hpos : 0 < B.volume (T : ℝ) := (M.domain_positive B.in_domain).2
  rw [← M.neg_mixedTV_eq_weightedGruneisen_mul_volumetricCv T B.in_domain]
  unfold Response.expansion Response.bulk
  rw [B.volume_deriv.deriv]
  have hcancel : B.slope / B.volume (T : ℝ) *
      (B.volume (T : ℝ) * Response.FVV M.freeEnergy ((T : ℝ), B.volume (T : ℝ))) =
      B.slope * Response.FVV M.freeEnergy ((T : ℝ), B.volume (T : ℝ)) := by
    field_simp
  dsimp only
  rw [hcancel]
  linarith

theorem bulk_pos_of_branch (M : HarmonicVolumeModel) (p : ℝ) (T : Temperature)
    (B : Response.StableBranchAt M.freeEnergy M.domain p (T : ℝ)) :
    0 < Response.bulk M.freeEnergy ((T : ℝ), B.volume (T : ℝ)) :=
  mul_pos (M.domain_positive B.in_domain).2 B.stable

theorem expansion_pos_iff_weightedGruneisen_pos (M : HarmonicVolumeModel) (p : ℝ)
    (T : Temperature) (B : Response.StableBranchAt M.freeEnergy M.domain p (T : ℝ)) :
    0 < Response.expansion B.volume (T : ℝ) ↔
      0 < M.weightedGruneisen T (B.volume (T : ℝ) / M.reference.avogadro) B.in_domain.2 := by
  have hT : 0 < T.val := by
    have h : 0 < ((T.val : NNReal) : ℝ) := B.in_domain.1
    exact_mod_cast h
  have hK := M.bulk_pos_of_branch p T B
  have hC := M.volumetricCv_pos T _ B.in_domain.2 hT
  rw [← mul_pos_iff_of_pos_right hK, M.expansion_mul_bulk_eq_weightedGruneisen_mul_volumetricCv,
    mul_pos_iff_of_pos_right hC]

theorem expansion_neg_iff_weightedGruneisen_neg (M : HarmonicVolumeModel) (p : ℝ)
    (T : Temperature) (B : Response.StableBranchAt M.freeEnergy M.domain p (T : ℝ)) :
    Response.expansion B.volume (T : ℝ) < 0 ↔
      M.weightedGruneisen T (B.volume (T : ℝ) / M.reference.avogadro) B.in_domain.2 < 0 := by
  have hT : 0 < T.val := by
    have h : 0 < ((T.val : NNReal) : ℝ) := B.in_domain.1
    exact_mod_cast h
  have hK := M.bulk_pos_of_branch p T B
  have hC := M.volumetricCv_pos T _ B.in_domain.2 hT
  have h := M.expansion_mul_bulk_eq_weightedGruneisen_mul_volumetricCv p T B
  constructor
  · intro ha
    by_contra hg
    have h1 := mul_nonneg (not_lt.mp hg) hC.le
    have h2 := mul_neg_of_neg_of_pos ha hK
    linarith
  · intro hg
    by_contra ha
    have h1 := mul_nonneg (not_lt.mp ha) hK.le
    have h2 := mul_neg_of_neg_of_pos hg hC
    linarith

theorem expansion_eq_zero_iff_weightedGruneisen_eq_zero (M : HarmonicVolumeModel) (p : ℝ)
    (T : Temperature) (B : Response.StableBranchAt M.freeEnergy M.domain p (T : ℝ)) :
    Response.expansion B.volume (T : ℝ) = 0 ↔
      M.weightedGruneisen T (B.volume (T : ℝ) / M.reference.avogadro) B.in_domain.2 = 0 := by
  have hT : 0 < T.val := by
    have h : 0 < ((T.val : NNReal) : ℝ) := B.in_domain.1
    exact_mod_cast h
  have hK := M.bulk_pos_of_branch p T B
  have hC := M.volumetricCv_pos T _ B.in_domain.2 hT
  have h := M.expansion_mul_bulk_eq_weightedGruneisen_mul_volumetricCv p T B
  constructor
  · intro ha
    rw [ha, zero_mul] at h
    exact (mul_eq_zero.mp h.symm).resolve_right hC.ne'
  · intro hg
    rw [hg, zero_mul] at h
    exact (mul_eq_zero.mp h).resolve_right hK.ne'

end OMAI.PhyslibBridge.HarmonicVolumeModel

namespace OMAI.PhyslibBridge

/-! Strict decrease of the per-mode heat capacity with frequency at fixed positive temperature.
Supporting only: no witness or endpoint depends on these results. -/

/-- Reduced Einstein heat capacity c/kB at the reduced frequency x = hbar omega/(kB T). -/
def einsteinCapacity (x : ℝ) : ℝ := x ^ 2 * Real.exp x / (Real.exp x - 1) ^ 2

theorem harmonicHeatCapacity_eq_kB_mul_einsteinCapacity {omega t : ℝ}
    (hw : 0 < omega) (ht : 0 < t) :
    harmonicHeatCapacity ℏ kB omega t =
      kB * einsteinCapacity (harmonicArgument ℏ kB omega t) := by
  have hd := (harmonic_bose_denominator_pos ℏ_pos kB_pos hw ht).ne'
  have hx : (ℏ : ℝ) * omega = harmonicArgument ℏ kB omega t * (kB * t) := by
    unfold harmonicArgument
    field_simp [kB_ne_zero, ht.ne']
  rw [harmonicHeatCapacity_eq_exp ℏ_pos kB_pos hw ht, hx]
  unfold einsteinCapacity
  have hk := kB_ne_zero
  have ht0 := ht.ne'
  field_simp

theorem einstein_gap_pos {x : ℝ} (hx : 0 < x) :
    0 < x * (Real.exp x + 1) - 2 * (Real.exp x - 1) := by
  have hg : StrictMonoOn (fun y : ℝ => y * (Real.exp y + 1) - 2 * (Real.exp y - 1))
      (Set.Ici 0) := by
    apply strictMonoOn_of_deriv_pos (convex_Ici 0)
    · exact (by fun_prop : Continuous fun y : ℝ =>
        y * (Real.exp y + 1) - 2 * (Real.exp y - 1)).continuousOn
    · intro y hy
      rw [interior_Ici] at hy
      have hd : HasDerivAt (fun y : ℝ => y * (Real.exp y + 1) - 2 * (Real.exp y - 1))
          (1 - (1 - y) * Real.exp y) y := by
        have h := ((hasDerivAt_id' y).mul ((Real.hasDerivAt_exp y).add_const 1)).sub
          (((Real.hasDerivAt_exp y).sub_const 1).const_mul 2)
        convert h using 1
        · ring
      rw [hd.deriv]
      have h1 : 1 - y < Real.exp (-y) := by
        linarith [Real.add_one_lt_exp (neg_ne_zero.mpr (ne_of_gt hy))]
      have h2 : (1 - y) * Real.exp y < 1 := by
        calc (1 - y) * Real.exp y < Real.exp (-y) * Real.exp y :=
              mul_lt_mul_of_pos_right h1 (Real.exp_pos y)
          _ = 1 := by rw [← Real.exp_add, neg_add_cancel, Real.exp_zero]
      linarith
  have h := hg (Set.mem_Ici.mpr le_rfl) (Set.mem_Ici.mpr hx.le) hx
  simpa using h

theorem einsteinCapacity_hasDerivAt {x : ℝ} (hx : 0 < x) :
    HasDerivAt einsteinCapacity
      (-(x * Real.exp x * (x * (Real.exp x + 1) - 2 * (Real.exp x - 1))) /
        (Real.exp x - 1) ^ 3) x := by
  have he : Real.exp x - 1 ≠ 0 := (sub_pos.mpr (Real.one_lt_exp_iff.mpr hx)).ne'
  have h1 : HasDerivAt (fun y : ℝ => y ^ 2 * Real.exp y)
      ((2 * x + x ^ 2) * Real.exp x) x := by
    have h := (hasDerivAt_pow 2 x).mul (Real.hasDerivAt_exp x)
    convert h using 1
    norm_num
    ring
  have h2 : HasDerivAt (fun y : ℝ => (Real.exp y - 1) ^ 2)
      (2 * (Real.exp x - 1) * Real.exp x) x := by
    have h := ((Real.hasDerivAt_exp x).sub_const 1).pow 2
    convert h using 1
    norm_num
  have h := h1.div h2 (pow_ne_zero 2 he)
  convert h using 1
  · funext y
    rfl
  · field_simp
    ring

theorem einsteinCapacity_strictAntiOn : StrictAntiOn einsteinCapacity (Set.Ioi 0) := by
  apply strictAntiOn_of_deriv_neg (convex_Ioi 0)
  · exact fun x hx => (einsteinCapacity_hasDerivAt hx).continuousAt.continuousWithinAt
  · intro x hx
    rw [interior_Ioi] at hx
    have he : 0 < Real.exp x - 1 := sub_pos.mpr (Real.one_lt_exp_iff.mpr hx)
    rw [(einsteinCapacity_hasDerivAt hx).deriv]
    exact div_neg_of_neg_of_pos (neg_neg_of_pos (mul_pos (mul_pos hx (Real.exp_pos x))
      (einstein_gap_pos hx))) (pow_pos he 3)

theorem harmonicHeatCapacity_strictAntiOn_frequency {t : ℝ} (ht : 0 < t) :
    StrictAntiOn (fun omega => harmonicHeatCapacity ℏ kB omega t) (Set.Ioi 0) := by
  intro a ha b hb hab
  have ha' : (0 : ℝ) < a := ha
  have hb' : (0 : ℝ) < b := hb
  have hkt := mul_pos kB_pos ht
  dsimp only
  rw [harmonicHeatCapacity_eq_kB_mul_einsteinCapacity ha' ht,
    harmonicHeatCapacity_eq_kB_mul_einsteinCapacity hb' ht]
  refine mul_lt_mul_of_pos_left (einsteinCapacity_strictAntiOn ?_ ?_ ?_) kB_pos
  · exact div_pos (mul_pos ℏ_pos ha') hkt
  · exact div_pos (mul_pos ℏ_pos hb') hkt
  · exact div_lt_div_of_pos_right (mul_lt_mul_of_pos_left hab ℏ_pos) hkt

end OMAI.PhyslibBridge
