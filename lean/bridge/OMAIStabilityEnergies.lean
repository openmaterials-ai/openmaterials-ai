module

public import Mathlib.Analysis.SpecialFunctions.Integrals.Basic
public import Mathlib.MeasureTheory.Integral.DivergenceTheorem
public import Mathlib.MeasureTheory.Integral.IntervalIntegral.FundThmCalculus
public import Mathlib.Tactic

/-!
# Energy differences of the stability domain

The catalog's stability producers are energy differences over ground-state total
energies: a per-atom distance above the convex hull of competing phases, a reaction
energy, an adsorption energy, an average intercalation voltage, and surface and
grain-boundary energies from slab supercells. Physlib has no model of these
constructions, so these results use Mathlib only and identify no Physlib declaration.

The hull distance does not change when every entry's formation energy is shifted by the
same affine function of composition; in particular the hull distance of per-atom formation
energies does not depend on the elemental reference energies. A supporting affine function
certifies a zero distance. A linear combination of cell energies is unchanged by every
per-element energy offset exactly when it conserves atoms, which for the catalog's adsorption
and voltage formulas is the balance of the cells. The average intercalation voltage is the
mean of the open-circuit voltage profile over the ion content, also for a cell energy with
kinks between voltage plateaus. For slab energies affine in the number of bulk units, the
catalog's surface and grain-boundary energies are independent of slab thickness exactly when
the bulk reference equals the slab slope, and grow without bound otherwise.
-/

@[expose] public section

noncomputable section

open Finset Filter
open scoped Topology

namespace OMAI.PhyslibBridge.Stability

/-! ## Catalog transcriptions -/

/-- The reviewed catalog expression of `compute_surface_energy`,
`gamma = (-N E_bulk + E_slab) / (2 A)`, with `E_slab` and `E_bulk` the slab and per-unit
bulk energies. This definition alone is not a physical proof. -/
def surfaceEnergy (Eslab Ebulk N A : ℝ) : ℝ := (-N * Ebulk + Eslab) / (2 * A)

/-- The reviewed catalog expression of `compute_grain_boundary_energy`,
`gamma_GB = (-N E_bulk + E_GB) / (2 A)`. This definition alone is not a physical proof. -/
def grainBoundaryEnergy (EGB Ebulk N A : ℝ) : ℝ := (-N * Ebulk + EGB) / (2 * A)

/-- The reviewed catalog expression of `compute_intercalation_voltage`,
`V = (mu n + E_empty - E_full) / (n q)`. This definition alone is not a physical proof. -/
def intercalationVoltage (Efull Eempty n mu q : ℝ) : ℝ := (mu * n + Eempty - Efull) / (n * q)

/-- The reviewed catalog expression of `compute_adsorption_energy`,
`E_ads = E_adslab - E_adsorbate - E_slab`. This definition alone is not a physical
proof. -/
def adsorptionEnergy (Eadslab Eslab Eadsorbate : ℝ) : ℝ := Eadslab - Eadsorbate - Eslab

/-- The reviewed catalog expression of `compute_reaction_energy`,
`dE_rxn = sum_i H_f[i] c_rxn[i]` over the reaction species. This definition alone is not
a physical proof. -/
def reactionEnergy {ι : Type*} [Fintype ι] (c h : ι → ℝ) : ℝ := ∑ i, h i * c i

/-- Per-atom formation energy `(E - sum_a n_a mu_a) / sum_a n_a` of a cell with `n_a`
atoms of element `a`, total energy `E` and elemental reference energies `mu_a`. -/
def formationEnergy {E : Type*} [Fintype E] (Etot : ℝ) (n mu : E → ℝ) : ℝ :=
  (Etot - ∑ a, n a * mu a) / ∑ a, n a

/-! ## Convex hull of competing phases -/

variable {ι κ : Type*} [Fintype ι] [Fintype κ]

/-- `w` decomposes the composition `y` into the competing entries `S` with atomic
fractions `x`: nonnegative weights supported on `S` that sum to one and reproduce `y`. -/
def Decomposition (S : Set ι) (x : ι → κ → ℝ) (y : κ → ℝ) (w : ι → ℝ) : Prop :=
  (∀ j, 0 ≤ w j) ∧ (∀ j, j ∉ S → w j = 0) ∧ ∑ j, w j = 1 ∧ ∀ a, ∑ j, w j * x j a = y a

/-- Per-atom energies of every decomposition of `y` into the competing entries `S`. -/
def decompositionEnergies (S : Set ι) (x : ι → κ → ℝ) (h : ι → ℝ) (y : κ → ℝ) : Set ℝ :=
  {e | ∃ w, Decomposition S x y w ∧ e = ∑ j, w j * h j}

/-- The lower convex hull of the competing entries `S` at composition `y`. -/
def hullEnergy (S : Set ι) (x : ι → κ → ℝ) (h : ι → ℝ) (y : κ → ℝ) : ℝ :=
  sInf (decompositionEnergies S x h y)

/-- Interpreted definition of the catalog's opaque producer `compute_energy_above_hull`:
the per-atom distance of entry `i`'s formation energy above the lower convex hull of the
competing entries `S`. This definition alone is not a physical proof. -/
def energyAboveHull (S : Set ι) (x : ι → κ → ℝ) (h : ι → ℝ) (i : ι) : ℝ :=
  h i - hullEnergy S x h (x i)

omit [Fintype κ] in
private theorem self_mem_decompositionEnergies {S : Set ι} {x : ι → κ → ℝ} {h : ι → ℝ} {i : ι}
    (hi : i ∈ S) : h i ∈ decompositionEnergies S x h (x i) := by
  classical
  refine ⟨Pi.single i 1, ⟨fun j => ?_, fun j hj => ?_, ?_, fun a => ?_⟩, ?_⟩
  · by_cases hji : j = i <;> simp [hji]
  · have : j ≠ i := fun h' => hj (h' ▸ hi)
    simp [this]
  · simp
  · simp [Pi.single_apply]
  · simp [Pi.single_apply]

omit [Fintype κ] in
private theorem decompositionEnergies_bddBelow (S : Set ι) (x : ι → κ → ℝ) (h : ι → ℝ)
    (y : κ → ℝ) : BddBelow (decompositionEnergies S x h y) := by
  refine ⟨-∑ k, |h k|, ?_⟩
  rintro e ⟨w, ⟨hw0, -, hw1, -⟩, rfl⟩
  have hb : ∀ j, -(∑ k, |h k|) ≤ h j := fun j =>
    (neg_le_neg (single_le_sum (fun k _ => abs_nonneg (h k)) (mem_univ j))).trans
      (neg_abs_le (h j))
  calc -∑ k, |h k| = ∑ j, w j * -(∑ k, |h k|) := by rw [← sum_mul, hw1, one_mul]
    _ ≤ ∑ j, w j * h j := sum_le_sum fun j _ => mul_le_mul_of_nonneg_left (hb j) (hw0 j)

omit [Fintype κ] in
/-- Every competing entry lies on or above the convex hull of its competitors. -/
theorem energyAboveHull_nonneg {S : Set ι} (x : ι → κ → ℝ) (h : ι → ℝ) {i : ι} (hi : i ∈ S) :
    0 ≤ energyAboveHull S x h i :=
  sub_nonneg.mpr (csInf_le (decompositionEnergies_bddBelow S x h (x i))
    (self_mem_decompositionEnergies hi))

private theorem decomposition_affine {S : Set ι} {x : ι → κ → ℝ} {y : κ → ℝ} {w : ι → ℝ}
    (hw : Decomposition S x y w) (h : ι → ℝ) (c : ℝ) (δ : κ → ℝ) :
    ∑ j, w j * (h j + (c + ∑ a, δ a * x j a)) = ∑ j, w j * h j + (c + ∑ a, δ a * y a) := by
  obtain ⟨-, -, hw1, hwy⟩ := hw
  simp only [mul_add, sum_add_distrib, mul_sum]
  congr 1
  rw [← sum_mul, hw1, one_mul]
  congr 1
  rw [sum_comm]
  refine sum_congr rfl fun a _ => ?_
  rw [← hwy a, mul_sum]
  exact sum_congr rfl fun j _ => by ring

/-- Shifting every entry's formation energy by the same affine function of composition,
`h_j + c + sum_a delta_a x_ja`, leaves the hull distance of every competing entry
unchanged. Changing the elemental reference energies of the formation energies is such a
shift, so the catalog's hull distance does not depend on the reference set. -/
theorem energyAboveHull_affine_invariant {S : Set ι} (x : ι → κ → ℝ) (h : ι → ℝ) (c : ℝ)
    (δ : κ → ℝ) {i : ι} (hi : i ∈ S) :
    energyAboveHull S x (fun j => h j + (c + ∑ a, δ a * x j a)) i = energyAboveHull S x h i := by
  set ℓ := c + ∑ a, δ a * x i a
  have hne : (decompositionEnergies S x h (x i)).Nonempty := ⟨_, self_mem_decompositionEnergies hi⟩
  have hne' : (decompositionEnergies S x (fun j => h j + (c + ∑ a, δ a * x j a)) (x i)).Nonempty :=
    ⟨_, self_mem_decompositionEnergies hi⟩
  have hbdd := decompositionEnergies_bddBelow S x h (x i)
  have hbdd' := decompositionEnergies_bddBelow S x (fun j => h j + (c + ∑ a, δ a * x j a)) (x i)
  have hhull : hullEnergy S x (fun j => h j + (c + ∑ a, δ a * x j a)) (x i) =
      hullEnergy S x h (x i) + ℓ := by
    apply le_antisymm
    · have : hullEnergy S x (fun j => h j + (c + ∑ a, δ a * x j a)) (x i) - ℓ ≤
          hullEnergy S x h (x i) := by
        apply le_csInf hne
        rintro e ⟨w, hw, rfl⟩
        rw [sub_le_iff_le_add]
        exact csInf_le hbdd' ⟨w, hw, (decomposition_affine hw h c δ).symm⟩
      linarith
    · have : hullEnergy S x h (x i) ≤
          hullEnergy S x (fun j => h j + (c + ∑ a, δ a * x j a)) (x i) - ℓ := by
        apply le_sub_iff_add_le.mpr
        apply le_csInf hne'
        rintro e ⟨w, hw, rfl⟩
        rw [decomposition_affine hw h c δ]
        have := csInf_le hbdd ⟨w, hw, rfl⟩
        unfold hullEnergy
        linarith
      linarith
  unfold energyAboveHull
  rw [hhull]
  ring

/-- The hull distance of per-atom formation energies `(E_j - sum_a n_ja mu_a) / N_j`, with
atomic fractions `n_ja / N_j`, is the same for every set of elemental reference energies
`mu`. -/
theorem energyAboveHull_formationEnergy_reference_independent (S : Set ι) (Ecell : ι → ℝ)
    (n : ι → κ → ℝ) (hN : ∀ j, ∑ a, n j a ≠ 0) {i : ι} (hi : i ∈ S) (μ μ' : κ → ℝ) :
    energyAboveHull S (fun j a => n j a / ∑ b, n j b) (fun j => formationEnergy (Ecell j) (n j) μ') i =
      energyAboveHull S (fun j a => n j a / ∑ b, n j b) (fun j => formationEnergy (Ecell j) (n j) μ) i := by
  have hshift : (fun j => formationEnergy (Ecell j) (n j) μ') =
      fun j => formationEnergy (Ecell j) (n j) μ +
        (0 + ∑ a, (μ a - μ' a) * (n j a / ∑ b, n j b)) := by
    funext j
    unfold formationEnergy
    have hNj := hN j
    rw [zero_add, div_add' _ _ _ hNj]
    congr 1
    have : (∑ a, (μ a - μ' a) * (n j a / ∑ b, n j b)) * ∑ b, n j b = ∑ a, (μ a - μ' a) * n j a := by
      rw [sum_mul]
      exact sum_congr rfl fun a _ => by field_simp
    rw [this]
    simp only [sub_mul, sum_sub_distrib]
    have e1 : ∑ a, μ a * n j a = ∑ a, n j a * μ a := sum_congr rfl fun a _ => mul_comm _ _
    have e2 : ∑ a, μ' a * n j a = ∑ a, n j a * μ' a := sum_congr rfl fun a _ => mul_comm _ _
    rw [e1, e2]
    ring
  rw [hshift]
  exact energyAboveHull_affine_invariant _ _ 0 _ hi

omit [Fintype κ] in
/-- Adding competing phases can only lower the hull, so the hull distance of an entry
against a larger competing set is at least its distance against a smaller one. -/
theorem energyAboveHull_mono_competitors {S S' : Set ι} (hSS' : S ⊆ S') (x : ι → κ → ℝ)
    (h : ι → ℝ) {i : ι} (hi : i ∈ S) :
    energyAboveHull S x h i ≤ energyAboveHull S' x h i := by
  unfold energyAboveHull hullEnergy
  have hsub : decompositionEnergies S x h (x i) ⊆ decompositionEnergies S' x h (x i) := by
    rintro e ⟨w, ⟨hw0, hwS, hw1, hwy⟩, rfl⟩
    exact ⟨w, ⟨hw0, fun j hj => hwS j fun h' => hj (hSS' h'), hw1, hwy⟩, rfl⟩
  have := csInf_le_csInf (decompositionEnergies_bddBelow S' x h (x i))
    ⟨_, self_mem_decompositionEnergies hi⟩ hsub
  linarith

/-- An affine function of composition that lies on or below every competitor's formation
energy and touches entry `i` certifies that `i` is on the hull: its distance is zero. -/
theorem energyAboveHull_eq_zero_of_supporting {S : Set ι} (x : ι → κ → ℝ) (h : ι → ℝ)
    {i : ι} (hi : i ∈ S) (c : ℝ) (δ : κ → ℝ) (hle : ∀ j ∈ S, c + ∑ a, δ a * x j a ≤ h j)
    (heq : c + ∑ a, δ a * x i a = h i) : energyAboveHull S x h i = 0 := by
  apply le_antisymm _ (energyAboveHull_nonneg x h hi)
  unfold energyAboveHull hullEnergy
  rw [sub_nonpos]
  apply le_csInf ⟨_, self_mem_decompositionEnergies hi⟩
  rintro e ⟨w, ⟨hw0, hwS, hw1, hwy⟩, rfl⟩
  have hsupp : ∀ j, w j * (c + ∑ a, δ a * x j a) ≤ w j * h j := fun j => by
    by_cases hj : j ∈ S
    · exact mul_le_mul_of_nonneg_left (hle j hj) (hw0 j)
    · simp [hwS j hj]
  calc h i = c + ∑ a, δ a * x i a := heq.symm
    _ = ∑ j, w j * (c + ∑ a, δ a * x j a) := by
      have := decomposition_affine (h := fun _ => 0) ⟨hw0, hwS, hw1, hwy⟩ c δ
      simpa using this.symm
    _ ≤ ∑ j, w j * h j := sum_le_sum fun j _ => hsupp j

/-! ## Per-element reference offsets and atom balance -/

/-- A linear combination `sum_i nu_i E_i` of cell energies is unchanged by every per-element
energy offset `E_i + sum_a n_ia delta_a` exactly when it conserves every element. -/
theorem combination_offset_invariant_iff {σ E : Type*} [Fintype σ] [Fintype E] [DecidableEq E]
    (ν Ecell : σ → ℝ) (n : σ → E → ℝ) :
    (∀ δ : E → ℝ, ∑ s, ν s * (Ecell s + ∑ a, n s a * δ a) = ∑ s, ν s * Ecell s) ↔
      ∀ a, ∑ s, ν s * n s a = 0 := by
  have hexp : ∀ δ : E → ℝ, ∑ s, ν s * (Ecell s + ∑ a, n s a * δ a) =
      ∑ s, ν s * Ecell s + ∑ a, δ a * ∑ s, ν s * n s a := by
    intro δ
    simp only [mul_add, sum_add_distrib, mul_sum]
    congr 1
    rw [sum_comm]
    exact sum_congr rfl fun a _ => sum_congr rfl fun s _ => by ring
  constructor
  · intro hinv a
    have := hinv (Pi.single a 1)
    rw [hexp] at this
    simpa [Pi.single_apply] using this
  · intro hbal δ
    rw [hexp]
    simp [hbal]

/-- The catalog's reaction energy, summed over per-atom formation energies with weights
`c_i = nu_i N_i` (balancing coefficients times atoms per formula unit), equals the
reaction energy `sum_i nu_i E_i` of the cell energies for every choice of elemental
reference energies exactly when the reaction is balanced. With unbalanced coefficients it
depends on the references. -/
theorem reactionEnergy_reference_independent_iff {σ E : Type*} [Fintype σ] [Fintype E]
    [DecidableEq E] (ν Ecell : σ → ℝ) (n : σ → E → ℝ) (hN : ∀ s, ∑ a, n s a ≠ 0) :
    (∀ μ : E → ℝ, reactionEnergy (fun s => ν s * ∑ a, n s a)
        (fun s => formationEnergy (Ecell s) (n s) μ) = ∑ s, ν s * Ecell s) ↔
      ∀ a, ∑ s, ν s * n s a = 0 := by
  have hred : ∀ μ : E → ℝ, reactionEnergy (fun s => ν s * ∑ a, n s a)
      (fun s => formationEnergy (Ecell s) (n s) μ) =
        ∑ s, ν s * (Ecell s + ∑ a, n s a * (-μ a)) := by
    intro μ
    unfold reactionEnergy formationEnergy
    refine sum_congr rfl fun s _ => ?_
    field_simp [hN s]
    simp only [sum_neg_distrib]
    ring
  rw [← combination_offset_invariant_iff ν Ecell n]
  constructor
  · intro h δ
    have := h (fun a => -δ a)
    rw [hred] at this
    simpa using this
  · intro h μ
    rw [hred]
    exact h _

/-- The catalog's adsorption energy is unchanged by every per-element energy offset of the
three cells exactly when the adsorbate-on-slab cell contains the slab's atoms plus the
adsorbate's. -/
theorem adsorptionEnergy_offset_invariant_iff {E : Type*} [Fintype E] [DecidableEq E]
    (Eadslab Eslab Eadsorbate : ℝ) (nAdslab nSlab nAdsorbate : E → ℝ) :
    (∀ δ : E → ℝ, adsorptionEnergy (Eadslab + ∑ a, nAdslab a * δ a) (Eslab + ∑ a, nSlab a * δ a)
        (Eadsorbate + ∑ a, nAdsorbate a * δ a) = adsorptionEnergy Eadslab Eslab Eadsorbate) ↔
      nAdslab = nSlab + nAdsorbate := by
  have key := combination_offset_invariant_iff (σ := Fin 3) ![1, -1, -1]
    ![Eadslab, Eslab, Eadsorbate] ![nAdslab, nSlab, nAdsorbate]
  simp only [Fin.sum_univ_three, Matrix.cons_val_zero, Matrix.cons_val_one, Matrix.cons_val_two,
    Matrix.head_cons, Matrix.tail_cons, one_mul, neg_one_mul] at key
  unfold adsorptionEnergy
  constructor
  · intro h
    funext a
    have := key.mp (fun δ => by have := h δ; linarith) a
    simp only [Pi.add_apply]
    linarith
  · intro hn δ
    have := key.mpr (fun a => by rw [hn]; simp only [Pi.add_apply]; ring) δ
    linarith

/-- The catalog's average intercalation voltage is unchanged by every per-element energy
offset of the two cells, with the working-ion reservoir energy offset by that element's
offset, exactly when the intercalated cell contains the host's atoms plus `n` working ions. -/
theorem intercalationVoltage_offset_invariant_iff {E : Type*} [Fintype E] [DecidableEq E]
    (Efull Eempty n mu q : ℝ) (hn : n ≠ 0) (hq : q ≠ 0) (ion : E) (nFull nEmpty : E → ℝ) :
    (∀ δ : E → ℝ, intercalationVoltage (Efull + ∑ a, nFull a * δ a)
        (Eempty + ∑ a, nEmpty a * δ a) n (mu + δ ion) q = intercalationVoltage Efull Eempty n mu q) ↔
      nFull = nEmpty + n • Pi.single ion 1 := by
  have key := combination_offset_invariant_iff (σ := Fin 3) ![-1, 1, n] ![Efull, Eempty, mu]
    ![nFull, nEmpty, Pi.single ion 1]
  simp only [Fin.sum_univ_three, Matrix.cons_val_zero, Matrix.cons_val_one, Matrix.cons_val_two,
    Matrix.head_cons, Matrix.tail_cons, neg_one_mul, one_mul] at key
  have hion : ∀ δ : E → ℝ, ∑ a, (Pi.single ion (1 : ℝ) : E → ℝ) a * δ a = δ ion := by
    intro δ; simp [Pi.single_apply]
  simp only [hion] at key
  unfold intercalationVoltage
  have hnq : n * q ≠ 0 := mul_ne_zero hn hq
  constructor
  · intro h
    funext a
    have := key.mp (fun δ => by
      have hδ := h δ
      rw [div_eq_div_iff hnq hnq] at hδ
      have := mul_right_cancel₀ hnq hδ
      linarith) a
    simp only [Pi.add_apply, Pi.smul_apply, smul_eq_mul]
    linarith
  · intro hfull δ
    have := key.mpr (fun a => by
      rw [hfull]; simp only [Pi.add_apply, Pi.smul_apply, smul_eq_mul]; ring) δ
    congr 1
    linarith

/-! ## Average voltage and open-circuit voltage profile -/

/-- If the cell energy `E(x)` is continuous in the ion content `x` on `[0, n]` and has
derivative `E'(x)` off a countable set, as the convex-hull energy of a multi-plateau electrode
does, the catalog's average intercalation voltage between the empty (`x = 0`) and full
(`x = n`) cells is the mean over `[0, n]` of the open-circuit voltage profile
`V(x) = (mu - E'(x)) / q`. -/
theorem intercalationVoltage_eq_mean_ocv {Ecell E' : ℝ → ℝ} {n mu q : ℝ} {s : Set ℝ}
    (hs : s.Countable) (hc : ContinuousOn Ecell (Set.uIcc 0 n))
    (hderiv : ∀ x ∈ Set.Ioo (min 0 n) (max 0 n) \ s, HasDerivAt Ecell (E' x) x)
    (hint : IntervalIntegrable E' MeasureTheory.volume 0 n) :
    intercalationVoltage (Ecell n) (Ecell 0) n mu q =
      (∫ x in (0 : ℝ)..n, (mu - E' x) / q) / n := by
  have hftc := MeasureTheory.integral_eq_of_hasDerivAt_off_countable Ecell E' hs hc hderiv hint
  have hsplit : ∫ x in (0 : ℝ)..n, (mu - E' x) / q = (mu * n - (Ecell n - Ecell 0)) / q := by
    simp only [div_eq_mul_inv]
    rw [intervalIntegral.integral_mul_const, intervalIntegral.integral_sub intervalIntegrable_const hint,
      intervalIntegral.integral_const, hftc, smul_eq_mul, sub_zero]
    ring
  rw [hsplit]
  unfold intercalationVoltage
  rw [div_div]
  congr 1
  · ring
  · ring

/-! ## Slab-thickness dependence of surface and grain-boundary energies -/

/-- For slab energies `N e + c` affine in the number `N` of bulk units, the catalog's
surface energy with bulk reference `E_bulk` is the same for two different thicknesses
exactly when `E_bulk = e`, and is then `c / (2 A)`; otherwise it grows without bound with
the slab thickness. -/
theorem surfaceEnergy_thickness_independent_iff {e c Ebulk A : ℝ} (hA : A ≠ 0) :
    ((∀ N M : ℝ, surfaceEnergy (N * e + c) Ebulk N A = surfaceEnergy (M * e + c) Ebulk M A) ↔
        Ebulk = e) ∧
      (Ebulk = e → ∀ N, surfaceEnergy (N * e + c) Ebulk N A = c / (2 * A)) ∧
      (Ebulk ≠ e → Tendsto (fun N : ℝ => |surfaceEnergy (N * e + c) Ebulk N A|) atTop atTop) := by
  have hform : ∀ N, surfaceEnergy (N * e + c) Ebulk N A = c / (2 * A) + N * ((e - Ebulk) / (2 * A)) := by
    intro N; unfold surfaceEnergy; field_simp; ring
  refine ⟨⟨fun h => ?_, fun h N M => ?_⟩, fun h N => ?_, fun h => ?_⟩
  · have := h 0 1
    rw [hform, hform] at this
    have h2A : (2 * A) ≠ 0 := mul_ne_zero two_ne_zero hA
    have : (e - Ebulk) / (2 * A) = 0 := by linarith
    rcases div_eq_zero_iff.mp this with h' | h'
    · linarith
    · exact absurd h' h2A
  · rw [hform, hform, h]; simp
  · rw [hform, h]; simp
  · have hk : (e - Ebulk) / (2 * A) ≠ 0 := div_ne_zero (sub_ne_zero.mpr (Ne.symm h)) (mul_ne_zero two_ne_zero hA)
    simp only [hform]
    have hlin : Tendsto (fun N : ℝ => |N| * |(e - Ebulk) / (2 * A)| - |c / (2 * A)|) atTop atTop := by
      apply tendsto_atTop_add_const_right
      apply Tendsto.atTop_mul_const (abs_pos.mpr hk)
      exact tendsto_abs_atTop_atTop
    refine tendsto_atTop_mono (fun N => ?_) hlin
    have h1 := abs_sub_abs_le_abs_sub (N * ((e - Ebulk) / (2 * A))) (-(c / (2 * A)))
    rw [abs_neg, sub_neg_eq_add, add_comm, abs_mul] at h1
    exact h1

/-- The catalog's grain-boundary energy is the same slab-difference function as its surface
energy, so the thickness criterion above applies to it unchanged. -/
theorem grainBoundaryEnergy_eq_surfaceEnergy : grainBoundaryEnergy = surfaceEnergy := rfl

end OMAI.PhyslibBridge.Stability
