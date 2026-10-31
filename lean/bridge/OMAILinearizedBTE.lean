module

public import Mathlib.Analysis.SpecialFunctions.Exp
public import Mathlib.Analysis.SpecialFunctions.Sqrt
public import Mathlib.LinearAlgebra.Matrix.PosDef
public import Mathlib.Tactic
public import OMAIPhyslibKappaContraction

/-!
# The linearized phonon Boltzmann equation

The catalog solves the linearized BTE `Σ_{q'ν'} M_{qν,q'ν'} F^α_{q'ν'} = c_{qν} v^α_{qν}` with the
symmetric weighting `M = C^(1/2) Ω~ C^(1/2)` of Chaput's collision matrix (Phys. Rev. Lett. 110,
265506 (2013)). Its Kronecker term is the scattering rate `2 Γ` of the canonical linewidth
`Γ = Im Σ = 1/(2 τ)`, and a kernel enters every element, the diagonal included, with the constant
`π / (N_q ħ²)` of `2 Γ`, `|V₃|²` in the labeling `q + q' + q'' = 0`, the weight `2 √(n'' (n'' + 1))`
of the third mode and three energy channels. The conductivity is `κ^{αβ} = Σ c v^α F^β / (V N_q)`. Physlib has
no phonon-transport model, so these results use Mathlib and the local contraction module only.

The catalog collision matrix is symmetric for an even smearing kernel and a `|V₃|²` symmetric
under exchange of its first two modes on momentum-conserving triples. Without the in-scattering
kernel the solution is the relaxation-time `F = v / (2 Γ)`. For a symmetric collision matrix the conductivity of any solution is symmetric
(Onsager), and if Chaput's matrix is positive semidefinite and every mode heat capacity is
nonnegative, the conductivity is positive semidefinite. The positive semidefiniteness of `Ω~`
itself, which needs exact energy conservation, is a stated hypothesis, not a result here.
-/

@[expose] public section

noncomputable section

open Real Finset Matrix

namespace OMAI.PhyslibBridge.LinearizedBTE

/-! ## Catalog transcriptions -/

/-- The Bose-Einstein occupation `n(x) = 1 / (eˣ - 1)` at `x = ħω / (k_B T)`. -/
def bose (x : ℝ) : ℝ := 1 / (exp x - 1)

/-- Chaput's symmetric collision matrix `Ω~` of the catalog's
`solve_bte[bte_solver=direct_inverse]` auxiliary formula, on modes `(q, ν)` of a finite mesh `Q`
with linewidths `Gamma`, kernel `V3`, frequencies `omega` and smearing kernel `delta`. This
definition alone is not a physical proof. -/
def chaputCollision {Q ι : Type*} [Fintype Q] [AddCommGroup Q] [DecidableEq Q] [Fintype ι]
    [DecidableEq ι] (hbar kB T : ℝ) (delta : ℝ → ℝ) (omega Gamma : Q → ι → ℝ)
    (V3 : Q → ι → Q → ι → Q → ι → ℝ) : Matrix (Q × ι) (Q × ι) ℝ :=
  fun m m' =>
    2 * Gamma m.1 m.2 * (if m = m' then 1 else 0) +
      π / (Fintype.card Q * hbar ^ 2) *
        ∑ ν'', V3 m.1 m.2 m'.1 m'.2 (-m.1 - m'.1) ν'' *
          (2 * √(bose (hbar * omega (-m.1 - m'.1) ν'' / (kB * T)) *
            (1 + bose (hbar * omega (-m.1 - m'.1) ν'' / (kB * T))))) *
          (delta (omega m'.1 m'.2 - omega m.1 m.2 + omega (-m.1 - m'.1) ν'') +
            delta (omega m'.1 m'.2 - omega m.1 m.2 - omega (-m.1 - m'.1) ν'') +
            delta (omega m'.1 m'.2 + omega m.1 m.2 - omega (-m.1 - m'.1) ν''))

/-- The weighting `M_{m m'} = √(c_m c_m') Ω~_{m m'}` of the catalog's auxiliary formula. -/
def lbteMatrix {κ : Type*} (c : κ → ℝ) (Ω : Matrix κ κ ℝ) : Matrix κ κ ℝ :=
  fun m m' => √(c m * c m') * Ω m m'

/-- The reviewed catalog expression of `solve_bte[bte_solver=direct_inverse]`: the linear system
`Σ_{m'} M_{m m'} F^α_{m'} = c_m v^α_m`. This definition alone is not a physical proof. -/
def lbteSolves {κ : Type*} [Fintype κ] (M : Matrix κ κ ℝ) (c : κ → ℝ) (v F : κ → Fin 3 → ℝ) :
    Prop :=
  ∀ m α, ∑ m', M m m' * F m' α = c m * v m α

/-- The reviewed catalog expression of `contract_kappa[bte_solver=direct_inverse]`:
`κ^{αβ} = Σ_m c_m v^α_m F^β_m / (V N_q)`. This definition alone is not a physical proof. -/
def lbteKappa {κ : Type*} [Fintype κ] (c : κ → ℝ) (v F : κ → Fin 3 → ℝ) (V Nq : ℝ) :
    Matrix (Fin 3) (Fin 3) ℝ :=
  fun α β => (∑ m, c m * v m α * F m β) / (V * Nq)

/-! ## Symmetry of the collision matrix -/

section Symmetry

variable {Q ι : Type*} [Fintype Q] [AddCommGroup Q] [DecidableEq Q] [Fintype ι] [DecidableEq ι]

private theorem chaputCollision_isSymm_of_all {hbar kB T : ℝ} (delta : ℝ → ℝ) (omega Gamma : Q → ι → ℝ)
    (V3 : Q → ι → Q → ι → Q → ι → ℝ) (heven : ∀ x, delta (-x) = delta x)
    (hV3 : ∀ q ν q' ν' q'' ν'', V3 q ν q' ν' q'' ν'' = V3 q' ν' q ν q'' ν'') :
    (chaputCollision hbar kB T delta omega Gamma V3).IsSymm := by
  ext m m'
  simp only [transpose_apply, chaputCollision]
  have hq : -m'.1 - m.1 = -m.1 - m'.1 := by abel
  rw [hq]
  congr 1
  · by_cases h : m = m'
    · subst h; rfl
    · simp [h, Ne.symm h]
  · congr 1
    refine sum_congr rfl fun ν'' _ => ?_
    rw [hV3 m'.1 m'.2 m.1 m.2]
    congr 1
    set a := omega m.1 m.2
    set b := omega m'.1 m'.2
    set d := omega (-m.1 - m'.1) ν''
    rw [show a - b + d = -(b - a - d) by ring, show a - b - d = -(b - a + d) by ring, heven, heven,
      add_comm a b]
    ring

/-- For an even smearing kernel and a `|V₃|²` symmetric under exchange of its first two modes on
the momentum-conserving triples `(q, q', -q - q')` that the matrix reads, the catalog's collision
matrix is symmetric. -/
theorem chaputCollision_isSymm {hbar kB T : ℝ} (delta : ℝ → ℝ) (omega Gamma : Q → ι → ℝ)
    (V3 : Q → ι → Q → ι → Q → ι → ℝ) (heven : ∀ x, delta (-x) = delta x)
    (hV3 : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = V3 q' ν' q ν (-q - q') ν'') :
    (chaputCollision hbar kB T delta omega Gamma V3).IsSymm := by
  set V3' : Q → ι → Q → ι → Q → ι → ℝ := fun q ν q' ν' _ ν'' => V3 q ν q' ν' (-q - q') ν''
  have hsame : chaputCollision hbar kB T delta omega Gamma V3 =
      chaputCollision hbar kB T delta omega Gamma V3' := rfl
  rw [hsame]
  refine chaputCollision_isSymm_of_all delta omega Gamma V3' heven ?_
  intro q ν q' ν' q'' ν''
  simp only [V3']
  rw [hV3 q ν q' ν' ν'', show -q' - q = -q - q' by abel]

/-- The weighting of a symmetric matrix is symmetric. -/
theorem lbteMatrix_isSymm {κ : Type*} (c : κ → ℝ) {Ω : Matrix κ κ ℝ} (hΩ : Ω.IsSymm) :
    (lbteMatrix c Ω).IsSymm := by
  ext m m'
  simp only [transpose_apply, lbteMatrix]
  rw [mul_comm (c m') (c m), show Ω m' m = Ω m m' from congrFun (congrFun hΩ m) m' ▸ rfl]

end Symmetry

/-! ## The relaxation-time limit -/

/-- Without the in-scattering kernel, that is with `|V₃|²` zero on the triples the matrix reads,
the catalog's linear system is solved exactly by the relaxation-time mean free displacement
`F = v / (2 Γ)`, for nonzero linewidths and positive heat capacities. -/
theorem lbteSolves_rta_limit {Q ι : Type*} [Fintype Q] [AddCommGroup Q] [DecidableEq Q]
    [Fintype ι] [DecidableEq ι] {hbar kB T : ℝ} (delta : ℝ → ℝ) (omega Gamma : Q → ι → ℝ)
    (V3 : Q → ι → Q → ι → Q → ι → ℝ) (c : Q × ι → ℝ) (v F : Q × ι → Fin 3 → ℝ)
    (hV3 : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = 0) (hGamma : ∀ q ν, Gamma q ν ≠ 0)
    (hc : ∀ m, 0 < c m) :
    lbteSolves (lbteMatrix c (chaputCollision hbar kB T delta omega Gamma V3)) c v F ↔
      ∀ m α, F m α = v m α / (2 * Gamma m.1 m.2) := by
  have hdiag : ∀ m m', lbteMatrix c (chaputCollision hbar kB T delta omega Gamma V3) m m' =
      if m = m' then 2 * Gamma m.1 m.2 * c m else 0 := by
    intro m m'
    simp only [lbteMatrix, chaputCollision, hV3, zero_mul, sum_const_zero, mul_zero, add_zero]
    by_cases h : m = m'
    · subst h
      simp only [↓reduceIte]
      rw [sqrt_mul_self (hc m).le]
      ring
    · simp [h]
  have hsum : ∀ m α, ∑ m', lbteMatrix c (chaputCollision hbar kB T delta omega Gamma V3) m m' *
      F m' α = 2 * Gamma m.1 m.2 * c m * F m α := by
    intro m α
    simp only [hdiag, ite_mul, zero_mul, sum_ite_eq, mem_univ, ↓reduceIte]
  unfold lbteSolves
  simp only [hsum]
  constructor
  · intro h m α
    have h2 : 2 * Gamma m.1 m.2 ≠ 0 := mul_ne_zero two_ne_zero (hGamma m.1 m.2)
    rw [eq_div_iff h2]
    apply mul_left_cancel₀ (hc m).ne'
    linear_combination h m α
  · intro h m α
    rw [h m α]
    have hG : Gamma m.1 m.2 ≠ 0 := hGamma m.1 m.2
    field_simp

/-! ## The conductivity -/

section Conductivity

variable {κ : Type*} [Fintype κ]

private theorem lbteKappa_eq_sum {M : Matrix κ κ ℝ} {c : κ → ℝ} {v F : κ → Fin 3 → ℝ}
    (h : lbteSolves M c v F) (V Nq : ℝ) (α β : Fin 3) :
    lbteKappa c v F V Nq α β = (∑ m, ∑ m', F m β * M m m' * F m' α) / (V * Nq) := by
  unfold lbteKappa
  congr 1
  refine sum_congr rfl fun m _ => ?_
  rw [mul_comm (c m * v m α) (F m β), ← h m α, mul_sum]
  refine sum_congr rfl fun m' _ => ?_
  ring

/-- Onsager symmetry: for a symmetric collision matrix the conductivity of any solution of the
catalog's linear system is a symmetric tensor. -/
theorem lbteKappa_isSymm {M : Matrix κ κ ℝ} (hM : M.IsSymm) {c : κ → ℝ} {v F : κ → Fin 3 → ℝ}
    (h : lbteSolves M c v F) (V Nq : ℝ) : (lbteKappa c v F V Nq).IsSymm := by
  ext α β
  simp only [transpose_apply]
  rw [lbteKappa_eq_sum h, lbteKappa_eq_sum h]
  congr 1
  rw [sum_comm]
  refine sum_congr rfl fun m _ => sum_congr rfl fun m' _ => ?_
  rw [show M m' m = M m m' from congrFun (congrFun hM m) m' ▸ rfl]
  ring

private theorem lbteMatrix_eq_conj [DecidableEq κ] (c : κ → ℝ) (hc : ∀ m, 0 ≤ c m) (Ω : Matrix κ κ ℝ) :
    lbteMatrix c Ω = (diagonal fun m => √(c m))ᴴ * Ω * diagonal fun m => √(c m) := by
  ext m m'
  simp only [lbteMatrix, diagonal_conjTranspose, mul_diagonal, diagonal_mul]
  rw [sqrt_mul (hc m)]
  simp only [Pi.star_apply, star_trivial]
  ring

/-- Second-law positivity: if Chaput's collision matrix is positive semidefinite and every mode
heat capacity is nonnegative, the conductivity of any solution of the catalog's linear system is
positive semidefinite for `V N_q > 0`. -/
theorem lbteKappa_posSemidef [DecidableEq κ] {Ω : Matrix κ κ ℝ} (hΩ : Ω.PosSemidef) {c : κ → ℝ}
    (hc : ∀ m, 0 ≤ c m) {v F : κ → Fin 3 → ℝ} (h : lbteSolves (lbteMatrix c Ω) c v F) {V Nq : ℝ}
    (hVN : 0 < V * Nq) : (lbteKappa c v F V Nq).PosSemidef := by
  have hM : (lbteMatrix c Ω).PosSemidef := by
    rw [lbteMatrix_eq_conj c hc]
    exact hΩ.conjTranspose_mul_mul_same _
  have hsolves : Lattice.LBTESolves (lbteMatrix c Ω) c v F := fun α m => by
    rw [← h m α]; exact sum_congr rfl fun m' _ => mul_comm _ _
  have heq : lbteKappa c v F V Nq = Lattice.modeContractedKappa c v F Nq V := by
    ext α β
    simp only [lbteKappa, Lattice.modeContractedKappa]
    rw [mul_comm V Nq]
    congr 1
    exact sum_congr rfl fun m _ => by ring
  rw [heq]
  exact Lattice.lbteKappa_posSemidef _ hM c v F hsolves Nq V (by rwa [mul_comm])

end Conductivity

end OMAI.PhyslibBridge.LinearizedBTE
