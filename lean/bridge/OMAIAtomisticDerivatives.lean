module

public import Mathlib.Analysis.Calculus.FDeriv.Symmetric
public import Mathlib.Analysis.Calculus.Deriv.MeanValue
public import Mathlib.Analysis.Calculus.Deriv.Pow
public import Mathlib.Analysis.Calculus.Deriv.Prod
public import Mathlib.Analysis.Calculus.MeanValue
public import Mathlib.Analysis.Calculus.IteratedDeriv.Defs
public import Mathlib.Analysis.SpecialFunctions.Trigonometric.Deriv
public import Mathlib.Tactic

/-!
# Derivatives of an atomistic potential energy

The catalog reads Hellmann-Feynman forces, second- and third-order force constants and their
finite-displacement estimate as partial derivatives of one potential energy surface. Physlib
has no model of an interatomic potential, so these are local results over Mathlib.

A configuration assigns three Cartesian coordinates to every site of a finite set. An energy
invariant under rigid translations and differentiable at a configuration has forces that sum
to zero there. A potential invariant under rigid translations has second-order force
constants whose sum over the sites of one index vanishes wherever the first partial derivative
`dV/du_k` is differentiable, and third-order ones wherever the second-order force constant
`Phi2_{kl}` is differentiable (the acoustic sum rules); a potential twice or three times
continuously differentiable there qualifies. An energy invariant under rotations in a
coordinate plane and differentiable at a configuration exerts no torque in that plane. The
central-difference estimate of a force constant from displaced forces differs from the
derivative by at most `M h^2 / 6`, with `M` a bound on the third derivative of the force along
the displacement, a quartic force constant when the force is `-grad V`. The force need only be
three times continuously differentiable on an open set containing the displacement segment, so
pair potentials singular at zero separation are covered.

Partial derivatives are read off Mathlib's `fderiv`, which is zero where a function is not
differentiable. Each sum rule therefore carries a differentiability hypothesis at the point
where it is evaluated; without one it could hold only through that zero value. Two-atom
witnesses give a nonzero force, torque term, second-order and third-order force constant. No
result validates a DFT, MLIP or finite-difference implementation.
-/

@[expose] public section

noncomputable section

open Finset

namespace OMAI.PhyslibBridge.Atomistic

section Partial

variable {ι : Type*} [Fintype ι] [DecidableEq ι]

/-- The partial derivative of `f` along coordinate `k` at `x`, read off its Fréchet
derivative; it is zero where `f` is not differentiable. -/
def partialAt (f : (ι → ℝ) → ℝ) (k : ι) (x : ι → ℝ) : ℝ := fderiv ℝ f x (Pi.single k 1)

theorem clm_apply_eq_sum (L : (ι → ℝ) →L[ℝ] ℝ) (v : ι → ℝ) :
    L v = ∑ k, v k * L (Pi.single k 1) := by
  have h := LinearMap.pi_apply_eq_sum_univ (L : (ι → ℝ) →ₗ[ℝ] ℝ) v
  simp only [ContinuousLinearMap.coe_coe, smul_eq_mul] at h
  rw [h]
  refine Finset.sum_congr rfl fun k _ => ?_
  congr 2
  funext j
  simp [Pi.single_apply, eq_comm]

omit [DecidableEq ι] in
/-- If `f` is differentiable at `x` and constant along a curve through `x` with velocity `w`
there, the derivative of `f` at `x` vanishes on `w`. -/
theorem fderiv_apply_eq_zero_of_invariant_curve (f : (ι → ℝ) → ℝ) (c : ℝ → ι → ℝ)
    (x w : ι → ℝ) (hd : DifferentiableAt ℝ f x) (hc0 : c 0 = x) (hc : HasDerivAt c w 0)
    (hf : ∀ s, f (c s) = f x) : fderiv ℝ f x w = 0 := by
  have hd' : HasFDerivAt f (fderiv ℝ f x) (c 0) := by rw [hc0]; exact hd.hasFDerivAt
  have h1 : HasDerivAt (f ∘ c) (fderiv ℝ f x w) 0 := hd'.comp_hasDerivAt 0 hc
  have h2 : HasDerivAt (f ∘ c) 0 0 := by
    have : f ∘ c = fun _ => f x := funext hf
    rw [this]
    exact hasDerivAt_const _ _
  exact h1.unique h2

/-- The partial derivative of a function differentiable at `x`, computed along the coordinate
line through `x`. -/
theorem partialAt_eq_of_hasDerivAt {f : (ι → ℝ) → ℝ} {x : ι → ℝ} {k : ι} {c : ℝ}
    (hd : DifferentiableAt ℝ f x)
    (hl : HasDerivAt (fun t : ℝ => f (x + t • Pi.single k 1)) c 0) : partialAt f k x = c := by
  have hline : HasDerivAt (fun t : ℝ => x + t • (Pi.single k 1 : ι → ℝ)) (Pi.single k 1) 0 := by
    simpa using ((hasDerivAt_id (0 : ℝ)).smul_const (Pi.single k 1 : ι → ℝ)).const_add x
  have hd' : HasFDerivAt f (fderiv ℝ f x) (x + (0 : ℝ) • (Pi.single k 1 : ι → ℝ)) := by
    simpa using hd.hasFDerivAt
  exact (hd'.comp_hasDerivAt (0 : ℝ) hline).unique hl

/-- A mixed partial derivative read off the second Fréchet derivative. -/
theorem partialAt_partialAt {g : (ι → ℝ) → ℝ} {u : ι → ℝ}
    (hg : DifferentiableAt ℝ (fderiv ℝ g) u) (l m : ι) :
    partialAt (fun y => partialAt g l y) m u =
      fderiv ℝ (fderiv ℝ g) u (Pi.single m 1) (Pi.single l 1) := by
  unfold partialAt
  rw [fderiv_clm_apply hg (differentiableAt_const _)]
  simp

/-- A partial derivative of a `C^(n+1)` function is `C^n`. -/
theorem contDiffAt_partialAt {n : ℕ} {g : (ι → ℝ) → ℝ} {u : ι → ℝ}
    (hg : ContDiffAt ℝ (n + 1) g u) (k : ι) :
    ContDiffAt ℝ n (fun x => partialAt g k x) u := by
  unfold partialAt
  exact (hg.fderiv_right (by simp)).clm_apply contDiffAt_const

/-- Mixed partial derivatives of a `C^2` function commute. -/
theorem partialAt_symm {g : (ι → ℝ) → ℝ} {u : ι → ℝ}
    (hg : ContDiffAt ℝ 2 g u) (l m : ι) :
    partialAt (fun y => partialAt g l y) m u = partialAt (fun y => partialAt g m y) l u := by
  have hd : DifferentiableAt ℝ (fderiv ℝ g) u :=
    (hg.fderiv_right (m := 1) (by norm_num)).differentiableAt (by norm_num)
  rw [partialAt_partialAt hd, partialAt_partialAt hd]
  exact (hg.isSymmSndFDerivAt (by simp)) _ _

end Partial

section Sites

variable {A : Type*} [Fintype A] [DecidableEq A]

/-- A rigid translation of every site by `t`. -/
def translate (t : Fin 3 → ℝ) (R : A × Fin 3 → ℝ) : A × Fin 3 → ℝ := fun k => R k + t k.2

/-- A rigid rotation by the angle `s` in the `(α, β)` coordinate plane, for `α ≠ β`. -/
def rotatePlane (α β : Fin 3) (s : ℝ) (R : A × Fin 3 → ℝ) : A × Fin 3 → ℝ := fun k =>
  if k.2 = α then Real.cos s * R (k.1, α) - Real.sin s * R (k.1, β)
  else if k.2 = β then Real.sin s * R (k.1, α) + Real.cos s * R (k.1, β)
  else R k

/-- The reviewed catalog expression of `compute_forces_hf`,
`F^{at}_{i, alpha} = -dE_tot/dR^{at}_{i, alpha}`. This definition alone is not a physical
proof. -/
def hfForce (E : (A × Fin 3 → ℝ) → ℝ) (R : A × Fin 3 → ℝ) (i : A) (α : Fin 3) : ℝ :=
  -partialAt E (i, α) R

/-- For a function differentiable at `u` and invariant under rigid translations of `u`, the
partial derivatives along one Cartesian direction sum to zero over the sites. -/
theorem sum_partialAt_eq_zero_of_translate (g : (A × Fin 3 → ℝ) → ℝ) (u : A × Fin 3 → ℝ)
    (hd : DifferentiableAt ℝ g u) (hg : ∀ t, g (translate t u) = g u) (β : Fin 3) :
    ∑ s, partialAt g (s, β) u = 0 := by
  set v : A × Fin 3 → ℝ := fun k => if k.2 = β then 1 else 0 with hv
  have hline : ∀ s : ℝ, g (u + s • v) = g u := by
    intro s
    have : u + s • v = translate (Pi.single β s) u := by
      funext k
      by_cases hk : k.2 = β <;> simp [translate, v, hk]
    rw [this]
    exact hg _
  have hc : HasDerivAt (fun s : ℝ => u + s • v) v 0 := by
    simpa using ((hasDerivAt_id (0 : ℝ)).smul_const v).const_add u
  have h0 := fderiv_apply_eq_zero_of_invariant_curve g (fun s => u + s • v) u v hd (by simp) hc
    hline
  rw [clm_apply_eq_sum, Fintype.sum_prod_type] at h0
  simpa [v, partialAt, ite_mul, Finset.sum_ite_eq'] using h0

/-- Hellmann-Feynman forces of an energy differentiable at `R` and invariant under rigid
translations of `R` sum to zero in every Cartesian direction. -/
theorem hfForce_sum_eq_zero (E : (A × Fin 3 → ℝ) → ℝ) (R : A × Fin 3 → ℝ)
    (hd : DifferentiableAt ℝ E R) (hE : ∀ t, E (translate t R) = E R) (α : Fin 3) :
    ∑ i, hfForce E R i α = 0 := by
  simp only [hfForce, Finset.sum_neg_distrib, neg_eq_zero]
  exact sum_partialAt_eq_zero_of_translate E R hd hE α

omit [Fintype A] [DecidableEq A] in
private theorem rotatePlane_zero (α β : Fin 3) (R : A × Fin 3 → ℝ) : rotatePlane α β 0 R = R := by
  funext ⟨i, a⟩
  by_cases ha : a = α
  · subst ha; simp [rotatePlane]
  · by_cases hb : a = β
    · subst hb; simp [rotatePlane, ha]
    · simp [rotatePlane, ha, hb]

omit [Fintype A] [DecidableEq A] in
private theorem rotatePlane_hasDerivAt (α β : Fin 3) (R : A × Fin 3 → ℝ) :
    HasDerivAt (fun s => rotatePlane α β s R)
      (fun k => if k.2 = α then -R (k.1, β) else if k.2 = β then R (k.1, α) else 0) 0 := by
  rw [hasDerivAt_pi]
  intro k
  by_cases ha : k.2 = α
  · have e : (fun s => rotatePlane α β s R k) =
        fun s => Real.cos s * R (k.1, α) - Real.sin s * R (k.1, β) := by
      funext s; simp [rotatePlane, ha]
    rw [e]
    have := ((Real.hasDerivAt_cos 0).mul_const (R (k.1, α))).sub
      ((Real.hasDerivAt_sin 0).mul_const (R (k.1, β)))
    convert this using 1
    simp [ha]
  · by_cases hb : k.2 = β
    · have hβα : β ≠ α := fun h => ha (hb.trans h)
      have e : (fun s => rotatePlane α β s R k) =
          fun s => Real.sin s * R (k.1, α) + Real.cos s * R (k.1, β) := by
        funext s; simp [rotatePlane, hb, hβα]
      rw [e]
      have := ((Real.hasDerivAt_sin 0).mul_const (R (k.1, α))).add
        ((Real.hasDerivAt_cos 0).mul_const (R (k.1, β)))
      convert this using 1
      simp [hb, hβα]
    · have e : (fun s => rotatePlane α β s R k) = fun _ => R k := by
        funext s; simp [rotatePlane, ha, hb]
      rw [e]
      simpa [ha, hb] using hasDerivAt_const (0 : ℝ) (R k)

/-- An energy differentiable at `R` and invariant under rotations of `R` in the `(α, β)` plane
exerts no torque in that plane: `sum_i (R_{i alpha} F_{i beta} - R_{i beta} F_{i alpha}) = 0`. -/
theorem hfForce_torque_eq_zero (E : (A × Fin 3 → ℝ) → ℝ) (R : A × Fin 3 → ℝ) (α β : Fin 3)
    (hd : DifferentiableAt ℝ E R) (hE : ∀ s, E (rotatePlane α β s R) = E R) :
    ∑ i, (R (i, α) * hfForce E R i β - R (i, β) * hfForce E R i α) = 0 := by
  by_cases hαβ : α = β
  · subst hαβ; simp
  have h0 := fderiv_apply_eq_zero_of_invariant_curve E (fun s => rotatePlane α β s R) R _ hd
    (rotatePlane_zero α β R) (rotatePlane_hasDerivAt α β R) hE
  rw [clm_apply_eq_sum, Fintype.sum_prod_type] at h0
  have key : ∀ i, (∑ γ : Fin 3, (if γ = α then -R (i, β) else if γ = β then R (i, α) else 0) *
      fderiv ℝ E R (Pi.single (i, γ) 1)) =
      -(R (i, α) * hfForce E R i β - R (i, β) * hfForce E R i α) := by
    intro i
    simp only [hfForce, partialAt]
    fin_cases α <;> fin_cases β <;> simp_all [Fin.sum_univ_three] <;> ring
  simp only [key, Finset.sum_neg_distrib, neg_eq_zero] at h0
  exact h0

/-! ## Force constants -/

/-- The reviewed catalog expression of `compute_force_constants[order=2]`,
`Phi2_{kl} = d^2 V / du_k du_l`. This definition alone is not a physical proof. -/
def forceConstant2 (V : (A × Fin 3 → ℝ) → ℝ) (u : A × Fin 3 → ℝ) (k l : A × Fin 3) : ℝ :=
  partialAt (fun x => partialAt V k x) l u

/-- The reviewed catalog expression of `compute_force_constants[order=3]`,
`Phi3_{klm} = d^3 V / du_k du_l du_m`. This definition alone is not a physical proof. -/
def forceConstant3 (V : (A × Fin 3 → ℝ) → ℝ) (u : A × Fin 3 → ℝ) (k l m : A × Fin 3) : ℝ :=
  partialAt (fun y => forceConstant2 V y k l) m u

/-- Partial derivatives of a translation-invariant function are translation invariant. -/
theorem partialAt_translate (g : (A × Fin 3 → ℝ) → ℝ) (hg : ∀ x t, g (translate t x) = g x)
    (k : A × Fin 3) : ∀ x t, partialAt g k (translate t x) = partialAt g k x := by
  intro x t
  have hc : ∀ y : A × Fin 3 → ℝ, translate t y = y + fun m : A × Fin 3 => t m.2 := fun y => by
    funext m; simp [translate]
  unfold partialAt
  rw [hc, ← fderiv_comp_add_right]
  congr 2
  funext y
  rw [← hc]
  exact hg y t

/-- The acoustic sum rule at second order: for a potential invariant under rigid translations
whose first partial derivative `dV/du_k` is differentiable at `u`, `sum_s Phi2_{k, (s, beta)} = 0`
for every direction `beta`. A potential twice continuously differentiable at `u` qualifies. -/
theorem forceConstant2_sum_eq_zero (V : (A × Fin 3 → ℝ) → ℝ) (hV : ∀ x t, V (translate t x) = V x)
    (u : A × Fin 3 → ℝ) (k : A × Fin 3) (hV2 : DifferentiableAt ℝ (fun x => partialAt V k x) u)
    (β : Fin 3) :
    ∑ s, forceConstant2 V u k (s, β) = 0 :=
  sum_partialAt_eq_zero_of_translate _ u hV2 (fun t => partialAt_translate V hV k u t) β

/-- The acoustic sum rule at third order: for a potential invariant under rigid translations
whose second-order force constant `Phi2_{kl}` is differentiable in the configuration at `u`,
`sum_s Phi3_{k, l, (s, gamma)} = 0` for every direction `gamma`. A potential three times
continuously differentiable at `u` qualifies. -/
theorem forceConstant3_sum_eq_zero (V : (A × Fin 3 → ℝ) → ℝ) (hV : ∀ x t, V (translate t x) = V x)
    (u : A × Fin 3 → ℝ) (k l : A × Fin 3)
    (hV3 : DifferentiableAt ℝ (fun y => forceConstant2 V y k l) u) (γ : Fin 3) :
    ∑ s, forceConstant3 V u k l (s, γ) = 0 :=
  sum_partialAt_eq_zero_of_translate (fun y => forceConstant2 V y k l) u hV3
    (fun t => partialAt_translate _ (partialAt_translate V hV k) l u t) γ

/-- A potential three times continuously differentiable at `u` satisfies the hypothesis of the
third-order sum rule. -/
theorem forceConstant3_sum_eq_zero_of_contDiffAt (V : (A × Fin 3 → ℝ) → ℝ)
    (hV : ∀ x t, V (translate t x) = V x) (u : A × Fin 3 → ℝ) (hV3 : ContDiffAt ℝ 3 V u)
    (k l : A × Fin 3) (γ : Fin 3) : ∑ s, forceConstant3 V u k l (s, γ) = 0 :=
  forceConstant3_sum_eq_zero V hV u k l
    ((contDiffAt_partialAt (n := 1)
      ((contDiffAt_partialAt (n := 2) (hV3.of_le (by norm_num)) k).of_le (by norm_num)) l).differentiableAt
      (by norm_num)) γ

/-- For a potential three times continuously differentiable at `u`, the third-order force
constants are symmetric under every permutation of their three indices. -/
theorem forceConstant3_symm (V : (A × Fin 3 → ℝ) → ℝ) (u : A × Fin 3 → ℝ)
    (hV : ContDiffAt ℝ 3 V u) (k l m : A × Fin 3) :
    forceConstant3 V u k l m = forceConstant3 V u l k m ∧
      forceConstant3 V u k l m = forceConstant3 V u k m l := by
  constructor
  · -- symmetric second derivatives near `u` make the two functions agree near `u`
    have hnear : ∀ᶠ y in nhds u, forceConstant2 V y k l = forceConstant2 V y l k := by
      have h2 : ContDiffAt ℝ 2 V u := hV.of_le (by norm_num)
      filter_upwards [h2.eventually (by simp)] with y hy2
      exact partialAt_symm hy2 k l
    unfold forceConstant3 partialAt
    rw [Filter.EventuallyEq.fderiv_eq hnear]
  · have h2 : ContDiffAt ℝ 2 (fun x => partialAt V k x) u :=
      contDiffAt_partialAt (n := 2) (hV.of_le (by norm_num)) k
    exact partialAt_symm h2 l m

/-! ## Finite-displacement force constants -/

/-- The reviewed catalog expression of `compute_fc2_finite_displacement`,
`Phi2_{ij} = -dF_j/du_i`, the derivative of the force on coordinate `j` with respect to the
displacement of coordinate `i`. This definition alone is not a physical proof. -/
def fdForceConstant (F : (A × Fin 3 → ℝ) → A × Fin 3 → ℝ) (u : A × Fin 3 → ℝ)
    (i j : A × Fin 3) : ℝ :=
  -partialAt (fun x => F x j) i u

/-- The central-difference estimate of `-dF_j/du_i` from the forces at `u -+ h e_i`. -/
def centralDifference (F : (A × Fin 3 → ℝ) → A × Fin 3 → ℝ) (u : A × Fin 3 → ℝ)
    (i j : A × Fin 3) (h : ℝ) : ℝ :=
  (F (u - h • Pi.single i 1) j - F (u + h • Pi.single i 1) j) / (2 * h)

private theorem abs_le_of_deriv_abs_le {f f' : ℝ → ℝ} {K : ℝ} {n : ℕ} (hf0 : f 0 = 0) {b : ℝ}
    (hf : ∀ x ∈ Set.Icc 0 b, HasDerivAt f (f' x) x) (hb0 : 0 ≤ b)
    (hb : ∀ x ∈ Set.Icc 0 b, |f' x| ≤ K * x ^ n) :
    |f b| ≤ K * b ^ (n + 1) / (n + 1) := by
  have hn : (0 : ℝ) < n + 1 := by positivity
  have hP : ∀ x, HasDerivAt (fun x => K * x ^ (n + 1) / (n + 1)) (K * x ^ n) x := by
    intro x
    have := ((hasDerivAt_pow (n + 1) x).const_mul K).div_const ((n : ℝ) + 1)
    convert this using 1
    field_simp
    push_cast
    ring
  have mono : ∀ (s : ℝ), s = 1 ∨ s = -1 →
      MonotoneOn (fun x => K * x ^ (n + 1) / (n + 1) - s * f x) (Set.Icc 0 b) := by
    intro s hs
    have hd : ∀ x ∈ Set.Icc 0 b, HasDerivAt (fun x => K * x ^ (n + 1) / (n + 1) - s * f x)
        (K * x ^ n - s * f' x) x := fun x hx => (hP x).sub ((hf x hx).const_mul s)
    apply monotoneOn_of_deriv_nonneg (convex_Icc 0 b)
    · exact fun x hx => (hd x hx).continuousAt.continuousWithinAt
    · exact fun x hx => (hd x (interior_subset hx)).differentiableAt.differentiableWithinAt
    · intro x hx
      have hx' : x ∈ Set.Icc 0 b := interior_subset hx
      rw [(hd x hx').deriv]
      have := hb x hx'
      rcases hs with rfl | rfl
      · have := (abs_le.mp this).2; linarith
      · have := (abs_le.mp this).1; linarith
  have h1 := mono 1 (Or.inl rfl) ⟨le_rfl, hb0⟩ ⟨hb0, le_rfl⟩ hb0
  have h2 := mono (-1) (Or.inr rfl) ⟨le_rfl, hb0⟩ ⟨hb0, le_rfl⟩ hb0
  have hz : (0 : ℝ) ^ (n + 1) = 0 := zero_pow (Nat.succ_ne_zero n)
  simp only [hz, hf0, mul_zero, zero_div, one_mul, neg_one_mul, sub_zero, sub_neg_eq_add] at h1 h2
  rw [abs_le]
  constructor <;> linarith

/-- The central difference `(g(h) - g(-h)) / (2h)` of a function three times continuously
differentiable on an open set containing `[-h, h]` differs from `g'(0)` by at most
`M h^2 / 6`, where `M` bounds `|g'''|` on `[-h, h]`. -/
theorem central_difference_bound {g : ℝ → ℝ} {U : Set ℝ} {h M : ℝ} (hh : 0 < h)
    (hU : IsOpen U) (hIcc : Set.Icc (-h) h ⊆ U) (hg : ContDiffOn ℝ 3 g U)
    (hM : ∀ t ∈ Set.Icc (-h) h, |iteratedDeriv 3 g t| ≤ M) :
    |(g h - g (-h)) / (2 * h) - deriv g 0| ≤ M * h ^ 2 / 6 := by
  have g1 : ContDiffOn ℝ 2 (deriv g) U := hg.deriv_of_isOpen hU (by norm_num)
  have g2 : ContDiffOn ℝ 1 (deriv (deriv g)) U := g1.deriv_of_isOpen hU (by norm_num)
  have d0 : ∀ x ∈ Set.Icc (-h) h, DifferentiableAt ℝ g x := fun x hx =>
    (hg.contDiffAt (hU.mem_nhds (hIcc hx))).differentiableAt (by norm_num)
  have d1 : ∀ x ∈ Set.Icc (-h) h, DifferentiableAt ℝ (deriv g) x := fun x hx =>
    (g1.contDiffAt (hU.mem_nhds (hIcc hx))).differentiableAt (by norm_num)
  have d2 : ∀ x ∈ Set.Icc (-h) h, DifferentiableAt ℝ (deriv (deriv g)) x := fun x hx =>
    (g2.contDiffAt (hU.mem_nhds (hIcc hx))).differentiableAt (by norm_num)
  have h3 : iteratedDeriv 3 g = deriv (deriv (deriv g)) := by
    simp [iteratedDeriv_succ, iteratedDeriv_zero]
  rw [h3] at hM
  -- points of `[0, t]` with `t <= h` and their negatives lie in `[-h, h]`
  have mem : ∀ t ∈ Set.Icc 0 h, ∀ x ∈ Set.Icc 0 t, x ∈ Set.Icc (-h) h ∧ -x ∈ Set.Icc (-h) h :=
    fun t ht x hx => ⟨⟨by linarith [hx.1], by linarith [hx.2, ht.2]⟩,
      ⟨by linarith [hx.2, ht.2], by linarith [hx.1]⟩⟩
  -- |g''(t) - g''(-t)| <= 2 M t
  have s1 : ∀ t ∈ Set.Icc 0 h,
      |deriv (deriv g) t - deriv (deriv g) (-t)| ≤ (2 * M) * t ^ 1 := by
    intro t ht
    have := abs_le_of_deriv_abs_le (f := fun x => deriv (deriv g) x - deriv (deriv g) (-x))
      (f' := fun x => deriv (deriv (deriv g)) x + deriv (deriv (deriv g)) (-x)) (K := 2 * M) (n := 0)
      (by simp)
      (fun x hx => by
        have hneg := (d2 (-x) (mem t ht x hx).2).hasDerivAt.comp x (hasDerivAt_neg x)
        convert (d2 x (mem t ht x hx).1).hasDerivAt.sub hneg using 1 <;> (try funext y) <;> simp)
      ht.1
      (fun x hx => by
        have ha := hM x ⟨by linarith [hx.1, ht.2], by linarith [hx.2, ht.2]⟩
        have hb := hM (-x) ⟨by linarith [hx.2, ht.2], by linarith [hx.1]⟩
        calc |deriv (deriv (deriv g)) x + deriv (deriv (deriv g)) (-x)|
            ≤ |deriv (deriv (deriv g)) x| + |deriv (deriv (deriv g)) (-x)| := abs_add_le _ _
          _ ≤ 2 * M * x ^ 0 := by simp; linarith)
    simpa using this
  -- |g'(t) + g'(-t) - 2 g'(0)| <= M t^2
  have s2 : ∀ t ∈ Set.Icc 0 h,
      |deriv g t + deriv g (-t) - 2 * deriv g 0| ≤ M * t ^ 2 := by
    intro t ht
    have := abs_le_of_deriv_abs_le (f := fun x => deriv g x + deriv g (-x) - 2 * deriv g 0)
      (f' := fun x => deriv (deriv g) x - deriv (deriv g) (-x)) (K := 2 * M) (n := 1)
      (by simp; ring)
      (fun x hx => by
        have hneg := (d1 (-x) (mem t ht x hx).2).hasDerivAt.comp x (hasDerivAt_neg x)
        convert ((d1 x (mem t ht x hx).1).hasDerivAt.add hneg).sub_const (2 * deriv g 0) using 1 <;>
          first | (funext y; simp) | ring)
      ht.1
      (fun x hx => s1 x ⟨hx.1, hx.2.trans ht.2⟩)
    convert this using 1
    push_cast
    ring
  -- |g(h) - g(-h) - 2 h g'(0)| <= M h^3 / 3
  have s3 := abs_le_of_deriv_abs_le (f := fun x => g x - g (-x) - 2 * x * deriv g 0)
    (f' := fun x => deriv g x + deriv g (-x) - 2 * deriv g 0) (K := M) (n := 2)
    (by simp)
    (fun x hx => by
      have hneg := (d0 (-x) (mem h ⟨hh.le, le_rfl⟩ x hx).2).hasDerivAt.comp x (hasDerivAt_neg x)
      have hlin := ((hasDerivAt_id x).const_mul (2 : ℝ)).mul_const (deriv g 0)
      convert ((d0 x (mem h ⟨hh.le, le_rfl⟩ x hx).1).hasDerivAt.sub hneg).sub hlin using 1 <;>
        (try funext y) <;> simp)
    hh.le s2
  have h2h : (0 : ℝ) < 2 * h := by positivity
  rw [show (g h - g (-h)) / (2 * h) - deriv g 0 = (g h - g (-h) - 2 * h * deriv g 0) / (2 * h) by
    field_simp]
  rw [abs_div, abs_of_pos h2h, div_le_iff₀ h2h]
  have : M * h ^ (2 + 1) / ((2 : ℕ) + 1) = M * h ^ 3 / 3 := by push_cast; ring
  rw [this] at s3
  nlinarith [s3]

/-- The central-difference estimate of `-dF_j/du_i` from forces at `u -+ h e_i` differs from
the catalog's finite-displacement force constant by at most `M h^2 / 6`, where `M` bounds the
third derivative of the force `F_j` along the displacement on `[-h, h]`; for `F = -grad V` that
derivative is minus the quartic force constant `d^4 V / du_j du_i^3`. The force must be
differentiable at `u`
and three times continuously differentiable along the displacement line on an open set `U`
of steps containing `[-h, h]`, which holds for a potential four times continuously
differentiable near the displaced configurations, singular pair potentials included. -/
theorem centralDifference_error (F : (A × Fin 3 → ℝ) → A × Fin 3 → ℝ) (u : A × Fin 3 → ℝ)
    (i j : A × Fin 3) {U : Set ℝ} {h M : ℝ} (hh : 0 < h)
    (hFu : DifferentiableAt ℝ (fun x => F x j) u) (hU : IsOpen U) (hIcc : Set.Icc (-h) h ⊆ U)
    (hF : ContDiffOn ℝ 3 (fun t : ℝ => F (u + t • Pi.single i 1) j) U)
    (hM : ∀ t ∈ Set.Icc (-h) h, |iteratedDeriv 3 (fun t : ℝ => F (u + t • Pi.single i 1) j) t| ≤ M) :
    |centralDifference F u i j h - fdForceConstant F u i j| ≤ M * h ^ 2 / 6 := by
  set g : ℝ → ℝ := fun t => F (u + t • Pi.single i 1) j
  have hline : HasDerivAt (fun t : ℝ => u + t • (Pi.single i 1 : A × Fin 3 → ℝ)) (Pi.single i 1) 0 := by
    simpa using ((hasDerivAt_id (0 : ℝ)).smul_const (Pi.single i 1 : A × Fin 3 → ℝ)).const_add u
  have hd : HasFDerivAt (fun x => F x j) (fderiv ℝ (fun x => F x j) u)
      (u + (0 : ℝ) • (Pi.single i 1 : A × Fin 3 → ℝ)) := by simpa using hFu.hasFDerivAt
  have hcomp := hd.comp_hasDerivAt (0 : ℝ) hline
  have hg0 : deriv g 0 = partialAt (fun x => F x j) i u := hcomp.deriv
  have hcd : centralDifference F u i j h = -((g h - g (-h)) / (2 * h)) := by
    simp only [centralDifference, g, neg_smul, ← sub_eq_add_neg]
    ring
  rw [hcd, fdForceConstant, ← hg0,
    show -((g h - g (-h)) / (2 * h)) - -deriv g 0 = -((g h - g (-h)) / (2 * h) - deriv g 0) by ring,
    abs_neg]
  exact central_difference_bound hh hU hIcc hF hM

/-! ## Two-atom witnesses -/

/-- The squared separation `|R_1 - R_0|^2` of two atoms, a translation- and rotation-invariant
energy. -/
def pairEnergy (R : Fin 2 × Fin 3 → ℝ) : ℝ :=
  (R (1, 0) - R (0, 0)) ^ 2 + (R (1, 1) - R (0, 1)) ^ 2 + (R (1, 2) - R (0, 2)) ^ 2

/-- Two atoms one unit apart along the first axis. -/
def pairConfig : Fin 2 × Fin 3 → ℝ := fun k => if k = (1, 0) then 1 else 0

/-- Atom 0 at `(1, 0, 0)` and atom 1 at `(0, 1, 0)`, a bond off the coordinate axes. -/
def bentConfig : Fin 2 × Fin 3 → ℝ := fun k => if k = (0, 0) ∨ k = (1, 1) then 1 else 0

theorem pairEnergy_translate (t : Fin 3 → ℝ) (R : Fin 2 × Fin 3 → ℝ) :
    pairEnergy (translate t R) = pairEnergy R := by
  simp [pairEnergy, translate]

theorem pairEnergy_rotatePlane (α β : Fin 3) (hαβ : α ≠ β) (s : ℝ) (R : Fin 2 × Fin 3 → ℝ) :
    pairEnergy (rotatePlane α β s R) = pairEnergy R := by
  fin_cases α <;> fin_cases β <;> simp_all [pairEnergy, rotatePlane] <;>
    nlinarith [Real.sin_sq_add_cos_sq s]

theorem pairEnergy_contDiff : ContDiff ℝ 2 pairEnergy := by
  unfold pairEnergy
  fun_prop

/-- The gradient of the pair energy on atom 0, `dE/dR_{0 a} = -2 (R_{1 a} - R_{0 a})`. -/
theorem pairEnergy_partialAt (a : Fin 3) (R : Fin 2 × Fin 3 → ℝ) :
    partialAt pairEnergy (0, a) R = -2 * (R (1, a) - R (0, a)) := by
  apply partialAt_eq_of_hasDerivAt (pairEnergy_contDiff.differentiable (by norm_num) R)
  have e : (fun t : ℝ => pairEnergy (R + t • Pi.single (0, a) 1)) =
      fun t => pairEnergy R - 2 * (R (1, a) - R (0, a)) * t + t ^ 2 := by
    funext t
    fin_cases a <;> simp [pairEnergy] <;> ring
  rw [e]
  have := (((hasDerivAt_id' (0 : ℝ)).const_mul (2 * (R (1, a) - R (0, a)))).const_sub
    (pairEnergy R)).add (hasDerivAt_pow 2 (0 : ℝ))
  convert this using 1
  simp

/-- The pair energy satisfies the hypotheses of the force-balance theorems with a nonzero force:
the force on atom 0 along the bond is `2`. -/
theorem pairEnergy_force : hfForce pairEnergy pairConfig 0 0 = 2 := by
  simp [hfForce, pairEnergy_partialAt, pairConfig]

/-- At the bent configuration the torque balance has nonzero terms: atom 0 contributes `2` to
`sum_i (R_{i x} F_{i y} - R_{i y} F_{i x})`. -/
theorem pairEnergy_torque_term :
    bentConfig (0, 0) * hfForce pairEnergy bentConfig 0 1 -
      bentConfig (0, 1) * hfForce pairEnergy bentConfig 0 0 = 2 := by
  simp [hfForce, pairEnergy_partialAt, bentConfig]

/-- The pair energy has a nonzero second-order force constant between the two atoms, so the
acoustic sum rule balances nonzero terms: `Phi2_{(0,0),(1,0)} = -2`. -/
theorem pairEnergy_forceConstant2 : forceConstant2 pairEnergy pairConfig (0, 0) (1, 0) = -2 := by
  have hpartial : (fun x => partialAt pairEnergy ((0 : Fin 2), (0 : Fin 3)) x) =
      fun x => -2 * (x (1, 0) - x (0, 0)) := funext (pairEnergy_partialAt 0)
  unfold forceConstant2
  rw [hpartial]
  have h10 := (ContinuousLinearMap.proj (R := ℝ) (φ := fun _ : Fin 2 × Fin 3 => ℝ)
    ((1 : Fin 2), (0 : Fin 3))).hasFDerivAt (x := pairConfig)
  have h00 := (ContinuousLinearMap.proj (R := ℝ) (φ := fun _ : Fin 2 × Fin 3 => ℝ)
    ((0 : Fin 2), (0 : Fin 3))).hasFDerivAt (x := pairConfig)
  have hlin := (h10.sub h00).const_mul (-2 : ℝ)
  have hfd := (show HasFDerivAt (fun x : Fin 2 × Fin 3 → ℝ => -2 * (x (1, 0) - x (0, 0))) _
    pairConfig from hlin)
  unfold partialAt
  rw [hfd.fderiv]
  simp

/-- A partial derivative of a function of the bond coordinate `R_{1x} - R_{0x}` alone. -/
theorem bond_partialAt {f : (Fin 2 × Fin 3 → ℝ) → ℝ} {φ φ' : ℝ → ℝ}
    (hf : ∀ y, f y = φ (y (1, 0) - y (0, 0))) (hφ : ∀ s, HasDerivAt φ (φ' s) s)
    (x : Fin 2 × Fin 3 → ℝ) (k : Fin 2 × Fin 3) :
    partialAt f k x = φ' (x (1, 0) - x (0, 0)) *
      ((Pi.single k (1 : ℝ) : Fin 2 × Fin 3 → ℝ) (1, 0) -
        (Pi.single k (1 : ℝ) : Fin 2 × Fin 3 → ℝ) (0, 0)) := by
  obtain rfl : f = fun y => φ (y (1, 0) - y (0, 0)) := funext hf
  have h10 := (ContinuousLinearMap.proj (R := ℝ) (φ := fun _ : Fin 2 × Fin 3 => ℝ)
    ((1 : Fin 2), (0 : Fin 3))).hasFDerivAt (x := x)
  have h00 := (ContinuousLinearMap.proj (R := ℝ) (φ := fun _ : Fin 2 × Fin 3 => ℝ)
    ((0 : Fin 2), (0 : Fin 3))).hasFDerivAt (x := x)
  have h := (hφ (x (1, 0) - x (0, 0))).comp_hasFDerivAt x (h10.sub h00)
  have hfd := (show HasFDerivAt (fun y : Fin 2 × Fin 3 → ℝ => φ (y (1, 0) - y (0, 0))) _ x from h)
  unfold partialAt
  rw [hfd.fderiv]
  simp

/-- The cubic bond energy `(R_{1x} - R_{0x})^3` of two atoms, invariant under rigid
translations. -/
def cubicBond (R : Fin 2 × Fin 3 → ℝ) : ℝ := (R (1, 0) - R (0, 0)) ^ 3

theorem cubicBond_translate (t : Fin 3 → ℝ) (R : Fin 2 × Fin 3 → ℝ) :
    cubicBond (translate t R) = cubicBond R := by
  simp [cubicBond, translate]

theorem cubicBond_contDiff : ContDiff ℝ 3 cubicBond := by
  unfold cubicBond
  fun_prop

/-- The cubic bond energy has a nonzero third-order force constant, so the third-order acoustic
sum rule balances nonzero terms: `Phi3_{(0,0),(0,0),(1,0)} = 6`. -/
theorem cubicBond_forceConstant3 :
    forceConstant3 cubicBond pairConfig (0, 0) (0, 0) (1, 0) = 6 := by
  have p1 : ∀ x : Fin 2 × Fin 3 → ℝ,
      partialAt cubicBond (0, 0) x = -3 * (x (1, 0) - x (0, 0)) ^ 2 := by
    intro x
    rw [bond_partialAt (f := cubicBond) (φ := fun s => s ^ 3) (φ' := fun s => 3 * s ^ 2)
      (fun y => rfl) (fun s => by simpa using hasDerivAt_pow 3 s) x (0, 0)]
    simp
  have p2 : ∀ y : Fin 2 × Fin 3 → ℝ,
      forceConstant2 cubicBond y (0, 0) (0, 0) = 6 * (y (1, 0) - y (0, 0)) := by
    intro y
    unfold forceConstant2
    rw [bond_partialAt (f := fun x => partialAt cubicBond (0, 0) x) (φ := fun s => -3 * s ^ 2)
      (φ' := fun s => -3 * (2 * s)) p1
      (fun s => by simpa using (hasDerivAt_pow 2 s).const_mul (-3 : ℝ)) y (0, 0)]
    simp
    ring
  unfold forceConstant3
  rw [bond_partialAt (f := fun y => forceConstant2 cubicBond y (0, 0) (0, 0)) (φ := fun s => 6 * s)
    (φ' := fun _ => 6) p2 (fun s => by simpa using (hasDerivAt_id' s).const_mul (6 : ℝ))
    pairConfig (1, 0)]
  simp

end Sites

end OMAI.PhyslibBridge.Atomistic
