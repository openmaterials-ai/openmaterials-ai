module

public import OMAIAtomisticDerivatives
public import Mathlib.Analysis.Calculus.DerivativeTest
public import Mathlib.Analysis.Matrix.PosDef
public import Mathlib.Analysis.Matrix.Spectrum

/-!
# Normal modes of a molecule at a minimum of its potential

The catalog's `compute_molecular_frequencies` returns the normal-mode frequencies of a
molecular structure from an opaque Hessian solve, with imaginary modes serialized negative and
their count `n_imaginary` used as the saddle-order diagnostic (zero for a minimum). Here the
modes are read as the eigenvalues of the mass-weighted Hessian
`H_kl = Phi2_kl / sqrt(m_k m_l)` of the potential at the structure: a positive eigenvalue is a
squared angular frequency, a negative one an imaginary mode. Physlib has no molecular model,
so these are local results.

At a local minimum of a potential twice continuously differentiable there, with positive
masses, the mass-weighted Hessian is positive semidefinite, so no eigenvalue is negative and
`n_imaginary = 0`. For a potential invariant under rigid translations, the three mass-weighted
rigid translations are zero modes.
-/

@[expose] public section

noncomputable section

open Finset OMAI.PhyslibBridge.Atomistic Filter
open scoped Topology Matrix

namespace OMAI.PhyslibBridge.MolecularModes

variable {A : Type*} [Fintype A] [DecidableEq A]

/-- The mass-weighted Hessian `H_kl = Phi2_kl / sqrt(m_k m_l)` of the potential at `u`. -/
def massWeightedHessian (V : (A × Fin 3 → ℝ) → ℝ) (u : A × Fin 3 → ℝ) (m : A → ℝ) :
    Matrix (A × Fin 3) (A × Fin 3) ℝ :=
  fun k l => forceConstant2 V u k l / Real.sqrt (m k.1 * m l.1)

/-- The interpreted catalog expression of `compute_molecular_frequencies`: the signed normal-mode
frequencies `sqrt(lambda)` for each eigenvalue `lambda >= 0` of the mass-weighted Hessian and
`-sqrt(-lambda)` for an imaginary mode, in coherent angular units. This definition alone is not a
physical proof. -/
def molecularFrequencies {V : (A × Fin 3 → ℝ) → ℝ} {u : A × Fin 3 → ℝ} {m : A → ℝ}
    (hH : (massWeightedHessian V u m).IsHermitian) (i : A × Fin 3) : ℝ :=
  if 0 ≤ hH.eigenvalues i then Real.sqrt (hH.eigenvalues i) else -Real.sqrt (-hH.eigenvalues i)

/-- The mass-weighted Hessian of a potential twice continuously differentiable at `u` is
symmetric. -/
theorem massWeightedHessian_isHermitian (V : (A × Fin 3 → ℝ) → ℝ) (u : A × Fin 3 → ℝ)
    (m : A → ℝ) (hV : ContDiffAt ℝ 2 V u) : (massWeightedHessian V u m).IsHermitian := by
  ext k l
  simp only [Matrix.conjTranspose_apply, star_trivial, massWeightedHessian, forceConstant2]
  rw [partialAt_symm hV, mul_comm (m l.1)]

private theorem deriv2_nonneg_of_isLocalMin {φ : ℝ → ℝ} (hmin : IsLocalMin φ 0)
    (hc : ContinuousAt φ 0) : 0 ≤ deriv (deriv φ) 0 := by
  by_contra hneg
  have hneg := not_le.mp hneg
  have hmax := isLocalMax_of_deriv_deriv_neg hneg hmin.deriv_eq_zero hc
  have hconst : φ =ᶠ[𝓝 0] fun _ => φ 0 := by
    filter_upwards [hmin, hmax] with y h1 h2 using le_antisymm h2 h1
  have hd : deriv φ =ᶠ[𝓝 0] fun _ => 0 := by
    filter_upwards [hconst.eventuallyEq_nhds] with y hy
    rw [hy.deriv_eq]
    simp
  rw [hd.deriv_eq] at hneg
  simp at hneg

omit [DecidableEq A] in
private theorem line_deriv2 {V : (A × Fin 3 → ℝ) → ℝ} {u : A × Fin 3 → ℝ}
    (hV : ContDiffAt ℝ 2 V u) (y : A × Fin 3 → ℝ) :
    deriv (deriv (fun t : ℝ => V (u + t • y))) 0 = fderiv ℝ (fderiv ℝ V) u y y := by
  have hline : ∀ t : ℝ, HasDerivAt (fun t : ℝ => u + t • y) y t := fun t => by
    simpa using ((hasDerivAt_id t).smul_const y).const_add u
  have hcont : Tendsto (fun t : ℝ => u + t • y) (𝓝 0) (𝓝 u) := by
    have : Continuous (fun t : ℝ => u + t • y) := by fun_prop
    simpa using this.tendsto 0
  have hnear : ∀ᶠ x in 𝓝 u, DifferentiableAt ℝ V x :=
    (hV.eventually (by simp)).mono fun x hx => hx.differentiableAt (by norm_num)
  have heq : deriv (fun t : ℝ => V (u + t • y)) =ᶠ[𝓝 0] fun t => fderiv ℝ V (u + t • y) y := by
    filter_upwards [hcont.eventually hnear] with t ht
    exact ((ht.hasFDerivAt).comp_hasDerivAt t (hline t)).deriv
  rw [heq.deriv_eq]
  have hd2 : DifferentiableAt ℝ (fderiv ℝ V) u :=
    (hV.fderiv_right (m := 1) (by norm_num)).differentiableAt (by norm_num)
  have hd2' : HasFDerivAt (fderiv ℝ V) (fderiv ℝ (fderiv ℝ V) u) (u + (0 : ℝ) • y) := by
    simpa using hd2.hasFDerivAt
  have h1 := hd2'.comp_hasDerivAt (0 : ℝ) (hline 0)
  have h2 : HasDerivAt (fun t : ℝ => fderiv ℝ V (u + t • y)) (fderiv ℝ (fderiv ℝ V) u y) 0 := h1
  exact (h2.clm_apply (hasDerivAt_const 0 y)).deriv.trans (by simp)

private theorem hessian_quadratic (V : (A × Fin 3 → ℝ) → ℝ) (u : A × Fin 3 → ℝ)
    (hV : ContDiffAt ℝ 2 V u) (y : A × Fin 3 → ℝ) :
    ∑ k, ∑ l, y k * forceConstant2 V u k l * y l = fderiv ℝ (fderiv ℝ V) u y y := by
  have hd2 : DifferentiableAt ℝ (fderiv ℝ V) u :=
    (hV.fderiv_right (m := 1) (by norm_num)).differentiableAt (by norm_num)
  have hphi : ∀ k l, forceConstant2 V u k l =
      fderiv ℝ (fderiv ℝ V) u (Pi.single l 1) (Pi.single k 1) := fun k l =>
    partialAt_partialAt hd2 k l
  set L := fderiv ℝ (fderiv ℝ V) u
  rw [clm_apply_eq_sum (L y) y]
  have hcol : ∀ k, (L y) (Pi.single k 1) = ∑ l, y l * L (Pi.single l 1) (Pi.single k 1) := by
    intro k
    have := clm_apply_eq_sum ((ContinuousLinearMap.apply ℝ ℝ (Pi.single k 1 : A × Fin 3 → ℝ)).comp L) y
    simpa using this
  simp only [hcol, Finset.mul_sum]
  refine Finset.sum_congr rfl fun k _ => Finset.sum_congr rfl fun l _ => ?_
  rw [hphi]
  ring

/-- At a local minimum of a potential twice continuously differentiable there, with positive
masses, the mass-weighted Hessian is positive semidefinite. -/
theorem massWeightedHessian_posSemidef (V : (A × Fin 3 → ℝ) → ℝ) (u : A × Fin 3 → ℝ)
    (m : A → ℝ) (hm : ∀ i, 0 < m i) (hV : ContDiffAt ℝ 2 V u) (hmin : IsLocalMin V u) :
    (massWeightedHessian V u m).PosSemidef := by
  refine Matrix.posSemidef_iff_dotProduct_mulVec.mpr ⟨massWeightedHessian_isHermitian V u m hV, ?_⟩
  intro x
  set y : A × Fin 3 → ℝ := fun k => x k / Real.sqrt (m k.1)
  have hquad : star x ⬝ᵥ (massWeightedHessian V u m *ᵥ x) =
      ∑ k, ∑ l, y k * forceConstant2 V u k l * y l := by
    simp only [star_trivial, dotProduct, Matrix.mulVec, massWeightedHessian, Finset.mul_sum]
    refine Finset.sum_congr rfl fun k _ => Finset.sum_congr rfl fun l _ => ?_
    rw [Real.sqrt_mul (hm k.1).le]
    have h1 : Real.sqrt (m k.1) ≠ 0 := (Real.sqrt_pos.mpr (hm k.1)).ne'
    have h2 : Real.sqrt (m l.1) ≠ 0 := (Real.sqrt_pos.mpr (hm l.1)).ne'
    simp only [y]
    field_simp
  rw [hquad, hessian_quadratic V u hV y, ← line_deriv2 hV y]
  apply deriv2_nonneg_of_isLocalMin
  · have hcont : Continuous (fun t : ℝ => u + t • y) := by fun_prop
    have hmin' : IsLocalMin V (u + (0 : ℝ) • y) := by simpa using hmin
    exact IsLocalMin.comp_continuous (g := fun t : ℝ => u + t • y) (b := (0 : ℝ)) hmin'
      hcont.continuousAt
  · have hcont : Continuous (fun t : ℝ => u + t • y) := by fun_prop
    have hc' : ContinuousAt V (u + (0 : ℝ) • y) := by simpa using hV.continuousAt
    exact ContinuousAt.comp (g := V) (f := fun t : ℝ => u + t • y) (x := (0 : ℝ)) hc'
      hcont.continuousAt

/-- At a local minimum of a potential twice continuously differentiable there, with positive
masses, every eigenvalue of the mass-weighted Hessian is nonnegative: no catalog frequency is
serialized negative (`n_imaginary = 0`) and each squared frequency is its eigenvalue. -/
theorem molecularFrequencies_of_isLocalMin (V : (A × Fin 3 → ℝ) → ℝ) (u : A × Fin 3 → ℝ)
    (m : A → ℝ) (hm : ∀ i, 0 < m i) (hV : ContDiffAt ℝ 2 V u) (hmin : IsLocalMin V u)
    (i : A × Fin 3) :
    0 ≤ molecularFrequencies (massWeightedHessian_isHermitian V u m hV) i ∧
      molecularFrequencies (massWeightedHessian_isHermitian V u m hV) i ^ 2 =
        (massWeightedHessian_isHermitian V u m hV).eigenvalues i := by
  have h0 := (massWeightedHessian_posSemidef V u m hm hV hmin).eigenvalues_nonneg i
  unfold molecularFrequencies
  simp only [h0, ↓reduceIte]
  exact ⟨Real.sqrt_nonneg _, Real.sq_sqrt h0⟩

/-- For a potential invariant under rigid translations and positive masses, each mass-weighted
rigid translation `sqrt(m_i) e_beta` is a zero mode of the mass-weighted Hessian. -/
theorem massWeightedHessian_translation (V : (A × Fin 3 → ℝ) → ℝ)
    (hV : ∀ x t, V (translate t x) = V x) (u : A × Fin 3 → ℝ) (m : A → ℝ) (hm : ∀ i, 0 < m i)
    (β : Fin 3) :
    massWeightedHessian V u m *ᵥ (fun k => if k.2 = β then Real.sqrt (m k.1) else 0) = 0 := by
  funext k
  simp only [Matrix.mulVec, dotProduct, massWeightedHessian, Pi.zero_apply]
  have hrow : ∀ l : A × Fin 3, forceConstant2 V u k l / Real.sqrt (m k.1 * m l.1) *
      (if l.2 = β then Real.sqrt (m l.1) else 0) =
      (if l.2 = β then forceConstant2 V u k l / Real.sqrt (m k.1) else 0) := by
    intro l
    split_ifs
    · rw [Real.sqrt_mul (hm k.1).le]
      have h1 : Real.sqrt (m k.1) ≠ 0 := (Real.sqrt_pos.mpr (hm k.1)).ne'
      have h2 : Real.sqrt (m l.1) ≠ 0 := (Real.sqrt_pos.mpr (hm l.1)).ne'
      field_simp
    · simp
  simp only [hrow]
  rw [Fintype.sum_prod_type]
  simp only [Finset.sum_ite_eq', Finset.mem_univ, ite_true]
  rw [← Finset.sum_div, forceConstant2_sum_eq_zero V hV u k β, zero_div]

end OMAI.PhyslibBridge.MolecularModes
