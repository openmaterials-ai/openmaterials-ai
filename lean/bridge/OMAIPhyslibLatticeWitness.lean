/- Exact models for the lattice-dynamics bridge. The monatomic chain with nearest-neighbour
springs on the Physlib crystal `ofUnitCell ℤ Unit` has the textbook catalog dynamical matrix,
longitudinal dispersion and group velocity, so the hypotheses of the Hellmann-Feynman
group-velocity theorem are satisfiable. Einstein springs on the three-cell ring
`ofUnitCell (ZMod 3) Unit` are mechanically stable, so the stability hypothesis of the
dispersion theorem is satisfiable. The chain springs folded onto a finite ring of cells
`ℤ ⧸ N`, in particular the three-cell ring `ℤ ⧸ 3ℤ`, are mechanically stable, so the
folded-stability hypothesis of the commensurate-wavevector theorem is satisfiable. -/
module

public import OMAIPhyslibGroupVelocity
public import OMAIPhyslibPhononDispersion
public import Mathlib.Analysis.SpecialFunctions.Trigonometric.Deriv

@[expose] public section

noncomputable section

namespace OMAI.PhyslibBridge.LatticeWitness

open Physlib.CondensedMatter Matrix ComplexConjugate OMAI.PhyslibBridge.Lattice

/-- The monatomic chain: one atom per cell, cells labelled by `ℤ`. -/
abbrev chain : Crystal ℤ := Crystal.ofUnitCell ℤ Unit

/-- Nearest-neighbour coupling pattern `2, -1, -1` of a longitudinal spring chain. -/
def coupling (d : ℤ) : ℝ := if d = 0 then 2 else if d = 1 ∨ d = -1 then -1 else 0

theorem coupling_neg (d : ℤ) : coupling (-d) = coupling d := by
  unfold coupling
  split_ifs <;> first | rfl | (exfalso; omega)

/-- Longitudinal springs of stiffness `K` between nearest neighbours. -/
def springs (K : ℝ) : ForceConstants chain where
  phi a α b β := if α = 0 ∧ β = 0 then K * coupling (b.cell - a.cell) else 0
  symm a α b β := by
    by_cases h : α = 0 ∧ β = 0
    · have h' : β = 0 ∧ α = 0 := ⟨h.2, h.1⟩
      rw [ite_eq_left_of_eq_true _ _ (eq_true h), ite_eq_left_of_eq_true _ _ (eq_true h'), ← coupling_neg, neg_sub]
    · have h' : ¬(β = 0 ∧ α = 0) := fun h' => h ⟨h'.2, h'.1⟩
      rw [ite_eq_right_of_eq_false _ _ (eq_false h), ite_eq_right_of_eq_false _ _ (eq_false h')]
  translate g a α b β := by
    simp only [Crystal.Site.cell_vadd, add_sub_add_left_eq_sub]
  range := {-1, 0, 1}
  support κ α R κ' β hR := by
    simp only [Finset.mem_insert, Finset.mem_singleton, not_or] at hR
    have hc : coupling (R - 0) = 0 := by
      unfold coupling
      split_ifs <;> first | rfl | (exfalso; omega)
    simp only [hc, mul_zero, ite_self]

/-- Cells sit at `R a` along the x axis. -/
def chainPos (a : ℝ) : ℤ →+ (Axis → ℝ) := zmultiplesHom _ (Pi.single 0 a)

theorem chainPos_apply (a : ℝ) (R : ℤ) (γ : Axis) :
    chainPos a R γ = if γ = 0 then (R : ℝ) * a else 0 := by
  simp [chainPos, Pi.single_apply, zsmul_eq_mul]

theorem springs_shell (K : ℝ) : (springs K).shell = {-1, 0, 1} := by
  show ({-1, 0, 1} : Finset ℤ) ∪ Finset.image Neg.neg {-1, 0, 1} = {-1, 0, 1}
  decide

/-- The longitudinal displacement of the single atom. -/
def longitudinal : Mode chain → ℂ := Pi.single ((), 0) 1

/-- The textbook longitudinal branch `ω^2 = (2K/M)(1 - cos(q_x a))`. -/
def longitudinalOmega2 (K Mass a qx : ℝ) : ℝ := 2 * K / Mass * (1 - Real.cos (qx * a))

theorem planeWave_chain (a : ℝ) (q : Axis → ℝ) (R : ℤ) :
    planeWave (chainPos a) q R = Complex.exp (((q 0 * ((R : ℝ) * a) : ℝ) : ℂ) * Complex.I) := by
  unfold planeWave
  congr 3
  simp [chainPos_apply]

theorem exp_add_exp_neg (x : ℝ) :
    Complex.exp (((x : ℝ) : ℂ) * Complex.I) + Complex.exp (((-x : ℝ) : ℂ) * Complex.I) =
      2 * (Real.cos x : ℂ) := by
  rw [Complex.ofReal_cos, Complex.cos, Complex.ofReal_neg, neg_mul]
  ring

theorem chain_entry_longitudinal (K Mass a : ℝ) (hMass : 0 < Mass) (q : Axis → ℝ) :
    (springs K).dynamicalMatrix (planeWave (chainPos a) q) (fun _ => Mass) ((), 0) ((), 0) =
      (longitudinalOmega2 K Mass a (q 0) : ℂ) := by
  unfold ForceConstants.dynamicalMatrix ForceConstants.fc
  rw [springs_shell, Finset.sum_insert (by decide), Finset.sum_insert (by decide),
    Finset.sum_singleton]
  have hsq : Real.sqrt (Mass * Mass) = Mass := Real.sqrt_mul_self hMass.le
  have c1 : coupling (-1 - 0) = -1 := by norm_num [coupling]
  have c0 : coupling (0 - 0) = 2 := by norm_num [coupling]
  have c2 : coupling (1 - 0) = -1 := by norm_num [coupling]
  simp only [hsq, springs, and_self, ite_true, planeWave_chain, c1, c0, c2]
  have e1 : Complex.exp (((q 0 * (((-1 : ℤ) : ℝ) * a) : ℝ) : ℂ) * Complex.I) =
      Complex.exp (((-(q 0 * a) : ℝ) : ℂ) * Complex.I) := by
    congr 3; push_cast; ring
  have e0 : Complex.exp (((q 0 * (((0 : ℤ) : ℝ) * a) : ℝ) : ℂ) * Complex.I) = 1 := by simp
  have e2 : Complex.exp (((q 0 * (((1 : ℤ) : ℝ) * a) : ℝ) : ℂ) * Complex.I) =
      Complex.exp (((q 0 * a : ℝ) : ℂ) * Complex.I) := by
    congr 3; push_cast; ring
  rw [e1, e0, e2]
  have hcos := exp_add_exp_neg (q 0 * a)
  have hm : (Mass : ℂ) ≠ 0 := by exact_mod_cast hMass.ne'
  unfold longitudinalOmega2
  rw [div_eq_iff hm]
  push_cast at hcos ⊢
  rw [neg_mul] at hcos
  field_simp
  linear_combination (-(K : ℂ)) * hcos

theorem chain_entry_transverse (K Mass a : ℝ) (q : Axis → ℝ) (β : Axis) (hβ : β ≠ 0) :
    (springs K).dynamicalMatrix (planeWave (chainPos a) q) (fun _ => Mass) ((), β) ((), 0) = 0 := by
  unfold ForceConstants.dynamicalMatrix ForceConstants.fc
  have h : ∀ R : ℤ, (springs K).phi ⟨0, ()⟩ β ⟨R, ()⟩ 0 = 0 := fun R => by
    simp [springs, hβ]
  simp [h]

/-- The longitudinal displacement solves the catalog eigen-equation of the chain at every
wavevector, with the textbook eigenvalue `(2K/M)(1 - cos(q_x a))`. -/
theorem chain_longitudinal_eigen (K Mass a : ℝ) (hMass : 0 < Mass) (q : Axis → ℝ) :
    ((springs K).dynamicalMatrix (planeWave (chainPos a) q) (fun _ => Mass)).mulVec
        longitudinal =
      (longitudinalOmega2 K Mass a (q 0) : ℂ) • longitudinal := by
  funext i
  obtain ⟨u, β⟩ := i
  rw [longitudinal, Matrix.mulVec_single]
  simp only [Pi.smul_apply, MulOpposite.smul_eq_mul_unop, MulOpposite.unop_op, Matrix.col_apply,
    mul_one, smul_eq_mul]
  by_cases hβ : β = 0
  · subst hβ
    rw [chain_entry_longitudinal K Mass a hMass q, Pi.single_eq_same, mul_one]
  · rw [chain_entry_transverse K Mass a q β hβ, Pi.single_eq_of_ne (by simp [hβ]), mul_zero]

theorem longitudinal_normalized : star longitudinal ⬝ᵥ longitudinal = 1 := by
  simp [longitudinal, dotProduct, Pi.single_apply]

/-- The chain's catalog group velocity along x is the textbook `a sqrt(K/M) cos(q_x a / 2)`
on `0 < q_x a < π`, obtained from the Hellmann-Feynman theorem with the actual derivative of
the catalog dynamical matrix. -/
theorem chain_groupVelocity (K Mass a : ℝ) (hK : 0 < K) (hMass : 0 < Mass) (q : Axis → ℝ)
    (hq : 0 < q 0 * a) (hq' : q 0 * a < Real.pi) :
    catalogGroupVelocity longitudinal
        ((springs K).dynamicalMatrixDeriv (chainPos a) q (fun _ => Mass) 0)
        (Real.sqrt (longitudinalOmega2 K Mass a (q 0))) =
      ((a * Real.sqrt (K / Mass) * Real.cos (q 0 * a / 2) : ℝ) : ℂ) := by
  set x := q 0 * a with hx
  have hline : ∀ s : ℝ, (q + s • Pi.single (0 : Axis) (1 : ℝ) : Axis → ℝ) 0 = q 0 + s :=
    fun s => by simp
  let lam : ℝ → ℝ := fun s => longitudinalOmega2 K Mass a (q 0 + s)
  have hlam : HasDerivAt lam (2 * K / Mass * (a * Real.sin x)) 0 := by
    have h0 : HasDerivAt (fun s : ℝ => q 0 + s) 1 0 := (hasDerivAt_id (0 : ℝ)).const_add (q 0)
    have h1 : HasDerivAt (fun s : ℝ => (q 0 + s) * a) (1 * a) 0 := h0.mul_const a
    have h2 := (h1.cos.const_sub 1).const_mul (2 * K / Mass)
    convert h2 using 1
    · rfl
    · rw [add_zero, one_mul, hx]
      ring
  have heig : ∀ s : ℝ, ((springs K).dynamicalMatrix
      (planeWave (chainPos a) (q + s • Pi.single (0 : Axis) (1 : ℝ))) (fun _ => Mass)).mulVec
      longitudinal = (lam s : ℂ) • longitudinal := fun s => by
    have := chain_longitudinal_eigen K Mass a hMass (q + s • Pi.single (0 : Axis) (1 : ℝ))
    rw [hline] at this
    exact this
  have hs2 : 0 < Real.sin (x / 2) :=
    Real.sin_pos_of_pos_of_lt_pi (by linarith) (by linarith [Real.pi_pos])
  have hcosx : Real.cos x = 1 - 2 * Real.sin (x / 2) ^ 2 := by
    have h := Real.cos_two_mul (x / 2)
    rw [show 2 * (x / 2) = x by ring] at h
    nlinarith [Real.cos_sq_add_sin_sq (x / 2)]
  have hsinx : Real.sin x = 2 * Real.sin (x / 2) * Real.cos (x / 2) := by
    rw [← Real.sin_two_mul]; congr 1; ring
  have hKM : 0 < K / Mass := div_pos hK hMass
  have hr : Real.sqrt (K / Mass) ^ 2 = K / Mass := Real.sq_sqrt hKM.le
  have hrpos : 0 < Real.sqrt (K / Mass) := Real.sqrt_pos.2 hKM
  have hlam0 : lam 0 = (2 * Real.sqrt (K / Mass) * Real.sin (x / 2)) ^ 2 := by
    simp only [lam, add_zero, longitudinalOmega2, ← hx, hcosx]
    rw [mul_pow, mul_pow, hr]
    field_simp
    ring
  have hpos : 0 < lam 0 := by
    rw [hlam0]; positivity
  have hsqrt : Real.sqrt (lam 0) = 2 * Real.sqrt (K / Mass) * Real.sin (x / 2) := by
    rw [hlam0, Real.sqrt_sq (by positivity)]
  obtain ⟨v, hv, hd⟩ := (springs K).catalogGroupVelocity_eq_deriv (chainPos a) q (fun _ => Mass) 0
    (fun _ => longitudinal) 0 lam (fun _ => hasDerivAt_const _ _) (Filter.Eventually.of_forall heig)
    (Filter.Eventually.of_forall fun _ => longitudinal_normalized) hpos
  have hvl : v = 2 * K / Mass * (a * Real.sin x) / (2 * Real.sqrt (lam 0)) :=
    hd.unique (hlam.sqrt hpos.ne')
  have hlam0' : lam 0 = longitudinalOmega2 K Mass a (q 0) := by simp [lam]
  rw [← hlam0', hv, hvl, hsqrt, hsinx]
  congr 1
  have hsne : Real.sin (x / 2) ≠ 0 := hs2.ne'
  have hrne : Real.sqrt (K / Mass) ≠ 0 := hrpos.ne'
  rw [show 2 * K / Mass = 2 * Real.sqrt (K / Mass) ^ 2 by rw [hr]; ring]
  field_simp

/-- The three-cell periodic ring, a Born-von Karman supercell of the chain. -/
abbrev ring3 : Crystal (ZMod 3) := Crystal.ofUnitCell (ZMod 3) Unit

/-- On-site Einstein springs of stiffness `K` on the ring. -/
def einstein (K : ℝ) : ForceConstants ring3 where
  phi a α b β := if a = b ∧ α = β then K else 0
  symm a α b β := by
    have : (a = b ∧ α = β) ↔ (b = a ∧ β = α) :=
      ⟨fun h => ⟨h.1.symm, h.2.symm⟩, fun h => ⟨h.1.symm, h.2.symm⟩⟩
    simp only [this]
  translate g a α b β := by
    have : (g +ᵥ a = g +ᵥ b) ↔ a = b := ⟨fun h => vadd_left_cancel g h, fun h => h ▸ rfl⟩
    simp only [this]
  range := {0}
  support κ α R κ' β hR := by
    have : (⟨0, κ⟩ : ring3.Site) ≠ ⟨R, κ'⟩ := fun h => hR (by
      rw [Finset.mem_singleton]; exact (congrArg Crystal.Site.cell h).symm)
    simp [this]

/-- Einstein springs with `K ≥ 0` are mechanically stable: the harmonic energy is
`K ∑ u^2 ≥ 0`. -/
theorem einstein_stable (K : ℝ) (hK : 0 ≤ K) : (einstein K).Stable := by
  intro u
  unfold ForceConstants.energy einstein
  simp only
  refine Finset.sum_nonneg fun a _ => Finset.sum_nonneg fun α _ => ?_
  have : ∀ b β, u a α * (if a = b ∧ α = β then K else 0) * u b β =
      if b = a ∧ β = α then K * u a α ^ 2 else 0 := by
    intro b β
    by_cases h : a = b ∧ α = β
    · obtain ⟨rfl, rfl⟩ := h; simp; ring
    · have h' : ¬(b = a ∧ β = α) := fun h' => h ⟨h'.1.symm, h'.2.symm⟩
      simp only [h, h', ↓reduceIte]; ring
  simp only [this]
  exact Finset.sum_nonneg fun b _ => Finset.sum_nonneg fun β _ => by
    split_ifs
    · positivity
    · exact le_refl _

/-- The chain springs folded onto a finite ring of cells `ℤ ⧸ N`. The harmonic energy of the
folded supercell is `K ∑_n (u_n - u_{n+1})^2` in the longitudinal displacements `u_n`, so the
folded force constants are mechanically stable for `K ≥ 0`. This is the hypothesis
`(Φ.fold N).Stable` of `planeWave_dynamicalMatrix_posSemidef_of_folded_stable`. -/
theorem springs_fold_stable (K : ℝ) (hK : 0 ≤ K) (N : AddSubgroup ℤ) [Fintype (ℤ ⧸ N)]
    [DecidableEq (ℤ ⧸ N)] : ((springs K).fold N).Stable := by
  intro u
  -- The folded force constants: longitudinal only, summed over the cells that fold together.
  have hphi : ∀ (a b : (foldCrystal chain N).Site) (α β : Axis),
      ((springs K).fold N).phi a α b β =
        if α = 0 ∧ β = 0 then
          ∑ R ∈ ({-1, 0, 1} : Finset ℤ) with QuotientAddGroup.mk (s := N) R = b.cell - a.cell, K * coupling R
        else 0 := by
    intro a b α β
    simp only [ForceConstants.fold, springs_shell]
    by_cases h : α = 0 ∧ β = 0 <;> simp [ForceConstants.fc, springs, h]
  -- Only the longitudinal components enter.
  have hab : ∀ a b : (foldCrystal chain N).Site,
      ∑ α, ∑ β, u a α * ((springs K).fold N).phi a α b β * u b β =
        u a 0 * (∑ R ∈ ({-1, 0, 1} : Finset ℤ) with QuotientAddGroup.mk (s := N) R = b.cell - a.cell,
          K * coupling R) * u b 0 := by
    intro a b
    rw [Finset.sum_eq_single (0 : Axis)]
    · rw [Finset.sum_eq_single (0 : Axis)]
      · simp [hphi]
      · intro β _ hβ
        simp [hphi, hβ]
      · simp
    · intro α _ hα
      simp [hphi, hα]
    · simp
  set v : ℤ ⧸ N → ℝ := fun n => u ⟨n, ()⟩ 0
  -- The energy as a double sum over cells.
  have hE : ((springs K).fold N).energy u =
      ∑ n : ℤ ⧸ N, ∑ m : ℤ ⧸ N,
        v n * (∑ R ∈ ({-1, 0, 1} : Finset ℤ) with QuotientAddGroup.mk (s := N) R = m - n, K * coupling R) * v m := by
    unfold ForceConstants.energy
    rw [sum_sites, Fintype.sum_unique]
    refine Finset.sum_congr rfl fun n _ => ?_
    rw [Finset.sum_comm, sum_sites, Fintype.sum_unique]
    exact Finset.sum_congr rfl fun m _ => hab _ _
  -- Each cell couples to itself and to its two neighbours: the fibre sum collapses.
  have hfib : ∀ n : ℤ ⧸ N,
      ∑ m : ℤ ⧸ N,
          v n * (∑ R ∈ ({-1, 0, 1} : Finset ℤ) with QuotientAddGroup.mk (s := N) R = m - n, K * coupling R) * v m =
        ∑ R ∈ ({-1, 0, 1} : Finset ℤ), v n * (K * coupling R) * v (n + (R : ℤ ⧸ N)) := by
    intro n
    simp only [Finset.mul_sum, Finset.sum_mul]
    have hm : ∀ m : ℤ ⧸ N,
        ∑ R ∈ ({-1, 0, 1} : Finset ℤ) with QuotientAddGroup.mk (s := N) R = m - n, v n * (K * coupling R) * v m =
          ∑ R ∈ ({-1, 0, 1} : Finset ℤ) with n + QuotientAddGroup.mk (s := N) R = m,
            v n * (K * coupling R) * v (n + (R : ℤ ⧸ N)) := by
      intro m
      refine Finset.sum_congr (Finset.filter_congr fun R _ => ?_) fun R hR => ?_
      · rw [eq_sub_iff_add_eq, add_comm]
      · rw [(Finset.mem_filter.1 hR).2]
    rw [Finset.sum_congr rfl fun m _ => hm m]
    exact Finset.sum_fiberwise_of_maps_to (fun R _ => Finset.mem_univ _) _
  -- The nearest-neighbour sum is a sum of squared differences.
  have c1 : coupling (-1) = -1 := by norm_num [coupling]
  have c0 : coupling 0 = 2 := by norm_num [coupling]
  have c2 : coupling 1 = -1 := by norm_num [coupling]
  have hterm : ∀ n : ℤ ⧸ N,
      ∑ R ∈ ({-1, 0, 1} : Finset ℤ), v n * (K * coupling R) * v (n + (R : ℤ ⧸ N)) =
        K * (2 * v n ^ 2 - v n * v (n + -((1 : ℤ) : ℤ ⧸ N)) - v n * v (n + ((1 : ℤ) : ℤ ⧸ N))) := by
    intro n
    rw [Finset.sum_insert (by decide), Finset.sum_insert (by decide), Finset.sum_singleton, c1, c0,
      c2, QuotientAddGroup.mk_neg, QuotientAddGroup.mk_zero, add_zero]
    ring
  have hshift : ∑ n : ℤ ⧸ N, v n * v (n + -((1 : ℤ) : ℤ ⧸ N)) =
      ∑ n : ℤ ⧸ N, v n * v (n + ((1 : ℤ) : ℤ ⧸ N)) := by
    have h := Equiv.sum_comp (Equiv.addRight ((1 : ℤ) : ℤ ⧸ N))
      (fun n => v n * v (n + -((1 : ℤ) : ℤ ⧸ N)))
    simp only [Equiv.coe_addRight, add_neg_cancel_right] at h
    rw [← h]
    exact Finset.sum_congr rfl fun n _ => mul_comm _ _
  have hsq : ∑ n : ℤ ⧸ N, v (n + ((1 : ℤ) : ℤ ⧸ N)) ^ 2 = ∑ n : ℤ ⧸ N, v n ^ 2 := by
    have h := Equiv.sum_comp (Equiv.addRight ((1 : ℤ) : ℤ ⧸ N)) (fun n => v n ^ 2)
    simpa only [Equiv.coe_addRight] using h
  have hsum : ∑ n : ℤ ⧸ N,
      (2 * v n ^ 2 - v n * v (n + -((1 : ℤ) : ℤ ⧸ N)) - v n * v (n + ((1 : ℤ) : ℤ ⧸ N))) =
        ∑ n : ℤ ⧸ N, (v n - v (n + ((1 : ℤ) : ℤ ⧸ N))) ^ 2 := by
    have expand : ∀ n : ℤ ⧸ N, (v n - v (n + ((1 : ℤ) : ℤ ⧸ N))) ^ 2 =
        v n ^ 2 - 2 * (v n * v (n + ((1 : ℤ) : ℤ ⧸ N))) + v (n + ((1 : ℤ) : ℤ ⧸ N)) ^ 2 :=
      fun n => by ring
    simp only [expand, Finset.sum_sub_distrib, Finset.sum_add_distrib, ← Finset.mul_sum, hshift,
      hsq]
    ring
  rw [hE, Finset.sum_congr rfl fun n _ => hfib n, Finset.sum_congr rfl fun n _ => hterm n,
    ← Finset.mul_sum, hsum]
  exact mul_nonneg hK (Finset.sum_nonneg fun n _ => sq_nonneg _)

/-- The translations of the chain modulo three cells, `3ℤ`. -/
abbrev threeCells : AddSubgroup ℤ := AddSubgroup.zmultiples (3 : ℤ)

/-- The three cosets of `3ℤ`, counted through `ZMod 3`. -/
instance threeCells.fintype : Fintype (ℤ ⧸ threeCells) :=
  Fintype.ofEquiv (ZMod 3) (Int.quotientZMultiplesNatEquivZMod 3).symm.toEquiv

/-- The chain springs folded onto the three-cell ring `ℤ ⧸ 3ℤ` are mechanically stable: the
folded-stability hypothesis of the commensurate-wavevector theorem is satisfiable. -/
theorem springs_fold_three_stable (K : ℝ) (hK : 0 ≤ K) :
    ((springs K).fold threeCells).Stable :=
  springs_fold_stable K hK threeCells

end OMAI.PhyslibBridge.LatticeWitness
