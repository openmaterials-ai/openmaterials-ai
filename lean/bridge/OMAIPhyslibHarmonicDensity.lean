/- Positive primitive-cell-volume normalization of actual Physlib mode heat capacities.
The finite uniform-q grid, fixed positive spectrum and temperature premises are
inherited from HarmonicSums. No cell-geometry or phonon producer is asserted. -/
module

public import OMAIPhyslibHarmonicSums

@[expose] public section

namespace OMAI.PhyslibBridge
open Constants Temperature
open scoped BigOperators
noncomputable section

/-- A positive primitive-cell volume, represented by its exact real SI value
in cubic metres. The primitive-cell interpretation is an explicit model input,
not a claim that a geometric or numerical producer has been verified. -/
structure PrimitiveCellVolume where
  siValue : ℝ
  siValue_pos : 0 < siValue

/-- Exact OMAI `contract_volumetric_heat_capacity` normalization. Every branch
is summed and q is uniformly averaged. There is no Avogadro factor and no
additional division by the number of atoms or branches. -/
def uniformVolumetricContraction (grid : HarmonicModeGrid) (volume : PrimitiveCellVolume)
    (value : Fin grid.qCount → Fin (3 * grid.atomCount) → ℝ) : ℝ :=
  (∑ q, ∑ band, value q band) / ((grid.qCount : ℝ) * volume.siValue)

/-- Denominator ordering matches the exact authored OMAI catalog expression. -/
theorem uniformVolumetricContraction_eq_catalog (grid : HarmonicModeGrid)
    (volume : PrimitiveCellVolume)
    (value : Fin grid.qCount → Fin (3 * grid.atomCount) → ℝ) :
    uniformVolumetricContraction grid volume value =
      (∑ q, ∑ band, value q band) / (volume.siValue * grid.qCount) := by
  simp only [uniformVolumetricContraction, mul_comm]

theorem uniformVolumetricContraction_scale_pos (grid : HarmonicModeGrid)
    (volume : PrimitiveCellVolume) :
    0 < 1 / ((grid.qCount : ℝ) * volume.siValue) :=
  div_pos zero_lt_one (mul_pos (Nat.cast_pos.mpr grid.qCount_pos) volume.siValue_pos)

/-- OMAI volumetric heat capacity with the reviewed per-mode sinh expression.
With upstream SI constants, positive Kelvin temperature, angular frequency in
radians per second, and volume in cubic metres, the result is J/(m^3 K). -/
def harmonicVolumetricHeatCapacity (grid : HarmonicModeGrid)
    (volume : PrimitiveCellVolume) (T : Temperature) : ℝ :=
  uniformVolumetricContraction grid volume fun q band =>
    harmonicHeatCapacity ℏ kB (grid.oscillator q band).ω (T : ℝ)

/-- The actual derivative-defined Physlib single-mode heat capacities contract
to the catalog volumetric expression. The spectrum and weights are fixed in
the per-mode temperature derivatives. No joint-product theorem is needed. -/
theorem harmonic_volumetric_heatCapacity_eq_omai (grid : HarmonicModeGrid)
    (volume : PrimitiveCellVolume) (T : Temperature) (hT : 0 < T.val) :
    uniformVolumetricContraction grid volume
      (fun q band => (harmonicEnsemble (grid.oscillator q band)).heatCapacity T) =
      harmonicVolumetricHeatCapacity grid volume T := by
  simp only [uniformVolumetricContraction, harmonicVolumetricHeatCapacity,
    harmonic_heatCapacity_eq_omai _ T hT]

/-- Independent molar/volumetric consistency for any mode values. The molar
basis is a mole of primitive cells, so its volume is N_A times V_cell. This is
normalization algebra, not a proof of a geometric molar-volume producer. -/
theorem uniformVolumetricContraction_eq_molar_div (grid : HarmonicModeGrid)
    (volume : PrimitiveCellVolume)
    (value : Fin grid.qCount → Fin (3 * grid.atomCount) → ℝ) :
    uniformVolumetricContraction grid volume value =
      uniformMolarContraction grid value / (grid.avogadro * volume.siValue) := by
  unfold uniformVolumetricContraction uniformMolarContraction
  field_simp [ne_of_gt grid.avogadro_pos, ne_of_gt volume.siValue_pos,
    ne_of_gt (Nat.cast_pos.mpr grid.qCount_pos : (0 : ℝ) < grid.qCount)]

/-- C_vol = C_mol/(N_A V_cell). Both sides retain the same primitive-cell,
uniform-q, fixed-spectrum interpretation. Its total real algebra alone does
not assert a physical interpretation at zero temperature. -/
theorem harmonicVolumetricHeatCapacity_eq_molar_div (grid : HarmonicModeGrid)
    (volume : PrimitiveCellVolume) (T : Temperature) :
    harmonicVolumetricHeatCapacity grid volume T =
      harmonicMolarHeatCapacity grid T / (grid.avogadro * volume.siValue) :=
  uniformVolumetricContraction_eq_molar_div grid volume _

/-- Exact conversion of a positive primitive-cell volume from Angstrom cubed
to cubic metres. This does not certify a floating-point adapter. -/
def PrimitiveCellVolume.ofAngstromCubed (value : ℝ) (hvalue : 0 < value) :
    PrimitiveCellVolume where
  siValue := value / (10 : ℝ) ^ 30
  siValue_pos := div_pos hvalue (by positivity)

theorem PrimitiveCellVolume.ofAngstromCubed_siValue (value : ℝ) (hvalue : 0 < value) :
    (PrimitiveCellVolume.ofAngstromCubed value hvalue).siValue =
      value / (10 : ℝ) ^ 30 := rfl

/-- The inverse volume scale is exactly 10^30 when the numerical input is in
Angstrom cubed. Applying the SI contraction directly to that input would
therefore change the result by that factor. -/
theorem uniformVolumetricContraction_ofAngstromCubed (grid : HarmonicModeGrid)
    (volume : ℝ) (hvolume : 0 < volume)
    (value : Fin grid.qCount → Fin (3 * grid.atomCount) → ℝ) :
    uniformVolumetricContraction grid (PrimitiveCellVolume.ofAngstromCubed volume hvolume)
      value = (10 : ℝ) ^ 30 *
        ((∑ q, ∑ band, value q band) / ((grid.qCount : ℝ) * volume)) := by
  unfold uniformVolumetricContraction PrimitiveCellVolume.ofAngstromCubed
  field_simp

/-- Exact real interpretation of OMAI's linear-THz frequency value as angular
SI frequency. It does not verify a floating-point conversion implementation. -/
def linearTHzToAngularSI (frequency : ℝ) : ℝ :=
  2 * Real.pi * (10 : ℝ) ^ 12 * frequency

/-- Effective hbar multiplying a numerical linear-THz value, not a change in
the upstream physical constant. Frequencies must use one convention or the
other consistently. -/
def linearTHzEffectiveHbar (hbar : ℝ) : ℝ :=
  hbar * (2 * Real.pi * (10 : ℝ) ^ 12)

theorem linearTHzToAngularSI_pos {frequency : ℝ} (hfrequency : 0 < frequency) :
    0 < linearTHzToAngularSI frequency := by
  unfold linearTHzToAngularSI
  positivity

/-- The dimensionless argument is unchanged by the exact linear-THz/SI
reinterpretation. This algebra is not a zero-frequency limit theorem. -/
theorem harmonicArgument_angularSI_eq_linearTHz (hbar kB frequency temperature : ℝ) :
    harmonicArgument hbar kB (linearTHzToAngularSI frequency) temperature =
      harmonicArgument (linearTHzEffectiveHbar hbar) kB frequency temperature := by
  unfold harmonicArgument linearTHzToAngularSI linearTHzEffectiveHbar
  ring

/-- The sinh-form capacity has the same exact value in either frequency
interpretation. This supporting unit lemma adds no operator/producer coverage. -/
theorem harmonicHeatCapacity_angularSI_eq_linearTHz (hbar kB frequency temperature : ℝ) :
    harmonicHeatCapacity hbar kB (linearTHzToAngularSI frequency) temperature =
      harmonicHeatCapacity (linearTHzEffectiveHbar hbar) kB frequency temperature := by
  have henergy : hbar * linearTHzToAngularSI frequency =
      linearTHzEffectiveHbar hbar * frequency := by
    unfold linearTHzToAngularSI linearTHzEffectiveHbar
    ring
  simp only [harmonicHeatCapacity, harmonicArgument, henergy]

end
end OMAI.PhyslibBridge
