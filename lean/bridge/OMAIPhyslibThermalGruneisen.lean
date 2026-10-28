/- Catalog endpoint for the local static-plus-harmonic thermal Gruneisen identity. -/
module

public import OMAIPhyslibModeGruneisen

@[expose] public section

noncomputable section

open Constants Temperature

namespace OMAI.PhyslibBridge.Response

/-- The reviewed OMAI catalog expression gamma_th = alpha_V * K / C_V^vol, with inputs
ThermalExpansion, BulkModulus and VolumetricHeatCapacity in that order. This definition
alone is not a physical proof. -/
def thermalGruneisenIdentity (alpha K Cvol : ℝ) : ℝ :=
  alpha * K / Cvol

/-- The heat-capacity-weighted mean of the derivative-defined mode Gruneisen parameters of
the same volume family, weighted by actual Physlib per-mode canonical heat capacities at the
branch cell volume, equals the catalog expression built from the branch's volumetric
expansion, isothermal bulk modulus and volumetric heat capacity at the same temperature.
No FC3, finite-difference, Phonopy or numerical QHA estimator is verified. -/
theorem harmonic_static_thermalGruneisen_eq_omai (M : HarmonicVolumeModel) (p : ℝ)
    (T : Temperature) (B : StableBranchAt M.freeEnergy M.domain p (T : ℝ)) :
    M.weightedGruneisen T (B.volume (T : ℝ) / M.reference.avogadro) B.in_domain.2 =
      thermalGruneisenIdentity (expansion B.volume (T : ℝ))
        (bulk M.freeEnergy ((T : ℝ), B.volume (T : ℝ)))
        (harmonicVolumetricHeatCapacity
          (M.gridAt (B.volume (T : ℝ) / M.reference.avogadro) B.in_domain.2)
          (M.primitiveCellVolumeAt (B.volume (T : ℝ) / M.reference.avogadro) B.in_domain.2) T) := by
  have hT : 0 < T.val := by
    have h : 0 < ((T.val : NNReal) : ℝ) := B.in_domain.1
    exact_mod_cast h
  have hC := M.volumetricCv_pos T _ B.in_domain.2 hT
  unfold thermalGruneisenIdentity
  rw [M.expansion_mul_bulk_eq_weightedGruneisen_mul_volumetricCv p T B, mul_div_assoc,
    div_self hC.ne', mul_one]

end OMAI.PhyslibBridge.Response
