module

public import OMAIAtomisticDerivatives
public import OMAIElasticity

/-!
# Cell stress and elastic constants from one cell energy

The catalog reads the cell stress as `sigma_ab = -(1/V) dE/d eps_ab` (compressive positive) and
the elastic constants as `C_abcd = -d sigma_ab / d eps_cd`, with `eps` the homogeneous strain of
the cell. Here `E` is the energy of the homogeneously deformed cell as a function of its
deformation gradient `F`, and `V` is the reference cell volume. At `F = 1 + eps` with `eps`
infinitesimal the derivatives with respect to `eps` and `F` agree; at a finite deformation
`-(1/V) dE/dF` is the first Piola-Kirchhoff stress, not the Cauchy stress. Physlib has no
elastic-solid model, so these are local results.

Invariance of `E` under rotations of the deformed cell (objectivity), with `E` differentiable
at `F`, balances the stress: `sum_b sigma_ab F_cb` is symmetric in `a` and `c`, so the
catalog stress is symmetric at `F = 1`. The elastic constants `(1/V) d^2E/dF dF` of an energy
twice continuously differentiable at the reference have the major symmetry `C_abcd = C_cdab`.
If the energy is also invariant under rotations in every coordinate plane of the cells near the
reference, and the reference is stress-free, they have both minor symmetries as well, and the
Voigt positivity theorem of `OMAIElasticity` applies to them. Objectivity is needed only near
the reference, not at singular deformation gradients.

The St Venant-Kirchhoff energy `V0 (lam/2 (tr E)^2 + mu tr(E E))` of the Green-Lagrange strain
`E = (F^T F - 1)/2` is a compiled witness. It is invariant under every rotation of the cell, a
polynomial in `F` (compiled as twice continuously differentiable), and stress-free at the
reference, so `elasticConstants_symmetries` applies
to it. Its catalog elastic constants at the reference are the isotropic tensor
`(V0/V) (lam delta_ab delta_cd + mu (delta_ac delta_bd + delta_ad delta_bc))`, positive
definite for `lam >= 0`, `mu > 0` and `V = V0 > 0`, so `voigt_pos_of_stable_reference` applies
to it as well.
-/

@[expose] public section

noncomputable section

open Finset OMAI.PhyslibBridge.Atomistic Filter
open scoped Topology

namespace OMAI.PhyslibBridge.CellElasticity

/-- Coordinates of a homogeneously deformed cell: the deformation gradient `F = 1 + eps`. -/
abbrev Cell := Fin 3 × Fin 3 → ℝ

/-- The undeformed reference cell `F = 1`. -/
def referenceCell : Cell := fun k => if k.1 = k.2 then 1 else 0

/-- The reviewed catalog expression of `compute_stress_cell`,
`sigma_ab = -(1/V) dE/d eps_ab`, compressive positive. This definition alone is not a physical
proof. -/
def cellStress (E : Cell → ℝ) (V : ℝ) (F : Cell) (a b : Fin 3) : ℝ :=
  -(1 / V) * partialAt E (a, b) F

/-- The reviewed catalog expression of `compute_elastic_constants`,
`C_abcd = -d sigma_ab / d eps_cd`. This definition alone is not a physical proof. -/
def elasticConstants (E : Cell → ℝ) (V : ℝ) (F : Cell) (a b c d : Fin 3) : ℝ :=
  -partialAt (fun G => cellStress E V G a b) (c, d) F

/-- A rigid rotation by the angle `s` in the `(α, β)` plane applied to the deformed cell, for
`α ≠ β`: `F -> Q F`. -/
def rotateCell (α β : Fin 3) (s : ℝ) (F : Cell) : Cell := fun k =>
  if k.1 = α then Real.cos s * F (α, k.2) - Real.sin s * F (β, k.2)
  else if k.1 = β then Real.sin s * F (α, k.2) + Real.cos s * F (β, k.2)
  else F k

private theorem rotateCell_zero (α β : Fin 3) (F : Cell) : rotateCell α β 0 F = F := by
  funext ⟨a, b⟩
  by_cases ha : a = α
  · subst ha; simp [rotateCell]
  · by_cases hb : a = β
    · subst hb; simp [rotateCell, ha]
    · simp [rotateCell, ha, hb]

private theorem rotateCell_hasDerivAt (α β : Fin 3) (F : Cell) :
    HasDerivAt (fun s => rotateCell α β s F)
      (fun k => if k.1 = α then -F (β, k.2) else if k.1 = β then F (α, k.2) else 0) 0 := by
  rw [hasDerivAt_pi]
  intro k
  by_cases ha : k.1 = α
  · have e : (fun s => rotateCell α β s F k) =
        fun s => Real.cos s * F (α, k.2) - Real.sin s * F (β, k.2) := by
      funext s; simp [rotateCell, ha]
    rw [e]
    have := ((Real.hasDerivAt_cos 0).mul_const (F (α, k.2))).sub
      ((Real.hasDerivAt_sin 0).mul_const (F (β, k.2)))
    convert this using 1
    simp [ha]
  · by_cases hb : k.1 = β
    · have hβα : β ≠ α := fun h => ha (hb.trans h)
      have e : (fun s => rotateCell α β s F k) =
          fun s => Real.sin s * F (α, k.2) + Real.cos s * F (β, k.2) := by
        funext s; simp [rotateCell, hb, hβα]
      rw [e]
      have := ((Real.hasDerivAt_sin 0).mul_const (F (α, k.2))).add
        ((Real.hasDerivAt_cos 0).mul_const (F (β, k.2)))
      convert this using 1
      simp [hb, hβα]
    · have e : (fun s => rotateCell α β s F k) = fun _ => F k := by
        funext s; simp [rotateCell, ha, hb]
      rw [e]
      simpa [ha, hb] using hasDerivAt_const (0 : ℝ) (F k)

/-- Rotation invariance of a cell energy differentiable at `F`, in the `(α, β)` plane, balances
the catalog stress: `sum_b sigma_{alpha b} F_{beta b} = sum_b sigma_{beta b} F_{alpha b}`. At the
reference cell this is the symmetry of the stress. -/
theorem cellStress_rotation_balance (E : Cell → ℝ) (V : ℝ) (F : Cell) (α β : Fin 3)
    (hd : DifferentiableAt ℝ E F) (hE : ∀ s, E (rotateCell α β s F) = E F) :
    ∑ b, cellStress E V F α b * F (β, b) = ∑ b, cellStress E V F β b * F (α, b) := by
  by_cases hαβ : α = β
  · subst hαβ; rfl
  have h0 := fderiv_apply_eq_zero_of_invariant_curve E (fun s => rotateCell α β s F) F _ hd
    (rotateCell_zero α β F) (rotateCell_hasDerivAt α β F) hE
  rw [clm_apply_eq_sum, Fintype.sum_prod_type] at h0
  simp only [cellStress, partialAt]
  fin_cases α <;> fin_cases β <;> simp_all [Fin.sum_univ_three] <;> linear_combination (1 / V) * h0

/-! ## Elastic constants -/

private theorem partialAt_stress (E : Cell → ℝ) (V : ℝ) (F : Cell) (hE : ContDiffAt ℝ 2 E F)
    (a b c d : Fin 3) :
    elasticConstants E V F a b c d = (1 / V) * partialAt (fun G => partialAt E (a, b) G) (c, d) F := by
  have hd : DifferentiableAt ℝ (fun G => partialAt E (a, b) G) F :=
    (contDiffAt_partialAt (n := 1) (hE.of_le (by norm_num)) (a, b)).differentiableAt (by norm_num)
  unfold elasticConstants cellStress
  simp only [partialAt] at hd ⊢
  rw [fderiv_const_mul hd]
  simp

/-- The catalog's elastic constants of a cell energy twice continuously differentiable at `F`
have the major symmetry `C_abcd = C_cdab`. -/
theorem elasticConstants_major (E : Cell → ℝ) (V : ℝ) (F : Cell) (hE : ContDiffAt ℝ 2 E F)
    (a b c d : Fin 3) : elasticConstants E V F a b c d = elasticConstants E V F c d a b := by
  rw [partialAt_stress E V F hE, partialAt_stress E V F hE, partialAt_symm hE]

private theorem stress_line_hasDerivAt (E : Cell → ℝ) (V : ℝ) (hE : ContDiffAt ℝ 2 E referenceCell)
    (a b c d : Fin 3) :
    HasDerivAt (fun t : ℝ => cellStress E V (referenceCell + t • Pi.single (c, d) 1) a b)
      (-elasticConstants E V referenceCell a b c d) 0 := by
  have hd : DifferentiableAt ℝ (fun G => cellStress E V G a b) referenceCell := by
    have h1 := (contDiffAt_partialAt (n := 1) (hE.of_le (by norm_num)) (a, b)).differentiableAt
      (by norm_num)
    exact h1.const_mul _
  have hline : HasDerivAt (fun t : ℝ => referenceCell + t • (Pi.single (c, d) 1 : Cell))
      (Pi.single (c, d) 1) 0 := by
    simpa using ((hasDerivAt_id (0 : ℝ)).smul_const (Pi.single (c, d) 1 : Cell)).const_add
      referenceCell
  have hd' : HasFDerivAt (fun G => cellStress E V G a b)
      (fderiv ℝ (fun G => cellStress E V G a b) referenceCell)
      (referenceCell + (0 : ℝ) • (Pi.single (c, d) 1 : Cell)) := by simpa using hd.hasFDerivAt
  have h3 := hd'.comp_hasDerivAt (0 : ℝ) hline
  have h2 : HasDerivAt (fun t : ℝ => cellStress E V (referenceCell + t • Pi.single (c, d) 1) a b)
      (fderiv ℝ (fun G => cellStress E V G a b) referenceCell (Pi.single (c, d) 1)) 0 := h3
  convert h2 using 1
  simp [elasticConstants, partialAt]

/-- At a stress-free reference cell, an energy that is invariant under rotations in every
coordinate plane of the cells near the reference and twice continuously differentiable at the
reference gives catalog elastic constants with the major symmetry and both minor symmetries,
`C_abcd = C_cdab = C_bacd = C_abdc`. Objectivity is used only along strain lines through the
reference, so it is asked on a neighbourhood, not at singular deformation gradients. -/
theorem elasticConstants_symmetries (E : Cell → ℝ) (V : ℝ)
    (hrot : ∀ α β, α ≠ β → ∀ᶠ G in 𝓝 referenceCell, ∀ s, E (rotateCell α β s G) = E G)
    (hE : ContDiffAt ℝ 2 E referenceCell)
    (hfree : ∀ a b, cellStress E V referenceCell a b = 0) (a b c d : Fin 3) :
    elasticConstants E V referenceCell a b c d = elasticConstants E V referenceCell c d a b ∧
      elasticConstants E V referenceCell a b c d = elasticConstants E V referenceCell b a c d ∧
      elasticConstants E V referenceCell a b c d = elasticConstants E V referenceCell a b d c := by
  set C := elasticConstants E V referenceCell
  -- the first minor symmetry from differentiating the rotation balance along a strain line
  have minor : ∀ α β γ δ, C α β γ δ = C β α γ δ := by
    intro α β γ δ
    by_cases hαβ : α = β
    · rw [hαβ]
    set line : ℝ → Cell := fun t => referenceCell + t • Pi.single (γ, δ) 1
    -- the energy is differentiable and objective along the strain line near the reference
    have hnear : ∀ᶠ t in 𝓝 (0 : ℝ), DifferentiableAt ℝ E (line t) ∧
        ∀ s, E (rotateCell α β s (line t)) = E (line t) := by
      have hcont : Tendsto line (𝓝 0) (𝓝 referenceCell) := by
        have : Continuous line := by fun_prop
        simpa [line] using this.tendsto 0
      exact hcont.eventually (((hE.eventually (by simp)).mono fun G hG =>
        hG.differentiableAt (by norm_num)).and (hrot α β hαβ))
    have hB : (fun t => (∑ b, cellStress E V (line t) α b * line t (β, b)) -
        (∑ b, cellStress E V (line t) β b * line t (α, b))) =ᶠ[𝓝 0] fun _ => 0 := by
      filter_upwards [hnear] with t ht
      rw [cellStress_rotation_balance E V (line t) α β ht.1 ht.2, sub_self]
    have hlin : ∀ (p q : Fin 3), HasDerivAt (fun t => line t (p, q))
        (if (p, q) = (γ, δ) then 1 else 0) 0 := by
      intro p q
      have := ((hasDerivAt_id (0 : ℝ)).mul_const ((Pi.single (γ, δ) 1 : Cell) (p, q))).const_add
        (referenceCell (p, q))
      convert this using 1
      · funext t; simp [line]
      · simp [Pi.single_apply]
    have hderiv : HasDerivAt (fun t => (∑ b, cellStress E V (line t) α b * line t (β, b)) -
        (∑ b, cellStress E V (line t) β b * line t (α, b)))
        ((∑ b, ((-C α b γ δ) * line 0 (β, b) + cellStress E V (line 0) α b *
            (if (β, b) = (γ, δ) then 1 else 0))) -
          (∑ b, ((-C β b γ δ) * line 0 (α, b) + cellStress E V (line 0) β b *
            (if (α, b) = (γ, δ) then 1 else 0)))) 0 := by
      apply HasDerivAt.sub
      · apply HasDerivAt.fun_sum
        intro b _
        exact (stress_line_hasDerivAt E V hE α b γ δ).mul (hlin β b)
      · apply HasDerivAt.fun_sum
        intro b _
        exact (stress_line_hasDerivAt E V hE β b γ δ).mul (hlin α b)
    have hzero : HasDerivAt (fun t => (∑ b, cellStress E V (line t) α b * line t (β, b)) -
        (∑ b, cellStress E V (line t) β b * line t (α, b))) 0 0 :=
      (hasDerivAt_const (0 : ℝ) (0 : ℝ)).congr_of_eventuallyEq hB
    have heq := hderiv.unique hzero
    have hl0 : line 0 = referenceCell := by simp [line]
    simp only [hl0, hfree, zero_mul, add_zero] at heq
    simp only [referenceCell, mul_ite, mul_one, mul_zero, Finset.sum_ite_eq, Finset.mem_univ,
      ite_true] at heq
    linarith
  have major : ∀ α β γ δ, C α β γ δ = C γ δ α β := elasticConstants_major E V referenceCell hE
  refine ⟨major a b c d, minor a b c d, ?_⟩
  rw [major a b c d, minor c d a b, major d c a b]

/-- For a cell energy invariant under rotations in every coordinate plane of the cells near a
stress-free reference and twice continuously differentiable there, whose catalog elastic
constants store positive energy for every nonzero symmetric strain, the catalog's Voigt bulk
and shear moduli are positive and its Poisson ratio lies strictly between `-1` and `1/2`. -/
theorem voigt_pos_of_stable_reference (E : Cell → ℝ) (V : ℝ)
    (hrot : ∀ α β, α ≠ β → ∀ᶠ G in 𝓝 referenceCell, ∀ s, E (rotateCell α β s G) = E G)
    (hE : ContDiffAt ℝ 2 E referenceCell)
    (hfree : ∀ a b, cellStress E V referenceCell a b = 0)
    (hstable : Elasticity.PosDef (fun a b c d => elasticConstants E V referenceCell a b c d)) :
    0 < Elasticity.voigtBulk (fun a b c d => elasticConstants E V referenceCell a b c d) ∧
      0 < Elasticity.voigtShear (fun a b c d => elasticConstants E V referenceCell a b c d) ∧
      -1 < Elasticity.poissonRatio
          (Elasticity.voigtBulk (fun a b c d => elasticConstants E V referenceCell a b c d))
          (Elasticity.voigtShear (fun a b c d => elasticConstants E V referenceCell a b c d)) ∧
      Elasticity.poissonRatio
          (Elasticity.voigtBulk (fun a b c d => elasticConstants E V referenceCell a b c d))
          (Elasticity.voigtShear (fun a b c d => elasticConstants E V referenceCell a b c d)) < 1 / 2 := by
  have hC : ∀ a b c d, elasticConstants E V referenceCell a b c d =
      elasticConstants E V referenceCell b a c d :=
    fun a b c d => (elasticConstants_symmetries E V hrot hE hfree a b c d).2.1
  obtain ⟨hK, hG⟩ := Elasticity.voigt_pos_of_posDef hC hstable
  obtain ⟨h1, h2⟩ := Elasticity.poissonRatio_bounds_of_posDef hC hstable
  exact ⟨hK, hG, h1, h2⟩

/-! ## A St Venant-Kirchhoff witness -/

/-- The Green-Lagrange strain `E = (F^T F - 1) / 2` of the deformed cell. -/
def greenLagrange (F : Cell) (a b : Fin 3) : ℝ :=
  ((∑ c, F (c, a) * F (c, b)) - Elasticity.kron a b) / 2

/-- The St Venant-Kirchhoff energy of the cell, `V0 (lam/2 (tr E)^2 + mu tr(E E))` with `E` the
Green-Lagrange strain, `lam` and `mu` the Lame parameters and `V0` the reference volume. -/
def svkEnergy (lam mu V0 : ℝ) (F : Cell) : ℝ :=
  V0 * (lam / 2 * (∑ a, greenLagrange F a a) ^ 2 +
    mu * ∑ a, ∑ b, greenLagrange F a b * greenLagrange F b a)

/-- The reference cell is the Kronecker delta. -/
theorem referenceCell_apply (a b : Fin 3) : referenceCell (a, b) = Elasticity.kron a b := rfl

/-- The Green-Lagrange strain vanishes at the reference cell. -/
theorem greenLagrange_referenceCell (a b : Fin 3) : greenLagrange referenceCell a b = 0 := by
  fin_cases a <;> fin_cases b <;> simp [greenLagrange, referenceCell, Elasticity.kron]

private theorem rotateCell_gram (α β : Fin 3) (hαβ : α ≠ β) (s : ℝ) (F : Cell) (a b : Fin 3) :
    ∑ c, rotateCell α β s F (c, a) * rotateCell α β s F (c, b) = ∑ c, F (c, a) * F (c, b) := by
  have hβ : β ∈ univ.erase α := mem_erase.mpr ⟨hαβ.symm, mem_univ β⟩
  have split : ∀ g : Fin 3 → ℝ, ∑ c, g c = g α + g β + ∑ c ∈ (univ.erase α).erase β, g c := by
    intro g
    rw [← Finset.add_sum_erase univ g (mem_univ α), ← Finset.add_sum_erase (univ.erase α) g hβ,
      add_assoc]
  have hrest : ∀ c ∈ (univ.erase α).erase β,
      rotateCell α β s F (c, a) * rotateCell α β s F (c, b) = F (c, a) * F (c, b) := by
    intro c hc
    have hcβ : c ≠ β := (mem_erase.mp hc).1
    have hcα : c ≠ α := (mem_erase.mp (mem_erase.mp hc).2).1
    simp [rotateCell, hcα, hcβ]
  rw [split (fun c => rotateCell α β s F (c, a) * rotateCell α β s F (c, b)),
    split (fun c => F (c, a) * F (c, b)), Finset.sum_congr rfl hrest]
  simp only [rotateCell, hαβ.symm, ite_true, ite_false]
  linear_combination (F (α, a) * F (α, b) + F (β, a) * F (β, b)) * Real.sin_sq_add_cos_sq s

/-- A rigid rotation of the deformed cell leaves the Green-Lagrange strain unchanged. -/
theorem greenLagrange_rotateCell (α β : Fin 3) (hαβ : α ≠ β) (s : ℝ) (F : Cell) :
    greenLagrange (rotateCell α β s F) = greenLagrange F := by
  funext a b
  unfold greenLagrange
  rw [rotateCell_gram α β hαβ s F a b]

/-- The St Venant-Kirchhoff energy is invariant under rotations of the deformed cell in every
coordinate plane. -/
theorem svkEnergy_rotateCell (lam mu V0 : ℝ) (α β : Fin 3) (hαβ : α ≠ β) (s : ℝ) (F : Cell) :
    svkEnergy lam mu V0 (rotateCell α β s F) = svkEnergy lam mu V0 F := by
  unfold svkEnergy
  rw [greenLagrange_rotateCell α β hαβ s F]

/-- The St Venant-Kirchhoff energy is a polynomial in `F`, compiled here as twice continuously
differentiable. -/
theorem svkEnergy_contDiff (lam mu V0 : ℝ) : ContDiff ℝ 2 (svkEnergy lam mu V0) := by
  unfold svkEnergy greenLagrange
  fun_prop

private theorem greenLagrange_differentiable (a b : Fin 3) :
    Differentiable ℝ (fun F : Cell => greenLagrange F a b) := by
  unfold greenLagrange
  fun_prop

private theorem hasFDerivAt_mul_zero {f g : Cell → ℝ} {x : Cell} (hf : DifferentiableAt ℝ f x)
    (hg : DifferentiableAt ℝ g x) (hf0 : f x = 0) (hg0 : g x = 0) :
    HasFDerivAt (fun y => f y * g y) (0 : Cell →L[ℝ] ℝ) x := by
  have h := hf.hasFDerivAt.mul hg.hasFDerivAt
  rw [hf0, hg0, zero_smul, zero_smul, add_zero] at h
  exact h

/-- The derivative of the St Venant-Kirchhoff energy vanishes at the reference cell: the energy
is quadratic in a strain that is zero there. -/
theorem svkEnergy_hasFDerivAt_referenceCell (lam mu V0 : ℝ) :
    HasFDerivAt (svkEnergy lam mu V0) (0 : Cell →L[ℝ] ℝ) referenceCell := by
  have hd : Differentiable ℝ (fun F : Cell => ∑ a, greenLagrange F a a) := by
    unfold greenLagrange
    fun_prop
  have htr : HasFDerivAt (fun F : Cell => (∑ a, greenLagrange F a a) ^ 2) (0 : Cell →L[ℝ] ℝ)
      referenceCell := by
    have h := hasFDerivAt_mul_zero (f := fun F : Cell => ∑ a, greenLagrange F a a)
      (g := fun F : Cell => ∑ a, greenLagrange F a a) (x := referenceCell) hd.differentiableAt
      hd.differentiableAt (by simp [greenLagrange_referenceCell])
      (by simp [greenLagrange_referenceCell])
    simpa [sq] using h
  have hab : ∀ a b : Fin 3, HasFDerivAt (fun F : Cell => greenLagrange F a b * greenLagrange F b a)
      (0 : Cell →L[ℝ] ℝ) referenceCell := fun a b =>
    hasFDerivAt_mul_zero (greenLagrange_differentiable a b).differentiableAt
      (greenLagrange_differentiable b a).differentiableAt (greenLagrange_referenceCell a b)
      (greenLagrange_referenceCell b a)
  have hin : ∀ a : Fin 3,
      HasFDerivAt (fun F : Cell => ∑ b, greenLagrange F a b * greenLagrange F b a)
        (0 : Cell →L[ℝ] ℝ) referenceCell := fun a => by
    simpa using HasFDerivAt.fun_sum (u := univ)
      (A := fun b (F : Cell) => greenLagrange F a b * greenLagrange F b a)
      (A' := fun _ => (0 : Cell →L[ℝ] ℝ)) fun b _ => hab a b
  have hq : HasFDerivAt (fun F : Cell => ∑ a, ∑ b, greenLagrange F a b * greenLagrange F b a)
      (0 : Cell →L[ℝ] ℝ) referenceCell := by
    simpa using HasFDerivAt.fun_sum (u := univ)
      (A := fun a (F : Cell) => ∑ b, greenLagrange F a b * greenLagrange F b a)
      (A' := fun _ => (0 : Cell →L[ℝ] ℝ)) fun a _ => hin a
  have h := ((htr.const_mul (lam / 2)).add (hq.const_mul mu)).const_mul V0
  simp only [Pi.add_apply, smul_zero, add_zero] at h
  unfold svkEnergy
  exact h

/-- The reference cell is stress-free for the St Venant-Kirchhoff energy. -/
theorem svkEnergy_cellStress_referenceCell (lam mu V0 V : ℝ) (a b : Fin 3) :
    cellStress (svkEnergy lam mu V0) V referenceCell a b = 0 := by
  simp [cellStress, partialAt, (svkEnergy_hasFDerivAt_referenceCell lam mu V0).fderiv]

/-- The St Venant-Kirchhoff energy meets the hypotheses of `elasticConstants_symmetries`: its
catalog elastic constants at the reference have the major symmetry and both minor symmetries. -/
theorem svkEnergy_elasticConstants_symmetries (lam mu V0 V : ℝ) (a b c d : Fin 3) :
    elasticConstants (svkEnergy lam mu V0) V referenceCell a b c d =
        elasticConstants (svkEnergy lam mu V0) V referenceCell c d a b ∧
      elasticConstants (svkEnergy lam mu V0) V referenceCell a b c d =
        elasticConstants (svkEnergy lam mu V0) V referenceCell b a c d ∧
      elasticConstants (svkEnergy lam mu V0) V referenceCell a b c d =
        elasticConstants (svkEnergy lam mu V0) V referenceCell a b d c :=
  elasticConstants_symmetries (svkEnergy lam mu V0) V
    (fun α β hαβ => Eventually.of_forall fun G s => svkEnergy_rotateCell lam mu V0 α β hαβ s G)
    (svkEnergy_contDiff lam mu V0).contDiffAt (svkEnergy_cellStress_referenceCell lam mu V0 V)
    a b c d

/-! ### Elastic constants of the witness -/

private theorem kron_comm (a b : Fin 3) : Elasticity.kron a b = Elasticity.kron b a := by
  by_cases h : a = b
  · rw [h]
  · simp [Elasticity.kron, h, Ne.symm h]

private theorem sum_kron_mul (a : Fin 3) (f : Fin 3 → ℝ) :
    ∑ i, Elasticity.kron i a * f i = f a := by
  fin_cases a <;> simp [Elasticity.kron]

private theorem sum_kron_mul' (a : Fin 3) (f : Fin 3 → ℝ) :
    ∑ i, Elasticity.kron a i * f i = f a := by
  fin_cases a <;> simp [Elasticity.kron]

private theorem sum_kron_mul_kron (c d : Fin 3) :
    ∑ e, Elasticity.kron c e * Elasticity.kron e d = Elasticity.kron c d := by
  fin_cases c <;> fin_cases d <;> simp [Elasticity.kron]

private theorem single_apply (a b p q : Fin 3) :
    (Pi.single (a, b) (1 : ℝ) : Cell) (p, q) = Elasticity.kron p a * Elasticity.kron q b := by
  simp only [Pi.single_apply, Prod.mk.injEq, Elasticity.kron]
  split_ifs <;> simp_all

private theorem gram_line (G : Cell) (a b : Fin 3) (s : ℝ) (c d : Fin 3) :
    ∑ i, (G + s • Pi.single (a, b) 1 : Cell) (i, c) * (G + s • Pi.single (a, b) 1 : Cell) (i, d) =
      ∑ i, G (i, c) * G (i, d) +
        s * (G (a, d) * Elasticity.kron c b + G (a, c) * Elasticity.kron d b) +
        s ^ 2 * (Elasticity.kron c b * Elasticity.kron d b) := by
  have expand : ∀ i, (G + s • Pi.single (a, b) 1 : Cell) (i, c) *
      (G + s • Pi.single (a, b) 1 : Cell) (i, d) =
      G (i, c) * G (i, d) +
        s * (Elasticity.kron i a *
          (G (i, d) * Elasticity.kron c b + G (i, c) * Elasticity.kron d b)) +
        s ^ 2 * (Elasticity.kron i a *
          (Elasticity.kron i a * (Elasticity.kron c b * Elasticity.kron d b))) := by
    intro i
    simp only [Pi.add_apply, Pi.smul_apply, smul_eq_mul, single_apply]
    ring
  simp only [expand, Finset.sum_add_distrib, ← Finset.mul_sum, sum_kron_mul]
  have hk : Elasticity.kron a a = 1 := by simp [Elasticity.kron]
  rw [hk, one_mul]

private theorem greenLagrange_line (G : Cell) (a b : Fin 3) (s : ℝ) (c d : Fin 3) :
    greenLagrange (G + s • Pi.single (a, b) 1) c d =
      greenLagrange G c d +
        s * ((G (a, d) * Elasticity.kron c b + G (a, c) * Elasticity.kron d b) / 2) +
        s ^ 2 * (Elasticity.kron c b * Elasticity.kron d b / 2) := by
  unfold greenLagrange
  rw [gram_line]
  ring

private theorem hasDerivAt_quadratic (k0 k1 k2 : ℝ) :
    HasDerivAt (fun t : ℝ => k0 + t * k1 + t ^ 2 * k2) k1 0 := by
  have h := (((hasDerivAt_id' (0 : ℝ)).mul_const k1).const_add k0).add
    ((hasDerivAt_pow 2 (0 : ℝ)).mul_const k2)
  convert h using 1
  simp

private theorem line_hasDerivAt (F : Cell) (k : Fin 3 × Fin 3) (p q : Fin 3) :
    HasDerivAt (fun t : ℝ => (F + t • Pi.single k 1 : Cell) (p, q))
      (if (p, q) = k then 1 else 0) 0 := by
  have h := ((hasDerivAt_id' (0 : ℝ)).mul_const ((Pi.single k 1 : Cell) (p, q))).const_add
    (F (p, q))
  convert h using 1
  simp [Pi.single_apply]

/-- The derivative of the St Venant-Kirchhoff energy with respect to `F_ab` is `V0` times the
first Piola-Kirchhoff stress `F (lam tr(E) 1 + 2 mu E)`:
`dE/dF_ab = V0 (lam tr(E) F_ab + 2 mu sum_c F_ac E_cb)`. -/
theorem svkEnergy_partialAt (lam mu V0 : ℝ) (G : Cell) (a b : Fin 3) :
    partialAt (svkEnergy lam mu V0) (a, b) G =
      V0 * (lam * (∑ c, greenLagrange G c c) * G (a, b) +
        2 * mu * ∑ c, G (a, c) * greenLagrange G c b) := by
  apply partialAt_eq_of_hasDerivAt
    ((svkEnergy_contDiff lam mu V0).differentiable (by norm_num) G)
  have hE : ∀ c d, HasDerivAt (fun t : ℝ => greenLagrange (G + t • Pi.single (a, b) 1) c d)
      ((G (a, d) * Elasticity.kron c b + G (a, c) * Elasticity.kron d b) / 2) 0 := by
    intro c d
    simp only [greenLagrange_line]
    exact hasDerivAt_quadratic _ _ _
  have htr := HasDerivAt.fun_sum (u := univ) fun c _ => hE c c
  have hq := HasDerivAt.fun_sum (u := univ) fun c _ =>
    HasDerivAt.fun_sum (u := univ) fun d _ => (hE c d).mul (hE d c)
  have h := (((htr.mul htr).const_mul (lam / 2)).add (hq.const_mul mu)).const_mul V0
  convert h using 1
  · funext t
    simp only [svkEnergy, sq, Pi.add_apply, Pi.mul_apply]
  · simp only [zero_smul, add_zero]
    congr 1
    fin_cases b <;> simp [Fin.sum_univ_three, Elasticity.kron, greenLagrange] <;> ring

/-- The catalog elastic constants of the St Venant-Kirchhoff energy at the reference cell are
`V0 / V` times the isotropic tensor `lam delta_ab delta_cd + mu (delta_ac delta_bd + delta_ad
delta_bc)`. -/
theorem svkEnergy_elasticConstants (lam mu V0 V : ℝ) (a b c d : Fin 3) :
    elasticConstants (svkEnergy lam mu V0) V referenceCell a b c d =
      V0 / V * Elasticity.isotropic lam mu a b c d := by
  rw [partialAt_stress _ V referenceCell (svkEnergy_contDiff lam mu V0).contDiffAt]
  have hP : (fun G => partialAt (svkEnergy lam mu V0) (a, b) G) = fun G : Cell =>
      V0 * (lam * (∑ e, greenLagrange G e e) * G (a, b) +
        2 * mu * ∑ e, G (a, e) * greenLagrange G e b) :=
    funext fun G => svkEnergy_partialAt lam mu V0 G a b
  rw [hP]
  have hd : DifferentiableAt ℝ (fun G : Cell => V0 * (lam * (∑ e, greenLagrange G e e) * G (a, b) +
      2 * mu * ∑ e, G (a, e) * greenLagrange G e b)) referenceCell := by
    unfold greenLagrange
    fun_prop
  have hE : ∀ e f, HasDerivAt
      (fun t : ℝ => greenLagrange (referenceCell + t • Pi.single (c, d) 1) e f)
      ((Elasticity.kron c f * Elasticity.kron e d + Elasticity.kron c e * Elasticity.kron f d) / 2)
      0 := by
    intro e f
    simp only [greenLagrange_line, referenceCell_apply]
    exact hasDerivAt_quadratic _ _ _
  have htr := HasDerivAt.fun_sum (u := univ) fun e _ => hE e e
  have hq := HasDerivAt.fun_sum (u := univ) fun e _ =>
    (line_hasDerivAt referenceCell (c, d) a e).mul (hE e b)
  have h : HasDerivAt (fun t : ℝ => V0 *
      (lam * (∑ e, greenLagrange (referenceCell + t • Pi.single (c, d) 1) e e) *
          (referenceCell + t • Pi.single (c, d) 1 : Cell) (a, b) +
        2 * mu * ∑ e, (referenceCell + t • Pi.single (c, d) 1 : Cell) (a, e) *
          greenLagrange (referenceCell + t • Pi.single (c, d) 1) e b)) _ 0 :=
    (((htr.const_mul lam).mul (line_hasDerivAt referenceCell (c, d) a b)).add
      (hq.const_mul (2 * mu))).const_mul V0
  rw [partialAt_eq_of_hasDerivAt (k := (c, d)) hd h]
  simp only [zero_smul, add_zero, greenLagrange_referenceCell, referenceCell_apply, mul_zero,
    zero_mul, zero_add, Finset.sum_const_zero]
  have h1 : ∑ e, (Elasticity.kron c e * Elasticity.kron e d +
      Elasticity.kron c e * Elasticity.kron e d) / 2 = Elasticity.kron c d := by
    rw [← sum_kron_mul_kron c d]
    exact Finset.sum_congr rfl fun e _ => by ring
  have h2 : ∑ e, Elasticity.kron a e * ((Elasticity.kron c b * Elasticity.kron e d +
      Elasticity.kron c e * Elasticity.kron b d) / 2) =
      (Elasticity.kron c b * Elasticity.kron a d + Elasticity.kron c a * Elasticity.kron b d) / 2 :=
    sum_kron_mul' a _
  rw [h1, h2, Elasticity.isotropic, kron_comm c b, kron_comm c a]
  ring

/-- For `lam >= 0`, `mu > 0` and `V = V0 > 0` the catalog elastic constants of the St
Venant-Kirchhoff energy at the reference store positive energy for every nonzero symmetric
strain. -/
theorem svkEnergy_posDef {lam mu V0 : ℝ} (hlam : 0 ≤ lam) (hmu : 0 < mu) (hV0 : 0 < V0) :
    Elasticity.PosDef
      (fun a b c d => elasticConstants (svkEnergy lam mu V0) V0 referenceCell a b c d) := by
  have h : (fun a b c d => elasticConstants (svkEnergy lam mu V0) V0 referenceCell a b c d) =
      Elasticity.isotropic lam mu := by
    funext a b c d
    rw [svkEnergy_elasticConstants, div_self hV0.ne', one_mul]
  rw [h, Elasticity.isotropic_stable_iff, Elasticity.voigtBulk_isotropic,
    Elasticity.voigtShear_isotropic]
  constructor <;> linarith

/-- The St Venant-Kirchhoff energy with `lam >= 0`, `mu > 0` and `V = V0 > 0` meets the
hypotheses of `voigt_pos_of_stable_reference`: at the reference the catalog's Voigt bulk and
shear moduli are positive and its Poisson ratio lies strictly between `-1` and `1/2`. -/
theorem svkEnergy_voigt_pos {lam mu V0 : ℝ} (hlam : 0 ≤ lam) (hmu : 0 < mu) (hV0 : 0 < V0) :
    0 < Elasticity.voigtBulk
          (fun a b c d => elasticConstants (svkEnergy lam mu V0) V0 referenceCell a b c d) ∧
      0 < Elasticity.voigtShear
          (fun a b c d => elasticConstants (svkEnergy lam mu V0) V0 referenceCell a b c d) ∧
      -1 < Elasticity.poissonRatio
          (Elasticity.voigtBulk
            (fun a b c d => elasticConstants (svkEnergy lam mu V0) V0 referenceCell a b c d))
          (Elasticity.voigtShear
            (fun a b c d => elasticConstants (svkEnergy lam mu V0) V0 referenceCell a b c d)) ∧
      Elasticity.poissonRatio
          (Elasticity.voigtBulk
            (fun a b c d => elasticConstants (svkEnergy lam mu V0) V0 referenceCell a b c d))
          (Elasticity.voigtShear
            (fun a b c d => elasticConstants (svkEnergy lam mu V0) V0 referenceCell a b c d)) <
        1 / 2 :=
  voigt_pos_of_stable_reference (svkEnergy lam mu V0) V0
    (fun α β hαβ => Eventually.of_forall fun G s => svkEnergy_rotateCell lam mu V0 α β hαβ s G)
    (svkEnergy_contDiff lam mu V0).contDiffAt (svkEnergy_cellStress_referenceCell lam mu V0 V0)
    (svkEnergy_posDef hlam hmu hV0)

end OMAI.PhyslibBridge.CellElasticity
