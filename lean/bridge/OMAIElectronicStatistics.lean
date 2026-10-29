module

public import Mathlib.Analysis.SpecialFunctions.Exp
public import Mathlib.Topology.Order.IntermediateValue
public import Mathlib.Tactic

/-!
# Carrier mobility and the Fermi level

The catalog's `compute_carrier_mobility` is amset's Boltzmann mobility `mu = sigma / (n e)`.
With scattering rates that add mechanism by mechanism, `1/tau_k = sum_i 1/tau_{k,i}` in every
state `k`, the mobility is `c sum_k w_k tau_k` with `w_k >= 0` the Fermi-window and velocity
weights and `c > 0`, and the single-mechanism mobilities are `mu_i = c sum_k w_k tau_{k,i}`.
amset also reports the `mu_i`. Combining them by Matthiessen's rule never underestimates the
mobility: `mu <= (sum_i 1/mu_i)^-1`.

The catalog's `compute_electronic_dos` is the density of states `g(E) = sum_b g_b delta(E - E_b)`
of the Kohn-Sham levels, with degeneracies `g_b > 0`. The transport codes fix the chemical
potential from it: the electron count `N(mu) = sum_b g_b / (1 + e^((E_b - mu)/(k_B T)))` is
continuous and strictly increasing at `T > 0`, so every count strictly between zero and the
number of states fixes a unique Fermi level. These are local results over Mathlib.
-/

@[expose] public section

noncomputable section

open Finset Filter Topology Real

namespace OMAI.PhyslibBridge.ElectronicStatistics

variable {κ ι : Type*} [Fintype κ] [Fintype ι]

/-- The relaxation time of a state whose mechanism rates add, `1 / sum_i 1/tau_i`. -/
def combinedTime (tau : ι → ℝ) : ℝ := 1 / ∑ i, 1 / tau i

/-- The interpreted catalog expression of `compute_carrier_mobility`, the Boltzmann mobility
`c sum_k w_k tau_k` with the combined relaxation times. This definition alone is not a
physical proof. -/
def boltzmannMobility (c : ℝ) (w : κ → ℝ) (tau : κ → ι → ℝ) : ℝ :=
  c * ∑ k, w k * combinedTime (tau k)

/-- The mobility with mechanism `i` alone, `c sum_k w_k tau_{k,i}`. -/
def mechanismMobility (c : ℝ) (w : κ → ℝ) (tau : κ → ι → ℝ) (i : ι) : ℝ :=
  c * ∑ k, w k * tau k i

private theorem combinedTime_le {tau X : ι → ℝ} (htau : ∀ i, 0 < tau i) (hX : ∀ i, 0 < X i) :
    combinedTime tau ≤ (∑ i, tau i / X i ^ 2) / (∑ i, 1 / X i) ^ 2 := by
  have htitu := sq_sum_div_le_sum_sq_div univ (fun i => 1 / X i)
    (g := fun i => 1 / tau i) (fun i _ => by have := htau i; positivity)
  have hsimp : ∀ i, (1 / X i) ^ 2 / (1 / tau i) = tau i / X i ^ 2 := fun i => by
    have := htau i; have := hX i; field_simp
  simp only [hsimp] at htitu
  rcases isEmpty_or_nonempty ι with hι | hι
  · simp [combinedTime]
  have hS : 0 < ∑ i, 1 / tau i := sum_pos (fun i _ => by have := htau i; positivity) univ_nonempty
  have hT : 0 < ∑ i, 1 / X i := sum_pos (fun i _ => by have := hX i; positivity) univ_nonempty
  unfold combinedTime
  rw [div_le_div_iff₀ hS (by positivity)]
  rw [div_le_iff₀ hS] at htitu
  nlinarith

/-- Matthiessen's rule overestimates the mobility. With scattering rates that add in every
state, the Boltzmann mobility is at most the Matthiessen combination of the single-mechanism
mobilities, `mu <= (sum_i 1/mu_i)^-1`. -/
theorem boltzmannMobility_le_matthiessen {c : ℝ} (hc : 0 < c) {w : κ → ℝ} (hw : ∀ k, 0 ≤ w k)
    {tau : κ → ι → ℝ} (htau : ∀ k i, 0 < tau k i) :
    boltzmannMobility c w tau ≤ 1 / ∑ i, 1 / mechanismMobility c w tau i := by
  by_cases hall : ∀ k, w k = 0
  · simp [boltzmannMobility, mechanismMobility, hall]
  push Not at hall
  obtain ⟨k0, hk0⟩ := hall
  have hk0pos : 0 < w k0 := (hw k0).lt_of_ne' hk0
  have hX : ∀ i, 0 < mechanismMobility c w tau i := fun i => by
    unfold mechanismMobility
    refine mul_pos hc (lt_of_lt_of_le (mul_pos hk0pos (htau k0 i)) ?_)
    exact single_le_sum (f := fun k => w k * tau k i)
      (fun k _ => mul_nonneg (hw k) (htau k i).le) (mem_univ k0)
  set X := mechanismMobility c w tau
  rcases isEmpty_or_nonempty ι with hι | hι
  · simp [boltzmannMobility, combinedTime]
  have hT : 0 < ∑ i, 1 / X i := sum_pos (fun i _ => by have := hX i; positivity) univ_nonempty
  have hpt : ∀ k, w k * combinedTime (tau k) ≤
      w k * ((∑ i, tau k i / X i ^ 2) / (∑ i, 1 / X i) ^ 2) :=
    fun k => mul_le_mul_of_nonneg_left (combinedTime_le (htau k) hX) (hw k)
  have hsum : ∑ k, w k * ((∑ i, tau k i / X i ^ 2) / (∑ i, 1 / X i) ^ 2) =
      (∑ i, 1 / X i) / (∑ i, 1 / X i) ^ 2 / c := by
    have hrow : ∑ k, w k * ∑ i, tau k i / X i ^ 2 = (∑ i, 1 / X i) / c := by
      simp only [mul_sum]
      rw [sum_comm]
      rw [sum_div]
      refine sum_congr rfl fun i _ => ?_
      have hXi : X i = c * ∑ k, w k * tau k i := rfl
      have := hX i
      rw [show ∑ k, w k * (tau k i / X i ^ 2) = (∑ k, w k * tau k i) / X i ^ 2 by
        rw [sum_div]; exact sum_congr rfl fun k _ => by ring]
      rw [show ∑ k, w k * tau k i = X i / c by rw [hXi]; field_simp]
      field_simp
    have hpull : ∑ k, w k * ((∑ i, tau k i / X i ^ 2) / (∑ i, 1 / X i) ^ 2) =
        (∑ k, w k * ∑ i, tau k i / X i ^ 2) / (∑ i, 1 / X i) ^ 2 := by
      rw [sum_div]; exact sum_congr rfl fun k _ => by ring
    rw [hpull, hrow]
    ring
  unfold boltzmannMobility
  calc c * ∑ k, w k * combinedTime (tau k)
      ≤ c * ∑ k, w k * ((∑ i, tau k i / X i ^ 2) / (∑ i, 1 / X i) ^ 2) :=
        mul_le_mul_of_nonneg_left (sum_le_sum fun k _ => hpt k) hc.le
    _ = 1 / ∑ i, 1 / X i := by rw [hsum]; field_simp

/-- The electron count `N(mu) = sum_b g_b / (1 + e^((E_b - mu)/(k_B T)))` of levels `E_b` with
degeneracies `g_b`, read off the density of states. -/
def electronCount (g E : ι → ℝ) (kT mu : ℝ) : ℝ := ∑ b, g b / (1 + exp ((E b - mu) / kT))

/-- The interpreted catalog expression of `compute_electronic_dos`: the integral of the density
of states `sum_b g_b delta(E - E_b)` against a test function `phi`. This definition alone is not a
physical proof. -/
def electronicDOS (g E : ι → ℝ) (phi : ℝ → ℝ) : ℝ := ∑ b, g b * phi (E b)

/-- The electron count is the density of states integrated against the Fermi function. -/
theorem electronCount_eq_dos (g E : ι → ℝ) (kT mu : ℝ) :
    electronCount g E kT mu = electronicDOS g E (fun e => 1 / (1 + exp ((e - mu) / kT))) := by
  simp [electronCount, electronicDOS, div_eq_mul_inv]

/-- At positive temperature every electron count strictly between zero and the number of states
`sum_b g_b` fixes a unique chemical potential: exactly one `mu` makes the density of states,
integrated against the Fermi function, hold `N` electrons. -/
theorem exists_unique_fermiLevel [Nonempty ι] {g : ι → ℝ} (hg : ∀ b, 0 < g b) (E : ι → ℝ)
    {kT : ℝ} (hkT : 0 < kT) {N : ℝ} (hN0 : 0 < N) (hN : N < ∑ b, g b) :
    ∃! mu, electronicDOS g E (fun e => 1 / (1 + exp ((e - mu) / kT))) = N := by
  simp_rw [← electronCount_eq_dos]
  have hterm : ∀ b, StrictMono fun mu => g b / (1 + exp ((E b - mu) / kT)) := by
    intro b m1 m2 h
    apply div_lt_div_of_pos_left (hg b) (by positivity)
    have : (E b - m2) / kT < (E b - m1) / kT := div_lt_div_of_pos_right (by linarith) hkT
    linarith [exp_lt_exp.mpr this]
  have hmono : StrictMono (electronCount g E kT) := fun m1 m2 h =>
    sum_lt_sum_of_nonempty univ_nonempty fun b _ => hterm b h
  have hcont : Continuous (electronCount g E kT) := by
    unfold electronCount
    refine continuous_finsetSum _ fun b _ => continuous_const.div ?_ fun x => by positivity
    exact continuous_const.add (continuous_exp.comp ((continuous_const.sub continuous_id).div_const _))
  have hbot : Tendsto (electronCount g E kT) atBot (𝓝 0) := by
    unfold electronCount
    rw [show (0 : ℝ) = ∑ b : ι, (0 : ℝ) by simp]
    refine tendsto_finsetSum _ fun b _ => ?_
    have h1 : Tendsto (fun mu : ℝ => E b - mu) atBot atTop := by
      simpa [sub_eq_add_neg] using tendsto_atTop_add_const_left _ (E b) tendsto_neg_atBot_atTop
    have h2 : Tendsto (fun mu => 1 + exp ((E b - mu) / kT)) atBot atTop :=
      tendsto_atTop_add_const_left _ 1 (tendsto_exp_atTop.comp (h1.atTop_div_const hkT))
    simpa [div_eq_mul_inv] using h2.inv_tendsto_atTop.const_mul (g b)
  have htop : Tendsto (electronCount g E kT) atTop (𝓝 (∑ b, g b)) := by
    unfold electronCount
    refine tendsto_finsetSum _ fun b _ => ?_
    have h1 : Tendsto (fun mu : ℝ => E b - mu) atTop atBot := by
      simpa [sub_eq_add_neg] using tendsto_atBot_add_const_left _ (E b) tendsto_neg_atTop_atBot
    have h2 : Tendsto (fun mu => 1 + exp ((E b - mu) / kT)) atTop (𝓝 (1 + 0)) :=
      (tendsto_exp_atBot.comp (h1.atBot_div_const hkT)).const_add 1
    have h3 := (tendsto_const_nhds (x := g b)).div h2 (by norm_num)
    rw [add_zero, div_one] at h3
    exact h3
  obtain ⟨a, ha⟩ := (hbot.eventually (gt_mem_nhds hN0)).exists
  obtain ⟨c, hc⟩ := (htop.eventually (lt_mem_nhds hN)).exists
  have hac : a ≤ c := (hmono.lt_iff_lt.mp (ha.trans hc)).le
  obtain ⟨mu, -, hmu⟩ := intermediate_value_Icc hac hcont.continuousOn ⟨ha.le, hc.le⟩
  exact ⟨mu, hmu, fun nu hnu => hmono.injective (hnu.trans hmu.symm)⟩

end OMAI.PhyslibBridge.ElectronicStatistics
