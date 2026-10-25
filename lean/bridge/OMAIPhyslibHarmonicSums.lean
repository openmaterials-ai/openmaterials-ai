/- Finite uniform-q contractions of the proved single-mode ensemble quantities.
No joint product ensemble or phonon/eigenmode construction is asserted here. -/
module

public import OMAIPhyslibHarmonicEnsemble

@[expose] public section

namespace OMAI.PhyslibBridge
open Constants Temperature
open QuantumMechanics.OneDimension
open scoped BigOperators
noncomputable section

/-- A finite rectangular mode grid for one primitive-cell basis. OMAI has
`N_modes = 3 * N_atoms`. Fin labels correspond to its 1-based labels by `i.val+1`.
Every entry is a stable upstream oscillator. This data does not construct the
phonon modes or identify their frequencies with eigenvalues of a dynamical matrix.
`avogadro` is the explicit positive scale per mole of primitive cells. -/
structure HarmonicModeGrid where
  qCount : ℕ
  qCount_pos : 0 < qCount
  atomCount : ℕ
  atomCount_pos : 0 < atomCount
  avogadro : ℝ
  avogadro_pos : 0 < avogadro
  oscillator : Fin qCount → Fin (3 * atomCount) → HarmonicOscillator

/-- Exact OMAI molar contraction: uniform weight `1/N_q`, summed over all
`3*N_atoms` branches, then scaled by `N_A`. The basis is a mole of primitive
cells, not a mole of atoms. Nonuniform q weights are outside this definition. -/
def uniformMolarContraction (grid : HarmonicModeGrid)
    (value : Fin grid.qCount → Fin (3 * grid.atomCount) → ℝ) : ℝ :=
  grid.avogadro * (∑ q, ∑ band, value q band) / grid.qCount

theorem uniformMolarContraction_eq_weighted_sum (grid : HarmonicModeGrid)
    (value : Fin grid.qCount → Fin (3 * grid.atomCount) → ℝ) :
    uniformMolarContraction grid value =
      (grid.avogadro / (grid.qCount : ℝ)) * (∑ q, ∑ band, value q band) := by
  unfold uniformMolarContraction
  ring

theorem uniformMolarContraction_scale_pos (grid : HarmonicModeGrid) :
    0 < grid.avogadro / (grid.qCount : ℝ) :=
  div_pos grid.avogadro_pos (Nat.cast_pos.mpr grid.qCount_pos)

/-- OMAI `contract_molar_free_energy` with its per-mode free-energy formula. -/
def harmonicMolarFreeEnergy (grid : HarmonicModeGrid) (T : Temperature) : ℝ :=
  uniformMolarContraction grid fun q band =>
    harmonicFreeEnergy ℏ kB (grid.oscillator q band).ω (T : ℝ)

/-- OMAI `contract_molar_internal_energy` with its per-mode energy formula. -/
def harmonicMolarInternalEnergy (grid : HarmonicModeGrid) (T : Temperature) : ℝ :=
  uniformMolarContraction grid fun q band =>
    harmonicInternalEnergy ℏ kB (grid.oscillator q band).ω (T : ℝ)

/-- OMAI `contract_molar_entropy` with its per-mode entropy formula. -/
def harmonicMolarEntropy (grid : HarmonicModeGrid) (T : Temperature) : ℝ :=
  uniformMolarContraction grid fun q band =>
    harmonicEntropy ℏ kB (grid.oscillator q band).ω (T : ℝ)

/-- OMAI `contract_molar_heat_capacity` with its per-mode sinh formula. -/
def harmonicMolarHeatCapacity (grid : HarmonicModeGrid) (T : Temperature) : ℝ :=
  uniformMolarContraction grid fun q band =>
    harmonicHeatCapacity ℏ kB (grid.oscillator q band).ω (T : ℝ)

/-- The normalized sum of the actual single-mode Physlib free energies equals
the OMAI closed-form contraction. This is not a product-partition theorem. -/
theorem harmonic_molar_helmholtzFreeEnergy_eq_omai (grid : HarmonicModeGrid)
    (T : Temperature) (hT : 0 < T.val) :
    uniformMolarContraction grid
      (fun q band => (harmonicEnsemble (grid.oscillator q band)).helmholtzFreeEnergy T) =
      harmonicMolarFreeEnergy grid T := by
  simp only [uniformMolarContraction, harmonicMolarFreeEnergy,
    harmonic_helmholtzFreeEnergy_eq_omai _ T hT]

/-- The normalized sum of the actual single-mode Physlib mean energies equals
the OMAI closed-form contraction, including each mode's zero-point energy. -/
theorem harmonic_molar_meanEnergy_eq_omai (grid : HarmonicModeGrid)
    (T : Temperature) (hT : 0 < T.val) :
    uniformMolarContraction grid
      (fun q band => (harmonicEnsemble (grid.oscillator q band)).meanEnergy T) =
      harmonicMolarInternalEnergy grid T := by
  simp only [uniformMolarContraction, harmonicMolarInternalEnergy,
    harmonic_meanEnergy_eq_omai _ T hT]

/-- The normalized sum of the actual single-mode Physlib entropies equals the
OMAI closed-form contraction; the basis remains moles of primitive cells. -/
theorem harmonic_molar_thermodynamicEntropy_eq_omai (grid : HarmonicModeGrid)
    (T : Temperature) (hT : 0 < T.val) :
    uniformMolarContraction grid
      (fun q band => (harmonicEnsemble (grid.oscillator q band)).thermodynamicEntropy T) =
      harmonicMolarEntropy grid T := by
  simp only [uniformMolarContraction, harmonicMolarEntropy,
    harmonic_thermodynamicEntropy_eq_omai _ T hT]

/-- The normalized sum of the actual derivative-defined Physlib single-mode
heat capacities equals the OMAI sinh-form contraction. Spectra and weights are
fixed in the per-mode temperature derivatives used by the upstream quantities. -/
theorem harmonic_molar_heatCapacity_eq_omai (grid : HarmonicModeGrid)
    (T : Temperature) (hT : 0 < T.val) :
    uniformMolarContraction grid
      (fun q band => (harmonicEnsemble (grid.oscillator q band)).heatCapacity T) =
      harmonicMolarHeatCapacity grid T := by
  simp only [uniformMolarContraction, harmonicMolarHeatCapacity,
    harmonic_heatCapacity_eq_omai _ T hT]

end
end OMAI.PhyslibBridge
