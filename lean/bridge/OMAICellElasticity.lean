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
If the energy is also invariant under every rotation and the reference is stress-free, they
have both minor symmetries as well, and the Voigt positivity theorem of `OMAIElasticity`
applies to them. The St Venant-Kirchhoff energy satisfies every one of these hypotheses: its
elastic constants at the reference are the isotropic tensor of its Lame parameters.
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
coordinate plane and twice continuously differentiable at the reference gives catalog elastic
constants with the major symmetry and both minor symmetries, `C_abcd = C_cdab = C_bacd = C_abdc`. -/
theorem elasticConstants_symmetries (E : Cell → ℝ) (V : ℝ)
    (hrot : ∀ α β, α ≠ β → ∀ s G, E (rotateCell α β s G) = E G)
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
    -- the energy is differentiable along the strain line near the reference
    have hnear : ∀ᶠ t in 𝓝 (0 : ℝ), DifferentiableAt ℝ E (line t) := by
      have hcont : Tendsto line (𝓝 0) (𝓝 referenceCell) := by
        have : Continuous line := by fun_prop
        simpa [line] using this.tendsto 0
      exact hcont.eventually ((hE.eventually (by simp)).mono fun G hG =>
        hG.differentiableAt (by norm_num))
    have hB : (fun t => (∑ b, cellStress E V (line t) α b * line t (β, b)) -
        (∑ b, cellStress E V (line t) β b * line t (α, b))) =ᶠ[𝓝 0] fun _ => 0 := by
      filter_upwards [hnear] with t ht
      rw [cellStress_rotation_balance E V (line t) α β ht (fun s => hrot α β hαβ s (line t)),
        sub_self]
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

/-- For a cell energy invariant under rotations in every coordinate plane and twice
continuously differentiable at a stress-free reference, whose catalog elastic constants store
positive energy for every nonzero symmetric strain, the catalog's Voigt bulk and shear moduli
are positive and its Poisson ratio lies strictly between `-1` and `1/2`. -/
theorem voigt_pos_of_stable_reference (E : Cell → ℝ) (V : ℝ)
    (hrot : ∀ α β, α ≠ β → ∀ s G, E (rotateCell α β s G) = E G)
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

end OMAI.PhyslibBridge.CellElasticity
