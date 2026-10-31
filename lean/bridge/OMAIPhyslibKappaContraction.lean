/- The catalog's per-mode thermal-conductivity contractions, over Mathlib only. The
linearized-BTE conductivity is symmetric and positive semidefinite when the collision matrix is.
OMAILinearizedBTE applies this to the catalog's weighted Chaput collision matrix, with the positive
semidefiniteness of Chaput's matrix as a hypothesis.
The cumulative distribution is monotone in the cutoff when every modal contribution is
nonnegative, as in the relaxation-time approximation. A three-mode linearized BTE with one
three-phonon process, Casimir boundary scattering and Bose-Einstein weights has a negative modal
contribution, so its cumulative distribution is not monotone in either the frequency or the
mean-free-path binning. -/
module

public import Mathlib.LinearAlgebra.Matrix.PosDef
public import Mathlib.Tactic

@[expose] public section

noncomputable section

namespace OMAI.PhyslibBridge.Lattice

open Matrix

/-- The catalog relaxation-time mean free displacement `F_α = v_α / (2 Γ)`. -/
def rtaMeanFreeDisplacement (v : Fin 3 → ℝ) (Γ : ℝ) : Fin 3 → ℝ :=
  fun β => v β / (2 * Γ)

/-- The catalog per-mode contraction
`κ_{αβ} = (∑_m F_{β,m} c_m v_{α,m}) / (N_q V_cell)`. -/
def modeContractedKappa {ι : Type*} [Fintype ι] (c : ι → ℝ) (v F : ι → Fin 3 → ℝ)
    (Nq V : ℝ) : Matrix (Fin 3) (Fin 3) ℝ :=
  fun α β => (∑ m, F m β * c m * v m α) / (Nq * V)

/-- The catalog linearized BTE `∑_{m'} F_{α,m'} M_{m,m'} = c_m v_{α,m}`. -/
def LBTESolves {ι : Type*} [Fintype ι] (Mcol : Matrix ι ι ℝ) (c : ι → ℝ)
    (v F : ι → Fin 3 → ℝ) : Prop :=
  ∀ α m, ∑ m', F m' α * Mcol m m' = c m * v m α

/-- With the linearized BTE, `κ_{αβ} N_q V = ∑_{m,m'} F_{β,m} M_{m,m'} F_{α,m'}`. -/
theorem lbteKappa_eq {ι : Type*} [Fintype ι] (Mcol : Matrix ι ι ℝ) (c : ι → ℝ)
    (v F : ι → Fin 3 → ℝ) (h : LBTESolves Mcol c v F) (Nq V : ℝ) (α β : Fin 3) :
    modeContractedKappa c v F Nq V α β =
      (∑ m, ∑ m', F m β * Mcol m m' * F m' α) / (Nq * V) := by
  unfold modeContractedKappa
  congr 1
  refine Finset.sum_congr rfl fun m _ => ?_
  rw [mul_assoc, ← h α m, Finset.mul_sum]
  refine Finset.sum_congr rfl fun m' _ => ?_
  ring

/-- Onsager symmetry and second-law positivity: if the collision matrix is symmetric positive
semidefinite and `N_q V > 0`, the linearized-BTE conductivity is symmetric and positive
semidefinite. No sign of `c` or of the individual modal contributions is needed. -/
theorem lbteKappa_posSemidef {ι : Type*} [Fintype ι] (Mcol : Matrix ι ι ℝ)
    (hM : Mcol.PosSemidef) (c : ι → ℝ) (v F : ι → Fin 3 → ℝ) (h : LBTESolves Mcol c v F)
    (Nq V : ℝ) (hNV : 0 < Nq * V) :
    (modeContractedKappa c v F Nq V).PosSemidef := by
  obtain ⟨hMh, hMq⟩ := posSemidef_iff_dotProduct_mulVec.1 hM
  have hMs : ∀ m m', Mcol m m' = Mcol m' m := fun m m' => by
    have := congrFun (congrFun hMh m') m
    simpa [conjTranspose_apply] using this
  refine posSemidef_iff_dotProduct_mulVec.2 ⟨?_, fun x => ?_⟩
  · ext α β
    simp only [conjTranspose_apply, star_trivial, lbteKappa_eq Mcol c v F h]
    congr 1
    rw [Finset.sum_comm]
    refine Finset.sum_congr rfl fun m _ => Finset.sum_congr rfl fun m' _ => ?_
    rw [hMs]
    ring
  · let y : ι → ℝ := fun m => ∑ γ, x γ * F m γ
    have hy := hMq y
    simp only [star_trivial] at hy ⊢
    have hq : x ⬝ᵥ (modeContractedKappa c v F Nq V *ᵥ x) = (y ⬝ᵥ (Mcol *ᵥ y)) / (Nq * V) := by
      simp only [dotProduct, mulVec, lbteKappa_eq Mcol c v F h, y, Finset.sum_div,
        Finset.mul_sum, Finset.sum_mul]
      conv_lhs => enter [2, α]; rw [Finset.sum_comm (β := ℝ)]
      rw [Finset.sum_comm (β := ℝ)]
      conv_lhs => enter [2, m, 2, α]; rw [Finset.sum_comm (β := ℝ)]
      conv_lhs => enter [2, m]; rw [Finset.sum_comm (β := ℝ)]
      refine Finset.sum_congr rfl fun m _ => Finset.sum_congr rfl fun m' _ =>
        Finset.sum_congr rfl fun α _ => Finset.sum_congr rfl fun β _ => ?_
      ring
    rw [hq]
    exact div_nonneg hy hNV.le

/-- The catalog cumulative conductivity with a step `θ` and a per-mode score `s` (the
frequency or the mean-free-displacement magnitude). -/
def cumulativeKappa {ι : Type*} [Fintype ι] (θ : ℝ → ℝ) (s c : ι → ℝ) (v F : ι → Fin 3 → ℝ)
    (Nq V cut : ℝ) : Matrix (Fin 3) (Fin 3) ℝ :=
  fun α β => (∑ m, θ (cut - s m) * F m β * c m * v m α) / (Nq * V)

/-- When every modal contribution `c_m (v_m·x)(F_m·x)` is nonnegative, as in the relaxation-time
approximation, the cumulative conductivity is nondecreasing in the cutoff in the Loewner
order, for any nondecreasing step. -/
theorem cumulativeKappa_mono {ι : Type*} [Fintype ι] (θ : ℝ → ℝ) (hθ : Monotone θ)
    (s c : ι → ℝ) (v F : ι → Fin 3 → ℝ) (Nq V : ℝ) (hNV : 0 < Nq * V)
    (hmodal : ∀ m (x : Fin 3 → ℝ), 0 ≤ c m * (v m ⬝ᵥ x) * (F m ⬝ᵥ x))
    {cut₁ cut₂ : ℝ} (hcut : cut₁ ≤ cut₂) (x : Fin 3 → ℝ) :
    x ⬝ᵥ (cumulativeKappa θ s c v F Nq V cut₁ *ᵥ x) ≤
      x ⬝ᵥ (cumulativeKappa θ s c v F Nq V cut₂ *ᵥ x) := by
  have hq : ∀ cut, x ⬝ᵥ (cumulativeKappa θ s c v F Nq V cut *ᵥ x) =
      (∑ m, θ (cut - s m) * (c m * (v m ⬝ᵥ x) * (F m ⬝ᵥ x))) / (Nq * V) := by
    intro cut
    simp only [dotProduct, mulVec, cumulativeKappa, Finset.sum_div, Finset.mul_sum,
      Finset.sum_mul]
    rw [Finset.sum_comm (β := ℝ)]
    conv_lhs => enter [2, β]; rw [Finset.sum_comm (β := ℝ)]
    rw [Finset.sum_comm (β := ℝ)]
    refine Finset.sum_congr rfl fun m _ => Finset.sum_congr rfl fun β _ =>
      Finset.sum_congr rfl fun α _ => ?_
    ring
  rw [hq, hq]
  refine div_le_div_of_nonneg_right ?_ hNV.le
  refine Finset.sum_le_sum fun m _ => ?_
  exact mul_le_mul_of_nonneg_right (hθ (by linarith)) (hmodal m x)

/-- Relaxation-time modal contributions are nonnegative for nonnegative capacities and
positive linewidths. -/
theorem rta_modal_nonneg (c Γ : ℝ) (hc : 0 ≤ c) (hΓ : 0 < Γ) (v x : Fin 3 → ℝ) :
    0 ≤ c * (v ⬝ᵥ x) * (rtaMeanFreeDisplacement v Γ ⬝ᵥ x) := by
  have h : rtaMeanFreeDisplacement v Γ ⬝ᵥ x = (v ⬝ᵥ x) / (2 * Γ) := by
    simp only [rtaMeanFreeDisplacement, dotProduct, Finset.sum_div]
    refine Finset.sum_congr rfl fun i _ => ?_
    ring
  rw [h, mul_assoc]
  refine mul_nonneg hc ?_
  rw [← mul_div_assoc]
  exact div_nonneg (mul_self_nonneg _) (by linarith)

/-- The catalog mean-free-path score `|F_m| = sqrt(∑_α F_{α,m}^2)` of the mfp cutoff. -/
def mfpScore {ι : Type*} (F : ι → Fin 3 → ℝ) (m : ι) : ℝ :=
  Real.sqrt (∑ α, F m α ^ 2)

/-- A mode whose contribution is negative and whose score no other mode shares makes the
cumulative distribution decrease across its score, for any step `θ` that is 1 above zero and 0
below. -/
theorem cumulativeKappa_not_monotone {ι : Type*} [Fintype ι] [DecidableEq ι] (θ : ℝ → ℝ)
    (hpos : ∀ y, 0 < y → θ y = 1) (hneg : ∀ y, y < 0 → θ y = 0) (s c : ι → ℝ)
    (v F : ι → Fin 3 → ℝ) (Nq V : ℝ) (hNV : 0 < Nq * V) (α β : Fin 3) (m : ι)
    (hm : F m β * c m * v m α < 0) (hs : ∀ m', m' ≠ m → s m' ≠ s m) :
    ¬ Monotone (fun cut => cumulativeKappa θ s c v F Nq V cut α β) := by
  intro hmono
  let D := (Finset.univ.erase m).image fun m' => |s m' - s m|
  have hDpos : ∀ d ∈ D, 0 < d := by
    intro d hd
    obtain ⟨m', hm', rfl⟩ := Finset.mem_image.1 hd
    exact abs_pos.2 (sub_ne_zero.2 (hs m' (Finset.ne_of_mem_erase hm')))
  obtain ⟨δ, hδ, hδle⟩ : ∃ δ > 0, ∀ m', m' ≠ m → δ ≤ |s m' - s m| := by
    by_cases hD : D.Nonempty
    · refine ⟨D.min' hD, hDpos _ (D.min'_mem hD), fun m' hm' => D.min'_le _ ?_⟩
      exact Finset.mem_image.2 ⟨m', Finset.mem_erase.2 ⟨hm', Finset.mem_univ _⟩, rfl⟩
    · refine ⟨1, one_pos, fun m' hm' => absurd ⟨_, Finset.mem_image.2
        ⟨m', Finset.mem_erase.2 ⟨hm', Finset.mem_univ _⟩, rfl⟩⟩ hD⟩
  have hstep : ∀ m', θ (s m + δ / 2 - s m') = θ (s m - δ / 2 - s m') + if m' = m then 1 else 0 := by
    intro m'
    by_cases h : m' = m
    · subst h
      rw [hpos _ (by linarith), hneg _ (by linarith)]
      simp
    · simp only [h, ↓reduceIte, add_zero]
      have hle := hδle m' h
      rcases lt_or_gt_of_ne (hs m' h) with hlt | hgt
      · rw [abs_of_neg (by linarith)] at hle
        rw [hpos _ (by linarith), hpos _ (by linarith)]
      · rw [abs_of_pos (by linarith)] at hle
        rw [hneg _ (by linarith), hneg _ (by linarith)]
  have h := hmono (show s m - δ / 2 ≤ s m + δ / 2 by linarith)
  simp only [cumulativeKappa] at h
  rw [div_le_div_iff_of_pos_right hNV] at h
  simp only [hstep, add_mul, Finset.sum_add_distrib, ite_mul, one_mul, zero_mul,
    Finset.sum_ite_eq', Finset.mem_univ, ite_true] at h
  linarith

/-- The Bose-Einstein factor `n(n+1) = e^x/(e^x - 1)^2` at `x = ħω/(k_B T)`. -/
def boseFactor (x : ℝ) : ℝ := Real.exp x / (Real.exp x - 1) ^ 2

/-- Three modes with `ħω/(k_B T) = 1, 2, 3`, so that `ω_3 = ω_1 + ω_2`. -/
def tpOmega : Fin 3 → ℝ := ![1, 2, 3]

/-- The single three-phonon coalescence process `1 + 2 <-> 3`. -/
def tpU : Fin 3 → ℝ := ![1, 1, -1]

/-- x components of the group velocities. -/
def tpVx : Fin 3 → ℝ := ![2, 2, -1]

def tpN (m : Fin 3) : ℝ := boseFactor (tpOmega m)

/-- Canonical mode heat capacities `x^2 n(n+1)`, in units of `k_B`. -/
def tpCap (m : Fin 3) : ℝ := tpOmega m ^ 2 * tpN m

def tpVelocity (m : Fin 3) : Fin 3 → ℝ := Pi.single 0 (tpVx m)

/-- The symmetric collision matrix `M = D (P u u^T + diag(n(n+1)|v|/L)) D` with `D = diag(ω)`:
one process of strength `P` and Casimir boundary scattering `1/τ = |v|/L`, in units
`ħ = k_B = T = 1`. -/
def tpCollision (P L : ℝ) : Matrix (Fin 3) (Fin 3) ℝ := fun m m' =>
  tpOmega m * (P * tpU m * tpU m' + if m = m' then tpN m * |tpVx m| / L else 0) * tpOmega m'

/-- `Δ = 2 n_1 n_2 n_3 + K (n_2 n_3 + n_1 n_3 + 2 n_1 n_2)` with `K = P L`. -/
def tpDelta (P L : ℝ) : ℝ :=
  2 * tpN 0 * tpN 1 * tpN 2 + P * L * (tpN 1 * tpN 2 + tpN 0 * tpN 2 + 2 * tpN 0 * tpN 1)

/-- The exact solution of the linearized BTE of the model (Sherman-Morrison). -/
def tpFx (P L : ℝ) : Fin 3 → ℝ :=
  ![L * (tpDelta P L - 6 * (P * L) * tpN 1 * tpN 2) / tpDelta P L,
    L * (tpDelta P L - 3 * (P * L) * tpN 0 * tpN 2) / tpDelta P L,
    L * (4 * (P * L) * tpN 0 * tpN 1 - tpDelta P L) / tpDelta P L]

def tpF (P L : ℝ) (m : Fin 3) : Fin 3 → ℝ := Pi.single 0 (tpFx P L m)

theorem exp_two_eq : Real.exp 2 = Real.exp 1 ^ 2 := by
  rw [← Real.exp_nat_mul]; norm_num

theorem exp_three_eq : Real.exp 3 = Real.exp 1 ^ 3 := by
  rw [← Real.exp_nat_mul]; norm_num

theorem tpN_formulas : tpN 0 = Real.exp 1 / (Real.exp 1 - 1) ^ 2 ∧
    tpN 1 = Real.exp 1 ^ 2 / (Real.exp 1 ^ 2 - 1) ^ 2 ∧
    tpN 2 = Real.exp 1 ^ 3 / (Real.exp 1 ^ 3 - 1) ^ 2 := by
  refine ⟨rfl, ?_, ?_⟩
  · show Real.exp 2 / (Real.exp 2 - 1) ^ 2 = _
    rw [exp_two_eq]
  · show Real.exp 3 / (Real.exp 3 - 1) ^ 2 = _
    rw [exp_three_eq]

/-- The Bose-Einstein factors of the model are positive and ordered strongly enough:
`2 n_3 < n_2`, `2 n_3 < n_1`, `3 n_2 < n_1`, `n_2 < 1/2` and `n_3 < 1/2`. -/
theorem tpN_facts : (∀ m, 0 < tpN m) ∧ 2 * tpN 2 < tpN 1 ∧ 2 * tpN 2 < tpN 0 ∧
    3 * tpN 1 < tpN 0 ∧ tpN 1 < 1 / 2 ∧ tpN 2 < 1 / 2 := by
  obtain ⟨h0, h1, h2⟩ := tpN_formulas
  have hE : (2 : ℝ) < Real.exp 1 := by
    have := Real.add_one_lt_exp (one_ne_zero (α := ℝ)); linarith
  set E := Real.exp 1 with hEdef
  have hE1 : 0 < E - 1 := by linarith
  have hE2 : 0 < E ^ 2 - 1 := by nlinarith
  have hE3 : 0 < E ^ 3 - 1 := by nlinarith
  have hpos : ∀ m, 0 < tpN m := by
    intro m; fin_cases m
    · show 0 < tpN 0; rw [h0]; positivity
    · show 0 < tpN 1; rw [h1]; positivity
    · show 0 < tpN 2; rw [h2]; positivity
  refine ⟨hpos, ?_, ?_, ?_, ?_, ?_⟩
  · rw [h1, h2, ← mul_div_assoc, div_lt_div_iff₀ (by positivity) (by positivity)]
    have key : E ^ 2 * (E ^ 3 - 1) ^ 2 - 2 * E ^ 3 * (E ^ 2 - 1) ^ 2 =
        E ^ 2 * (E - 1) ^ 2 * (E ^ 4 - E ^ 2 + 1) := by ring
    have hq : 0 < E ^ 4 - E ^ 2 + 1 := by nlinarith [sq_nonneg (E ^ 2 - 1 / 2)]
    have : 0 < E ^ 2 * (E - 1) ^ 2 * (E ^ 4 - E ^ 2 + 1) := by positivity
    linarith
  · rw [h0, h2, ← mul_div_assoc, div_lt_div_iff₀ (by positivity) (by positivity)]
    have key : E * (E ^ 3 - 1) ^ 2 - 2 * E ^ 3 * (E - 1) ^ 2 =
        E * (E - 1) ^ 2 * ((E ^ 2 + E + 1) ^ 2 - 2 * E ^ 2) := by ring
    have hq : 0 < (E ^ 2 + E + 1) ^ 2 - 2 * E ^ 2 := by nlinarith
    have : 0 < E * (E - 1) ^ 2 * ((E ^ 2 + E + 1) ^ 2 - 2 * E ^ 2) := by positivity
    linarith
  · rw [h0, h1, ← mul_div_assoc, div_lt_div_iff₀ (by positivity) (by positivity)]
    have key : E * (E ^ 2 - 1) ^ 2 - 3 * E ^ 2 * (E - 1) ^ 2 =
        E * (E - 1) ^ 2 * (E ^ 2 - E + 1) := by ring
    have hq : 0 < E ^ 2 - E + 1 := by nlinarith
    have : 0 < E * (E - 1) ^ 2 * (E ^ 2 - E + 1) := by positivity
    linarith
  · rw [h1, div_lt_iff₀ (by positivity)]
    nlinarith
  · rw [h2, div_lt_iff₀ (by positivity)]
    nlinarith

theorem tpDelta_pos (P L : ℝ) (hP : 0 < P) (hL : 0 < L) : 0 < tpDelta P L := by
  obtain ⟨hn, -⟩ := tpN_facts
  have := hn 0; have := hn 1; have := hn 2
  unfold tpDelta; positivity

/-- The model's `F` solves the catalog linearized BTE with the model's collision matrix and
canonical heat capacities. -/
theorem tp_lbteSolves (P L : ℝ) (hP : 0 < P) (hL : 0 < L) :
    LBTESolves (tpCollision P L) tpCap tpVelocity (tpF P L) := by
  have hD := (tpDelta_pos P L hP hL).ne'
  intro α m
  fin_cases α <;> fin_cases m <;>
    simp [tpCollision, tpF, tpVelocity, tpFx, tpCap, tpOmega, tpU, tpVx, Fin.sum_univ_three] <;>
    field_simp <;> unfold tpDelta <;> ring

/-- The model's collision matrix is symmetric and positive definite. -/
theorem tp_collision_posDef (P L : ℝ) (hP : 0 < P) (hL : 0 < L) :
    (tpCollision P L).PosDef := by
  obtain ⟨hn, -⟩ := tpN_facts
  have r0 : 0 < tpN 0 * 2 / L := by have := hn 0; positivity
  have r1 : 0 < tpN 1 * 2 / L := by have := hn 1; positivity
  have r2 : 0 < tpN 2 * 1 / L := by have := hn 2; positivity
  refine posDef_iff_dotProduct_mulVec.2 ⟨?_, fun x hx => ?_⟩
  · ext i j
    simp only [conjTranspose_apply, star_trivial, tpCollision]
    by_cases h : i = j
    · subst h; rfl
    · have h' : ¬j = i := Ne.symm h
      simp only [h, h', ↓reduceIte]; ring
  · have hq : star x ⬝ᵥ (tpCollision P L *ᵥ x) =
        P * (x 0 + 2 * x 1 - 3 * x 2) ^ 2 + tpN 0 * 2 / L * x 0 ^ 2 +
          4 * (tpN 1 * 2 / L) * x 1 ^ 2 + 9 * (tpN 2 * 1 / L) * x 2 ^ 2 := by
      simp only [star_trivial, dotProduct, mulVec, tpCollision, Fin.sum_univ_three, tpOmega, tpU,
        tpVx]
      norm_num [Matrix.vecHead, Matrix.vecTail]
      ring
    rw [hq]
    have hx' : x 0 ≠ 0 ∨ x 1 ≠ 0 ∨ x 2 ≠ 0 := by
      by_contra h
      simp only [not_or, not_not] at h
      exact hx (funext fun i => by fin_cases i <;> simp [h.1, h.2.1, h.2.2])
    have s0 := mul_nonneg r0.le (sq_nonneg (x 0))
    have s1 := mul_nonneg (by positivity : (0 : ℝ) ≤ 4 * (tpN 1 * 2 / L)) (sq_nonneg (x 1))
    have s2 := mul_nonneg (by positivity : (0 : ℝ) ≤ 9 * (tpN 2 * 1 / L)) (sq_nonneg (x 2))
    have sP := mul_nonneg hP.le (sq_nonneg (x 0 + 2 * x 1 - 3 * x 2))
    rcases hx' with h | h | h
    · have := mul_pos r0 (pow_pos (abs_pos.2 h) 2); rw [sq_abs] at this; linarith
    · have := mul_pos (by positivity : (0 : ℝ) < 4 * (tpN 1 * 2 / L)) (pow_pos (abs_pos.2 h) 2)
      rw [sq_abs] at this; linarith
    · have := mul_pos (by positivity : (0 : ℝ) < 9 * (tpN 2 * 1 / L)) (pow_pos (abs_pos.2 h) 2)
      rw [sq_abs] at this; linarith

/-- For `P L ≥ 10` all three mean free displacements are positive and ordered
`F_2 < F_3 < F_1`, and the third mode's contribution `F_3 c_3 v_3` to `κ_xx` is negative. -/
theorem tp_signs (P L : ℝ) (hP : 0 < P) (hL : 0 < L) (hPL : 10 ≤ P * L) :
    0 < tpFx P L 1 ∧ tpFx P L 1 < tpFx P L 2 ∧ tpFx P L 2 < tpFx P L 0 ∧
      tpF P L 2 0 * tpCap 2 * tpVelocity 2 0 < 0 := by
  obtain ⟨hn, h21, h20, h10, h1h, h2h⟩ := tpN_facts
  have n0 := hn 0
  have n1 := hn 1
  have n2 := hn 2
  have hD := tpDelta_pos P L hP hL
  set K := P * L with hK
  have hKpos : 0 < K := by positivity
  set Δ := tpDelta P L with hΔ
  have hΔe : Δ = 2 * tpN 0 * tpN 1 * tpN 2 + K * (tpN 1 * tpN 2 + tpN 0 * tpN 2 +
      2 * tpN 0 * tpN 1) := rfl
  have e0 : tpFx P L 0 = L * (Δ - 6 * K * tpN 1 * tpN 2) / Δ := rfl
  have e1 : tpFx P L 1 = L * (Δ - 3 * K * tpN 0 * tpN 2) / Δ := rfl
  have e2 : tpFx P L 2 = L * (4 * K * tpN 0 * tpN 1 - Δ) / Δ := rfl
  have p01 := mul_pos n0 n1
  have p02 := mul_pos n0 n2
  have p12 := mul_pos n1 n2
  -- Δ - 3 K n_1 n_3 > 0, since n_2 > n_3.
  have a1 : 0 < Δ - 3 * K * tpN 0 * tpN 2 := by
    rw [hΔe]; nlinarith [mul_pos hKpos p12, mul_pos hKpos (mul_pos n0 (by linarith : 0 < tpN 1 - tpN 2)),
      mul_pos (mul_pos n0 n1) n2]
  -- 4 K n_1 n_2 - Δ > 0, since 2 n_3 < n_1, 2 n_3 < n_2 and 2 n_3 < 1 < K.
  have a2 : 0 < 4 * K * tpN 0 * tpN 1 - Δ := by
    rw [hΔe]
    have q1 : tpN 1 * tpN 2 * 2 < tpN 1 * tpN 0 := by nlinarith
    have q2 : tpN 0 * tpN 2 * 2 < tpN 0 * tpN 1 := by nlinarith
    have q3 : 2 * tpN 0 * tpN 1 * tpN 2 < K * (tpN 0 * tpN 1) := by
      have : 2 * tpN 2 < K := by linarith
      nlinarith
    nlinarith [mul_pos hKpos p01]
  -- 2 Δ < K (4 n_1 n_2 + 3 n_1 n_3), since 3 n_2 < n_1, n_2 < 1/2 and K ≥ 10.
  have a12 : Δ - 3 * K * tpN 0 * tpN 2 < 4 * K * tpN 0 * tpN 1 - Δ := by
    rw [hΔe]
    have q : 4 * tpN 0 * tpN 1 < K * (tpN 0 - 2 * tpN 1) := by
      have h3 : tpN 0 / 3 < tpN 0 - 2 * tpN 1 := by linarith
      have h4 : 4 * tpN 0 * tpN 1 < 2 * tpN 0 := by nlinarith
      have h5 : 2 * tpN 0 ≤ K * (tpN 0 / 3) := by nlinarith
      nlinarith [mul_lt_mul_of_pos_left h3 hKpos]
    nlinarith [mul_lt_mul_of_pos_right q n2]
  -- 4 K n_1 n_2 - Δ < Δ - 6 K n_2 n_3, since 2 n_2 < n_1.
  have a20 : 4 * K * tpN 0 * tpN 1 - Δ < Δ - 6 * K * tpN 1 * tpN 2 := by
    rw [hΔe]
    have q : 2 * K * tpN 1 < 2 * tpN 0 * tpN 1 + K * tpN 0 := by
      have : 2 * tpN 1 < tpN 0 := by linarith
      nlinarith [mul_pos hKpos p01]
    nlinarith [mul_lt_mul_of_pos_right q n2]
  refine ⟨?_, ?_, ?_, ?_⟩
  · rw [e1]; positivity
  · rw [e1, e2]
    exact div_lt_div_of_pos_right (mul_lt_mul_of_pos_left a12 hL) hD
  · rw [e2, e0]
    exact div_lt_div_of_pos_right (mul_lt_mul_of_pos_left a20 hL) hD
  · have hF2 : 0 < tpFx P L 2 := by rw [e2]; positivity
    simp only [tpF, tpVelocity, Pi.single_eq_same, tpCap, tpVx, tpOmega]
    simp only [Fin.isValue, Matrix.cons_val_two, Matrix.tail_cons, Matrix.head_cons]
    nlinarith [mul_pos hF2 n2]

theorem tp_mfpScore (P L : ℝ) (m : Fin 3) : mfpScore (tpF P L) m = |tpFx P L m| := by
  unfold mfpScore tpF
  have : ∑ α : Fin 3, (Pi.single (0 : Fin 3) (tpFx P L m) : Fin 3 → ℝ) α ^ 2 = tpFx P L m ^ 2 := by
    rw [Fin.sum_univ_three]
    simp
  rw [this, Real.sqrt_sq_eq_abs]

/-- The cumulative conductivity of the three-mode linearized BTE, binned by frequency, is not
monotone in the cutoff: it drops across `ω_3` by the negative contribution of mode 3. -/
theorem tp_cumulative_omega_not_monotone (θ : ℝ → ℝ) (hpos : ∀ y, 0 < y → θ y = 1)
    (hneg : ∀ y, y < 0 → θ y = 0) (P L Nq V : ℝ) (hP : 0 < P) (hL : 0 < L) (hPL : 10 ≤ P * L)
    (hNV : 0 < Nq * V) :
    LBTESolves (tpCollision P L) tpCap tpVelocity (tpF P L) ∧ (tpCollision P L).PosDef ∧
      ¬ Monotone (fun cut => cumulativeKappa θ tpOmega tpCap tpVelocity (tpF P L) Nq V cut 0 0) := by
  refine ⟨tp_lbteSolves P L hP hL, tp_collision_posDef P L hP hL, ?_⟩
  refine cumulativeKappa_not_monotone θ hpos hneg _ _ _ _ Nq V hNV 0 0 2
    (tp_signs P L hP hL hPL).2.2.2 ?_
  intro m hm
  fin_cases m <;> simp_all [tpOmega]

/-- The same linearized BTE binned by the catalog mean-free-path score `|F|` is not monotone
either: the scores are ordered `|F_2| < |F_3| < |F_1|`, and crossing `|F_3|` adds the negative
contribution of mode 3. -/
theorem tp_cumulative_mfp_not_monotone (θ : ℝ → ℝ) (hpos : ∀ y, 0 < y → θ y = 1)
    (hneg : ∀ y, y < 0 → θ y = 0) (P L Nq V : ℝ) (hP : 0 < P) (hL : 0 < L) (hPL : 10 ≤ P * L)
    (hNV : 0 < Nq * V) :
    ¬ Monotone (fun cut =>
      cumulativeKappa θ (mfpScore (tpF P L)) tpCap tpVelocity (tpF P L) Nq V cut 0 0) := by
  obtain ⟨h1, h12, h20, hk⟩ := tp_signs P L hP hL hPL
  refine cumulativeKappa_not_monotone θ hpos hneg _ _ _ _ Nq V hNV 0 0 2 hk ?_
  intro m hm
  simp only [tp_mfpScore]
  rw [abs_of_pos (by linarith : 0 < tpFx P L 2)]
  fin_cases m
  · show |tpFx P L 0| ≠ tpFx P L 2
    rw [abs_of_pos (by linarith : 0 < tpFx P L 0)]; exact ne_of_gt h20
  · show |tpFx P L 1| ≠ tpFx P L 2
    rw [abs_of_pos h1]; exact ne_of_lt h12
  · exact absurd rfl hm

end OMAI.PhyslibBridge.Lattice
