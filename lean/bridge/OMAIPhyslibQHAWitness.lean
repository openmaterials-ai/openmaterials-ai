module

public import OMAIPhyslibQHA
public import OMAIPhyslibGruneisenWitness

/-!
# Exact witnesses for the local quasiharmonic producers

The signed-rate families of the thermal Gruneisen witness have a stable stationary point at
(T, V) = (1 K, A) and p = 0, so the implicit-function theorem gives a two-parameter
equilibrium family through it. On every narrow volume window around A the Gibbs-surface
producers take exact signs: positive or negative expansion, C_P strictly above C_V, and a
contracted Gamma strictly between 1 and 2 for the positive rates and negative for the negative
rates. A constant-frequency control has zero expansion, C_P = C_V and zero
Gamma. These are exact model examples, not fitted materials or numerical volume scans.
-/

@[expose] public section

noncomputable section

open Filter Set Constants Temperature
open scoped Topology

namespace OMAI.PhyslibBridge.QHAWitness

open OMAI.PhyslibBridge.Response OMAI.PhyslibBridge.GruneisenWitness

/-- A two-parameter equilibrium family through (1 K, p = 0, V = A) for every signed rate
vector, from the implicit-function theorem. -/
theorem rate_gibbsBranch (r : Fin 3 → ℝ) (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n) :
    ∃ B : GibbsBranchAt (rateModel r A hA n hn).freeEnergy (rateModel r A hA n hn).domain
        ((witnessTemperature : ℝ), 0),
      B.volume ((witnessTemperature : ℝ), 0) = A :=
  exists_gibbsBranchAt _ _ _ A 0 (rateModel r A hA n hn).domain_isOpen
    (rateModel r A hA n hn).freeEnergy_contDiffOn
    (by rw [witnessTemperature_toReal]; exact rate_domain_reference r A hA n hn)
    (by rw [witnessTemperature_toReal, add_zero]; exact rate_FV_reference r A hA n hn)
    (by rw [witnessTemperature_toReal]; exact rate_curvature_pos r A hA n hn)

/-- Every narrow window around A selects that family. -/
theorem rate_window (r : Fin 3 → ℝ) (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n) :
    ∃ B : GibbsBranchAt (rateModel r A hA n hn).freeEnergy (rateModel r A hA n hn).domain
        ((witnessTemperature : ℝ), 0),
      B.volume ((witnessTemperature : ℝ), 0) = A ∧ ∃ ε₀ > 0, ∀ ε, 0 < ε → ε ≤ ε₀ →
        qhaGibbsEnergy (rateModel r A hA n hn).freeEnergy (Ioo (A - ε) (A + ε))
          =ᶠ[𝓝 ((witnessTemperature : ℝ), 0)] B.gibbs := by
  obtain ⟨B, hB⟩ := rate_gibbsBranch r A hA n hn
  obtain ⟨ε₀, hε₀, hsel⟩ := harmonic_static_qhaGibbs_window (rateModel r A hA n hn)
    witnessTemperature 0 B
  refine ⟨B, hB, ε₀, hε₀, fun ε hε hεle => ?_⟩
  have h := (hsel ε hε hεle).2
  rw [hB] at h
  exact h

theorem rate_weightedGruneisen_at_branch (r : Fin 3 → ℝ) (A : ℝ) (hA : 0 < A) (n : ℕ)
    (hn : 0 < n)
    (B : GibbsBranchAt (rateModel r A hA n hn).freeEnergy (rateModel r A hA n hn).domain
      ((witnessTemperature : ℝ), 0))
    (hB : B.volume ((witnessTemperature : ℝ), 0) = A) :
    (rateModel r A hA n hn).weightedGruneisen witnessTemperature
        (B.volume ((witnessTemperature : ℝ), 0) / A) B.in_domain.self_of_nhds.2 =
      (rateModel r A hA n hn).weightedGruneisen witnessTemperature 1 (one_mem_J r A hA n hn) :=
  (rateModel r A hA n hn).weightedGruneisen_congr witnessTemperature
    (by rw [hB]; exact div_self hA.ne') _ _

/-- Positive rates: on every narrow window the Gibbs-surface expansion is positive, C_P exceeds
C_V strictly, and the contracted Gamma lies strictly between 1 and 2. -/
theorem positive_qha_witness (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n) :
    ∃ ε₀ > 0, ∀ ε, 0 < ε → ε ≤ ε₀ →
      0 < qhaThermalExpansion
          (qhaGibbsEnergy (rateModel positiveRates A hA n hn).freeEnergy (Ioo (A - ε) (A + ε)))
          ((witnessTemperature : ℝ), 0) ∧
      (rateModel positiveRates A hA n hn).cv ((witnessTemperature : ℝ), A) <
        qhaHeatCapacityP
          (qhaGibbsEnergy (rateModel positiveRates A hA n hn).freeEnergy (Ioo (A - ε) (A + ε)))
          ((witnessTemperature : ℝ), 0) ∧
      1 < qhaThermalGruneisen
          (fun i : Fin n × Fin 3 => (rateModel positiveRates A hA n hn).modeGruneisen i.1 i.2 1)
          (fun i => ((rateModel positiveRates A hA n hn).gridAt 1
            (one_mem_J positiveRates A hA n hn)).oscillator i.1 i.2) witnessTemperature ∧
      qhaThermalGruneisen
          (fun i : Fin n × Fin 3 => (rateModel positiveRates A hA n hn).modeGruneisen i.1 i.2 1)
          (fun i => ((rateModel positiveRates A hA n hn).gridAt 1
            (one_mem_J positiveRates A hA n hn)).oscillator i.1 i.2) witnessTemperature < 2 := by
  obtain ⟨B, hB, ε₀, hε₀, hsel⟩ := rate_window positiveRates A hA n hn
  refine ⟨ε₀, hε₀, fun ε hε hεle => ?_⟩
  have hI := hsel ε hε hεle
  have hΓ := rate_weightedGruneisen_at_branch positiveRates A hA n hn B hB
  obtain ⟨h1, h2⟩ := positive_weightedGruneisen_bounds A hA n hn
  have hα : 0 < qhaThermalExpansion
      (qhaGibbsEnergy (rateModel positiveRates A hA n hn).freeEnergy (Ioo (A - ε) (A + ε)))
      ((witnessTemperature : ℝ), 0) := by
    rw [harmonic_static_qhaThermalExpansion_pos_iff _ _ _ B hI, hΓ]
    linarith
  have hCp := (harmonic_static_qhaHeatCapacityP_gt_iff _ _ _ B hI).mpr hα.ne'
  rw [hB] at hCp
  have hc := qhaThermalGruneisen_eq_weightedGruneisen (rateModel positiveRates A hA n hn)
    witnessTemperature 1 (one_mem_J positiveRates A hA n hn)
  exact ⟨hα, hCp, lt_of_lt_of_eq h1 hc.symm, lt_of_eq_of_lt hc h2⟩

/-- Negative rates: negative expansion, C_P still strictly above C_V, and a negative contracted
Gamma. -/
theorem negative_qha_witness (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n) :
    ∃ ε₀ > 0, ∀ ε, 0 < ε → ε ≤ ε₀ →
      qhaThermalExpansion
          (qhaGibbsEnergy (rateModel negativeRates A hA n hn).freeEnergy (Ioo (A - ε) (A + ε)))
          ((witnessTemperature : ℝ), 0) < 0 ∧
      (rateModel negativeRates A hA n hn).cv ((witnessTemperature : ℝ), A) <
        qhaHeatCapacityP
          (qhaGibbsEnergy (rateModel negativeRates A hA n hn).freeEnergy (Ioo (A - ε) (A + ε)))
          ((witnessTemperature : ℝ), 0) ∧
      qhaThermalGruneisen
          (fun i : Fin n × Fin 3 => (rateModel negativeRates A hA n hn).modeGruneisen i.1 i.2 1)
          (fun i => ((rateModel negativeRates A hA n hn).gridAt 1
            (one_mem_J negativeRates A hA n hn)).oscillator i.1 i.2) witnessTemperature < 0 := by
  obtain ⟨B, hB, ε₀, hε₀, hsel⟩ := rate_window negativeRates A hA n hn
  refine ⟨ε₀, hε₀, fun ε hε hεle => ?_⟩
  have hI := hsel ε hε hεle
  have hΓ := rate_weightedGruneisen_at_branch negativeRates A hA n hn B hB
  have hneg := negative_weightedGruneisen_neg A hA n hn
  have hα : qhaThermalExpansion
      (qhaGibbsEnergy (rateModel negativeRates A hA n hn).freeEnergy (Ioo (A - ε) (A + ε)))
      ((witnessTemperature : ℝ), 0) < 0 := by
    rw [(harmonic_static_qhaThermalExpansion_eq_omai _ _ _ B hI).1]
    refine ((rateModel negativeRates A hA n hn).expansion_neg_iff_weightedGruneisen_neg 0
      witnessTemperature B.isobar).mpr ?_
    change (rateModel negativeRates A hA n hn).weightedGruneisen witnessTemperature
      (B.volume ((witnessTemperature : ℝ), 0) / A) B.in_domain.self_of_nhds.2 < 0
    rw [hΓ]
    exact hneg
  have hCp := (harmonic_static_qhaHeatCapacityP_gt_iff _ _ _ B hI).mpr hα.ne
  rw [hB] at hCp
  have hc := qhaThermalGruneisen_eq_weightedGruneisen (rateModel negativeRates A hA n hn)
    witnessTemperature 1 (one_mem_J negativeRates A hA n hn)
  exact ⟨hα, hCp, lt_of_eq_of_lt hc hneg⟩

theorem zero_FV_reference (A : ℝ) (hA : 0 < A) {t : ℝ} (ht : 0 < t) :
    FV (zeroModel A hA).freeEnergy (t, A) = 0 := by
  rw [zero_FV A hA ht hA, div_self hA.ne', sub_self]

/-- Constant frequencies: on every narrow window the Gibbs-surface expansion vanishes,
C_P = C_V exactly and the contracted Gamma is zero. -/
theorem zero_qha_control (A : ℝ) (hA : 0 < A) :
    ∃ ε₀ > 0, ∀ ε, 0 < ε → ε ≤ ε₀ →
      qhaThermalExpansion (qhaGibbsEnergy (zeroModel A hA).freeEnergy (Ioo (A - ε) (A + ε)))
          ((witnessTemperature : ℝ), 0) = 0 ∧
      qhaHeatCapacityP (qhaGibbsEnergy (zeroModel A hA).freeEnergy (Ioo (A - ε) (A + ε)))
          ((witnessTemperature : ℝ), 0) = (zeroModel A hA).cv ((witnessTemperature : ℝ), A) ∧
      ∀ (T : Temperature) (v : ℝ) (hv : v ∈ (zeroModel A hA).J),
        qhaThermalGruneisen
          (fun i : Fin (zeroModel A hA).reference.qCount ×
              Fin (3 * (zeroModel A hA).reference.atomCount) =>
            (zeroModel A hA).modeGruneisen i.1 i.2 v)
          (fun i => ((zeroModel A hA).gridAt v hv).oscillator i.1 i.2) T = 0 := by
  have hx : ((witnessTemperature : ℝ), A) ∈ (zeroModel A hA).domain := by
    rw [witnessTemperature_toReal]
    exact zero_domain hA one_pos hA
  obtain ⟨B, hB⟩ := exists_gibbsBranchAt (zeroModel A hA).freeEnergy (zeroModel A hA).domain
    (witnessTemperature : ℝ) A 0 (zeroModel A hA).domain_isOpen
    (zeroModel A hA).freeEnergy_contDiffOn hx
    (by rw [witnessTemperature_toReal, add_zero]; exact zero_FV_reference A hA one_pos)
    (by rw [witnessTemperature_toReal, zero_FVV_reference hA]; exact div_pos one_pos hA)
  obtain ⟨ε₀, hε₀, hsel⟩ := harmonic_static_qhaGibbs_window (zeroModel A hA)
    witnessTemperature 0 B
  refine ⟨ε₀, hε₀, fun ε hε hεle => ?_⟩
  have hI := (hsel ε hε hεle).2
  rw [hB] at hI
  have hmixed : mixedTV (zeroModel A hA).freeEnergy ((witnessTemperature : ℝ), A) = 0 := by
    rw [mixedTV_eq_deriv_FV ((zeroModel A hA).freeEnergy_contDiffAt hx)]
    have heq : (fun s => FV (zeroModel A hA).freeEnergy (s, A)) =ᶠ[𝓝 (witnessTemperature : ℝ)]
        fun _ => (0 : ℝ) := by
      filter_upwards [isOpen_Ioi.mem_nhds (show (0 : ℝ) < (witnessTemperature : ℝ) by
        rw [witnessTemperature_toReal]; exact one_pos)] with s hs
      exact zero_FV_reference A hA hs
    rw [heq.deriv_eq, deriv_const]
  have hα : qhaThermalExpansion (qhaGibbsEnergy (zeroModel A hA).freeEnergy (Ioo (A - ε) (A + ε)))
      ((witnessTemperature : ℝ), 0) = 0 := by
    rw [(harmonic_static_qhaThermalExpansion_eq_omai _ _ _ B hI).2, hB, hmixed, neg_zero,
      zero_div]
  refine ⟨hα, ?_, fun T v hv => ?_⟩
  · rw [(harmonic_static_qhaHeatCapacityP_eq_omai _ _ _ B hI).2, hα, hB]
    ring
  · rw [qhaThermalGruneisen_eq_weightedGruneisen]
    exact zeroModel_weightedGruneisen A hA T v hv

/-- Literal non-unit instance: A = 3 and two reduced q points. -/
theorem positive_qha_witness_nonunit :
    ∃ ε₀ > 0, ∀ ε, 0 < ε → ε ≤ ε₀ →
      0 < qhaThermalExpansion
          (qhaGibbsEnergy (rateModel positiveRates 3 three_pos 2 two_pos).freeEnergy
            (Ioo (3 - ε) (3 + ε))) ((witnessTemperature : ℝ), 0) ∧
      (rateModel positiveRates 3 three_pos 2 two_pos).cv ((witnessTemperature : ℝ), 3) <
        qhaHeatCapacityP
          (qhaGibbsEnergy (rateModel positiveRates 3 three_pos 2 two_pos).freeEnergy
            (Ioo (3 - ε) (3 + ε))) ((witnessTemperature : ℝ), 0) ∧
      1 < qhaThermalGruneisen
          (fun i : Fin 2 × Fin 3 =>
            (rateModel positiveRates 3 three_pos 2 two_pos).modeGruneisen i.1 i.2 1)
          (fun i => ((rateModel positiveRates 3 three_pos 2 two_pos).gridAt 1
            (one_mem_J positiveRates 3 three_pos 2 two_pos)).oscillator i.1 i.2)
          witnessTemperature ∧
      qhaThermalGruneisen
          (fun i : Fin 2 × Fin 3 =>
            (rateModel positiveRates 3 three_pos 2 two_pos).modeGruneisen i.1 i.2 1)
          (fun i => ((rateModel positiveRates 3 three_pos 2 two_pos).gridAt 1
            (one_mem_J positiveRates 3 three_pos 2 two_pos)).oscillator i.1 i.2)
          witnessTemperature < 2 :=
  positive_qha_witness 3 three_pos 2 two_pos

end OMAI.PhyslibBridge.QHAWitness
