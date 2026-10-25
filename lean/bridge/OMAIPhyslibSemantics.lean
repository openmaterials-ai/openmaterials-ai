/- OMAI scalar/isotropic thermoelectric interpretations and harmonic closed-form consistency.
No numerical-solver, arbitrary anisotropic-tensor, or infinite-ensemble proof is claimed.
See omai/data/physlib_formula_seeds.json for the complete model/unit assumptions. -/
module

public import Physlib.CondensedMatter.Thermoelectric.Basic
public import Mathlib.Analysis.SpecialFunctions.Log.Basic
public import Mathlib.Tactic.FieldSimp

@[expose] public section

namespace OMAI.PhyslibBridge
open CondensedMatter
noncomputable section

/-- OMAI contract_power_factor. -/
def powerFactor (sigma seebeck : ℝ) : ℝ := sigma * seebeck ^ 2
/-- OMAI sum_thermal_conductivity, explicitly scalar specialization. -/
def totalThermalConductivity (lattice electronic : ℝ) : ℝ := lattice + electronic
/-- OMAI contract_zt, explicitly scalar specialization. -/
def figureOfMerit (pf temperature totalConductivity : ℝ) : ℝ :=
  pf * temperature / totalConductivity

theorem powerFactor_eq_physlib (material : ThermoelectricMaterial) :
    powerFactor material.σ material.S = material.powerFactor := rfl

theorem powerFactor_pos (material : ThermoelectricMaterial) (hS : material.S ≠ 0) :
    0 < powerFactor material.σ material.S := ThermoelectricMaterial.powerFactor_pos (M := material) hS

theorem totalThermalConductivity_eq_physlib (material : ThermoelectricMaterial) :
    totalThermalConductivity material.κl material.κe =
      material.totalThermalConductivity := rfl

theorem totalThermalConductivity_pos (material : ThermoelectricMaterial) :
    0 < totalThermalConductivity material.κl material.κe :=
  material.totalThermalConductivity_pos

theorem figureOfMerit_eq_physlib (material : ThermoelectricMaterial) (temperature : ℝ) :
    figureOfMerit (powerFactor material.σ material.S) temperature
      (totalThermalConductivity material.κl material.κe) =
      material.figureOfMerit temperature := rfl

theorem figureOfMerit_pos (material : ThermoelectricMaterial) {temperature : ℝ}
    (hS : material.S ≠ 0) (hT : 0 < temperature) :
    0 < figureOfMerit (powerFactor material.σ material.S) temperature
      (totalThermalConductivity material.κl material.κe) :=
  ThermoelectricMaterial.figureOfMerit_pos (M := material) hS hT

/-- Only lattice conductivity varies; all other operating-point values stay fixed. -/
theorem figureOfMerit_le_of_lattice_le (material : ThermoelectricMaterial)
    {lattice' temperature : ℝ} (hpos : 0 < lattice') (hle : material.κl ≤ lattice')
    (hT : 0 ≤ temperature) :
    figureOfMerit (powerFactor material.σ material.S) temperature
      (totalThermalConductivity lattice' material.κe) ≤
    figureOfMerit (powerFactor material.σ material.S) temperature
      (totalThermalConductivity material.κl material.κe) :=
  material.figureOfMerit_le_of_le hpos hle hT

/-- Explicit isotropic 3×3 embedding, not a coercion of arbitrary tensors. -/
def isotropicTensor (value : ℝ) (i j : Fin 3) : ℝ := if i = j then value else 0

theorem isotropicTensor_diagonal (value : ℝ) (i : Fin 3) :
    isotropicTensor value i i = value := by simp [isotropicTensor]

theorem isotropic_total_conductivity (lattice electronic : ℝ) (i j : Fin 3) :
    isotropicTensor lattice i j + isotropicTensor electronic i j =
      isotropicTensor (totalThermalConductivity lattice electronic) i j := by
  by_cases h : i = j <;> simp [isotropicTensor, totalThermalConductivity, h]

/-- zT uses the common diagonal entry of an explicitly isotropic tensor. -/
theorem isotropic_figureOfMerit_eq_physlib
    (material : ThermoelectricMaterial) (temperature : ℝ) (i : Fin 3) :
    figureOfMerit (powerFactor material.σ material.S) temperature
      (isotropicTensor material.κl i i + isotropicTensor material.κe i i) =
      material.figureOfMerit temperature := by
  simp only [isotropicTensor_diagonal]
  rfl

/-- Explicit interpretation of OMAI's n_BE function symbol. -/
def boseOccupation (x : ℝ) : ℝ := 1 / (Real.exp x - 1)
/-- omega is angular frequency; not the numerical value in linear THz. -/
def harmonicArgument (hbar kB omega temperature : ℝ) : ℝ :=
  hbar * omega / (kB * temperature)
/-- OMAI compute_free_energy, including zero-point energy. -/
def harmonicFreeEnergy (hbar kB omega temperature : ℝ) : ℝ :=
  hbar * omega / 2 + kB * temperature *
    Real.log (1 - Real.exp (-harmonicArgument hbar kB omega temperature))
/-- OMAI compute_internal_energy. -/
def harmonicInternalEnergy (hbar kB omega temperature : ℝ) : ℝ :=
  hbar * (boseOccupation (harmonicArgument hbar kB omega temperature) + 1 / 2) * omega
/-- OMAI compute_entropy. -/
def harmonicEntropy (hbar kB omega temperature : ℝ) : ℝ :=
  hbar * boseOccupation (harmonicArgument hbar kB omega temperature) * omega / temperature -
    kB * Real.log (1 - Real.exp (-harmonicArgument hbar kB omega temperature))

theorem harmonicArgument_pos {hbar kB omega temperature : ℝ}
    (hh : 0 < hbar) (hk : 0 < kB) (hw : 0 < omega) (hT : 0 < temperature) :
    0 < harmonicArgument hbar kB omega temperature :=
  div_pos (mul_pos hh hw) (mul_pos hk hT)

theorem harmonic_bose_denominator_pos {hbar kB omega temperature : ℝ}
    (hh : 0 < hbar) (hk : 0 < kB) (hw : 0 < omega) (hT : 0 < temperature) :
    0 < Real.exp (harmonicArgument hbar kB omega temperature) - 1 := by
  exact sub_pos.mpr (Real.one_lt_exp_iff.mpr (harmonicArgument_pos hh hk hw hT))

theorem harmonic_log_argument_pos {hbar kB omega temperature : ℝ}
    (hh : 0 < hbar) (hk : 0 < kB) (hw : 0 < omega) (hT : 0 < temperature) :
    0 < 1 - Real.exp (-harmonicArgument hbar kB omega temperature) := by
  apply sub_pos.mpr
  exact Real.exp_lt_one_iff.mpr (neg_neg_of_pos (harmonicArgument_pos hh hk hw hT))

/-- Direct consistency of OMAI closed forms, not an ensemble identification.
No equality F=U-TS is assumed as a premise. -/
theorem harmonic_freeEnergy_eq_internalEnergy_sub_temperature_mul_entropy
    {hbar kB omega temperature : ℝ}
    (hh : 0 < hbar) (hk : 0 < kB) (hw : 0 < omega) (hT : 0 < temperature) :
    harmonicFreeEnergy hbar kB omega temperature =
      harmonicInternalEnergy hbar kB omega temperature -
        temperature * harmonicEntropy hbar kB omega temperature := by
  have hden := ne_of_gt (harmonic_bose_denominator_pos hh hk hw hT)
  unfold harmonicFreeEnergy harmonicInternalEnergy harmonicEntropy boseOccupation
  field_simp [ne_of_gt hT, hden]
  ring

end
end OMAI.PhyslibBridge
