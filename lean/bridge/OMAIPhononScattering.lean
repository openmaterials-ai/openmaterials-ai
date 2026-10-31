module

public import Mathlib.Analysis.SpecialFunctions.Exp
public import Mathlib.Analysis.SpecialFunctions.Sqrt
public import Mathlib.Analysis.Complex.Basic
public import Mathlib.Algebra.Order.Chebyshev
public import Mathlib.Tactic

/-!
# Phonon scattering channels and the relaxation-time mean free path

The catalog's three linewidth channels are the canonical linewidth `Gamma = Im Sigma = 1/(2 tau)`
on a finite Brillouin-zone mesh `Q` with branch set `ι` and basis atoms `B`. The Tamura isotope
linewidth is `(π / 4 N_q) ω² Σ_{q'ν'} δ(ω - ω') Σ_b g_b |e_b(qν)* · e_b(q'ν')|²`. The three-phonon
linewidth is `(π / 2 N_q ħ²) Σ_{q'ν'ν''} |V₃|² [(1 + n' + n'') δ(ω - ω' - ω'') + 2 (n' - n'')
δ(ω + ω' - ω'')]` with `ω'' = ω(q - q', ν'')`. The Casimir boundary linewidth is `|v| / (2L)`.
Matthiessen's rule adds the channels, and the relaxation-time mean free displacement is
`F = v / (2 Γ)`. Physlib has no phonon-scattering model, so these results use Mathlib only and
identify no Physlib declaration.

The isotope linewidth is nonnegative and, for normalized eigenvectors, at most
`(π/4) ω² g_max D(ω)` with `D(ω) = (1/N_q) Σ_{q'ν'} δ(ω - ω')` the density of states smeared with
the isotope kernel, which integrates to the number of branches. The three-phonon linewidth is
nonnegative for a `|V₃|²` symmetric under exchange of the two partner phonons, as the
Maradudin-Fein form is, and an even smearing kernel that does not increase with `|x|`, which
covers the catalog's Gaussian. For an arbitrary `|V₃|²` it is nonnegative when the kernel vanishes
at signed offsets above `ω_qν`, and a compiled example shows that an even but non-monotone kernel
can make it negative even with the symmetry. With the boundary channel present the
relaxation-time mean free displacement never exceeds the boundary length `L`, with equality
exactly when the other channels vanish. That bound holds only because the boundary linewidth and
the relaxation time carry the same factor 2 of `Γ = 1/(2τ)`.
-/

@[expose] public section

noncomputable section

open Real Finset

namespace OMAI.PhyslibBridge.PhononScattering

/-! ## Catalog transcriptions -/

/-- The Bose-Einstein occupation `n(x) = 1 / (eˣ - 1)` at the dimensionless argument
`x = ħω / (k_B T)`. -/
def bose (x : ℝ) : ℝ := 1 / (exp x - 1)

/-- The reviewed catalog expression of `compute_isotope_scattering`: the Tamura isotope
linewidth of mode `(q, ν)` with frequencies `omega`, eigenvector components `e q ν b α` of basis
atom `b` along Cartesian axis `α`, mass-variance factors `g` and smearing kernel `delta`. This
definition alone is not a physical proof. -/
def isotopeLinewidth {Q ι B : Type*} [Fintype Q] [Fintype ι] [Fintype B]
    (delta : ℝ → ℝ) (omega : Q → ι → ℝ) (g : B → ℝ) (e : Q → ι → B → Fin 3 → ℂ)
    (q : Q) (ν : ι) : ℝ :=
  π / (4 * Fintype.card Q) * omega q ν ^ 2 *
    ∑ q', ∑ ν', delta (omega q ν - omega q' ν') *
      ∑ b, g b * ‖∑ α, star (e q ν b α) * e q' ν' b α‖ ^ 2

/-- The reviewed catalog expression of `compute_linewidth[channel=anharmonic_3ph]`: the
three-phonon linewidth of mode `(q, ν)` with kernel `V3 q ν q' ν' q'' ν''` (the catalog's
`|V₃|²`), frequencies `omega`, smearing kernel `delta`, and `n = bose (ħω / (k_B T))`. This
definition alone is not a physical proof. -/
def anharmonicLinewidth {Q ι : Type*} [Fintype Q] [AddCommGroup Q] [Fintype ι]
    (hbar kB T : ℝ) (delta : ℝ → ℝ) (omega : Q → ι → ℝ)
    (V3 : Q → ι → Q → ι → Q → ι → ℝ) (q : Q) (ν : ι) : ℝ :=
  π / (2 * Fintype.card Q * hbar ^ 2) *
    ∑ q', ∑ ν', ∑ ν'', V3 q ν q' ν' (q - q') ν'' *
      ((1 + bose (hbar * omega q' ν' / (kB * T)) + bose (hbar * omega (q - q') ν'' / (kB * T))) *
          delta (omega q ν - omega q' ν' - omega (q - q') ν'') +
        2 * (bose (hbar * omega q' ν' / (kB * T)) - bose (hbar * omega (q - q') ν'' / (kB * T))) *
          delta (omega q ν + omega q' ν' - omega (q - q') ν''))

/-- The reviewed catalog expression of `compute_boundary_scattering`: the Casimir boundary
linewidth `|v| / (2L)` of a mode with group velocity `v`. This definition alone is not a physical
proof. -/
def boundaryLinewidth (v : Fin 3 → ℝ) (L : ℝ) : ℝ := √(∑ α, v α ^ 2) / (2 * L)

/-- The reviewed catalog expression of `sum_linewidths`: Matthiessen's rule. This definition
alone is not a physical proof. -/
def totalLinewidth (anh iso bnd : ℝ) : ℝ := anh + iso + bnd

/-- The reviewed catalog expression of `solve_bte[bte_solver=rta]`: the relaxation-time mean free
displacement `F = v / (2 Γ)`. This definition alone is not a physical proof. -/
def rtaDisplacement (v : Fin 3 → ℝ) (Γ : ℝ) : Fin 3 → ℝ := fun α => v α / (2 * Γ)

/-! ## Bose-Einstein occupation -/

theorem bose_pos {x : ℝ} (hx : 0 < x) : 0 < bose x := by
  unfold bose
  have : 1 < exp x := one_lt_exp_iff.mpr hx
  exact one_div_pos.mpr (by linarith)

/-- The occupation decreases strictly with the argument on `(0, ∞)`. -/
theorem bose_strictAntiOn : StrictAntiOn bose (Set.Ioi 0) := by
  intro x hx y hy hxy
  unfold bose
  have h1 : 1 < exp x := one_lt_exp_iff.mpr hx
  have h2 : exp x < exp y := exp_lt_exp.mpr hxy
  exact one_div_lt_one_div_of_lt (by linarith) (by linarith)

/-! ## Isotope linewidth -/

section Isotope

variable {Q ι B : Type*} [Fintype Q] [Fintype ι] [Fintype B]

theorem isotopeLinewidth_nonneg (delta : ℝ → ℝ) (omega : Q → ι → ℝ) (g : B → ℝ)
    (e : Q → ι → B → Fin 3 → ℂ) (q : Q) (ν : ι) (hdelta : ∀ x, 0 ≤ delta x)
    (hg : ∀ b, 0 ≤ g b) : 0 ≤ isotopeLinewidth delta omega g e q ν := by
  unfold isotopeLinewidth
  apply mul_nonneg
  · apply mul_nonneg
    · exact div_nonneg pi_pos.le (by positivity)
    · positivity
  · apply sum_nonneg; intro q' _
    apply sum_nonneg; intro ν' _
    apply mul_nonneg (hdelta _)
    apply sum_nonneg; intro b _
    exact mul_nonneg (hg b) (by positivity)

private theorem overlap_sq_le (a c : Fin 3 → ℂ) :
    ‖∑ α, star (a α) * c α‖ ^ 2 ≤ (∑ α, ‖a α‖ ^ 2) * ∑ α, ‖c α‖ ^ 2 := by
  have h1 : ‖∑ α, star (a α) * c α‖ ≤ ∑ α, ‖a α‖ * ‖c α‖ := by
    refine (norm_sum_le _ _).trans (le_of_eq ?_)
    refine sum_congr rfl fun α _ => ?_
    rw [norm_mul, norm_star]
  have h2 : (∑ α, ‖a α‖ * ‖c α‖) ^ 2 ≤ (∑ α, ‖a α‖ ^ 2) * ∑ α, ‖c α‖ ^ 2 :=
    sum_mul_sq_le_sq_mul_sq _ _ _
  calc ‖∑ α, star (a α) * c α‖ ^ 2 ≤ (∑ α, ‖a α‖ * ‖c α‖) ^ 2 :=
        pow_le_pow_left₀ (norm_nonneg _) h1 2
    _ ≤ _ := h2

private theorem sum_mul_le_sum_mul_sum {x y : B → ℝ} (hx : ∀ b, 0 ≤ x b) (hy : ∀ b, 0 ≤ y b) :
    ∑ b, x b * y b ≤ (∑ b, x b) * ∑ b, y b := by
  rw [sum_mul]
  refine sum_le_sum fun b _ => mul_le_mul_of_nonneg_left ?_ (hx b)
  exact single_le_sum (fun c _ => hy c) (mem_univ b)

/-- For normalized eigenvectors and mass-variance factors in `[0, g_max]`, the isotope linewidth
is at most `(π/4) ω² g_max D(ω)` with `D(ω) = (1/N_q) Σ_{q'ν'} δ(ω - ω')` the smeared density of
states at the mode's frequency. -/
theorem isotopeLinewidth_le_dos (delta : ℝ → ℝ) (omega : Q → ι → ℝ) (g : B → ℝ)
    (e : Q → ι → B → Fin 3 → ℂ) (q : Q) (ν : ι) (gmax : ℝ) (hdelta : ∀ x, 0 ≤ delta x)
    (hg : ∀ b, 0 ≤ g b) (hgmax : ∀ b, g b ≤ gmax)
    (hnorm : ∀ q ν, ∑ b, ∑ α, ‖e q ν b α‖ ^ 2 = 1) :
    isotopeLinewidth delta omega g e q ν ≤
      π / 4 * omega q ν ^ 2 * gmax *
        ((∑ q', ∑ ν', delta (omega q ν - omega q' ν')) / Fintype.card Q) := by
  have hne : Nonempty B := by
    by_contra h
    have h0 := hnorm q ν
    rw [not_nonempty_iff] at h
    simp at h0
  obtain ⟨b0⟩ := hne
  have hgm : 0 ≤ gmax := (hg b0).trans (hgmax b0)
  have hinner : ∀ q' ν', ∑ b, g b * ‖∑ α, star (e q ν b α) * e q' ν' b α‖ ^ 2 ≤ gmax := by
    intro q' ν'
    calc ∑ b, g b * ‖∑ α, star (e q ν b α) * e q' ν' b α‖ ^ 2
        ≤ ∑ b, gmax * ((∑ α, ‖e q ν b α‖ ^ 2) * ∑ α, ‖e q' ν' b α‖ ^ 2) := by
          refine sum_le_sum fun b _ => ?_
          exact mul_le_mul (hgmax b) (overlap_sq_le _ _) (by positivity) hgm
      _ = gmax * ∑ b, (∑ α, ‖e q ν b α‖ ^ 2) * ∑ α, ‖e q' ν' b α‖ ^ 2 := by rw [mul_sum]
      _ ≤ gmax * ((∑ b, ∑ α, ‖e q ν b α‖ ^ 2) * ∑ b, ∑ α, ‖e q' ν' b α‖ ^ 2) :=
          mul_le_mul_of_nonneg_left
            (sum_mul_le_sum_mul_sum (fun _ => by positivity) (fun _ => by positivity)) hgm
      _ = gmax := by rw [hnorm, hnorm, mul_one, mul_one]
  unfold isotopeLinewidth
  have hsum : ∑ q', ∑ ν', delta (omega q ν - omega q' ν') *
        ∑ b, g b * ‖∑ α, star (e q ν b α) * e q' ν' b α‖ ^ 2 ≤
      ∑ q', ∑ ν', delta (omega q ν - omega q' ν') * gmax :=
    sum_le_sum fun q' _ => sum_le_sum fun ν' _ =>
      mul_le_mul_of_nonneg_left (hinner q' ν') (hdelta _)
  have hpref : 0 ≤ π / (4 * Fintype.card Q) * omega q ν ^ 2 :=
    mul_nonneg (div_nonneg pi_pos.le (by positivity)) (by positivity)
  calc π / (4 * Fintype.card Q) * omega q ν ^ 2 *
        ∑ q', ∑ ν', delta (omega q ν - omega q' ν') *
          ∑ b, g b * ‖∑ α, star (e q ν b α) * e q' ν' b α‖ ^ 2
      ≤ π / (4 * Fintype.card Q) * omega q ν ^ 2 *
          ∑ q', ∑ ν', delta (omega q ν - omega q' ν') * gmax :=
        mul_le_mul_of_nonneg_left hsum hpref
    _ = π / 4 * omega q ν ^ 2 * gmax *
          ((∑ q', ∑ ν', delta (omega q ν - omega q' ν')) / Fintype.card Q) := by
        simp only [← sum_mul]
        ring

end Isotope

/-! ## Three-phonon linewidth -/

section Anharmonic

variable {Q ι : Type*} [Fintype Q] [AddCommGroup Q] [Fintype ι]

private theorem pair_nonneg (delta : ℝ → ℝ) (hdelta : ∀ x, 0 ≤ delta x)
    (hmono : ∀ x y, |x| ≤ |y| → delta y ≤ delta x) {a b c nb nc V : ℝ} (ha : 0 < a)
    (hV : 0 ≤ V) (hnb : 0 < nb) (hnc : 0 < nc) (hanti : (b ≤ c → nc ≤ nb) ∧ (c ≤ b → nb ≤ nc)) :
    0 ≤ V * ((1 + nb + nc) * delta (a - b - c) + 2 * (nb - nc) * delta (a + b - c)) +
      V * ((1 + nc + nb) * delta (a - c - b) + 2 * (nc - nb) * delta (a + c - b)) := by
  have h1 : 0 ≤ (1 + nb + nc) * delta (a - b - c) := mul_nonneg (by linarith) (hdelta _)
  have h2 : 0 ≤ (1 + nc + nb) * delta (a - c - b) := mul_nonneg (by linarith) (hdelta _)
  have h3 : 0 ≤ 2 * (nb - nc) * delta (a + b - c) + 2 * (nc - nb) * delta (a + c - b) := by
    rcases le_total b c with hbc | hcb
    · have hn := hanti.1 hbc
      have hd : delta (a + c - b) ≤ delta (a + b - c) := hmono _ _ (by
        rw [abs_of_nonneg (by linarith : (0:ℝ) ≤ a + c - b)]
        exact abs_le.mpr ⟨by linarith, by linarith⟩)
      nlinarith [mul_nonneg (sub_nonneg.2 hn) (sub_nonneg.2 hd)]
    · have hn := hanti.2 hcb
      have hd : delta (a + b - c) ≤ delta (a + c - b) := hmono _ _ (by
        rw [abs_of_nonneg (by linarith : (0:ℝ) ≤ a + b - c)]
        exact abs_le.mpr ⟨by linarith, by linarith⟩)
      nlinarith [mul_nonneg (sub_nonneg.2 hn) (sub_nonneg.2 hd)]
  rw [← mul_add]
  exact mul_nonneg hV (by linarith)

private theorem sum_swap_nonneg (q : Q) (f : Q → ι → ι → ℝ)
    (h : ∀ q' ν' ν'', 0 ≤ f q' ν' ν'' + f (q - q') ν'' ν') :
    0 ≤ ∑ q', ∑ ν', ∑ ν'', f q' ν' ν'' := by
  have hre : ∑ q', ∑ ν', ∑ ν'', f q' ν' ν'' = ∑ q', ∑ ν', ∑ ν'', f (q - q') ν'' ν' := by
    rw [← Fintype.sum_equiv (Equiv.subLeft q) (fun q' => ∑ ν', ∑ ν'', f (q - q') ν' ν'')
      (fun q' => ∑ ν', ∑ ν'', f q' ν' ν'') (fun _ => rfl)]
    exact sum_congr rfl fun q' _ => sum_comm
  have h2 : 0 ≤ ∑ q', ∑ ν', ∑ ν'', f q' ν' ν'' + ∑ q', ∑ ν', ∑ ν'', f (q - q') ν'' ν' := by
    simp only [← sum_add_distrib]
    exact sum_nonneg fun q' _ => sum_nonneg fun ν' _ => sum_nonneg fun ν'' _ => h q' ν' ν''
  rw [← hre] at h2
  linarith

/-- The catalog's three-phonon linewidth with its Gaussian smearing is nonnegative. The
hypotheses are those of the catalog: a kernel `|V₃|²` symmetric under exchange of the two partner
phonons (the Maradudin-Fein form is), an even smearing kernel that does not increase with `|x|`
(Gaussian, Lorentzian, box, triangle), and positive frequencies for the mode and for every partner
the kernel couples to, so the acoustic zero modes at Γ are admissible where `|V₃|²` vanishes on
them. Pairing each term with its partner `(q', ν') ↔ (q - q', ν'')` makes the absorption part
`2 (n' - n'') [δ(ω + s) - δ(ω - s)]` with `s = ω' - ω''`, which is nonnegative. -/
theorem anharmonicLinewidth_nonneg {hbar kB T : ℝ} (hh : 0 < hbar) (hk : 0 < kB) (hT : 0 < T)
    (delta : ℝ → ℝ) (omega : Q → ι → ℝ) (V3 : Q → ι → Q → ι → Q → ι → ℝ) (q : Q) (ν : ι)
    (hω : 0 < omega q ν) (hV3 : ∀ a b c d e f, 0 ≤ V3 a b c d e f)
    (hzero : ∀ q' ν' ν'', V3 q ν q' ν' (q - q') ν'' ≠ 0 →
      0 < omega q' ν' ∧ 0 < omega (q - q') ν'')
    (hswap : ∀ q' ν' ν'', V3 q ν q' ν' (q - q') ν'' = V3 q ν (q - q') ν'' q' ν')
    (hdelta : ∀ x, 0 ≤ delta x) (hmono : ∀ x y, |x| ≤ |y| → delta y ≤ delta x) :
    0 ≤ anharmonicLinewidth hbar kB T delta omega V3 q ν := by
  have hkT : 0 < kB * T := mul_pos hk hT
  unfold anharmonicLinewidth
  apply mul_nonneg (div_nonneg pi_pos.le (by positivity))
  apply sum_swap_nonneg q
  intro q' ν' ν''
  rw [sub_sub_cancel, ← hswap q' ν' ν'']
  by_cases hV : V3 q ν q' ν' (q - q') ν'' = 0
  · rw [hV]; simp
  · obtain ⟨h1, h2⟩ := hzero q' ν' ν'' hV
    have a1 := div_pos (mul_pos hh h1) hkT
    have a2 := div_pos (mul_pos hh h2) hkT
    exact pair_nonneg delta hdelta hmono hω (hV3 _ _ _ _ _ _) (bose_pos a1) (bose_pos a2)
      ⟨fun h => bose_strictAntiOn.antitoneOn a1 a2
          (div_le_div_of_nonneg_right (mul_le_mul_of_nonneg_left h hh.le) hkT.le),
       fun h => bose_strictAntiOn.antitoneOn a2 a1
          (div_le_div_of_nonneg_right (mul_le_mul_of_nonneg_left h hh.le) hkT.le)⟩

/-- For an arbitrary nonnegative `|V₃|²` with no exchange symmetry and an arbitrary nonnegative
smearing kernel, the three-phonon linewidth is nonnegative when the kernel vanishes at signed
offsets `x > ω_qν`: an absorption term is negative only when `n' < n''`, that is `ω' > ω''`, which
puts its offset `ω + ω' - ω''` above `ω`. -/
theorem anharmonicLinewidth_nonneg_of_support {hbar kB T : ℝ} (hh : 0 < hbar) (hk : 0 < kB)
    (hT : 0 < T) (delta : ℝ → ℝ) (omega : Q → ι → ℝ) (V3 : Q → ι → Q → ι → Q → ι → ℝ)
    (q : Q) (ν : ι) (hV3 : ∀ a b c d e f, 0 ≤ V3 a b c d e f)
    (hzero : ∀ q' ν' ν'', V3 q ν q' ν' (q - q') ν'' ≠ 0 →
      0 < omega q' ν' ∧ 0 < omega (q - q') ν'')
    (hdelta : ∀ x, 0 ≤ delta x) (hsupport : ∀ x, omega q ν < x → delta x = 0) :
    0 ≤ anharmonicLinewidth hbar kB T delta omega V3 q ν := by
  have hkT : 0 < kB * T := mul_pos hk hT
  unfold anharmonicLinewidth
  apply mul_nonneg (div_nonneg pi_pos.le (by positivity))
  apply sum_nonneg; intro q' _
  apply sum_nonneg; intro ν' _
  apply sum_nonneg; intro ν'' _
  by_cases hV : V3 q ν q' ν' (q - q') ν'' = 0
  · rw [hV, zero_mul]
  obtain ⟨h1, h2⟩ := hzero q' ν' ν'' hV
  have a1 := div_pos (mul_pos hh h1) hkT
  have a2 := div_pos (mul_pos hh h2) hkT
  apply mul_nonneg (hV3 _ _ _ _ _ _)
  apply add_nonneg
  · exact mul_nonneg (by linarith [bose_pos a1, bose_pos a2]) (hdelta _)
  · by_cases hzero' : delta (omega q ν + omega q' ν' - omega (q - q') ν'') = 0
    · rw [hzero', mul_zero]
    · have hle : omega q ν + omega q' ν' - omega (q - q') ν'' ≤ omega q ν := by
        by_contra hfar; exact hzero' (hsupport _ (not_le.mp hfar))
      have hlt : omega q' ν' ≤ omega (q - q') ν'' := by linarith
      have hmono : bose (hbar * omega (q - q') ν'' / (kB * T)) ≤
          bose (hbar * omega q' ν' / (kB * T)) :=
        bose_strictAntiOn.antitoneOn a1 a2
          (div_le_div_of_nonneg_right (mul_le_mul_of_nonneg_left hlt hh.le) hkT.le)
      exact mul_nonneg (by linarith) (hdelta _)

/-- The monotonicity of the smearing kernel is needed even with exchange symmetry and an even
kernel. On a one-point mesh with branch frequencies `1`, `2` and `4`, a symmetric `|V₃|²` coupling
the branches `2` and `4` and an even kernel with weight only at `|x| = 3` give a negative
linewidth for the first branch, `π (n(4) - n(2)) < 0`. -/
theorem anharmonicLinewidth_neg_of_nonmonotone :
    ∃ (delta : ℝ → ℝ) (omega : Unit → Fin 3 → ℝ)
      (V3 : Unit → Fin 3 → Unit → Fin 3 → Unit → Fin 3 → ℝ),
      (∀ x, 0 ≤ delta x) ∧ (∀ x, delta (-x) = delta x) ∧ (∀ q ν, 0 < omega q ν) ∧
        (∀ a b c d e f, 0 ≤ V3 a b c d e f) ∧
        (∀ q' ν' ν'', V3 () 0 q' ν' (() - q') ν'' = V3 () 0 (() - q') ν'' q' ν') ∧
        anharmonicLinewidth 1 1 1 delta omega V3 () 0 < 0 := by
  refine ⟨fun x => if |x| = 3 then 1 else 0, fun _ ν => if ν = 0 then 1 else if ν = 1 then 2 else 4,
    fun _ _ _ ν' _ ν'' => if (ν' = 1 ∧ ν'' = 2) ∨ (ν' = 2 ∧ ν'' = 1) then 1 else 0,
    ?_, ?_, ?_, ?_, ?_, ?_⟩
  · intro x; dsimp only; split_ifs <;> norm_num
  · intro x; dsimp only; rw [abs_neg]
  · intro _ ν; dsimp only; split_ifs <;> norm_num
  · intro _ _ _ _ _ _; dsimp only; split_ifs <;> norm_num
  · intro _ ν' ν''; dsimp only
    split_ifs <;> first | rfl | (exfalso; tauto)
  · have hmono : bose 4 < bose 2 := bose_strictAntiOn (by norm_num) (by norm_num) (by norm_num)
    unfold anharmonicLinewidth
    simp only [Fintype.card_unit, Fin.sum_univ_three, Finset.univ_unique, Finset.sum_singleton,
      Fin.isValue]
    norm_num [abs_of_pos, abs_of_neg]
    nlinarith [pi_pos, hmono]

end Anharmonic

/-! ## Boundary scattering and the relaxation-time mean free path -/

/-- The Euclidean length of a mean free displacement or a velocity. -/
def norm3 (u : Fin 3 → ℝ) : ℝ := √(∑ α, u α ^ 2)

theorem norm3_rtaDisplacement (v : Fin 3 → ℝ) {Γ : ℝ} (hΓ : 0 < Γ) :
    norm3 (rtaDisplacement v Γ) = norm3 v / (2 * Γ) := by
  unfold norm3 rtaDisplacement
  have h2 : 0 < 2 * Γ := by linarith
  rw [show (∑ α, (v α / (2 * Γ)) ^ 2) = (∑ α, v α ^ 2) / (2 * Γ) ^ 2 by
    rw [sum_div]; exact sum_congr rfl fun α _ => by rw [div_pow]]
  rw [sqrt_div' _ (by positivity), sqrt_sq h2.le]

/-- Casimir bound: with the boundary channel present and the other channels nonnegative, the
relaxation-time mean free displacement of a moving mode never exceeds the boundary length, and
it equals it exactly when the anharmonic and isotope channels vanish. -/
theorem rta_casimir_bound (v : Fin 3 → ℝ) {L anh iso : ℝ} (hL : 0 < L) (hv : 0 < norm3 v)
    (hanh : 0 ≤ anh) (hiso : 0 ≤ iso) :
    norm3 (rtaDisplacement v (totalLinewidth anh iso (boundaryLinewidth v L))) ≤ L ∧
      (norm3 (rtaDisplacement v (totalLinewidth anh iso (boundaryLinewidth v L))) = L ↔
        anh + iso = 0) := by
  have hb : boundaryLinewidth v L = norm3 v / (2 * L) := rfl
  have hbpos : 0 < norm3 v / (2 * L) := div_pos hv (by linarith)
  have hΓ : 0 < totalLinewidth anh iso (boundaryLinewidth v L) := by
    unfold totalLinewidth; rw [hb]; linarith
  rw [norm3_rtaDisplacement v hΓ]
  unfold totalLinewidth
  rw [hb]
  have hden : 0 < 2 * (anh + iso + norm3 v / (2 * L)) := by linarith
  have key : norm3 v / (2 * (anh + iso + norm3 v / (2 * L))) =
      L * norm3 v / (2 * L * (anh + iso) + norm3 v) := by
    field_simp
  rw [key]
  have hden2 : 0 < 2 * L * (anh + iso) + norm3 v := by nlinarith
  constructor
  · rw [div_le_iff₀ hden2]
    nlinarith [mul_nonneg (mul_nonneg hL.le hL.le) (add_nonneg hanh hiso)]
  · rw [div_eq_iff hden2.ne']
    constructor
    · intro h
      have h2 : L * L * (anh + iso) = 0 := by linear_combination (-1 / 2 : ℝ) * h
      exact (mul_eq_zero.mp h2).resolve_left (by positivity)
    · intro h; rw [h]; ring

end OMAI.PhyslibBridge.PhononScattering
