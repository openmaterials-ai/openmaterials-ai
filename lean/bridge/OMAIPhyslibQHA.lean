/- Catalog endpoints for the local quasiharmonic Gibbs energy and the responses derived from it. -/
module

public import OMAIPhyslibGibbsBranch
public import OMAIPhyslibModeGruneisen

/-!
# Local quasiharmonic Gibbs energy and its producers

The quasiharmonic Gibbs energy is the minimum over volume of F(T, V) + pV, where F is the
molar Helmholtz surface of the actual static-plus-harmonic Physlib ensembles. The definitions
below are the catalog producers written as functions of that Gibbs surface: the windowed
minimum itself, C_P = -T (∂²G/∂T²)_p, α_V = (∂V/∂T)_p / V with V = (∂G/∂p)_T, the isothermal
modulus V (∂²F/∂V²)_T at the selected volume, and the heat-capacity-weighted mean of supplied
mode Gruneisen parameters. The theorems identify them, on a local stable equilibrium family,
with the entropy, enthalpy derivative, expansion, curvature modulus and mode-weighted Gamma of
the same ensembles. No numerical volume scan, EOS fit, minimizer or Phonopy producer is
verified.
-/

@[expose] public section

noncomputable section
open Filter Set Constants Temperature QuantumMechanics.OneDimension
open scoped Topology BigOperators

namespace OMAI.PhyslibBridge.Response

/-- G^qha(E_tot, S, omega) of compute_qha_gibbs: the infimum over volumes V in the window I of
F(T, V) + pV, with x = (T, p). F carries the static energy, structure and frequencies. This
definition alone is not a physical proof. -/
def qhaGibbsEnergy (F : Surface) (I : Set ℝ) (x : ℝ × ℝ) : ℝ :=
  sInf ((fun w => F (x.1, w) + x.2 * w) '' I)

/-- The volume read off a Gibbs surface, V = (∂G/∂p)_T. -/
def gibbsVolume (G : ℝ × ℝ → ℝ) (x : ℝ × ℝ) : ℝ :=
  deriv (fun q => G (x.1, q)) x.2

/-- C_P^qha(G_qha) of compute_heat_capacity_p: C_P = -T (∂²G/∂T²)_p. -/
def qhaHeatCapacityP (G : ℝ × ℝ → ℝ) (x : ℝ × ℝ) : ℝ :=
  -x.1 * deriv (deriv (fun s => G (s, x.2))) x.1

/-- alpha^qha(G_qha) of compute_thermal_expansion: alpha_V = (∂V/∂T)_p / V, V = (∂G/∂p)_T. -/
def qhaThermalExpansion (G : ℝ × ℝ → ℝ) (x : ℝ × ℝ) : ℝ :=
  deriv (fun s => gibbsVolume G (s, x.2)) x.1 / gibbsVolume G x

/-- K^qha(E_tot, S, omega) of compute_bulk_modulus_qha: the isothermal modulus V (∂²F/∂V²)_T of
the Helmholtz surface at the volume selected by the windowed Gibbs energy. -/
def qhaBulkModulus (F : Surface) (I : Set ℝ) (x : ℝ × ℝ) : ℝ :=
  gibbsVolume (qhaGibbsEnergy F I) x *
    deriv (deriv (fun w => F (x.1, w))) (gibbsVolume (qhaGibbsEnergy F I) x)

/-- gamma^qha(gamma_G, omega) of contract_thermal_gruneisen: the mean of the supplied mode
parameters weighted by the actual Physlib canonical heat capacities of the supplied
oscillators. Totalized; nothing is asserted at T = 0. -/
def qhaThermalGruneisen {ι : Type*} [Fintype ι] (γ : ι → ℝ) (osc : ι → HarmonicOscillator)
    (T : Temperature) : ℝ :=
  (∑ i, γ i * (harmonicEnsemble (osc i)).heatCapacity T) /
    ∑ i, (harmonicEnsemble (osc i)).heatCapacity T

namespace GibbsBranchAt

variable {F : Surface} {D : Set (ℝ × ℝ)} {t₀ p₀ : ℝ}

/-- A unique minimizer on a window fixes the windowed Gibbs energy at the family value. -/
theorem qhaGibbsEnergy_eq_of_strictMin (B : GibbsBranchAt F D (t₀, p₀)) {J : Set ℝ} {x : ℝ × ℝ}
    (hxV : B.volume x ∈ J) (hmin : ∀ w ∈ J, w ≠ B.volume x → B.gibbs x < F (x.1, w) + x.2 * w) :
    qhaGibbsEnergy F J x = B.gibbs x := by
  apply IsLeast.csInf_eq
  refine ⟨⟨B.volume x, hxV, rfl⟩, ?_⟩
  rintro y ⟨w, hw, rfl⟩
  by_cases hwx : w = B.volume x
  · subst hwx
    exact le_rfl
  · exact (hmin w hw hwx).le

/-- Checkable window. On any open volume interval (a, b) that contains the selected volume,
lies in the domain and has F_VV(T, ·) > 0 for every temperature near T₀, the family volume is
the unique minimizer of F(T, ·) + pV for every (T, p) near the point, and the windowed Gibbs
energy over (a, b) equals the family value there. A scan certifies its own window by this
convexity. -/
theorem qhaGibbsEnergy_convex_window (B : GibbsBranchAt F D (t₀, p₀)) (hD : IsOpen D)
    (hF : ContDiffOn ℝ 2 F D) {a b : ℝ} (hJ : B.volume (t₀, p₀) ∈ Ioo a b)
    (hconv : ∀ᶠ t in 𝓝 t₀, ∀ w ∈ Ioo a b, (t, w) ∈ D ∧ 0 < FVV F (t, w)) :
    (∀ᶠ x in 𝓝 (t₀, p₀), B.volume x ∈ Ioo a b ∧
        ∀ w ∈ Ioo a b, w ≠ B.volume x → B.gibbs x < F (x.1, w) + x.2 * w) ∧
      qhaGibbsEnergy F (Ioo a b) =ᶠ[𝓝 (t₀, p₀)] B.gibbs := by
  have hcV : ContinuousAt B.volume (t₀, p₀) := B.differentiable.self_of_nhds.continuousAt
  have hV : ∀ᶠ x in 𝓝 (t₀, p₀), B.volume x ∈ Ioo a b := hcV.eventually (isOpen_Ioo.mem_nhds hJ)
  have hT : ∀ᶠ x in 𝓝 (t₀, p₀), ∀ w ∈ Ioo a b, (x.1, w) ∈ D ∧ 0 < FVV F (x.1, w) :=
    (continuous_fst.tendsto (t₀, p₀)).eventually hconv
  have hmin : ∀ᶠ x in 𝓝 (t₀, p₀), B.volume x ∈ Ioo a b ∧
      ∀ w ∈ Ioo a b, w ≠ B.volume x → B.gibbs x < F (x.1, w) + x.2 * w := by
    filter_upwards [hV, hT, B.equilibrium] with x hxV hxT hxeq
    exact ⟨hxV, strictMin_of_convex_interval hD hF hxT hxV hxeq⟩
  refine ⟨hmin, ?_⟩
  filter_upwards [hmin] with x hx
  exact B.qhaGibbsEnergy_eq_of_strictMin hx.1 hx.2

/-- Every sufficiently narrow window around the base volume selects the family: the family
volume is the unique minimizer in the window and the windowed Gibbs energy equals its value. -/
theorem qhaGibbsEnergy_selects (B : GibbsBranchAt F D (t₀, p₀)) (hD : IsOpen D)
    (hF : ContDiffOn ℝ 2 F D) :
    ∃ ε₀ > 0, ∀ ε, 0 < ε → ε ≤ ε₀ →
      (∀ᶠ x in 𝓝 (t₀, p₀),
        B.volume x ∈ Ioo (B.volume (t₀, p₀) - ε) (B.volume (t₀, p₀) + ε) ∧
        ∀ w ∈ Ioo (B.volume (t₀, p₀) - ε) (B.volume (t₀, p₀) + ε), w ≠ B.volume x →
          B.gibbs x < F (x.1, w) + x.2 * w) ∧
      qhaGibbsEnergy F (Ioo (B.volume (t₀, p₀) - ε) (B.volume (t₀, p₀) + ε))
        =ᶠ[𝓝 (t₀, p₀)] B.gibbs := by
  obtain ⟨ε₀, hε₀, h⟩ := B.window_strictMin hD hF
  refine ⟨ε₀, hε₀, fun ε hε hεle => ⟨h ε hε hεle, ?_⟩⟩
  filter_upwards [h ε hε hεle] with x hx
  exact B.qhaGibbsEnergy_eq_of_strictMin hx.1 hx.2

theorem eventually_gibbsVolume (B : GibbsBranchAt F D (t₀, p₀)) (hD : IsOpen D)
    (hF : ContDiffOn ℝ 2 F D) {G : ℝ × ℝ → ℝ} (hG : G =ᶠ[𝓝 (t₀, p₀)] B.gibbs) :
    ∀ᶠ x in 𝓝 (t₀, p₀), gibbsVolume G x = B.volume x := by
  filter_upwards [hG.eventuallyEq_nhds, B.gibbs_pressure_hasDerivAt hD hF] with x hx hd
  obtain ⟨t, p⟩ := x
  have hcomp : (fun q => G (t, q)) =ᶠ[𝓝 p] (fun q => B.gibbs (t, q)) :=
    hx.comp_tendsto ((continuous_const.prodMk continuous_id).tendsto p)
  exact (hd.congr_of_eventuallyEq hcomp).deriv

theorem eventually_temperature_hasDerivAt (B : GibbsBranchAt F D (t₀, p₀)) (hD : IsOpen D)
    (hF : ContDiffOn ℝ 2 F D) {G : ℝ × ℝ → ℝ} (hG : G =ᶠ[𝓝 (t₀, p₀)] B.gibbs) :
    ∀ᶠ x in 𝓝 (t₀, p₀), HasDerivAt (fun s => G (s, x.2)) (FT F (x.1, B.volume x)) x.1 := by
  filter_upwards [hG.eventuallyEq_nhds, B.gibbs_temperature_hasDerivAt hD hF] with x hx hd
  obtain ⟨t, p⟩ := x
  have hcomp : (fun s => G (s, p)) =ᶠ[𝓝 t] (fun s => B.gibbs (s, p)) :=
    hx.comp_tendsto ((continuous_id.prodMk continuous_const).tendsto t)
  exact hd.congr_of_eventuallyEq hcomp

/-- C_P = -T (∂²G/∂T²)_p equals the enthalpy derivative along the constant-pressure path. -/
theorem qhaHeatCapacityP_eq_cp (B : GibbsBranchAt F D (t₀, p₀)) (hD : IsOpen D)
    (hF : ContDiffOn ℝ 2 F D) {G : ℝ × ℝ → ℝ} (hG : G =ᶠ[𝓝 (t₀, p₀)] B.gibbs) :
    qhaHeatCapacityP G (t₀, p₀) = cp F p₀ B.isobar.volume t₀ := by
  have hev : deriv (fun s => G (s, p₀)) =ᶠ[𝓝 t₀] fun s => FT F (s, B.volume (s, p₀)) := by
    filter_upwards [tendsto_isobar.eventually (B.eventually_temperature_hasDerivAt hD hF hG)]
      with s hs
    exact hs.deriv
  have h2 := (B.isobar_FT_hasDerivAt hD hF).congr_of_eventuallyEq hev
  have hFx := hF.contDiffAt (hD.mem_nhds B.in_domain.self_of_nhds)
  change -t₀ * deriv (deriv (fun s => G (s, p₀))) t₀ = _
  rw [h2.deriv, B.isobar.cp_eq hFx]
  simp only [cv, isobar_volume]
  ring

/-- alpha_V = (∂V/∂T)_p / V from the Gibbs surface equals the expansion of the family. -/
theorem qhaThermalExpansion_eq_expansion (B : GibbsBranchAt F D (t₀, p₀)) (hD : IsOpen D)
    (hF : ContDiffOn ℝ 2 F D) {G : ℝ × ℝ → ℝ} (hG : G =ᶠ[𝓝 (t₀, p₀)] B.gibbs) :
    qhaThermalExpansion G (t₀, p₀) = expansion B.isobar.volume t₀ := by
  have hev : (fun s => gibbsVolume G (s, p₀)) =ᶠ[𝓝 t₀] fun s => B.volume (s, p₀) :=
    tendsto_isobar.eventually (B.eventually_gibbsVolume hD hF hG)
  have h0 : gibbsVolume G (t₀, p₀) = B.volume (t₀, p₀) :=
    (B.eventually_gibbsVolume hD hF hG).self_of_nhds
  change deriv (fun s => gibbsVolume G (s, p₀)) t₀ / gibbsVolume G (t₀, p₀) =
    deriv (fun s => B.volume (s, p₀)) t₀ / B.volume (t₀, p₀)
  rw [hev.deriv_eq, h0]

/-- (∂V/∂T)_p read off the Gibbs surface is the slope of the constant-pressure path. -/
theorem deriv_gibbsVolume_isobar (B : GibbsBranchAt F D (t₀, p₀)) (hD : IsOpen D)
    (hF : ContDiffOn ℝ 2 F D) {G : ℝ × ℝ → ℝ} (hG : G =ᶠ[𝓝 (t₀, p₀)] B.gibbs) :
    deriv (fun s => gibbsVolume G (s, p₀)) t₀ = B.isobar.slope := by
  have hev : (fun s => gibbsVolume G (s, p₀)) =ᶠ[𝓝 t₀] fun s => B.volume (s, p₀) :=
    tendsto_isobar.eventually (B.eventually_gibbsVolume hD hF hG)
  rw [hev.deriv_eq]
  exact B.isobar_hasDerivAt.deriv

/-- The curvature modulus at the selected volume is the family's isothermal modulus. -/
theorem qhaBulkModulus_eq_bulk (B : GibbsBranchAt F D (t₀, p₀)) (hD : IsOpen D)
    (hF : ContDiffOn ℝ 2 F D) {I : Set ℝ}
    (hI : qhaGibbsEnergy F I =ᶠ[𝓝 (t₀, p₀)] B.gibbs) :
    qhaBulkModulus F I (t₀, p₀) = bulk F (t₀, B.volume (t₀, p₀)) := by
  have h0 : gibbsVolume (qhaGibbsEnergy F I) (t₀, p₀) = B.volume (t₀, p₀) :=
    (B.eventually_gibbsVolume hD hF hI).self_of_nhds
  change gibbsVolume (qhaGibbsEnergy F I) (t₀, p₀) *
      deriv (deriv (fun w => F (t₀, w))) (gibbsVolume (qhaGibbsEnergy F I) (t₀, p₀)) = _
  rw [h0, ← FVV_eq_deriv_deriv_volume hD hF B.in_domain.self_of_nhds]
  rfl

/-- The same modulus from the Gibbs surface alone: K_T = -V / (∂V/∂p)_T. -/
theorem bulk_eq_gibbs_compressibility (B : GibbsBranchAt F D (t₀, p₀)) (hD : IsOpen D)
    (hF : ContDiffOn ℝ 2 F D) {G : ℝ × ℝ → ℝ} (hG : G =ᶠ[𝓝 (t₀, p₀)] B.gibbs) :
    -gibbsVolume G (t₀, p₀) / deriv (fun q => gibbsVolume G (t₀, q)) p₀ =
      bulk F (t₀, B.volume (t₀, p₀)) := by
  have hev : (fun q => gibbsVolume G (t₀, q)) =ᶠ[𝓝 p₀] fun q => B.volume (t₀, q) :=
    tendsto_isotherm.eventually (B.eventually_gibbsVolume hD hF hG)
  rw [hev.deriv_eq, (B.isotherm_hasDerivAt hD hF).deriv,
    (B.eventually_gibbsVolume hD hF hG).self_of_nhds]
  have hne := B.stable.ne'
  unfold bulk
  field_simp

end GibbsBranchAt

/-- The supplied-parameter contraction is a weighted mean: for T > 0 it lies between any lower
and upper bounds of the mode parameters. -/
theorem qhaThermalGruneisen_mem_Icc {ι : Type*} [Fintype ι] [Nonempty ι] (γ : ι → ℝ)
    (osc : ι → HarmonicOscillator) (T : Temperature) (hT : 0 < T.val) {a b : ℝ}
    (ha : ∀ i, a ≤ γ i) (hb : ∀ i, γ i ≤ b) :
    a ≤ qhaThermalGruneisen γ osc T ∧ qhaThermalGruneisen γ osc T ≤ b := by
  have hTr : 0 < (T : ℝ) := by
    change 0 < (T.val : ℝ)
    exact_mod_cast hT
  have hw : ∀ i, 0 < (harmonicEnsemble (osc i)).heatCapacity T := fun i => by
    rw [harmonic_heatCapacity_eq_omai (osc i) T hT]
    exact harmonicHeatCapacity_pos ℏ_pos kB_pos (osc i).hω hTr
  have hS : 0 < ∑ i, (harmonicEnsemble (osc i)).heatCapacity T :=
    Finset.sum_pos (fun i _ => hw i) Finset.univ_nonempty
  unfold qhaThermalGruneisen
  constructor
  · rw [le_div_iff₀ hS, Finset.mul_sum]
    exact Finset.sum_le_sum fun i _ => mul_le_mul_of_nonneg_right (ha i) (hw i).le
  · rw [div_le_iff₀ hS, Finset.mul_sum]
    exact Finset.sum_le_sum fun i _ => mul_le_mul_of_nonneg_right (hb i) (hw i).le

/-- On the model's own mode parameters and oscillators, the contraction is the mode-weighted
Gamma of the volume family. -/
theorem qhaThermalGruneisen_eq_weightedGruneisen (M : HarmonicVolumeModel) (T : Temperature)
    (v : ℝ) (hv : v ∈ M.J) :
    qhaThermalGruneisen
        (fun i : Fin M.reference.qCount × Fin (3 * M.reference.atomCount) =>
          M.modeGruneisen i.1 i.2 v)
        (fun i => (M.gridAt v hv).oscillator i.1 i.2) T =
      M.weightedGruneisen T v hv := by
  unfold qhaThermalGruneisen HarmonicVolumeModel.weightedGruneisen
  rw [Fintype.sum_prod_type, Fintype.sum_prod_type]
  rfl

section Model

variable (M : HarmonicVolumeModel) (T : Temperature) (p : ℝ)

theorem temperature_pos_of_branch {M : HarmonicVolumeModel} {T : Temperature} {p : ℝ}
    (B : GibbsBranchAt M.freeEnergy M.domain ((T : ℝ), p)) : 0 < T.val := by
  have h : 0 < ((T.val : NNReal) : ℝ) := B.in_domain.self_of_nhds.1
  exact_mod_cast h

/-- compute_qha_gibbs, minimization: on every sufficiently narrow volume window around the base
volume, the family volume is the unique minimizer of F(T, V) + pV for every (T, p) near the base
point, and the windowed Gibbs energy equals F(T, V(T, p)) + pV(T, p). -/
theorem harmonic_static_qhaGibbs_window
    (B : GibbsBranchAt M.freeEnergy M.domain ((T : ℝ), p)) :
    ∃ ε₀ > 0, ∀ ε, 0 < ε → ε ≤ ε₀ →
      (∀ᶠ x in 𝓝 ((T : ℝ), p),
        B.volume x ∈ Ioo (B.volume ((T : ℝ), p) - ε) (B.volume ((T : ℝ), p) + ε) ∧
        ∀ w ∈ Ioo (B.volume ((T : ℝ), p) - ε) (B.volume ((T : ℝ), p) + ε), w ≠ B.volume x →
          M.freeEnergy (x.1, B.volume x) + x.2 * B.volume x < M.freeEnergy (x.1, w) + x.2 * w) ∧
      qhaGibbsEnergy M.freeEnergy
          (Ioo (B.volume ((T : ℝ), p) - ε) (B.volume ((T : ℝ), p) + ε))
        =ᶠ[𝓝 ((T : ℝ), p)] B.gibbs :=
  B.qhaGibbsEnergy_selects M.domain_isOpen M.freeEnergy_contDiffOn

/-- compute_qha_gibbs, checkable window: on any open volume interval (a, b) containing the
selected volume, inside the model domain and with F_VV(T, ·) > 0 for every temperature near T,
the family volume is the unique minimizer of F(T, V) + pV for every (T, p) near the point and the
windowed Gibbs energy over (a, b) equals F(T, V(T, p)) + pV(T, p) there. -/
theorem harmonic_static_qhaGibbs_convex_window
    (B : GibbsBranchAt M.freeEnergy M.domain ((T : ℝ), p)) {a b : ℝ}
    (hJ : B.volume ((T : ℝ), p) ∈ Ioo a b)
    (hconv : ∀ᶠ t in 𝓝 (T : ℝ), ∀ w ∈ Ioo a b,
      (t, w) ∈ M.domain ∧ 0 < FVV M.freeEnergy (t, w)) :
    (∀ᶠ x in 𝓝 ((T : ℝ), p), B.volume x ∈ Ioo a b ∧
        ∀ w ∈ Ioo a b, w ≠ B.volume x →
          M.freeEnergy (x.1, B.volume x) + x.2 * B.volume x < M.freeEnergy (x.1, w) + x.2 * w) ∧
      qhaGibbsEnergy M.freeEnergy (Ioo a b) =ᶠ[𝓝 ((T : ℝ), p)] B.gibbs :=
  B.qhaGibbsEnergy_convex_window M.domain_isOpen M.freeEnergy_contDiffOn hJ hconv

/-- compute_qha_gibbs, temperature envelope: (∂G/∂T)_p is -(N_A/N_q) times the Physlib
thermodynamic entropy of the static-plus-harmonic ensemble at the selected volume. -/
theorem harmonic_static_qhaGibbs_entropy
    (B : GibbsBranchAt M.freeEnergy M.domain ((T : ℝ), p)) {I : Set ℝ}
    (hI : qhaGibbsEnergy M.freeEnergy I =ᶠ[𝓝 ((T : ℝ), p)] B.gibbs) :
    deriv (fun s => qhaGibbsEnergy M.freeEnergy I (s, p)) (T : ℝ) =
      -((M.reference.avogadro / (M.reference.qCount : ℝ)) *
        (M.ensembleAt (B.volume ((T : ℝ), p) / M.reference.avogadro)
          B.in_domain.self_of_nhds.2).thermodynamicEntropy T) := by
  have hd := (B.eventually_temperature_hasDerivAt M.domain_isOpen M.freeEnergy_contDiffOn
    hI).self_of_nhds
  rw [hd.deriv, M.FT_eq_neg_entropy B.in_domain.self_of_nhds,
    M.entropy_eq_actual T (temperature_pos_of_branch B) _ B.in_domain.self_of_nhds.2]

/-- compute_qha_gibbs, pressure envelope: (∂G/∂p)_T is the selected molar volume. -/
theorem harmonic_static_qhaGibbs_volume
    (B : GibbsBranchAt M.freeEnergy M.domain ((T : ℝ), p)) {I : Set ℝ}
    (hI : qhaGibbsEnergy M.freeEnergy I =ᶠ[𝓝 ((T : ℝ), p)] B.gibbs) :
    gibbsVolume (qhaGibbsEnergy M.freeEnergy I) ((T : ℝ), p) = B.volume ((T : ℝ), p) :=
  (B.eventually_gibbsVolume M.domain_isOpen M.freeEnergy_contDiffOn hI).self_of_nhds

/-- compute_thermal_expansion: the expansion read off the Gibbs surface is the expansion of the
constant-pressure path, alpha_V = -F_TV / (V F_VV). -/
theorem harmonic_static_qhaThermalExpansion_eq_omai
    (B : GibbsBranchAt M.freeEnergy M.domain ((T : ℝ), p)) {I : Set ℝ}
    (hI : qhaGibbsEnergy M.freeEnergy I =ᶠ[𝓝 ((T : ℝ), p)] B.gibbs) :
    qhaThermalExpansion (qhaGibbsEnergy M.freeEnergy I) ((T : ℝ), p) =
        expansion B.isobar.volume (T : ℝ) ∧
      qhaThermalExpansion (qhaGibbsEnergy M.freeEnergy I) ((T : ℝ), p) =
        -mixedTV M.freeEnergy ((T : ℝ), B.volume ((T : ℝ), p)) /
          (B.volume ((T : ℝ), p) * FVV M.freeEnergy ((T : ℝ), B.volume ((T : ℝ), p))) := by
  have hα := B.qhaThermalExpansion_eq_expansion M.domain_isOpen M.freeEnergy_contDiffOn hI
  refine ⟨hα, ?_⟩
  have hFx := M.freeEnergy_contDiffAt B.in_domain.self_of_nhds
  have hEq := B.isobar.equilibrium_derivative hFx
  have hV := (M.domain_positive B.in_domain.self_of_nhds).2
  have hK := B.stable.ne'
  rw [hα]
  unfold expansion
  rw [B.isobar.volume_deriv.deriv]
  change B.isobar.slope / B.volume ((T : ℝ), p) = _
  have hs : B.isobar.slope = -mixedTV M.freeEnergy ((T : ℝ), B.volume ((T : ℝ), p)) /
      FVV M.freeEnergy ((T : ℝ), B.volume ((T : ℝ), p)) := by
    change mixedTV M.freeEnergy ((T : ℝ), B.volume ((T : ℝ), p)) +
      B.isobar.slope * FVV M.freeEnergy ((T : ℝ), B.volume ((T : ℝ), p)) = 0 at hEq
    field_simp
    linarith
  rw [hs]
  field_simp

/-- compute_thermal_expansion, sign: the Gibbs-surface expansion is positive exactly when the
mode-weighted Gamma of the same family is positive. -/
theorem harmonic_static_qhaThermalExpansion_pos_iff
    (B : GibbsBranchAt M.freeEnergy M.domain ((T : ℝ), p)) {I : Set ℝ}
    (hI : qhaGibbsEnergy M.freeEnergy I =ᶠ[𝓝 ((T : ℝ), p)] B.gibbs) :
    0 < qhaThermalExpansion (qhaGibbsEnergy M.freeEnergy I) ((T : ℝ), p) ↔
      0 < M.weightedGruneisen T (B.volume ((T : ℝ), p) / M.reference.avogadro)
        B.in_domain.self_of_nhds.2 := by
  rw [(harmonic_static_qhaThermalExpansion_eq_omai M T p B hI).1]
  exact M.expansion_pos_iff_weightedGruneisen_pos p T B.isobar

/-- compute_bulk_modulus_qha: the curvature modulus V (∂²F/∂V²)_T at the volume (∂G/∂p)_T
equals -V / (∂V/∂p)_T read off the Gibbs surface alone. -/
theorem harmonic_static_qhaBulkModulus_eq_omai
    (B : GibbsBranchAt M.freeEnergy M.domain ((T : ℝ), p)) {I : Set ℝ}
    (hI : qhaGibbsEnergy M.freeEnergy I =ᶠ[𝓝 ((T : ℝ), p)] B.gibbs) :
    qhaBulkModulus M.freeEnergy I ((T : ℝ), p) =
      -gibbsVolume (qhaGibbsEnergy M.freeEnergy I) ((T : ℝ), p) /
        deriv (fun q => gibbsVolume (qhaGibbsEnergy M.freeEnergy I) ((T : ℝ), q)) p := by
  rw [B.qhaBulkModulus_eq_bulk M.domain_isOpen M.freeEnergy_contDiffOn hI,
    B.bulk_eq_gibbs_compressibility M.domain_isOpen M.freeEnergy_contDiffOn hI]

/-- compute_heat_capacity_p: C_P = -T (∂²G/∂T²)_p equals the actual Physlib enthalpy
derivative along the constant-pressure path and, with expansion and modulus read off the same
Gibbs surface, C_V + T V alpha_V² K_T. -/
theorem harmonic_static_qhaHeatCapacityP_eq_omai
    (B : GibbsBranchAt M.freeEnergy M.domain ((T : ℝ), p)) {I : Set ℝ}
    (hI : qhaGibbsEnergy M.freeEnergy I =ᶠ[𝓝 ((T : ℝ), p)] B.gibbs) :
    qhaHeatCapacityP (qhaGibbsEnergy M.freeEnergy I) ((T : ℝ), p) =
        M.actualCp p B.isobar.volume (T : ℝ) ∧
      qhaHeatCapacityP (qhaGibbsEnergy M.freeEnergy I) ((T : ℝ), p) =
        M.cv ((T : ℝ), B.volume ((T : ℝ), p)) + (T : ℝ) * B.volume ((T : ℝ), p) *
          qhaThermalExpansion (qhaGibbsEnergy M.freeEnergy I) ((T : ℝ), p) ^ 2 *
          qhaBulkModulus M.freeEnergy I ((T : ℝ), p) := by
  have hC := B.qhaHeatCapacityP_eq_cp M.domain_isOpen M.freeEnergy_contDiffOn hI
  have hA := (M.actualCp_eq_responseCp p (T : ℝ) B.isobar).symm
  refine ⟨hC.trans hA, ?_⟩
  have hgap := M.actualCp_sub_cv p (T : ℝ) B.isobar
  rw [(harmonic_static_qhaThermalExpansion_eq_omai M T p B hI).1,
    B.qhaBulkModulus_eq_bulk M.domain_isOpen M.freeEnergy_contDiffOn hI, hC.trans hA]
  change M.actualCp p B.isobar.volume (T : ℝ) - M.cv ((T : ℝ), B.volume ((T : ℝ), p)) =
    (T : ℝ) * B.volume ((T : ℝ), p) * expansion B.isobar.volume (T : ℝ) ^ 2 *
      bulk M.freeEnergy ((T : ℝ), B.volume ((T : ℝ), p)) at hgap
  linarith

/-- compute_heat_capacity_p, the polyfit route: C_P = -T (∂²G/∂T²)_p equals
C_V + T (∂V/∂T)_p (∂S/∂V)_T at the selected volume, with (∂V/∂T)_p read off the Gibbs surface and
S the molar entropy of the same ensembles; the Maxwell relation gives
(∂S/∂V)_T = -F_TV = alpha_V K_T. -/
theorem harmonic_static_qhaHeatCapacityP_eq_entropy_slope
    (B : GibbsBranchAt M.freeEnergy M.domain ((T : ℝ), p)) {I : Set ℝ}
    (hI : qhaGibbsEnergy M.freeEnergy I =ᶠ[𝓝 ((T : ℝ), p)] B.gibbs) :
    qhaHeatCapacityP (qhaGibbsEnergy M.freeEnergy I) ((T : ℝ), p) =
        M.cv ((T : ℝ), B.volume ((T : ℝ), p)) + (T : ℝ) *
          deriv (fun s => gibbsVolume (qhaGibbsEnergy M.freeEnergy I) (s, p)) (T : ℝ) *
          deriv (fun w => M.entropy ((T : ℝ), w)) (B.volume ((T : ℝ), p)) ∧
      deriv (fun w => M.entropy ((T : ℝ), w)) (B.volume ((T : ℝ), p)) =
        -mixedTV M.freeEnergy ((T : ℝ), B.volume ((T : ℝ), p)) ∧
      deriv (fun w => M.entropy ((T : ℝ), w)) (B.volume ((T : ℝ), p)) =
        qhaThermalExpansion (qhaGibbsEnergy M.freeEnergy I) ((T : ℝ), p) *
          qhaBulkModulus M.freeEnergy I ((T : ℝ), p) := by
  have hx := B.in_domain.self_of_nhds
  have hFx := M.freeEnergy_contDiffAt hx
  -- Maxwell relation: S = -F_T near the selected volume, so (∂S/∂V)_T = -F_TV.
  have hS : HasDerivAt (fun w => M.entropy ((T : ℝ), w))
      (-mixedTV M.freeEnergy ((T : ℝ), B.volume ((T : ℝ), p))) (B.volume ((T : ℝ), p)) := by
    have hFT := (partial_volume_hasDerivAt hFx (1, 0)).neg
    rw [mixed_symmetric hFx] at hFT
    refine hFT.congr_of_eventuallyEq ?_
    have hopen : IsOpen {w : ℝ | ((T : ℝ), w) ∈ M.domain} :=
      M.domain_isOpen.preimage (continuous_const.prodMk continuous_id)
    filter_upwards [hopen.mem_nhds hx] with w hw
    have h := M.FT_eq_neg_entropy hw
    simp only [FT] at h
    simp only [Pi.neg_apply]
    linarith
  have hSd := hS.deriv
  have hV := (M.domain_positive hx).2
  have hK := B.stable.ne'
  have hαK : qhaThermalExpansion (qhaGibbsEnergy M.freeEnergy I) ((T : ℝ), p) *
      qhaBulkModulus M.freeEnergy I ((T : ℝ), p) =
        -mixedTV M.freeEnergy ((T : ℝ), B.volume ((T : ℝ), p)) := by
    rw [(harmonic_static_qhaThermalExpansion_eq_omai M T p B hI).2,
      B.qhaBulkModulus_eq_bulk M.domain_isOpen M.freeEnergy_contDiffOn hI]
    unfold bulk
    field_simp
  refine ⟨?_, hSd, hSd.trans hαK.symm⟩
  rw [B.qhaHeatCapacityP_eq_cp M.domain_isOpen M.freeEnergy_contDiffOn hI, B.isobar.cp_eq hFx,
    B.deriv_gibbsVolume_isobar M.domain_isOpen M.freeEnergy_contDiffOn hI, hSd,
    M.cv_eq_responseCv hx]
  simp only [GibbsBranchAt.isobar_volume]
  ring

/-- compute_heat_capacity_p, strictness: C_P exceeds C_V exactly when the Gibbs-surface
expansion is nonzero; they coincide when it vanishes. -/
theorem harmonic_static_qhaHeatCapacityP_gt_iff
    (B : GibbsBranchAt M.freeEnergy M.domain ((T : ℝ), p)) {I : Set ℝ}
    (hI : qhaGibbsEnergy M.freeEnergy I =ᶠ[𝓝 ((T : ℝ), p)] B.gibbs) :
    M.cv ((T : ℝ), B.volume ((T : ℝ), p)) <
        qhaHeatCapacityP (qhaGibbsEnergy M.freeEnergy I) ((T : ℝ), p) ↔
      qhaThermalExpansion (qhaGibbsEnergy M.freeEnergy I) ((T : ℝ), p) ≠ 0 := by
  rw [(harmonic_static_qhaHeatCapacityP_eq_omai M T p B hI).2]
  have hT : 0 < (T : ℝ) := B.in_domain.self_of_nhds.1
  have hV := (M.domain_positive B.in_domain.self_of_nhds).2
  have hK : 0 < qhaBulkModulus M.freeEnergy I ((T : ℝ), p) := by
    rw [B.qhaBulkModulus_eq_bulk M.domain_isOpen M.freeEnergy_contDiffOn hI]
    exact mul_pos hV B.stable
  constructor
  · intro h hα
    rw [hα] at h
    simp at h
  · intro hα
    have : 0 < (T : ℝ) * B.volume ((T : ℝ), p) *
        qhaThermalExpansion (qhaGibbsEnergy M.freeEnergy I) ((T : ℝ), p) ^ 2 *
        qhaBulkModulus M.freeEnergy I ((T : ℝ), p) := by
      have := pow_pos (abs_pos.mpr hα) 2
      rw [sq_abs] at this
      positivity
    linarith

/-- contract_thermal_gruneisen: applied to the derivative-defined mode parameters and the
oscillators of the same volume family at the selected cell volume, the heat-capacity-weighted
contraction equals alpha_V K_T / C_V^vol with alpha_V and K_T read off the windowed Gibbs
energy. -/
theorem harmonic_static_qhaThermalGruneisen_eq_omai
    (B : GibbsBranchAt M.freeEnergy M.domain ((T : ℝ), p)) {I : Set ℝ}
    (hI : qhaGibbsEnergy M.freeEnergy I =ᶠ[𝓝 ((T : ℝ), p)] B.gibbs) :
    qhaThermalGruneisen
        (fun i : Fin M.reference.qCount × Fin (3 * M.reference.atomCount) =>
          M.modeGruneisen i.1 i.2 (B.volume ((T : ℝ), p) / M.reference.avogadro))
        (fun i => (M.gridAt (B.volume ((T : ℝ), p) / M.reference.avogadro)
          B.in_domain.self_of_nhds.2).oscillator i.1 i.2) T =
      qhaThermalExpansion (qhaGibbsEnergy M.freeEnergy I) ((T : ℝ), p) *
          qhaBulkModulus M.freeEnergy I ((T : ℝ), p) /
        harmonicVolumetricHeatCapacity
          (M.gridAt (B.volume ((T : ℝ), p) / M.reference.avogadro) B.in_domain.self_of_nhds.2)
          (M.primitiveCellVolumeAt (B.volume ((T : ℝ), p) / M.reference.avogadro)
            B.in_domain.self_of_nhds.2) T := by
  rw [qhaThermalGruneisen_eq_weightedGruneisen,
    (harmonic_static_qhaThermalExpansion_eq_omai M T p B hI).1,
    B.qhaBulkModulus_eq_bulk M.domain_isOpen M.freeEnergy_contDiffOn hI]
  have hC := M.volumetricCv_pos T _ B.in_domain.self_of_nhds.2 (temperature_pos_of_branch B)
  have hαK := M.expansion_mul_bulk_eq_weightedGruneisen_mul_volumetricCv p T B.isobar
  change expansion B.isobar.volume (T : ℝ) * bulk M.freeEnergy ((T : ℝ), B.volume ((T : ℝ), p)) =
    M.weightedGruneisen T (B.volume ((T : ℝ), p) / M.reference.avogadro)
        B.in_domain.self_of_nhds.2 *
      harmonicVolumetricHeatCapacity
        (M.gridAt (B.volume ((T : ℝ), p) / M.reference.avogadro) B.in_domain.self_of_nhds.2)
        (M.primitiveCellVolumeAt (B.volume ((T : ℝ), p) / M.reference.avogadro)
          B.in_domain.self_of_nhds.2) T at hαK
  rw [hαK, mul_div_assoc, div_self hC.ne', mul_one]

end Model

end OMAI.PhyslibBridge.Response
