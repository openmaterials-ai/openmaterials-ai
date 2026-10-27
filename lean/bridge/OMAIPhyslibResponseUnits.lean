/- Exact-real cell/molar basis changes for scalar thermodynamic response.
These are normalization helpers, not structure/volume or numerical-adapter proofs. -/
module

public import Mathlib.Analysis.Calculus.ContDiff.Deriv
public import Mathlib.Analysis.Calculus.Deriv.Comp
public import Mathlib.Analysis.Calculus.Deriv.CompMul
public import Mathlib.Analysis.Calculus.Deriv.Mul
public import Mathlib.Tactic

@[expose] public section

namespace OMAI.PhyslibBridge
noncomputable section

/-- Lift a per-cell quantity to a molar quantity while changing the independent
volume coordinate from cell v to molar V=A*v, with a fixed positive scale A. -/
def molarLift (A : ℝ) (f : ℝ → ℝ → ℝ) (t V : ℝ) : ℝ := A * f t (V / A)

theorem molarLift_volume_hasDerivAt {A t v fv : ℝ} {f : ℝ → ℝ → ℝ}
    (hA : 0 < A) (hf : HasDerivAt (f t) fv v) :
    HasDerivAt (molarLift A f t) fv (A * v) := by
  have hcancel : A * v / A = v := by field_simp
  have hf' : HasDerivAt (f t) fv (A * v / A) := by simpa only [hcancel] using hf
  have h := (hf'.comp (A * v) ((hasDerivAt_id (A * v)).div_const A)).const_mul A
  convert h using 1
  · rfl
  · field_simp

/-- The first volume derivative has no residual Avogadro factor. -/
theorem molarLift_volume_deriv {A : ℝ} (hA : 0 < A) (f : ℝ → ℝ → ℝ) (t : ℝ) :
    deriv (molarLift A f t) = fun V => deriv (f t) (V / A) := by
  funext V
  have hfun : molarLift A f t = fun W => A * f t (A⁻¹ * W) := by
    funext W
    simp [molarLift, div_eq_mul_inv, mul_comm]
  rw [hfun, deriv_const_mul_field, deriv_comp_mul_left]
  simp only [smul_eq_mul]
  rw [← mul_assoc, mul_inv_cancel₀ hA.ne', one_mul, mul_comm A⁻¹ V, ← div_eq_mul_inv]

theorem molarLift_volume_second_deriv {A t v : ℝ} {f : ℝ → ℝ → ℝ}
    (hA : 0 < A) (hf : ContDiffAt ℝ 2 (f t) v) :
    deriv (deriv (molarLift A f t)) (A * v) = deriv (deriv (f t)) v / A := by
  have hd : DifferentiableAt ℝ (deriv (f t)) v :=
    (hf.derivWithin (m := 1) (by norm_num)).differentiableAt (by norm_num)
  have hcancel : v = A * v / A := by field_simp
  have h := hd.hasDerivAt.comp_of_eq (A * v)
    ((hasDerivAt_id (A * v)).div_const A) hcancel
  rw [molarLift_volume_deriv hA f t]
  simpa only [Function.comp_def, mul_one_div, id_eq] using h.deriv

/-- Bulk modulus is unchanged by the coherent cell/molar coordinate change. -/
theorem molarLift_volume_bulk {A t v : ℝ} {f : ℝ → ℝ → ℝ}
    (hA : 0 < A) (hf : ContDiffAt ℝ 2 (f t) v) :
    (A * v) * deriv (deriv (molarLift A f t)) (A * v) =
      v * deriv (deriv (f t)) v := by
  rw [molarLift_volume_second_deriv hA hf]
  field_simp

theorem molarCurve_expansion {A t : ℝ} {v : ℝ → ℝ}
    (hA : 0 < A) (hv : 0 < v t) (hd : DifferentiableAt ℝ v t) :
    deriv (fun s => A * v s) t / (A * v t) = deriv v t / v t := by
  rw [(hd.hasDerivAt.const_mul A).deriv]
  field_simp

/-- At fixed volume, temperature derivatives acquire the extensive scale A. -/
theorem molarLift_temperature_hasDerivAt {A t v ft : ℝ} {f : ℝ → ℝ → ℝ}
    (hA : 0 < A) (hf : HasDerivAt (fun s => f s v) ft t) :
    HasDerivAt (fun s => molarLift A f s (A * v)) (A * ft) t := by
  have hcancel : A * v / A = v := by field_simp
  simpa only [molarLift, hcancel] using hf.const_mul A

end
end OMAI.PhyslibBridge
