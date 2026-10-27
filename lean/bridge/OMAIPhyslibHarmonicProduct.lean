/- Heterogeneous finite products of full Nat harmonic occupation ensembles.
The Hamiltonian is unweighted; molar normalization is applied only afterwards. -/
module

public import OMAIPhyslibHarmonicSums

@[expose] public section

namespace OMAI.PhyslibBridge
open MeasureTheory Real Constants Temperature
open QuantumMechanics.OneDimension
open scoped BigOperators ENNReal
noncomputable section

/-- The full independent occupation model for an arbitrary finite, possibly
heterogeneous spectrum. The empty-index case has one empty occupation function. -/
def harmonicProduct {n : ℕ} (Q : Fin n → HarmonicOscillator) :
    CanonicalEnsemble (Fin n → ℕ) where
  energy := fun occupation => ∑ i, (Q i).eigenValue (occupation i)
  dof := 0
  phaseSpaceunit := 1
  hPos := by norm_num
  energy_measurable := by fun_prop
  μ := Measure.pi fun _ => (Measure.count : Measure ℕ)

/-- Occupation coordinates enumerate every Nat level independently. -/
theorem harmonicProduct_energy {n : ℕ} (Q : Fin n → HarmonicOscillator)
    (occupation : Fin n → ℕ) :
    (harmonicProduct Q).energy occupation = ∑ i, (Q i).eigenValue (occupation i) := rfl

theorem harmonicProduct_measure {n : ℕ} (Q : Fin n → HarmonicOscillator) :
    (harmonicProduct Q).μ = Measure.pi (fun _ : Fin n => (Measure.count : Measure ℕ)) := rfl

/-- Heterogeneous head/tail factorization, including measure-preserving transport. -/
theorem harmonicProduct_succ {n : ℕ} (Q : Fin (n + 1) → HarmonicOscillator) :
    harmonicProduct Q =
      (harmonicEnsemble (Q 0) + harmonicProduct (fun i => Q i.succ)).congr
        (MeasurableEquiv.piFinSuccAbove (fun _ => ℕ) 0) := by
  apply CanonicalEnsemble.ext
  · funext x
    simpa [harmonicProduct, harmonicEnsemble, Fin.tail] using
      (Fin.sum_univ_succ (fun i => (Q i).eigenValue (x i)))
  · rfl
  · rfl
  · exact (((measurePreserving_piFinSuccAbove
      (fun _ : Fin (n + 1) => (Measure.count : Measure ℕ)) 0).symm _).map_eq).symm

instance harmonicProduct_measure_neZero {n : ℕ} (Q : Fin n → HarmonicOscillator) :
    NeZero (harmonicProduct Q).μ := by
  refine ⟨fun h => ?_⟩
  have hc := congrArg (fun μ : Measure (Fin n → ℕ) => μ {fun _ => 0}) h
  simp [harmonicProduct] at hc

/-- The vacuum has exactly one microstate and unit statistical weight. -/
theorem harmonicProduct_vacuum_measure (Q : Fin 0 → HarmonicOscillator) :
    (harmonicProduct Q).μ Set.univ = 1 := by
  simp [harmonicProduct]

theorem harmonicProduct_vacuum_partition (Q : Fin 0 → HarmonicOscillator)
    (T : Temperature) : (harmonicProduct Q).partitionFunction T = 1 := by
  rw [CanonicalEnsemble.partitionFunction_dof_zero _ _ rfl,
    CanonicalEnsemble.mathematicalPartitionFunction_eq_integral]
  simp [harmonicProduct, measureReal_def]

/-- Boltzmann finiteness follows from full-spectrum single-mode summability. -/
theorem harmonicProduct_boltzmann_finite {n : ℕ} (Q : Fin n → HarmonicOscillator)
    (T : Temperature) (hT : 0 < T.val) :
    IsFiniteMeasure ((harmonicProduct Q).μBolt T) := by
  induction n with
  | zero =>
    apply (isFiniteMeasure_iff _).mpr
    simp [CanonicalEnsemble.μBolt, harmonicProduct]
  | succ n ih =>
    let := harmonic_boltzmann_finite (Q 0) T hT
    let := ih (fun i => Q i.succ)
    rw [harmonicProduct_succ, CanonicalEnsemble.μBolt_congr]
    infer_instance

theorem harmonicProduct_energy_integrable {n : ℕ} (Q : Fin n → HarmonicOscillator)
    (T : Temperature) (hT : 0 < T.val) :
    Integrable (harmonicProduct Q).energy ((harmonicProduct Q).μProd T) := by
  induction n with
  | zero => simp [harmonicProduct]
  | succ n ih =>
    let := harmonic_boltzmann_finite (Q 0) T hT
    let := harmonicProduct_boltzmann_finite (fun i => Q i.succ) T hT
    rw [harmonicProduct_succ]
    apply CanonicalEnsemble.integrable_energy_congr
    exact CanonicalEnsemble.integrable_energy_add _ _ T
      (harmonic_energy_integrable (Q 0) T hT) (ih (fun i => Q i.succ))

/-- The actual joint partition is the product of the individual partitions. -/
theorem harmonicProduct_partitionFunction {n : ℕ} (Q : Fin n → HarmonicOscillator)
    (T : Temperature) :
    (harmonicProduct Q).partitionFunction T =
      ∏ i, (harmonicEnsemble (Q i)).partitionFunction T := by
  induction n with
  | zero => simpa using harmonicProduct_vacuum_partition Q T
  | succ n ih =>
    rw [harmonicProduct_succ, CanonicalEnsemble.partitionFunction_congr,
      CanonicalEnsemble.partitionFunction_add (harmonicEnsemble (Q 0))
        (harmonicProduct (fun i => Q i.succ)) T rfl, ih, Fin.prod_univ_succ]

theorem harmonicProduct_helmholtzFreeEnergy {n : ℕ} (Q : Fin n → HarmonicOscillator)
    (T : Temperature) (hT : 0 < T.val) :
    (harmonicProduct Q).helmholtzFreeEnergy T =
      ∑ i, (harmonicEnsemble (Q i)).helmholtzFreeEnergy T := by
  induction n with
  | zero =>
    rw [CanonicalEnsemble.helmholtzFreeEnergy_def, harmonicProduct_vacuum_partition]
    simp
  | succ n ih =>
    let := harmonic_boltzmann_finite (Q 0) T hT
    let := harmonicProduct_boltzmann_finite (fun i => Q i.succ) T hT
    rw [harmonicProduct_succ, CanonicalEnsemble.helmholtzFreeEnergy_congr,
      CanonicalEnsemble.helmholtzFreeEnergy_add (harmonicEnsemble (Q 0))
        (harmonicProduct (fun i => Q i.succ)) T rfl, ih, Fin.sum_univ_succ]

theorem harmonicProduct_meanEnergy {n : ℕ} (Q : Fin n → HarmonicOscillator)
    (T : Temperature) (hT : 0 < T.val) :
    (harmonicProduct Q).meanEnergy T =
      ∑ i, (harmonicEnsemble (Q i)).meanEnergy T := by
  induction n with
  | zero => simp [CanonicalEnsemble.meanEnergy, harmonicProduct]
  | succ n ih =>
    let := harmonic_boltzmann_finite (Q 0) T hT
    let := harmonicProduct_boltzmann_finite (fun i => Q i.succ) T hT
    rw [harmonicProduct_succ, CanonicalEnsemble.meanEnergy_congr,
      CanonicalEnsemble.meanEnergy_add _ _ (harmonic_energy_integrable (Q 0) T hT)
        (harmonicProduct_energy_integrable (fun i => Q i.succ) T hT),
      ih, Fin.sum_univ_succ]

/-- Entropy is derived from the statistical F=U-TS identity on the constructed
ensemble, not postulated as an additive state function. -/
theorem harmonicProduct_thermodynamicEntropy {n : ℕ}
    (Q : Fin n → HarmonicOscillator) (T : Temperature) (hT : 0 < T.val) :
    (harmonicProduct Q).thermodynamicEntropy T =
      ∑ i, (harmonicEnsemble (Q i)).thermodynamicEntropy T := by
  let := harmonicProduct_boltzmann_finite Q T hT
  have hj := (harmonicProduct Q).helmholtzFreeEnergy_eq_meanEnergy_sub_temp_mul_thermodynamicEntropy T hT
      (harmonicProduct_energy_integrable Q T hT)
  have hi (i : Fin n) := by
    let := harmonic_boltzmann_finite (Q i) T hT
    exact (harmonicEnsemble (Q i)).helmholtzFreeEnergy_eq_meanEnergy_sub_temp_mul_thermodynamicEntropy T hT
        (harmonic_energy_integrable (Q i) T hT)
  rw [harmonicProduct_helmholtzFreeEnergy Q T hT,
    harmonicProduct_meanEnergy Q T hT] at hj
  simp_rw [hi] at hj
  rw [Finset.sum_sub_distrib, ← Finset.mul_sum] at hj
  have hTr : 0 < (T.val : ℝ) := by exact_mod_cast hT
  nlinarith

/-- The joint mean energy agrees with a finite sum on the entire open
positive-temperature domain, with the spectrum held fixed. -/
theorem harmonicProduct_meanEnergyT_eq_omai {n : ℕ}
    (Q : Fin n → HarmonicOscillator) {t : ℝ} (ht : 0 < t) :
    (harmonicProduct Q).meanEnergyT t =
      ∑ i, harmonicInternalEnergy ℏ kB (Q i).ω t := by
  have hpos : 0 < (Temperature.ofNNReal (Real.toNNReal t)).val := by
    simpa only [Temperature.ofNNReal_val] using Real.toNNReal_pos.mpr ht
  have h := harmonicProduct_meanEnergy Q (Temperature.ofNNReal (Real.toNNReal t)) hpos
  simp only [harmonic_meanEnergy_eq_omai _ _ hpos] at h
  simpa [CanonicalEnsemble.meanEnergyT, Temperature.ofNNReal, Temperature.toReal,
    Real.toNNReal_of_nonneg ht.le] using h

/-- Derivative-defined joint heat capacity: only a finite sum is differentiated;
the infinite occupation sums have already been evaluated in mean energy. -/
theorem harmonicProduct_heatCapacity {n : ℕ} (Q : Fin n → HarmonicOscillator)
    (T : Temperature) (hT : 0 < T.val) :
    (harmonicProduct Q).heatCapacity T =
      ∑ i, (harmonicEnsemble (Q i)).heatCapacity T := by
  have hTr : 0 < (T : ℝ) := by
    change 0 < (T.val : ℝ)
    exact_mod_cast hT
  have hd : HasDerivAt (fun t => ∑ i, harmonicInternalEnergy ℏ kB (Q i).ω t)
      (∑ i, harmonicHeatCapacity ℏ kB (Q i).ω (T : ℝ)) (T : ℝ) :=
    HasDerivAt.fun_sum (fun i _ =>
      harmonicInternalEnergy_hasDerivAt ℏ_pos kB_pos (Q i).ω_pos hTr)
  have hdj : HasDerivWithinAt (harmonicProduct Q).meanEnergyT
      (∑ i, harmonicHeatCapacity ℏ kB (Q i).ω (T : ℝ)) (Set.Ioi 0) (T : ℝ) :=
    hd.hasDerivWithinAt.congr (fun _ ht => harmonicProduct_meanEnergyT_eq_omai Q ht)
      (harmonicProduct_meanEnergyT_eq_omai Q hTr)
  have hc : (harmonicProduct Q).heatCapacity T =
      ∑ i, harmonicHeatCapacity ℏ kB (Q i).ω (T : ℝ) :=
    hdj.derivWithin (isOpen_Ioi.uniqueDiffWithinAt hTr)
  simpa only [harmonic_heatCapacity_eq_omai _ T hT] using hc

/-- Explicit rectangular-grid indexing: q-major enumeration of all 3*N_atoms
branches. This only reindexes modes, without changing their statistical weights. -/
def harmonicGridOscillator (grid : HarmonicModeGrid) :
    Fin (grid.qCount * (3 * grid.atomCount)) → HarmonicOscillator :=
  fun i => grid.oscillator (finProdFinEquiv.symm i).1 (finProdFinEquiv.symm i).2

/-- The grid's joint ensemble has one Nat occupation for every grid mode. -/
def harmonicGridEnsemble (grid : HarmonicModeGrid) :
    CanonicalEnsemble (Fin (grid.qCount * (3 * grid.atomCount)) → ℕ) :=
  harmonicProduct (harmonicGridOscillator grid)

/-- Encoding of a rectangular occupation function into the joint state type. -/
def harmonicGridOccupation (grid : HarmonicModeGrid) :
    ((Fin grid.qCount × Fin (3 * grid.atomCount)) → ℕ) ≃ᵐ
      (Fin (grid.qCount * (3 * grid.atomCount)) → ℕ) :=
  MeasurableEquiv.piCongrLeft (fun _ => ℕ) finProdFinEquiv

theorem harmonicGridOccupation_measurePreserving (grid : HarmonicModeGrid) :
    MeasurePreserving (harmonicGridOccupation grid)
      (Measure.pi fun _ : Fin grid.qCount × Fin (3 * grid.atomCount) =>
        (Measure.count : Measure ℕ)) (harmonicGridEnsemble grid).μ :=
  measurePreserving_piCongrLeft (fun _ => (Measure.count : Measure ℕ)) finProdFinEquiv

/-- The index equivalence preserves the exact double sum used by OMAI. -/
theorem harmonicGrid_sum (grid : HarmonicModeGrid)
    (f : HarmonicOscillator → ℝ) :
    (∑ i, f (harmonicGridOscillator grid i)) =
      ∑ q, ∑ band, f (grid.oscillator q band) := by
  rw [← finProdFinEquiv.sum_comp (fun i => f (harmonicGridOscillator grid i))]
  simp [harmonicGridOscillator, Fintype.sum_prod_type]

/-- Under rectangular occupation coordinates the Hamiltonian is the unweighted
sum of the exact upstream oscillator eigenvalues, retaining zero-point energy. -/
theorem harmonicGridEnsemble_energy (grid : HarmonicModeGrid)
    (occupation : (Fin grid.qCount × Fin (3 * grid.atomCount)) → ℕ) :
    (harmonicGridEnsemble grid).energy (harmonicGridOccupation grid occupation) =
      ∑ q, ∑ band, (grid.oscillator q band).eigenValue (occupation (q, band)) := by
  change (∑ i, (harmonicGridOscillator grid i).eigenValue
    (harmonicGridOccupation grid occupation i)) = _
  rw [← finProdFinEquiv.sum_comp]
  simp [harmonicGridOscillator, harmonicGridOccupation, MeasurableEquiv.piCongrLeft,
    Fintype.sum_prod_type]

theorem harmonicGridEnsemble_partitionFunction (grid : HarmonicModeGrid)
    (T : Temperature) :
    (harmonicGridEnsemble grid).partitionFunction T =
      ∏ q, ∏ band, (harmonicEnsemble (grid.oscillator q band)).partitionFunction T := by
  rw [harmonicGridEnsemble, harmonicProduct_partitionFunction,
    ← finProdFinEquiv.prod_comp]
  simp [harmonicGridOscillator, Fintype.prod_prod_type]

theorem harmonicGridEnsemble_helmholtzFreeEnergy (grid : HarmonicModeGrid)
    (T : Temperature) (hT : 0 < T.val) :
    (harmonicGridEnsemble grid).helmholtzFreeEnergy T =
      ∑ q, ∑ band, (harmonicEnsemble (grid.oscillator q band)).helmholtzFreeEnergy T := by
  rw [harmonicGridEnsemble, harmonicProduct_helmholtzFreeEnergy _ T hT]
  exact harmonicGrid_sum grid (fun Q => (harmonicEnsemble Q).helmholtzFreeEnergy T)

theorem harmonicGridEnsemble_meanEnergy (grid : HarmonicModeGrid)
    (T : Temperature) (hT : 0 < T.val) :
    (harmonicGridEnsemble grid).meanEnergy T =
      ∑ q, ∑ band, (harmonicEnsemble (grid.oscillator q band)).meanEnergy T := by
  rw [harmonicGridEnsemble, harmonicProduct_meanEnergy _ T hT]
  exact harmonicGrid_sum grid (fun Q => (harmonicEnsemble Q).meanEnergy T)

theorem harmonicGridEnsemble_thermodynamicEntropy (grid : HarmonicModeGrid)
    (T : Temperature) (hT : 0 < T.val) :
    (harmonicGridEnsemble grid).thermodynamicEntropy T =
      ∑ q, ∑ band, (harmonicEnsemble (grid.oscillator q band)).thermodynamicEntropy T := by
  rw [harmonicGridEnsemble, harmonicProduct_thermodynamicEntropy _ T hT]
  exact harmonicGrid_sum grid (fun Q => (harmonicEnsemble Q).thermodynamicEntropy T)

theorem harmonicGridEnsemble_heatCapacity (grid : HarmonicModeGrid)
    (T : Temperature) (hT : 0 < T.val) :
    (harmonicGridEnsemble grid).heatCapacity T =
      ∑ q, ∑ band, (harmonicEnsemble (grid.oscillator q band)).heatCapacity T := by
  rw [harmonicGridEnsemble, harmonicProduct_heatCapacity _ T hT]
  exact harmonicGrid_sum grid (fun Q => (harmonicEnsemble Q).heatCapacity T)

/-- Primitive-cell molar normalization is external to the joint Hamiltonian. -/
theorem harmonic_joint_molar_helmholtzFreeEnergy_eq_omai (grid : HarmonicModeGrid)
    (T : Temperature) (hT : 0 < T.val) :
    (grid.avogadro / (grid.qCount : ℝ)) * (harmonicGridEnsemble grid).helmholtzFreeEnergy T =
      harmonicMolarFreeEnergy grid T := by
  rw [harmonicGridEnsemble_helmholtzFreeEnergy grid T hT,
    ← uniformMolarContraction_eq_weighted_sum]
  exact harmonic_molar_helmholtzFreeEnergy_eq_omai grid T hT

theorem harmonic_joint_molar_meanEnergy_eq_omai (grid : HarmonicModeGrid)
    (T : Temperature) (hT : 0 < T.val) :
    (grid.avogadro / (grid.qCount : ℝ)) * (harmonicGridEnsemble grid).meanEnergy T =
      harmonicMolarInternalEnergy grid T := by
  rw [harmonicGridEnsemble_meanEnergy grid T hT,
    ← uniformMolarContraction_eq_weighted_sum]
  exact harmonic_molar_meanEnergy_eq_omai grid T hT

theorem harmonic_joint_molar_thermodynamicEntropy_eq_omai (grid : HarmonicModeGrid)
    (T : Temperature) (hT : 0 < T.val) :
    (grid.avogadro / (grid.qCount : ℝ)) * (harmonicGridEnsemble grid).thermodynamicEntropy T =
      harmonicMolarEntropy grid T := by
  rw [harmonicGridEnsemble_thermodynamicEntropy grid T hT,
    ← uniformMolarContraction_eq_weighted_sum]
  exact harmonic_molar_thermodynamicEntropy_eq_omai grid T hT

theorem harmonic_joint_molar_heatCapacity_eq_omai (grid : HarmonicModeGrid)
    (T : Temperature) (hT : 0 < T.val) :
    (grid.avogadro / (grid.qCount : ℝ)) * (harmonicGridEnsemble grid).heatCapacity T =
      harmonicMolarHeatCapacity grid T := by
  rw [harmonicGridEnsemble_heatCapacity grid T hT,
    ← uniformMolarContraction_eq_weighted_sum]
  exact harmonic_molar_heatCapacity_eq_omai grid T hT

/-- Closed product partition, valid for the strictly positive full spectra. -/
theorem harmonicProduct_partitionFunction_eq_geometric {n : ℕ}
    (Q : Fin n → HarmonicOscillator) (T : Temperature) (hT : 0 < T.val) :
    (harmonicProduct Q).partitionFunction T =
      ∏ i, Real.exp (-oscillatorArgument (Q i) T / 2) /
        (1 - Real.exp (-oscillatorArgument (Q i) T)) := by
  rw [harmonicProduct_partitionFunction]
  simp only [harmonic_partitionFunction _ T hT]

/-- The vacuum is nonempty but has only one occupation function. -/
theorem harmonicProduct_vacuum_unique (occupation : Fin 0 → ℕ) :
    occupation = fun i => Fin.elim0 i := Subsingleton.elim _ _

theorem harmonicProduct_vacuum_energy (Q : Fin 0 → HarmonicOscillator)
    (occupation : Fin 0 → ℕ) : (harmonicProduct Q).energy occupation = 0 := by
  simp [harmonicProduct]

/-- A singleton spectrum recovers the actual one-mode partition. -/
theorem harmonicProduct_singleton_partition (Q : HarmonicOscillator) (T : Temperature) :
    (harmonicProduct (fun _ : Fin 1 => Q)).partitionFunction T =
      (harmonicEnsemble Q).partitionFunction T := by
  rw [harmonicProduct_partitionFunction]
  simp

theorem harmonicProduct_singleton_heatCapacity (Q : HarmonicOscillator)
    (T : Temperature) (hT : 0 < T.val) :
    (harmonicProduct (fun _ : Fin 1 => Q)).heatCapacity T =
      (harmonicEnsemble Q).heatCapacity T := by
  rw [harmonicProduct_heatCapacity _ T hT]
  simp

/-- Concrete distinct angular frequencies prevent an equal-frequency nsmul
interpretation from passing the two-mode model checks. -/
def harmonicUnequalPair : Fin 2 → HarmonicOscillator :=
  ![⟨1, 1, by norm_num, by norm_num⟩, ⟨1, 2, by norm_num, by norm_num⟩]

theorem harmonicUnequalPair_frequencies :
    (harmonicUnequalPair 0).ω ≠ (harmonicUnequalPair 1).ω := by
  norm_num [harmonicUnequalPair]

theorem harmonicUnequalPair_energy (occupation : Fin 2 → ℕ) :
    (harmonicProduct harmonicUnequalPair).energy occupation =
      ((occupation 0 : ℝ) + 1 / 2) * (ℏ : ℝ) +
      ((occupation 1 : ℝ) + 1 / 2) * (ℏ : ℝ) * 2 := by
  simp [harmonicProduct, Fin.sum_univ_two, harmonicUnequalPair,
    HarmonicOscillator.eigenValue]

theorem harmonicUnequalPair_partition (T : Temperature) :
    (harmonicProduct harmonicUnequalPair).partitionFunction T =
      (harmonicEnsemble (harmonicUnequalPair 0)).partitionFunction T *
        (harmonicEnsemble (harmonicUnequalPair 1)).partitionFunction T := by
  rw [harmonicProduct_partitionFunction, Fin.prod_univ_two]

theorem harmonicUnequalPair_heatCapacity (T : Temperature) (hT : 0 < T.val) :
    (harmonicProduct harmonicUnequalPair).heatCapacity T =
      harmonicHeatCapacity ℏ kB 1 (T : ℝ) + harmonicHeatCapacity ℏ kB 2 (T : ℝ) := by
  rw [harmonicProduct_heatCapacity _ T hT, Fin.sum_univ_two]
  simp only [harmonic_heatCapacity_eq_omai _ T hT]
  rfl

end
end OMAI.PhyslibBridge
