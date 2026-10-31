module

public import Mathlib.Analysis.SpecialFunctions.Exp
public import Mathlib.Analysis.SpecialFunctions.Sqrt
public import Mathlib.LinearAlgebra.Matrix.PosDef
public import Mathlib.Tactic
public import OMAIPhyslibKappaContraction
public import OMAIPhononScattering

/-!
# The linearized phonon Boltzmann equation

The catalog solves the linearized BTE `Σ_{q'ν'} M_{qν,q'ν'} F^α_{q'ν'} = c_{qν} v^α_{qν}` with the
symmetric weighting `M = C^(1/2) Ω~ C^(1/2)` of Chaput's collision matrix (Phys. Rev. Lett. 110,
265506 (2013)). Its Kronecker term is the scattering rate `2 Γ` of the canonical linewidth
`Γ = Im Σ = 1/(2 τ)`, and a kernel enters every element, the diagonal included, with the constant
`π / (N_q ħ²)` of `2 Γ`, `|V₃|²` in the labeling `q + q' + q'' = 0`, the weight `2 √(n'' (n'' + 1))`
of the third mode and three energy channels. The conductivity is `κ^{αβ} = Σ c v^α F^β / (V N_q)`. Physlib has
no phonon-transport model, so these results use Mathlib and the local contraction and
phonon-scattering modules only.

The catalog collision matrix is symmetric for an even smearing kernel and a `|V₃|²` symmetric
under exchange of its first two modes on momentum-conserving triples. Without the in-scattering
kernel the solution is the relaxation-time `F = v / (2 Γ)`. For a symmetric collision matrix the
conductivity of any solution is symmetric (Onsager), and if Chaput's matrix is positive
semidefinite and every mode heat capacity is nonnegative, the conductivity is positive
semidefinite.

For an even smearing kernel of the frequency offset the quadratic form of `Ω~` is
`Σ 2 (Γ - Γ^db) x²` plus a sum of squares over
momentum-conserving triples, where the detailed-balance linewidth `Γ^db` weights each process by
`s' s'' / s` with `s = √(n (n + 1))`, so `Ω~` is positive semidefinite whenever `Γ ≥ Γ^db`. With
exact energy conservation the Bose identities `1 + n' + n'' = s' s'' / s` on the decay shell and
`n' - n'' = s' s'' / s` on the absorption shell make the catalog's three-phonon linewidth equal to
`Γ^db`. With the nonnegative isotope and boundary channels, `Ω~` and the conductivity of the
catalog chain are then positive semidefinite with no positivity hypothesis. The exact identity,
not positivity alone, certifies the kernel constant `π / (N_q ħ²)` and the weight
`2 √(n'' (n'' + 1))` relative to `Γ`: a smaller off-diagonal scale would stay positive
semidefinite. With Gaussian smearing `Γ` can fall below `Γ^db`, and issue 221 gives a numerical
`Ω~` with a negative eigenvalue. The tetrahedron method is not a kernel of the offset and is not
covered.
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

/-! ## Detailed balance -/

/-- `√(n (n + 1))` of a mode with frequency `ω`, which is `1 / (2 sinh(ħω / 2 k_B T))` for `ω > 0`
and `0` at `ω = 0`. Twice this root of the third mode weights the kernel of `chaputCollision`,
phono3py's `1 / sinh`. -/
def boseRoot (hbar kB T ω : ℝ) : ℝ :=
  √(bose (hbar * ω / (kB * T)) * (1 + bose (hbar * ω / (kB * T))))

/-- The three energy channels of `chaputCollision` for modes with frequencies `ω`, `ω'` and `ω''`. -/
def channelSum (delta : ℝ → ℝ) (ω ω' ω'' : ℝ) : ℝ :=
  delta (ω' - ω + ω'') + delta (ω' - ω - ω'') + delta (ω' + ω - ω'')

/-- The detailed-balance linewidth `Γ^db = (π / 2 N_q ħ²) Σ_{q'ν'ν''} |V₃|² E s' s'' / s` in the
collision labeling `q + q' + q'' = 0`, with `s = boseRoot` and `E = channelSum`. -/
def detailedBalanceLinewidth {Q ι : Type*} [Fintype Q] [AddCommGroup Q] [Fintype ι]
    (hbar kB T : ℝ) (delta : ℝ → ℝ) (omega : Q → ι → ℝ) (V3 : Q → ι → Q → ι → Q → ι → ℝ)
    (q : Q) (ν : ι) : ℝ :=
  π / (2 * Fintype.card Q * hbar ^ 2) *
    ∑ q', ∑ ν', ∑ ν'', V3 q ν q' ν' (-q - q') ν'' *
      (boseRoot hbar kB T (omega q' ν') * boseRoot hbar kB T (omega (-q - q') ν'') /
        boseRoot hbar kB T (omega q ν)) *
      channelSum delta (omega q ν) (omega q' ν') (omega (-q - q') ν'')

/-- The sum of squares `Σ_{a b ν''} |V₃|² E s_a s_b s_c (x_a / s_a + x_b / s_b + x_c / s_c)²` over
the momentum-conserving triples of modes `a`, `b` and `c = (-q_a - q_b, ν'')`. -/
def collisionSquares {Q ι : Type*} [Fintype Q] [AddCommGroup Q] [Fintype ι]
    (hbar kB T : ℝ) (delta : ℝ → ℝ) (omega : Q → ι → ℝ) (V3 : Q → ι → Q → ι → Q → ι → ℝ)
    (x : Q × ι → ℝ) : ℝ :=
  ∑ a, ∑ b, ∑ ν'', V3 a.1 a.2 b.1 b.2 (-a.1 - b.1) ν'' *
    channelSum delta (omega a.1 a.2) (omega b.1 b.2) (omega (-a.1 - b.1) ν'') *
    (boseRoot hbar kB T (omega a.1 a.2) * boseRoot hbar kB T (omega b.1 b.2) *
      boseRoot hbar kB T (omega (-a.1 - b.1) ν'')) *
    (x a / boseRoot hbar kB T (omega a.1 a.2) + x b / boseRoot hbar kB T (omega b.1 b.2) +
      x (-a.1 - b.1, ν'') / boseRoot hbar kB T (omega (-a.1 - b.1) ν'')) ^ 2

/-! ## Bose-Einstein identities -/

private theorem bose_pos' {x : ℝ} (hx : 0 < x) : 0 < bose x := by
  unfold bose
  have : 1 < exp x := one_lt_exp_iff.mpr hx
  exact one_div_pos.mpr (by linarith)

theorem boseRoot_nonneg (hbar kB T ω : ℝ) : 0 ≤ boseRoot hbar kB T ω := sqrt_nonneg _

theorem boseRoot_pos {hbar kB T ω : ℝ} (hh : 0 < hbar) (hk : 0 < kB) (hT : 0 < T) (hω : 0 < ω) :
    0 < boseRoot hbar kB T ω := by
  have hb := bose_pos' (show 0 < hbar * ω / (kB * T) by positivity)
  exact sqrt_pos.mpr (mul_pos hb (by linarith))

private theorem sqrt_bose {x : ℝ} (hx : 0 < x) :
    √(bose x * (1 + bose x)) = exp (x / 2) / (exp x - 1) := by
  have he : exp (x / 2) ^ 2 = exp x := by rw [sq, ← exp_add, add_halves]
  have h1 : 1 < exp x := one_lt_exp_iff.mpr hx
  rw [show bose x * (1 + bose x) = (exp (x / 2) / (exp x - 1)) ^ 2 by
    rw [div_pow, he]
    unfold bose
    generalize exp x = E at *
    have hne : E - 1 ≠ 0 := by linarith
    field_simp
    ring]
  exact sqrt_sq (div_nonneg (exp_pos _).le (by linarith))

/-- On the decay shell `x = y + z` the root occupations satisfy `s_y s_z / s_x = 1 + n_y + n_z`. -/
private theorem bose_decay {y z : ℝ} (hy : 0 < y) (hz : 0 < z) :
    √(bose y * (1 + bose y)) * √(bose z * (1 + bose z)) / √(bose (y + z) * (1 + bose (y + z))) =
      1 + bose y + bose z := by
  rw [sqrt_bose hy, sqrt_bose hz, sqrt_bose (add_pos hy hz)]
  unfold bose
  simp only [add_div, exp_add]
  have h1 : 1 < exp y := one_lt_exp_iff.mpr hy
  have h2 : 1 < exp z := one_lt_exp_iff.mpr hz
  have h3 : 1 < exp y * exp z := by nlinarith
  have n1 : exp y - 1 ≠ 0 := by linarith
  have n2 : exp z - 1 ≠ 0 := by linarith
  have n3 : exp y * exp z - 1 ≠ 0 := by linarith
  have e1 : exp (y / 2) ≠ 0 := exp_ne_zero _
  have e2 : exp (z / 2) ≠ 0 := exp_ne_zero _
  field_simp
  ring

/-- On the absorption shell `x + y` the root occupations satisfy `s_y s_{x+y} / s_x = n_y - n_{x+y}`. -/
private theorem bose_absorb {x y : ℝ} (hx : 0 < x) (hy : 0 < y) :
    √(bose y * (1 + bose y)) * √(bose (x + y) * (1 + bose (x + y))) / √(bose x * (1 + bose x)) =
      bose y - bose (x + y) := by
  rw [sqrt_bose hy, sqrt_bose (add_pos hx hy), sqrt_bose hx]
  unfold bose
  simp only [add_div, exp_add]
  have hY : exp y = exp (y / 2) * exp (y / 2) := by rw [← exp_add, add_halves]
  have h1 : 1 < exp x := one_lt_exp_iff.mpr hx
  have h2 : 1 < exp y := one_lt_exp_iff.mpr hy
  have e1 : exp (x / 2) ≠ 0 := exp_ne_zero _
  rw [hY] at h2 ⊢
  generalize exp x = X at *
  generalize exp (x / 2) = X2 at *
  generalize exp (y / 2) = Y2 at *
  rw [div_mul_div_comm, show Y2 * (X2 * Y2) = X2 * (Y2 * Y2) by ring]
  generalize Y2 * Y2 = Y at *
  have n1 : X - 1 ≠ 0 := by linarith
  have n2 : Y - 1 ≠ 0 := by linarith
  have n3 : X * Y - 1 ≠ 0 := by nlinarith
  rw [div_div_div_eq, div_sub_div _ _ n2 n3,
    div_eq_div_iff (mul_ne_zero (mul_ne_zero n2 n3) e1) (mul_ne_zero n2 n3)]
  ring

/-- A kernel that vanishes at every nonzero offset is even. -/
private theorem even_of_shell (delta : ℝ → ℝ) (hshell : ∀ x, x ≠ 0 → delta x = 0) :
    ∀ x, delta (-x) = delta x := by
  intro x
  by_cases hx : x = 0
  · rw [hx, neg_zero]
  · rw [hshell x hx, hshell (-x) (neg_ne_zero.mpr hx)]

/-- With exact energy conservation the two partner orderings of one decay or absorption process
weigh the detailed-balance root ratio and the catalog's occupation factors equally. -/
private theorem pair_onShell (delta : ℝ → ℝ) (hshell : ∀ x, x ≠ 0 → delta x = 0)
    {hbar kB T ω ω' ω'' : ℝ} (hh : 0 < hbar) (hk : 0 < kB) (hT : 0 < T) (h0 : 0 < ω)
    (h1 : 0 < ω') (h2 : 0 < ω'') :
    boseRoot hbar kB T ω' * boseRoot hbar kB T ω'' / boseRoot hbar kB T ω *
        (channelSum delta ω ω' ω'' + channelSum delta ω ω'' ω') =
      ((1 + bose (hbar * ω' / (kB * T)) + bose (hbar * ω'' / (kB * T))) * delta (ω - ω' - ω'') +
          2 * (bose (hbar * ω' / (kB * T)) - bose (hbar * ω'' / (kB * T))) *
            delta (ω + ω' - ω'')) +
        ((1 + bose (hbar * ω'' / (kB * T)) + bose (hbar * ω' / (kB * T))) *
            delta (ω - ω'' - ω') +
          2 * (bose (hbar * ω'' / (kB * T)) - bose (hbar * ω' / (kB * T))) *
            delta (ω + ω'' - ω')) := by
  have heven := even_of_shell delta hshell
  have hlin : ∀ u v : ℝ, hbar * (u + v) / (kB * T) = hbar * u / (kB * T) + hbar * v / (kB * T) :=
    fun u v => by ring
  have pu : ∀ {u : ℝ}, 0 < u → 0 < hbar * u / (kB * T) := fun hu => by positivity
  set r := boseRoot hbar kB T ω' * boseRoot hbar kB T ω'' / boseRoot hbar kB T ω with hr
  have key0 : ω - ω' - ω'' = 0 →
      r = 1 + bose (hbar * ω' / (kB * T)) + bose (hbar * ω'' / (kB * T)) := by
    intro hA
    rw [hr, show ω = ω' + ω'' by linarith]
    unfold boseRoot
    rw [hlin]
    exact bose_decay (pu h1) (pu h2)
  have key1 : ω + ω' - ω'' = 0 →
      r = bose (hbar * ω' / (kB * T)) - bose (hbar * ω'' / (kB * T)) := by
    intro hA
    rw [hr, show ω'' = ω + ω' by linarith]
    unfold boseRoot
    rw [hlin]
    exact bose_absorb (pu h0) (pu h1)
  have key2 : ω + ω'' - ω' = 0 →
      r = bose (hbar * ω'' / (kB * T)) - bose (hbar * ω' / (kB * T)) := by
    intro hA
    rw [hr, mul_comm, show ω' = ω + ω'' by linarith]
    unfold boseRoot
    rw [hlin]
    exact bose_absorb (pu h0) (pu h2)
  have e0 : r * delta (ω - ω' - ω'') =
      (1 + bose (hbar * ω' / (kB * T)) + bose (hbar * ω'' / (kB * T))) * delta (ω - ω' - ω'') := by
    by_cases hA : ω - ω' - ω'' = 0
    · rw [key0 hA]
    · rw [hshell _ hA, mul_zero, mul_zero]
  have e1 : r * delta (ω + ω' - ω'') =
      (bose (hbar * ω' / (kB * T)) - bose (hbar * ω'' / (kB * T))) * delta (ω + ω' - ω'') := by
    by_cases hA : ω + ω' - ω'' = 0
    · rw [key1 hA]
    · rw [hshell _ hA, mul_zero, mul_zero]
  have e2 : r * delta (ω + ω'' - ω') =
      (bose (hbar * ω'' / (kB * T)) - bose (hbar * ω' / (kB * T))) * delta (ω + ω'' - ω') := by
    by_cases hA : ω + ω'' - ω' = 0
    · rw [key2 hA]
    · rw [hshell _ hA, mul_zero, mul_zero]
  unfold channelSum
  rw [show ω' - ω + ω'' = -(ω - ω' - ω'') by ring, show ω' - ω - ω'' = -(ω + ω'' - ω') by ring,
    show ω' + ω - ω'' = ω + ω' - ω'' by ring, show ω'' - ω + ω' = -(ω - ω' - ω'') by ring,
    show ω'' - ω - ω' = -(ω + ω' - ω'') by ring, show ω'' + ω - ω' = ω + ω'' - ω' by ring,
    show ω - ω'' - ω' = ω - ω' - ω'' by ring, heven, heven, heven]
  linear_combination 2 * e0 + 2 * e1 + 2 * e2

/-! ## Reindexing momentum-conserving triples -/

section Triples

variable {Q ι : Type*} [Fintype Q] [AddCommGroup Q] [Fintype ι]

private theorem tripleSum_swap12 (F : Q × ι → Q × ι → Q × ι → ℝ) :
    ∑ a, ∑ b, ∑ ν, F a b (-a.1 - b.1, ν) = ∑ a, ∑ b, ∑ ν, F b a (-a.1 - b.1, ν) := by
  rw [sum_comm]
  refine sum_congr rfl fun a _ => sum_congr rfl fun b _ => sum_congr rfl fun ν _ => ?_
  rw [show -b.1 - a.1 = -a.1 - b.1 by abel]

private theorem tripleSum_swap23 (F : Q × ι → Q × ι → Q × ι → ℝ) :
    ∑ a, ∑ b, ∑ ν, F a b (-a.1 - b.1, ν) = ∑ a, ∑ b, ∑ ν, F a (-a.1 - b.1, ν) b := by
  refine sum_congr rfl fun a _ => ?_
  have hφ : Function.Involutive fun p : (Q × ι) × ι => ((-a.1 - p.1.1, p.2), p.1.2) := by
    rintro ⟨⟨q, μ⟩, ν⟩
    simp only [Prod.mk.injEq, and_true]
    abel
  rw [← Fintype.sum_prod_type', ← Fintype.sum_prod_type']
  exact Fintype.sum_equiv hφ.toPerm _ _ fun p => by
    simp only [Function.Involutive.coe_toPerm]
    rw [show -a.1 - (-a.1 - p.1.1) = p.1.1 by abel]

/-- The sum of squares over momentum-conserving triples equals three diagonal sums plus six
cross sums, by the permutation symmetry of the triple weight `w`. -/
private theorem sos_identity (w : Q × ι → Q × ι → Q × ι → ℝ) (s x : Q × ι → ℝ)
    (hw12 : ∀ a b ν, w a b (-a.1 - b.1, ν) = w b a (-a.1 - b.1, ν))
    (hw23 : ∀ a b ν, w a b (-a.1 - b.1, ν) = w a (-a.1 - b.1, ν) b)
    (hs : ∀ a b ν, w a b (-a.1 - b.1, ν) ≠ 0 → s a ≠ 0 ∧ s b ≠ 0 ∧ s (-a.1 - b.1, ν) ≠ 0) :
    ∑ a, ∑ b, ∑ ν, w a b (-a.1 - b.1, ν) * (s a * s b * s (-a.1 - b.1, ν)) *
        (x a / s a + x b / s b + x (-a.1 - b.1, ν) / s (-a.1 - b.1, ν)) ^ 2 =
      3 * ∑ a, ∑ b, ∑ ν, w a b (-a.1 - b.1, ν) * (s b * s (-a.1 - b.1, ν) / s a) * x a ^ 2 +
        6 * ∑ a, ∑ b, ∑ ν, w a b (-a.1 - b.1, ν) * s (-a.1 - b.1, ν) * x a * x b := by
  have hterm : ∀ a b ν, w a b (-a.1 - b.1, ν) * (s a * s b * s (-a.1 - b.1, ν)) *
      (x a / s a + x b / s b + x (-a.1 - b.1, ν) / s (-a.1 - b.1, ν)) ^ 2 =
      w a b (-a.1 - b.1, ν) * (s b * s (-a.1 - b.1, ν) / s a) * x a ^ 2 +
      w a b (-a.1 - b.1, ν) * (s a * s (-a.1 - b.1, ν) / s b) * x b ^ 2 +
      w a b (-a.1 - b.1, ν) * (s a * s b / s (-a.1 - b.1, ν)) * x (-a.1 - b.1, ν) ^ 2 +
      2 * (w a b (-a.1 - b.1, ν) * s (-a.1 - b.1, ν) * x a * x b) +
      2 * (w a b (-a.1 - b.1, ν) * s b * x a * x (-a.1 - b.1, ν)) +
      2 * (w a b (-a.1 - b.1, ν) * s a * x b * x (-a.1 - b.1, ν)) := by
    intro a b ν
    by_cases hw : w a b (-a.1 - b.1, ν) = 0
    · simp [hw]
    · obtain ⟨h1, h2, h3⟩ := hs a b ν hw
      field_simp
      ring
  have hG2 := tripleSum_swap12 fun a b c => w a b c * (s a * s c / s b) * x b ^ 2
  have hG3 := tripleSum_swap23 fun a b c => w a b c * (s a * s b / s c) * x c ^ 2
  have hH2 := tripleSum_swap23 fun a b c => w a b c * s b * x a * x c
  have hH3 := tripleSum_swap12 fun a b c => w a b c * s a * x b * x c
  have eG2 : ∑ a, ∑ b, ∑ ν, w a b (-a.1 - b.1, ν) * (s a * s (-a.1 - b.1, ν) / s b) * x b ^ 2 =
      ∑ a, ∑ b, ∑ ν, w a b (-a.1 - b.1, ν) * (s b * s (-a.1 - b.1, ν) / s a) * x a ^ 2 := by
    rw [hG2]
    exact sum_congr rfl fun a _ => sum_congr rfl fun b _ => sum_congr rfl fun ν _ => by
      rw [← hw12 a b ν]
  have eG3 : ∑ a, ∑ b, ∑ ν, w a b (-a.1 - b.1, ν) * (s a * s b / s (-a.1 - b.1, ν)) *
      x (-a.1 - b.1, ν) ^ 2 =
      ∑ a, ∑ b, ∑ ν, w a b (-a.1 - b.1, ν) * (s a * s (-a.1 - b.1, ν) / s b) * x b ^ 2 := by
    rw [hG3]
    exact sum_congr rfl fun a _ => sum_congr rfl fun b _ => sum_congr rfl fun ν _ => by
      rw [← hw23 a b ν]
  have eH2 : ∑ a, ∑ b, ∑ ν, w a b (-a.1 - b.1, ν) * s b * x a * x (-a.1 - b.1, ν) =
      ∑ a, ∑ b, ∑ ν, w a b (-a.1 - b.1, ν) * s (-a.1 - b.1, ν) * x a * x b := by
    rw [hH2]
    exact sum_congr rfl fun a _ => sum_congr rfl fun b _ => sum_congr rfl fun ν _ => by
      rw [← hw23 a b ν]
  have eH3 : ∑ a, ∑ b, ∑ ν, w a b (-a.1 - b.1, ν) * s a * x b * x (-a.1 - b.1, ν) =
      ∑ a, ∑ b, ∑ ν, w a b (-a.1 - b.1, ν) * s b * x a * x (-a.1 - b.1, ν) := by
    rw [hH3]
    exact sum_congr rfl fun a _ => sum_congr rfl fun b _ => sum_congr rfl fun ν _ => by
      rw [← hw12 a b ν]
  simp only [hterm, sum_add_distrib, ← mul_sum]
  rw [eH3, eH2, eG3, eG2]
  ring

end Triples


/-! ## Energy channels -/

theorem channelSum_nonneg {delta : ℝ → ℝ} (hdelta : ∀ x, 0 ≤ delta x) (ω ω' ω'' : ℝ) :
    0 ≤ channelSum delta ω ω' ω'' :=
  add_nonneg (add_nonneg (hdelta _) (hdelta _)) (hdelta _)

theorem channelSum_swap12 (delta : ℝ → ℝ) (heven : ∀ x, delta (-x) = delta x) (ω ω' ω'' : ℝ) :
    channelSum delta ω ω' ω'' = channelSum delta ω' ω ω'' := by
  unfold channelSum
  rw [show ω - ω' + ω'' = -(ω' - ω - ω'') by ring, show ω - ω' - ω'' = -(ω' - ω + ω'') by ring,
    heven, heven, add_comm ω ω']
  ring

theorem channelSum_swap23 (delta : ℝ → ℝ) (heven : ∀ x, delta (-x) = delta x) (ω ω' ω'' : ℝ) :
    channelSum delta ω ω' ω'' = channelSum delta ω ω'' ω' := by
  unfold channelSum
  rw [show ω'' - ω + ω' = ω' - ω + ω'' by ring, show ω'' - ω - ω' = -(ω' + ω - ω'') by ring,
    show ω'' + ω - ω' = -(ω' - ω - ω'') by ring, heven, heven]
  ring

/-! ## Positivity of the collision matrix -/

section Positivity

variable {Q ι : Type*} [Fintype Q] [AddCommGroup Q] [DecidableEq Q] [Fintype ι] [DecidableEq ι]

/-- For an even smearing kernel, the quadratic form of the catalog's collision matrix is the
detailed-balance excess of the linewidths plus a sum of squares over momentum-conserving triples.
The hypotheses: an even kernel, a `|V₃|²` symmetric under every permutation of its three modes on
the triples `(q, q', -q - q')` the matrix reads, and positive frequencies on all three modes of
every triple it couples. A zero-frequency mode, such as an acoustic mode at `Γ`, decouples, as in
kALDo's `physical_mode` mask and in phono3py, which computes `|V₃|²` only when all three
frequencies exceed `cutoff_frequency`. -/
theorem chaputCollision_quadratic {hbar kB T : ℝ} (hh : 0 < hbar) (hk : 0 < kB) (hT : 0 < T)
    (delta : ℝ → ℝ) (heven : ∀ x, delta (-x) = delta x) (omega Gamma : Q → ι → ℝ)
    (V3 : Q → ι → Q → ι → Q → ι → ℝ)
    (h12 : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = V3 q' ν' q ν (-q - q') ν'')
    (h23 : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = V3 q ν (-q - q') ν'' q' ν')
    (hzero : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' ≠ 0 →
      0 < omega q ν ∧ 0 < omega q' ν' ∧ 0 < omega (-q - q') ν'')
    (x : Q × ι → ℝ) :
    ∑ a, ∑ b, x a * chaputCollision hbar kB T delta omega Gamma V3 a b * x b =
      ∑ a, 2 * (Gamma a.1 a.2 - detailedBalanceLinewidth hbar kB T delta omega V3 a.1 a.2) *
          x a ^ 2 +
        π / (3 * Fintype.card Q * hbar ^ 2) * collisionSquares hbar kB T delta omega V3 x := by
  let s : Q × ι → ℝ := fun m => boseRoot hbar kB T (omega m.1 m.2)
  let w : Q × ι → Q × ι → Q × ι → ℝ := fun a b c =>
    V3 a.1 a.2 b.1 b.2 c.1 c.2 * channelSum delta (omega a.1 a.2) (omega b.1 b.2) (omega c.1 c.2)
  have hw12 : ∀ a b ν, w a b (-a.1 - b.1, ν) = w b a (-a.1 - b.1, ν) := by
    intro a b ν
    simp only [w]
    rw [h12, channelSum_swap12 delta heven]
  have hw23 : ∀ a b ν, w a b (-a.1 - b.1, ν) = w a (-a.1 - b.1, ν) b := by
    intro a b ν
    simp only [w]
    rw [h23, channelSum_swap23 delta heven]
  have hs : ∀ a b ν, w a b (-a.1 - b.1, ν) ≠ 0 → s a ≠ 0 ∧ s b ≠ 0 ∧ s (-a.1 - b.1, ν) ≠ 0 := by
    intro a b ν hw
    have hV : V3 a.1 a.2 b.1 b.2 (-a.1 - b.1) ν ≠ 0 := fun h => hw (by simp only [w, h, zero_mul])
    obtain ⟨p1, p2, p3⟩ := hzero a.1 a.2 b.1 b.2 ν hV
    exact ⟨(boseRoot_pos hh hk hT p1).ne', (boseRoot_pos hh hk hT p2).ne',
      (boseRoot_pos hh hk hT p3).ne'⟩
  have hcs : collisionSquares hbar kB T delta omega V3 x =
      3 * ∑ a, ∑ b, ∑ ν, w a b (-a.1 - b.1, ν) * (s b * s (-a.1 - b.1, ν) / s a) * x a ^ 2 +
        6 * ∑ a, ∑ b, ∑ ν, w a b (-a.1 - b.1, ν) * s (-a.1 - b.1, ν) * x a * x b :=
    sos_identity w s x hw12 hw23 hs
  have hentry : ∀ a b, x a * chaputCollision hbar kB T delta omega Gamma V3 a b * x b =
      (if a = b then 2 * Gamma a.1 a.2 * x a ^ 2 else 0) + 2 * (π / (Fintype.card Q * hbar ^ 2)) *
        ∑ ν, w a b (-a.1 - b.1, ν) * s (-a.1 - b.1, ν) * x a * x b := by
    intro a b
    have hab : chaputCollision hbar kB T delta omega Gamma V3 a b =
        2 * Gamma a.1 a.2 * (if a = b then 1 else 0) + π / (Fintype.card Q * hbar ^ 2) *
          ∑ ν'', V3 a.1 a.2 b.1 b.2 (-a.1 - b.1) ν'' * (2 * s (-a.1 - b.1, ν'')) *
            channelSum delta (omega a.1 a.2) (omega b.1 b.2) (omega (-a.1 - b.1) ν'') := rfl
    rw [hab, mul_add, add_mul]
    congr 1
    · split_ifs with h
      · subst h; ring
      · ring
    · rw [mul_sum, mul_sum, mul_sum, sum_mul]
      refine sum_congr rfl fun ν _ => ?_
      simp only [w]
      ring
  have hL : ∑ a, ∑ b, x a * chaputCollision hbar kB T delta omega Gamma V3 a b * x b =
      ∑ a, 2 * Gamma a.1 a.2 * x a ^ 2 + 2 * (π / (Fintype.card Q * hbar ^ 2)) *
        ∑ a, ∑ b, ∑ ν, w a b (-a.1 - b.1, ν) * s (-a.1 - b.1, ν) * x a * x b := by
    simp only [hentry, sum_add_distrib, sum_ite_eq, mem_univ, ↓reduceIte, ← mul_sum]
  have hD : ∑ a, 2 * detailedBalanceLinewidth hbar kB T delta omega V3 a.1 a.2 * x a ^ 2 =
      π / (Fintype.card Q * hbar ^ 2) *
        ∑ a, ∑ b, ∑ ν, w a b (-a.1 - b.1, ν) * (s b * s (-a.1 - b.1, ν) / s a) * x a ^ 2 := by
    rw [mul_sum]
    refine sum_congr rfl fun a _ => ?_
    rw [Fintype.sum_prod_type]
    simp only [detailedBalanceLinewidth, mul_sum, sum_mul, w, s]
    refine sum_congr rfl fun q' _ => sum_congr rfl fun ν' _ => sum_congr rfl fun ν _ => ?_
    ring
  have hsplit : ∑ a, 2 * (Gamma a.1 a.2 - detailedBalanceLinewidth hbar kB T delta omega V3 a.1 a.2) *
      x a ^ 2 = ∑ a, 2 * Gamma a.1 a.2 * x a ^ 2 -
        ∑ a, 2 * detailedBalanceLinewidth hbar kB T delta omega V3 a.1 a.2 * x a ^ 2 := by
    rw [← sum_sub_distrib]
    exact sum_congr rfl fun a _ => by ring
  rw [hL, hsplit, hD, hcs]
  ring

/-- The catalog's collision matrix is positive semidefinite for any nonnegative even smearing
kernel when every linewidth is at least the detailed-balance linewidth, under the hypotheses of
`chaputCollision_quadratic` and a nonnegative `|V₃|²`. -/
theorem chaputCollision_posSemidef {hbar kB T : ℝ} (hh : 0 < hbar) (hk : 0 < kB) (hT : 0 < T)
    (delta : ℝ → ℝ) (hdelta : ∀ x, 0 ≤ delta x) (heven : ∀ x, delta (-x) = delta x)
    (omega Gamma : Q → ι → ℝ) (V3 : Q → ι → Q → ι → Q → ι → ℝ)
    (hV3 : ∀ q ν q' ν' ν'', 0 ≤ V3 q ν q' ν' (-q - q') ν'')
    (h12 : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = V3 q' ν' q ν (-q - q') ν'')
    (h23 : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = V3 q ν (-q - q') ν'' q' ν')
    (hzero : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' ≠ 0 →
      0 < omega q ν ∧ 0 < omega q' ν' ∧ 0 < omega (-q - q') ν'')
    (hGamma : ∀ q ν, detailedBalanceLinewidth hbar kB T delta omega V3 q ν ≤ Gamma q ν) :
    (chaputCollision hbar kB T delta omega Gamma V3).PosSemidef := by
  refine PosSemidef.of_dotProduct_mulVec_nonneg
    (isHermitian_iff_isSymm.mpr (chaputCollision_isSymm delta omega Gamma V3 heven h12)) fun x => ?_
  have hq : star x ⬝ᵥ (chaputCollision hbar kB T delta omega Gamma V3 *ᵥ x) =
      ∑ a, ∑ b, x a * chaputCollision hbar kB T delta omega Gamma V3 a b * x b := by
    simp only [dotProduct, mulVec, Pi.star_apply, star_trivial, mul_sum, mul_assoc]
  rw [hq, chaputCollision_quadratic hh hk hT delta heven omega Gamma V3 h12 h23 hzero x]
  apply add_nonneg
  · exact sum_nonneg fun a _ =>
      mul_nonneg (mul_nonneg two_pos.le (sub_nonneg.mpr (hGamma _ _))) (sq_nonneg _)
  · apply mul_nonneg (div_nonneg pi_pos.le (by positivity))
    unfold collisionSquares
    exact sum_nonneg fun a _ => sum_nonneg fun b _ => sum_nonneg fun ν _ =>
      mul_nonneg (mul_nonneg (mul_nonneg (hV3 _ _ _ _ _) (channelSum_nonneg hdelta _ _ _))
        (mul_nonneg (mul_nonneg (boseRoot_nonneg _ _ _ _) (boseRoot_nonneg _ _ _ _))
          (boseRoot_nonneg _ _ _ _))) (sq_nonneg _)

end Positivity

/-! ## Exact energy conservation -/

section OnShell

variable {Q ι : Type*} [Fintype Q] [AddCommGroup Q] [Fintype ι]

private theorem sum_partner_swap (q : Q) (f : Q → ι → ι → ℝ) :
    ∑ q', ∑ ν', ∑ ν'', f q' ν' ν'' = ∑ q', ∑ ν', ∑ ν'', f (q - q') ν'' ν' := by
  rw [← Fintype.sum_equiv (Equiv.subLeft q) (fun q' => ∑ ν', ∑ ν'', f (q - q') ν' ν'')
    (fun q' => ∑ ν', ∑ ν'', f q' ν' ν'') (fun _ => rfl)]
  exact sum_congr rfl fun q' _ => sum_comm

private theorem sum_eq_of_pair (q : Q) (C D : Q → ι → ι → ℝ)
    (h : ∀ q' ν' ν'', C q' ν' ν'' + C (q - q') ν'' ν' = D q' ν' ν'' + D (q - q') ν'' ν') :
    ∑ q', ∑ ν', ∑ ν'', C q' ν' ν'' = ∑ q', ∑ ν', ∑ ν'', D q' ν' ν'' := by
  have hC := sum_partner_swap q C
  have hD := sum_partner_swap q D
  have hsum : (∑ q', ∑ ν', ∑ ν'', C q' ν' ν'') + ∑ q', ∑ ν', ∑ ν'', C (q - q') ν'' ν' =
      (∑ q', ∑ ν', ∑ ν'', D q' ν' ν'') + ∑ q', ∑ ν', ∑ ν'', D (q - q') ν'' ν' := by
    simp only [← sum_add_distrib]
    exact sum_congr rfl fun q' _ => sum_congr rfl fun ν' _ => sum_congr rfl fun ν'' _ =>
      h q' ν' ν''
  linarith

/-- With exact energy conservation the catalog's three-phonon linewidth equals the
detailed-balance linewidth, so it is exactly the diagonal that makes `Ω~` a sum of squares. The
collision-labeled kernel is the catalog's decay-labeled one at `(q, -q', q + q')`, the frequencies
are even in `q`, and the decay-labeled kernel is symmetric in its two partners. -/
theorem anharmonicLinewidth_eq_detailedBalance {hbar kB T : ℝ} (hh : 0 < hbar) (hk : 0 < kB)
    (hT : 0 < T) (delta : ℝ → ℝ) (hshell : ∀ x, x ≠ 0 → delta x = 0) (omega : Q → ι → ℝ)
    (homega : ∀ q ν, omega (-q) ν = omega q ν) (V3 Vd : Q → ι → Q → ι → Q → ι → ℝ)
    (hrel : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = Vd q ν (-q') ν' (q + q') ν'')
    (q : Q) (ν : ι) (hω : 0 < omega q ν)
    (hzero : ∀ q' ν' ν'', Vd q ν q' ν' (q - q') ν'' ≠ 0 →
      0 < omega q' ν' ∧ 0 < omega (q - q') ν'')
    (hswap : ∀ q' ν' ν'', Vd q ν q' ν' (q - q') ν'' = Vd q ν (q - q') ν'' q' ν') :
    PhononScattering.anharmonicLinewidth hbar kB T delta omega Vd q ν =
      detailedBalanceLinewidth hbar kB T delta omega V3 q ν := by
  have hb : ∀ x, PhononScattering.bose x = bose x := fun _ => rfl
  have hneg2 : ∀ a b : Q, -a - -b = -(a - b) := fun a b => by abel
  unfold PhononScattering.anharmonicLinewidth detailedBalanceLinewidth
  simp only [hb]
  congr 1
  conv_rhs => rw [← Equiv.sum_comp (Equiv.neg Q)]
  simp only [Equiv.neg_apply]
  refine sum_eq_of_pair q _ _ fun q' ν' ν'' => ?_
  simp only [hrel]
  simp only [neg_neg, ← sub_eq_add_neg, sub_sub_cancel, hneg2, homega]
  rw [← hswap q' ν' ν'']
  by_cases hV : Vd q ν q' ν' (q - q') ν'' = 0
  · simp [hV]
  · obtain ⟨h1, h2⟩ := hzero q' ν' ν'' hV
    have hp := pair_onShell delta hshell hh hk hT hω h1 h2
    linear_combination (-Vd q ν q' ν' (q - q') ν'') * hp

end OnShell


/-! ## The catalog chain on shell -/

section Catalog

variable {Q ι : Type*} [Fintype Q] [AddCommGroup Q] [DecidableEq Q] [Fintype ι] [DecidableEq ι]

/-- With exact energy conservation the catalog's collision matrix is positive semidefinite for
any linewidths at least the catalog's three-phonon linewidth, with no positivity hypothesis on
`Ω~`. The collision-labeled `|V₃|²` is nonnegative and permutation symmetric on
momentum-conserving triples, vanishes unless all three frequencies are positive, and is the
decay-labeled kernel at `(q, -q', q + q')`, and the frequencies are even in `q`. -/
theorem chaputCollision_posSemidef_onShell {hbar kB T : ℝ} (hh : 0 < hbar) (hk : 0 < kB)
    (hT : 0 < T) (delta : ℝ → ℝ) (hdelta : ∀ x, 0 ≤ delta x) (hshell : ∀ x, x ≠ 0 → delta x = 0)
    (omega Gamma : Q → ι → ℝ) (homega : ∀ q ν, omega (-q) ν = omega q ν)
    (V3 Vd : Q → ι → Q → ι → Q → ι → ℝ) (hV3 : ∀ q ν q' ν' ν'', 0 ≤ V3 q ν q' ν' (-q - q') ν'')
    (h12 : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = V3 q' ν' q ν (-q - q') ν'')
    (h23 : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = V3 q ν (-q - q') ν'' q' ν')
    (hzero : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' ≠ 0 →
      0 < omega q ν ∧ 0 < omega q' ν' ∧ 0 < omega (-q - q') ν'')
    (hrel : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = Vd q ν (-q') ν' (q + q') ν'')
    (hGamma : ∀ q ν,
      PhononScattering.anharmonicLinewidth hbar kB T delta omega Vd q ν ≤ Gamma q ν) :
    (chaputCollision hbar kB T delta omega Gamma V3).PosSemidef := by
  have heven := even_of_shell delta hshell
  have hVd : ∀ q ν q' ν' ν'', Vd q ν q' ν' (q - q') ν'' = V3 q ν (-q') ν' (-q - -q') ν'' := by
    intro q ν q' ν' ν''
    rw [hrel, neg_neg, ← sub_eq_add_neg]
  refine chaputCollision_posSemidef hh hk hT delta hdelta heven omega Gamma V3 hV3 h12 h23 hzero
    fun q ν => le_trans (le_of_eq ?_) (hGamma q ν)
  by_cases hω : 0 < omega q ν
  · refine (anharmonicLinewidth_eq_detailedBalance hh hk hT delta hshell omega homega V3 Vd hrel q ν
      hω (fun q' ν' ν'' hne => ?_) (fun q' ν' ν'' => ?_)).symm
    · rw [hVd] at hne
      obtain ⟨-, p2, p3⟩ := hzero q ν (-q') ν' ν'' hne
      rw [homega] at p2
      rw [show -q - -q' = -(q - q') by abel, homega] at p3
      exact ⟨p2, p3⟩
    · calc Vd q ν q' ν' (q - q') ν'' = V3 q ν (-q') ν' (-q - -q') ν'' := hVd q ν q' ν' ν''
        _ = V3 q ν (-q - -q') ν'' (-q') ν' := h23 q ν (-q') ν' ν''
        _ = V3 q ν (-(q - q')) ν'' (-q - -(q - q')) ν' := by
          rw [show -q - -q' = -(q - q') by abel, show -q - -(q - q') = -q' by abel]
        _ = Vd q ν (q - q') ν'' q' ν' := by
          rw [hrel, neg_neg, show q + -(q - q') = q' by abel]
  · have hV0 : ∀ q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = 0 := fun q' ν' ν'' => by
      by_contra hne
      exact hω (hzero q ν q' ν' ν'' hne).1
    unfold detailedBalanceLinewidth PhononScattering.anharmonicLinewidth
    simp only [hVd, hV0, zero_mul, sum_const_zero, mul_zero]

/-- Second-law positivity of the catalog chain with exact energy conservation: the linewidth is
the Matthiessen sum of the catalog's three-phonon, isotope and boundary linewidths, and the
conductivity of any solution of the direct linearized BTE is positive semidefinite, with no
positivity hypothesis on `Ω~`. -/
theorem lbteKappa_posSemidef_onShell {B : Type*} [Fintype B] {hbar kB T : ℝ} (hh : 0 < hbar)
    (hk : 0 < kB) (hT : 0 < T) (delta : ℝ → ℝ) (hdelta : ∀ x, 0 ≤ delta x)
    (hshell : ∀ x, x ≠ 0 → delta x = 0) (omega : Q → ι → ℝ)
    (homega : ∀ q ν, omega (-q) ν = omega q ν) (V3 Vd : Q → ι → Q → ι → Q → ι → ℝ)
    (hV3 : ∀ q ν q' ν' ν'', 0 ≤ V3 q ν q' ν' (-q - q') ν'')
    (h12 : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = V3 q' ν' q ν (-q - q') ν'')
    (h23 : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = V3 q ν (-q - q') ν'' q' ν')
    (hzero : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' ≠ 0 →
      0 < omega q ν ∧ 0 < omega q' ν' ∧ 0 < omega (-q - q') ν'')
    (hrel : ∀ q ν q' ν' ν'', V3 q ν q' ν' (-q - q') ν'' = Vd q ν (-q') ν' (q + q') ν'')
    (deltaIso : ℝ → ℝ) (hdeltaIso : ∀ x, 0 ≤ deltaIso x) (g : B → ℝ) (hg : ∀ b, 0 ≤ g b)
    (e : Q → ι → B → Fin 3 → ℂ) {L : ℝ} (hL : 0 ≤ L) {c : Q × ι → ℝ} (hc : ∀ m, 0 ≤ c m)
    {v F : Q × ι → Fin 3 → ℝ}
    (h : lbteSolves (lbteMatrix c (chaputCollision hbar kB T delta omega
      (fun q ν => PhononScattering.totalLinewidth
        (PhononScattering.anharmonicLinewidth hbar kB T delta omega Vd q ν)
        (PhononScattering.isotopeLinewidth deltaIso omega g e q ν)
        (PhononScattering.boundaryLinewidth (v (q, ν)) L)) V3)) c v F)
    {V Nq : ℝ} (hVN : 0 < V * Nq) : (lbteKappa c v F V Nq).PosSemidef := by
  refine lbteKappa_posSemidef (chaputCollision_posSemidef_onShell hh hk hT delta hdelta hshell omega
    _ homega V3 Vd hV3 h12 h23 hzero hrel fun q ν => ?_) hc h hVN
  have hiso := PhononScattering.isotopeLinewidth_nonneg deltaIso omega g e q ν hdeltaIso hg
  have hbnd : 0 ≤ PhononScattering.boundaryLinewidth (v (q, ν)) L :=
    div_nonneg (sqrt_nonneg _) (by linarith)
  unfold PhononScattering.totalLinewidth
  linarith

end Catalog
end OMAI.PhyslibBridge.LinearizedBTE
