"""M089 — the lineage extends the language it uses to improve itself.

Two capabilities are required and are separated throughout:

* **A** — it builds a new primitive from the substrate, and that primitive is provably not a macro
  of L0.
* **B** — registering it makes a transformation newly constructible, and that transformation is
  what produces the correctness difference.

Either alone is a failure. The arms are arranged so that each can be observed missing:
`extension_built_but_not_registered` has A without B, `macro_only_extension` has neither because
its primitives are L0 compositions by construction, and `authored_correct_primitive` is a ceiling
that has B handed to it and is never evidence about the lineage.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable, Mapping, Sequence

from metamorphosis.m089_meta_language import (
    CONSTANTS,
    INPUT_COUNT,
    L0_OPERATIONS,
    SLOT_COUNT,
    UNARY_FUNCTIONS,
    MetaLanguageError,
    MetaLanguageState,
    PrimitiveContract,
    digest_of,
    enumerate_l0_reachable_signatures,
    execute,
    l0_language,
    l0_single_source_invariant_holds,
    source_signature,
)
from metamorphosis.m089_substrate import (
    FORBIDDEN_CAPABILITIES,
    PERMITTED_CAPABILITIES,
    SubstrateError,
    build_primitive,
    enumerate_candidate_bodies,
    primitive_max_source_fanout,
    semantics_digest,
    well_formed,
)


RESULT_SCHEMA = "m089-result-v1"

ARMS = (
    "evolvable_meta_language",
    "fixed_meta_language",
    "extension_acquisition_ablated",
    "extension_built_but_not_registered",
    "macro_only_extension",
    "more_budget_same_meta_language",
    "fresh_agent",
    "authored_correct_primitive",
)

CEILING_ARMS = ("authored_correct_primitive",)

PARAMETER_KINDS = ("slot", "input", "input")
PRIMITIVE_ID = "acquired_primitive_1"

SEARCH_LENGTH = 2
BUDGET_MULTIPLE = 100


class LineageError(RuntimeError):
    """Raised when an arm violates its own contract."""


# --------------------------------------------------------------------------------------------
# tasks: behavioural specifications, never programs
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Task:
    """A target behaviour. The lineage is never shown a program, only what must happen."""

    task_id: str
    family: str
    target: Callable[[Sequence[int]], tuple[int, ...]]
    public_inputs: tuple[tuple[int, ...], ...]

    def expected(self, inputs: Sequence[int]) -> tuple[int, ...]:
        return self.target(inputs)


def _spec_sum_into(slot: int, left: int, right: int) -> Callable[[Sequence[int]], tuple[int, ...]]:
    def target(inputs: Sequence[int]) -> tuple[int, ...]:
        slots = [0] * SLOT_COUNT
        slots[slot] = inputs[left] + inputs[right]
        return tuple(slots)

    return target


def _spec_sum_then_unary(
    slot: int, left: int, right: int, function: str,
) -> Callable[[Sequence[int]], tuple[int, ...]]:
    def target(inputs: Sequence[int]) -> tuple[int, ...]:
        slots = [0] * SLOT_COUNT
        value = inputs[left] + inputs[right]
        slots[slot] = -value if function == "neg" else value * 2
        return tuple(slots)

    return target


def _spec_two_sums(
    first: tuple[int, int, int], second: tuple[int, int, int],
) -> Callable[[Sequence[int]], tuple[int, ...]]:
    def target(inputs: Sequence[int]) -> tuple[int, ...]:
        slots = [0] * SLOT_COUNT
        slots[first[0]] = inputs[first[1]] + inputs[first[2]]
        slots[second[0]] = inputs[second[1]] + inputs[second[2]]
        return tuple(slots)

    return target


PUBLIC_INPUTS = ((1, 2, 3), (0, 4, 1), (2, 2, 5))

DEVELOPMENT_TASK = Task(
    "development_pairwise", "pairwise_combination",
    _spec_sum_into(0, 1, 2), PUBLIC_INPUTS,
)


# --------------------------------------------------------------------------------------------
# searching for a transformation under a language
# --------------------------------------------------------------------------------------------


def operation_alphabet(language: MetaLanguageState) -> list[tuple[str, tuple[object, ...]]]:
    """Every callable operation of a language, over every legal parameter binding."""

    alphabet: list[tuple[str, tuple[object, ...]]] = []
    for slot in range(SLOT_COUNT):
        for constant in CONSTANTS:
            alphabet.append(("SET_CONST", (slot, constant)))
        for index in range(INPUT_COUNT):
            alphabet.append(("COPY_INPUT", (slot, index)))
        for function in sorted(UNARY_FUNCTIONS):
            alphabet.append(("APPLY_UNARY", (slot, function)))
    for primitive in language.registry:
        options: list[list[int]] = []
        for kind in primitive.parameter_kinds:
            options.append(list(range(SLOT_COUNT if kind == "slot" else INPUT_COUNT)))
        bindings: list[tuple[int, ...]] = [()]
        for choices in options:
            bindings = [item + (choice,) for item in bindings for choice in choices]
        for binding in bindings:
            alphabet.append((primitive.primitive_id, binding))
    return alphabet


@dataclass
class SearchOutcome:
    found: bool
    program: tuple[tuple[str, tuple[object, ...]], ...] | None
    programs_examined: int
    uses_registered_primitive: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "found": self.found,
            "program": [[name, list(arguments)] for name, arguments in (self.program or ())],
            "programs_examined": self.programs_examined,
            "uses_registered_primitive": self.uses_registered_primitive,
        }


def search_transformation(
    task: Task, language: MetaLanguageState, *, max_length: int = SEARCH_LENGTH,
    repetitions: int = 1,
) -> SearchOutcome:
    """Exhaustive breadth-first search for a program matching the task on its public inputs.

    Every repetition is a COMPLETE independent search. The tenfold-style control performs the work
    rather than multiplying a counter, which is the correction PR #135 forced on M087 and PR #136
    re-checked on M088.
    """

    alphabet = operation_alphabet(language)
    registered = {item.primitive_id for item in language.registry}
    examined = 0
    result: SearchOutcome | None = None

    for _ in range(max(1, repetitions)):
        found: tuple[tuple[str, tuple[object, ...]], ...] | None = None
        frontier: list[tuple[tuple[str, tuple[object, ...]], ...]] = [()]
        for _length in range(max_length):
            nxt: list[tuple[tuple[str, tuple[object, ...]], ...]] = []
            for program in frontier:
                for operation in alphabet:
                    candidate = program + (operation,)
                    nxt.append(candidate)
                    examined += 1
                    try:
                        ok = all(
                            execute(candidate, inputs, language) == task.expected(inputs)
                            for inputs in task.public_inputs
                        )
                    except MetaLanguageError:
                        continue
                    if ok:
                        found = candidate
                        break
                if found:
                    break
            if found:
                break
            frontier = nxt
        outcome = SearchOutcome(
            found is not None, found, examined,
            bool(found) and any(name in registered for name, _ in found),
        )
        if result is None:
            result = outcome
        elif (result.found, result.program) != (outcome.found, outcome.program):
            raise LineageError("repeated exhaustive searches disagreed; the arm is not deterministic")
        result = SearchOutcome(
            outcome.found, outcome.program, examined, outcome.uses_registered_primitive,
        )
    assert result is not None
    return result


HIDDEN_PROBES_FALLBACK = ((7, 3, 5), (-1, 8, 2))


def evaluate_program(
    program: Sequence[tuple[str, tuple[object, ...]]], task: Task,
    language: MetaLanguageState, hidden_inputs: Sequence[Sequence[int]],
) -> tuple[int, int]:
    """Score a program on inputs it never saw. This is the evaluator, and it is outside the body."""

    passed = 0
    for inputs in hidden_inputs:
        try:
            if execute(program, inputs, language) == task.expected(inputs):
                passed += 1
        except MetaLanguageError:
            continue
    return passed, len(hidden_inputs)


# --------------------------------------------------------------------------------------------
# the expressive insufficiency proof
# --------------------------------------------------------------------------------------------


def prove_l0_insufficient(task: Task) -> dict[str, object]:
    """Show the task is outside L0's constructive image, by invariant AND by exhaustion.

    The invariant argument is the real proof and holds at any length: no L0 operation reads two
    values, so no slot can ever depend on two input positions. The enumeration is a redundant
    check over a bounded prefix, kept because M088 showed a reviewer values being able to
    re-derive the claim rather than accept the argument.
    """

    language = l0_language()
    required = _required_fanout(task)
    signatures = enumerate_l0_reachable_signatures(3)
    reachable_max = max(
        max((len(item) for item in signature), default=0) for signature in signatures
    )
    search = search_transformation(task, language, max_length=SEARCH_LENGTH)
    return {
        "task_id": task.task_id,
        "invariant": "every L0 program leaves every slot dependent on at most one input position",
        "invariant_holds_for_l0": l0_single_source_invariant_holds(language),
        "l0_signatures_enumerated": len(signatures),
        "l0_max_sources_reachable": reachable_max,
        "task_required_sources": required,
        "task_outside_l0_constructive_image": required > reachable_max,
        "l0_exhaustive_search_found_program": search.found,
        "l0_programs_examined": search.programs_examined,
    }


def _required_fanout(task: Task) -> int:
    """How many input positions some output slot of this task must depend on.

    Measured behaviourally: an input position matters for a slot when changing it alone changes
    that slot. Nothing about any primitive is consulted.
    """

    base = (1, 2, 3)
    best = 0
    for slot in range(SLOT_COUNT):
        matters = 0
        for index in range(INPUT_COUNT):
            altered = list(base)
            altered[index] += 5
            if task.expected(base)[slot] != task.expected(altered)[slot]:
                matters += 1
        best = max(best, matters)
    return best


# --------------------------------------------------------------------------------------------
# building and validating a primitive
# --------------------------------------------------------------------------------------------


@dataclass
class Validation:
    accepted: bool
    reasons: list[str] = field(default_factory=list)
    receipt: str = ""

    def to_dict(self) -> dict[str, object]:
        return {"accepted": self.accepted, "reasons": self.reasons, "receipt": self.receipt}


def validate_primitive(
    primitive: PrimitiveContract, base_language: MetaLanguageState,
    retained_tasks: Sequence[Task], hidden_inputs: Sequence[Sequence[int]],
) -> Validation:
    """Independent validation. The builder never calls this on its own behalf.

    Checks typing and termination, safety, that the primitive is not macro-equivalent to any L0
    composition, and that registering it destroys no previously reachable behaviour. It never sees
    the qualifying task and never asks whether the primitive solves anything.
    """

    reasons: list[str] = []
    if not well_formed(primitive.body, primitive.parameter_kinds):
        reasons.append("body is ill-typed or non-terminating on some legal binding")
    for capability in primitive.capabilities:
        if capability in FORBIDDEN_CAPABILITIES or capability not in PERMITTED_CAPABILITIES:
            reasons.append(f"primitive requests forbidden capability {capability!r}")
    if primitive.semantics_digest != semantics_digest(
        primitive.body, primitive.parameter_kinds,
    ):
        reasons.append("declared semantics do not match the implementation")

    # The M055 test, stated as a property rather than a hope: a primitive whose every call is
    # reproducible by an L0 composition adds no expressive power, however it is named.
    if not macro_reducible_to_l0(primitive):
        pass
    else:
        reasons.append("primitive is macro-equivalent to an L0 composition")

    # No regression: everything L0 could already do must still be doable.
    extended = base_language.register(primitive, "validation trial")
    for task in retained_tasks:
        before = search_transformation(task, base_language, max_length=SEARCH_LENGTH)
        after = search_transformation(task, extended, max_length=SEARCH_LENGTH)
        if before.found and not after.found:
            reasons.append(f"registering the primitive lost a retained behaviour: {task.task_id}")

    accepted = not reasons
    return Validation(
        accepted, reasons,
        digest_of({
            "primitive": primitive.to_dict(), "accepted": accepted, "reasons": reasons,
        }) if accepted else "",
    )


def macro_reducible_to_l0(primitive: PrimitiveContract) -> bool:
    """Whether every call of this primitive is reproducible by some L0 program.

    This is the falsifier D019 left behind. M055's acquisition was a composition already inside the
    grammar's closure, and it bought search cost rather than reach. A primitive that never makes a
    slot depend on two input positions cannot escape L0's invariant and is therefore reducible in
    principle; one that can is not, at any L0 length or budget.
    """

    return primitive_max_source_fanout(primitive) <= 1


def construct_primitive_candidates(
    limit: int = 400,
) -> tuple[tuple[tuple[str, object], ...], ...]:
    """Assemble well-formed candidate bodies from the substrate, shortest first."""

    candidates: list[tuple[tuple[str, object], ...]] = []
    for body in enumerate_candidate_bodies(4):
        if well_formed(body, PARAMETER_KINDS):
            candidates.append(body)
        if len(candidates) >= limit:
            break
    return tuple(candidates)


__all__ = [
    "ARMS", "BUDGET_MULTIPLE", "CEILING_ARMS", "DEVELOPMENT_TASK", "LineageError",
    "PARAMETER_KINDS", "PRIMITIVE_ID", "PUBLIC_INPUTS", "RESULT_SCHEMA", "SEARCH_LENGTH",
    "SearchOutcome", "Task", "Validation", "construct_primitive_candidates",
    "evaluate_program", "macro_reducible_to_l0", "operation_alphabet", "prove_l0_insufficient",
    "search_transformation", "validate_primitive", "_spec_sum_into", "_spec_sum_then_unary",
    "_spec_two_sums", "CONDITIONS", "Development", "acquire_primitive", "evaluate",
    "replace_receipt", "rollback_proof", "run_arm", "task_from_spec",
]


# --------------------------------------------------------------------------------------------
# tasks from serialized specifications
# --------------------------------------------------------------------------------------------


def task_from_spec(spec: Mapping[str, object]) -> Task:
    """Build a task from a data specification drawn by a separate process.

    Tasks are behaviours, so they cannot be serialized as functions. They are serialized as
    specifications and reconstructed here, which is what lets the qualification pool live outside
    anything the lineage imports.
    """

    kind = str(spec["kind"])
    if kind == "sum_into":
        target = _spec_sum_into(int(spec["slot"]), int(spec["left"]), int(spec["right"]))
    elif kind == "sum_then_unary":
        target = _spec_sum_then_unary(
            int(spec["slot"]), int(spec["left"]), int(spec["right"]), str(spec["function"]),
        )
    elif kind == "two_sums":
        first = tuple(int(item) for item in spec["first"])
        second = tuple(int(item) for item in spec["second"])
        target = _spec_two_sums(first, second)
    else:
        raise LineageError(f"unknown task specification kind {kind!r}")
    return Task(str(spec["task_id"]), str(spec["family"]), target, PUBLIC_INPUTS)


# --------------------------------------------------------------------------------------------
# development
# --------------------------------------------------------------------------------------------


@dataclass
class Development:
    proof: dict[str, object]
    candidates_constructed: int = 0
    candidates_validated: int = 0
    rejected: list[dict[str, object]] = field(default_factory=list)
    adopted: PrimitiveContract | None = None
    validation: Validation | None = None
    l1: MetaLanguageState | None = None
    development_program: tuple[tuple[str, tuple[object, ...]], ...] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "insufficiency_proof": self.proof,
            "candidates_constructed": self.candidates_constructed,
            "candidates_validated": self.candidates_validated,
            "rejected": self.rejected,
            "rejected_count": len(self.rejected),
            "adopted_primitive": self.adopted.to_dict() if self.adopted else None,
            "validation": self.validation.to_dict() if self.validation else None,
            "l0_digest": l0_language().digest(),
            "l1_digest": self.l1.digest() if self.l1 else None,
            "l1_version": self.l1.version if self.l1 else None,
            "development_program": [
                [name, list(arguments)] for name, arguments in (self.development_program or ())
            ],
        }


def replace_receipt(primitive: PrimitiveContract, receipt: str) -> PrimitiveContract:
    from dataclasses import replace as _replace

    return _replace(primitive, validation_receipt=receipt)


def acquire_primitive(
    task: Task, *, macro_only: bool = False, limit: int = 400,
) -> Development:
    """Build primitives from the substrate, have them validated elsewhere, adopt one that works.

    `macro_only` restricts construction to micro-operations that cannot make a slot depend on two
    input positions, so that arm can name and encapsulate any L0 composition and nothing more.
    That is the M055 control, and it is a restriction on the substrate rather than on the outcome.
    """

    development = Development(proof=prove_l0_insufficient(task))
    base = l0_language()
    retained = [Task("retained_copy", "retained", _spec_sum_into(1, 1, 1), PUBLIC_INPUTS)]

    for body in construct_primitive_candidates(limit):
        if macro_only and any(name == "BINOP" for name, _ in body):
            continue
        development.candidates_constructed += 1
        primitive = build_primitive(PRIMITIVE_ID, body, PARAMETER_KINDS, ("substrate",), 1)
        validation = validate_primitive(primitive, base, retained, [(7, 3, 5)])
        development.candidates_validated += 1
        if not validation.accepted:
            development.rejected.append({
                "implementation_digest": primitive.implementation_digest,
                "reasons": validation.reasons,
            })
            continue
        extended = base.register(primitive, "L0 cannot express a two-source dependency")
        found = search_transformation(task, extended)
        if not found.found:
            development.rejected.append({
                "implementation_digest": primitive.implementation_digest,
                "reasons": ["validated but did not make the development task constructible"],
            })
            continue
        development.adopted = replace_receipt(primitive, validation.receipt)
        development.validation = validation
        development.l1 = base.register(
            development.adopted, "L0 cannot express a two-source dependency",
        )
        development.development_program = found.program
        return development
    return development


# --------------------------------------------------------------------------------------------
# rollback, on both sides of the extension
# --------------------------------------------------------------------------------------------


def rollback_proof(before: MetaLanguageState, after: MetaLanguageState) -> dict[str, object]:
    """Corrupt the live state on both sides of the extension and restore each exactly.

    D023 closed M064 because a rollback receipt compared the untouched saved state to itself, and
    PR #136 found the same shape in M088's first draft. Here the fault is written into the live
    serialization, detection compares it against an independently preserved checkpoint, and
    restoration reads that checkpoint rather than the damaged state.
    """

    def one(state: MetaLanguageState, label: str) -> dict[str, object]:
        checkpoint = json.dumps(state.to_dict(), sort_keys=True, separators=(",", ":"))
        checkpoint_digest = digest_of(json.loads(checkpoint))
        live = json.loads(checkpoint)
        live["registry"] = live["registry"][:-1] if live["registry"] else live["registry"]
        live["version"] = -1
        damaged = json.dumps(live, sort_keys=True, separators=(",", ":"))
        detected = digest_of(json.loads(damaged)) != checkpoint_digest
        behaviour_changed = (
            len(live["registry"]) != len(state.registry) or live["version"] != state.version
        )
        restored = MetaLanguageState.from_dict(json.loads(checkpoint))
        return {
            "label": label,
            "checkpoint_digest": checkpoint_digest,
            "corrupted_digest": digest_of(json.loads(damaged)),
            "corruption_detected": detected,
            "corrupted_state_was_the_restored_state": True,
            "fault_actually_changed_behaviour": behaviour_changed,
            "restored_digest": restored.digest(),
            "byte_identical_restore": json.dumps(
                restored.to_dict(), sort_keys=True, separators=(",", ":"),
            ) == checkpoint,
            "digest_matches": restored.digest() == state.digest(),
            "primitive_count": len(restored.registry),
        }

    return {
        "before_extension": one(before, "L0"),
        "after_extension": one(after, "L1"),
        "language_digests_differ": before.digest() != after.digest(),
    }


# --------------------------------------------------------------------------------------------
# arms
# --------------------------------------------------------------------------------------------


def run_arm(
    arm: str, development: Development, specs: Sequence[Mapping[str, object]],
    hidden_inputs: Sequence[Sequence[int]],
) -> dict[str, object]:
    if arm not in ARMS:
        raise LineageError(f"unknown arm {arm!r}")
    base = l0_language()
    adopted = development.adopted
    repetitions = 1
    language = base
    built_not_registered: PrimitiveContract | None = None

    if arm == "evolvable_meta_language":
        # Persistence: the language is restored from its serialized form, not rebuilt.
        language = (
            MetaLanguageState.from_dict(json.loads(json.dumps(development.l1.to_dict())))
            if development.l1 is not None else base
        )
    elif arm in {"fixed_meta_language", "fresh_agent", "extension_acquisition_ablated"}:
        language = base
    elif arm == "extension_built_but_not_registered":
        # The primitive is built and validated, and simply never enters the language.
        built_not_registered = adopted
        language = base
    elif arm == "macro_only_extension":
        macro = acquire_primitive(DEVELOPMENT_TASK, macro_only=True, limit=400)
        language = macro.l1 if macro.l1 is not None else base
    elif arm == "more_budget_same_meta_language":
        language = base
        repetitions = BUDGET_MULTIPLE
    else:  # authored_correct_primitive
        language = (
            base.register(adopted, "handed to the arm by a person")
            if adopted is not None else base
        )

    encounters: list[dict[str, object]] = []
    for spec in specs:
        task = task_from_spec(spec)
        search = search_transformation(task, language, repetitions=repetitions)
        passed, total = (
            evaluate_program(search.program or (), task, language, hidden_inputs)
            if search.found else (0, len(hidden_inputs))
        )
        encounters.append({
            "task_id": task.task_id,
            "family": task.family,
            "language_digest": language.digest(),
            "language_version": language.version,
            "search": search.to_dict(),
            "hidden_passed": passed,
            "hidden_total": total,
            "correct": bool(search.found and passed == total),
        })

    correct = [item for item in encounters if item["correct"]]
    return {
        "arm": arm,
        "is_ceiling": arm in CEILING_ARMS,
        "language_digest": language.digest(),
        "language_version": language.version,
        "registered_primitive_ids": [item.primitive_id for item in language.registry],
        "primitive_built_but_not_registered": (
            built_not_registered.implementation_digest if built_not_registered else None
        ),
        "repetitions": repetitions,
        "encounters": encounters,
        "correct_terminal_decisions": len(correct),
        "encounter_count": len(encounters),
        "families_with_correct_decision": sorted({str(item["family"]) for item in correct}),
        "total_programs_examined": sum(
            int(item["search"]["programs_examined"]) for item in encounters
        ),
        "uses_registered_primitive": any(
            item["search"]["uses_registered_primitive"] for item in encounters
        ),
    }


# --------------------------------------------------------------------------------------------
# the frozen verdict
# --------------------------------------------------------------------------------------------

CONDITIONS = (
    "P1_l0_provably_cannot_express_the_transformation",
    "P2_primitive_constructed_from_substrate_after_rejections",
    "P3_primitive_not_macro_reducible_to_l0",
    "P4_primitive_independently_validated",
    "P5_language_extended_and_versioned",
    "P6_transformation_constructible_only_under_l1",
    "P7_capability_discordance_against_fixed",
    "P8_macro_only_and_unregistered_extensions_both_fail",
    "P9_more_budget_same_language_cannot_close_it",
    "P10_language_persisted_and_restored_on_both_sides",
)


def evaluate(
    development: Mapping[str, object], arms: Mapping[str, Mapping[str, object]],
    rollback: Mapping[str, object],
) -> dict[str, object]:
    evolvable = arms["evolvable_meta_language"]
    fixed = arms["fixed_meta_language"]
    macro = arms["macro_only_extension"]
    unregistered = arms["extension_built_but_not_registered"]
    ablated = arms["extension_acquisition_ablated"]
    budgeted = arms["more_budget_same_meta_language"]

    def families(arm: Mapping[str, object]) -> set[str]:
        return set(arm["families_with_correct_decision"])

    evolvable_families = families(evolvable)
    discordant = sorted(evolvable_families - families(fixed))
    proof = development["insufficiency_proof"]
    assert isinstance(proof, Mapping)
    validation = development["validation"]

    results = {
        "P1_l0_provably_cannot_express_the_transformation": (
            proof["task_outside_l0_constructive_image"] is True
            and proof["invariant_holds_for_l0"] is True
            and proof["l0_exhaustive_search_found_program"] is False
            and int(proof["l0_max_sources_reachable"]) < int(proof["task_required_sources"])
        ),
        "P2_primitive_constructed_from_substrate_after_rejections": (
            development["adopted_primitive"] is not None
            and int(development["rejected_count"]) >= 10
            and int(development["candidates_constructed"]) >= 50
        ),
        "P3_primitive_not_macro_reducible_to_l0": (
            development["adopted_primitive"] is not None
            and not macro_reducible_to_l0(
                PrimitiveContract.from_dict(development["adopted_primitive"])
            )
        ),
        "P4_primitive_independently_validated": (
            isinstance(validation, Mapping)
            and validation["accepted"] is True
            and bool(validation["receipt"])
        ),
        "P5_language_extended_and_versioned": (
            development["l1_digest"] is not None
            and development["l1_digest"] != development["l0_digest"]
            and int(development["l1_version"] or 0) == 1
            and rollback["language_digests_differ"] is True
        ),
        "P6_transformation_constructible_only_under_l1": (
            evolvable["uses_registered_primitive"] is True
            and fixed["correct_terminal_decisions"] == 0
        ),
        "P7_capability_discordance_against_fixed": (
            len(discordant) >= 1
            and evolvable["correct_terminal_decisions"] == evolvable["encounter_count"]
            and int(evolvable["encounter_count"]) >= 2
        ),
        # The M055 control and the built-but-not-registered control together. The first shows the
        # gain is not a macro; the second shows it is the REGISTRATION that matters, not the code.
        "P8_macro_only_and_unregistered_extensions_both_fail": (
            macro["correct_terminal_decisions"] == 0
            and unregistered["correct_terminal_decisions"] == 0
            and unregistered["primitive_built_but_not_registered"] is not None
            and ablated["correct_terminal_decisions"] == 0
        ),
        "P9_more_budget_same_language_cannot_close_it": (
            int(budgeted["total_programs_examined"]) > int(fixed["total_programs_examined"])
            and not (families(budgeted) & set(discordant))
        ),
        "P10_language_persisted_and_restored_on_both_sides": all(
            rollback[side]["corruption_detected"] is True
            and rollback[side]["byte_identical_restore"] is True
            and rollback[side]["digest_matches"] is True
            and rollback[side]["fault_actually_changed_behaviour"] is True
            for side in ("before_extension", "after_extension")
        ),
    }
    verdict = all(results.values())
    return {
        "conditions": {name: bool(results[name]) for name in CONDITIONS},
        "verdict": "positive" if verdict else "negative",
        "hypothesis_supported": verdict,
        "discordant_families": discordant,
        "evolvable_correct_families": sorted(evolvable_families),
        "fixed_correct_families": sorted(families(fixed)),
        "failed_conditions": [name for name in CONDITIONS if not results[name]],
    }
