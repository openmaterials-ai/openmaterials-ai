module

public import OMAIPhyslibModeGruneisen
public import OMAIPhyslibResponseWitness

/-!
# Exact witnesses for the heat-capacity-weighted Gruneisen parameter

A signed-rate family of three exponential frequency curves, with an arbitrary positive number
of reduced q points and an arbitrary positive molar scale, at the quantum scale
hbar omega/(kB T) = b + 1 for T = 1 K and v = 1. The mode Gruneisen parameters are the rates
times v. A static tilt and stiffness make (T, V) = (1 K, A) a stable stationary point, so the
implicit-function theorem gives a constant-pressure branch through it. These are exact toy
models, not fitted materials or numerical volume scans.
-/

@[expose] public section

noncomputable section

open Constants Temperature QuantumMechanics.OneDimension Filter
open scoped BigOperators Topology

namespace OMAI.PhyslibBridge.GruneisenWitness

/-- The frequency scale kB/hbar (SI); hbar omega/(kB T) = 1 for omega = kB/hbar and T = 1 K. -/
def quantumScale : ℝ := kB / (ℏ : ℝ)

theorem quantumScale_pos : 0 < quantumScale := div_pos kB_pos ℏ_pos

/-- omega_b(v) = (kB/hbar) (b + 1) exp(-r_b (v - 1)), so gamma_b(v) = r_b v. -/
def rateOmega (r : Fin 3 → ℝ) (b : Fin 3) (v : ℝ) : ℝ :=
  quantumScale * ((b.val : ℝ) + 1) * Real.exp (-(r b) * (v - 1))

theorem rateOmega_pos (r : Fin 3 → ℝ) (b : Fin 3) (v : ℝ) : 0 < rateOmega r b v := by
  have := quantumScale_pos
  unfold rateOmega
  positivity

theorem rateOmega_hasDerivAt (r : Fin 3 → ℝ) (b : Fin 3) (v : ℝ) :
    HasDerivAt (rateOmega r b) (-(r b) * rateOmega r b v) v := by
  have h := ((((hasDerivAt_id v).sub_const 1).const_mul (-(r b))).exp).const_mul
    (quantumScale * ((b.val : ℝ) + 1))
  convert h using 1
  · rfl
  · simp only [rateOmega, id_eq, mul_one]
    ring

theorem rateOmega_contDiff (r : Fin 3 → ℝ) (b : Fin 3) : ContDiff ℝ 2 (rateOmega r b) := by
  unfold rateOmega
  fun_prop

/-- Decreasing frequencies: gamma_b(1) = 1, 2, 3. -/
def positiveRates : Fin 3 → ℝ := fun b => (b.val : ℝ) + 1

/-- Increasing frequencies: gamma_b(1) = -1, -2, -3. -/
def negativeRates : Fin 3 → ℝ := fun b => -((b.val : ℝ) + 1)

/-- n reduced-q points (any positive count), one atom, three branches, molar scale A. -/
abbrev rateReference (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n) : HarmonicModeGrid where
  qCount := n
  qCount_pos := hn
  atomCount := 1
  atomCount_pos := by norm_num
  avogadro := A
  avogadro_pos := hA
  oscillator := fun _ b =>
    { m := 1
      ω := quantumScale * ((b.val : ℝ) + 1)
      hω := mul_pos quantumScale_pos (by positivity)
      hm := by norm_num }

abbrev rateFamily (r : Fin 3 → ℝ) (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n)
    (E : ℝ → ℝ) (hE : ContDiff ℝ 2 E) : HarmonicVolumeModel where
  reference := rateReference A hA n hn
  J := Set.Ioi 0
  open_J := isOpen_Ioi
  positive_J := fun _ h => h
  omega := fun _ b => rateOmega r b
  omega_pos := fun _ b v _ => rateOmega_pos r b v
  omega_C2 := fun _ b => (rateOmega_contDiff r b).contDiffOn
  staticEnergy := E
  staticEnergy_C2 := hE.contDiffOn

/-- Unit-scale, single-q, zero-static auxiliary family defining the cell free energy. -/
abbrev rateBase (r : Fin 3 → ℝ) : HarmonicVolumeModel :=
  rateFamily r 1 one_pos 1 Nat.one_pos (fun _ => 0) contDiff_const

def rateBaseF (r : Fin 3 → ℝ) : Response.Surface := (rateBase r).freeEnergy

theorem rateBaseF_eq_sum (r : Fin 3 → ℝ) (t v : ℝ) :
    rateBaseF r (t, v) = ∑ b : Fin 3, harmonicFreeEnergy ℏ kB (rateOmega r b v) t := by
  simp [rateBaseF, rateBase, rateFamily, rateReference, HarmonicVolumeModel.freeEnergy,
    uniformMolarContraction]

/-- The q count n cancels in the uniform q average, so the free energy does not depend on n. -/
theorem rateFamily_freeEnergy (r : Fin 3 → ℝ) (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n)
    (E : ℝ → ℝ) (hE : ContDiff ℝ 2 E) (t V : ℝ) :
    (rateFamily r A hA n hn E hE).freeEnergy (t, V) =
      molarLift A (fun s v => E v + rateBaseF r (s, v)) t V := by
  have hn0 : (n : ℝ) ≠ 0 := Nat.cast_ne_zero.mpr hn.ne'
  simp [HarmonicVolumeModel.freeEnergy, uniformMolarContraction, rateFamily, rateReference,
    rateBaseF_eq_sum, molarLift]
  field_simp

def rateSlope (r : Fin 3 → ℝ) : ℝ := Response.FV (rateBaseF r) (1, 1)
def rateCurvature (r : Fin 3 → ℝ) : ℝ := Response.FVV (rateBaseF r) (1, 1)

/-- Static tilt cancelling the thermal pressure at (1 K, v = 1), plus a stiffness that makes
the total curvature positive for every signed rate vector. -/
def rateStatic (r : Fin 3 → ℝ) (v : ℝ) : ℝ :=
  -rateSlope r * (v - 1) + ((1 + |rateCurvature r|) / 2) * (v - 1) ^ 2

theorem rateStatic_contDiff (r : Fin 3 → ℝ) : ContDiff ℝ 2 (rateStatic r) := by
  unfold rateStatic
  fun_prop

abbrev rateModel (r : Fin 3 → ℝ) (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n) :
    HarmonicVolumeModel := rateFamily r A hA n hn (rateStatic r) (rateStatic_contDiff r)

/-- T = 1 K. -/
def witnessTemperature : Temperature := Temperature.ofNNReal 1

theorem witnessTemperature_toReal : (witnessTemperature : ℝ) = 1 := by
  simp [witnessTemperature, Temperature.toReal]

theorem witnessTemperature_val_pos : 0 < witnessTemperature.val := by
  simp [witnessTemperature]

theorem one_mem_J (r : Fin 3 → ℝ) (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n) :
    (1 : ℝ) ∈ (rateModel r A hA n hn).J := Set.mem_Ioi.mpr one_pos

theorem rateBase_domain (r : Fin 3 → ℝ) {t v : ℝ} (ht : 0 < t) (hv : 0 < v) :
    (t, v) ∈ (rateBase r).domain :=
  ⟨ht, show 0 < v / 1 by rw [div_one]; exact hv⟩

theorem rateBaseF_contDiffAt (r : Fin 3 → ℝ) {t v : ℝ} (ht : 0 < t) (hv : 0 < v) :
    ContDiffAt ℝ 2 (rateBaseF r) (t, v) :=
  (rateBase r).freeEnergy_contDiffAt (rateBase_domain r ht hv)

theorem rate_domain (r : Fin 3 → ℝ) {A t v : ℝ} (hA : 0 < A) (n : ℕ) (hn : 0 < n)
    (ht : 0 < t) (hv : 0 < v) : (t, A * v) ∈ (rateModel r A hA n hn).domain :=
  ⟨ht, show 0 < A * v / A by rw [mul_div_cancel_left₀ _ hA.ne']; exact hv⟩

theorem rate_domain_reference (r : Fin 3 → ℝ) (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n) :
    ((1 : ℝ), A) ∈ (rateModel r A hA n hn).domain :=
  ⟨one_pos, show 0 < A / A from div_pos hA hA⟩

theorem rateStatic_hasDerivAt (r : Fin 3 → ℝ) (v : ℝ) :
    HasDerivAt (rateStatic r) (-rateSlope r + (1 + |rateCurvature r|) * (v - 1)) v := by
  have h := (((hasDerivAt_id v).sub_const 1).const_mul (-rateSlope r)).fun_add
    ((((hasDerivAt_id v).sub_const 1).pow 2).const_mul ((1 + |rateCurvature r|) / 2))
  convert h using 1
  · ext w
    rfl
  · dsimp
    ring

/-- The per-cell free energy of the rate model, static energy included. -/
def rateCell (r : Fin 3 → ℝ) (t v : ℝ) : ℝ := rateStatic r v + rateBaseF r (t, v)

theorem rateCell_hasDerivAt (r : Fin 3 → ℝ) {t v : ℝ} (ht : 0 < t) (hv : 0 < v) :
    HasDerivAt (rateCell r t)
      (-rateSlope r + (1 + |rateCurvature r|) * (v - 1) + Response.FV (rateBaseF r) (t, v)) v :=
  (rateStatic_hasDerivAt r v).fun_add (Response.volume_hasDerivAt (rateBaseF_contDiffAt r ht hv))

theorem rateCell_contDiffAt (r : Fin 3 → ℝ) {t v : ℝ} (ht : 0 < t) (hv : 0 < v) :
    ContDiffAt ℝ 2 (rateCell r t) v :=
  (rateStatic_contDiff r).contDiffAt.add ((rateBaseF_contDiffAt r ht hv).comp v (by fun_prop))

theorem rate_FV_scaled (r : Fin 3 → ℝ) {A t v : ℝ} (hA : 0 < A) (n : ℕ) (hn : 0 < n)
    (ht : 0 < t) (hv : 0 < v) :
    Response.FV (rateModel r A hA n hn).freeEnergy (t, A * v) =
      -rateSlope r + (1 + |rateCurvature r|) * (v - 1) + Response.FV (rateBaseF r) (t, v) := by
  have hfun : (fun W => (rateModel r A hA n hn).freeEnergy (t, W)) =
      molarLift A (rateCell r) t := by
    funext W
    exact rateFamily_freeEnergy r A hA n hn (rateStatic r) (rateStatic_contDiff r) t W
  rw [Response.FV_eq_deriv ((rateModel r A hA n hn).freeEnergy_contDiffAt
    (rate_domain r hA n hn ht hv)), hfun]
  exact (molarLift_volume_hasDerivAt hA (rateCell_hasDerivAt r ht hv)).deriv

theorem rate_FV_reference (r : Fin 3 → ℝ) (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n) :
    Response.FV (rateModel r A hA n hn).freeEnergy (1, A) = 0 := by
  simpa [rateSlope] using rate_FV_scaled r hA n hn one_pos one_pos

theorem rateCell_second (r : Fin 3 → ℝ) :
    deriv (deriv (rateCell r 1)) 1 = 1 + |rateCurvature r| + rateCurvature r := by
  have heq : deriv (rateCell r 1) =ᶠ[𝓝 (1 : ℝ)] (fun v => -rateSlope r +
      (1 + |rateCurvature r|) * (v - 1) + Response.FV (rateBaseF r) (1, v)) := by
    filter_upwards [isOpen_Ioi.mem_nhds (by norm_num : (1 : ℝ) ∈ Set.Ioi 0)] with v hv
    exact (rateCell_hasDerivAt r one_pos hv).deriv
  rw [heq.deriv_eq]
  have hl : HasDerivAt (fun v => -rateSlope r + (1 + |rateCurvature r|) * (v - 1))
      (1 + |rateCurvature r|) 1 := by
    simpa only [mul_one, id_eq] using (((hasDerivAt_id (1 : ℝ)).sub_const 1).const_mul
      (1 + |rateCurvature r|)).const_add (-rateSlope r)
  exact (hl.fun_add (Response.partial_volume_hasDerivAt
    (rateBaseF_contDiffAt r one_pos one_pos) (0, 1))).deriv

theorem rate_FVV_reference (r : Fin 3 → ℝ) (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n) :
    Response.FVV (rateModel r A hA n hn).freeEnergy (1, A) =
      (1 + |rateCurvature r| + rateCurvature r) / A := by
  rw [Response.FVV_eq_deriv_deriv_volume (rateModel r A hA n hn).domain_isOpen
    (rateModel r A hA n hn).freeEnergy_contDiffOn (rate_domain_reference r A hA n hn)]
  have hfun : (fun W => (rateModel r A hA n hn).freeEnergy (1, W)) =
      molarLift A (rateCell r) 1 := by
    funext W
    exact rateFamily_freeEnergy r A hA n hn (rateStatic r) (rateStatic_contDiff r) 1 W
  rw [hfun]
  have h := molarLift_volume_second_deriv (A := A) (t := 1) (v := 1) (f := rateCell r)
    hA (rateCell_contDiffAt r one_pos one_pos)
  simpa only [mul_one, rateCell_second] using h

theorem rate_curvature_pos (r : Fin 3 → ℝ) (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n) :
    0 < Response.FVV (rateModel r A hA n hn).freeEnergy (1, A) := by
  rw [rate_FVV_reference r A hA n hn]
  have h := neg_le_abs (rateCurvature r)
  exact div_pos (by linarith) hA

/-- A stable constant-pressure branch through (1 K, A) for every signed rate vector. -/
theorem rate_branch (r : Fin 3 → ℝ) (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n) :
    ∃ B : Response.StableBranchAt (rateModel r A hA n hn).freeEnergy
        (rateModel r A hA n hn).domain 0 (witnessTemperature : ℝ),
      B.volume (witnessTemperature : ℝ) = A := by
  obtain ⟨B, hB, -⟩ := Response.exists_stableBranchAt (rateModel r A hA n hn).freeEnergy
    (rateModel r A hA n hn).domain 0 (witnessTemperature : ℝ) A
    (rateModel r A hA n hn).domain_isOpen (rateModel r A hA n hn).freeEnergy_contDiffOn
    (by rw [witnessTemperature_toReal]; exact rate_domain_reference r A hA n hn)
    (by rw [witnessTemperature_toReal, add_zero]; exact rate_FV_reference r A hA n hn)
    (by rw [witnessTemperature_toReal]; exact rate_curvature_pos r A hA n hn)
  exact ⟨B, hB⟩

/-- gamma_b(v) = r_b v for every signed rate vector. -/
theorem rate_modeGruneisen (r : Fin 3 → ℝ) (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n)
    (q : Fin n) (b : Fin 3) (v : ℝ) :
    (rateModel r A hA n hn).modeGruneisen q b v = r b * v := by
  have hw := (rateOmega_pos r b v).ne'
  change -(v * deriv (rateOmega r b) v) / rateOmega r b v = r b * v
  rw [(rateOmega_hasDerivAt r b v).deriv]
  field_simp

/-- At v = 1 and T = 1 K the reduced frequency of branch b is exactly b + 1. -/
theorem rate_reference_argument (r : Fin 3 → ℝ) (b : Fin 3) :
    harmonicArgument ℏ kB (rateOmega r b 1) (witnessTemperature : ℝ) = (b.val : ℝ) + 1 := by
  rw [witnessTemperature_toReal]
  unfold harmonicArgument rateOmega quantumScale
  rw [sub_self, mul_zero, Real.exp_zero, mul_one]
  field_simp [ℏ_ne_zero, kB_ne_zero]

/-- The actual Physlib weight of branch b at the witness point; it does not depend on r. -/
theorem rate_weight_eq (r : Fin 3 → ℝ) (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n)
    (q : Fin n) (b : Fin 3) :
    (rateModel r A hA n hn).modeHeatCapacity witnessTemperature 1 (one_mem_J r A hA n hn) q b =
      kB * (((b.val : ℝ) + 1) ^ 2 * Real.exp ((b.val : ℝ) + 1) /
        (Real.exp ((b.val : ℝ) + 1) - 1) ^ 2) := by
  rw [HarmonicVolumeModel.modeHeatCapacity_eq_closed (rateModel r A hA n hn) witnessTemperature
    1 (one_mem_J r A hA n hn) witnessTemperature_val_pos q b]
  change harmonicHeatCapacity ℏ kB (rateOmega r b 1) (witnessTemperature : ℝ) = _
  have ht : 0 < (witnessTemperature : ℝ) := by
    rw [witnessTemperature_toReal]
    exact one_pos
  rw [harmonicHeatCapacity_eq_exp ℏ_pos kB_pos (rateOmega_pos r b 1) ht,
    rate_reference_argument r b, witnessTemperature_toReal]
  have hω : (ℏ : ℝ) * rateOmega r b 1 = kB * ((b.val : ℝ) + 1) := by
    unfold rateOmega quantumScale
    rw [sub_self, mul_zero, Real.exp_zero, mul_one]
    field_simp [ℏ_ne_zero]
  rw [hω]
  have hd : Real.exp ((b.val : ℝ) + 1) - 1 ≠ 0 :=
    (sub_pos.mpr (Real.one_lt_exp_iff.mpr (by positivity))).ne'
  have hk := kB_ne_zero
  field_simp

/-- c(2)/kB < c(1)/kB, from u (u^2 - 1)^2 - 4 u^2 (u - 1)^2 = u (u - 1)^4 with u = e. -/
theorem einsteinWeight_two_lt_one :
    2 ^ 2 * Real.exp 2 / (Real.exp 2 - 1) ^ 2 < 1 ^ 2 * Real.exp 1 / (Real.exp 1 - 1) ^ 2 := by
  have hu1 : 0 < Real.exp 1 - 1 := sub_pos.mpr (Real.one_lt_exp_iff.mpr one_pos)
  have h2 : Real.exp 2 = Real.exp 1 ^ 2 := by
    rw [← Real.exp_nat_mul]
    norm_num
  have hd2 : 0 < Real.exp 1 ^ 2 - 1 := by
    have hf : Real.exp 1 ^ 2 - 1 = (Real.exp 1 - 1) * (Real.exp 1 + 1) := by ring
    rw [hf]
    exact mul_pos hu1 (by positivity)
  rw [h2, div_lt_div_iff₀ (pow_pos hd2 2) (pow_pos hu1 2)]
  have key : 1 ^ 2 * Real.exp 1 * (Real.exp 1 ^ 2 - 1) ^ 2 =
      2 ^ 2 * Real.exp 1 ^ 2 * (Real.exp 1 - 1) ^ 2 + Real.exp 1 * (Real.exp 1 - 1) ^ 4 := by
    ring
  rw [key]
  exact lt_add_of_pos_right _ (mul_pos (Real.exp_pos 1) (pow_pos hu1 4))

/-- c(3)/kB < c(2)/kB, from
4 u^2 (u^3 - 1)^2 - 9 u^3 (u^2 - 1)^2 = u^2 (u - 1)^4 (4 u^2 + 7 u + 4) with u = e. -/
theorem einsteinWeight_three_lt_two :
    3 ^ 2 * Real.exp 3 / (Real.exp 3 - 1) ^ 2 < 2 ^ 2 * Real.exp 2 / (Real.exp 2 - 1) ^ 2 := by
  have hu1 : 0 < Real.exp 1 - 1 := sub_pos.mpr (Real.one_lt_exp_iff.mpr one_pos)
  have h2 : Real.exp 2 = Real.exp 1 ^ 2 := by
    rw [← Real.exp_nat_mul]
    norm_num
  have h3 : Real.exp 3 = Real.exp 1 ^ 3 := by
    rw [← Real.exp_nat_mul]
    norm_num
  have hd2 : 0 < Real.exp 1 ^ 2 - 1 := by
    have hf : Real.exp 1 ^ 2 - 1 = (Real.exp 1 - 1) * (Real.exp 1 + 1) := by ring
    rw [hf]
    exact mul_pos hu1 (by positivity)
  have hd3 : 0 < Real.exp 1 ^ 3 - 1 := by
    have hf : Real.exp 1 ^ 3 - 1 = (Real.exp 1 - 1) * (Real.exp 1 ^ 2 + Real.exp 1 + 1) := by
      ring
    rw [hf]
    exact mul_pos hu1 (by positivity)
  rw [h2, h3, div_lt_div_iff₀ (pow_pos hd3 2) (pow_pos hd2 2)]
  have key : 2 ^ 2 * Real.exp 1 ^ 2 * (Real.exp 1 ^ 3 - 1) ^ 2 =
      3 ^ 2 * Real.exp 1 ^ 3 * (Real.exp 1 ^ 2 - 1) ^ 2 +
        Real.exp 1 ^ 2 * (Real.exp 1 - 1) ^ 4 *
          (4 * Real.exp 1 ^ 2 + 7 * Real.exp 1 + 4) := by
    ring
  rw [key]
  exact lt_add_of_pos_right _ (mul_pos (mul_pos (pow_pos (Real.exp_pos 1) 2) (pow_pos hu1 4))
    (by positivity))

/-- The three mode Gruneisen parameters 1, 2, 3 of the positive family are pairwise distinct. -/
theorem positive_modeGruneisen_injective (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n)
    (q : Fin n) :
    Function.Injective fun b : Fin 3 =>
      (rateModel positiveRates A hA n hn).modeGruneisen q b 1 := by
  intro b c h
  simp only [rate_modeGruneisen, positiveRates, mul_one, add_left_inj, Nat.cast_inj] at h
  exact Fin.ext h

theorem branch_zero_succ : (((0 : Fin 3) : ℕ) : ℝ) + 1 = 1 := by norm_num
theorem branch_one_succ : (((1 : Fin 3) : ℕ) : ℝ) + 1 = 2 := by norm_num
theorem branch_two_succ : (((2 : Fin 3) : ℕ) : ℝ) + 1 = 3 := by norm_num

theorem einsteinWeight_pos {x : ℝ} (hx : 0 < x) :
    0 < x ^ 2 * Real.exp x / (Real.exp x - 1) ^ 2 :=
  div_pos (by positivity) (pow_pos (sub_pos.mpr (Real.one_lt_exp_iff.mpr hx)) 2)

/-- Cancellation of the q count and of kB in the weighted mean. -/
theorem weighted_cancel (N k a0 a1 a2 w0 w1 w2 : ℝ) (hN : N ≠ 0) (hk : k ≠ 0) :
    N * (a0 * (k * w0) + a1 * (k * w1) + a2 * (k * w2)) / (N * (k * w0 + k * w1 + k * w2)) =
      (a0 * w0 + a1 * w1 + a2 * w2) / (w0 + w1 + w2) := by
  rw [mul_div_mul_left _ _ hN,
    show a0 * (k * w0) + a1 * (k * w1) + a2 * (k * w2) = k * (a0 * w0 + a1 * w1 + a2 * w2) by
      ring,
    show k * w0 + k * w1 + k * w2 = k * (w0 + w1 + w2) by ring]
  exact mul_div_mul_left _ _ hk

/-- Gamma at the witness point for every signed rate vector and every n: the rates averaged
with the weights c(1), c(2), c(3) of the reduced frequencies x_b = b + 1. -/
theorem rate_weightedGruneisen_eq (r : Fin 3 → ℝ) (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n) :
    (rateModel r A hA n hn).weightedGruneisen witnessTemperature 1 (one_mem_J r A hA n hn) =
      (r 0 * (1 ^ 2 * Real.exp 1 / (Real.exp 1 - 1) ^ 2) +
          r 1 * (2 ^ 2 * Real.exp 2 / (Real.exp 2 - 1) ^ 2) +
          r 2 * (3 ^ 2 * Real.exp 3 / (Real.exp 3 - 1) ^ 2)) /
        (1 ^ 2 * Real.exp 1 / (Real.exp 1 - 1) ^ 2 +
          2 ^ 2 * Real.exp 2 / (Real.exp 2 - 1) ^ 2 +
          3 ^ 2 * Real.exp 3 / (Real.exp 3 - 1) ^ 2) := by
  have hn0 : (n : ℝ) ≠ 0 := Nat.cast_ne_zero.mpr hn.ne'
  unfold HarmonicVolumeModel.weightedGruneisen
  simp only [rate_modeGruneisen, rate_weight_eq, mul_one]
  simp only [Finset.sum_const, Finset.card_univ, Fintype.card_fin, nsmul_eq_mul]
  rw [Fin.sum_univ_three, Fin.sum_univ_three]
  simp only [branch_zero_succ, branch_one_succ, branch_two_succ]
  exact weighted_cancel _ _ _ _ _ _ _ _ hn0 kB_ne_zero

/-- The actual Physlib weights are strictly ordered, w_0 > w_1 > w_2, for every r and q. -/
theorem rate_weights_strictAnti (r : Fin 3 → ℝ) (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n)
    (q : Fin n) :
    (rateModel r A hA n hn).modeHeatCapacity witnessTemperature 1 (one_mem_J r A hA n hn) q
        (2 : Fin 3) <
      (rateModel r A hA n hn).modeHeatCapacity witnessTemperature 1 (one_mem_J r A hA n hn) q
        (1 : Fin 3) ∧
    (rateModel r A hA n hn).modeHeatCapacity witnessTemperature 1 (one_mem_J r A hA n hn) q
        (1 : Fin 3) <
      (rateModel r A hA n hn).modeHeatCapacity witnessTemperature 1 (one_mem_J r A hA n hn) q
        (0 : Fin 3) := by
  simp only [rate_weight_eq, branch_zero_succ, branch_one_succ, branch_two_succ]
  exact ⟨mul_lt_mul_of_pos_left einsteinWeight_three_lt_two kB_pos,
    mul_lt_mul_of_pos_left einsteinWeight_two_lt_one kB_pos⟩

theorem positive_bounds_of_weights {w0 w1 w2 : ℝ} (h1 : 0 < w1) (h2 : 0 < w2)
    (h20 : w2 < w0) :
    1 < (1 * w0 + 2 * w1 + 3 * w2) / (w0 + w1 + w2) ∧
      (1 * w0 + 2 * w1 + 3 * w2) / (w0 + w1 + w2) < 2 := by
  have hD : 0 < w0 + w1 + w2 := by linarith
  constructor
  · rw [one_lt_div hD]
    linarith
  · rw [div_lt_iff₀ hD]
    linarith

/-- 2 is the arithmetic mean of the mode gammas 1, 2, 3; quantum weights pull Gamma below it. -/
theorem positive_weightedGruneisen_bounds (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n) :
    1 < (rateModel positiveRates A hA n hn).weightedGruneisen witnessTemperature 1
          (one_mem_J positiveRates A hA n hn) ∧
      (rateModel positiveRates A hA n hn).weightedGruneisen witnessTemperature 1
          (one_mem_J positiveRates A hA n hn) < 2 := by
  rw [rate_weightedGruneisen_eq]
  simp only [positiveRates, branch_zero_succ, branch_one_succ, branch_two_succ]
  exact positive_bounds_of_weights (einsteinWeight_pos two_pos) (einsteinWeight_pos three_pos)
    (einsteinWeight_three_lt_two.trans einsteinWeight_two_lt_one)

theorem negative_weightedGruneisen_neg (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n) :
    (rateModel negativeRates A hA n hn).weightedGruneisen witnessTemperature 1
      (one_mem_J negativeRates A hA n hn) < 0 := by
  rw [rate_weightedGruneisen_eq]
  simp only [negativeRates, branch_zero_succ, branch_one_succ, branch_two_succ]
  have h0 := einsteinWeight_pos (one_pos : (0 : ℝ) < 1)
  have h1 := einsteinWeight_pos (two_pos : (0 : ℝ) < 2)
  have h2 := einsteinWeight_pos (three_pos : (0 : ℝ) < 3)
  exact div_neg_of_neg_of_pos (by linarith) (by linarith)

/-- Positive branch: 1 < Gamma < 2 at the branch cell volume and positive expansion. -/
theorem positive_gamma_witness (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n) :
    ∃ B : Response.StableBranchAt (rateModel positiveRates A hA n hn).freeEnergy
        (rateModel positiveRates A hA n hn).domain 0 (witnessTemperature : ℝ),
      B.volume (witnessTemperature : ℝ) = A ∧
      1 < (rateModel positiveRates A hA n hn).weightedGruneisen witnessTemperature
            (B.volume (witnessTemperature : ℝ) / A) B.in_domain.2 ∧
      (rateModel positiveRates A hA n hn).weightedGruneisen witnessTemperature
            (B.volume (witnessTemperature : ℝ) / A) B.in_domain.2 < 2 ∧
      0 < Response.expansion B.volume (witnessTemperature : ℝ) := by
  obtain ⟨B, hB⟩ := rate_branch positiveRates A hA n hn
  have hv : B.volume (witnessTemperature : ℝ) / A = 1 := by
    rw [hB]
    exact div_self hA.ne'
  have hΓ := (rateModel positiveRates A hA n hn).weightedGruneisen_congr witnessTemperature hv
    B.in_domain.2 (one_mem_J positiveRates A hA n hn)
  obtain ⟨h1, h2⟩ := positive_weightedGruneisen_bounds A hA n hn
  have hpos : 0 < (rateModel positiveRates A hA n hn).weightedGruneisen witnessTemperature
      (B.volume (witnessTemperature : ℝ) / A) B.in_domain.2 := by
    rw [hΓ]
    linarith
  refine ⟨B, hB, ?_, ?_, ?_⟩
  · rw [hΓ]
    exact h1
  · rw [hΓ]
    exact h2
  · exact ((rateModel positiveRates A hA n hn).expansion_pos_iff_weightedGruneisen_pos 0
      witnessTemperature B).mpr hpos

/-- Negative branch: increasing frequencies give Gamma < 0 and negative expansion. -/
theorem negative_gamma_witness (A : ℝ) (hA : 0 < A) (n : ℕ) (hn : 0 < n) :
    ∃ B : Response.StableBranchAt (rateModel negativeRates A hA n hn).freeEnergy
        (rateModel negativeRates A hA n hn).domain 0 (witnessTemperature : ℝ),
      B.volume (witnessTemperature : ℝ) = A ∧
      (rateModel negativeRates A hA n hn).weightedGruneisen witnessTemperature
            (B.volume (witnessTemperature : ℝ) / A) B.in_domain.2 < 0 ∧
      Response.expansion B.volume (witnessTemperature : ℝ) < 0 := by
  obtain ⟨B, hB⟩ := rate_branch negativeRates A hA n hn
  have hv : B.volume (witnessTemperature : ℝ) / A = 1 := by
    rw [hB]
    exact div_self hA.ne'
  have hΓ := (rateModel negativeRates A hA n hn).weightedGruneisen_congr witnessTemperature hv
    B.in_domain.2 (one_mem_J negativeRates A hA n hn)
  have hneg : (rateModel negativeRates A hA n hn).weightedGruneisen witnessTemperature
      (B.volume (witnessTemperature : ℝ) / A) B.in_domain.2 < 0 := by
    rw [hΓ]
    exact negative_weightedGruneisen_neg A hA n hn
  exact ⟨B, hB, hneg, ((rateModel negativeRates A hA n hn).expansion_neg_iff_weightedGruneisen_neg
    0 witnessTemperature B).mpr hneg⟩

/-- Constant frequencies: every mode gamma vanishes, so Gamma = 0 at every T and v. -/
theorem zeroModel_weightedGruneisen (A : ℝ) (hA : 0 < A) (T : Temperature) (v : ℝ)
    (hv : v ∈ (Response.zeroModel A hA).J) :
    (Response.zeroModel A hA).weightedGruneisen T v hv = 0 := by
  have hγ : ∀ q b, (Response.zeroModel A hA).modeGruneisen q b v = 0 := by
    intro q b
    change -(v * deriv (fun _ : ℝ => (b.val : ℝ) + 1) v) / ((b.val : ℝ) + 1) = 0
    rw [deriv_const, mul_zero, neg_zero, zero_div]
  simp only [HarmonicVolumeModel.weightedGruneisen, hγ, zero_mul, Finset.sum_const_zero,
    zero_div]

/-- The existing stable constant-frequency control: zero expansion and Gamma = 0. -/
theorem zero_gamma_control (A : ℝ) (hA : 0 < A) :
    ∃ B : Response.StableBranchAt (Response.zeroModel A hA).freeEnergy
        (Response.zeroModel A hA).domain 0 1,
      B.volume 1 = A ∧ Response.expansion B.volume 1 = 0 ∧
      ∀ (T : Temperature) (v : ℝ) (hv : v ∈ (Response.zeroModel A hA).J),
        (Response.zeroModel A hA).weightedGruneisen T v hv = 0 := by
  obtain ⟨B, hB, ha, -⟩ := Response.zero_response_control A hA
  exact ⟨B, hB, ha, zeroModel_weightedGruneisen A hA⟩

/-- Literal non-unit instance: A = 3 and two reduced q points. -/
theorem positive_gamma_witness_nonunit :
    ∃ B : Response.StableBranchAt (rateModel positiveRates 3 three_pos 2 two_pos).freeEnergy
        (rateModel positiveRates 3 three_pos 2 two_pos).domain 0 (witnessTemperature : ℝ),
      B.volume (witnessTemperature : ℝ) = 3 ∧
      1 < (rateModel positiveRates 3 three_pos 2 two_pos).weightedGruneisen witnessTemperature
            (B.volume (witnessTemperature : ℝ) / 3) B.in_domain.2 ∧
      (rateModel positiveRates 3 three_pos 2 two_pos).weightedGruneisen witnessTemperature
            (B.volume (witnessTemperature : ℝ) / 3) B.in_domain.2 < 2 ∧
      0 < Response.expansion B.volume (witnessTemperature : ℝ) :=
  positive_gamma_witness 3 three_pos 2 two_pos

end OMAI.PhyslibBridge.GruneisenWitness
