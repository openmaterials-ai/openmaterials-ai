/- Real phonon frequencies of a mechanically stable crystal. On a finite Born-von Karman
supercell whose harmonic energy is never negative, a Bloch-wave argument makes the dynamical
matrix positive semidefinite at every character of the translations. Folding the force constants
of an infinite crystal into the supercell, `Phi_BvK(R) = sum_L Phi(R + L)`, reproduces the
catalog's plane-wave dynamical matrix `D(q)` exactly at every wavevector commensurate with the
supercell, so a stable supercell gives `omega^2 >= 0` there. Incommensurate wavevectors, the
usual case of a BTE mesh finer than the force-constant supercell, are not covered. -/
module

public import OMAIPhyslibLatticeDynamics

@[expose] public section

noncomputable section

namespace OMAI.PhyslibBridge.Lattice

open Physlib.CondensedMatter Matrix ComplexConjugate
open scoped ComplexOrder

/-- For a real symmetric kernel `P`, the Hermitian form of a complex vector is the sum of the real
forms of its real and imaginary parts. -/
theorem hermitian_form_of_real_symmetric {ι : Type*} [Fintype ι] (P : ι → ι → ℝ)
    (hP : ∀ a b, P a b = P b a) (u : ι → ℂ) :
    ∑ a, ∑ b, conj (u a) * (P a b : ℂ) * u b =
      ((∑ a, ∑ b, (u a).re * P a b * (u b).re + ∑ a, ∑ b, (u a).im * P a b * (u b).im : ℝ) :
        ℂ) := by
  apply Complex.ext
  · simp only [Complex.re_sum, Complex.mul_re, Complex.conj_re, Complex.conj_im,
      Complex.ofReal_re, Complex.ofReal_im, Complex.mul_im]
    rw [← Finset.sum_add_distrib]
    refine Finset.sum_congr rfl fun a _ => ?_
    rw [← Finset.sum_add_distrib]
    refine Finset.sum_congr rfl fun b _ => ?_
    ring
  · simp only [Complex.im_sum, Complex.mul_im, Complex.mul_re, Complex.conj_re, Complex.conj_im,
      Complex.ofReal_re, Complex.ofReal_im]
    have hswap : ∑ a, ∑ b, (u a).im * P a b * (u b).re = ∑ a, ∑ b, (u a).re * P a b * (u b).im := by
      rw [Finset.sum_comm]
      refine Finset.sum_congr rfl fun a _ => Finset.sum_congr rfl fun b _ => ?_
      rw [hP]
      ring
    have h : ∑ a, ∑ b, ((u a).re * (P a b) * (u b).im - (u a).im * (P a b) * (u b).re) = 0 := by
      simp only [Finset.sum_sub_distrib, hswap, sub_self]
    simp only [mul_zero, sub_zero, zero_add, neg_mul]
    rw [← h]
    refine Finset.sum_congr rfl fun a _ => Finset.sum_congr rfl fun b _ => ?_
    ring

/-- A sum over the sites of a finite crystal is a sum over unit-cell labels and cells. -/
theorem sum_sites {G : Type*} [AddCommGroup G] [AddGroup.FG G] [Fintype G] {C : Crystal G}
    [Fintype C.UnitCell] {M : Type*} [AddCommMonoid M] (f : C.Site → M) :
    ∑ a, f a = ∑ κ, ∑ n, f ⟨n, κ⟩ := by
  rw [← Fintype.sum_prod_type']
  exact Fintype.sum_equiv (Crystal.siteEquiv C) _ _ fun a => rfl

namespace ForceConstants

theorem fc_eq_zero_of_not_mem_shell {G : Type*} [AddCommGroup G]
    [AddGroup.FG G] [DecidableEq G] {C : Crystal G} (Φ : ForceConstants C) {R : G}
    (h : R ∉ Φ.shell) (i j : Mode C) : Φ.fc R i j = 0 :=
  Φ.support _ _ _ _ _ fun hR => h (Finset.mem_union_left _ hR)

/-- The real harmonic energy of a displacement field of a finite crystal. -/
def energy {G : Type*} [AddCommGroup G] [AddGroup.FG G] [Fintype G]
    {C : Crystal G} [Fintype C.UnitCell] (Φ : ForceConstants C) (u : C.Site → Axis → ℝ) : ℝ :=
  ∑ a, ∑ α, ∑ b, ∑ β, u a α * Φ.phi a α b β * u b β

/-- Mechanical stability of the supercell: the harmonic energy is never negative. -/
def Stable {G : Type*} [AddCommGroup G] [AddGroup.FG G] [Fintype G]
    {C : Crystal G} [Fintype C.UnitCell] (Φ : ForceConstants C) : Prop :=
  ∀ u : C.Site → Axis → ℝ, 0 ≤ Φ.energy u

/-- Translating the second site to the cell `n + R` of the first returns the reference-cell
force constant: the phase of a unitary character then leaves only `ψ R`. -/
theorem bloch_cell_sum {G : Type*} [AddCommGroup G] [AddGroup.FG G] [Fintype G]
    {C : Crystal G} (Φ : ForceConstants C) (ψ : AddChar G ℂ) (n : G) (κ : C.UnitCell) (α : Axis) (κ' : C.UnitCell) (β : Axis) :
    ∑ m, conj (ψ n) * (Φ.phi ⟨n, κ⟩ α ⟨m, κ'⟩ β : ℂ) * ψ m =
      ∑ R, ψ R * (Φ.fc R (κ, α) (κ', β) : ℂ) := by
  rw [← Equiv.sum_comp (Equiv.addLeft n)]
  refine Finset.sum_congr rfl fun R _ => ?_
  have ht := Φ.translate n ⟨0, κ⟩ α ⟨R, κ'⟩ β
  simp only [Crystal.Site.vadd_def, add_zero] at ht
  simp only [Equiv.coe_addLeft, ForceConstants.fc, ht, AddChar.map_add_eq_mul,
    ← AddChar.map_neg_eq_conj]
  have h1 : ψ (-n) * ψ n = 1 := by rw [← AddChar.map_add_eq_mul, neg_add_cancel, AddChar.map_zero_eq_one]
  linear_combination (ψ R * (Φ.phi ⟨0, κ⟩ α ⟨R, κ'⟩ β : ℂ)) * h1

end ForceConstants

/-- The Bloch embedding `u(n, κ, α) = ψ(n) y(κ, α)` of a unit-cell displacement. -/
def blochField {G : Type*} [AddCommGroup G] [AddGroup.FG G] {C : Crystal G}
    (ψ : AddChar G ℂ) (y : Mode C → ℂ) : C.Site × Axis → ℂ :=
  fun p => ψ p.1.cell * y (p.1.label, p.2)

namespace ForceConstants

/-- The supercell Hermitian energy of a Bloch field is the number of cells times the Fourier
form `∑_{ij} conj(y_i) y_j ∑_R ψ(R) Φ_{ij}(R)`. -/
theorem bloch_energy {G : Type*} [AddCommGroup G] [AddGroup.FG G] [Fintype G]
    {C : Crystal G} [Fintype C.UnitCell] (Φ : ForceConstants C) (ψ : AddChar G ℂ)
    (y : Mode C → ℂ) :
    ∑ p : C.Site × Axis, ∑ p' : C.Site × Axis,
        conj (blochField ψ y p) * (Φ.phi p.1 p.2 p'.1 p'.2 : ℂ) * blochField ψ y p' =
      (Fintype.card G : ℂ) *
        ∑ i : Mode C, ∑ j : Mode C, conj (y i) * y j * ∑ R, ψ R * (Φ.fc R i j : ℂ) := by
  simp only [Fintype.sum_prod_type, sum_sites, blochField]
  rw [Finset.mul_sum]
  refine Finset.sum_congr rfl fun κ _ => ?_
  have hn : ∀ n : G, (∑ α, ∑ κ', ∑ m, ∑ β,
      conj (ψ n * y (κ, α)) * (Φ.phi ⟨n, κ⟩ α ⟨m, κ'⟩ β : ℂ) * (ψ m * y (κ', β))) =
      ∑ α, ∑ κ', ∑ β, conj (y (κ, α)) * y (κ', β) * ∑ R, ψ R * (Φ.fc R (κ, α) (κ', β) : ℂ) := by
    intro n
    refine Finset.sum_congr rfl fun α _ => Finset.sum_congr rfl fun κ' _ => ?_
    rw [Finset.sum_comm (β := ℂ)]
    refine Finset.sum_congr rfl fun β _ => ?_
    rw [← Φ.bloch_cell_sum ψ n κ α κ' β, Finset.mul_sum]
    refine Finset.sum_congr rfl fun m _ => ?_
    rw [map_mul]
    ring
  rw [Finset.sum_congr rfl fun n _ => hn n, Finset.sum_const, Finset.card_univ, nsmul_eq_mul]

/-- On a finite (Born-von Karman) crystal whose harmonic energy is never negative, the dynamical
matrix built from the supercell's own force constants is positive semidefinite at every
character `ψ` of its translations. -/
theorem dynamicalMatrix_posSemidef_of_stable {G : Type*} [AddCommGroup G]
    [AddGroup.FG G] [Fintype G] [DecidableEq G] {C : Crystal G} [Fintype C.UnitCell]
    (Φ : ForceConstants C) (hstab : Φ.Stable) (ψ : AddChar G ℂ)
    (M : C.UnitCell → ℝ) (hM : ∀ κ, 0 < M κ) :
    (Φ.dynamicalMatrix ψ M).PosSemidef := by
  refine posSemidef_iff_dotProduct_mulVec.2
    ⟨Φ.dynamicalMatrix_isHermitian ψ (fun R => (AddChar.map_neg_eq_conj ψ R).symm) M, fun x => ?_⟩
  let y : Mode C → ℂ := fun i => x i / (Real.sqrt (M i.1) : ℂ)
  have hS : ∀ i j, ∑ R ∈ Φ.shell, ψ R * (Φ.fc R i j : ℂ) = ∑ R, ψ R * (Φ.fc R i j : ℂ) :=
    fun i j => Finset.sum_subset (Finset.subset_univ _) fun R _ hR => by
      rw [Φ.fc_eq_zero_of_not_mem_shell hR, Complex.ofReal_zero, mul_zero]
  have h1 : star x ⬝ᵥ (Φ.dynamicalMatrix ψ M *ᵥ x) =
      ∑ i, ∑ j, conj (y i) * y j * ∑ R, ψ R * (Φ.fc R i j : ℂ) := by
    simp only [dotProduct, mulVec, Pi.star_apply, RCLike.star_def]
    refine Finset.sum_congr rfl fun i _ => ?_
    rw [Finset.mul_sum]
    refine Finset.sum_congr rfl fun j _ => ?_
    have hi : (Real.sqrt (M i.1) : ℂ) ≠ 0 := by exact_mod_cast (Real.sqrt_pos.2 (hM i.1)).ne'
    have hj : (Real.sqrt (M j.1) : ℂ) ≠ 0 := by exact_mod_cast (Real.sqrt_pos.2 (hM j.1)).ne'
    simp only [ForceConstants.dynamicalMatrix, hS, y, map_div₀, Complex.conj_ofReal,
      Real.sqrt_mul (hM i.1).le, Complex.ofReal_mul]
    field_simp
  have h2 := Φ.bloch_energy ψ y
  have h3 := hermitian_form_of_real_symmetric (fun p p' : C.Site × Axis => Φ.phi p.1 p.2 p'.1 p'.2)
    (fun p p' => Φ.symm _ _ _ _) (blochField ψ y)
  have hreal : ∀ f : C.Site × Axis → ℝ,
      0 ≤ ∑ p : C.Site × Axis, ∑ p' : C.Site × Axis, f p * Φ.phi p.1 p.2 p'.1 p'.2 * f p' := by
    intro f
    have := hstab (fun a α => f (a, α))
    unfold ForceConstants.energy at this
    simpa only [Fintype.sum_prod_type] using this
  have hA := hreal fun p => (blochField ψ y p).re
  have hB := hreal fun p => (blochField ψ y p).im
  rw [h2] at h3
  have hcard : (0 : ℝ) < Fintype.card G := by exact_mod_cast Fintype.card_pos
  have hval : star x ⬝ᵥ (Φ.dynamicalMatrix ψ M *ᵥ x) =
      (((∑ p : C.Site × Axis, ∑ p' : C.Site × Axis,
          (blochField ψ y p).re * Φ.phi p.1 p.2 p'.1 p'.2 * (blochField ψ y p').re +
        ∑ p : C.Site × Axis, ∑ p' : C.Site × Axis,
          (blochField ψ y p).im * Φ.phi p.1 p.2 p'.1 p'.2 * (blochField ψ y p').im) /
          Fintype.card G : ℝ) : ℂ) := by
    rw [h1, Complex.ofReal_div, ← h3]
    push_cast
    field_simp
  rw [hval]
  exact Complex.zero_le_real.2 (div_nonneg (add_nonneg hA hB) hcard.le)

end ForceConstants

/-- The Born-von Karman supercell of a crystal: its translations modulo a sublattice `N`, with
the same unit cell. -/
abbrev foldCrystal {G : Type*} [AddCommGroup G] [AddGroup.FG G] (C : Crystal G)
    (N : AddSubgroup G) : Crystal (G ⧸ N) where
  UnitCell := C.UnitCell

/-- A character of the translations that is trivial on `N`, as a character of `G ⧸ N`. -/
def quotientChar {G : Type*} [AddCommGroup G] (ψ : AddChar G ℂ) (N : AddSubgroup G)
    (hN : ∀ L ∈ N, ψ L = 1) : AddChar (G ⧸ N) ℂ where
  toFun x := Quotient.liftOn' x ψ fun a b hab => by
    rw [QuotientAddGroup.leftRel_apply] at hab
    rw [← mul_one (ψ a), ← hN _ hab, ← AddChar.map_add_eq_mul, add_neg_cancel_left]
  map_zero_eq_one' := AddChar.map_zero_eq_one ψ
  map_add_eq_mul' x y := by
    induction x using QuotientAddGroup.induction_on
    induction y using QuotientAddGroup.induction_on
    exact AddChar.map_add_eq_mul ψ _ _

theorem quotientChar_mk {G : Type*} [AddCommGroup G] (ψ : AddChar G ℂ) (N : AddSubgroup G)
    (hN : ∀ L ∈ N, ψ L = 1) (R : G) : quotientChar ψ N hN (R : G ⧸ N) = ψ R :=
  rfl

namespace ForceConstants

/-- The force constants of the supercell: the interaction of two supercell sites is the sum of
the crystal force constants over every cell difference that folds onto their cell difference,
`Phi_BvK(R) = sum_L Phi(R + L)`. -/
def fold {G : Type*} [AddCommGroup G] [AddGroup.FG G] [DecidableEq G] {C : Crystal G}
    (Φ : ForceConstants C) (N : AddSubgroup G) [DecidableEq (G ⧸ N)] :
    ForceConstants (foldCrystal C N) where
  phi a α b β := ∑ R ∈ Φ.shell with QuotientAddGroup.mk (s := N) R = b.cell - a.cell,
    Φ.fc R (a.label, α) (b.label, β)
  symm a α b β := by
    refine Finset.sum_nbij' Neg.neg Neg.neg ?_ ?_ (fun R _ => neg_neg R) (fun R _ => neg_neg R) ?_
    · intro R hR
      simp only [Finset.mem_filter] at hR ⊢
      exact ⟨Φ.neg_mem_shell hR.1, by rw [QuotientAddGroup.mk_neg, hR.2, neg_sub]⟩
    · intro R hR
      simp only [Finset.mem_filter] at hR ⊢
      exact ⟨Φ.neg_mem_shell hR.1, by rw [QuotientAddGroup.mk_neg, hR.2, neg_sub]⟩
    · intro R _
      exact (Φ.fc_neg R _ _).symm
  translate g a α b β := by
    simp only [Crystal.Site.cell_vadd, Crystal.Site.label_vadd, add_sub_add_left_eq_sub]
  range := Φ.shell.image (fun R : G => (R : G ⧸ N))
  support κ α R κ' β hR := by
    refine Finset.sum_eq_zero fun S hS => ?_
    simp only [Finset.mem_filter, sub_zero] at hS
    exact absurd (Finset.mem_image.2 ⟨S, hS.1, hS.2⟩) hR

/-- Folding identity: when the phase on `G ⧸ N` agrees with the phase of every crystal cell, the
supercell dynamical matrix is the crystal's dynamical matrix. -/
theorem fold_dynamicalMatrix {G : Type*} [AddCommGroup G] [AddGroup.FG G] [DecidableEq G]
    {C : Crystal G} (Φ : ForceConstants C) (N : AddSubgroup G) [DecidableEq (G ⧸ N)]
    (ψbar : G ⧸ N → ℂ) (ψ : G → ℂ) (hψ : ∀ R : G, ψbar (QuotientAddGroup.mk R) = ψ R)
    (M : C.UnitCell → ℝ) :
    (Φ.fold N).dynamicalMatrix ψbar M = Φ.dynamicalMatrix ψ M := by
  ext i j
  unfold dynamicalMatrix
  congr 1
  simp only [fc, fold, sub_zero, Complex.ofReal_sum, Finset.mul_sum]
  have hmaps : ∀ R ∈ Φ.shell, (R : G ⧸ N) ∈ (Φ.fold N).shell := fun R hR =>
    Finset.mem_union_left _ (Finset.mem_image.2 ⟨R, hR, rfl⟩)
  rw [← Finset.sum_fiberwise_of_maps_to hmaps]
  refine Finset.sum_congr rfl fun Rb _ => Finset.sum_congr rfl fun R hR => ?_
  rw [(Finset.mem_filter.1 hR).2.symm, hψ]

/-- Real frequencies at commensurate wavevectors. Let `N` be the sublattice of a finite
supercell and `q` a wavevector commensurate with it, `e^{i q.L} = 1` for every `L` in `N`. If the
supercell built by folding the crystal force constants is mechanically stable, the catalog
dynamical matrix `D(q)` of the crystal is positive semidefinite, so `omega^2 >= 0` on every
branch at `q`. -/
theorem planeWave_dynamicalMatrix_posSemidef_of_folded_stable {G : Type*} [AddCommGroup G]
    [AddGroup.FG G] [DecidableEq G] {C : Crystal G} [Fintype C.UnitCell]
    (Φ : ForceConstants C) (N : AddSubgroup G) [Fintype (G ⧸ N)] [DecidableEq (G ⧸ N)]
    (hstab : (Φ.fold N).Stable) (pos : G →+ (Axis → ℝ)) (q : Axis → ℝ)
    (hq : ∀ L ∈ N, planeWave pos q L = 1) (M : C.UnitCell → ℝ) (hM : ∀ κ, 0 < M κ) :
    (Φ.dynamicalMatrix (planeWave pos q) M).PosSemidef := by
  rw [← Φ.fold_dynamicalMatrix N (quotientChar (planeWaveChar pos q) N hq) (planeWave pos q)
    (fun R => rfl) M]
  exact (Φ.fold N).dynamicalMatrix_posSemidef_of_stable hstab _ M hM

end ForceConstants

end OMAI.PhyslibBridge.Lattice
