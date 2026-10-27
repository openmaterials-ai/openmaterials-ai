/- Volumetric normalization of the actual heterogeneous joint ensemble. -/
module

public import OMAIPhyslibHarmonicProduct
public import OMAIPhyslibHarmonicDensity

@[expose] public section
namespace OMAI.PhyslibBridge
noncomputable section

/-- The joint ensemble capacity divided by N_q times the positive primitive-cell
volume equals the existing OMAI volumetric endpoint. The spectrum and grid remain
fixed. This strengthens the same endpoint; it adds no independent producer. -/
theorem harmonic_joint_volumetric_heatCapacity_eq_omai (grid : HarmonicModeGrid)
    (volume : PrimitiveCellVolume) (T : Temperature) (hT : 0 < T.val) :
    (harmonicGridEnsemble grid).heatCapacity T / ((grid.qCount : ℝ) * volume.siValue) =
      harmonicVolumetricHeatCapacity grid volume T := by
  rw [harmonicGridEnsemble_heatCapacity grid T hT]
  exact harmonic_volumetric_heatCapacity_eq_omai grid volume T hT

end
end OMAI.PhyslibBridge
