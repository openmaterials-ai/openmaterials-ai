/- OMAI absolute-temperature values and signed three-dimensional pressure contraction.
These results concern scalar/unit representations and an inviscid constitutive law.
They do not establish a DFT stress formula, mechanical equilibrium, or a free-energy derivative. -/
module

public import Physlib.Thermodynamics.Temperature.Basic
public import Physlib.FluidDynamics.CauchyFlow.Inviscid
public import Mathlib.Tactic.FieldSimp

@[expose] public section

namespace OMAI.PhyslibBridge
noncomputable section

/-- Wrap an absolute temperature without replacing negative inputs by zero.
The real value and Physlib value must use the same absolute-temperature scale. -/
def absoluteTemperature (temperature : ℝ) (hT : 0 ≤ temperature) : Temperature :=
  Temperature.ofRealNonneg temperature hT

theorem absoluteTemperature_toReal (temperature : ℝ) (hT : 0 ≤ temperature) :
    (absoluteTemperature temperature hT : ℝ) = temperature := rfl

theorem absoluteTemperature_roundtrip (temperature : Temperature) :
    absoluteTemperature (temperature : ℝ) temperature.val.property = temperature := by
  apply Temperature.ext
  rfl

/-- Inverse temperature has inverse-energy units, with the same kB as the ensemble. -/
def inverseTemperature (kB temperature : ℝ) : ℝ := 1 / (kB * temperature)

theorem absoluteTemperature_beta_eq (temperature : ℝ) (hT : 0 ≤ temperature) :
    ((absoluteTemperature temperature hT).β : ℝ) =
      inverseTemperature Constants.kB temperature := rfl

theorem absoluteTemperature_beta_pos (temperature : ℝ) (hT : 0 < temperature) :
    0 < ((absoluteTemperature temperature hT.le).β : ℝ) := by
  apply Temperature.beta_pos
  exact hT

/-- If target numerical temperatures are a times source values and target numerical
energies are b times source values, kB scales by b/a and beta scales by 1/b.
This proves the numerical unit relation; it does not choose a unit convention. -/
theorem inverseTemperature_unit_scaling {kB temperature temperatureScale energyScale : ℝ}
    (hk : 0 < kB) (hT : 0 < temperature)
    (ht : 0 < temperatureScale) (he : 0 < energyScale) :
    inverseTemperature (energyScale / temperatureScale * kB)
      (temperatureScale * temperature) = inverseTemperature kB temperature / energyScale := by
  unfold inverseTemperature
  field_simp [ne_of_gt hk, ne_of_gt hT, ne_of_gt ht, ne_of_gt he]

/-- The Physlib Boltzmann constant must satisfy the same explicit unit conversion.
For kelvin and joules, both scale factors are one and kB is Constants.kB. -/
theorem absoluteTemperature_beta_unit_scaling
    {kB temperature temperatureScale energyScale : ℝ}
    (hk : 0 < kB) (hT : 0 < temperature)
    (ht : 0 < temperatureScale) (he : 0 < energyScale)
    (hkUnits : Constants.kB = energyScale / temperatureScale * kB) :
    ((absoluteTemperature (temperatureScale * temperature) (mul_nonneg ht.le hT.le)).β : ℝ) =
      inverseTemperature kB temperature / energyScale := by
  rw [absoluteTemperature_beta_eq, hkUnits]
  exact inverseTemperature_unit_scaling hk hT ht he

open FluidDynamics Space Time

/-- OMAI uses compressive-positive stress, the negative of Physlib Cauchy stress.
All entries and pressure must be expressed in the same pressure unit (Pa for SI).
Fin 3 labels the three Cartesian axes 0,1,2, corresponding to OMAI's 1,2,3. -/
def compressiveStress (flow : CauchyFlow 3) (t : Time) (x : Space 3) :
    Matrix (Fin 3) (Fin 3) ℝ := -flow.stress t x

/-- The OMAI contract_pressure formula at one space-time point. -/
def pressureFromStress (sigma : Matrix (Fin 3) (Fin 3) ℝ) : ℝ :=
  (∑ i : Fin 3, sigma i i) / 3

theorem compressiveStress_roundtrip (flow : CauchyFlow 3) (t : Time) (x : Space 3) :
    -compressiveStress flow t x = flow.stress t x := by
  simp [compressiveStress]

theorem compressiveStress_eq_pressure_identity
    (flow : CauchyFlow 3) (pressure : ScalarField 3)
    (hInviscid : CauchyFlow.IsInviscid 3 flow pressure)
    (t : Time) (x : Space 3) :
    compressiveStress flow t x = pressure t x • (1 : Matrix (Fin 3) (Fin 3) ℝ) := by
  simp [compressiveStress, hInviscid t x]

theorem compressiveStress_diagonal_of_isInviscid
    (flow : CauchyFlow 3) (pressure : ScalarField 3)
    (hInviscid : CauchyFlow.IsInviscid 3 flow pressure)
    (t : Time) (x : Space 3) (i : Fin 3) :
    compressiveStress flow t x i i = pressure t x := by
  simp [compressiveStress, hInviscid t x]

/-- A constitutive identity at each space-time point; no equilibrium or pressure positivity
is assumed. The result identifies the given inviscid pressure, not a free-energy derivative. -/
theorem pressureFromStress_eq_physlib_pressure
    (flow : CauchyFlow 3) (pressure : ScalarField 3)
    (hInviscid : CauchyFlow.IsInviscid 3 flow pressure)
    (t : Time) (x : Space 3) :
    pressureFromStress (compressiveStress flow t x) = pressure t x := by
  simp [pressureFromStress, compressiveStress_diagonal_of_isInviscid flow pressure hInviscid]

end
end OMAI.PhyslibBridge
