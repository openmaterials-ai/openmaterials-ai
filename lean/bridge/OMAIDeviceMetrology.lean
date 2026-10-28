module

public import Mathlib.Analysis.SpecialFunctions.Gamma.Basic
public import Mathlib.Analysis.SpecialFunctions.Gamma.BohrMollerup
public import Mathlib.Analysis.SpecialFunctions.ImproperIntegrals
public import Mathlib.Analysis.SpecialFunctions.Pow.Deriv
public import Mathlib.MeasureTheory.Integral.IntegralEqImproper
public import Mathlib.MeasureTheory.Measure.Haar.NormedSpace
public import Mathlib.NumberTheory.Harmonic.GammaDeriv
public import Mathlib.Tactic

/-!
# Analog device metrology formulas

The catalog's analog-device-metrology operators are closed forms. Physlib has no model
of a memristive or Schottky device, so these results use Mathlib only and identify no
Physlib declaration.

* The conductance drift law is invariant under a change of reference time, and its
  exponent is minus the slope of `log G` against `log t`.
* The thermionic conductance is the zero-bias slope of the Richardson current; with an
  ideality factor `n` the slope is `G / n` in one current form and `G` in the other, and
  the barrier is recovered exactly from conductances at two temperatures.
* The retention time is the mean exit time of a constant-rate escape, divided by `M` for
  `M` exit paths, and the barrier is recovered from retention times at two temperatures.
* Under a voltage ramp the expected hop count from zero to `V` is the leading term minus
  `g_r k_B T / (alpha_F tau_ret)`; the leading term equals one at the catalog's location
  `V*`, and the minimum-Gumbel law of the first hop has mean `V* - gamma k_B T / alpha_F`,
  the catalog's set voltage.
* The programming error equals the per-cell model it was written from, decreases strictly
  as the conductance window widens, tends to `c sqrt(S_2 / 2) / S_1`, and exceeds
  `c / sqrt(2 n_w)` for every kernel and window.
* For a pulse during which the conductance changes monotonically, the dissipated energy
  lies between the catalog's energy at the initial and at the final conductance.
* For a channel of segments in series, the catalog conductance with the length-averaged
  conductivity is an upper bound on the true conductance.

No result validates a measured parameter, a fit or a device simulation.
-/

@[expose] public section

noncomputable section

open Real MeasureTheory Set Filter Topology

namespace OMAI.PhyslibBridge.DeviceMetrology

/-! ## Catalog transcriptions -/

/-- The reviewed catalog expression of `apply_conductance_drift`,
`G_c = G_0 / (t_d / t_{d,0})^nu`, with input ConductanceDriftExponent and parameters
`G_0`, `t_d`, `t_{d,0}`. This definition alone is not a physical proof. -/
def driftConductance (nu G0 td td0 : ℝ) : ℝ := G0 / (td / td0) ^ nu

/-- The reviewed catalog expression of `emit_thermionic_conductance`,
`G_c = P_th T q_e exp(-Phi_Bn / (T k_B)) / k_B`. This definition alone is not a physical
proof. -/
def thermionicConductance (PhiBn T Pth qe kB : ℝ) : ℝ :=
  Pth * T * qe * exp (-PhiBn / (T * kB)) / kB

/-- The reviewed catalog expression of `zero_bias_retention`,
`tau_ret = exp(E_m / (T k_B)) / nu_0`. This definition alone is not a physical proof. -/
def retentionTime (Em T nu0 kB : ℝ) : ℝ := exp (Em / (T * kB)) / nu0

/-- The reviewed catalog expression of `ramp_set_voltage`,
`V_set = -gamma T k_B / alpha_F + (E_m - T k_B log(T g_r k_B nu_0 / alpha_F)) / alpha_F`,
with `gamma` the Euler-Mascheroni constant. This definition alone is not a physical
proof. -/
def rampSetVoltage (Em T alphaF nu0 gr kB : ℝ) : ℝ :=
  -(eulerMascheroniConstant * T * kB) / alphaF +
    (Em - T * kB * log (T * gr * kB * nu0 / alphaF)) / alphaF

/-- The reviewed catalog expression of `propagate_programming_error`,
`eps = c_G sqrt(S_1 w_max / (W_G - 1) + S_2 / 2 + n_w w_max^2 / (2 (W_G - 1)^2)) / S_1`.
This definition alone is not a physical proof. -/
def programmingError (cG WG nw wmax S1 S2 : ℝ) : ℝ :=
  cG * sqrt (S1 * wmax / (WG - 1) + S2 / 2 + nw * wmax ^ 2 / (2 * (WG - 1) ^ 2)) / S1

/-- The reviewed catalog expression of `dissipate_pulse_energy`, `E_pulse = G_c V_p^2 t_p`.
This definition alone is not a physical proof. -/
def pulseEnergy (Gc Vp tp : ℝ) : ℝ := Gc * Vp ^ 2 * tp

/-- The reviewed catalog expression of `contract_device_conductance`,
`G_c = A_g sigma_el / L_g`. This definition alone is not a physical proof. -/
def deviceConductance (sigma Ag Lg : ℝ) : ℝ := Ag * sigma / Lg

/-! ## Conductance drift -/

/-- Drifting from `t_{d,0}` to `t_1` and then, with the value at `t_1` as the new
reference, from `t_1` to `t_2` gives the same conductance as drifting from `t_{d,0}` to
`t_2`: the power law does not depend on the choice of reference time. -/
theorem driftConductance_rereference (nu G0 : ℝ) {td0 t1 t2 : ℝ} (h0 : 0 < td0) (h1 : 0 < t1)
    (h2 : 0 < t2) :
    driftConductance nu (driftConductance nu G0 t1 td0) t2 t1 = driftConductance nu G0 t2 td0 := by
  unfold driftConductance
  have hb : t2 / td0 = (t1 / td0) * (t2 / t1) := by field_simp
  rw [hb, mul_rpow (by positivity) (by positivity)]
  have ha : 0 < (t1 / td0) ^ nu := by positivity
  have hc : 0 < (t2 / t1) ^ nu := by positivity
  field_simp

/-- The drift exponent is minus the slope of `log G` against `log t_d`, at every time. -/
theorem driftConductance_logSlope (nu : ℝ) {G0 td0 : ℝ} (hG : G0 ≠ 0) (h0 : 0 < td0) (u : ℝ) :
    HasDerivAt (fun u => log (driftConductance nu G0 (exp u) td0)) (-nu) u := by
  have h : (fun u => log (driftConductance nu G0 (exp u) td0)) =
      fun u => log G0 - nu * (u - log td0) := by
    funext u
    unfold driftConductance
    have hx : 0 < exp u / td0 := by positivity
    rw [log_div hG (rpow_pos_of_pos hx nu).ne', log_rpow hx, log_div (exp_pos u).ne' h0.ne',
      log_exp]
  rw [h]
  have := ((hasDerivAt_id' u).sub_const (log td0)).const_mul nu
  simpa using this.const_sub (log G0)

/-! ## Thermionic emission -/

/-- The Richardson-Dushman current of one Schottky contact,
`I(V) = P_th T^2 exp(-Phi_Bn / (k_B T)) (exp(q_e V / (k_B T)) - 1)`. -/
def thermionicCurrent (PhiBn T Pth qe kB V : ℝ) : ℝ :=
  Pth * T ^ 2 * exp (-PhiBn / (kB * T)) * (exp (qe * V / (kB * T)) - 1)

/-- The catalog's thermionic conductance is the zero-bias slope of the Richardson-Dushman
current. -/
theorem thermionicConductance_eq_zeroBiasSlope (PhiBn Pth qe : ℝ) {T kB : ℝ} (hT : 0 < T)
    (hk : 0 < kB) :
    HasDerivAt (thermionicCurrent PhiBn T Pth qe kB)
      (thermionicConductance PhiBn T Pth qe kB) 0 := by
  have hexp := ((hasDerivAt_id' (0 : ℝ)).const_mul (qe / (kB * T))).exp
  have := (hexp.sub_const 1).const_mul (Pth * T ^ 2 * exp (-PhiBn / (kB * T)))
  unfold thermionicCurrent thermionicConductance
  have hx : -PhiBn / (T * kB) = -PhiBn / (kB * T) := by ring
  convert this using 1
  · funext V; congr 3; ring
  · rw [hx]; field_simp; simp

/-- With an ideality factor `n`, the current `I_s (exp(q_e V / (n k_B T)) - 1)` has
zero-bias slope `G / n`, while `I_s exp(q_e V / (n k_B T)) (1 - exp(-q_e V / (k_B T)))`
has zero-bias slope `G` for every `n`, where `I_s = P_th T^2 exp(-Phi_Bn / (k_B T))` and
`G` is the catalog's thermionic conductance. -/
theorem thermionicConductance_ideality (PhiBn Pth qe : ℝ) {T kB n : ℝ} (hT : 0 < T)
    (hk : 0 < kB) (hn : 0 < n) :
    HasDerivAt (fun V => Pth * T ^ 2 * exp (-PhiBn / (kB * T)) *
        (exp (qe * V / (n * kB * T)) - 1)) (thermionicConductance PhiBn T Pth qe kB / n) 0 ∧
      HasDerivAt (fun V => Pth * T ^ 2 * exp (-PhiBn / (kB * T)) *
        (exp (qe * V / (n * kB * T)) * (1 - exp (-(qe * V) / (kB * T)))))
        (thermionicConductance PhiBn T Pth qe kB) 0 := by
  have hG : thermionicConductance PhiBn T Pth qe kB =
      Pth * T ^ 2 * exp (-PhiBn / (kB * T)) * (qe / (kB * T)) := by
    unfold thermionicConductance
    have hx : -PhiBn / (T * kB) = -PhiBn / (kB * T) := by ring
    rw [hx]; field_simp
  have ea := ((hasDerivAt_id' (0 : ℝ)).const_mul (qe / (n * kB * T))).exp
  have eb := ((hasDerivAt_id' (0 : ℝ)).const_mul (-qe / (kB * T))).exp
  constructor
  · have := (ea.sub_const 1).const_mul (Pth * T ^ 2 * exp (-PhiBn / (kB * T)))
    convert this using 1
    · funext V; congr 3; ring
    · rw [hG]; field_simp; simp
  · have := (ea.mul (eb.const_sub 1)).const_mul (Pth * T ^ 2 * exp (-PhiBn / (kB * T)))
    convert this using 1
    · funext V; simp only [Pi.mul_apply]; congr 4 <;> ring_nf
    · rw [hG]; simp; field_simp

/-- The barrier height is recovered exactly from the catalog's thermionic conductance at
two different temperatures: `Phi_Bn = k_B log((G_1 / T_1) / (G_2 / T_2)) / (1/T_2 - 1/T_1)`,
whatever the prefactor `P_th`. -/
theorem thermionic_barrier_two_temperatures (PhiBn : ℝ) {T1 T2 Pth qe kB : ℝ} (h1 : 0 < T1)
    (h2 : 0 < T2) (hne : T1 ≠ T2) (hP : 0 < Pth) (hq : 0 < qe) (hk : 0 < kB) :
    PhiBn = kB * log ((thermionicConductance PhiBn T1 Pth qe kB / T1) /
      (thermionicConductance PhiBn T2 Pth qe kB / T2)) / (1 / T2 - 1 / T1) := by
  have hratio : (thermionicConductance PhiBn T1 Pth qe kB / T1) /
      (thermionicConductance PhiBn T2 Pth qe kB / T2) =
        exp (-PhiBn / (T1 * kB) - -PhiBn / (T2 * kB)) := by
    unfold thermionicConductance
    rw [exp_sub]
    have e1 := exp_pos (-PhiBn / (T1 * kB))
    have e2 := exp_pos (-PhiBn / (T2 * kB))
    field_simp
  rw [hratio, log_exp]
  have hd : 1 / T2 - 1 / T1 ≠ 0 := by
    intro h; apply hne; field_simp at h; linarith
  field_simp
  ring

/-! ## Retention -/

/-- The mean exit time of a state that leaves by `M` equivalent paths, each at the
Arrhenius rate `k = nu_0 exp(-E_m / (k_B T))`, is the catalog's retention time divided
by `M`: the exit time has density `M k exp(-M k t)` and mean `1 / (M k)`. -/
theorem retentionTime_mean_exit (Em T kB : ℝ) {nu0 : ℝ} {M : ℕ} (hM : 0 < M) (hnu : 0 < nu0) :
    ∫ t in Ioi 0, t * ((M * (nu0 * exp (-Em / (T * kB)))) *
        exp (-((M * (nu0 * exp (-Em / (T * kB)))) * t))) =
      retentionTime Em T nu0 kB / M := by
  set r := (M : ℝ) * (nu0 * exp (-Em / (T * kB)))
  have hr : 0 < r := by positivity
  have hint := integral_rpow_mul_exp_neg_mul_Ioi (a := 2) (by norm_num) hr
  norm_num [Gamma_two] at hint
  have hcongr : (∫ t in Ioi 0, t * (r * exp (-(r * t)))) = r * ∫ t in Ioi 0, t * exp (-(r * t)) := by
    rw [← integral_const_mul]; congr 1; funext t; ring
  rw [hcongr, hint]
  unfold retentionTime
  have he : exp (Em / (T * kB)) = (exp (-Em / (T * kB)))⁻¹ := by
    rw [← exp_neg]; congr 1; ring
  rw [he]
  have hM' : (0 : ℝ) < M := by exact_mod_cast hM
  have := exp_pos (-Em / (T * kB))
  simp only [r]
  field_simp

/-- The migration barrier is recovered exactly from the catalog's retention times at two
different temperatures, `E_m = k_B log(tau_1 / tau_2) / (1/T_1 - 1/T_2)`, whatever the
attempt frequency; at one temperature `E_m` and `nu_0` cannot be separated. -/
theorem retention_barrier_two_temperatures (Em : ℝ) {T1 T2 nu0 kB : ℝ} (h1 : 0 < T1)
    (h2 : 0 < T2) (hne : T1 ≠ T2) (hnu : 0 < nu0) (hk : 0 < kB) :
    Em = kB * log (retentionTime Em T1 nu0 kB / retentionTime Em T2 nu0 kB) / (1 / T1 - 1 / T2) := by
  have hratio : retentionTime Em T1 nu0 kB / retentionTime Em T2 nu0 kB =
      exp (Em / (T1 * kB) - Em / (T2 * kB)) := by
    unfold retentionTime
    rw [exp_sub]
    have := exp_pos (Em / (T2 * kB))
    field_simp
  rw [hratio, log_exp]
  have hd : 1 / T1 - 1 / T2 ≠ 0 := by
    intro h; apply hne; field_simp at h; linarith
  field_simp

/-! ## Set voltage under a ramp -/

/-- Hop rate at bias `V`, `nu_0 exp(-(E_m - alpha_F V) / (k_B T))`. -/
def hopRate (Em T alphaF nu0 kB V : ℝ) : ℝ := nu0 * exp (-(Em - alphaF * V) / (kB * T))

/-- Leading term of the expected hop count under the ramp,
`g_r nu_0 (k_B T / alpha_F) exp((alpha_F V - E_m) / (k_B T))`. -/
def leadingHops (Em T alphaF nu0 gr kB V : ℝ) : ℝ :=
  T * gr * kB * nu0 / alphaF * exp ((alphaF * V - Em) / (kB * T))

/-- The location `V* = (E_m - T k_B log(T g_r k_B nu_0 / alpha_F)) / alpha_F`. -/
def rampLocation (Em T alphaF nu0 gr kB : ℝ) : ℝ :=
  (Em - T * kB * log (T * gr * kB * nu0 / alphaF)) / alphaF

theorem leadingHops_hasDerivAt (Em gr nu0 : ℝ) {T alphaF kB : ℝ} (hT : 0 < T) (ha : 0 < alphaF)
    (hk : 0 < kB) (V : ℝ) :
    HasDerivAt (leadingHops Em T alphaF nu0 gr kB) (gr * hopRate Em T alphaF nu0 kB V) V := by
  have := (((hasDerivAt_id V).const_mul alphaF).sub_const Em).div_const (kB * T) |>.exp
  have h := this.const_mul (T * gr * kB * nu0 / alphaF)
  unfold leadingHops hopRate
  convert h using 1
  · funext v; simp
  · have hx : -(Em - alphaF * V) / (kB * T) = (alphaF * id V - Em) / (kB * T) := by
      simp only [id]; ring
    rw [hx]; field_simp

/-- Under a ramp with dwell `g_r` per volt, the expected number of hops between zero bias
and `V` is the leading term minus `g_r k_B T / (alpha_F tau_ret)`, where `tau_ret` is the
catalog's retention time at the same barrier, temperature and attempt frequency. -/
theorem ramp_expectedHops (Em gr nu0 : ℝ) {T alphaF kB : ℝ} (hT : 0 < T) (ha : 0 < alphaF)
    (hk : 0 < kB) (hnu : 0 < nu0) (V : ℝ) :
    ∫ v in (0)..V, gr * hopRate Em T alphaF nu0 kB v =
      leadingHops Em T alphaF nu0 gr kB V -
        gr * kB * T / (alphaF * retentionTime Em T nu0 kB) := by
  rw [intervalIntegral.integral_eq_sub_of_hasDerivAt
    (fun v _ => leadingHops_hasDerivAt Em gr nu0 hT ha hk v)]
  · congr 1
    unfold leadingHops retentionTime
    have he : exp (Em / (T * kB)) = (exp ((alphaF * 0 - Em) / (kB * T)))⁻¹ := by
      rw [← exp_neg]; congr 1; ring
    rw [he]
    have := exp_pos ((alphaF * 0 - Em) / (kB * T))
    field_simp
  · apply Continuous.intervalIntegrable
    unfold hopRate
    fun_prop

/-- The leading hop count is `exp((V - V*) / b)` with `b = k_B T / alpha_F`; in
particular it equals one at the catalog's location `V*`. -/
theorem leadingHops_eq_exp (Em gr : ℝ) {T alphaF nu0 kB : ℝ} (hT : 0 < T) (ha : 0 < alphaF)
    (hk : 0 < kB) (hnu : 0 < nu0) (hg : 0 < gr) (V : ℝ) :
    leadingHops Em T alphaF nu0 gr kB V =
      exp ((V - rampLocation Em T alphaF nu0 gr kB) / (kB * T / alphaF)) := by
  have hc : 0 < T * gr * kB * nu0 / alphaF := by positivity
  unfold leadingHops rampLocation
  have hx : (V - (Em - T * kB * log (T * gr * kB * nu0 / alphaF)) / alphaF) / (kB * T / alphaF) =
      (alphaF * V - Em) / (kB * T) + log (T * gr * kB * nu0 / alphaF) := by
    field_simp; ring
  rw [hx, exp_add, exp_log hc]
  ring

private theorem abs_log_le (y : ℝ) (hy : 0 < y) :
    |log y| ≤ 2 * y ^ ((1 : ℝ) / 2 - 1) + y := by
  rcases le_or_gt y 1 with h1 | h1
  · have h := abs_log_mul_self_rpow_lt y (1 / 2) hy h1 (by norm_num)
    have hp : 0 < y ^ ((1 : ℝ) / 2) := rpow_pos_of_pos hy _
    have hsplit : y ^ ((1 : ℝ) / 2 - 1) = y ^ ((1 : ℝ) / 2) / y := by
      rw [rpow_sub hy, rpow_one]
    rw [abs_mul, abs_of_pos hp] at h
    rw [hsplit]
    have hlog : |log y| < 2 / y ^ ((1 : ℝ) / 2) := by
      rw [lt_div_iff₀ hp]; linarith
    have hsq : y ^ ((1 : ℝ) / 2) * y ^ ((1 : ℝ) / 2) = y := by
      rw [← rpow_add hy]; norm_num
    have : 2 / y ^ ((1 : ℝ) / 2) = 2 * (y ^ ((1 : ℝ) / 2) / y) := by
      field_simp; linarith [hsq]
    linarith
  · have hl : 0 ≤ log y := log_nonneg h1.le
    rw [abs_of_nonneg hl]
    have := log_le_sub_one_of_pos hy
    have : 0 ≤ 2 * y ^ ((1 : ℝ) / 2 - 1) := by positivity
    linarith

private theorem integrableOn_log_mul_exp_neg :
    IntegrableOn (fun y => log y * exp (-y)) (Ioi 0) := by
  have h1 := GammaIntegral_convergent (s := 1 / 2) (by norm_num)
  have h2 := GammaIntegral_convergent (s := 2) (by norm_num)
  have hdom : IntegrableOn (fun y : ℝ => 2 * (exp (-y) * y ^ ((1 : ℝ) / 2 - 1)) +
      exp (-y) * y ^ ((2 : ℝ) - 1)) (Ioi 0) := (h1.const_mul 2).add h2
  refine hdom.mono' ?_ ?_
  · exact (ContinuousOn.mul (continuousOn_log.mono (fun y hy => ne_of_gt (mem_Ioi.mp hy)))
      (continuous_exp.comp continuous_neg).continuousOn).aestronglyMeasurable measurableSet_Ioi
  · refine (ae_restrict_iff' measurableSet_Ioi).mpr (Eventually.of_forall fun y hy => ?_)
    have hy' : 0 < y := hy
    rw [norm_mul, Real.norm_eq_abs, Real.norm_eq_abs, abs_of_pos (exp_pos _)]
    have hb := abs_log_le y hy'
    have : y ^ ((2 : ℝ) - 1) = y := by norm_num
    rw [this]
    nlinarith [exp_pos (-y)]

private theorem gumbel_moments :
    (∫ x : ℝ, exp x * exp (-exp x)) = 1 ∧
      (∫ x : ℝ, x * exp x * exp (-exp x)) = -eulerMascheroniConstant := by
  constructor
  · have := integral_comp_exp (fun y => exp (-y))
    simp only [smul_eq_mul] at this
    rw [this, integral_exp_neg_Ioi_zero]
  · have := integral_comp_exp (fun y => log y * exp (-y))
    simp only [smul_eq_mul, log_exp] at this
    rw [eulerMascheroniConstant_eq_neg_integral_log, neg_neg, ← this]
    congr 1; funext x; ring

private theorem gumbel_integrable :
    Integrable (fun x : ℝ => exp x * exp (-exp x)) ∧
      Integrable (fun x : ℝ => x * exp x * exp (-exp x)) := by
  constructor
  · have := (integrable_comp_exp (fun y => exp (-y))).mpr (integrableOn_exp_neg_Ioi 0)
    simpa only [smul_eq_mul] using this
  · have := (integrable_comp_exp (fun y => log y * exp (-y))).mpr integrableOn_log_mul_exp_neg
    simp only [smul_eq_mul, log_exp] at this
    refine this.congr (Eventually.of_forall fun x => ?_)
    simp only; ring

/-- If the first hop under the ramp has the survival `exp(-N(V))` of the leading hop count
`N(V) = exp((V - V*) / b)`, `b = k_B T / alpha_F`, its density is
`(1/b) exp((V - V*)/b) exp(-exp((V - V*)/b))` (a minimum-Gumbel law) and its mean is the
catalog's set voltage `V* - gamma b`. -/
theorem ramp_meanSetVoltage (Em gr : ℝ) {T alphaF nu0 kB : ℝ} (hT : 0 < T) (ha : 0 < alphaF)
    (hk : 0 < kB) (hnu : 0 < nu0) (hg : 0 < gr) :
    (∀ v, HasDerivAt (fun V => 1 - exp (-leadingHops Em T alphaF nu0 gr kB V))
      (1 / (kB * T / alphaF) *
        exp ((v - rampLocation Em T alphaF nu0 gr kB) / (kB * T / alphaF)) *
          exp (-exp ((v - rampLocation Em T alphaF nu0 gr kB) / (kB * T / alphaF)))) v) ∧
      ∫ v, v * (1 / (kB * T / alphaF) *
        exp ((v - rampLocation Em T alphaF nu0 gr kB) / (kB * T / alphaF)) *
          exp (-exp ((v - rampLocation Em T alphaF nu0 gr kB) / (kB * T / alphaF)))) =
        rampSetVoltage Em T alphaF nu0 gr kB := by
  set b := kB * T / alphaF with hbdef
  set c := rampLocation Em T alphaF nu0 gr kB
  have hb : 0 < b := by positivity
  have hN : leadingHops Em T alphaF nu0 gr kB = fun V => exp ((V - c) / b) := by
    funext V; exact leadingHops_eq_exp Em gr hT ha hk hnu hg V
  constructor
  · intro v
    rw [hN]
    have h1 : HasDerivAt (fun x => (x - c) / b) (1 / b) v := by
      simpa using ((hasDerivAt_id' v).sub_const c).div_const b
    have h2 : HasDerivAt (fun x => -exp ((x - c) / b)) (-(exp ((v - c) / b) * (1 / b))) v :=
      h1.exp.neg
    have h3 := (h2.exp).const_sub 1
    convert h3 using 1
    ring
  · obtain ⟨m0, m1⟩ := gumbel_moments
    obtain ⟨i0, i1⟩ := gumbel_integrable
    have hshift : (∫ v, v * (1 / b * exp ((v - c) / b) * exp (-exp ((v - c) / b)))) =
        ∫ x, (x + c) * (1 / b * exp (x / b) * exp (-exp (x / b))) := by
      rw [← integral_add_right_eq_self (fun v => v * (1 / b * exp ((v - c) / b) *
        exp (-exp ((v - c) / b)))) c]
      simp only [add_sub_cancel_right]
    have hscale : (∫ x, (x + c) * (1 / b * exp (x / b) * exp (-exp (x / b)))) =
        ∫ y, (b * y + c) * exp y * exp (-exp y) := by
      have := Measure.integral_comp_mul_left (fun y => (b * y + c) * (1 / b * exp y * exp (-exp y))) b⁻¹
      simp only [inv_inv, abs_of_pos hb, smul_eq_mul] at this
      have hl : (fun x => (x + c) * (1 / b * exp (x / b) * exp (-exp (x / b)))) =
          fun x => (b * (b⁻¹ * x) + c) * (1 / b * exp (b⁻¹ * x) * exp (-exp (b⁻¹ * x))) := by
        funext x; field_simp
      rw [hl, this, ← integral_const_mul]
      congr 1; funext y; field_simp
    rw [hshift, hscale]
    have hsplit : (fun y => (b * y + c) * exp y * exp (-exp y)) =
        fun y => b * (y * exp y * exp (-exp y)) + c * (exp y * exp (-exp y)) := by
      funext y; ring
    rw [hsplit, integral_add (i1.const_mul b) (i0.const_mul c), integral_const_mul,
      integral_const_mul, m0, m1]
    simp only [c, rampLocation, rampSetVoltage, hbdef]
    field_simp

/-! ## Programming error -/

/-- The catalog's programming error is the per-cell model it was written from:
`eps = c sqrt(sum_i (1/r + |w_i|)^2 / 2) / sum_i |w_i|` with `1/r = w_max / (W - 1)`,
over the nonzero kernel weights `w_i`. -/
theorem programmingError_eq_cells {n : ℕ} (w : Fin n → ℝ) (cG WG wmax : ℝ) (hW : WG ≠ 1) :
    programmingError cG WG n wmax (∑ i, |w i|) (∑ i, w i ^ 2) =
      cG * sqrt ((∑ i, (wmax / (WG - 1) + |w i|) ^ 2) / 2) / ∑ i, |w i| := by
  unfold programmingError
  have hW1 : WG - 1 ≠ 0 := sub_ne_zero.mpr hW
  have hsum : ∑ i, (wmax / (WG - 1) + |w i|) ^ 2 =
      n * (wmax / (WG - 1)) ^ 2 + 2 * (wmax / (WG - 1)) * ∑ i, |w i| + ∑ i, w i ^ 2 := by
    simp only [add_sq, Finset.sum_add_distrib, Finset.sum_const, Finset.card_univ,
      Fintype.card_fin, nsmul_eq_mul, sq_abs, Finset.mul_sum]
  rw [hsum]
  congr 3
  field_simp
  ring

/-- The catalog's programming error decreases strictly as the conductance window widens. -/
theorem programmingError_strictAntiOn {cG nw wmax S1 S2 : ℝ} (hc : 0 < cG) (hn : 0 ≤ nw)
    (hw : 0 < wmax) (hS1 : 0 < S1) (hS2 : 0 ≤ S2) :
    StrictAntiOn (fun W => programmingError cG W nw wmax S1 S2) (Ioi 1) := by
  intro W1 h1 W2 h2 hlt
  simp only [mem_Ioi] at h1 h2
  unfold programmingError
  have d1 : 0 < W1 - 1 := by linarith
  have d2 : 0 < W2 - 1 := by linarith
  have hR : S1 * wmax / (W2 - 1) + S2 / 2 + nw * wmax ^ 2 / (2 * (W2 - 1) ^ 2) <
      S1 * wmax / (W1 - 1) + S2 / 2 + nw * wmax ^ 2 / (2 * (W1 - 1) ^ 2) := by
    have a : S1 * wmax / (W2 - 1) < S1 * wmax / (W1 - 1) :=
      div_lt_div_of_pos_left (by positivity) d1 (by linarith)
    have b : nw * wmax ^ 2 / (2 * (W2 - 1) ^ 2) ≤ nw * wmax ^ 2 / (2 * (W1 - 1) ^ 2) :=
      div_le_div_of_nonneg_left (by positivity) (by positivity) (by nlinarith)
    linarith
  have hpos : 0 ≤ S1 * wmax / (W2 - 1) + S2 / 2 + nw * wmax ^ 2 / (2 * (W2 - 1) ^ 2) := by
    positivity
  have hs := sqrt_lt_sqrt hpos hR
  have := mul_lt_mul_of_pos_left hs hc
  exact div_lt_div_of_pos_right this hS1

/-- As the conductance window grows without bound, the catalog's programming error tends to
the floor `c sqrt(S_2 / 2) / S_1` set by the kernel alone. -/
theorem tendsto_programmingError (cG nw wmax S1 S2 : ℝ) :
    Tendsto (fun W => programmingError cG W nw wmax S1 S2) atTop (𝓝 (cG * sqrt (S2 / 2) / S1)) := by
  unfold programmingError
  have hinv : Tendsto (fun W : ℝ => (W - 1)⁻¹) atTop (𝓝 0) :=
    tendsto_inv_atTop_zero.comp (tendsto_atTop_add_const_right _ (-1) tendsto_id)
  have hR : Tendsto (fun W : ℝ => S1 * wmax / (W - 1) + S2 / 2 + nw * wmax ^ 2 / (2 * (W - 1) ^ 2))
      atTop (𝓝 (S2 / 2)) := by
    have h1 : Tendsto (fun W : ℝ => S1 * wmax * (W - 1)⁻¹) atTop (𝓝 0) := by
      simpa using hinv.const_mul (S1 * wmax)
    have h2 : Tendsto (fun W : ℝ => nw * wmax ^ 2 / 2 * ((W - 1)⁻¹) ^ 2) atTop (𝓝 0) := by
      simpa using (hinv.pow 2).const_mul (nw * wmax ^ 2 / 2)
    have := (h1.add_const (S2 / 2)).add h2
    simp only [zero_add, add_zero] at this
    refine this.congr (fun W => ?_)
    simp only [div_eq_mul_inv, mul_inv, inv_pow]
    ring
  exact ((hR.sqrt).const_mul cG).div_const S1

/-- For every kernel of `n_w` nonzero weights and every window `W > 1`, the catalog's
programming error exceeds `c / sqrt(2 n_w)` (the kernel floor `c sqrt(S_2/2)/S_1` is at
least `c / sqrt(2 n_w)` by the Cauchy-Schwarz inequality `S_1^2 <= n_w S_2`). -/
theorem programmingError_gt (n : ℕ) (hn : 0 < n) (w : Fin n → ℝ) (hw0 : ∀ i, w i ≠ 0)
    {cG WG wmax : ℝ} (hc : 0 < cG) (hW : 1 < WG) (hw : 0 < wmax) :
    cG / sqrt (2 * n) < programmingError cG WG n wmax (∑ i, |w i|) (∑ i, w i ^ 2) := by
  set S1 := ∑ i, |w i|
  set S2 := ∑ i, w i ^ 2
  have hne : (Finset.univ : Finset (Fin n)).Nonempty := Finset.univ_nonempty_iff.mpr ⟨⟨0, hn⟩⟩
  have hS1 : 0 < S1 := Finset.sum_pos (fun i _ => abs_pos.mpr (hw0 i)) hne
  have hS2 : 0 ≤ S2 := Finset.sum_nonneg (fun i _ => sq_nonneg _)
  have hn' : (0 : ℝ) < n := by exact_mod_cast hn
  have hCS : S1 ^ 2 ≤ n * S2 := by
    have := Finset.sum_mul_sq_le_sq_mul_sq Finset.univ (fun _ => (1 : ℝ)) (fun i => |w i|)
    simpa [S1, S2, sq_abs] using this
  have hd : 0 < WG - 1 := by linarith
  have hfloor : cG / sqrt (2 * n) ≤ cG * sqrt (S2 / 2) / S1 := by
    have hs : 0 < sqrt (2 * n) := sqrt_pos.mpr (by positivity)
    rw [div_le_div_iff₀ hs hS1, mul_assoc]
    apply mul_le_mul_of_nonneg_left _ hc.le
    rw [← sqrt_mul (by positivity)]
    apply le_sqrt_of_sq_le
    have : S2 / 2 * (2 * n) = n * S2 := by ring
    rw [this]; exact hCS
  have hstrict : cG * sqrt (S2 / 2) / S1 < programmingError cG WG n wmax S1 S2 := by
    unfold programmingError
    apply div_lt_div_of_pos_right _ hS1
    apply mul_lt_mul_of_pos_left _ hc
    apply sqrt_lt_sqrt (by positivity)
    have : 0 < S1 * wmax / (WG - 1) := by positivity
    have : 0 ≤ (n : ℝ) * wmax ^ 2 / (2 * (WG - 1) ^ 2) := by positivity
    linarith
  exact lt_of_le_of_lt hfloor hstrict

/-! ## Pulse energy -/

/-- For a pulse of width `t_p` during which the conductance rises monotonically (SET), the
dissipated energy `int_0^t_p V_p^2 G(t) dt` lies between the catalog's energy at the
initial and at the final conductance; for a falling conductance (RESET) the bounds swap. -/
theorem pulseEnergy_bracket {G : ℝ → ℝ} {Vp tp : ℝ} (htp : 0 ≤ tp) :
    (MonotoneOn G (Icc 0 tp) →
      pulseEnergy (G 0) Vp tp ≤ ∫ t in (0)..tp, G t * Vp ^ 2 ∧
        ∫ t in (0)..tp, G t * Vp ^ 2 ≤ pulseEnergy (G tp) Vp tp) ∧
    (AntitoneOn G (Icc 0 tp) →
      pulseEnergy (G tp) Vp tp ≤ ∫ t in (0)..tp, G t * Vp ^ 2 ∧
        ∫ t in (0)..tp, G t * Vp ^ 2 ≤ pulseEnergy (G 0) Vp tp) := by
  have hI : uIcc 0 tp = Icc 0 tp := uIcc_of_le htp
  have hc (g : ℝ) : ∫ _ in (0)..tp, g * Vp ^ 2 = pulseEnergy g Vp tp := by
    simp [pulseEnergy]; ring
  have hV : 0 ≤ Vp ^ 2 := sq_nonneg _
  constructor
  · intro hG
    have hint' : IntervalIntegrable G volume 0 tp := MonotoneOn.intervalIntegrable (hI ▸ hG)
    have hint2 : IntervalIntegrable (fun t => G t * Vp ^ 2) volume 0 tp := hint'.mul_const _
    constructor
    · rw [← hc]
      exact intervalIntegral.integral_mono_on htp intervalIntegrable_const hint2 fun t ht =>
        mul_le_mul_of_nonneg_right (hG ⟨le_refl 0, htp⟩ ht ht.1) hV
    · rw [← hc]
      exact intervalIntegral.integral_mono_on htp hint2 intervalIntegrable_const fun t ht =>
        mul_le_mul_of_nonneg_right (hG ht ⟨htp, le_refl tp⟩ ht.2) hV
  · intro hG
    have hint' : IntervalIntegrable G volume 0 tp := AntitoneOn.intervalIntegrable (hI ▸ hG)
    have hint2 : IntervalIntegrable (fun t => G t * Vp ^ 2) volume 0 tp := hint'.mul_const _
    constructor
    · rw [← hc]
      exact intervalIntegral.integral_mono_on htp intervalIntegrable_const hint2 fun t ht =>
        mul_le_mul_of_nonneg_right (hG ht ⟨htp, le_refl tp⟩ ht.2) hV
    · rw [← hc]
      exact intervalIntegral.integral_mono_on htp hint2 intervalIntegrable_const fun t ht =>
        mul_le_mul_of_nonneg_right (hG ⟨le_refl 0, htp⟩ ht ht.1) hV

/-! ## Device conductance of a non-uniform channel -/

/-- A channel of cross-section `A` made of segments of lengths `l_i` and conductivities
`sigma_i` in series has conductance `A / sum_i (l_i / sigma_i)`, which never exceeds the
catalog's conductance with the length-averaged conductivity
`sigma_bar = sum_i l_i sigma_i / L` and the total length `L = sum_i l_i`. -/
theorem deviceConductance_series_le {n : ℕ} (hn : 0 < n) (l sigma : Fin n → ℝ)
    (hl : ∀ i, 0 < l i) (hs : ∀ i, 0 < sigma i) {A : ℝ} (hA : 0 < A) :
    A / ∑ i, l i / sigma i ≤
      deviceConductance ((∑ i, l i * sigma i) / ∑ i, l i) A (∑ i, l i) := by
  have hne : (Finset.univ : Finset (Fin n)).Nonempty := Finset.univ_nonempty_iff.mpr ⟨⟨0, hn⟩⟩
  have hL : 0 < ∑ i, l i := Finset.sum_pos (fun i _ => hl i) hne
  have hR : 0 < ∑ i, l i / sigma i := Finset.sum_pos (fun i _ => div_pos (hl i) (hs i)) hne
  have hP : 0 < ∑ i, l i * sigma i := Finset.sum_pos (fun i _ => mul_pos (hl i) (hs i)) hne
  have hCS : (∑ i, l i) ^ 2 ≤ (∑ i, l i * sigma i) * ∑ i, l i / sigma i := by
    have := Finset.sum_mul_sq_le_sq_mul_sq Finset.univ (fun i => sqrt (l i * sigma i))
      (fun i => sqrt (l i / sigma i))
    have hfg : ∀ i, sqrt (l i * sigma i) * sqrt (l i / sigma i) = l i := by
      intro i
      rw [← sqrt_mul (mul_pos (hl i) (hs i)).le]
      have : l i * sigma i * (l i / sigma i) = l i ^ 2 := by field_simp [(hs i).ne']
      rw [this, sqrt_sq (hl i).le]
    simp only [hfg, sq_sqrt (mul_pos (hl _) (hs _)).le, sq_sqrt (div_pos (hl _) (hs _)).le] at this
    exact this
  unfold deviceConductance
  rw [div_le_div_iff₀ hR hL]
  have : A * ((∑ i, l i * sigma i) / ∑ i, l i) * ∑ i, l i / sigma i =
      A * ((∑ i, l i * sigma i) * ∑ i, l i / sigma i) / ∑ i, l i := by ring
  rw [this, le_div_iff₀ hL]
  nlinarith

end OMAI.PhyslibBridge.DeviceMetrology
