module

public import Physlib.CondensedMatter.Thermoelectric.Basic
public import OMAISommerfeldTransport
public import Mathlib.Topology.Algebra.Order.Field
public import Mathlib.Tactic

/-!
# Boltzmann electronic transport coefficients

The catalog's transport producers (`compute_electronic_conductivity`, `compute_seebeck`,
`compute_electronic_thermal_conductivity`) are opaque Boltzmann-transport solvers. BoltzTraP2,
which amset calls, evaluates them from the Onsager kinetic coefficients
`L_k = sum_b w_b (E_b - mu)^k` on a finite energy grid, with `w_b >= 0` the transport
distribution times the Fermi window `-df/dE` times the bin width:
`sigma = e^2 L_0`, `S = -(L_1 / L_0) / (e T)` and `kappa_e = (L_2 - L_1^2 / L_0) / T`.
These definitions interpret the producers; they hold for any relaxation-time model, since the
scattering enters only through `w`.

The electronic thermal conductivity is never negative, and it vanishes exactly when the whole
transport window sits at one energy (the Mahan-Sofo delta function). The coefficients therefore
satisfy the axioms of Physlib's `ThermoelectricMaterial` for every positive lattice
conductivity, and its figure of merit is bounded by the squared mean over the variance of the
transport energy, a bound approached as the lattice conductivity vanishes.
-/

@[expose] public section

noncomputable section

open Finset Filter Topology CondensedMatter

namespace OMAI.PhyslibBridge.ElectronicTransport

variable {ι : Type*} [Fintype ι]

/-- The Onsager kinetic coefficient `L_k = sum_b w_b (E_b - mu)^k` of a transport window. -/
def kinetic (w E : ι → ℝ) (mu : ℝ) (k : ℕ) : ℝ := ∑ b, w b * (E b - mu) ^ k

/-- The interpreted catalog expression of `compute_electronic_conductivity`,
`sigma = e^2 L_0`. This definition alone is not a physical proof. -/
def boltzmannConductivity (w E : ι → ℝ) (mu e : ℝ) : ℝ := e ^ 2 * kinetic w E mu 0

/-- The interpreted catalog expression of `compute_seebeck`, `S = -(L_1 / L_0) / (e T)` with
`e > 0` the elementary charge, so that electrons above `mu` give a negative Seebeck coefficient.
This definition alone is not a physical proof. -/
def boltzmannSeebeck (w E : ι → ℝ) (mu e T : ℝ) : ℝ :=
  -(kinetic w E mu 1 / kinetic w E mu 0) / (e * T)

/-- The interpreted catalog expression of `compute_electronic_thermal_conductivity`,
`kappa_e = (L_2 - L_1^2 / L_0) / T`. This definition alone is not a physical proof. -/
def boltzmannKappaE (w E : ι → ℝ) (mu T : ℝ) : ℝ :=
  (kinetic w E mu 2 - kinetic w E mu 1 ^ 2 / kinetic w E mu 0) / T

private theorem lagrange (w E : ι → ℝ) (mu : ℝ) :
    ∑ b, ∑ c, w b * w c * (E b - E c) ^ 2 =
      2 * (kinetic w E mu 0 * kinetic w E mu 2 - kinetic w E mu 1 ^ 2) := by
  have hrow : ∀ b, ∑ c, w b * w c * (E b - E c) ^ 2 =
      w b * (E b - mu) ^ 2 * kinetic w E mu 0 + w b * kinetic w E mu 2 -
        2 * (w b * (E b - mu)) * kinetic w E mu 1 := by
    intro b
    simp only [kinetic, pow_zero, mul_one, pow_one, mul_sum, ← sum_add_distrib, ← sum_sub_distrib]
    exact sum_congr rfl fun c _ => by ring
  simp only [hrow, sum_sub_distrib, sum_add_distrib, ← sum_mul, ← mul_sum]
  simp only [kinetic, pow_zero, mul_one, pow_one]
  ring

private theorem kinetic_zero_nonneg {w : ι → ℝ} (hw : ∀ b, 0 ≤ w b) (E : ι → ℝ) (mu : ℝ) :
    0 ≤ kinetic w E mu 0 := sum_nonneg fun b _ => by simpa using hw b

private theorem kinetic_two_nonneg {w : ι → ℝ} (hw : ∀ b, 0 ≤ w b) (E : ι → ℝ) (mu : ℝ) :
    0 ≤ kinetic w E mu 2 := sum_nonneg fun b _ => mul_nonneg (hw b) (sq_nonneg _)

private theorem variance_nonneg {w : ι → ℝ} (hw : ∀ b, 0 ≤ w b) (E : ι → ℝ) (mu : ℝ) :
    0 ≤ kinetic w E mu 0 * kinetic w E mu 2 - kinetic w E mu 1 ^ 2 := by
  have h := lagrange w E mu
  have h0 : 0 ≤ ∑ b, ∑ c, w b * w c * (E b - E c) ^ 2 :=
    sum_nonneg fun b _ => sum_nonneg fun c _ => mul_nonneg (mul_nonneg (hw b) (hw c)) (sq_nonneg _)
  linarith

/-- The electronic thermal conductivity of a transport window is never negative, and it
vanishes exactly when every weighted state has one energy: `kappa_e = 0` if and only if the
transport distribution is a single delta function. -/
theorem boltzmannKappaE_nonneg_and_eq_zero_iff {w : ι → ℝ} (hw : ∀ b, 0 ≤ w b) (E : ι → ℝ)
    (mu : ℝ) {T : ℝ} (hT : 0 < T) :
    0 ≤ boltzmannKappaE w E mu T ∧
      (boltzmannKappaE w E mu T = 0 ↔ ∃ E0, ∀ b, w b ≠ 0 → E b = E0) := by
  rcases (kinetic_zero_nonneg hw E mu).lt_or_eq with hL0 | hL0
  · have hform : boltzmannKappaE w E mu T =
        (kinetic w E mu 0 * kinetic w E mu 2 - kinetic w E mu 1 ^ 2) / (kinetic w E mu 0 * T) := by
      unfold boltzmannKappaE
      field_simp
    refine ⟨by rw [hform]; exact div_nonneg (variance_nonneg hw E mu) (by positivity), ?_⟩
    rw [hform, div_eq_zero_iff, or_iff_left (by positivity)]
    have hl := lagrange w E mu
    have hterm : ∀ b c, 0 ≤ w b * w c * (E b - E c) ^ 2 := fun b c =>
      mul_nonneg (mul_nonneg (hw b) (hw c)) (sq_nonneg _)
    constructor
    · intro hzero
      have hsum : ∑ b, ∑ c, w b * w c * (E b - E c) ^ 2 = 0 := by rw [hl, hzero, mul_zero]
      obtain ⟨b0, hb0⟩ : ∃ b0, w b0 ≠ 0 := by
        by_contra hall
        push Not at hall
        simp [kinetic, hall] at hL0
      refine ⟨E b0, fun b hb => ?_⟩
      have hrow := (sum_eq_zero_iff_of_nonneg fun b _ => sum_nonneg fun c _ => hterm b c).mp
        hsum b (mem_univ b)
      have hbc := (sum_eq_zero_iff_of_nonneg fun c _ => hterm b c).mp hrow b0 (mem_univ b0)
      have hwb : 0 < w b * w b0 := mul_pos ((hw b).lt_of_ne' hb) ((hw b0).lt_of_ne' hb0)
      have : (E b - E b0) ^ 2 = 0 := by
        rcases mul_eq_zero.mp hbc with h | h
        · exact absurd h hwb.ne'
        · exact h
      linarith [pow_eq_zero_iff (n := 2) (two_ne_zero) |>.mp this]
    · rintro ⟨E0, hE0⟩
      have hsum : ∑ b, ∑ c, w b * w c * (E b - E c) ^ 2 = 0 := by
        refine sum_eq_zero fun b _ => sum_eq_zero fun c _ => ?_
        by_cases hb : w b = 0
        · simp [hb]
        by_cases hc : w c = 0
        · simp [hc]
        rw [hE0 b hb, hE0 c hc]; ring
      linarith
  · have hall : ∀ b, w b = 0 := by
      intro b
      have := (sum_eq_zero_iff_of_nonneg fun b _ => by simpa using hw b).mp
        (by simpa [kinetic] using hL0.symm) b (mem_univ b)
      simpa using this
    have hz : boltzmannKappaE w E mu T = 0 := by simp [boltzmannKappaE, kinetic, hall]
    exact ⟨hz.ge, iff_of_true hz ⟨0, fun b hb => absurd (hall b) hb⟩⟩

/-- The Boltzmann coefficients of a nonempty transport window at positive temperature, with any
positive lattice conductivity, satisfy the axioms of a Physlib thermoelectric material:
positive electrical conductivity and nonnegative electronic thermal conductivity. -/
theorem exists_boltzmann_thermoelectricMaterial {w : ι → ℝ} (hw : ∀ b, 0 ≤ w b) (E : ι → ℝ)
    {mu e T kappaL : ℝ} (hL0 : 0 < kinetic w E mu 0) (he : e ≠ 0) (hT : 0 < T)
    (hkl : 0 < kappaL) :
    ∃ M : ThermoelectricMaterial, M.S = boltzmannSeebeck w E mu e T ∧
      M.σ = boltzmannConductivity w E mu e ∧ M.κl = kappaL ∧ M.κe = boltzmannKappaE w E mu T :=
  ⟨⟨boltzmannSeebeck w E mu e T, boltzmannConductivity w E mu e, kappaL, boltzmannKappaE w E mu T,
    by unfold boltzmannConductivity; positivity, hkl,
    (boltzmannKappaE_nonneg_and_eq_zero_iff hw E mu hT).1⟩, rfl, rfl, rfl, rfl⟩

private theorem figureOfMerit_closed {w : ι → ℝ} (E : ι → ℝ) {mu e T : ℝ}
    (hL0 : 0 < kinetic w E mu 0) (he : e ≠ 0) (hT : 0 < T) (M : ThermoelectricMaterial)
    (hS : M.S = boltzmannSeebeck w E mu e T) (hs : M.σ = boltzmannConductivity w E mu e)
    (hk : M.κe = boltzmannKappaE w E mu T) :
    M.figureOfMerit T = kinetic w E mu 1 ^ 2 /
      (kinetic w E mu 0 * kinetic w E mu 2 - kinetic w E mu 1 ^ 2 + M.κl * T * kinetic w E mu 0) := by
  have hl := M.κl_pos
  have hden : 0 < M.κl + M.κe := add_pos_of_pos_of_nonneg hl M.κe_nonneg
  have hden' : kinetic w E mu 0 * kinetic w E mu 2 - kinetic w E mu 1 ^ 2 +
      M.κl * T * kinetic w E mu 0 = (M.κl + M.κe) * (T * kinetic w E mu 0) := by
    rw [hk]; unfold boltzmannKappaE; field_simp; ring
  rw [ThermoelectricMaterial.figureOfMerit_eq, hden', hS, hs]
  unfold boltzmannSeebeck boltzmannConductivity
  rw [div_eq_div_iff hden.ne' (mul_pos hden (mul_pos hT hL0)).ne']
  field_simp

/-- The Mahan-Sofo bound. For a transport window whose energies are not all equal and whose
first moment `L_1` is nonzero, every Physlib material carrying its Seebeck coefficient,
conductivity and electronic thermal conductivity has a figure of merit strictly below
`L_1^2 / (L_0 L_2 - L_1^2)`, the squared mean over the variance of the transport energy
`E - mu`. The bound is sharp: materials with small enough lattice conductivity come within any
`eps > 0` of it. -/
theorem figureOfMerit_lt_mahanSofo {w : ι → ℝ} (hw : ∀ b, 0 ≤ w b) (E : ι → ℝ)
    {mu e T : ℝ} (hL0 : 0 < kinetic w E mu 0) (he : e ≠ 0) (hT : 0 < T)
    (hvar : 0 < kinetic w E mu 0 * kinetic w E mu 2 - kinetic w E mu 1 ^ 2)
    (hL1 : kinetic w E mu 1 ≠ 0) :
    (∀ M : ThermoelectricMaterial, M.S = boltzmannSeebeck w E mu e T →
      M.σ = boltzmannConductivity w E mu e → M.κe = boltzmannKappaE w E mu T →
        M.figureOfMerit T <
          kinetic w E mu 1 ^ 2 / (kinetic w E mu 0 * kinetic w E mu 2 - kinetic w E mu 1 ^ 2)) ∧
      ∀ eps > 0, ∃ M : ThermoelectricMaterial, M.S = boltzmannSeebeck w E mu e T ∧
        M.σ = boltzmannConductivity w E mu e ∧ M.κe = boltzmannKappaE w E mu T ∧
        kinetic w E mu 1 ^ 2 / (kinetic w E mu 0 * kinetic w E mu 2 - kinetic w E mu 1 ^ 2) - eps <
          M.figureOfMerit T := by
  set L0 := kinetic w E mu 0
  set L1 := kinetic w E mu 1
  set L2 := kinetic w E mu 2
  have hL1sq : 0 < L1 ^ 2 := by positivity
  refine ⟨fun M hS hs hk => ?_, fun eps heps => ?_⟩
  · rw [figureOfMerit_closed E hL0 he hT M hS hs hk]
    exact div_lt_div_of_pos_left hL1sq hvar (by nlinarith [mul_pos (mul_pos M.κl_pos hT) hL0])
  · have hcont : ContinuousAt (fun k : ℝ => L1 ^ 2 / (L0 * L2 - L1 ^ 2 + k * T * L0)) 0 :=
      continuousAt_const.div (continuousAt_const.add
        ((continuousAt_id.mul continuousAt_const).mul continuousAt_const)) (by simpa using hvar.ne')
    obtain ⟨delta, hdelta, hball⟩ := Metric.continuousAt_iff.mp hcont eps heps
    obtain ⟨M, hS, hs, hl, hk⟩ := exists_boltzmann_thermoelectricMaterial hw E hL0 he hT
      (kappaL := delta / 2) (by positivity)
    refine ⟨M, hS, hs, hk, ?_⟩
    rw [figureOfMerit_closed E hL0 he hT M hS hs hk, hl]
    have hx : dist (delta / 2) 0 < delta := by
      rw [Real.dist_eq, sub_zero, abs_of_pos (by positivity)]
      linarith
    have hclose := hball hx
    simp only [zero_mul, add_zero, Real.dist_eq] at hclose
    linarith [(abs_lt.mp hclose).1]

end OMAI.PhyslibBridge.ElectronicTransport
