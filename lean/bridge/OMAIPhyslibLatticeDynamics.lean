/- Harmonic lattice dynamics on a Physlib crystal. Physlib's `Crystal` supplies the sites and
the translation action; the lattice-dynamics content (force constants, the Fourier-transformed
dynamical matrix, the index-permutation symmetry, Hermiticity and the acoustic zero modes at
Gamma) is OMAI-local. The phase is the catalog's cell-vector convention `e^{+i q.R}`; phonopy and
phono3py use atom positions, which multiplies D by `diag(e^{i q.tau})` on both sides. -/
module

public import Physlib.CondensedMatter.Crystal.Basic
public import Mathlib.Analysis.Matrix.Spectrum
public import Mathlib.Analysis.Matrix.PosDef
public import Mathlib.Analysis.SpecialFunctions.Pow.Real

@[expose] public section

noncomputable section

namespace OMAI.PhyslibBridge.Lattice

open Physlib.CondensedMatter Matrix ComplexConjugate
open scoped ComplexOrder

/-- Cartesian component of a displacement. -/
abbrev Axis := Fin 3

/-- The plane-wave phase `e^{i q·R}` for a lattice embedding `pos` of the translations. -/
def planeWave {G : Type*} [AddCommGroup G] (pos : G →+ (Axis → ℝ)) (q : Axis → ℝ)
    (R : G) : ℂ :=
  Complex.exp (((∑ α, q α * pos R α : ℝ) : ℂ) * Complex.I)

theorem planeWave_conj {G : Type*} [AddCommGroup G] (pos : G →+ (Axis → ℝ))
    (q : Axis → ℝ) (R : G) : conj (planeWave pos q R) = planeWave pos q (-R) := by
  unfold planeWave
  rw [← Complex.exp_conj]
  congr 1
  simp only [map_mul, Complex.conj_ofReal, Complex.conj_I, map_neg, Pi.neg_apply, mul_neg,
    Finset.sum_neg_distrib, Complex.ofReal_neg, neg_mul]

theorem planeWave_zero {G : Type*} [AddCommGroup G] (pos : G →+ (Axis → ℝ)) (R : G) :
    planeWave pos 0 R = 1 := by
  simp [planeWave]

theorem planeWave_add {G : Type*} [AddCommGroup G] (pos : G →+ (Axis → ℝ)) (q : Axis → ℝ)
    (R S : G) : planeWave pos q (R + S) = planeWave pos q R * planeWave pos q S := by
  unfold planeWave
  rw [← Complex.exp_add]
  congr 1
  simp only [map_add, Pi.add_apply, mul_add, Finset.sum_add_distrib, Complex.ofReal_add, add_mul]

/-- The plane wave as an additive character of the translations. -/
def planeWaveChar {G : Type*} [AddCommGroup G] (pos : G →+ (Axis → ℝ)) (q : Axis → ℝ) :
    AddChar G ℂ where
  toFun := planeWave pos q
  map_zero_eq_one' := by simp [planeWave]
  map_add_eq_mul' := planeWave_add pos q

/-- The catalog dispersion relation `∑_j D_ij e_j = ω^2 e_i` for one mode. This definition alone
is not a physical proof. -/
def DispersionRelation {n : Type*} [Fintype n] (D : Matrix n n ℂ) (omega2 : ℂ) (e : n → ℂ) :
    Prop :=
  ∀ i, ∑ j, D i j * e j = omega2 * e i

/-- A positive semidefinite dynamical matrix has real, nonnegative `ω²`. Every solution of the
catalog dispersion relation with a nonzero eigenvector has `Re ω² ≥ 0` and `Im ω² = 0`, since
`e^† D e = ω² e^† e` with `e^† D e ≥ 0` and `e^† e > 0`. -/
theorem dispersion_omega2_nonneg {n : Type*} [Fintype n] {D : Matrix n n ℂ} {omega2 : ℂ}
    {e : n → ℂ} (hD : D.PosSemidef) (h : DispersionRelation D omega2 e) (he : e ≠ 0) :
    0 ≤ omega2.re ∧ omega2.im = 0 := by
  have hmul : D.mulVec e = omega2 • e := funext fun i => h i
  have hq : star e ⬝ᵥ D.mulVec e = omega2 * (star e ⬝ᵥ e) := by
    rw [hmul, dotProduct_smul, smul_eq_mul]
  have hpos : 0 < star e ⬝ᵥ e := dotProduct_star_self_pos_iff.2 he
  have hnn := hD.dotProduct_mulVec_nonneg e
  rw [hq, Complex.nonneg_iff] at hnn
  rw [Complex.pos_iff] at hpos
  simp only [Complex.mul_re, Complex.mul_im, ← hpos.2, mul_zero, sub_zero, zero_add] at hnn
  exact ⟨by nlinarith [hnn.1, hpos.1], (mul_eq_zero.1 hnn.2.symm).resolve_right hpos.1.ne'⟩

/-- Second-order force constants of a crystal: the real second derivatives of the lattice
potential with respect to the displacement of site `a` along `α` and of site `b` along `β`.
`symm` is the equality of mixed partial derivatives, `translate` the invariance of the
potential under a lattice translation, and `range` a finite set of cells outside which the
reference-cell interactions vanish. -/
structure ForceConstants {G : Type*} [AddCommGroup G] [AddGroup.FG G] (C : Crystal G) where
  phi : C.Site → Axis → C.Site → Axis → ℝ
  symm : ∀ a α b β, phi a α b β = phi b β a α
  translate : ∀ (g : G) a α b β, phi (g +ᵥ a) α (g +ᵥ b) β = phi a α b β
  range : Finset G
  support : ∀ κ α R κ' β, R ∉ range → phi ⟨0, κ⟩ α ⟨R, κ'⟩ β = 0

/-- A displacement component: a unit-cell label with a Cartesian axis. -/
abbrev Mode {G : Type*} [AddCommGroup G] [AddGroup.FG G] (C : Crystal G) :=
  C.UnitCell × Axis

namespace ForceConstants

/-- The catalog's `Φ^{(2)}_{i,j,R}`: component `i` of the reference cell against component
`j` of cell `R`. -/
def fc {G : Type*} [AddCommGroup G] [AddGroup.FG G] {C : Crystal G} (Φ : ForceConstants C)
    (R : G) (i j : Mode C) : ℝ :=
  Φ.phi ⟨0, i.1⟩ i.2 ⟨R, j.1⟩ j.2

/-- The index-permutation symmetry `Φ_ij(-R) = Φ_ji(R)` of the cell-resolved force constants,
derived from the symmetry of second derivatives and the translation invariance of the crystal
potential. (In lattice dynamics "Newton's third law" usually names the acoustic sum rule.) -/
theorem fc_neg {G : Type*} [AddCommGroup G] [AddGroup.FG G] {C : Crystal G}
    (Φ : ForceConstants C) (R : G) (i j : Mode C) : Φ.fc (-R) j i = Φ.fc R i j := by
  unfold fc
  have h := Φ.translate R ⟨0, j.1⟩ j.2 ⟨-R, i.1⟩ i.2
  simp only [Crystal.Site.vadd_def, add_zero, add_neg_cancel] at h
  rw [← h]
  exact Φ.symm _ _ _ _

/-- The interaction cells closed under inversion. -/
def shell {G : Type*} [AddCommGroup G] [AddGroup.FG G] [DecidableEq G] {C : Crystal G}
    (Φ : ForceConstants C) : Finset G :=
  Φ.range ∪ Φ.range.image Neg.neg

theorem neg_mem_shell {G : Type*} [AddCommGroup G] [AddGroup.FG G] [DecidableEq G]
    {C : Crystal G} (Φ : ForceConstants C) {R : G} (h : R ∈ Φ.shell) : -R ∈ Φ.shell := by
  unfold shell at *
  rcases Finset.mem_union.1 h with h | h
  · exact Finset.mem_union_right _ (Finset.mem_image.2 ⟨R, h, rfl⟩)
  · obtain ⟨S, hS, rfl⟩ := Finset.mem_image.1 h
    rw [neg_neg]
    exact Finset.mem_union_left _ hS

/-- The catalog's dynamical matrix
`D_{i,j}(q) = (∑_R e^{i q·R} Φ^{(2)}_{i,j,R}) / sqrt(M_i M_j)`, with the plane-wave phase
supplied as a function `ψ` on lattice translations and masses `M` per unit-cell label. The
sum runs over the interaction cells; the reference-cell force constants vanish elsewhere. -/
def dynamicalMatrix {G : Type*} [AddCommGroup G] [AddGroup.FG G] [DecidableEq G]
    {C : Crystal G} (Φ : ForceConstants C) (ψ : G → ℂ) (M : C.UnitCell → ℝ) :
    Matrix (Mode C) (Mode C) ℂ :=
  fun i j => (∑ R ∈ Φ.shell, ψ R * (Φ.fc R i j : ℂ)) / (Real.sqrt (M i.1 * M j.1) : ℂ)

/-- With a unitary phase, `conj (ψ R) = ψ (-R)`, the dynamical matrix of any crystal force
constants is Hermitian. The proof uses the index-permutation symmetry derived above, so it rests
on the translation invariance of the crystal, not on an assumed symmetry of `Φ_{ij}(R)`. -/
theorem dynamicalMatrix_isHermitian {G : Type*} [AddCommGroup G] [AddGroup.FG G]
    [DecidableEq G] {C : Crystal G} (Φ : ForceConstants C) (ψ : G → ℂ)
    (hψ : ∀ R, conj (ψ R) = ψ (-R)) (M : C.UnitCell → ℝ) :
    (Φ.dynamicalMatrix ψ M).IsHermitian := by
  ext i j
  simp only [conjTranspose_apply, dynamicalMatrix, star_div₀, star_sum, star_mul',
    RCLike.star_def, Complex.conj_ofReal, hψ]
  rw [mul_comm (M j.1) (M i.1)]
  congr 1
  refine Finset.sum_nbij' Neg.neg Neg.neg (fun R hR => Φ.neg_mem_shell hR)
    (fun R hR => Φ.neg_mem_shell hR) (fun R _ => neg_neg R) (fun R _ => neg_neg R) ?_
  intro R _
  rw [← Φ.fc_neg (-R) i j, neg_neg]

/-- The dynamical matrix at every wavevector is Hermitian. -/
theorem planeWave_dynamicalMatrix_isHermitian {G : Type*} [AddCommGroup G] [AddGroup.FG G]
    [DecidableEq G] {C : Crystal G} (Φ : ForceConstants C) (pos : G →+ (Axis → ℝ))
    (q : Axis → ℝ) (M : C.UnitCell → ℝ) :
    (Φ.dynamicalMatrix (planeWave pos q) M).IsHermitian :=
  Φ.dynamicalMatrix_isHermitian _ (planeWave_conj pos q) M

/-- The acoustic sum rule: a rigid translation of the whole crystal exerts no force. -/
def AcousticSumRule {G : Type*} [AddCommGroup G] [AddGroup.FG G] [DecidableEq G]
    {C : Crystal G} [Fintype C.UnitCell] (Φ : ForceConstants C) : Prop :=
  ∀ (κ : C.UnitCell) (α β : Axis), ∑ R ∈ Φ.shell, ∑ κ', Φ.fc R (κ, α) (κ', β) = 0

/-- The mass-weighted rigid translation along `β`. -/
def translationMode {G : Type*} [AddCommGroup G] [AddGroup.FG G] {C : Crystal G}
    (M : C.UnitCell → ℝ) (β : Axis) : Mode C → ℂ :=
  fun j => if j.2 = β then (Real.sqrt (M j.1) : ℂ) else 0

/-- At `q = 0` the acoustic sum rule makes every mass-weighted rigid translation an exact
zero-frequency mode of the dynamical matrix. -/
theorem gamma_translationMode {G : Type*} [AddCommGroup G] [AddGroup.FG G] [DecidableEq G]
    {C : Crystal G} [Fintype C.UnitCell] (Φ : ForceConstants C) (pos : G →+ (Axis → ℝ))
    (hASR : Φ.AcousticSumRule) (M : C.UnitCell → ℝ) (hM : ∀ κ, 0 < M κ) (β : Axis) :
    (Φ.dynamicalMatrix (planeWave pos 0) M).mulVec (translationMode M β) = 0 := by
  funext i
  simp only [mulVec, dotProduct, dynamicalMatrix, planeWave_zero, one_mul, translationMode,
    Pi.zero_apply]
  have hsplit : ∀ j : Mode C,
      (∑ R ∈ Φ.shell, (Φ.fc R i j : ℂ)) / (Real.sqrt (M i.1 * M j.1) : ℂ) *
        (if j.2 = β then (Real.sqrt (M j.1) : ℂ) else 0) =
      (Real.sqrt (M i.1) : ℂ)⁻¹ *
        (if j.2 = β then ∑ R ∈ Φ.shell, (Φ.fc R i j : ℂ) else 0) := by
    intro j
    split_ifs
    · have hi : (Real.sqrt (M i.1) : ℂ) ≠ 0 := by
        exact_mod_cast (Real.sqrt_pos.2 (hM i.1)).ne'
      have hj : (Real.sqrt (M j.1) : ℂ) ≠ 0 := by
        exact_mod_cast (Real.sqrt_pos.2 (hM j.1)).ne'
      rw [Real.sqrt_mul (hM i.1).le, Complex.ofReal_mul]
      field_simp
    · simp
  rw [Finset.sum_congr rfl fun j _ => hsplit j, ← Finset.mul_sum]
  have hzero : ∑ j : Mode C, (if j.2 = β then ∑ R ∈ Φ.shell, (Φ.fc R i j : ℂ) else 0) = 0 := by
    rw [Fintype.sum_prod_type]
    simp only [Finset.sum_ite_eq', Finset.mem_univ, ite_true]
    rw [Finset.sum_comm]
    exact_mod_cast hASR i.1 i.2 β
  rw [hzero, mul_zero]

/-- The three rigid translations are linearly independent, so the zero eigenvalue at Gamma
has multiplicity at least three: the three acoustic branches. -/
theorem translationMode_linearIndependent {G : Type*} [AddCommGroup G] [AddGroup.FG G]
    {C : Crystal G} [Fintype C.UnitCell] (M : C.UnitCell → ℝ) (hM : ∀ κ, 0 < M κ) :
    LinearIndependent ℂ (translationMode (C := C) M) := by
  rw [Fintype.linearIndependent_iff]
  intro c hc β
  obtain ⟨κ⟩ := C.nonemptyUnitCell
  have h := congrFun hc (κ, β)
  simp only [Finset.sum_apply, Pi.smul_apply, translationMode, smul_eq_mul, mul_ite,
    mul_zero, Pi.zero_apply] at h
  rw [Finset.sum_ite_eq] at h
  simp only [Finset.mem_univ, ite_true] at h
  have hs : (Real.sqrt (M κ) : ℂ) ≠ 0 := by
    exact_mod_cast (Real.sqrt_pos.2 (hM κ)).ne'
  exact (mul_eq_zero.1 h).resolve_right hs

theorem three_le_finrank_ker_gamma {G : Type*} [AddCommGroup G] [AddGroup.FG G]
    [DecidableEq G] {C : Crystal G} [Fintype C.UnitCell] [DecidableEq C.UnitCell]
    (Φ : ForceConstants C) (pos : G →+ (Axis → ℝ)) (hASR : Φ.AcousticSumRule)
    (M : C.UnitCell → ℝ) (hM : ∀ κ, 0 < M κ) :
    3 ≤ Module.finrank ℂ
      (LinearMap.ker (Φ.dynamicalMatrix (planeWave pos 0) M).mulVecLin) := by
  let v : Axis → LinearMap.ker (Φ.dynamicalMatrix (planeWave pos 0) M).mulVecLin :=
    fun β => ⟨translationMode M β, by
      simpa [LinearMap.mem_ker] using Φ.gamma_translationMode pos hASR M hM β⟩
  have hv : LinearIndependent ℂ v :=
    LinearIndependent.of_comp (LinearMap.ker _).subtype
      (translationMode_linearIndependent M hM)
  simpa using hv.fintype_card_le_finrank

end ForceConstants

end OMAI.PhyslibBridge.Lattice
