module

public import Mathlib.Analysis.Calculus.Deriv.Pow
public import Mathlib.Analysis.SpecialFunctions.Pow.Deriv
public import Mathlib.Tactic

/-!
# Linear elasticity for the catalog's elastic contractions

The catalog contracts a fourth-rank stiffness tensor `C` to a Voigt bulk modulus
`K = sum_ab C_aabb / 9` and a Voigt shear modulus
`G = -sum_ab C_aabb / 30 + sum_ab C_abab / 10`, combines `K` and `G` into a Young's
modulus and a Poisson ratio, and reads a bulk modulus `V0 * E''(V0)` off an
energy-volume curve. Physlib has no model of an elastic solid, so these results use
Mathlib only and identify no Physlib declaration.

For every stiffness tensor with the first minor symmetry that stores positive energy for
every nonzero symmetric strain, the Voigt moduli are positive, so the catalog's Poisson
ratio lies in `(-1, 1/2)`. For an isotropic tensor the contractions return the Lame
values, positivity of both moduli is equivalent to stability, and the catalog's `E` and
`nu` are the Lame expressions. For a cubic tensor they return the Voigt-notation forms,
the volumetric strain responds to the mean stress alone with modulus `K`, and the energy
minimized over cell shape at fixed volume has curvature `V0 * E''(V0) = K`.

Indices run over `Fin 3`. `stress C e = C : e` is tensile-positive, the negative of the
catalog's compressive-positive Stress node. No result validates a DFT or
finite-difference producer of `C`, nor a fitted equation of state.
-/

@[expose] public section

noncomputable section

open Finset

namespace OMAI.PhyslibBridge.Elasticity

/-- A fourth-rank stiffness tensor on three Cartesian indices. -/
abbrev Stiffness := Fin 3 → Fin 3 → Fin 3 → Fin 3 → ℝ

/-- A second-rank tensor on three Cartesian indices (a strain or a stress). -/
abbrev Tensor2 := Fin 3 → Fin 3 → ℝ

/-- The reviewed catalog expression of `contract_bulk_modulus`, `K = sum_ab C_aabb / 9`.
This definition alone is not a physical proof. -/
def voigtBulk (C : Stiffness) : ℝ := (∑ a, ∑ b, C a a b b) / 9

/-- The reviewed catalog expression of `contract_shear_modulus`,
`G = -sum_ab C_aabb / 30 + sum_ab C_abab / 10`. This definition alone is not a physical
proof. -/
def voigtShear (C : Stiffness) : ℝ := -(∑ a, ∑ b, C a a b b) / 30 + (∑ a, ∑ b, C a b a b) / 10

/-- The reviewed catalog expression of `contract_youngs_modulus`, `E = 9 G K / (G + 3 K)`,
with inputs BulkModulus then ShearModulus. This definition alone is not a physical proof. -/
def youngsModulus (K G : ℝ) : ℝ := 9 * G * K / (G + 3 * K)

/-- The reviewed catalog expression of `contract_poisson_ratio`,
`nu = (-2 G + 3 K) / (2 G + 6 K)`, with inputs BulkModulus then ShearModulus. This
definition alone is not a physical proof. -/
def poissonRatio (K G : ℝ) : ℝ := (-2 * G + 3 * K) / (2 * G + 6 * K)

/-- The reviewed catalog expression of `compute_bulk_modulus_eos`, `K = V0 * E''(V)`, the
curvature of the cell energy `E` with respect to cell volume, evaluated at the reference
volume `V0`. This definition alone is not a physical proof. -/
def eosBulk (E : ℝ → ℝ) (V0 : ℝ) : ℝ := V0 * deriv (deriv E) V0

/-- The Kronecker delta on Cartesian indices. -/
def kron (a b : Fin 3) : ℝ := if a = b then 1 else 0

/-- The isotropic stiffness tensor with Lame parameters `lam` and `mu`. -/
def isotropic (lam mu : ℝ) : Stiffness := fun a b c d =>
  lam * kron a b * kron c d + mu * (kron a c * kron b d + kron a d * kron b c)

/-- The cubic stiffness tensor with Voigt constants `c11`, `c12`, `c44` and the cube axes
along the Cartesian axes. -/
def cubic (c11 c12 c44 : ℝ) : Stiffness := fun a b c d =>
  c12 * kron a b * kron c d + c44 * (kron a c * kron b d + kron a d * kron b c)
    + (c11 - c12 - 2 * c44) * (kron a b * kron a c * kron a d)

/-- Linear stress `sigma_ab = sum_cd C_abcd e_cd`, tensile-positive. -/
def stress (C : Stiffness) (e : Tensor2) : Tensor2 := fun a b => ∑ c, ∑ d, C a b c d * e c d

/-- Twice the strain energy density, `sum_abcd C_abcd e_ab e_cd`. -/
def strainEnergy (C : Stiffness) (e : Tensor2) : ℝ :=
  ∑ a, ∑ b, ∑ c, ∑ d, C a b c d * e a b * e c d

/-- The trace of a second-rank tensor. -/
def trace (e : Tensor2) : ℝ := ∑ a, e a a

/-- A strain is symmetric. -/
def Symmetric (e : Tensor2) : Prop := ∀ a b, e a b = e b a

/-- A stiffness tensor stores positive energy for every nonzero symmetric strain. -/
def PosDef (C : Stiffness) : Prop := ∀ e : Tensor2, Symmetric e → e ≠ 0 → 0 < strainEnergy C e

/-! ## Voigt moduli of a stable tensor of any symmetry -/

/-- The strain energy of a uniform dilation `e = s * delta` is `9 K s^2` with `K` the
catalog's Voigt bulk modulus, for every stiffness tensor. -/
theorem strainEnergy_hydrostatic (C : Stiffness) (s : ℝ) :
    strainEnergy C (fun a b => s * kron a b) = 9 * voigtBulk C * s ^ 2 := by
  simp [strainEnergy, voigtBulk, kron, Fin.sum_univ_three]
  ring

/-- An orthogonal basis of symmetric traceless strains, with squared norms 2, 6, 2, 2, 2. -/
def dev1 : Tensor2 := ![![1, 0, 0], ![0, -1, 0], ![0, 0, 0]]
@[inherit_doc dev1] def dev2 : Tensor2 := ![![1, 0, 0], ![0, 1, 0], ![0, 0, -2]]
@[inherit_doc dev1] def dev3 : Tensor2 := ![![0, 1, 0], ![1, 0, 0], ![0, 0, 0]]
@[inherit_doc dev1] def dev4 : Tensor2 := ![![0, 0, 1], ![0, 0, 0], ![1, 0, 0]]
@[inherit_doc dev1] def dev5 : Tensor2 := ![![0, 0, 0], ![0, 0, 1], ![0, 1, 0]]

/-- For a stiffness tensor with the first minor symmetry, `10 G` is the sum of the strain
energies over an orthogonal basis of deviatoric strains, each divided by its squared norm. -/
theorem voigtShear_eq_deviatoric_sum (C : Stiffness)
    (hC : ∀ a b c d, C a b c d = C b a c d) :
    10 * voigtShear C =
      strainEnergy C dev1 / 2 + strainEnergy C dev2 / 6 + strainEnergy C dev3 / 2 +
        strainEnergy C dev4 / 2 + strainEnergy C dev5 / 2 := by
  simp [voigtShear, strainEnergy, dev1, dev2, dev3, dev4, dev5, Fin.sum_univ_three]
  linear_combination -(1 / 2) * hC 1 0 0 1 + (1 / 2) * hC 1 0 1 0 - (1 / 2) * hC 2 0 0 2 +
    (1 / 2) * hC 2 0 2 0 - (1 / 2) * hC 2 1 1 2 + (1 / 2) * hC 2 1 2 1

private theorem sym_of_fin (e : Tensor2) (h10 : e 1 0 = e 0 1) (h20 : e 2 0 = e 0 2)
    (h21 : e 2 1 = e 1 2) : Symmetric e := by
  intro a b
  fin_cases a <;> fin_cases b <;> simp_all

/-- A stiffness tensor of any symmetry with the first minor symmetry that stores positive
energy for every nonzero symmetric strain has positive catalog Voigt bulk and shear
moduli. -/
theorem voigt_pos_of_posDef {C : Stiffness} (hC : ∀ a b c d, C a b c d = C b a c d)
    (hpos : PosDef C) : 0 < voigtBulk C ∧ 0 < voigtShear C := by
  have hI := hpos (fun a b => 1 * kron a b) (fun a b => by simp only [kron, eq_comm])
    (by intro h; have := congrFun (congrFun h 0) 0; simp [kron] at this)
  rw [strainEnergy_hydrostatic] at hI
  have hne : ∀ (u : Tensor2) (a b : Fin 3), u a b ≠ 0 → u ≠ 0 := by
    intro u a b h hu; exact h (by rw [hu]; rfl)
  have p1 := hpos dev1 (sym_of_fin _ rfl rfl rfl) (hne dev1 0 0 (by simp [dev1]))
  have p2 := hpos dev2 (sym_of_fin _ rfl rfl rfl) (hne dev2 0 0 (by simp [dev2]))
  have p3 := hpos dev3 (sym_of_fin _ rfl rfl rfl) (hne dev3 0 1 (by simp [dev3]))
  have p4 := hpos dev4 (sym_of_fin _ rfl rfl rfl) (hne dev4 0 2 (by simp [dev4]))
  have p5 := hpos dev5 (sym_of_fin _ rfl rfl rfl) (hne dev5 1 2 (by simp [dev5]))
  have h10 := voigtShear_eq_deviatoric_sum C hC
  constructor <;> nlinarith

/-- The catalog's Poisson ratio of any stable stiffness tensor with the first minor symmetry
lies strictly between `-1` and `1/2`, with the Voigt moduli as inputs. -/
theorem poissonRatio_bounds_of_posDef {C : Stiffness} (hC : ∀ a b c d, C a b c d = C b a c d)
    (hpos : PosDef C) :
    -1 < poissonRatio (voigtBulk C) (voigtShear C) ∧
      poissonRatio (voigtBulk C) (voigtShear C) < 1 / 2 := by
  obtain ⟨hK, hG⟩ := voigt_pos_of_posDef hC hpos
  unfold poissonRatio
  have hd : 0 < 2 * voigtShear C + 6 * voigtBulk C := by positivity
  constructor
  · rw [lt_div_iff₀ hd]; nlinarith
  · rw [div_lt_iff₀ hd]; nlinarith

/-! ## Isotropic tensors -/

/-- The isotropic tensor is the cubic tensor with Zener ratio `2 c44 / (c11 - c12) = 1`. -/
theorem isotropic_eq_cubic (lam mu : ℝ) : isotropic lam mu = cubic (lam + 2 * mu) lam mu := by
  funext a b c d
  simp only [isotropic, cubic]
  ring

/-- For a cubic crystal the catalog's Voigt bulk modulus is `(C11 + 2 C12) / 3`. -/
theorem voigtBulk_cubic (c11 c12 c44 : ℝ) :
    voigtBulk (cubic c11 c12 c44) = (c11 + 2 * c12) / 3 := by
  simp [voigtBulk, cubic, kron, Fin.sum_univ_three]
  ring

/-- For a cubic crystal the catalog's Voigt shear modulus is `(C11 - C12 + 3 C44) / 5`. -/
theorem voigtShear_cubic (c11 c12 c44 : ℝ) :
    voigtShear (cubic c11 c12 c44) = (c11 - c12 + 3 * c44) / 5 := by
  simp [voigtShear, cubic, kron, Fin.sum_univ_three]
  ring

/-- For an isotropic tensor the catalog's Voigt bulk modulus is `lam + 2 mu / 3`. -/
theorem voigtBulk_isotropic (lam mu : ℝ) : voigtBulk (isotropic lam mu) = lam + 2 * mu / 3 := by
  rw [isotropic_eq_cubic, voigtBulk_cubic]
  ring

/-- For an isotropic tensor the catalog's Voigt shear modulus is the Lame `mu`. -/
theorem voigtShear_isotropic (lam mu : ℝ) : voigtShear (isotropic lam mu) = mu := by
  rw [isotropic_eq_cubic, voigtShear_cubic]
  ring

/-- The isotropic strain energy of a symmetric strain is `lam (tr e)^2 + 2 mu sum e_ab^2`. -/
theorem isotropic_strainEnergy (lam mu : ℝ) {e : Tensor2} (he : Symmetric e) :
    strainEnergy (isotropic lam mu) e = lam * trace e ^ 2 + 2 * mu * ∑ a, ∑ b, e a b ^ 2 := by
  have h10 := he 1 0
  have h20 := he 2 0
  have h21 := he 2 1
  simp only [strainEnergy, isotropic, trace, kron, Fin.sum_univ_three]
  simp
  rw [h10, h20, h21]
  ring

/-- The isotropic strain energy splits into a volumetric part weighted by the catalog's
Voigt bulk modulus and a deviatoric part weighted by its Voigt shear modulus. -/
theorem isotropic_strainEnergy_split (lam mu : ℝ) {e : Tensor2} (he : Symmetric e) :
    strainEnergy (isotropic lam mu) e =
      voigtBulk (isotropic lam mu) * trace e ^ 2 +
        2 * voigtShear (isotropic lam mu) *
          ∑ a, ∑ b, (e a b - kron a b * trace e / 3) ^ 2 := by
  rw [isotropic_strainEnergy lam mu he, voigtBulk_isotropic, voigtShear_isotropic]
  simp only [trace, kron, Fin.sum_univ_three]
  simp
  ring

/-- An isotropic solid stores positive strain energy for every nonzero symmetric strain
exactly when the catalog's Voigt bulk and shear moduli are both positive. -/
theorem isotropic_stable_iff (lam mu : ℝ) :
    PosDef (isotropic lam mu) ↔
      0 < voigtBulk (isotropic lam mu) ∧ 0 < voigtShear (isotropic lam mu) := by
  constructor
  · intro h
    refine voigt_pos_of_posDef (fun a b c d => ?_) h
    simp only [isotropic, kron]
    split_ifs <;> simp_all
  · rintro ⟨hK, hG⟩ e he hne
    rw [isotropic_strainEnergy_split lam mu he]
    set t := trace e
    set D := ∑ a, ∑ b, (e a b - kron a b * t / 3) ^ 2 with hD
    have hD0 : 0 ≤ D := sum_nonneg fun a _ => sum_nonneg fun b _ => sq_nonneg _
    by_contra hle
    have hle := not_lt.mp hle
    have ht : t = 0 := by
      have : voigtBulk (isotropic lam mu) * t ^ 2 ≤ 0 := by nlinarith
      have h2 : t ^ 2 ≤ 0 := by
        by_contra hpos; have hpos := not_le.mp hpos; nlinarith
      exact pow_eq_zero_iff (n := 2) (by norm_num) |>.mp (le_antisymm h2 (sq_nonneg t))
    have hDz : D = 0 := by
      have : 2 * voigtShear (isotropic lam mu) * D ≤ 0 := by nlinarith
      nlinarith
    apply hne
    funext a b
    have hab := (sum_eq_zero_iff_of_nonneg (fun a _ => sum_nonneg fun b _ => sq_nonneg _)).mp
      hDz a (mem_univ a)
    have hab' := (sum_eq_zero_iff_of_nonneg (fun b _ => sq_nonneg _)).mp hab b (mem_univ b)
    rw [ht] at hab'
    simpa using hab'

/-- With positive bulk and shear moduli the catalog's Poisson ratio lies strictly between
`-1` and `1/2`. -/
theorem poissonRatio_bounds {K G : ℝ} (hK : 0 < K) (hG : 0 < G) :
    -1 < poissonRatio K G ∧ poissonRatio K G < 1 / 2 := by
  unfold poissonRatio
  have hd : 0 < 2 * G + 6 * K := by positivity
  constructor
  · rw [lt_div_iff₀ hd]; nlinarith
  · rw [div_lt_iff₀ hd]; nlinarith

/-- For an isotropic tensor the catalog's Poisson ratio is the Lame value
`lam / (2 (lam + mu))`. -/
theorem poissonRatio_isotropic {lam mu : ℝ} (h : lam + mu ≠ 0) :
    poissonRatio (voigtBulk (isotropic lam mu)) (voigtShear (isotropic lam mu)) =
      lam / (2 * (lam + mu)) := by
  rw [voigtBulk_isotropic, voigtShear_isotropic]
  unfold poissonRatio
  have h6 : 2 * mu + 6 * (lam + 2 * mu / 3) = 6 * (lam + mu) := by ring
  rw [h6]
  field_simp
  ring

/-- For an isotropic tensor the catalog's Young's modulus is the Lame value
`mu (3 lam + 2 mu) / (lam + mu)`. -/
theorem youngsModulus_isotropic {lam mu : ℝ} (h : lam + mu ≠ 0) :
    youngsModulus (voigtBulk (isotropic lam mu)) (voigtShear (isotropic lam mu)) =
      mu * (3 * lam + 2 * mu) / (lam + mu) := by
  rw [voigtBulk_isotropic, voigtShear_isotropic]
  unfold youngsModulus
  have h3 : mu + 3 * (lam + 2 * mu / 3) = 3 * (lam + mu) := by ring
  rw [h3]
  field_simp
  ring

/-! ## Cubic tensors -/

/-- A cubic crystal under hydrostatic strain `e = s * delta` carries hydrostatic stress
`sigma = 3 K s * delta`, with `K` the catalog's Voigt bulk modulus. Hydrostatic strain
couples to no shear stress. -/
theorem cubic_hydrostatic_stress (c11 c12 c44 s : ℝ) :
    stress (cubic c11 c12 c44) (fun a b => s * kron a b) =
      fun a b => 3 * voigtBulk (cubic c11 c12 c44) * s * kron a b := by
  rw [voigtBulk_cubic]
  funext a b
  fin_cases a <;> fin_cases b <;> simp [stress, cubic, kron, Fin.sum_univ_three] <;> ring

/-- In a cubic crystal the trace of the stress depends on the strain only through its
trace, `tr sigma = 3 K tr e` for every strain, with `K` the catalog's Voigt bulk modulus.
Any stress of mean value `-P` therefore produces the volumetric strain `-P / K`, so the
catalog's Voigt bulk modulus is the crystal's stress-controlled bulk modulus. -/
theorem cubic_trace_stress (c11 c12 c44 : ℝ) (e : Tensor2) :
    trace (stress (cubic c11 c12 c44) e) = 3 * voigtBulk (cubic c11 c12 c44) * trace e := by
  rw [voigtBulk_cubic]
  simp [trace, stress, cubic, kron, Fin.sum_univ_three]
  ring

/-- In a cubic crystal with `c12 <= c11` and `c44 >= 0`, every symmetric strain of trace
`theta` stores at least the energy `K theta^2` of the hydrostatic strain of that trace. -/
theorem cubic_strainEnergy_ge {c11 c12 c44 : ℝ} (h12 : c12 ≤ c11) (h44 : 0 ≤ c44)
    {e : Tensor2} (he : Symmetric e) :
    voigtBulk (cubic c11 c12 c44) * trace e ^ 2 ≤ strainEnergy (cubic c11 c12 c44) e := by
  have h10 := he 1 0
  have h20 := he 2 0
  have h21 := he 2 1
  rw [voigtBulk_cubic]
  simp only [strainEnergy, cubic, trace, kron, Fin.sum_univ_three]
  simp
  rw [h10, h20, h21]
  have hd : 0 ≤ c11 - c12 := by linarith
  nlinarith [mul_nonneg hd (sq_nonneg (e 0 0 - e 1 1)), mul_nonneg hd (sq_nonneg (e 1 1 - e 2 2)),
    mul_nonneg hd (sq_nonneg (e 0 0 - e 2 2)), mul_nonneg h44 (sq_nonneg (e 0 1)),
    mul_nonneg h44 (sq_nonneg (e 0 2)), mul_nonneg h44 (sq_nonneg (e 1 2))]

/-! ## Equation-of-state curvature -/

/-- Linear hydrostatic strain `s(V) = (V / V0)^(1/3) - 1` of a cell of volume `V`. -/
def hydrostaticStrain (V0 V : ℝ) : ℝ := (V / V0) ^ ((1 : ℝ) / 3) - 1

/-- Energy of a cell of reference volume `V0` and energy `E0` scaled uniformly to volume
`V`, with the linear-elastic energy density `W(e) / 2` of the stiffness `C` and no
relaxation of the cell shape. -/
def uniformScalingEnergy (C : Stiffness) (E0 V0 V : ℝ) : ℝ :=
  E0 + V0 * strainEnergy C (fun a b => hydrostaticStrain V0 V * kron a b) / 2

/-- The strain energies of symmetric strains of trace `theta`. -/
def fixedTraceEnergies (C : Stiffness) (theta : ℝ) : Set ℝ :=
  {w | ∃ e : Tensor2, Symmetric e ∧ trace e = theta ∧ w = strainEnergy C e}

/-- Energy of a cell of reference volume `V0` at volume `V` with the cell shape relaxed:
the least linear-elastic energy over all symmetric strains whose volumetric part
`tr e = 3 s(V)` matches the volume. -/
def relaxedEnergy (C : Stiffness) (E0 V0 V : ℝ) : ℝ :=
  E0 + V0 * sInf (fixedTraceEnergies C (3 * hydrostaticStrain V0 V)) / 2

private theorem hydrostaticStrain_hasDerivAt {V0 V : ℝ} (hV0 : 0 < V0) (hV : 0 < V) :
    HasDerivAt (hydrostaticStrain V0)
      ((1 / 3) * (V / V0) ^ ((1 : ℝ) / 3 - 1) * (1 / V0)) V := by
  have hx : 0 < V / V0 := div_pos hV hV0
  have hdiv : HasDerivAt (fun V => V / V0) (1 / V0) V := by
    simpa using (hasDerivAt_id V).div_const V0
  have hpow := (hdiv.rpow_const (p := (1 : ℝ) / 3) (Or.inl hx.ne'))
  unfold hydrostaticStrain
  convert hpow.sub_const 1 using 1
  ring

/-- The curvature `V0 * E''(V0)` of `E0 + V0 * 9 K s(V)^2 / 2` is `K`. -/
theorem eosBulk_quadratic_strain (K E0 : ℝ) {V0 : ℝ} (hV0 : 0 < V0) :
    eosBulk (fun V => E0 + V0 * (9 * K * hydrostaticStrain V0 V ^ 2) / 2) V0 = K := by
  unfold eosBulk
  set s' : ℝ → ℝ := fun V => (1 / 3) * (V / V0) ^ ((1 : ℝ) / 3 - 1) * (1 / V0)
  have hfirst : ∀ V, 0 < V → HasDerivAt (fun V => E0 + V0 * (9 * K * hydrostaticStrain V0 V ^ 2) / 2)
      (V0 * (9 * K * (2 * hydrostaticStrain V0 V * s' V)) / 2) V := by
    intro V hV
    have hs := hydrostaticStrain_hasDerivAt hV0 hV
    have := ((hs.pow 2).const_mul (9 * K)).const_mul V0 |>.div_const 2 |>.const_add E0
    convert this using 1
    simp [s']
  have hderiv : ∀ᶠ V in nhds V0,
      deriv (fun V => E0 + V0 * (9 * K * hydrostaticStrain V0 V ^ 2) / 2) V =
        V0 * (9 * K * (2 * hydrostaticStrain V0 V * s' V)) / 2 :=
    (eventually_gt_nhds hV0).mono fun V hV => (hfirst V hV).deriv
  rw [Filter.EventuallyEq.deriv_eq hderiv]
  have hs0 : hydrostaticStrain V0 V0 = 0 := by
    simp [hydrostaticStrain, div_self hV0.ne']
  have hone : (1 / 3) * (V0 / V0) ^ ((1 : ℝ) / 3 - 1) * (1 / V0) = 1 / (3 * V0) := by
    rw [div_self hV0.ne', Real.one_rpow]; field_simp
  have hsd := hydrostaticStrain_hasDerivAt hV0 hV0
  have hs'd : HasDerivAt s' (deriv s' V0) V0 := by
    apply DifferentiableAt.hasDerivAt
    have hx : (V0 / V0) ≠ 0 := by rw [div_self hV0.ne']; exact one_ne_zero
    have : DifferentiableAt ℝ (fun V => V / V0) V0 := (differentiableAt_id).div_const V0
    exact ((this.rpow_const (Or.inl hx)).const_mul (1 / 3)).mul_const (1 / V0)
  have hfin : HasDerivAt (fun V => V0 * (9 * K * (2 * hydrostaticStrain V0 V * s' V)) / 2)
      (K / V0) V0 := by
    have hprod := ((((hsd.mul hs'd).const_mul 2).const_mul (9 * K)).const_mul V0).div_const 2
    convert hprod using 1
    · funext V; simp only [Pi.mul_apply]; ring
    · have hsv : s' V0 = 1 / (3 * V0) := hone
      rw [hs0, hsv, hone]
      field_simp
      ring
  rw [hfin.deriv]
  field_simp

/-- For every stiffness tensor the curvature `V0 * E''(V0)` of the energy under uniform
scaling of the cell, with no shape relaxation, is the catalog's Voigt bulk modulus. -/
theorem uniformScaling_eosBulk_eq_voigtBulk (C : Stiffness) (E0 : ℝ) {V0 : ℝ} (hV0 : 0 < V0) :
    eosBulk (uniformScalingEnergy C E0 V0) V0 = voigtBulk C := by
  have h : uniformScalingEnergy C E0 V0 =
      fun V => E0 + V0 * (9 * voigtBulk C * hydrostaticStrain V0 V ^ 2) / 2 := by
    funext V
    simp only [uniformScalingEnergy, strainEnergy_hydrostatic]
  rw [h, eosBulk_quadratic_strain _ _ hV0]

/-- In a cubic crystal with `c12 <= c11` and `c44 >= 0` the least energy at fixed volume
is the hydrostatic one, `K (3 s)^2`. -/
theorem cubic_relaxed_sInf {c11 c12 c44 : ℝ} (h12 : c12 ≤ c11) (h44 : 0 ≤ c44) (theta : ℝ) :
    sInf (fixedTraceEnergies (cubic c11 c12 c44) theta) =
      voigtBulk (cubic c11 c12 c44) * theta ^ 2 := by
  apply IsLeast.csInf_eq
  constructor
  · refine ⟨fun a b => theta / 3 * kron a b, fun a b => by simp only [kron, eq_comm], ?_, ?_⟩
    · simp [trace, kron]; ring
    · rw [strainEnergy_hydrostatic]; ring
  · rintro w ⟨e, he, htr, rfl⟩
    rw [← htr]
    exact cubic_strainEnergy_ge h12 h44 he

/-- In a cubic crystal with `c12 <= c11` and `c44 >= 0`, the curvature `V0 * E''(V0)` of
the cell energy minimized over cell shape at each volume is the catalog's Voigt bulk
modulus. This identifies the catalog's equation-of-state bulk modulus of a relaxed cubic
cell with its tensor contraction. -/
theorem cubic_relaxed_eosBulk_eq_voigtBulk {c11 c12 c44 : ℝ} (h12 : c12 ≤ c11) (h44 : 0 ≤ c44)
    (E0 : ℝ) {V0 : ℝ} (hV0 : 0 < V0) :
    eosBulk (relaxedEnergy (cubic c11 c12 c44) E0 V0) V0 = voigtBulk (cubic c11 c12 c44) := by
  have h : relaxedEnergy (cubic c11 c12 c44) E0 V0 =
      fun V => E0 + V0 * (9 * voigtBulk (cubic c11 c12 c44) * hydrostaticStrain V0 V ^ 2) / 2 := by
    funext V
    simp only [relaxedEnergy, cubic_relaxed_sInf h12 h44]
    ring
  rw [h, eosBulk_quadratic_strain _ _ hV0]

end OMAI.PhyslibBridge.Elasticity
