/- The participation ratio of a normalized vibrational mode: the documented range
1/N <= p <= 1 with both equality cases. Mathlib only; no Physlib model is involved. The amplitudes
are those of the mass-weighted eigenvector (the kALDo convention), which differs from the
displacement-based Bell-Dean value in multi-species crystals; the ratio measures the spread of
one mode over the basis atoms at fixed q. -/
module

public import Mathlib.Analysis.MeanInequalities
public import Mathlib.Algebra.Order.Chebyshev
public import Mathlib.Analysis.Complex.Basic

@[expose] public section

noncomputable section

namespace OMAI.PhyslibBridge.Lattice

/-- The catalog participation ratio `p = 1 / (N ∑_i a_i^2)` over the per-atom amplitudes. -/
def participationRatio {N : ℕ} (a : Fin N → ℝ) : ℝ :=
  1 / (N * ∑ i, a i ^ 2)

/-- The catalog per-atom amplitude `a_i = ∑_α |e_{i,α}|^2`. -/
def atomAmplitude {N : ℕ} (e : Fin N → Fin 3 → ℂ) (i : Fin N) : ℝ :=
  ∑ α, ‖e i α‖ ^ 2

theorem atomAmplitude_nonneg {N : ℕ} (e : Fin N → Fin 3 → ℂ) (i : Fin N) :
    0 ≤ atomAmplitude e i :=
  Finset.sum_nonneg fun _ _ => sq_nonneg _

/-- For nonnegative amplitudes summing to one, `1 ≤ N ∑ a_i^2 ≤ N`. -/
theorem sumSq_bounds {N : ℕ} (a : Fin N → ℝ) (ha : ∀ i, 0 ≤ a i) (hsum : ∑ i, a i = 1) :
    1 ≤ N * ∑ i, a i ^ 2 ∧ ∑ i, a i ^ 2 ≤ 1 := by
  constructor
  · have h := sq_sum_le_card_mul_sum_sq (s := Finset.univ) (f := a)
    simpa [hsum] using h
  · calc ∑ i, a i ^ 2 ≤ ∑ i, a i := Finset.sum_le_sum fun i _ => by
          have hle : a i ≤ 1 := by
            rw [← hsum]
            exact Finset.single_le_sum (fun j _ => ha j) (Finset.mem_univ i)
          nlinarith [ha i]
      _ = 1 := hsum

/-- The documented range of the participation ratio of a normalized mode: `1/N ≤ p ≤ 1`. -/
theorem participationRatio_bounds {N : ℕ} (e : Fin N → Fin 3 → ℂ)
    (hnorm : ∑ i, ∑ α, ‖e i α‖ ^ 2 = 1) :
    1 / (N : ℝ) ≤ participationRatio (atomAmplitude e) ∧
      participationRatio (atomAmplitude e) ≤ 1 := by
  obtain ⟨hlow, hhigh⟩ := sumSq_bounds (atomAmplitude e) (atomAmplitude_nonneg e) hnorm
  have hpos : 0 < (N : ℝ) * ∑ i, atomAmplitude e i ^ 2 := by linarith
  have hN : 0 < (N : ℝ) := by
    rcases Nat.eq_zero_or_pos N with h | h
    · subst h; norm_num at hlow
    · exact_mod_cast h
  unfold participationRatio
  constructor
  · rw [div_le_div_iff₀ hN hpos, one_mul, one_mul]
    nlinarith
  · rw [div_le_one hpos]
    exact hlow

/-- `p = 1` exactly for a uniformly extended mode, `a_i = 1/N` on every atom. -/
theorem participationRatio_eq_one_iff {N : ℕ} (e : Fin N → Fin 3 → ℂ)
    (hnorm : ∑ i, ∑ α, ‖e i α‖ ^ 2 = 1) :
    participationRatio (atomAmplitude e) = 1 ↔ ∀ i, atomAmplitude e i = 1 / N := by
  set a := atomAmplitude e
  have hsum : ∑ i, a i = 1 := hnorm
  obtain ⟨hlow, -⟩ := sumSq_bounds a (atomAmplitude_nonneg e) hsum
  have hN : 0 < (N : ℝ) := by
    rcases Nat.eq_zero_or_pos N with h | h
    · subst h; norm_num at hlow
    · exact_mod_cast h
  -- ∑ (a_i - 1/N)^2 = ∑ a_i^2 - 1/N.
  have hdev : ∑ i, (a i - 1 / N) ^ 2 = ∑ i, a i ^ 2 - 1 / N := by
    have hcard : (Finset.univ : Finset (Fin N)).card = N := by simp
    simp only [sub_sq, Finset.sum_add_distrib, Finset.sum_sub_distrib, ← Finset.sum_mul,
      ← Finset.mul_sum, hsum, Finset.sum_const, hcard, nsmul_eq_mul]
    field_simp
    ring
  unfold participationRatio
  rw [div_eq_one_iff_eq (by linarith)]
  constructor
  · intro h i
    have hz : ∑ i, (a i - 1 / N) ^ 2 = 0 := by
      rw [hdev]
      field_simp
      linarith
    have := (Finset.sum_eq_zero_iff_of_nonneg fun i _ => sq_nonneg (a i - 1 / N)).1 hz i
      (Finset.mem_univ i)
    linarith [pow_eq_zero_iff (n := 2) (by norm_num) |>.1 this]
  · intro h
    have hz : ∑ i, (a i - 1 / N) ^ 2 = 0 := Finset.sum_eq_zero fun i _ => by rw [h i]; ring
    rw [hdev] at hz
    field_simp at hz ⊢
    linarith

/-- `p = 1/N` exactly for a mode localized on a single atom. -/
theorem participationRatio_eq_inv_iff {N : ℕ} (e : Fin N → Fin 3 → ℂ)
    (hnorm : ∑ i, ∑ α, ‖e i α‖ ^ 2 = 1) :
    participationRatio (atomAmplitude e) = 1 / N ↔
      ∃ i, atomAmplitude e i = 1 ∧ ∀ j, j ≠ i → atomAmplitude e j = 0 := by
  set a := atomAmplitude e
  have ha : ∀ i, 0 ≤ a i := atomAmplitude_nonneg e
  have hsum : ∑ i, a i = 1 := hnorm
  obtain ⟨hlow, -⟩ := sumSq_bounds a ha hsum
  have hN : 0 < (N : ℝ) := by
    rcases Nat.eq_zero_or_pos N with h | h
    · subst h; norm_num at hlow
    · exact_mod_cast h
  have hle1 : ∀ i, a i ≤ 1 := fun i => by
    rw [← hsum]; exact Finset.single_le_sum (fun j _ => ha j) (Finset.mem_univ i)
  have hiff : participationRatio a = 1 / N ↔ ∑ i, a i ^ 2 = 1 := by
    unfold participationRatio
    rw [one_div, one_div, inv_inj, mul_eq_left₀ hN.ne']
  rw [hiff]
  constructor
  · intro h
    -- ∑ a_i (1 - a_i) = 0 with every term nonnegative.
    have hz : ∑ i, a i * (1 - a i) = 0 := by
      simp only [mul_sub, mul_one, Finset.sum_sub_distrib, hsum, ← sq, h, sub_self]
    have hterm := fun i =>
      (Finset.sum_eq_zero_iff_of_nonneg fun i _ => mul_nonneg (ha i) (by linarith [hle1 i])).1
        hz i (Finset.mem_univ i)
    have h01 : ∀ i, a i = 0 ∨ a i = 1 := fun i => by
      rcases mul_eq_zero.1 (hterm i) with h0 | h1
      · exact Or.inl h0
      · exact Or.inr (by linarith)
    obtain ⟨i, hi⟩ : ∃ i, a i = 1 := by
      by_contra hno
      have : ∀ i, a i = 0 := fun i => (h01 i).resolve_right fun h1 => hno ⟨i, h1⟩
      simp [this] at hsum
    refine ⟨i, hi, fun j hj => ?_⟩
    have hrest : ∑ k ∈ Finset.univ.erase i, a k = 0 := by
      rw [← Finset.add_sum_erase _ _ (Finset.mem_univ i), hi] at hsum
      linarith
    exact (Finset.sum_eq_zero_iff_of_nonneg fun k _ => ha k).1 hrest j
      (Finset.mem_erase.2 ⟨hj, Finset.mem_univ j⟩)
  · rintro ⟨i, hi, hrest⟩
    rw [← Finset.add_sum_erase _ _ (Finset.mem_univ i), hi,
      Finset.sum_eq_zero fun j hj => by rw [hrest j (Finset.ne_of_mem_erase hj)]; ring]
    ring

end OMAI.PhyslibBridge.Lattice
