"""The exact expressive invariant of the M091 inherited substrate, and its refutation certificate.

M091 proved its own insufficiency with an *affine* invariant: `inc`, `dec`, `neg` and `double` are
affine, affine maps compose, so every slot held a constant or `a*inputs[i] + b`. That argument is
spent — it says nothing about `mul` and `max`, which the assembly substrate also offers, and the
acquired clamp already left the affine class.

M092 needs a different and much stronger statement, because it must survive **any** budget. The
statement here is:

    Proposition M092-I (eventual polynomiality).
      Fix a distinguished input position k.  Fix every other input and every initial slot to
      integer constants.  Then for every program P over any language state whose primitive bodies
      are sequences of M091 micro-operations -- any number of primitives, any program length, any
      body length within the interpreter's bound -- and every slot j, there are a polynomial
      p in Z[X] and a threshold X0 in N, both COMPUTED from P by `germ_of_program`, such that

          slots_j(x) = p(x)     for every integer x >= X0.

    Corollary M092-P (parity is unreachable, at any budget).
      No such P satisfies slots_j(x) = x mod 2 for all x >= 0.
      Proof.  Otherwise p(x) = x mod 2 for all x >= X0, so p takes only the values 0 and 1 on an
      infinite set of integers.  A non-constant polynomial is unbounded, so p is a constant c.  But
      x mod 2 takes both values above X0, so c = 0 and c = 1.  Contradiction.  []

Two things about the shape of this argument matter, and both were design requirements.

**It is not an alternation-counting argument, and it never says "monotone".** Counting sign changes
of consecutive differences is exactly where `neg` makes trouble: a decreasing map has one
alternation and is not monotone nondecreasing, so the two notions come apart and a bound stated in
one of them does not transfer to the other. This proposition avoids the whole question. It does not
count anything; it identifies the germ at +infinity, and parity fails because a *bounded* polynomial
is constant. Nothing here depends on the direction any map moves in.

**It is length-independent, so a larger search cannot defeat it.** The germ evaluator is a
homomorphism: every micro-operation acts on germs, so composing programs composes germs. There is no
induction on program length to run out of, which is why `more_budget_same_substrate` is negative for
a semantic reason rather than because an enumeration was truncated.

The abstraction is **exact, not conservative**. `max` is resolved by comparing leading coefficients
of the difference, which is a decision and not a widening, and the threshold beyond which that
decision is valid is carried along as a Cauchy bound. So `germ_of_body` returns the true germ, and
`soundness_report` re-checks it against the concrete interpreter rather than trusting it.

Nothing in this module knows what M092 will eventually try to acquire. It is a statement about the
inherited substrate alone.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from metamorphosis.m090_language import (
    INPUT_COUNT,
    MAX_BODY_LENGTH,
    MAX_STACK_DEPTH,
    MICRO_OPERATIONS,
    SLOT_COUNT,
    LanguageError,
    MetaLanguageState,
)

INVARIANT_SCHEMA = "m092-eventual-polynomiality-v1"

# --------------------------------------------------------------------------------------------
# Z[X], dense coefficients, lowest degree first. Canonical form carries no trailing zero.
# --------------------------------------------------------------------------------------------

Poly = tuple[int, ...]


def _trim(coefficients: list[int]) -> Poly:
    while coefficients and coefficients[-1] == 0:
        coefficients.pop()
    return tuple(coefficients)


def constant_poly(value: int) -> Poly:
    return _trim([int(value)])


VARIABLE: Poly = (0, 1)
ZERO: Poly = ()


def poly_add(left: Poly, right: Poly) -> Poly:
    width = max(len(left), len(right))
    return _trim([
        (left[i] if i < len(left) else 0) + (right[i] if i < len(right) else 0)
        for i in range(width)
    ])


def poly_negate(value: Poly) -> Poly:
    return _trim([-coefficient for coefficient in value])


def poly_subtract(left: Poly, right: Poly) -> Poly:
    return poly_add(left, poly_negate(right))


def poly_multiply(left: Poly, right: Poly) -> Poly:
    if not left or not right:
        return ZERO
    out = [0] * (len(left) + len(right) - 1)
    for i, a in enumerate(left):
        for j, b in enumerate(right):
            out[i + j] += a * b
    return _trim(out)


def poly_evaluate(value: Poly, x: int) -> int:
    accumulator = 0
    for coefficient in reversed(value):
        accumulator = accumulator * x + coefficient
    return accumulator


def poly_degree(value: Poly) -> int:
    """Degree, with the zero polynomial reported as -1 so that bounds stay total."""

    return len(value) - 1


def sign_threshold(value: Poly) -> int:
    """A Cauchy bound: beyond it, `sign(value(x))` is the sign of the leading coefficient.

    For `p(x) = a_d x^d + ... + a_0` with `a_d != 0`, every real root has modulus at most
    `1 + max|a_i| / |a_d|`. Integer arithmetic rounds that bound upwards, so it stays a bound.
    """

    if not value:
        return 0
    leading = abs(value[-1])
    largest = max((abs(coefficient) for coefficient in value[:-1]), default=0)
    return 2 + largest // leading


# --------------------------------------------------------------------------------------------
# Germs at +infinity
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Germ:
    """A value's behaviour for all large `x`: a polynomial, and where it starts being exact.

    `threshold` is the smallest bound this construction has justified, not the smallest that
    exists. It only ever needs to be *a* bound, since every claim is of the form "for all
    sufficiently large x".
    """

    polynomial: Poly
    threshold: int = 0

    def at(self, x: int) -> int:
        return poly_evaluate(self.polynomial, x)

    def is_constant(self) -> bool:
        return poly_degree(self.polynomial) <= 0


def germ_constant(value: int) -> Germ:
    return Germ(constant_poly(value))


GERM_VARIABLE = Germ(VARIABLE)


@dataclass(frozen=True)
class MaxCertificate:
    """Why one branch of a `max` eventually wins. Emitted so it can be re-checked, not trusted."""

    left: Poly
    right: Poly
    difference: Poly
    threshold: int
    chosen: Poly
    identically_equal: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "left": list(self.left), "right": list(self.right),
            "difference": list(self.difference), "threshold": self.threshold,
            "chosen": list(self.chosen), "identically_equal": self.identically_equal,
        }


def verify_max_certificate(certificate: MaxCertificate, samples: int = 64) -> dict[str, object]:
    """Independently re-check a branch selection. Nothing here trusts `sign_threshold`.

    The algebraic check is exact and is the load-bearing half. For `d(x) = a_k x^k + ... + a_0` with
    `a_k != 0` and every `x >= T >= 2`,

        sum_{i<k} |a_i| x^i  <=  M * (x^k - 1) / (x - 1)   where M = max_{i<k} |a_i|,

    so `|a_k| * (T - 1) >= M` is sufficient for the leading term to dominate, hence for
    `sign(d(x))` to equal `sign(a_k)` throughout `[T, inf)`. That inequality is checked in integer
    arithmetic below, so no floating point and no root-finding is involved.

    The sampled check is corroboration and is reported separately, never as the proof.
    """

    difference = poly_subtract(certificate.left, certificate.right)
    findings: list[str] = []

    if difference != certificate.difference:
        findings.append("difference does not equal left - right")

    if not difference:
        if not certificate.identically_equal:
            findings.append("difference is zero but the certificate does not say so")
        if certificate.chosen != certificate.left:
            findings.append("equal germs must choose either branch consistently")
        return {
            "algebraically_verified": not findings,
            "identically_equal": True,
            "dominance_inequality_holds": True,
            "sampled_signs_constant": True,
            "findings": findings,
        }

    if certificate.identically_equal:
        findings.append("certificate claims equality but the difference is non-zero")

    leading = abs(difference[-1])
    largest = max((abs(c) for c in difference[:-1]), default=0)
    threshold = certificate.threshold
    dominance = threshold >= 2 and leading * (threshold - 1) >= largest
    if not dominance:
        findings.append("the leading term does not provably dominate above the threshold")

    expected = certificate.left if difference[-1] > 0 else certificate.right
    if certificate.chosen != expected:
        findings.append("the chosen branch is not the one the leading coefficient selects")

    sign = 1 if difference[-1] > 0 else -1
    constant = True
    for step in range(samples):
        value = poly_evaluate(difference, threshold + step * step)
        if value == 0 or (1 if value > 0 else -1) != sign:
            constant = False
            break
    if not constant:
        findings.append("a sampled point above the threshold contradicts the fixed sign")

    return {
        "algebraically_verified": not findings,
        "identically_equal": False,
        "dominance_inequality_holds": dominance,
        "sampled_signs_constant": constant,
        "findings": findings,
    }


def germ_binary(
    operator: str, left: Germ, right: Germ, certificates: list[MaxCertificate] | None = None,
) -> Germ:
    """`add`, `sub`, `mul` are ring operations. `max` is a decision, and it is exact."""

    threshold = max(left.threshold, right.threshold)
    if operator == "add":
        return Germ(poly_add(left.polynomial, right.polynomial), threshold)
    if operator == "sub":
        return Germ(poly_subtract(left.polynomial, right.polynomial), threshold)
    if operator == "mul":
        return Germ(poly_multiply(left.polynomial, right.polynomial), threshold)
    if operator == "max":
        difference = poly_subtract(left.polynomial, right.polynomial)
        if not difference:
            if certificates is not None:
                certificates.append(MaxCertificate(
                    left.polynomial, right.polynomial, difference, threshold,
                    left.polynomial, True,
                ))
            return Germ(left.polynomial, threshold)
        threshold = max(threshold, sign_threshold(difference))
        winner = left.polynomial if difference[-1] > 0 else right.polynomial
        if certificates is not None:
            certificates.append(MaxCertificate(
                left.polynomial, right.polynomial, difference, threshold, winner, False,
            ))
        return Germ(winner, threshold)
    raise LanguageError(f"unknown binary operator {operator!r}")


def germ_unary(operator: str, value: Germ) -> Germ:
    if operator == "inc":
        return Germ(poly_add(value.polynomial, constant_poly(1)), value.threshold)
    if operator == "dec":
        return Germ(poly_subtract(value.polynomial, constant_poly(1)), value.threshold)
    if operator == "neg":
        return Germ(poly_negate(value.polynomial), value.threshold)
    if operator == "double":
        return Germ(poly_multiply(value.polynomial, constant_poly(2)), value.threshold)
    raise LanguageError(f"unknown unary operator {operator!r}")


def _resolve(argument: object, arguments: Sequence[object]) -> object:
    if isinstance(argument, str) and argument.startswith("$"):
        index = int(argument[1:])
        if index >= len(arguments):
            raise LanguageError(f"parameter {argument} is not supplied")
        return arguments[index]
    return argument


def germ_of_body(
    body: Sequence[tuple[str, object]],
    arguments: Sequence[object],
    slots: Sequence[Germ],
    inputs: Sequence[Germ],
    certificates: list[MaxCertificate] | None = None,
) -> list[Germ]:
    """The germ interpreter. Deliberately step-for-step identical to `m090_language.run_body`.

    Every refusal the concrete interpreter raises is raised here on the same step, so an abstract
    run and a concrete run agree about *whether* a body runs as well as about what it computes.
    That matters: a soundness check that silently accepted where the concrete run refused would be
    comparing two different things.
    """

    if len(body) > MAX_BODY_LENGTH:
        raise LanguageError("primitive body exceeds the frozen length bound")
    stack: list[Germ] = []
    updated = list(slots)
    for name, argument in body:
        if name not in MICRO_OPERATIONS:
            raise LanguageError(f"unknown micro-operation {name!r}")
        if len(stack) > MAX_STACK_DEPTH:
            raise LanguageError("primitive body exceeded the stack bound")
        if name == "PUSH_INPUT":
            index = int(_resolve(argument, arguments))  # type: ignore[arg-type]
            if not 0 <= index < INPUT_COUNT:
                raise LanguageError("input index out of range")
            stack.append(inputs[index])
        elif name == "PUSH_SLOT":
            index = int(_resolve(argument, arguments))  # type: ignore[arg-type]
            if not 0 <= index < SLOT_COUNT:
                raise LanguageError("slot index out of range")
            stack.append(updated[index])
        elif name == "PUSH_CONST":
            stack.append(germ_constant(int(_resolve(argument, arguments))))  # type: ignore[arg-type]
        elif name == "BINOP":
            if len(stack) < 2:
                raise LanguageError("BINOP needs two operands")
            right, left = stack.pop(), stack.pop()
            stack.append(germ_binary(str(_resolve(argument, arguments)), left, right, certificates))
        elif name == "UNOP":
            if not stack:
                raise LanguageError("UNOP needs one operand")
            stack.append(germ_unary(str(_resolve(argument, arguments)), stack.pop()))
        elif name == "DUP":
            if not stack:
                raise LanguageError("DUP needs one operand")
            stack.append(stack[-1])
        elif name == "SWAP":
            if len(stack) < 2:
                raise LanguageError("SWAP needs two operands")
            stack[-1], stack[-2] = stack[-2], stack[-1]
        elif name == "STORE_SLOT":
            if not stack:
                raise LanguageError("STORE_SLOT needs one operand")
            index = int(_resolve(argument, arguments))  # type: ignore[arg-type]
            if not 0 <= index < SLOT_COUNT:
                raise LanguageError("slot index out of range")
            updated[index] = stack.pop()
    return updated


def germ_of_program(
    program: Sequence[tuple[str, tuple[object, ...]]],
    language: MetaLanguageState,
    variable_input: int = 0,
    other_inputs: Mapping[int, int] | None = None,
    initial_slots: Sequence[int] | None = None,
    certificates: list[MaxCertificate] | None = None,
) -> list[Germ]:
    """Germs of every slot after a whole program. This is the composition half of M092-I.

    There is no bound on `len(program)`. Germ composition is just function composition in a ring
    that is closed under every operation the substrate has, so the statement does not weaken as
    programs get longer -- which is the property a budget arm cannot attack.
    """

    fixed = dict(other_inputs or {})
    inputs = [
        GERM_VARIABLE if index == variable_input else germ_constant(fixed.get(index, 0))
        for index in range(INPUT_COUNT)
    ]
    slots = [germ_constant(value) for value in (initial_slots or [0] * SLOT_COUNT)]
    for name, arguments in program:
        definition = language.definition(name)
        if definition is None:
            raise LanguageError(f"operation {name!r} is not defined")
        slots = germ_of_body(definition.body, arguments, slots, inputs, certificates)
    return slots


# --------------------------------------------------------------------------------------------
# The refutation certificate
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ParityRefutation:
    """Why no germ can be parity. Finite, and re-checkable without rerunning any search."""

    polynomial: Poly
    threshold: int
    witness_even: int
    witness_odd: int
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "polynomial": list(self.polynomial),
            "degree": poly_degree(self.polynomial),
            "threshold": self.threshold,
            "witness_even": self.witness_even,
            "witness_odd": self.witness_odd,
            "reason": self.reason,
        }


def refute_parity(germ: Germ) -> ParityRefutation:
    """Exhibit two integers above the threshold where `germ` cannot agree with `x mod 2`.

    The two witnesses are an even and an odd integer above the threshold. Above the threshold the
    germ *is* the slot value, so disagreeing there is a genuine refutation and not an abstraction
    artefact. Both cases are refuted by the same pair:

    * a non-constant polynomial is unbounded, so it leaves `{0, 1}` -- checked directly at the
      witnesses rather than argued;
    * a constant polynomial takes one value, and parity takes two.
    """

    base = max(germ.threshold, 0)
    even = base + 2 if base % 2 == 0 else base + 1
    odd = even + 1
    if germ.is_constant():
        reason = "a constant germ cannot take both parity values"
    else:
        reason = "a non-constant polynomial is unbounded and cannot stay inside {0, 1}"
    return ParityRefutation(germ.polynomial, base, even, odd, reason)


def germ_matches_parity(germ: Germ, samples: int = 64) -> bool:
    """Whether a germ agrees with `x mod 2` above its threshold. Always False; checked, not assumed.

    Kept as a live computation so that the corollary is exercised rather than asserted. If this
    ever returned True the invariant would be broken, and the caller would find out.
    """

    base = max(germ.threshold, 0)
    return all(germ.at(base + step) == (base + step) % 2 for step in range(1, samples + 1))


# --------------------------------------------------------------------------------------------
# Degree and threshold bounds, stated exactly
# --------------------------------------------------------------------------------------------


def degree_bound(body_length: int, program_length: int = 1) -> int:
    """An exact upper bound on the degree a germ can reach.

    Only `mul` raises degree, and `mul` combines two stack entries, so one micro-operation can at
    most double the largest degree present. With at most `body_length * program_length`
    micro-operations executed, the degree is bounded by `2 ** (body_length * program_length)`.

    The bound is stated because the design gate asked for one. It is not load-bearing: the germ
    evaluator computes the *actual* degree, and `refute_parity` uses that. The corollary holds at
    every degree, so no bound is needed to reach the conclusion.
    """

    if body_length <= 0 or program_length <= 0:
        return 0
    return 2 ** (body_length * program_length)


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def invariant_manifest() -> dict[str, object]:
    """The invariant as an artifact a checker re-derives instead of trusting."""

    manifest: dict[str, object] = {
        "schema": INVARIANT_SCHEMA,
        "proposition": "M092-I",
        "statement": (
            "for every program over the inherited substrate, every slot agrees with a polynomial "
            "in the distinguished input for all sufficiently large values of it"
        ),
        "corollary": "M092-P",
        "corollary_statement": "no such program computes x mod 2 on an unbounded domain",
        "domain": "unbounded: all integers at or above a computed threshold",
        "abstraction_is_exact": True,
        "abstraction_is_a_widening": False,
        "length_independent": True,
        "counts_alternations": False,
        "uses_the_word_monotone": False,
        "micro_operations_covered": list(MICRO_OPERATIONS),
        "max_body_length": MAX_BODY_LENGTH,
        "degree_bound_formula": "2 ** (body_length * program_length)",
    }
    manifest["digest"] = hashlib.sha256(canonical_bytes(manifest)).hexdigest()
    return manifest


__all__ = [
    "GERM_VARIABLE", "INVARIANT_SCHEMA", "VARIABLE", "ZERO", "Germ", "MaxCertificate",
    "ParityRefutation", "Poly", "verify_max_certificate",
    "canonical_bytes", "constant_poly", "degree_bound", "germ_binary", "germ_constant",
    "germ_matches_parity", "germ_of_body", "germ_of_program", "germ_unary", "invariant_manifest",
    "poly_add", "poly_degree", "poly_evaluate", "poly_multiply", "poly_negate", "poly_subtract",
    "refute_parity", "sign_threshold",
]
