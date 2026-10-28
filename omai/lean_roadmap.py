"""The formalization roadmap: every operator rated by what proving it needs.

Each operator's formula is classified by the mathematics a Lean theorem about
it would take:

- ``definition``: a closed-form polynomial or rational formula. The formula is
  its own statement; a theorem that restates it (clear the denominator,
  substitute and ring-normalize) certifies nothing, so none is written. A
  useful theorem states a property of the formula: a limit, a bound, a sign,
  or a reduction to another model.
- ``hard``: the formula needs analysis (a sum over modes, an integral, a
  derivative, or a special function).
- ``na``: the right-hand side names an external code's output (an opaque
  function symbol) or the edge carries no formula; there is nothing
  algebraic to prove, only the dimension and the lineage.

``proven`` marks an operator that a compiled formula bridge in ``lean/bridge``
proves a statement about (``omai.formula_bindings.compiled_targets``), at
any difficulty. The website renders ``docs/data/lean_roadmap.json``.
"""
from __future__ import annotations

import json
from pathlib import Path

import sympy as sp
from sympy.core.function import AppliedUndef

_REPO = Path(__file__).resolve().parent.parent
_DOCS = _REPO / "docs"

_ANALYTIC = tuple(getattr(sp, n) for n in (
    "log", "exp", "sin", "cos", "tan", "cot", "sinh", "cosh", "tanh", "coth",
    "asin", "acos", "atan", "atan2", "asinh", "acosh", "atanh", "erf", "gamma",
    "Abs", "sign", "Min", "Max", "floor", "ceiling", "conjugate") if hasattr(sp, n))
# Undefined function symbols that name an analytic function, not a code output.
_NAMED_SPECIAL = frozenset({"n_{BE}", "\\delta", "\\theta"})


def _classify(op):
    """(class, difficulty, reason) for one operator's formula."""
    f = getattr(op, "formula", None)
    if not isinstance(f, sp.Equality):
        return ("no formula", "na",
                "the edge carries no formula; only dimension and lineage apply")
    rhs = f.rhs
    if any(rhs.has(x) for x in (sp.Integral, sp.Sum, sp.Product, sp.Derivative)):
        return ("integral / sum / derivative", "hard",
                "needs analysis: an aggregation over modes or a derivative, "
                "with convergence and measurability to establish")
    if any(rhs.has(x) for x in _ANALYTIC):
        return ("special function", "hard",
                "needs analysis: transcendental or non-rational functions "
                "(exponentials, logarithms, inverse tangents) with their "
                "analytic properties")
    # A power with a symbolic exponent (the conductance-drift power law
    # G_0 (t/t0)^(-nu)) is real exponentiation, not a rational formula.
    if any(isinstance(n, sp.Pow) and n.exp.has(sp.Symbol)
           for n in sp.preorder_traversal(rhs)):
        return ("special function", "hard",
                "needs analysis: a power with a symbolic exponent (real "
                "exponentiation), not a rational formula")
    undefined = {type(a).__name__ for a in rhs.atoms(AppliedUndef)}
    if undefined and undefined <= _NAMED_SPECIAL:
        return ("special function", "hard",
                "needs analysis: a named special function (Bose-Einstein "
                "occupation, Dirac delta or Heaviside step)")
    if undefined:
        return ("opaque code output", "na",
                "names an external code's output; nothing algebraic to prove")
    if any(isinstance(n, sp.Pow) and n.exp.is_Rational and not n.exp.is_Integer
           for n in sp.preorder_traversal(rhs)):
        return ("special function", "hard",
                "needs analysis: a fractional power (a root)")
    den = sp.denom(sp.together(rhs))
    cls = "polynomial" if den == 1 or den.is_number else "rational"
    return (cls, "definition",
            "closed-form definition; a theorem restating it would certify "
            "nothing, so a proof must state a property such as a limit, a "
            "bound or a reduction to another model")


def _compiled_operators() -> set[str]:
    from omai.formula_bindings import _packaged_bindings, compiled_targets

    payload = _packaged_bindings()
    return {target["id"] for binding in payload["bindings"]
            for target in compiled_targets(binding, payload["inventory"])
            if target["kind"] == "operator"}


def build_roadmap():
    from omai.map_data import DOMAINS
    from omai.physlean_export import json_version

    proven = _compiled_operators()
    rows, counts = [], {"definition": 0, "hard": 0, "na": 0}
    for d in DOMAINS:
        dom = getattr(d, "name", "?")
        for op in getattr(d, "operators", getattr(d, "edges", [])):
            cls, diff, reason = _classify(op)
            if diff == "na" and op.name in proven:
                reason = ("names an external code's output; a compiled bridge proves statements "
                          "about an interpreted definition of it under stated conditions")
            counts[diff] += 1
            rows.append({
                "domain": dom,
                "op": op.name,
                "class": cls,
                "difficulty": diff,
                "proven": op.name in proven,
                "reason": reason,
            })
    rows.sort(key=lambda r: (r["domain"], r["op"]))
    return {
        "version": (json_version() or "")[:12],
        "counts": counts,
        "proven": sum(1 for r in rows if r["proven"]),
        "rows": rows,
    }


def write_roadmap(out: Path | None = None):
    out = out or _DOCS / "data" / "lean_roadmap.json"
    roadmap = build_roadmap()
    out.write_text(json.dumps(roadmap))
    stats = dict(roadmap["counts"], proven=roadmap["proven"],
                 rows=len(roadmap["rows"]))
    return out, stats
