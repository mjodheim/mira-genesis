"""Evidence for the M092 design gates. Run before anything is frozen.

This script answers, with numbers rather than prose, the three questions that decide whether M092
may proceed at all:

  1. Is the eventual-polynomiality abstraction SOUND against the concrete M091 interpreter?
     Exhaustively over the frozen assembly body space, and on programs far longer than any arm
     will ever search.

  2. Is it CLOSED under unbounded composition?  If it is, `more_budget_same_substrate` is negative
     because of a semantic invariant, which is what the design gate requires -- not because an
     enumeration was truncated.

  3. Which candidate LOWER KERNELS escape it?  This is the anti-tailoring audit.  If non-iterative
     extensions all stay trapped, iteration is forced by the mathematics and not chosen because
     the eventual target happens to need it.

Nothing here knows what M092 will try to acquire, and nothing here is allowed to be a search.
"""
from __future__ import annotations

import argparse
import itertools
import json
import random
from typing import Iterator, Sequence

from metamorphosis.m090_language import (
    CONST_VALUES, INPUT_COUNT, SLOT_COUNT, UNARY_OPERATORS,
    LanguageError, MetaLanguageState, PrimitiveDefinition, execute, run_body,
)
from metamorphosis.m090_migration import INHERITED_DEFINITIONS
from metamorphosis.m091_substrate import SIGNATURES, body_alphabet, enumerate_candidate_bodies
from metamorphosis.m092_invariant import (
    GERM_VARIABLE, Germ, germ_constant, germ_matches_parity, germ_of_body, germ_of_program,
    invariant_manifest, poly_degree, poly_evaluate, refute_parity,
)

# M091's adopted primitive, restated as data so the composition probe runs over the language the
# lineage actually ended M091 with. M091's own modules are imported, never edited.
ACQUIRED_CLAMP = PrimitiveDefinition(
    primitive_id="CLAMP_FLOOR",
    parameter_kinds=("slot",),
    body=(("PUSH_SLOT", "$0"), ("PUSH_CONST", 0), ("BINOP", "max"), ("STORE_SLOT", "$0")),
    origin="acquired",
    provenance=("m091 adopted primitive",),
)


def inherited_l1() -> MetaLanguageState:
    return MetaLanguageState(
        primitives=INHERITED_DEFINITIONS + (ACQUIRED_CLAMP,),
        language_version=1,
        provenance=("m091 extended language, reconstructed for the M092 design audit",),
    )


# ------------------------------------------------------------------------------- 1. soundness


def _bindings(signature: Sequence[str]) -> list[tuple[object, ...]]:
    axes: list[Sequence[object]] = []
    for kind in signature:
        if kind == "slot":
            axes.append(range(SLOT_COUNT))
        elif kind == "input":
            axes.append(range(INPUT_COUNT))
        elif kind == "const":
            axes.append(CONST_VALUES)
        elif kind == "unary_op":
            axes.append(UNARY_OPERATORS)
    return [tuple(row) for row in itertools.product(*axes)] if axes else [()]


def soundness(max_length: int, probe_points: int) -> dict[str, object]:
    """Exhaustive over the frozen body space: does the germ predict the concrete run exactly?"""

    bodies = agreements = refusals = mismatched = disagreeing_refusals = 0
    max_degree = 0
    max_threshold = 0
    for signature in SIGNATURES:
        for body in enumerate_candidate_bodies(signature, max_length):
            bodies += 1
            for arguments in _bindings(signature):
                variable_input = 0
                other = {1: 3, 2: -4}
                inputs = [
                    GERM_VARIABLE if i == variable_input else germ_constant(other.get(i, 0))
                    for i in range(INPUT_COUNT)
                ]
                initial = [0, 2, -3, 5]
                try:
                    germs = germ_of_body(
                        body, arguments, [germ_constant(v) for v in initial], inputs,
                    )
                except LanguageError:
                    germs = None

                threshold = max((g.threshold for g in germs), default=0) if germs else 0
                max_threshold = max(max_threshold, threshold)
                if germs:
                    max_degree = max(max_degree, max(poly_degree(g.polynomial) for g in germs))

                for step in range(1, probe_points + 1):
                    x = threshold + step * step + 1
                    concrete_inputs = [
                        x if i == variable_input else other.get(i, 0) for i in range(INPUT_COUNT)
                    ]
                    try:
                        concrete = run_body(body, arguments, initial, concrete_inputs)
                    except LanguageError:
                        concrete = None
                    if (concrete is None) != (germs is None):
                        disagreeing_refusals += 1
                        break
                    if concrete is None:
                        refusals += 1
                        break
                    if [g.at(x) for g in germs] != list(concrete):
                        mismatched += 1
                        break
                    agreements += 1
    return {
        "bodies_enumerated": bodies,
        "exact_agreements": agreements,
        "refusals_agreed_on": refusals,
        "mismatches": mismatched,
        "refusal_disagreements": disagreeing_refusals,
        "max_observed_degree": max_degree,
        "max_observed_threshold": max_threshold,
        "max_body_length": max_length,
        "sound": mismatched == 0 and disagreeing_refusals == 0,
    }


# ---------------------------------------------------------------------------- 2. composition


def composition(trials: int, max_program_length: int, seed: int) -> dict[str, object]:
    """Closure under composition, on programs far longer than any arm searches."""

    rng = random.Random(seed)
    language = inherited_l1()
    definitions = list(language.primitives)
    mismatches = 0
    longest = 0
    for _ in range(trials):
        length = rng.randint(1, max_program_length)
        longest = max(longest, length)
        program: list[tuple[str, tuple[object, ...]]] = []
        for _ in range(length):
            definition = definitions[rng.randrange(len(definitions))]
            arguments: list[object] = []
            for kind in definition.parameter_kinds:
                if kind == "slot":
                    arguments.append(rng.randrange(SLOT_COUNT))
                elif kind == "input":
                    arguments.append(rng.randrange(INPUT_COUNT))
                elif kind == "const":
                    arguments.append(rng.choice(CONST_VALUES))
                elif kind == "unary_op":
                    arguments.append(rng.choice(UNARY_OPERATORS))
            program.append((definition.primitive_id, tuple(arguments)))
        other = {1: rng.randint(-5, 5), 2: rng.randint(-5, 5)}
        germs = germ_of_program(program, language, 0, other)
        threshold = max(g.threshold for g in germs)
        for step in (1, 3, 91, 4021):
            x = threshold + step
            concrete = execute(
                program, [x if i == 0 else other[i] for i in range(INPUT_COUNT)], language,
            )
            if [g.at(x) for g in germs] != list(concrete):
                mismatches += 1
                break
    return {
        "programs": trials,
        "longest_program": longest,
        "mismatches": mismatches,
        "closed_under_composition": mismatches == 0,
    }


# ------------------------------------------------------------------- 3. parity, and the axes


def parity_search(max_length: int) -> dict[str, object]:
    """Corroboration only: no body in the frozen space is parity. The proof is the invariant."""

    checked = matches = 0
    for signature in SIGNATURES:
        for body in enumerate_candidate_bodies(signature, max_length):
            for arguments in _bindings(signature):
                inputs = [GERM_VARIABLE] + [germ_constant(0)] * (INPUT_COUNT - 1)
                try:
                    germs = germ_of_body(
                        body, arguments, [germ_constant(0)] * SLOT_COUNT, inputs,
                    )
                except LanguageError:
                    continue
                checked += 1
                if any(germ_matches_parity(g) for g in germs):
                    matches += 1
    return {
        "germs_checked": checked,
        "parity_matches": matches,
        "note": "corroboration; the impossibility is Corollary M092-P, not this enumeration",
    }


INSUFFICIENCY_AXES = [
    ("A1 parity, x mod 2", True, "germ would be a bounded polynomial, hence constant"),
    ("A2 any non-constant periodic function", True, "same argument; boundedness forces a constant"),
    ("A3 floor division, floor(x/k)", True, "differs from any polynomial on unboundedly many x"),
    ("A4 bit or digit extraction", True, "periodic in x, so A2 applies"),
    ("A5 super-polynomial growth, 2**x", True, "outgrows every polynomial, so no germ matches"),
    ("A6 gcd(x, k) for fixed k", True, "periodic in x, so A2 applies"),
]

KERNEL_CANDIDATES = [
    ("K1 fuel-bounded conditional-jump register machine", True, False,
     "escapes using decrement, subtract and a conditional jump; no modulo, no target predicate"),
    ("K2 counted LOOP n { body }", True, True,
     "escapes, but 'repeat x times' hands the induction on x over directly"),
    ("K3 primitive-recursion combinator fold(n, init, step)", True, True,
     "same objection as K2; the recursion schema is the answer's shape"),
    ("K4 comparison plus conditional SELECT, no iteration", False, False,
     "eventually one branch wins, so the germ is closed; INSUFFICIENT"),
    ("K5 more registers, wider constants, min/abs, longer bodies", False, False,
     "all ring or lattice operations; the germ is closed; INSUFFICIENT"),
    ("K6 indirect addressing, address wraps modulo register count", True, True,
     "escapes only because wraparound IS modulo; contains the answer"),
    ("K7 floor division by a constant", True, True,
     "escapes, but floor(x/2) and x mod 2 are interdefinable; contains the answer"),
]


def kernel_audit() -> dict[str, object]:
    """K1 is demonstrated rather than asserted: a generic counter machine, no parity operation."""

    def counter_machine(x: int, fuel: int = 20_000) -> int | None:
        registers = [x, 0]
        while fuel > 0:
            fuel -= 1
            if registers[0] <= 0:
                return registers[1]
            registers[0] -= 1
            registers[1] = 1 - registers[1]
        return None

    demonstrated = all(counter_machine(n) == n % 2 for n in range(512))
    return {
        "candidates": [
            {
                "candidate": name,
                "escapes_the_invariant": escapes,
                "contains_the_answer_or_its_shape": tainted,
                "note": note,
            }
            for name, escapes, tainted, note in KERNEL_CANDIDATES
        ],
        "k1_escape_demonstrated_without_a_parity_operation": demonstrated,
        "non_iterative_candidates_all_trapped": all(
            not escapes for name, escapes, _, _ in KERNEL_CANDIDATES if name.startswith(("K4", "K5"))
        ),
        "selected": "K1",
        "claim": (
            "all audited target-neutral non-iterative extensions preserve the eventual-polynomial "
            "invariant; K1 is the smallest audited escape from that closure"
        ),
        "not_claimed": (
            "that iteration is universally forced by mathematics -- that would need a formal "
            "definition of the non-iterative extension class and a closure proof for all of it, "
            "which this audit has not done"
        ),
        "selection_reason": (
            "among iterative designs K1 is the most target-neutral: K2 and K3 supply the induction "
            "on x directly, and K6 and K7 escape only by containing modulo."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-body-length", type=int, default=3)
    parser.add_argument("--probe-points", type=int, default=4)
    parser.add_argument("--composition-trials", type=int, default=2000)
    parser.add_argument("--max-program-length", type=int, default=200)
    parser.add_argument("--seed", type=int, default=9201)
    parser.add_argument("--json", type=str, default="")
    arguments = parser.parse_args()

    report: dict[str, object] = {
        "invariant": invariant_manifest(),
        "soundness": soundness(arguments.max_body_length, arguments.probe_points),
        "composition": composition(
            arguments.composition_trials, arguments.max_program_length, arguments.seed,
        ),
        "parity_enumeration": parity_search(arguments.max_body_length),
        "insufficiency_axes": [
            {"axis": name, "blocked_by_the_same_invariant": blocked, "why": why}
            for name, blocked, why in INSUFFICIENCY_AXES
        ],
        "kernel_audit": kernel_audit(),
    }

    print("== M092 design audit ==\n")
    sound = report["soundness"]
    print(f"soundness    : {sound['bodies_enumerated']} bodies, "
          f"{sound['exact_agreements']} exact agreements, "
          f"{sound['mismatches']} mismatches, "
          f"{sound['refusal_disagreements']} refusal disagreements")
    print(f"               max degree {sound['max_observed_degree']}, "
          f"max threshold {sound['max_observed_threshold']}")
    comp = report["composition"]
    print(f"composition  : {comp['programs']} programs up to length "
          f"{comp['longest_program']}, {comp['mismatches']} mismatches")
    par = report["parity_enumeration"]
    print(f"parity search: {par['germs_checked']} germs, {par['parity_matches']} matches")
    print("\ninsufficiency axes blocked by the SAME invariant:")
    for row in report["insufficiency_axes"]:  # type: ignore[union-attr]
        print(f"  {row['axis']:<44} {row['why']}")
    print("\nlower-kernel candidates:")
    print(f"  {'candidate':<52} {'escapes':<9} {'tainted':<9} note")
    for row in report["kernel_audit"]["candidates"]:  # type: ignore[index]
        print(f"  {row['candidate']:<52} {str(row['escapes_the_invariant']):<9} "
              f"{str(row['contains_the_answer_or_its_shape']):<9} {row['note']}")
    print(f"\nselected kernel: {report['kernel_audit']['selected']}")  # type: ignore[index]

    if arguments.json:
        with open(arguments.json, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
        print(f"\nwrote {arguments.json}")

    ok = (
        sound["sound"]
        and comp["closed_under_composition"]
        and par["parity_matches"] == 0
        and report["kernel_audit"]["k1_escape_demonstrated_without_a_parity_operation"]  # type: ignore[index]
    )
    print(f"\ndesign gates 2 and 3 supported: {ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
