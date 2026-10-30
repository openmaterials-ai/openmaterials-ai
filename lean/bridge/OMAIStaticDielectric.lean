module

public import Mathlib.Analysis.Matrix.Spectrum
public import Mathlib.Algebra.Order.Star.Real
public import Mathlib.LinearAlgebra.Matrix.PosDef
public import Mathlib.LinearAlgebra.Matrix.SchurComplement
public import Mathlib.Tactic

/-!
# Static dielectric tensor and the Lyddane-Sachs-Teller relation

The catalog's `compute_static_dielectric` adds the ionic (lattice-polarization) response to
the high-frequency electronic tensor `eps_inf`. With `D` the Gamma-point dynamical matrix on
the optical coordinates (positive definite, the acoustic translations projected out), `Z` the
mass-weighted Born-charge matrix on those coordinates and `c = 4 pi e^2 / Omega` (Gaussian;
`e^2 / (epsilon_vac Omega)` in SI, `epsilon_vac` the vacuum permittivity), the static tensor is
`eps_0 = eps_inf + c Z^T D^-1 Z`. In the eigenbasis of `D` this is the mode-oscillator-strength
sum `sum_m Ztilde_m Ztilde_m^T / omega_m^2`.

The ionic term never lowers the response: `eps_0 - eps_inf` is positive semidefinite, and it
vanishes along a direction `u` exactly when no polar mode couples to `u` (`Z u = 0`). Along any
direction `u`, adding the non-analytic correction `c (Z u)(Z u)^T / (u eps_inf u)` of the
long-wavelength limit to `D` multiplies the product of the squared frequencies by
`(u eps_0 u) / (u eps_inf u)`: the generalized Lyddane-Sachs-Teller relation
`prod omega_LO^2 / prod omega_TO^2 = eps_0 / eps_inf`. The correction used here is the
Gonze-Lee form, the `q -> 0` limit of the catalog's `apply_nac_correction` along the direction of `q`.
Physlib has no dielectric model, so these are local results over Mathlib.
-/

@[expose] public section

noncomputable section

open Matrix

namespace OMAI.PhyslibBridge.StaticDielectric

variable {n : Type*} [Fintype n] [DecidableEq n]

/-- The interpreted catalog expression of `compute_static_dielectric`,
`eps_0 = eps_inf + c Z^T D^-1 Z`, with `D` the optical-coordinate Gamma-point dynamical matrix,
`Z` the mass-weighted Born-charge matrix on those coordinates and `c = 4 pi e^2 / Omega`.
This definition alone is not a physical proof. -/
def staticDielectric (epsInf : Matrix (Fin 3) (Fin 3) ℝ) (D : Matrix n n ℝ)
    (Z : Matrix n (Fin 3) ℝ) (c : ℝ) : Matrix (Fin 3) (Fin 3) ℝ :=
  epsInf + c • (Zᵀ * D⁻¹ * Z)

/-- The long-wavelength non-analytic correction along the direction `u`, in the Gonze-Lee form
`c (Z u)(Z u)^T / (u eps_inf u)` on the optical coordinates. -/
def nonAnalytic (epsInf : Matrix (Fin 3) (Fin 3) ℝ) (Z : Matrix n (Fin 3) ℝ) (c : ℝ)
    (u : Fin 3 → ℝ) : Matrix n n ℝ :=
  (c / (u ⬝ᵥ epsInf *ᵥ u)) • vecMulVec (Z *ᵥ u) (Z *ᵥ u)

omit [DecidableEq n] in
private theorem row_mul_col (a b : n → ℝ) (M : Matrix n n ℝ) :
    (replicateRow Unit a * M * replicateCol Unit b) () () = a ⬝ᵥ M *ᵥ b := by
  simp only [mul_apply, replicateRow_apply, replicateCol_apply, dotProduct, mulVec,
    Finset.mul_sum, Finset.sum_mul]
  rw [Finset.sum_comm]
  exact Finset.sum_congr rfl fun i _ => Finset.sum_congr rfl fun j _ => by ring

private theorem quad_ionic (D : Matrix n n ℝ) (Z : Matrix n (Fin 3) ℝ) (u : Fin 3 → ℝ) :
    u ⬝ᵥ (Zᵀ * D⁻¹ * Z) *ᵥ u = (Z *ᵥ u) ⬝ᵥ D⁻¹ *ᵥ (Z *ᵥ u) := by
  rw [← mulVec_mulVec, ← mulVec_mulVec, dotProduct_mulVec, vecMul_transpose]

/-- The ionic contribution never lowers the dielectric response, and it vanishes along a
direction exactly when no polar mode couples to it: with `D` positive definite and `c > 0`,
`eps_0 - eps_inf` is positive semidefinite, and `u (eps_0 - eps_inf) u = 0` if and only if
`Z u = 0`. -/
theorem staticDielectric_sub_posSemidef {epsInf : Matrix (Fin 3) (Fin 3) ℝ} {D : Matrix n n ℝ}
    (hD : D.PosDef) (Z : Matrix n (Fin 3) ℝ) {c : ℝ} (hc : 0 < c) :
    (staticDielectric epsInf D Z c - epsInf).PosSemidef ∧
      ∀ u : Fin 3 → ℝ, u ⬝ᵥ (staticDielectric epsInf D Z c - epsInf) *ᵥ u = 0 ↔ Z *ᵥ u = 0 := by
  have hInv : D⁻¹.PosDef := hD.inv
  have hsub : staticDielectric epsInf D Z c - epsInf = c • (Zᵀ * D⁻¹ * Z) := by
    simp [staticDielectric]
  rw [hsub]
  have hpsd : (Zᵀ * D⁻¹ * Z).PosSemidef := by
    simpa [conjTranspose_eq_transpose_of_trivial] using hInv.posSemidef.conjTranspose_mul_mul_same Z
  refine ⟨hpsd.smul hc.le, fun u => ?_⟩
  rw [smul_mulVec, dotProduct_smul, smul_eq_mul, mul_eq_zero, quad_ionic]
  constructor
  · rintro (h | h)
    · exact absurd h hc.ne'
    · by_contra hne
      have := hInv.dotProduct_mulVec_pos hne
      simp only [star_trivial] at this
      linarith
  · intro h
    right
    rw [h, mulVec_zero, dotProduct_zero]

/-- The generalized Lyddane-Sachs-Teller relation. Along any direction `u` with
`u eps_inf u > 0`, the long-wavelength non-analytic correction turns the transverse squared
frequencies (the eigenvalues of `D`) into the longitudinal ones (the eigenvalues of
`D + nonAnalytic`), and the ratio of their products is the ratio of the static to the
high-frequency dielectric response along `u`:
`prod omega_LO^2 / prod omega_TO^2 = (u eps_0 u) / (u eps_inf u)`. -/
theorem lyddaneSachsTeller {epsInf : Matrix (Fin 3) (Fin 3) ℝ} {D : Matrix n n ℝ}
    (hD : D.PosDef) (Z : Matrix n (Fin 3) ℝ) (c : ℝ) {u : Fin 3 → ℝ}
    (hu : 0 < u ⬝ᵥ epsInf *ᵥ u) :
    ∃ hLO : (D + nonAnalytic epsInf Z c u).IsHermitian,
      (∏ i, hLO.eigenvalues i) / (∏ i, hD.isHermitian.eigenvalues i) =
        (u ⬝ᵥ staticDielectric epsInf D Z c *ᵥ u) / (u ⬝ᵥ epsInf *ᵥ u) := by
  have hN : (nonAnalytic epsInf Z c u).IsHermitian := by
    ext i j
    simp [nonAnalytic, conjTranspose_apply, vecMulVec_apply, mul_comm]
  refine ⟨hD.isHermitian.add hN, ?_⟩
  have hdetD : D.det ≠ 0 := hD.det_pos.ne'
  have hTO : (∏ i, hD.isHermitian.eigenvalues i) = D.det := by
    simpa using (hD.isHermitian.det_eq_prod_eigenvalues).symm
  have hLOdet : (∏ i, (hD.isHermitian.add hN).eigenvalues i) =
      (D + nonAnalytic epsInf Z c u).det := by
    simpa using ((hD.isHermitian.add hN).det_eq_prod_eigenvalues).symm
  rw [hLOdet, hTO]
  have hlemma := det_add_replicateCol_mul_replicateRow (ι := Unit) (isUnit_iff_ne_zero.mpr hdetD)
    ((c / (u ⬝ᵥ epsInf *ᵥ u)) • (Z *ᵥ u)) (Z *ᵥ u)
  have hvec : nonAnalytic epsInf Z c u =
      replicateCol Unit ((c / (u ⬝ᵥ epsInf *ᵥ u)) • (Z *ᵥ u)) * replicateRow Unit (Z *ᵥ u) := by
    rw [← vecMulVec_eq, nonAnalytic]
    ext i j
    simp [vecMulVec_apply, mul_assoc]
  rw [hvec, hlemma]
  have hone : (1 + replicateRow Unit (Z *ᵥ u) * D⁻¹ *
      replicateCol Unit ((c / (u ⬝ᵥ epsInf *ᵥ u)) • (Z *ᵥ u))).det =
      1 + (c / (u ⬝ᵥ epsInf *ᵥ u)) * ((Z *ᵥ u) ⬝ᵥ D⁻¹ *ᵥ (Z *ᵥ u)) := by
    rw [det_unique, Matrix.add_apply, one_apply_eq, row_mul_col, mulVec_smul, dotProduct_smul, smul_eq_mul]
  rw [hone, mul_div_cancel_left₀ _ hdetD]
  have hq : u ⬝ᵥ staticDielectric epsInf D Z c *ᵥ u =
      u ⬝ᵥ epsInf *ᵥ u + c * ((Z *ᵥ u) ⬝ᵥ D⁻¹ *ᵥ (Z *ᵥ u)) := by
    rw [staticDielectric, add_mulVec, dotProduct_add, smul_mulVec, dotProduct_smul, smul_eq_mul,
      quad_ionic]
  rw [hq]
  field_simp

end OMAI.PhyslibBridge.StaticDielectric
