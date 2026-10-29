module

public import Mathlib.Analysis.Calculus.Deriv.Inv
public import Mathlib.Analysis.Calculus.Deriv.MeanValue
public import Mathlib.Analysis.Convex.Deriv
public import Mathlib.Analysis.Calculus.LocalExtr.Basic
public import Mathlib.Analysis.Convex.Jensen
public import Mathlib.Topology.Order.IntermediateValue
public import Mathlib.Tactic

/-!
# CALPHAD equilibrium thermodynamics

The catalog's thermochemistry producers are outputs of a Gibbs-energy minimization over an
assessed database: the equilibrium molar Gibbs energy, its enthalpy and entropy channels,
chemical potentials, phase fractions and transition temperatures. They are opaque solver
calls in the catalog. Each gets an interpreted definition from molar Gibbs functions of
the assessed phases, per mole of atoms at fixed pressure, and Physlib has no model of
these constructions, so these results use Mathlib only.

For a binary system the equilibrium molar Gibbs energy, the least energy of any finite
mixture of phases with the overall composition, is the convex envelope of the phase Gibbs
curves: convex in composition, below every phase curve, and above every convex function
below them. If every phase's Gibbs function is concave in temperature, the equilibrium
Gibbs energy at fixed composition is concave in temperature, so its entropy is
nondecreasing and, at nonnegative temperature, its enthalpy is nondecreasing, through
every phase transition. At a two-phase minimum with interior compositions both
differentiable phase curves share the common tangent, so the chemical potentials agree.
Mass balance fixes the phase fractions to the lever rule. For a unary system or a
congruent transformation, a Gibbs-energy difference that changes sign with a positive
entropy difference has exactly one transition temperature, where the stable phase
switches.
-/

@[expose] public section

noncomputable section

open Finset Filter Set
open scoped Topology

namespace OMAI.PhyslibBridge.Calphad

/-! ## Interpreted definitions of the catalog producers -/

/-- Energies of the finite mixtures of phases, each phase `p` with molar Gibbs function
`g p` of the mole fraction of the second component, whose overall composition is `x`. -/
def mixtureEnergies {P : Type*} (g : P → ℝ → ℝ) (x : ℝ) : Set ℝ :=
  {e | ∃ (m : ℕ) (w : Fin m → ℝ) (p : Fin m → P) (y : Fin m → ℝ), (∀ j, 0 ≤ w j) ∧
    (∀ j, y j ∈ Icc (0 : ℝ) 1) ∧ ∑ j, w j = 1 ∧ ∑ j, w j * y j = x ∧
    e = ∑ j, w j * g (p j) (y j)}

/-- Interpreted definition of the catalog's opaque producer `solve_equilibrium`: the least
molar Gibbs energy of any mixture of the assessed phases with overall composition `x`, at
the temperature and pressure built into `g`. This definition alone is not a physical
proof. -/
def equilibriumGibbs {P : Type*} (g : P → ℝ → ℝ) (x : ℝ) : ℝ := sInf (mixtureEnergies g x)

/-- Interpreted definition of the catalog's opaque producer `compute_molar_enthalpy`,
`H = G - T dG/dT` with the right derivative in temperature, the enthalpy of the state stable
just above `T` (it is `G - T G'` wherever `G` is differentiable). This definition alone is
not a physical proof. -/
def molarEnthalpy (G : ℝ → ℝ) (T : ℝ) : ℝ := G T - T * derivWithin G (Ioi T) T

/-- Interpreted definition of the catalog's opaque producer `compute_calphad_entropy`,
`S = -dG/dT` with the right derivative in temperature, the entropy of the state stable just
above `T` (it is `-G'` wherever `G` is differentiable). This definition alone is not a
physical proof. -/
def calphadEntropy (G : ℝ → ℝ) (T : ℝ) : ℝ := -derivWithin G (Ioi T) T

/-- The equilibrium molar Gibbs energy at fixed composition `x` as a function of temperature,
for phase Gibbs functions `gT T p y`. -/
def equilibriumGibbsT {P : Type*} (gT : ℝ → P → ℝ → ℝ) (x T : ℝ) : ℝ := equilibriumGibbs (gT T) x

/-- Interpreted definition of the catalog's opaque producer `compute_chemical_potentials`
for a binary system: the intercepts at `x = 0` and `x = 1` of the tangent to the molar
Gibbs function `G` at composition `x`. This definition alone is not a physical proof. -/
def chemicalPotentials (G : ℝ → ℝ) (x : ℝ) : Fin 2 → ℝ :=
  ![G x - x * deriv G x, G x + (1 - x) * deriv G x]

/-- Interpreted definition of the catalog's opaque producer `compute_phase_fractions` for
two phases of compositions `x1` and `x2` at overall composition `x`: the lever rule. This
definition alone is not a physical proof. -/
def leverFractions (x1 x2 x : ℝ) : Fin 2 → ℝ := ![(x2 - x) / (x2 - x1), (x - x1) / (x2 - x1)]

/-- Interpreted definition of the catalog's opaque producer `compute_transition_temperature`:
the lowest temperature in `[T1, T2]` at which phase `beta` is at least as stable as phase
`alpha`, with `dG = G_beta - G_alpha`. This definition alone is not a physical proof. -/
def transitionTemperature (dG : ℝ → ℝ) (T1 T2 : ℝ) : ℝ := sInf {T | T ∈ Icc T1 T2 ∧ dG T ≤ 0}

/-! ## The equilibrium Gibbs energy is the convex envelope of the phase curves -/

section Envelope

variable {P : Type*} {g : P → ℝ → ℝ}

private theorem single_mem (p : P) {x : ℝ} (hx : x ∈ Icc (0 : ℝ) 1) : g p x ∈ mixtureEnergies g x :=
  ⟨1, fun _ => 1, fun _ => p, fun _ => x, fun _ => zero_le_one, fun _ => hx, by simp, by simp,
    by simp⟩

private theorem mixtureEnergies_bddBelow {B : ℝ} (hB : ∀ p y, y ∈ Icc (0 : ℝ) 1 → B ≤ g p y)
    (x : ℝ) : BddBelow (mixtureEnergies g x) := by
  refine ⟨B, ?_⟩
  rintro e ⟨m, w, p, y, hw0, hy, hw1, -, rfl⟩
  calc B = ∑ j, w j * B := by rw [← sum_mul, hw1, one_mul]
    _ ≤ ∑ j, w j * g (p j) (y j) := sum_le_sum fun j _ => mul_le_mul_of_nonneg_left
        (hB _ _ (hy j)) (hw0 j)

private theorem mixture_combine {x x' a b e e' : ℝ} (ha : 0 ≤ a) (hb : 0 ≤ b) (hab : a + b = 1)
    (he : e ∈ mixtureEnergies g x) (he' : e' ∈ mixtureEnergies g x') :
    a * e + b * e' ∈ mixtureEnergies g (a * x + b * x') := by
  obtain ⟨m, w, p, y, hw0, hy, hw1, hwx, rfl⟩ := he
  obtain ⟨m', w', p', y', hw0', hy', hw1', hwx', rfl⟩ := he'
  refine ⟨m + m', Fin.append (fun j => a * w j) (fun j => b * w' j), Fin.append p p',
    Fin.append y y', fun j => ?_, fun j => ?_, ?_, ?_, ?_⟩
  · refine Fin.addCases (fun j => ?_) (fun j => ?_) j <;> simp [mul_nonneg, ha, hb, hw0, hw0']
  · refine Fin.addCases (fun j => ?_) (fun j => ?_) j <;> simp [hy, hy']
  · simp [Fin.sum_univ_add, ← mul_sum, hw1, hw1', hab]
  · simp [Fin.sum_univ_add, mul_assoc, ← mul_sum, hwx, hwx']
  · simp [Fin.sum_univ_add, mul_assoc, ← mul_sum]

/-- The equilibrium molar Gibbs energy of a binary system is convex in composition on
`[0, 1]`, provided the phase Gibbs curves are bounded below there. -/
theorem equilibriumGibbs_convexOn {B : ℝ}
    (hB : ∀ p y, y ∈ Icc (0 : ℝ) 1 → B ≤ g p y) : ConvexOn ℝ (Icc 0 1) (equilibriumGibbs g) := by
  rcases isEmpty_or_nonempty P with hP | hPne
  · have hempty : ∀ x, mixtureEnergies g x = ∅ := by
      intro x
      ext e
      simp only [mixtureEnergies, Set.mem_ofPred_eq, Set.mem_empty_iff_false, iff_false]
      rintro ⟨m, w, p, y, -, -, hw1, -⟩
      cases m with
      | zero => simp at hw1
      | succ m => exact hP.false (p 0)
    have : equilibriumGibbs g = fun _ => 0 := by
      funext x; simp [equilibriumGibbs, hempty x]
    rw [this]
    exact convexOn_const 0 (convex_Icc 0 1)
  obtain ⟨p⟩ := hPne
  refine ⟨convex_Icc 0 1, fun x hx x' hx' a b ha hb hab => ?_⟩
  have hne : (mixtureEnergies g x).Nonempty := ⟨_, single_mem p hx⟩
  have hne' : (mixtureEnergies g x').Nonempty := ⟨_, single_mem p hx'⟩
  have hbdd := mixtureEnergies_bddBelow hB (a • x + b • x')
  simp only [smul_eq_mul]
  rcases ha.eq_or_lt with rfl | ha'
  · simp only [zero_add] at hab; subst hab; simp
  rcases hb.eq_or_lt with rfl | hb'
  · simp only [add_zero] at hab; subst hab; simp
  have step : ∀ e' ∈ mixtureEnergies g x',
      equilibriumGibbs g (a * x + b * x') ≤ a * equilibriumGibbs g x + b * e' := by
    intro e' he'
    have : (equilibriumGibbs g (a * x + b * x') - b * e') / a ≤ equilibriumGibbs g x := by
      apply le_csInf hne
      intro e he
      rw [div_le_iff₀ ha', sub_le_iff_le_add]
      have := csInf_le hbdd (by simpa [smul_eq_mul] using mixture_combine ha hb hab he he')
      simp only [smul_eq_mul] at this
      unfold equilibriumGibbs; linarith
    rw [div_le_iff₀ ha'] at this
    linarith
  have : (equilibriumGibbs g (a * x + b * x') - a * equilibriumGibbs g x) / b ≤
      equilibriumGibbs g x' := by
    apply le_csInf hne'
    intro e' he'
    rw [div_le_iff₀ hb']
    have := step e' he'
    linarith
  rw [div_le_iff₀ hb'] at this
  linarith

/-- Every convex function on `[0, 1]` that lies below each phase's Gibbs curve lies below
the equilibrium molar Gibbs energy, which is therefore the convex envelope of the phase
curves. -/
theorem le_equilibriumGibbs_of_convex {φ : ℝ → ℝ} (hφ : ConvexOn ℝ (Icc 0 1) φ)
    (hle : ∀ p y, y ∈ Icc (0 : ℝ) 1 → φ y ≤ g p y) {x : ℝ} (hne : (mixtureEnergies g x).Nonempty) :
    φ x ≤ equilibriumGibbs g x := by
  apply le_csInf hne
  rintro e ⟨m, w, p, y, hw0, hy, hw1, hwx, rfl⟩
  have hj := hφ.map_sum_le (t := Finset.univ) (w := w) (p := y) (fun j _ => hw0 j)
    (by simpa using hw1) (fun j _ => hy j)
  simp only [smul_eq_mul] at hj
  rw [hwx] at hj
  exact hj.trans (sum_le_sum fun j _ => mul_le_mul_of_nonneg_left (hle _ _ (hy j)) (hw0 j))

/-- The equilibrium molar Gibbs energy lies below every phase's Gibbs curve. -/
theorem equilibriumGibbs_le {B : ℝ} (hB : ∀ p y, y ∈ Icc (0 : ℝ) 1 → B ≤ g p y) (p : P) {y : ℝ}
    (hy : y ∈ Icc (0 : ℝ) 1) : equilibriumGibbs g y ≤ g p y :=
  csInf_le (mixtureEnergies_bddBelow hB y) (single_mem p hy)

/-- The equilibrium molar Gibbs energy of a binary system is the convex envelope of the phase
Gibbs curves on `[0, 1]`: it is convex, it lies below every phase curve, and it lies above
every convex function that lies below every phase curve. The phase set need not be finite
and the infimum over mixtures need not be attained. -/
theorem equilibriumGibbs_isConvexEnvelope [Nonempty P] {B : ℝ}
    (hB : ∀ p y, y ∈ Icc (0 : ℝ) 1 → B ≤ g p y) :
    ConvexOn ℝ (Icc 0 1) (equilibriumGibbs g) ∧
      (∀ p y, y ∈ Icc (0 : ℝ) 1 → equilibriumGibbs g y ≤ g p y) ∧
      ∀ φ : ℝ → ℝ, ConvexOn ℝ (Icc 0 1) φ → (∀ p y, y ∈ Icc (0 : ℝ) 1 → φ y ≤ g p y) →
        ∀ x ∈ Icc (0 : ℝ) 1, φ x ≤ equilibriumGibbs g x := by
  obtain ⟨p⟩ := ‹Nonempty P›
  exact ⟨equilibriumGibbs_convexOn hB, fun q y hy => equilibriumGibbs_le hB q hy,
    fun φ hφ hle x hx => le_equilibriumGibbs_of_convex hφ hle ⟨_, single_mem p hx⟩⟩

/-- If every phase's Gibbs function is concave in temperature on a convex set `I` of
temperatures (nonnegative phase heat capacities), the equilibrium molar Gibbs energy at any
fixed composition is concave in temperature on `I`. -/
theorem equilibriumGibbsT_concaveOn {gT : ℝ → P → ℝ → ℝ} {I : Set ℝ} (hI : Convex ℝ I)
    {B : ℝ → ℝ} (hB : ∀ T ∈ I, ∀ p y, y ∈ Icc (0 : ℝ) 1 → B T ≤ gT T p y)
    (hconc : ∀ p y, y ∈ Icc (0 : ℝ) 1 → ConcaveOn ℝ I (fun T => gT T p y)) (x : ℝ) :
    ConcaveOn ℝ I (equilibriumGibbsT gT x) := by
  refine ⟨hI, fun T1 h1 T2 h2 a b ha hb hab => ?_⟩
  simp only [smul_eq_mul, equilibriumGibbsT, equilibriumGibbs]
  -- The admissible mixtures do not depend on temperature, only their energies do.
  have hmove : ∀ T T', (mixtureEnergies (gT T) x).Nonempty → (mixtureEnergies (gT T') x).Nonempty := by
    rintro T T' ⟨_, m, w, q, y, hw0, hy, hw1, hwx, rfl⟩
    exact ⟨_, m, w, q, y, hw0, hy, hw1, hwx, rfl⟩
  rcases (mixtureEnergies (gT (a * T1 + b * T2)) x).eq_empty_or_nonempty with hemp | hne
  · have e1 : mixtureEnergies (gT T1) x = ∅ := by
      by_contra h; exact (Set.nonempty_iff_ne_empty.mp (hmove _ _ (Set.nonempty_iff_ne_empty.mpr h))) hemp
    have e2 : mixtureEnergies (gT T2) x = ∅ := by
      by_contra h; exact (Set.nonempty_iff_ne_empty.mp (hmove _ _ (Set.nonempty_iff_ne_empty.mpr h))) hemp
    simp [hemp, e1, e2]
  apply le_csInf hne
  rintro e ⟨m, w, q, y, hw0, hy, hw1, hwx, rfl⟩
  have l1 := csInf_le (mixtureEnergies_bddBelow (hB T1 h1) x) ⟨m, w, q, y, hw0, hy, hw1, hwx, rfl⟩
  have l2 := csInf_le (mixtureEnergies_bddBelow (hB T2 h2) x) ⟨m, w, q, y, hw0, hy, hw1, hwx, rfl⟩
  have hpt : ∀ j, a * gT T1 (q j) (y j) + b * gT T2 (q j) (y j) ≤ gT (a * T1 + b * T2) (q j) (y j) :=
    fun j => by simpa [smul_eq_mul] using (hconc (q j) (y j) (hy j)).2 h1 h2 ha hb hab
  calc a * sInf (mixtureEnergies (gT T1) x) + b * sInf (mixtureEnergies (gT T2) x)
      ≤ a * ∑ j, w j * gT T1 (q j) (y j) + b * ∑ j, w j * gT T2 (q j) (y j) :=
        add_le_add (mul_le_mul_of_nonneg_left l1 ha) (mul_le_mul_of_nonneg_left l2 hb)
    _ = ∑ j, w j * (a * gT T1 (q j) (y j) + b * gT T2 (q j) (y j)) := by
        rw [mul_sum, mul_sum, ← sum_add_distrib]
        exact sum_congr rfl fun j _ => by ring
    _ ≤ ∑ j, w j * gT (a * T1 + b * T2) (q j) (y j) :=
        sum_le_sum fun j _ => mul_le_mul_of_nonneg_left (hpt j) (hw0 j)

end Envelope

/-! ## Entropy and enthalpy through phase transitions -/

/-- A molar Gibbs energy concave in temperature on `I` has a nondecreasing entropy channel on
the interior of `I`, kinks at phase transitions included. -/
theorem calphadEntropy_monotoneOn {G : ℝ → ℝ} {I : Set ℝ} (hG : ConcaveOn ℝ I G) :
    MonotoneOn (calphadEntropy G) (interior I) := by
  intro x hx y hy hxy
  have := hG.neg.monotoneOn_rightDeriv hx hy hxy
  simp only [derivWithin.neg] at this
  simpa [calphadEntropy] using this

/-- A molar Gibbs energy concave in temperature on a set `I` of nonnegative temperatures has a
nondecreasing enthalpy channel on the interior of `I`, latent heats at transitions
included. -/
theorem molarEnthalpy_monotoneOn {G : ℝ → ℝ} {I : Set ℝ} (hG : ConcaveOn ℝ I G)
    (hpos : ∀ T ∈ I, 0 ≤ T) : MonotoneOn (molarEnthalpy G) (interior I) := by
  intro T1 h1 T2 h2 hle
  rcases hle.eq_or_lt with rfl | hlt
  · rfl
  have hf := hG.neg
  have hs := hf.slope_le_leftDeriv_of_mem_interior (interior_subset h1) h2 hlt
  have hlr := hf.leftDeriv_le_rightDeriv_of_mem_interior h2
  have hmono := hf.monotoneOn_rightDeriv h1 h2 hlt.le
  have hT1 := hpos T1 (interior_subset h1)
  rw [slope_def_field] at hs
  simp only [derivWithin.neg, Pi.neg_apply] at hs hlr hmono
  have hd : 0 < T2 - T1 := sub_pos.mpr hlt
  rw [div_le_iff₀ hd] at hs
  unfold molarEnthalpy
  nlinarith [mul_nonneg hT1 (sub_nonneg.mpr hmono)]

/-- If every phase's Gibbs function is concave in temperature on a convex set `I`, the
equilibrium entropy at any fixed composition is nondecreasing on the interior of `I`,
through every phase transition: the equilibrium heat capacity, latent heats included, is
nonnegative. -/
theorem equilibrium_entropy_monotoneOn {P : Type*} {gT : ℝ → P → ℝ → ℝ} {I : Set ℝ}
    (hI : Convex ℝ I) {B : ℝ → ℝ} (hB : ∀ T ∈ I, ∀ p y, y ∈ Icc (0 : ℝ) 1 → B T ≤ gT T p y)
    (hconc : ∀ p y, y ∈ Icc (0 : ℝ) 1 → ConcaveOn ℝ I (fun T => gT T p y)) (x : ℝ) :
    MonotoneOn (calphadEntropy (equilibriumGibbsT gT x)) (interior I) :=
  calphadEntropy_monotoneOn (equilibriumGibbsT_concaveOn hI hB hconc x)

/-- Under the same hypotheses and nonnegative temperatures, the equilibrium enthalpy at any
fixed composition is nondecreasing on the interior of `I`, latent heats included. -/
theorem equilibrium_enthalpy_monotoneOn {P : Type*} {gT : ℝ → P → ℝ → ℝ} {I : Set ℝ}
    (hI : Convex ℝ I) {B : ℝ → ℝ} (hB : ∀ T ∈ I, ∀ p y, y ∈ Icc (0 : ℝ) 1 → B T ≤ gT T p y)
    (hconc : ∀ p y, y ∈ Icc (0 : ℝ) 1 → ConcaveOn ℝ I (fun T => gT T p y)) (hpos : ∀ T ∈ I, 0 ≤ T)
    (x : ℝ) : MonotoneOn (molarEnthalpy (equilibriumGibbsT gT x)) (interior I) :=
  molarEnthalpy_monotoneOn (equilibriumGibbsT_concaveOn hI hB hconc x) hpos

/-! ## Chemical potentials -/

/-- Molar Gibbs energy of a two-phase mixture at overall composition `x` with phase
compositions `y1 < x < y2`, each phase weighted by the lever rule. -/
def twoPhaseEnergy (g1 g2 : ℝ → ℝ) (x y1 y2 : ℝ) : ℝ :=
  ((y2 - x) * g1 y1 + (x - y1) * g2 y2) / (y2 - y1)

/-- At a two-phase minimum with interior compositions `x1 < x < x2`, the tangents of both
phase Gibbs curves are the common chord: both phases have the same chemical potentials. -/
theorem commonTangent_of_isLocalMin {g1 g2 : ℝ → ℝ} {x x1 x2 : ℝ} (h1 : x1 < x) (h2 : x < x2)
    (hd1 : DifferentiableAt ℝ g1 x1) (hd2 : DifferentiableAt ℝ g2 x2)
    (hmin1 : IsLocalMin (fun y => twoPhaseEnergy g1 g2 x y x2) x1)
    (hmin2 : IsLocalMin (fun y => twoPhaseEnergy g1 g2 x x1 y) x2) :
    deriv g1 x1 = (g2 x2 - g1 x1) / (x2 - x1) ∧ deriv g2 x2 = (g2 x2 - g1 x1) / (x2 - x1) ∧
      chemicalPotentials g1 x1 = chemicalPotentials g2 x2 := by
  have h21 : x2 - x1 ≠ 0 := by linarith
  set d1 := deriv g1 x1
  set d2 := deriv g2 x2
  have k1 : HasDerivAt (fun y => twoPhaseEnergy g1 g2 x y x2)
      ((((x2 - x) * d1 + (-1) * g2 x2) * (x2 - x1) -
        ((x2 - x) * g1 x1 + (x - x1) * g2 x2) * (-1)) / (x2 - x1) ^ 2) x1 := by
    have hn : HasDerivAt (fun y => (x2 - x) * g1 y + (x - y) * g2 x2)
        ((x2 - x) * d1 + (-1) * g2 x2) x1 :=
      (hd1.hasDerivAt.const_mul _).add (((hasDerivAt_id x1).const_sub x).mul_const _ |>.congr_deriv
        (by simp))
    have hdn : HasDerivAt (fun y => x2 - y) (-1) x1 := by
      simpa using (hasDerivAt_id x1).const_sub x2
    exact hn.div hdn h21
  have k2 : HasDerivAt (fun y => twoPhaseEnergy g1 g2 x x1 y)
      ((((1 : ℝ) * g1 x1 + (x - x1) * d2) * (x2 - x1) -
        ((x2 - x) * g1 x1 + (x - x1) * g2 x2) * 1) / (x2 - x1) ^ 2) x2 := by
    have hn : HasDerivAt (fun y => (y - x) * g1 x1 + (x - x1) * g2 y)
        ((1 : ℝ) * g1 x1 + (x - x1) * d2) x2 :=
      (((hasDerivAt_id x2).sub_const x).mul_const _).add (hd2.hasDerivAt.const_mul _)
    have hdn : HasDerivAt (fun y => y - x1) 1 x2 := by simpa using (hasDerivAt_id x2).sub_const x1
    exact hn.div hdn h21
  have e1 := hmin1.hasDerivAt_eq_zero k1
  have e2 := hmin2.hasDerivAt_eq_zero k2
  have hsq : (x2 - x1) ^ 2 ≠ 0 := pow_ne_zero 2 h21
  rw [div_eq_zero_iff, or_iff_left hsq] at e1 e2
  have hd1' : d1 = (g2 x2 - g1 x1) / (x2 - x1) := by
    rw [eq_div_iff h21]
    have : (x2 - x) * ((x2 - x1) * d1 + g1 x1 - g2 x2) = 0 := by linarith
    rcases mul_eq_zero.mp this with h | h
    · linarith
    · linarith
  have hd2' : d2 = (g2 x2 - g1 x1) / (x2 - x1) := by
    rw [eq_div_iff h21]
    have : (x - x1) * (g1 x1 + (x2 - x1) * d2 - g2 x2) = 0 := by linarith
    rcases mul_eq_zero.mp this with h | h
    · linarith
    · linarith
  refine ⟨hd1', hd2', ?_⟩
  have c1 : deriv g1 x1 = (g2 x2 - g1 x1) / (x2 - x1) := hd1'
  have c2 : deriv g2 x2 = (g2 x2 - g1 x1) / (x2 - x1) := hd2'
  funext k
  fin_cases k <;> simp [chemicalPotentials, c1, c2] <;> field_simp <;> ring

/-! ## Phase fractions -/

/-- For two phases of distinct compositions `x1 < x2`, mass balance and normalization fix
the phase amounts to the lever rule, and both lie in `[0, 1]` exactly when the overall
composition lies between the phase compositions. -/
theorem leverFractions_unique_and_bounds {x1 x2 x : ℝ} (h12 : x1 < x2) :
    (∀ n1 n2 : ℝ, (n1 + n2 = 1 ∧ n1 * x1 + n2 * x2 = x) ↔
        (n1 = leverFractions x1 x2 x 0 ∧ n2 = leverFractions x1 x2 x 1)) ∧
      ((∀ k, leverFractions x1 x2 x k ∈ Icc (0 : ℝ) 1) ↔ x ∈ Icc x1 x2) := by
  have hd : 0 < x2 - x1 := by linarith
  have hd' : x2 - x1 ≠ 0 := hd.ne'
  refine ⟨fun n1 n2 => ⟨fun ⟨hs, hb⟩ => ?_, fun ⟨h1, h2⟩ => ?_⟩, ⟨fun h => ?_, fun ⟨hl, hu⟩ k => ?_⟩⟩
  · simp only [leverFractions, Matrix.cons_val_zero, Matrix.cons_val_one]
    constructor <;> rw [eq_div_iff hd']
    · linear_combination x2 * hs - hb
    · linear_combination hb - x1 * hs
  · simp only [leverFractions, Matrix.cons_val_zero, Matrix.cons_val_one] at h1 h2
    subst h1 h2
    constructor <;> field_simp <;> ring
  · have h0 := h 0
    have h1 := h 1
    simp only [leverFractions, Matrix.cons_val_zero, Matrix.cons_val_one,
      Set.mem_Icc] at h0 h1
    rw [le_div_iff₀ hd] at h0 h1
    exact ⟨by linarith [h1.1], by linarith [h0.1]⟩
  · fin_cases k <;> simp only [leverFractions, Fin.zero_eta, Fin.mk_one, Matrix.cons_val_zero,
      Matrix.cons_val_one, Set.mem_Icc] <;>
      exact ⟨div_nonneg (by linarith) hd.le, (div_le_one hd).mpr (by linarith)⟩

/-! ## Transition temperature -/

/-- For a unary system or a congruent (partitionless) transformation between phases `alpha`
and `beta` of the same composition: if `dG = G_beta - G_alpha` is continuous on `[T1, T2]`,
positive at `T1`, negative at `T2`, and has derivative `-dS` with a positive entropy
difference `dS = S_beta - S_alpha` inside, then the interpreted transition temperature is the
unique temperature in `(T1, T2)` with `dG = 0`; phase `alpha` is stable below it and phase
`beta` above it. For an alloy this temperature is the T0 temperature, not a phase-diagram
boundary. -/
theorem transitionTemperature_unique {dG dS : ℝ → ℝ} {T1 T2 : ℝ} (h12 : T1 < T2)
    (hcont : ContinuousOn dG (Icc T1 T2))
    (hderiv : ∀ T ∈ Ioo T1 T2, HasDerivAt dG (-dS T) T) (hS : ∀ T ∈ Ioo T1 T2, 0 < dS T)
    (hstart : 0 < dG T1) (hend : dG T2 < 0) :
    transitionTemperature dG T1 T2 ∈ Ioo T1 T2 ∧ dG (transitionTemperature dG T1 T2) = 0 ∧
      (∀ T ∈ Icc T1 T2, dG T = 0 → T = transitionTemperature dG T1 T2) ∧
      (∀ T ∈ Ico T1 (transitionTemperature dG T1 T2), 0 < dG T) ∧
      (∀ T ∈ Ioc (transitionTemperature dG T1 T2) T2, dG T < 0) := by
  have hanti : StrictAntiOn dG (Icc T1 T2) := by
    apply strictAntiOn_of_deriv_neg (convex_Icc T1 T2) hcont
    intro T hT
    rw [interior_Icc] at hT
    rw [(hderiv T hT).deriv]
    linarith [hS T hT]
  obtain ⟨z, hz, hz0⟩ : ∃ z ∈ Icc T1 T2, dG z = 0 :=
    intermediate_value_Icc' h12.le hcont ⟨hend.le, hstart.le⟩
  have hzT1 : z ≠ T1 := by rintro rfl; linarith
  have hzT2 : z ≠ T2 := by rintro rfl; linarith
  have hzI : z ∈ Ioo T1 T2 := ⟨lt_of_le_of_ne hz.1 (Ne.symm hzT1), lt_of_le_of_ne hz.2 hzT2⟩
  have hset : {T | T ∈ Icc T1 T2 ∧ dG T ≤ 0} = Icc z T2 := by
    ext T
    simp only [Set.mem_ofPred_eq, Set.mem_Icc]
    constructor
    · rintro ⟨⟨h1, h2⟩, hle⟩
      refine ⟨?_, h2⟩
      by_contra hlt
      push Not at hlt
      have := hanti ⟨h1, h2⟩ hz hlt
      linarith
    · rintro ⟨h1, h2⟩
      refine ⟨⟨hz.1.trans h1, h2⟩, ?_⟩
      rcases h1.lt_or_eq with hlt | rfl
      · exact (hanti hz ⟨hz.1.trans hlt.le, h2⟩ hlt).le.trans hz0.le
      · exact hz0.le
  have htt : transitionTemperature dG T1 T2 = z := by
    unfold transitionTemperature
    rw [hset, csInf_Icc hz.2]
  rw [htt]
  refine ⟨hzI, hz0, fun T hT hT0 => ?_, fun T hT => ?_, fun T hT => ?_⟩
  · exact hanti.injOn hT hz (hT0.trans hz0.symm)
  · have := hanti ⟨hT.1, hT.2.le.trans hz.2⟩ hz hT.2
    linarith
  · have := hanti hz ⟨hz.1.trans hT.1.le, hT.2⟩ hT.1
    linarith

end OMAI.PhyslibBridge.Calphad
