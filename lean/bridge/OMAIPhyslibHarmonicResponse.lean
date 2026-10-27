/- Catalog endpoint for the local static-plus-harmonic Cp response identity. -/
module

public import OMAIPhyslibHarmonicVolume
public import OMAIPhyslibResponseWitness

@[expose] public section

noncomputable section

namespace OMAI.PhyslibBridge.Response

/-- The reviewed OMAI scalar expression, using one primitive-cell molar basis
and consistent SI inputs. This definition alone is not a physical proof. -/
def heatCapacityPIdentity (Cv T Vm alpha K : ℝ) : ℝ :=
  Cv + T * Vm * alpha ^ 2 * K

/-- The independently defined actual molar enthalpy derivative equals the OMAI
expression on the same local stable constant-pressure branch. Static energy and
positive volume-dependent modes belong to the actual canonical model; no
numerical QHA, EOS fit, static-energy or phonon producer is verified. -/
theorem harmonic_static_heatCapacityP_eq_omai (M : HarmonicVolumeModel) (p t : ℝ)
    (B : StableBranchAt M.freeEnergy M.domain p t) :
    M.actualCp p B.volume t =
      heatCapacityPIdentity (M.cv (t, B.volume t)) t (B.volume t)
        (expansion B.volume t) (bulk M.freeEnergy (t, B.volume t)) := by
  have h := M.actualCp_sub_cv p t B
  dsimp only [heatCapacityPIdentity]
  linarith

/-- Local stability gives Cp ≥ Cv for the actual model, not for arbitrary
independently supplied values sharing the catalog quantity names. -/
theorem harmonic_static_heatCapacityP_ge_heatCapacityV
    (M : HarmonicVolumeModel) (p t : ℝ)
    (B : StableBranchAt M.freeEnergy M.domain p t) :
    M.cv (t, B.volume t) ≤ M.actualCp p B.volume t :=
  M.actualCp_ge_cv p t B

end OMAI.PhyslibBridge.Response
