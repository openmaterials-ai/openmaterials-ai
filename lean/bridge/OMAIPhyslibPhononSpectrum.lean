module

public import OMAIPhyslibPhononDispersion
public import OMAIPhyslibHarmonicEnsemble
public import Mathlib.Analysis.Fourier.FiniteAbelian.PontryaginDuality
public import Mathlib.NumberTheory.ZetaValues
public import Mathlib.Analysis.SpecialFunctions.Gamma.Basic
public import Mathlib.MeasureTheory.Integral.DominatedConvergence
public import Mathlib.MeasureTheory.Integral.IntegralEqImproper

/-!
# Phonon density of states and Landauer conductance over Physlib crystals and oscillators

On a finite Born-von Karman crystal of Physlib sites, the catalog density of states taken over
every character of the translations has total weight 3 per unit-cell site and second moment
`sum_i Phi_ii(0) / M_i` when the harmonic energy is never negative. The catalog's Landauer
weight `hbar omega dn_BE/dT` is the derivative-defined heat capacity of a Physlib quantum
harmonic oscillator, and with unit transmission the catalog conductance is the thermal
conductance quantum `pi^2 k_B^2 T / (3 h)`.
-/

@[expose] public section

noncomputable section

namespace OMAI.PhyslibBridge.PhononSpectrum

open Physlib.CondensedMatter Matrix ComplexConjugate MeasureTheory Real Set Filter
open OMAI.PhyslibBridge.Lattice
open Constants Temperature QuantumMechanics.OneDimension
open scoped ENNReal ComplexOrder

/-! ## Density of states -/

/-- The reviewed catalog expression of `compute_dos`,
`g(omega) = (1/N_q) sum_{q nu} delta(omega - omega_{q nu})`, as a measure on frequency. This
definition alone is not a physical proof. -/
def catalogDOS {Q ι : Type*} [Fintype Q] [Fintype ι] (omega : Q → ι → ℝ) : Measure ℝ :=
  ((Fintype.card Q : ℝ≥0∞)⁻¹) • ∑ q, ∑ ν, Measure.dirac (omega q ν)

theorem integral_catalogDOS {Q ι : Type*} [Fintype Q] [Fintype ι] (omega : Q → ι → ℝ)
    (f : ℝ → ℝ) :
    ∫ x, f x ∂(catalogDOS omega) = (∑ q, ∑ ν, f (omega q ν)) / Fintype.card Q := by
  have hd : ∀ a : ℝ, Integrable f (Measure.dirac a) := fun a => integrable_dirac enorm_lt_top
  unfold catalogDOS
  rw [integral_smul_measure, integral_finsetSum_measure fun q _ =>
    (integrable_finsetSum_measure.2 fun ν _ => hd _)]
  simp only [fun q => integral_finsetSum_measure (μ := fun ν => Measure.dirac (omega q ν))
    (s := Finset.univ) fun ν _ => hd _, integral_dirac, ENNReal.toReal_inv,
    ENNReal.toReal_natCast, smul_eq_mul]
  rw [div_eq_inv_mul]

/-- The frequencies of a finite crystal at a character `ψ` of its translations: the nonnegative
square roots of the eigenvalues of the dynamical matrix built from the supercell's own force
constants. -/
def crystalFrequencies {G : Type*} [AddCommGroup G] [AddGroup.FG G] [Fintype G] [DecidableEq G]
    {C : Crystal G} [Fintype C.UnitCell] [DecidableEq C.UnitCell] (Φ : ForceConstants C)
    (M : C.UnitCell → ℝ) (ψ : AddChar G ℂ) (ν : Mode C) : ℝ :=
  Real.sqrt ((Φ.dynamicalMatrix_isHermitian ψ (fun R => (AddChar.map_neg_eq_conj ψ R).symm)
    M).eigenvalues ν)

/-- Character orthogonality on the translations: the sum of the dynamical-matrix traces over
every character is the number of cells times the mass-weighted on-site force constants. -/
theorem sum_trace_dynamicalMatrix {G : Type*} [AddCommGroup G] [AddGroup.FG G] [Fintype G]
    [DecidableEq G] {C : Crystal G} [Fintype C.UnitCell] (Φ : ForceConstants C)
    (M : C.UnitCell → ℝ) (hM : ∀ κ, 0 < M κ) :
    ∑ ψ : AddChar G ℂ, (Φ.dynamicalMatrix ψ M).trace =
      ((Fintype.card G * ∑ i : Mode C, Φ.fc 0 i i / M i.1 : ℝ) : ℂ) := by
  have hS : ∀ (ψ : AddChar G ℂ) (i : Mode C),
      ∑ R ∈ Φ.shell, ψ R * (Φ.fc R i i : ℂ) = ∑ R, ψ R * (Φ.fc R i i : ℂ) :=
    fun ψ i => Finset.sum_subset (Finset.subset_univ _) fun R _ hR => by
      rw [Φ.fc_eq_zero_of_not_mem_shell hR, Complex.ofReal_zero, mul_zero]
  simp only [Matrix.trace, Matrix.diag, ForceConstants.dynamicalMatrix, hS]
  rw [Finset.sum_comm, Finset.mul_sum]
  push_cast
  refine Finset.sum_congr rfl fun i _ => ?_
  rw [← Finset.sum_div, Finset.sum_comm]
  simp only [← Finset.sum_mul, AddChar.sum_apply_eq_ite, ite_mul, zero_mul,
    Finset.sum_ite_eq', Finset.mem_univ, ↓reduceIte]
  rw [Real.sqrt_mul_self (hM i.1).le]
  ring

/-- Sum rules of the catalog density of states of a finite crystal of Physlib sites, taken over
every character of the translations (the full Born-von Karman mesh). Its total weight is the
number of modes, three per unit-cell site, and when the harmonic energy is never negative its
second moment is `sum_i Phi_ii(0) / M_i`, so the mean-square frequency is the mass-weighted
on-site force constant averaged over modes. -/
theorem crystalDOS_sum_rules {G : Type*} [AddCommGroup G] [AddGroup.FG G] [Fintype G]
    [DecidableEq G] {C : Crystal G} [Fintype C.UnitCell] [DecidableEq C.UnitCell]
    (Φ : ForceConstants C) (hstab : Φ.Stable) (M : C.UnitCell → ℝ) (hM : ∀ κ, 0 < M κ) :
    ∫ _, (1 : ℝ) ∂(catalogDOS (crystalFrequencies Φ M)) = 3 * Fintype.card C.UnitCell ∧
      ∫ x, x ^ 2 ∂(catalogDOS (crystalFrequencies Φ M)) =
        ∑ i : Mode C, Φ.fc 0 i i / M i.1 := by
  have hcard : (Fintype.card (AddChar G ℂ) : ℝ) = Fintype.card G := by
    rw [AddChar.card_eq]
  have hpos : (0 : ℝ) < Fintype.card G := by exact_mod_cast Fintype.card_pos
  refine ⟨?_, ?_⟩
  · rw [integral_catalogDOS]
    simp only [Finset.sum_const, Finset.card_univ, nsmul_eq_mul, mul_one, Fintype.card_prod,
      Fintype.card_fin, Nat.cast_mul, hcard]
    field_simp
    push_cast
    ring
  · rw [integral_catalogDOS, hcard]
    have hev : ∀ (ψ : AddChar G ℂ) (ν : Mode C), crystalFrequencies Φ M ψ ν ^ 2 =
        (Φ.dynamicalMatrix_isHermitian ψ (fun R => (AddChar.map_neg_eq_conj ψ R).symm)
          M).eigenvalues ν := fun ψ ν =>
      Real.sq_sqrt ((Φ.dynamicalMatrix_posSemidef_of_stable hstab ψ M hM).eigenvalues_nonneg ν)
    have htr : ∀ ψ : AddChar G ℂ, ∑ ν, crystalFrequencies Φ M ψ ν ^ 2 =
        ((Φ.dynamicalMatrix ψ M).trace).re := fun ψ => by
      rw [(Φ.dynamicalMatrix_isHermitian ψ (fun R => (AddChar.map_neg_eq_conj ψ R).symm)
        M).trace_eq_sum_eigenvalues, Complex.re_sum]
      exact Finset.sum_congr rfl fun ν _ => by rw [hev]; exact (Complex.ofReal_re _).symm
    simp only [htr]
    rw [← Complex.re_sum, sum_trace_dynamicalMatrix Φ M hM, Complex.ofReal_re]
    field_simp

/-! ## Landauer conductance -/

/-- The reviewed catalog expression of `compute_conductance[transport_model=landauer]`,
`G(T) = (1/(2 pi)) int_0^infinity hbar omega T(omega) d n_BE(hbar omega/(k_B T))/dT d omega`,
with the transmission `trans` and angular frequency `omega`. This definition alone is not a
physical proof. -/
def catalogLandauer (hbar kB : ℝ) (trans : ℝ → ℝ) (T : ℝ) : ℝ :=
  (∫ omega in Ioi 0, hbar * omega * trans omega *
    deriv (fun t => boseOccupation (hbar * omega / (kB * t))) T) / (2 * π)

theorem landauerWeight_eq {hbar kB omega T : ℝ} (hh : 0 < hbar) (hk : 0 < kB)
    (hw : 0 < omega) (hT : 0 < T) :
    hbar * omega * deriv (fun t => boseOccupation (hbar * omega / (kB * t))) T =
      harmonicHeatCapacity hbar kB omega T := by
  have hhw : hbar * omega ≠ 0 := (mul_pos hh hw).ne'
  have hn : HasDerivAt (fun t => boseOccupation (hbar * omega / (kB * t)))
      (harmonicHeatCapacity hbar kB omega T / (hbar * omega)) T := by
    have := ((harmonicInternalEnergy_hasDerivAt hh hk hw hT).div_const (hbar * omega)).sub_const
      (1 / 2 : ℝ)
    convert this using 1
    ext t
    unfold harmonicInternalEnergy harmonicArgument
    field_simp
    ring
  rw [hn.deriv]
  field_simp

/-- The catalog's Landauer weight `hbar omega dn_BE/dT` at angular frequency `Q.ω` is the
derivative-defined canonical heat capacity of the Physlib quantum harmonic oscillator `Q`, with
the Physlib values of `hbar` and `k_B`. -/
theorem landauerWeight_eq_heatCapacity (Q : HarmonicOscillator) (T : Temperature)
    (hT : 0 < T.val) :
    (ℏ : ℝ) * Q.ω * deriv (fun t => boseOccupation ((ℏ : ℝ) * Q.ω / (kB * t))) (T : ℝ) =
      (harmonicEnsemble Q).heatCapacity T := by
  have hTr : 0 < (T : ℝ) := by
    change 0 < (T.val : ℝ)
    exact_mod_cast hT
  rw [harmonic_heatCapacity_eq_omai Q T hT]
  exact landauerWeight_eq ℏ_pos kB_pos Q.hω hTr

/-- The catalog Landauer conductance is the transmission-weighted spectral integral of the
Physlib canonical heat capacity of one quantum oscillator per angular frequency. -/
theorem catalogLandauer_eq_heatCapacity (trans : ℝ → ℝ) (T : Temperature) (hT : 0 < T.val)
    (Q : ℝ → HarmonicOscillator) (hQ : ∀ omega, 0 < omega → (Q omega).ω = omega) :
    catalogLandauer ℏ kB trans T =
      (∫ omega in Ioi 0, trans omega * (harmonicEnsemble (Q omega)).heatCapacity T) / (2 * π) := by
  unfold catalogLandauer
  congr 1
  refine setIntegral_congr_fun measurableSet_Ioi fun omega homega => ?_
  rw [← landauerWeight_eq_heatCapacity (Q omega) T hT, hQ omega homega]
  ring

/-- The Bose kernel `x^2 e^x / (e^x - 1)^2` of the thermal conductance. -/
def boseKernel (x : ℝ) : ℝ := x ^ 2 * exp x / (exp x - 1) ^ 2

theorem boseKernel_eq_tsum {x : ℝ} (hx : 0 < x) :
    boseKernel x = ∑' n : ℕ, x ^ 2 * (n * exp (-x) ^ n) := by
  have hr : ‖exp (-x)‖ < 1 := by
    rw [Real.norm_of_nonneg (exp_pos _).le]
    exact Real.exp_lt_one_iff.2 (by linarith)
  rw [tsum_mul_left, tsum_coe_mul_geometric_of_norm_lt_one hr]
  unfold boseKernel
  have hE : exp x - 1 ≠ 0 := (sub_pos.2 (one_lt_exp_iff.2 hx)).ne'
  have hE' : 1 - exp (-x) ≠ 0 := (sub_pos.2 (Real.exp_lt_one_iff.2 (by linarith))).ne'
  rw [exp_neg]
  have hx0 : exp x ≠ 0 := (exp_pos x).ne'
  field_simp

theorem integral_sq_mul_exp_neg {n : ℝ} (hn : 0 < n) :
    ∫ x in Ioi 0, x ^ 2 * exp (-(n * x)) = 2 / n ^ 3 := by
  have h := integral_rpow_mul_exp_neg_mul_Ioi (a := 3) (by norm_num) hn
  have hG : Gamma 3 = 2 := by
    rw [show (3 : ℝ) = ((2 : ℕ) : ℝ) + 1 by norm_num, Real.Gamma_nat_eq_factorial]
    norm_num
  rw [hG] at h
  have hcongr : ∫ x in Ioi 0, x ^ 2 * exp (-(n * x)) =
      ∫ x in Ioi (0 : ℝ), x ^ ((3 : ℝ) - 1) * exp (-(n * x)) := by
    refine setIntegral_congr_fun measurableSet_Ioi fun x _ => ?_
    norm_num
  rw [hcongr, h, Real.rpow_ofNat]
  ring

/-- The Bose integral `int_0^infinity x^2 e^x / (e^x - 1)^2 dx = pi^2 / 3`. -/
theorem integral_boseKernel : ∫ x in Ioi 0, boseKernel x = π ^ 2 / 3 := by
  set F : ℕ → ℝ → ℝ := fun n x => x ^ 2 * (n * exp (-x) ^ n)
  have hF : ∀ (n : ℕ) (x : ℝ), F n x = n * (x ^ 2 * exp (-((n : ℝ) * x))) := fun n x => by
    simp only [F]
    rw [← exp_nat_mul]
    ring_nf
  have hInt : ∀ n : ℕ, ∫ x in Ioi 0, F n x = 2 * (1 / (n : ℝ) ^ 2) := fun n => by
    simp only [hF]
    rw [integral_const_mul]
    rcases Nat.eq_zero_or_pos n with rfl | hn
    · simp
    · have hn' : (0 : ℝ) < n := by exact_mod_cast hn
      rw [integral_sq_mul_exp_neg hn']
      field_simp
  have hInteg : ∀ n : ℕ, IntegrableOn (F n) (Ioi 0) := fun n => by
    rcases Nat.eq_zero_or_pos n with rfl | hn
    · simp [F]
    · refine Integrable.of_integral_ne_zero ?_
      rw [hInt n]
      have hn' : (0 : ℝ) < n := by exact_mod_cast hn
      positivity
  have hnorm : ∀ n : ℕ, ∫ x in Ioi 0, ‖F n x‖ = 2 * (1 / (n : ℝ) ^ 2) := fun n => by
    rw [← hInt n]
    refine setIntegral_congr_fun measurableSet_Ioi fun x _ => ?_
    exact Real.norm_of_nonneg (by simp only [F]; positivity)
  have hsum : Summable fun n : ℕ => ∫ x in Ioi 0, ‖F n x‖ := by
    simp only [hnorm]
    exact hasSum_zeta_two.summable.mul_left 2
  have h := integral_tsum_of_summable_integral_norm hInteg hsum
  simp only [hInt] at h
  rw [tsum_mul_left, hasSum_zeta_two.tsum_eq] at h
  rw [setIntegral_congr_fun measurableSet_Ioi fun x hx => boseKernel_eq_tsum hx]
  rw [← h]
  ring

theorem landauerWeight_eq_boseKernel {hbar kB omega T : ℝ} (hh : 0 < hbar) (hk : 0 < kB)
    (hw : 0 < omega) (hT : 0 < T) :
    hbar * omega * deriv (fun t => boseOccupation (hbar * omega / (kB * t))) T =
      kB * boseKernel (hbar / (kB * T) * omega) := by
  rw [landauerWeight_eq hh hk hw hT, harmonicHeatCapacity_eq_exp hh hk hw hT]
  unfold boseKernel harmonicArgument
  have h1 : hbar / (kB * T) * omega = hbar * omega / (kB * T) := by ring
  rw [h1]
  have hE : exp (hbar * omega / (kB * T)) - 1 ≠ 0 :=
    (sub_pos.2 (one_lt_exp_iff.2 (by positivity))).ne'
  field_simp

/-- With unit transmission the catalog Landauer conductance is the thermal conductance quantum
`pi^2 k_B^2 T / (3 h) = pi k_B^2 T / (6 hbar)` of one perfectly transmitting channel. -/
theorem catalogLandauer_unit_transmission {hbar kB T : ℝ} (hh : 0 < hbar) (hk : 0 < kB)
    (hT : 0 < T) :
    catalogLandauer hbar kB (fun _ => 1) T = π ^ 2 * kB ^ 2 * T / (3 * (2 * π * hbar)) := by
  unfold catalogLandauer
  have ha : 0 < hbar / (kB * T) := by positivity
  have hcongr : ∫ omega in Ioi 0, hbar * omega * 1 *
      deriv (fun t => boseOccupation (hbar * omega / (kB * t))) T =
      ∫ omega in Ioi 0, kB * boseKernel (hbar / (kB * T) * omega) := by
    refine setIntegral_congr_fun measurableSet_Ioi fun omega homega => ?_
    rw [mul_one, landauerWeight_eq_boseKernel hh hk homega hT]
  rw [hcongr, integral_const_mul, integral_comp_mul_left_Ioi boseKernel 0 ha, mul_zero,
    integral_boseKernel, smul_eq_mul]
  field_simp

/-- The thermal conductance quantum with the Physlib constants: `pi^2 k_B^2 T / (3 h)`. -/
theorem catalogLandauer_unit_transmission_physlib (T : Temperature) (hT : 0 < T.val) :
    catalogLandauer ℏ kB (fun _ => 1) T = π ^ 2 * kB ^ 2 * T / (3 * h) := by
  have hTr : 0 < (T : ℝ) := by
    change 0 < (T.val : ℝ)
    exact_mod_cast hT
  rw [catalogLandauer_unit_transmission ℏ_pos kB_pos hTr]
  rfl

end OMAI.PhyslibBridge.PhononSpectrum
