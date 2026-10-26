/- A temperature-independent per-cell static energy attached to the actual
independent harmonic ensemble. Normalization remains outside the Hamiltonian. -/
module

public import OMAIPhyslibHarmonicProduct

@[expose] public section

namespace OMAI.PhyslibBridge
open MeasureTheory Real Constants Temperature
open scoped BigOperators ENNReal
noncomputable section

/-- One microstate, with unit counting mass and an arbitrary signed energy. -/
def staticEnergyEnsemble (e : ℝ) : CanonicalEnsemble Unit where
  energy := fun _ => e
  dof := 0
  phaseSpaceunit := 1
  hPos := by norm_num
  energy_measurable := by fun_prop
  μ := Measure.count

theorem staticEnergyEnsemble_energy (e : ℝ) (state : Unit) :
    (staticEnergyEnsemble e).energy state = e := rfl

theorem staticEnergyEnsemble_measure (e : ℝ) :
    (staticEnergyEnsemble e).μ = (Measure.count : Measure Unit) := rfl

theorem staticEnergyEnsemble_measure_univ (e : ℝ) :
    (staticEnergyEnsemble e).μ Set.univ = 1 := by
  simp [staticEnergyEnsemble]

instance staticEnergyEnsemble_measure_neZero (e : ℝ) :
    NeZero (staticEnergyEnsemble e).μ := by
  change NeZero (Measure.count : Measure Unit)
  infer_instance

instance staticEnergyEnsemble_boltzmann_finite (e : ℝ) (T : Temperature) :
    IsFiniteMeasure ((staticEnergyEnsemble e).μBolt T) := by
  apply (isFiniteMeasure_iff _).mpr
  simp [CanonicalEnsemble.μBolt, staticEnergyEnsemble, withDensity_const]

theorem staticEnergyEnsemble_energy_integrable (e : ℝ) (T : Temperature) :
    Integrable (staticEnergyEnsemble e).energy ((staticEnergyEnsemble e).μProd T) := by
  exact integrable_const e

/-- The singleton's actual partition function is positive for every finite offset. -/
theorem staticEnergyEnsemble_partitionFunction (e : ℝ) (T : Temperature) :
    (staticEnergyEnsemble e).partitionFunction T = Real.exp (-T.β * e) := by
  rw [CanonicalEnsemble.partitionFunction_dof_zero _ _ rfl,
    CanonicalEnsemble.mathematicalPartitionFunction_eq_integral]
  simp [staticEnergyEnsemble]

theorem staticEnergyEnsemble_helmholtzFreeEnergy (e : ℝ) (T : Temperature)
    (hT : 0 < T.val) : (staticEnergyEnsemble e).helmholtzFreeEnergy T = e := by
  rw [CanonicalEnsemble.helmholtzFreeEnergy_def, staticEnergyEnsemble_partitionFunction,
    Real.log_exp]
  have hTne : (T.val : ℝ) ≠ 0 := by exact_mod_cast hT.ne'
  have hkβT : (T.val : ℝ) * (kB * (T.β : ℝ)) = 1 := by
    rw [CanonicalEnsemble.kB_mul_beta T hT, mul_one_div, div_self hTne]
  calc
    -kB * T.val * (-T.β * e) = ((T.val : ℝ) * (kB * (T.β : ℝ))) * e := by ring
    _ = e := by rw [hkβT, one_mul]

theorem staticEnergyEnsemble_meanEnergy (e : ℝ) (T : Temperature) :
    (staticEnergyEnsemble e).meanEnergy T = e := by
  change (∫ _ : Unit, e ∂(staticEnergyEnsemble e).μProd T) = e
  simp

theorem staticEnergyEnsemble_thermodynamicEntropy (e : ℝ) (T : Temperature)
    (hT : 0 < T.val) : (staticEnergyEnsemble e).thermodynamicEntropy T = 0 := by
  have h := (staticEnergyEnsemble e).helmholtzFreeEnergy_eq_meanEnergy_sub_temp_mul_thermodynamicEntropy
    T hT (staticEnergyEnsemble_energy_integrable e T)
  rw [staticEnergyEnsemble_helmholtzFreeEnergy e T hT,
    staticEnergyEnsemble_meanEnergy] at h
  have hTr : 0 < (T.val : ℝ) := by exact_mod_cast hT
  nlinarith

theorem staticEnergyEnsemble_meanEnergyT (e t : ℝ) :
    (staticEnergyEnsemble e).meanEnergyT t = e :=
  staticEnergyEnsemble_meanEnergy e _

theorem staticEnergyEnsemble_heatCapacity (e : ℝ) (T : Temperature) :
    (staticEnergyEnsemble e).heatCapacity T = 0 := by
  have hfun : (staticEnergyEnsemble e).meanEnergyT = fun _ => e := by
    funext t
    exact staticEnergyEnsemble_meanEnergyT e t
  simp [CanonicalEnsemble.heatCapacity, hfun]

/-- The static factor contributes Nq times the primitive-cell energy to the
unweighted grid Hamiltonian. The external NA/Nq normalization is unchanged. -/
def staticHarmonicGridEnsemble (grid : HarmonicModeGrid) (eCell : ℝ) :
    CanonicalEnsemble (Unit × (Fin (grid.qCount * (3 * grid.atomCount)) → ℕ)) :=
  staticEnergyEnsemble ((grid.qCount : ℝ) * eCell) + harmonicGridEnsemble grid

private instance harmonicGrid_static_measure_neZero (grid : HarmonicModeGrid) :
    NeZero (harmonicGridEnsemble grid).μ := by
  unfold harmonicGridEnsemble
  infer_instance

private theorem harmonicGrid_static_boltzmann_finite (grid : HarmonicModeGrid)
    (T : Temperature) (hT : 0 < T.val) :
    IsFiniteMeasure ((harmonicGridEnsemble grid).μBolt T) := by
  exact harmonicProduct_boltzmann_finite (harmonicGridOscillator grid) T hT

theorem staticHarmonicGrid_energy (grid : HarmonicModeGrid) (eCell : ℝ)
    (state : Unit × (Fin (grid.qCount * (3 * grid.atomCount)) → ℕ)) :
    (staticHarmonicGridEnsemble grid eCell).energy state =
      (grid.qCount : ℝ) * eCell + (harmonicGridEnsemble grid).energy state.2 := rfl

theorem staticHarmonicGrid_measure (grid : HarmonicModeGrid) (eCell : ℝ) :
    (staticHarmonicGridEnsemble grid eCell).μ =
      (Measure.count : Measure Unit).prod (harmonicGridEnsemble grid).μ := rfl

instance staticHarmonicGrid_measure_neZero (grid : HarmonicModeGrid) (eCell : ℝ) :
    NeZero (staticHarmonicGridEnsemble grid eCell).μ := by
  unfold staticHarmonicGridEnsemble
  infer_instance

theorem staticHarmonicGrid_boltzmann_finite (grid : HarmonicModeGrid) (eCell : ℝ)
    (T : Temperature) (hT : 0 < T.val) :
    IsFiniteMeasure ((staticHarmonicGridEnsemble grid eCell).μBolt T) := by
  let := harmonicGrid_static_boltzmann_finite grid T hT
  unfold staticHarmonicGridEnsemble
  infer_instance

theorem staticHarmonicGrid_energy_integrable (grid : HarmonicModeGrid) (eCell : ℝ)
    (T : Temperature) (hT : 0 < T.val) :
    Integrable (staticHarmonicGridEnsemble grid eCell).energy
      ((staticHarmonicGridEnsemble grid eCell).μProd T) := by
  let := harmonicGrid_static_boltzmann_finite grid T hT
  exact CanonicalEnsemble.integrable_energy_add _ _ T
    (staticEnergyEnsemble_energy_integrable _ T)
    (harmonicProduct_energy_integrable (harmonicGridOscillator grid) T hT)

theorem staticHarmonicGrid_partitionFunction (grid : HarmonicModeGrid) (eCell : ℝ)
    (T : Temperature) :
    (staticHarmonicGridEnsemble grid eCell).partitionFunction T =
      Real.exp (-T.β * ((grid.qCount : ℝ) * eCell)) *
        (harmonicGridEnsemble grid).partitionFunction T := by
  rw [staticHarmonicGridEnsemble, CanonicalEnsemble.partitionFunction_add
      (staticEnergyEnsemble ((grid.qCount : ℝ) * eCell)) (harmonicGridEnsemble grid) T rfl,
    staticEnergyEnsemble_partitionFunction]

theorem staticHarmonicGrid_helmholtzFreeEnergy (grid : HarmonicModeGrid) (eCell : ℝ)
    (T : Temperature) (hT : 0 < T.val) :
    (staticHarmonicGridEnsemble grid eCell).helmholtzFreeEnergy T =
      (grid.qCount : ℝ) * eCell + (harmonicGridEnsemble grid).helmholtzFreeEnergy T := by
  let := harmonicGrid_static_boltzmann_finite grid T hT
  rw [staticHarmonicGridEnsemble, CanonicalEnsemble.helmholtzFreeEnergy_add
      (staticEnergyEnsemble ((grid.qCount : ℝ) * eCell)) (harmonicGridEnsemble grid) T rfl,
    staticEnergyEnsemble_helmholtzFreeEnergy _ T hT]

theorem staticHarmonicGrid_meanEnergy (grid : HarmonicModeGrid) (eCell : ℝ)
    (T : Temperature) (hT : 0 < T.val) :
    (staticHarmonicGridEnsemble grid eCell).meanEnergy T =
      (grid.qCount : ℝ) * eCell + (harmonicGridEnsemble grid).meanEnergy T := by
  let := harmonicGrid_static_boltzmann_finite grid T hT
  rw [staticHarmonicGridEnsemble, CanonicalEnsemble.meanEnergy_add
    (staticEnergyEnsemble ((grid.qCount : ℝ) * eCell)) (harmonicGridEnsemble grid)
    (staticEnergyEnsemble_energy_integrable _ T)
    (harmonicProduct_energy_integrable (harmonicGridOscillator grid) T hT),
    staticEnergyEnsemble_meanEnergy]

/-- This is invariance of the actual statistical entropy, obtained from F=U-TS. -/
theorem staticHarmonicGrid_thermodynamicEntropy (grid : HarmonicModeGrid) (eCell : ℝ)
    (T : Temperature) (hT : 0 < T.val) :
    (staticHarmonicGridEnsemble grid eCell).thermodynamicEntropy T =
      (harmonicGridEnsemble grid).thermodynamicEntropy T := by
  let := harmonicGrid_static_boltzmann_finite grid T hT
  let := staticHarmonicGrid_boltzmann_finite grid eCell T hT
  have hs := (staticHarmonicGridEnsemble grid eCell).helmholtzFreeEnergy_eq_meanEnergy_sub_temp_mul_thermodynamicEntropy
    T hT (staticHarmonicGrid_energy_integrable grid eCell T hT)
  have hh := (harmonicGridEnsemble grid).helmholtzFreeEnergy_eq_meanEnergy_sub_temp_mul_thermodynamicEntropy
    T hT (harmonicProduct_energy_integrable (harmonicGridOscillator grid) T hT)
  rw [staticHarmonicGrid_helmholtzFreeEnergy grid eCell T hT,
    staticHarmonicGrid_meanEnergy grid eCell T hT] at hs
  have hTr : 0 < (T.val : ℝ) := by exact_mod_cast hT
  nlinarith

/-- A function equality on the open positive-temperature domain, with both the
spectrum and the static per-cell energy held fixed. -/
theorem staticHarmonicGrid_meanEnergyT (grid : HarmonicModeGrid) (eCell : ℝ)
    {t : ℝ} (ht : 0 < t) :
    (staticHarmonicGridEnsemble grid eCell).meanEnergyT t =
      (grid.qCount : ℝ) * eCell + (harmonicGridEnsemble grid).meanEnergyT t := by
  have hpos : 0 < (Temperature.ofNNReal (Real.toNNReal t)).val := by
    simpa only [Temperature.ofNNReal_val] using Real.toNNReal_pos.mpr ht
  exact staticHarmonicGrid_meanEnergy grid eCell _ hpos

/-- The derivative-defined capacity is invariant at fixed volume; no statement
about a temperature-dependent static energy along a volume path is assumed. -/
theorem staticHarmonicGrid_heatCapacity (grid : HarmonicModeGrid) (eCell : ℝ)
    (T : Temperature) (hT : 0 < T.val) :
    (staticHarmonicGridEnsemble grid eCell).heatCapacity T =
      (harmonicGridEnsemble grid).heatCapacity T := by
  have hTr : 0 < (T.val : ℝ) := by exact_mod_cast hT
  have heq : Set.EqOn (staticHarmonicGridEnsemble grid eCell).meanEnergyT
      (fun t => (grid.qCount : ℝ) * eCell + (harmonicGridEnsemble grid).meanEnergyT t)
      (Set.Ioi 0) := fun _ ht => staticHarmonicGrid_meanEnergyT grid eCell ht
  unfold CanonicalEnsemble.heatCapacity
  rw [derivWithin_congr heq (heq hTr), derivWithin_const_add]

/-- A non-unit q count cancels only after external molar normalization. -/
theorem staticHarmonicGrid_molar_static_scale (grid : HarmonicModeGrid) (eCell : ℝ) :
    (grid.avogadro / (grid.qCount : ℝ)) * ((grid.qCount : ℝ) * eCell) =
      grid.avogadro * eCell := by
  have hq : (grid.qCount : ℝ) ≠ 0 := (Nat.cast_pos.mpr grid.qCount_pos).ne'
  field_simp

theorem staticHarmonicGrid_molar_helmholtzFreeEnergy (grid : HarmonicModeGrid)
    (eCell : ℝ) (T : Temperature) (hT : 0 < T.val) :
    (grid.avogadro / (grid.qCount : ℝ)) *
        (staticHarmonicGridEnsemble grid eCell).helmholtzFreeEnergy T =
      grid.avogadro * eCell + harmonicMolarFreeEnergy grid T := by
  rw [staticHarmonicGrid_helmholtzFreeEnergy grid eCell T hT, mul_add,
    staticHarmonicGrid_molar_static_scale, harmonic_joint_molar_helmholtzFreeEnergy_eq_omai grid T hT]

theorem staticHarmonicGrid_molar_meanEnergy (grid : HarmonicModeGrid)
    (eCell : ℝ) (T : Temperature) (hT : 0 < T.val) :
    (grid.avogadro / (grid.qCount : ℝ)) *
        (staticHarmonicGridEnsemble grid eCell).meanEnergy T =
      grid.avogadro * eCell + harmonicMolarInternalEnergy grid T := by
  rw [staticHarmonicGrid_meanEnergy grid eCell T hT, mul_add,
    staticHarmonicGrid_molar_static_scale, harmonic_joint_molar_meanEnergy_eq_omai grid T hT]

theorem staticHarmonicGrid_molar_thermodynamicEntropy (grid : HarmonicModeGrid)
    (eCell : ℝ) (T : Temperature) (hT : 0 < T.val) :
    (grid.avogadro / (grid.qCount : ℝ)) *
        (staticHarmonicGridEnsemble grid eCell).thermodynamicEntropy T =
      harmonicMolarEntropy grid T := by
  rw [staticHarmonicGrid_thermodynamicEntropy grid eCell T hT,
    harmonic_joint_molar_thermodynamicEntropy_eq_omai grid T hT]

theorem staticHarmonicGrid_molar_heatCapacity (grid : HarmonicModeGrid)
    (eCell : ℝ) (T : Temperature) (hT : 0 < T.val) :
    (grid.avogadro / (grid.qCount : ℝ)) *
        (staticHarmonicGridEnsemble grid eCell).heatCapacity T =
      harmonicMolarHeatCapacity grid T := by
  rw [staticHarmonicGrid_heatCapacity grid eCell T hT,
    harmonic_joint_molar_heatCapacity_eq_omai grid T hT]

theorem staticHarmonicGrid_zero_freeEnergy (grid : HarmonicModeGrid)
    (T : Temperature) (hT : 0 < T.val) :
    (staticHarmonicGridEnsemble grid 0).helmholtzFreeEnergy T =
      (harmonicGridEnsemble grid).helmholtzFreeEnergy T := by
  simpa using staticHarmonicGrid_helmholtzFreeEnergy grid 0 T hT

theorem staticHarmonicGrid_zero_meanEnergy (grid : HarmonicModeGrid)
    (T : Temperature) (hT : 0 < T.val) :
    (staticHarmonicGridEnsemble grid 0).meanEnergy T =
      (harmonicGridEnsemble grid).meanEnergy T := by
  simpa using staticHarmonicGrid_meanEnergy grid 0 T hT

/-- Opposite signed offsets change actual free energy by the expected amount. -/
theorem staticHarmonicGrid_signed_freeEnergy_difference (grid : HarmonicModeGrid)
    (eCell : ℝ) (T : Temperature) (hT : 0 < T.val) :
    (staticHarmonicGridEnsemble grid eCell).helmholtzFreeEnergy T -
        (staticHarmonicGridEnsemble grid (-eCell)).helmholtzFreeEnergy T =
      2 * (grid.qCount : ℝ) * eCell := by
  rw [staticHarmonicGrid_helmholtzFreeEnergy grid eCell T hT,
    staticHarmonicGrid_helmholtzFreeEnergy grid (-eCell) T hT]
  ring

/-- A normalization control with two q points and scale three. The scale is a
formal non-unit test parameter, not a numerical value for the physical Avogadro constant. -/
def staticNormalizationControlGrid : HarmonicModeGrid where
  qCount := 2
  qCount_pos := by norm_num
  atomCount := 1
  atomCount_pos := by norm_num
  avogadro := 3
  avogadro_pos := by norm_num
  oscillator := fun q _ => harmonicUnequalPair q

/-- A signed energy -5 per cell becomes -15 after the non-unit molar scale;
it is not divided by the number of q points a second time. -/
theorem staticHarmonicGrid_nonunit_molar_meanEnergy (T : Temperature) (hT : 0 < T.val) :
    (3 / 2 : ℝ) * (staticHarmonicGridEnsemble staticNormalizationControlGrid (-5)).meanEnergy T =
      -15 + harmonicMolarInternalEnergy staticNormalizationControlGrid T := by
  have h := staticHarmonicGrid_molar_meanEnergy staticNormalizationControlGrid (-5) T hT
  norm_num [staticNormalizationControlGrid] at h ⊢
  exact h

theorem staticHarmonicGrid_nonunit_molar_freeEnergy (T : Temperature) (hT : 0 < T.val) :
    (3 / 2 : ℝ) *
        (staticHarmonicGridEnsemble staticNormalizationControlGrid (-5)).helmholtzFreeEnergy T =
      -15 + harmonicMolarFreeEnergy staticNormalizationControlGrid T := by
  have h := staticHarmonicGrid_molar_helmholtzFreeEnergy staticNormalizationControlGrid (-5) T hT
  norm_num [staticNormalizationControlGrid] at h ⊢
  exact h

theorem staticHarmonicGrid_nonunit_molar_heatCapacity (T : Temperature) (hT : 0 < T.val) :
    (3 / 2 : ℝ) *
        (staticHarmonicGridEnsemble staticNormalizationControlGrid (-5)).heatCapacity T =
      harmonicMolarHeatCapacity staticNormalizationControlGrid T := by
  simpa [staticNormalizationControlGrid] using
    staticHarmonicGrid_molar_heatCapacity staticNormalizationControlGrid (-5) T hT

end
end OMAI.PhyslibBridge
