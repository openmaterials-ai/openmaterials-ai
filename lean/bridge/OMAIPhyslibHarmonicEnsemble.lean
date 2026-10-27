/- Infinite discrete harmonic oscillator with upstream spectrum and constants.
The counting measure includes every n : Nat, with zero-point energy retained. -/
module

public import OMAIPhyslibSemantics
public import Physlib.StatisticalMechanics.CanonicalEnsemble.Lemmas
public import Physlib.QuantumMechanics.HarmonicOscillator.OneDimension.TISE
public import Mathlib.Analysis.SpecificLimits.Normed
public import Mathlib.Analysis.SpecialFunctions.Trigonometric.Basic
public import Mathlib.MeasureTheory.Integral.Bochner.SumMeasure

@[expose] public section

namespace OMAI.PhyslibBridge
open MeasureTheory Real Constants Temperature
open QuantumMechanics.OneDimension
open scoped ENNReal
noncomputable section

/-- One quantum oscillator, with no classical phase-space normalization factor. -/
def harmonicEnsemble (Q : HarmonicOscillator) : CanonicalEnsemble ℕ where
  energy := Q.eigenValue
  dof := 0
  phaseSpaceunit := 1
  hPos := by norm_num
  energy_measurable := measurable_of_countable Q.eigenValue
  μ := Measure.count

/-- The same dimensionless argument as the OMAI per-mode formulas. -/
def oscillatorArgument (Q : HarmonicOscillator) (T : Temperature) : ℝ :=
  (T.β : ℝ) * (ℏ : ℝ) * Q.ω

theorem oscillatorArgument_eq_harmonicArgument (Q : HarmonicOscillator) (T : Temperature) :
    oscillatorArgument Q T = harmonicArgument ℏ kB Q.ω (T : ℝ) := by
  unfold oscillatorArgument harmonicArgument
  rw [Temperature.β_toReal]
  ring

theorem oscillatorArgument_pos (Q : HarmonicOscillator) (T : Temperature) (hT : 0 < T.val) :
    0 < oscillatorArgument Q T :=
  mul_pos (mul_pos (Temperature.beta_pos T hT) ℏ_pos) Q.ω_pos

/-- The upstream spectrum gives a constant zero-point factor times a geometric sequence. -/
theorem harmonic_boltzmann_factor (Q : HarmonicOscillator) (T : Temperature) (n : ℕ) :
    Real.exp (-(T.β : ℝ) * (harmonicEnsemble Q).energy n) =
      Real.exp (-oscillatorArgument Q T / 2) * Real.exp (-oscillatorArgument Q T) ^ n := by
  rw [← Real.exp_nat_mul, ← Real.exp_add]
  congr 1
  simp only [harmonicEnsemble, HarmonicOscillator.eigenValue, oscillatorArgument]
  ring

theorem harmonic_partition_hasSum (Q : HarmonicOscillator) (T : Temperature)
    (hT : 0 < T.val) :
    HasSum (fun n => Real.exp (-(T.β : ℝ) * (harmonicEnsemble Q).energy n))
      (Real.exp (-oscillatorArgument Q T / 2) /
        (1 - Real.exp (-oscillatorArgument Q T))) := by
  simpa only [harmonic_boltzmann_factor, div_eq_mul_inv] using
    (hasSum_geometric_of_lt_one (Real.exp_pos (-oscillatorArgument Q T)).le
      (Real.exp_lt_one_iff.mpr (neg_neg_of_pos (oscillatorArgument_pos Q T hT)))).mul_left
        (Real.exp (-oscillatorArgument Q T / 2))

theorem harmonic_boltzmann_integrable (Q : HarmonicOscillator) (T : Temperature)
    (hT : 0 < T.val) :
    Integrable (fun n => Real.exp (-(T.β : ℝ) * (harmonicEnsemble Q).energy n))
      (harmonicEnsemble Q).μ := by
  apply integrable_count_iff.mpr
  simpa only [Real.norm_eq_abs, abs_of_pos (Real.exp_pos _)] using
    (harmonic_partition_hasSum Q T hT).summable

theorem harmonic_boltzmann_finite (Q : HarmonicOscillator) (T : Temperature)
    (hT : 0 < T.val) : IsFiniteMeasure ((harmonicEnsemble Q).μBolt T) :=
  isFiniteMeasure_withDensity_ofReal (harmonic_boltzmann_integrable Q T hT).2

theorem harmonic_mathematicalPartitionFunction (Q : HarmonicOscillator) (T : Temperature)
    (hT : 0 < T.val) :
    (harmonicEnsemble Q).mathematicalPartitionFunction T =
      Real.exp (-oscillatorArgument Q T / 2) /
        (1 - Real.exp (-oscillatorArgument Q T)) := by
  rw [CanonicalEnsemble.mathematicalPartitionFunction_eq_integral,
    integral_countable (harmonic_boltzmann_integrable Q T hT)]
  simpa [harmonicEnsemble, measureReal_def] using (harmonic_partition_hasSum Q T hT).tsum_eq

theorem harmonic_partitionFunction (Q : HarmonicOscillator) (T : Temperature)
    (hT : 0 < T.val) :
    (harmonicEnsemble Q).partitionFunction T =
      Real.exp (-oscillatorArgument Q T / 2) /
        (1 - Real.exp (-oscillatorArgument Q T)) := by
  simpa [CanonicalEnsemble.partitionFunction, harmonicEnsemble] using
    harmonic_mathematicalPartitionFunction Q T hT

/-- The first energy moment, including the zero-point term, is absolutely summable. -/
theorem harmonic_energy_weighted_hasSum (Q : HarmonicOscillator) (T : Temperature)
    (hT : 0 < T.val) :
    HasSum (fun n => (harmonicEnsemble Q).energy n *
      Real.exp (-(T.β : ℝ) * (harmonicEnsemble Q).energy n))
      ((ℏ : ℝ) * Q.ω * Real.exp (-oscillatorArgument Q T / 2) *
        (Real.exp (-oscillatorArgument Q T) / (1 - Real.exp (-oscillatorArgument Q T)) ^ 2 +
          (1 / 2) * (1 - Real.exp (-oscillatorArgument Q T))⁻¹)) := by
  have hq : ‖Real.exp (-oscillatorArgument Q T)‖ < 1 := by
    rw [Real.norm_eq_abs, abs_of_pos (Real.exp_pos _)]
    exact Real.exp_lt_one_iff.mpr (neg_neg_of_pos (oscillatorArgument_pos Q T hT))
  have hsum := ((hasSum_coe_mul_geometric_of_norm_lt_one hq).add
    ((hasSum_geometric_of_norm_lt_one hq).mul_left (1 / 2 : ℝ))).mul_left
      ((ℏ : ℝ) * Q.ω * Real.exp (-oscillatorArgument Q T / 2))
  convert hsum using 1
  ext n
  rw [harmonic_boltzmann_factor]
  simp only [harmonicEnsemble, HarmonicOscillator.eigenValue]
  ring

theorem harmonic_energy_weighted_integrable (Q : HarmonicOscillator) (T : Temperature)
    (hT : 0 < T.val) :
    Integrable (fun n => (harmonicEnsemble Q).energy n *
      Real.exp (-(T.β : ℝ) * (harmonicEnsemble Q).energy n)) (harmonicEnsemble Q).μ := by
  apply integrable_count_iff.mpr
  have hnonneg (n : ℕ) : 0 ≤ (harmonicEnsemble Q).energy n *
      Real.exp (-(T.β : ℝ) * (harmonicEnsemble Q).energy n) := by
    apply mul_nonneg _ (Real.exp_pos _).le
    simp only [harmonicEnsemble, HarmonicOscillator.eigenValue]
    exact mul_nonneg (mul_nonneg (by positivity) ℏ_pos.le) Q.ω_pos.le
  simpa only [Real.norm_eq_abs, abs_of_nonneg (hnonneg _)] using
    (harmonic_energy_weighted_hasSum Q T hT).summable


instance harmonic_measure_neZero (Q : HarmonicOscillator) : NeZero (harmonicEnsemble Q).μ := by
  change NeZero (Measure.count : Measure ℕ)
  infer_instance

/-- Energy is integrable for the normalized infinite-state probability measure. -/
theorem harmonic_energy_integrable (Q : HarmonicOscillator) (T : Temperature)
    (hT : 0 < T.val) :
    Integrable (harmonicEnsemble Q).energy ((harmonicEnsemble Q).μProd T) := by
  have hbolt : Integrable (harmonicEnsemble Q).energy ((harmonicEnsemble Q).μBolt T) := by
    rw [CanonicalEnsemble.μBolt,
      integrable_withDensity_iff_integrable_smul' (by fun_prop) (by simp)]
    simpa only [ENNReal.toReal_ofReal (Real.exp_pos _).le, smul_eq_mul, mul_comm] using
      harmonic_energy_weighted_integrable Q T hT
  exact hbolt.smul_measure (ENNReal.inv_ne_top.mpr (mt Measure.measure_univ_eq_zero.mp (NeZero.ne _)))

/-- Identification of the infinite oscillator's free energy, with zero-point energy. -/
theorem harmonic_helmholtzFreeEnergy_eq_omai (Q : HarmonicOscillator) (T : Temperature)
    (hT : 0 < T.val) :
    (harmonicEnsemble Q).helmholtzFreeEnergy T =
      harmonicFreeEnergy ℏ kB Q.ω (T : ℝ) := by
  have hden : 1 - Real.exp (-oscillatorArgument Q T) ≠ 0 :=
    (sub_pos.mpr (Real.exp_lt_one_iff.mpr
      (neg_neg_of_pos (oscillatorArgument_pos Q T hT)))).ne'
  have hTr : (T : ℝ) ≠ 0 := by
    change (T.val : ℝ) ≠ 0
    exact_mod_cast hT.ne'
  rw [CanonicalEnsemble.helmholtzFreeEnergy_def, harmonic_partitionFunction Q T hT,
    Real.log_div (Real.exp_pos _).ne' hden, Real.log_exp]
  unfold harmonicFreeEnergy
  rw [← oscillatorArgument_eq_harmonicArgument]
  unfold oscillatorArgument
  rw [Temperature.β_toReal]
  change -kB * (T : ℝ) * (-(1 / (kB * (T : ℝ)) * (ℏ : ℝ) * Q.ω) / 2 - _) = _
  field_simp [kB_ne_zero, hTr]
  ring

/-- A positive-temperature rewrite between geometric occupation and the Bose formula. -/
theorem harmonic_geometric_occupation_eq_bose (Q : HarmonicOscillator) (T : Temperature)
    (hT : 0 < T.val) :
    Real.exp (-oscillatorArgument Q T) / (1 - Real.exp (-oscillatorArgument Q T)) =
      boseOccupation (oscillatorArgument Q T) := by
  have hexp : Real.exp (oscillatorArgument Q T) ≠ 0 := (Real.exp_pos _).ne'
  have hsub : Real.exp (oscillatorArgument Q T) - 1 ≠ 0 :=
    (sub_pos.mpr (Real.one_lt_exp_iff.mpr (oscillatorArgument_pos Q T hT))).ne'
  unfold boseOccupation
  rw [Real.exp_neg]
  field_simp

/-- The mean of the full Nat spectrum agrees with OMAI's per-mode internal energy. -/
theorem harmonic_meanEnergy_eq_omai (Q : HarmonicOscillator) (T : Temperature)
    (hT : 0 < T.val) :
    (harmonicEnsemble Q).meanEnergy T =
      harmonicInternalEnergy ℏ kB Q.ω (T : ℝ) := by
  have hden : 1 - Real.exp (-oscillatorArgument Q T) ≠ 0 :=
    (sub_pos.mpr (Real.exp_lt_one_iff.mpr
      (neg_neg_of_pos (oscillatorArgument_pos Q T hT)))).ne'
  have hc : Real.exp (-oscillatorArgument Q T / 2) ≠ 0 := (Real.exp_pos _).ne'
  have henergy : (∫ n, (harmonicEnsemble Q).energy n *
      Real.exp (-(T.β : ℝ) * (harmonicEnsemble Q).energy n) ∂(harmonicEnsemble Q).μ) =
      (ℏ : ℝ) * Q.ω * Real.exp (-oscillatorArgument Q T / 2) *
        (Real.exp (-oscillatorArgument Q T) / (1 - Real.exp (-oscillatorArgument Q T)) ^ 2 +
          (1 / 2) * (1 - Real.exp (-oscillatorArgument Q T))⁻¹) := by
    rw [integral_countable (harmonic_energy_weighted_integrable Q T hT)]
    simpa [harmonicEnsemble, measureReal_def] using
      (harmonic_energy_weighted_hasSum Q T hT).tsum_eq
  rw [CanonicalEnsemble.meanEnergy_eq_ratio_of_integrals, henergy,
    ← CanonicalEnsemble.mathematicalPartitionFunction_eq_integral,
    harmonic_mathematicalPartitionFunction Q T hT]
  unfold harmonicInternalEnergy
  rw [← oscillatorArgument_eq_harmonicArgument,
    ← harmonic_geometric_occupation_eq_bose Q T hT]
  field_simp [hden, hc]

/-- Entropy identification uses the upstream theorem only after its measure and
integrability hypotheses have been proved for the infinite spectrum. -/
theorem harmonic_thermodynamicEntropy_eq_omai (Q : HarmonicOscillator) (T : Temperature)
    (hT : 0 < T.val) :
    (harmonicEnsemble Q).thermodynamicEntropy T =
      harmonicEntropy ℏ kB Q.ω (T : ℝ) := by
  let := harmonic_boltzmann_finite Q T hT
  have hphysical := (harmonicEnsemble Q).helmholtzFreeEnergy_eq_meanEnergy_sub_temp_mul_thermodynamicEntropy T hT
      (harmonic_energy_integrable Q T hT)
  rw [harmonic_helmholtzFreeEnergy_eq_omai Q T hT, harmonic_meanEnergy_eq_omai Q T hT]
    at hphysical
  have hTr : 0 < (T : ℝ) := by
    change 0 < (T.val : ℝ)
    exact_mod_cast hT
  have hclosed := harmonic_freeEnergy_eq_internalEnergy_sub_temperature_mul_entropy
    ℏ_pos kB_pos Q.ω_pos hTr
  change _ = _ - (T : ℝ) * _ at hphysical
  nlinarith


/-- OMAI's per-mode heat capacity, in the published hyperbolic-sine form. -/
def harmonicHeatCapacity (hbar kB omega temperature : ℝ) : ℝ :=
  (hbar * omega) ^ 2 /
    (4 * kB * temperature ^ 2 * Real.sinh (harmonicArgument hbar kB omega temperature / 2) ^ 2)

/-- Frequency and constants are held fixed when differentiating in temperature. -/
theorem harmonicArgument_hasDerivAt {hbar kB omega temperature : ℝ}
    (hk : 0 < kB) (hT : 0 < temperature) :
    HasDerivAt (harmonicArgument hbar kB omega)
      (-(hbar * omega) / (kB * temperature ^ 2)) temperature := by
  have hd := (hasDerivAt_const temperature (hbar * omega)).div
    ((hasDerivAt_id temperature).const_mul kB) (mul_pos hk hT).ne'
  convert hd using 1
  · ext t
    rfl
  · dsimp
    field_simp
    ring

theorem harmonicInternalEnergy_hasDerivAt_exp {hbar kB omega temperature : ℝ}
    (hh : 0 < hbar) (hk : 0 < kB) (hw : 0 < omega) (hT : 0 < temperature) :
    HasDerivAt (harmonicInternalEnergy hbar kB omega)
      ((hbar * omega) ^ 2 * Real.exp (harmonicArgument hbar kB omega temperature) /
        (kB * temperature ^ 2 * (Real.exp (harmonicArgument hbar kB omega temperature) - 1) ^ 2))
      temperature := by
  have hden := (harmonic_bose_denominator_pos hh hk hw hT).ne'
  have hd := ((((hasDerivAt_const temperature (1 : ℝ)).div
    ((harmonicArgument_hasDerivAt hk hT).exp.sub_const 1) hden).add_const
      (1 / 2 : ℝ)).const_mul hbar).mul_const omega
  convert hd using 1
  · ext t
    rfl
  · field_simp
    ring

/-- Algebraic conversion needed to match the stored OMAI sinh expression. -/
theorem four_sinh_half_sq (x : ℝ) :
    4 * Real.sinh (x / 2) ^ 2 = (Real.exp x - 1) ^ 2 / Real.exp x := by
  have hex : Real.exp x = Real.exp (x / 2) ^ 2 := by
    rw [← Real.exp_nat_mul]
    congr 1
    ring
  rw [Real.sinh_eq, Real.exp_neg, hex]
  field_simp
  ring

theorem harmonicHeatCapacity_eq_exp {hbar kB omega temperature : ℝ}
    (hh : 0 < hbar) (hk : 0 < kB) (hw : 0 < omega) (hT : 0 < temperature) :
    harmonicHeatCapacity hbar kB omega temperature =
      (hbar * omega) ^ 2 * Real.exp (harmonicArgument hbar kB omega temperature) /
        (kB * temperature ^ 2 * (Real.exp (harmonicArgument hbar kB omega temperature) - 1) ^ 2) := by
  have hden := (harmonic_bose_denominator_pos hh hk hw hT).ne'
  have hex := (Real.exp_pos (harmonicArgument hbar kB omega temperature)).ne'
  unfold harmonicHeatCapacity
  rw [show 4 * kB * temperature ^ 2 *
      Real.sinh (harmonicArgument hbar kB omega temperature / 2) ^ 2 =
      kB * temperature ^ 2 * (4 *
        Real.sinh (harmonicArgument hbar kB omega temperature / 2) ^ 2) by ring,
    four_sinh_half_sq]
  field_simp

/-- The derivative of the per-mode energy is precisely the OMAI sinh heat capacity. -/
theorem harmonicInternalEnergy_hasDerivAt {hbar kB omega temperature : ℝ}
    (hh : 0 < hbar) (hk : 0 < kB) (hw : 0 < omega) (hT : 0 < temperature) :
    HasDerivAt (harmonicInternalEnergy hbar kB omega)
      (harmonicHeatCapacity hbar kB omega temperature) temperature := by
  rw [harmonicHeatCapacity_eq_exp hh hk hw hT]
  exact harmonicInternalEnergy_hasDerivAt_exp hh hk hw hT

/-- The upstream mean-energy function equals the closed form throughout its positive domain. -/
theorem harmonic_meanEnergyT_eq_omai (Q : HarmonicOscillator) {t : ℝ} (ht : 0 < t) :
    (harmonicEnsemble Q).meanEnergyT t = harmonicInternalEnergy ℏ kB Q.ω t := by
  have hpos : 0 < (Temperature.ofNNReal (Real.toNNReal t)).val := by
    simpa only [Temperature.ofNNReal_val] using Real.toNNReal_pos.mpr ht
  simpa [CanonicalEnsemble.meanEnergyT, Temperature.ofNNReal, Temperature.toReal,
    Real.toNNReal_of_nonneg ht.le] using
    harmonic_meanEnergy_eq_omai Q (Temperature.ofNNReal (Real.toNNReal t)) hpos

/-- Identification with Physlib's derivative-defined heat capacity on T > 0.
The infinite-sum identification is proved first; differentiation is then transferred
on the open positive-temperature domain. No derivative-under-sum premise is assumed. -/
theorem harmonic_heatCapacity_eq_omai (Q : HarmonicOscillator) (T : Temperature)
    (hT : 0 < T.val) :
    (harmonicEnsemble Q).heatCapacity T = harmonicHeatCapacity ℏ kB Q.ω (T : ℝ) := by
  have hTr : 0 < (T : ℝ) := by
    change 0 < (T.val : ℝ)
    exact_mod_cast hT
  have hderiv : HasDerivWithinAt (harmonicEnsemble Q).meanEnergyT
      (harmonicHeatCapacity ℏ kB Q.ω (T : ℝ)) (Set.Ioi 0) (T : ℝ) :=
    (harmonicInternalEnergy_hasDerivAt ℏ_pos kB_pos Q.ω_pos hTr).hasDerivWithinAt.congr
      (fun t ht => harmonic_meanEnergyT_eq_omai Q ht) (harmonic_meanEnergyT_eq_omai Q hTr)
  exact hderiv.derivWithin (isOpen_Ioi.uniqueDiffWithinAt hTr)


/-- At fixed frequency, minus the temperature derivative of F is the same per-mode entropy. -/
theorem harmonicFreeEnergy_hasDerivAt {hbar kB omega temperature : ℝ}
    (hh : 0 < hbar) (hk : 0 < kB) (hw : 0 < omega) (hT : 0 < temperature) :
    HasDerivAt (harmonicFreeEnergy hbar kB omega)
      (-harmonicEntropy hbar kB omega temperature) temperature := by
  have hlog := (harmonic_log_argument_pos hh hk hw hT).ne'
  have hden := (harmonic_bose_denominator_pos hh hk hw hT).ne'
  have hd := ((((hasDerivAt_id temperature).const_mul kB).mul
    (((hasDerivAt_const temperature (1 : ℝ)).sub
      (harmonicArgument_hasDerivAt hk hT).neg.exp).log hlog)).const_add (hbar * omega / 2))
  convert hd using 1
  · ext t
    rfl
  · dsimp
    unfold harmonicEntropy boseOccupation
    rw [Real.exp_neg]
    field_simp
    ring

end
end OMAI.PhyslibBridge
