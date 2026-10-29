/- Relaxation-time thermal conductivity weighted by the actual Physlib canonical heat capacities
of the harmonic modes: symmetry, positive semidefiniteness and the exact condition for
positive definiteness. The catalog's `F = v/(2 Gamma)` uses the half-width `Gamma = Im Sigma`
(phono3py's gamma), so `1/tau = 2 Gamma`; ShengBTE and kALDo report `1/tau` directly. -/
module

public import OMAIPhyslibHarmonicVolume
public import OMAIPhyslibLatticeDynamics
public import OMAIPhyslibKappaContraction

@[expose] public section

noncomputable section

namespace OMAI.PhyslibBridge.Lattice

open Matrix Constants Temperature QuantumMechanics.OneDimension

/-- The actual Physlib canonical heat capacity of each harmonic mode. -/
def canonicalModeHeatCapacity {ι : Type*} (Q : ι → HarmonicOscillator) (T : Temperature)
    (m : ι) : ℝ :=
  (harmonicEnsemble (Q m)).heatCapacity T

theorem canonicalModeHeatCapacity_pos {ι : Type*} (Q : ι → HarmonicOscillator)
    (T : Temperature) (hT : 0 < T.val) (m : ι) : 0 < canonicalModeHeatCapacity Q T m := by
  have hTr : 0 < (T : ℝ) := by
    change 0 < (T.val : ℝ)
    exact_mod_cast hT
  unfold canonicalModeHeatCapacity
  rw [harmonic_heatCapacity_eq_omai (Q m) T hT]
  exact harmonicHeatCapacity_pos ℏ_pos kB_pos (Q m).hω hTr

/-- The RTA quadratic form: `x·κ·x = ∑_m c_m (v_m·x)^2 / (2 Γ_m N_q V)`. -/
theorem rtaKappa_quadratic {ι : Type*} [Fintype ι] (c : ι → ℝ) (v : ι → Axis → ℝ)
    (Γ : ι → ℝ) (Nq V : ℝ) (x : Axis → ℝ) :
    x ⬝ᵥ (modeContractedKappa c v (fun m => rtaMeanFreeDisplacement (v m) (Γ m)) Nq V).mulVec x =
      (∑ m, c m * (v m ⬝ᵥ x) ^ 2 / (2 * Γ m)) / (Nq * V) := by
  simp only [dotProduct, mulVec, modeContractedKappa, rtaMeanFreeDisplacement, sq,
    Finset.sum_div, Finset.sum_mul, Finset.mul_sum]
  conv_rhs => rw [Finset.sum_comm]
  refine Finset.sum_congr rfl fun α _ => ?_
  rw [Finset.sum_comm]
  refine Finset.sum_congr rfl fun m _ => Finset.sum_congr rfl fun β _ => ?_
  ring

/-- The relaxation-time conductivity built from the actual canonical mode heat capacities at
`T > 0` and positive linewidths is symmetric and positive semidefinite, and it is positive
definite exactly when the group velocities of the modes span space. -/
theorem rtaKappa_canonical {ι : Type*} [Fintype ι] (Q : ι → HarmonicOscillator)
    (T : Temperature) (hT : 0 < T.val) (Γ : ι → ℝ) (hΓ : ∀ m, 0 < Γ m)
    (v : ι → Axis → ℝ) (Nq V : ℝ) (hNq : 0 < Nq) (hV : 0 < V) :
    let κ := modeContractedKappa (canonicalModeHeatCapacity Q T) v
      (fun m => rtaMeanFreeDisplacement (v m) (Γ m)) Nq V
    κ.IsSymm ∧ κ.PosSemidef ∧
      ((∀ x : Axis → ℝ, x ≠ 0 → 0 < x ⬝ᵥ κ.mulVec x) ↔
        ∀ x : Axis → ℝ, x ≠ 0 → ∃ m, v m ⬝ᵥ x ≠ 0) := by
  intro κ
  have hc := canonicalModeHeatCapacity_pos Q T hT
  have hNV : 0 < Nq * V := mul_pos hNq hV
  have hsymm : κ.IsSymm := by
    ext α β
    simp only [κ, transpose_apply, modeContractedKappa, rtaMeanFreeDisplacement]
    congr 1
    refine Finset.sum_congr rfl fun m _ => ?_
    ring
  have hterm : ∀ x m, 0 ≤ canonicalModeHeatCapacity Q T m * (v m ⬝ᵥ x) ^ 2 / (2 * Γ m) :=
    fun x m => div_nonneg (mul_nonneg (hc m).le (sq_nonneg _)) (by linarith [hΓ m])
  have hquad := rtaKappa_quadratic (canonicalModeHeatCapacity Q T) v Γ Nq V
  refine ⟨hsymm, ?_, ?_⟩
  · refine Matrix.posSemidef_iff_dotProduct_mulVec.2 ⟨hsymm, fun x => ?_⟩
    rw [star_trivial, hquad]
    exact div_nonneg (Finset.sum_nonneg fun m _ => hterm x m) hNV.le
  · constructor
    · intro h x hx
      by_contra hall
      simp only [not_exists, not_not] at hall
      have h0 := h x hx
      rw [hquad] at h0
      have : ∑ m, canonicalModeHeatCapacity Q T m * (v m ⬝ᵥ x) ^ 2 / (2 * Γ m) = 0 :=
        Finset.sum_eq_zero fun m _ => by rw [hall m]; ring
      rw [this, zero_div] at h0
      exact lt_irrefl _ h0
    · intro h x hx
      obtain ⟨m, hm⟩ := h x hx
      rw [hquad]
      refine div_pos ?_ hNV
      refine lt_of_lt_of_le ?_ (Finset.single_le_sum (fun m _ => hterm x m) (Finset.mem_univ m))
      exact div_pos (mul_pos (hc m) (lt_of_le_of_ne (sq_nonneg _) (pow_ne_zero 2 hm).symm))
        (by linarith [hΓ m])

end OMAI.PhyslibBridge.Lattice
