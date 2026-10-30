/- Phonon group velocity: the Hellmann-Feynman theorem for the dynamical matrix of a Physlib
crystal. On a differentiable normalized eigenvector path, away from Gamma, the catalog expression
e^dagger (dD/dq) e / (2 omega) is the wavevector derivative of the branch frequency. At
symmetry-enforced degeneracies (transverse pairs along high-symmetry lines) the eigenvector a code
returns need not lie on such a path. The catalog phase is the cell-vector convention; eigenvectors
in the atom-position convention of phonopy differ by `e^{-i q.tau}` and give wrong velocities in
the catalog's dD/dq. -/
module

public import OMAIPhyslibLatticeDynamics
public import Mathlib.Analysis.Calculus.Deriv.Star
public import Mathlib.Analysis.SpecialFunctions.ExpDeriv
public import Mathlib.Analysis.SpecialFunctions.Sqrt

@[expose] public section

noncomputable section

namespace OMAI.PhyslibBridge.Lattice

open Physlib.CondensedMatter Matrix ComplexConjugate Filter Topology

/-- The catalog group velocity `v = ∑_{i,j} conj(e_i) (∂D/∂q)_{ij} e_j / (2 ω)`. -/
def catalogGroupVelocity {n : Type*} [Fintype n] (e : n → ℂ) (dD : Matrix n n ℂ)
    (omega : ℝ) : ℂ :=
  (∑ j, ∑ i, conj (e i) * dD i j * e j) / (2 * (omega : ℂ))

theorem catalogGroupVelocity_eq {n : Type*} [Fintype n] (e : n → ℂ) (dD : Matrix n n ℂ)
    (omega : ℝ) :
    catalogGroupVelocity e dD omega = (star e ⬝ᵥ dD.mulVec e) / (2 * (omega : ℂ)) := by
  unfold catalogGroupVelocity
  congr 1
  rw [Finset.sum_comm]
  simp only [dotProduct, mulVec, Pi.star_apply, RCLike.star_def, Finset.mul_sum, mul_assoc]

/-- Hellmann-Feynman: along a path of matrices differentiable at `t` and Hermitian there, an
eigenvector differentiable at `t` that is normalized with real eigenvalue `λ(s)` for `s` near `t` makes
`λ` differentiable at `t` with `λ'(t) = e(t)^dagger A'(t) e(t)`, and that number is real. The
eigen-equation and the normalization are used on a neighbourhood of `t` only. -/
theorem hellmann_feynman {n : Type*} [Fintype n] (A : ℝ → Matrix n n ℂ) (A' : Matrix n n ℂ)
    (e : ℝ → n → ℂ) (e' : n → ℂ) (lam : ℝ → ℝ) (t : ℝ)
    (hA : ∀ i j, HasDerivAt (fun s => A s i j) (A' i j) t)
    (he : ∀ i, HasDerivAt (fun s => e s i) (e' i) t)
    (heig : ∀ᶠ s in 𝓝 t, (A s).mulVec (e s) = (lam s : ℂ) • e s)
    (hnorm : ∀ᶠ s in 𝓝 t, star (e s) ⬝ᵥ e s = 1)
    (hherm : (A t).IsHermitian) :
    HasDerivAt lam (star (e t) ⬝ᵥ A'.mulVec (e t)).re t ∧
      (star (e t) ⬝ᵥ A'.mulVec (e t)).im = 0 := by
  have heig0 := heig.self_of_nhds
  -- The Rayleigh quotient along the path, written entrywise.
  have hf : HasDerivAt (fun s => ∑ i, ∑ j, star (e s i) * A s i j * e s j)
      (∑ i, ∑ j, ((star (e' i) * A t i j + star (e t i) * A' i j) * e t j +
        star (e t i) * A t i j * e' j)) t := by
    refine HasDerivAt.fun_sum fun i _ => HasDerivAt.fun_sum fun j _ => ?_
    exact (((he i).star).mul (hA i j)).mul (he j)
  -- Near `t` the Rayleigh quotient is the eigenvalue.
  have hval : (fun s => ∑ i, ∑ j, star (e s i) * A s i j * e s j) =ᶠ[𝓝 t]
      fun s => (lam s : ℂ) := by
    filter_upwards [heig, hnorm] with s hs hn
    have h1 : star (e s) ⬝ᵥ (A s).mulVec (e s) = (lam s : ℂ) := by
      rw [hs, dotProduct_smul, hn, smul_eq_mul, mul_one]
    rw [← h1]
    simp only [dotProduct, mulVec, Pi.star_apply, Finset.mul_sum, mul_assoc]
  replace hf := hf.congr_of_eventuallyEq hval.symm
  -- Derivative of the normalization.
  have hn : HasDerivAt (fun s => ∑ i, star (e s i) * e s i)
      (∑ i, (star (e' i) * e t i + star (e t i) * e' i)) t :=
    HasDerivAt.fun_sum fun i _ => ((he i).star).mul (he i)
  have hnconst : (fun s => ∑ i, star (e s i) * e s i) =ᶠ[𝓝 t] fun _ => (1 : ℂ) := by
    filter_upwards [hnorm] with s hs
    simpa [dotProduct] using hs
  replace hn := hn.congr_of_eventuallyEq hnconst.symm
  have hn0 := (hasDerivAt_const t (1 : ℂ)).unique hn
  -- The two eigenvector-derivative terms combine into lam * (d/dt of the norm) = 0.
  have hleft : ∑ i, ∑ j, star (e' i) * A t i j * e t j = (lam t : ℂ) * ∑ i, star (e' i) * e t i := by
    have := congrArg (fun w => star e' ⬝ᵥ w) heig0
    simp only [dotProduct, mulVec, Pi.smul_apply, smul_eq_mul, Pi.star_apply] at this
    rw [Finset.mul_sum]
    simp only [Finset.mul_sum, mul_assoc] at this ⊢
    rw [this]
    refine Finset.sum_congr rfl fun i _ => ?_
    ring
  have hrow : star (e t) ᵥ* A t = (lam t : ℂ) • star (e t) := by
    have := star_mulVec (A t) (e t)
    rw [hherm.eq, heig0, star_smul] at this
    simpa using this.symm
  have hright : ∑ i, ∑ j, star (e t i) * A t i j * e' j =
      (lam t : ℂ) * ∑ i, star (e t i) * e' i := by
    have := congrArg (fun w => w ⬝ᵥ e') hrow
    simp only [dotProduct, vecMul, Pi.smul_apply, smul_eq_mul, Pi.star_apply] at this
    rw [Finset.sum_comm]
    simp only [← Finset.sum_mul] at this ⊢
    rw [this, Finset.mul_sum]
    refine Finset.sum_congr rfl fun i _ => ?_
    ring
  have hsplit : ∑ i, ∑ j, ((star (e' i) * A t i j + star (e t i) * A' i j) * e t j +
        star (e t i) * A t i j * e' j) =
      (∑ i, ∑ j, star (e' i) * A t i j * e t j) +
        (∑ i, ∑ j, star (e t i) * A' i j * e t j) +
        (∑ i, ∑ j, star (e t i) * A t i j * e' j) := by
    simp only [← Finset.sum_add_distrib]
    refine Finset.sum_congr rfl fun i _ => Finset.sum_congr rfl fun j _ => ?_
    ring
  have hmid : ∑ i, ∑ j, star (e t i) * A' i j * e t j = star (e t) ⬝ᵥ A'.mulVec (e t) := by
    simp only [dotProduct, mulVec, Pi.star_apply, Finset.mul_sum, mul_assoc]
  have hsum : (lam t : ℂ) * ∑ i, star (e' i) * e t i + (lam t : ℂ) * ∑ i, star (e t i) * e' i =
      (lam t : ℂ) * ∑ i, (star (e' i) * e t i + star (e t i) * e' i) := by
    rw [← mul_add, ← Finset.sum_add_distrib]
  have hX : ∑ i, ∑ j, ((star (e' i) * A t i j + star (e t i) * A' i j) * e t j +
        star (e t i) * A t i j * e' j) = star (e t) ⬝ᵥ A'.mulVec (e t) := by
    rw [hsplit, hleft, hright, hmid]
    linear_combination hsum - (lam t : ℂ) * hn0
  rw [hX] at hf
  have hre := (Complex.reCLM.hasFDerivAt (x := (lam t : ℂ))).comp_hasDerivAt t hf
  have him := (Complex.imCLM.hasFDerivAt (x := (lam t : ℂ))).comp_hasDerivAt t hf
  have hcre : (⇑Complex.reCLM ∘ fun s => ((lam s : ℝ) : ℂ)) = lam := by
    funext s; simp
  have hcim : (⇑Complex.imCLM ∘ fun s => ((lam s : ℝ) : ℂ)) = fun _ => (0 : ℝ) := by
    funext s; simp
  rw [hcre] at hre
  rw [hcim] at him
  exact ⟨by simpa using hre, by simpa using ((hasDerivAt_const t (0 : ℝ)).unique him).symm⟩

namespace ForceConstants

/-- The q-derivative of the catalog dynamical matrix along axis `α`:
`(∂D/∂q_α)_{ij} = (∑_R i R_α e^{i q·R} Φ_{ij}(R)) / sqrt(M_i M_j)`. -/
def dynamicalMatrixDeriv {G : Type*} [AddCommGroup G] [AddGroup.FG G]
    [DecidableEq G] {C : Crystal G} (Φ : ForceConstants C) (pos : G →+ (Axis → ℝ))
    (q : Axis → ℝ) (M : C.UnitCell → ℝ) (α : Axis) : Matrix (Mode C) (Mode C) ℂ :=
  fun i j => (∑ R ∈ Φ.shell, ((pos R α : ℂ) * Complex.I) * planeWave pos q R * (Φ.fc R i j : ℂ)) /
    (Real.sqrt (M i.1 * M j.1) : ℂ)

end ForceConstants

theorem planeWave_line {G : Type*} [AddCommGroup G] (pos : G →+ (Axis → ℝ)) (q : Axis → ℝ)
    (α : Axis) (s : ℝ) (R : G) :
    planeWave pos (q + s • Pi.single α 1) R =
      Complex.exp ((((∑ γ, q γ * pos R γ) + s * pos R α : ℝ) : ℂ) * Complex.I) := by
  unfold planeWave
  congr 3
  simp only [Pi.add_apply, Pi.smul_apply, Pi.single_apply, smul_eq_mul, mul_ite, mul_one,
    mul_zero, add_mul, Finset.sum_add_distrib, ite_mul, zero_mul, Finset.sum_ite_eq',
    Finset.mem_univ, ite_true]

theorem hasDerivAt_planeWave_line {G : Type*} [AddCommGroup G] (pos : G →+ (Axis → ℝ))
    (q : Axis → ℝ) (α : Axis) (R : G) :
    HasDerivAt (fun s : ℝ => planeWave pos (q + s • Pi.single α 1) R)
      (((pos R α : ℂ) * Complex.I) * planeWave pos q R) 0 := by
  simp only [planeWave_line]
  have hlin : HasDerivAt (fun s : ℝ => (∑ γ, q γ * pos R γ) + s * pos R α) (pos R α) 0 := by
    simpa using ((hasDerivAt_id (0 : ℝ)).mul_const (pos R α)).const_add (∑ γ, q γ * pos R γ)
  have h := ((hlin.ofReal_comp).mul_const Complex.I).cexp
  have hq : planeWave pos q R =
      Complex.exp ((((∑ γ, q γ * pos R γ) + 0 * pos R α : ℝ) : ℂ) * Complex.I) := by
    rw [zero_mul, add_zero]
    rfl
  rw [hq]
  convert h using 1
  ring

namespace ForceConstants

/-- The catalog dynamical matrix is differentiable along every wavevector axis, with the
derivative `dynamicalMatrixDeriv`. -/
theorem hasDerivAt_dynamicalMatrix {G : Type*} [AddCommGroup G]
    [AddGroup.FG G] [DecidableEq G] {C : Crystal G} (Φ : ForceConstants C)
    (pos : G →+ (Axis → ℝ)) (q : Axis → ℝ) (M : C.UnitCell → ℝ) (α : Axis)
    (i j : Mode C) :
    HasDerivAt (fun s : ℝ => Φ.dynamicalMatrix (planeWave pos (q + s • Pi.single α 1)) M i j)
      (Φ.dynamicalMatrixDeriv pos q M α i j) 0 := by
  unfold ForceConstants.dynamicalMatrix ForceConstants.dynamicalMatrixDeriv
  refine HasDerivAt.div_const (HasDerivAt.fun_sum fun R _ => ?_) _
  exact (hasDerivAt_planeWave_line pos q α R).mul_const _

/-- Group velocity of a crystal branch, on a differentiable eigenvector path away from Gamma.
Along the wavevector line `q + s e_α`, let `e(s)` be a differentiable eigenvector of the catalog
dynamical matrix, normalized and with eigenvalue `ω(s)^2` for `s` near `0`, with `ω(0)^2 > 0`.
Then the catalog expression `e^dagger (∂D/∂q_α) e / (2 ω)`, with the actual derivative of the
catalog matrix, is a real number `v`, and `ω = sqrt(ω^2)` is differentiable along the line with
derivative `v`. A nondegenerate branch away from Gamma admits such a path; that existence is a
hypothesis here. -/
theorem catalogGroupVelocity_eq_deriv {G : Type*} [AddCommGroup G]
    [AddGroup.FG G] [DecidableEq G] {C : Crystal G} [Fintype C.UnitCell]
    (Φ : ForceConstants C) (pos : G →+ (Axis → ℝ)) (q : Axis → ℝ) (M : C.UnitCell → ℝ)
    (α : Axis) (e : ℝ → Mode C → ℂ) (e' : Mode C → ℂ) (lam : ℝ → ℝ)
    (he : ∀ i, HasDerivAt (fun s => e s i) (e' i) 0)
    (heig : ∀ᶠ s in 𝓝 0,
      (Φ.dynamicalMatrix (planeWave pos (q + s • Pi.single α 1)) M).mulVec (e s) =
        (lam s : ℂ) • e s)
    (hnorm : ∀ᶠ s in 𝓝 0, star (e s) ⬝ᵥ e s = 1) (hpos : 0 < lam 0) :
    ∃ v : ℝ, catalogGroupVelocity (e 0) (Φ.dynamicalMatrixDeriv pos q M α) (Real.sqrt (lam 0)) =
        v ∧ HasDerivAt (fun s => Real.sqrt (lam s)) v 0 := by
  have hherm : (Φ.dynamicalMatrix (planeWave pos (q + (0 : ℝ) • Pi.single α 1)) M).IsHermitian :=
    Φ.planeWave_dynamicalMatrix_isHermitian pos _ M
  obtain ⟨hlam, him⟩ := hellmann_feynman
    (fun s => Φ.dynamicalMatrix (planeWave pos (q + s • Pi.single α 1)) M)
    (Φ.dynamicalMatrixDeriv pos q M α) e e' lam 0
    (fun i j => Φ.hasDerivAt_dynamicalMatrix pos q M α i j) he heig hnorm hherm
  set X := star (e 0) ⬝ᵥ (Φ.dynamicalMatrixDeriv pos q M α).mulVec (e 0)
  refine ⟨X.re / (2 * Real.sqrt (lam 0)), ?_, hlam.sqrt hpos.ne'⟩
  rw [catalogGroupVelocity_eq]
  have hXr : X = (X.re : ℂ) := Complex.ext (by simp) (by simp [him])
  change X / (2 * ((Real.sqrt (lam 0) : ℝ) : ℂ)) = ((X.re / (2 * Real.sqrt (lam 0)) : ℝ) : ℂ)
  conv_lhs => rw [hXr]
  push_cast
  ring

end ForceConstants

end OMAI.PhyslibBridge.Lattice
