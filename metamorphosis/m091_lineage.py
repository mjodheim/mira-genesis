"""M091 — the lineage creates a new operation in the language it actually owns.

M090 settled *where the language lives*: one registry, entirely serialized state, consulted by a
fixed generic interpreter that branches on no primitive identifier. It settled nothing about
whether the lineage can add to it, and said so — its probe extension was authored and labelled.

This milestone asks the question that precondition made askable. Two capabilities are required and
are kept apart everywhere, because either alone is a failure:

* **A — a new operation.** The lineage diagnoses that a required transformation lies outside what
  its language can express, assembles a primitive from a lower substrate, and that primitive is
  provably not reducible to any composition of the language it already had.
* **B — a larger language.** Registering it into the serialized state makes a transformation
  constructible that was not, and that transformation is what produces the correctness difference.

`extension_built_but_not_registered` has A without B — the same validated bytes, never entering the
state. `macro_only_extension` has neither, by construction: its substrate cannot leave the
invariant, so it can name and reuse any existing composition and add no semantics. That is M055's
falsifier, and it is answered structurally rather than by hoping.

The gap attacked here is **not** M089's. That one was fan-in: no operation read two values. This
one is *bending*: every inherited operation moves values affinely, and affine maps compose to
affine maps. The required transformation reads exactly **one** input position — M089's invariant is
untouched and its primitive would not help — and it is not affine.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from metamorphosis.m090_language import (
    CONST_VALUES,
    INPUT_COUNT,
    SLOT_COUNT,
    UNARY_OPERATORS,
    LanguageError,
    MetaLanguageState,
    PrimitiveDefinition,
    digest_of,
    execute,
    run_body,
)
from metamorphosis.m090_migration import migrated_l0
from metamorphosis.m091_expressivity import (
    INVARIANT_NAME,
    INVARIANT_STATEMENT,
    SOUNDNESS_INPUTS,
    abstraction_soundness_report,
    closure_lemma,
    parameter_bindings,
    primitive_bend_witness,
    primitive_shape_report,
    refute_affine_single_source,
)
from metamorphosis.m091_search import (
    BUDGET_REPETITIONS,
    BUDGET_SEARCH_LENGTH,
    SEARCH_LENGTH,
    SearchOutcome,
    encounter,
    evaluate_on_hidden,
    operation_alphabet,
    search_transformation,
)
from metamorphosis.m091_substrate import (
    SEMANTIC_PROBES,
    SIGNATURES,
    argument_row,
    build_definition,
    enumerate_candidate_bodies,
    fingerprint,
    implementation_digest,
    semantics_digest,
    well_formed,
)
from metamorphosis.m091_worlds import required_slots


RESULT_SCHEMA = "m091-result-v1"

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

# Handed the answer by a person. Useful — it shows the rest of the pipeline can exploit a new
# primitive — and never evidence about the lineage. Excluded from the verdict by name.
CEILING_ARMS = ("authored_correct_primitive",)

# A neutral identifier. Nothing anywhere decides anything by comparing against it: adoption is by
# behaviour, the certificates are re-derived from the body, and `test_renaming_the_primitive_
# changes_nothing` proves the name is inert.
PRIMITIVE_ID = "acquired_operation_1"
MACRO_PRIMITIVE_ID = "memoized_composition_1"

EXTENSION_REASON = (
    "the inherited language is closed under affine single-source maps and the required "
    "transformation is not one"
)
MACRO_REASON = "an existing composition of the inherited language, named and reused"

# How far the extensional macro comparison reaches. The invariant certificate is the real proof and
# holds at any length; this is the redundant check a reviewer can re-run.
MACRO_COMPARISON_LENGTH = 3

# A deterministic stride over the length-two programs of the inherited language, used to confirm
# concretely what the abstract lemma predicts. Exhausting that space is unnecessary — the lemma is
# the proof — and slow enough to discourage anyone from re-running the check.
SOUNDNESS_STRIDE = 17

REJECTION_CLASSES = (
    "malformed_or_partial",
    "unsafe_capability",
    "exceeds_the_resource_bound",
    "adds_no_semantics_beyond_the_inherited_invariant",
    "overbroad_widens_the_source_fan_in",
    "abstract_bend_is_not_observable",
    "macro_equivalent_to_an_inherited_composition",
    "registering_it_loses_a_retained_behaviour",
    "validated_but_does_not_make_the_limitation_constructible",
    "validated_but_the_constructed_transformation_does_not_use_it",
)

# A primitive that can blow a value up without bound is refused however well it behaves on the
# limitation. Extension buys expressive power, not licence. The probe states are deliberately far
# from the substrate's own small constants: growth is only visible if something large is fed in,
# and a squaring primitive that looks harmless on inputs below ten does not on four hundred.
RESOURCE_BOUND = 10_000
RESOURCE_PROBES: tuple[tuple[tuple[int, ...], tuple[int, ...]], ...] = (
    ((400, -400, 250), (400, -250, 0, 120)),
    ((-380, 310, -290), (-410, 330, 260, -150)),
)


class LineageError(RuntimeError):
    """Raised when an arm or a phase violates its own contract."""


# ---------------------------------------------------------------------------------------------
# searching for a transformation under a language
# ---------------------------------------------------------------------------------------------


# ---------------------------------------------------------------------------------------------
# diagnosing the limitation
# ---------------------------------------------------------------------------------------------


def _soundness_sample(language: MetaLanguageState) -> list[tuple[tuple[str, tuple[object, ...]], ...]]:
    alphabet = operation_alphabet(language)
    sample: list[tuple[tuple[str, tuple[object, ...]], ...]] = [
        (operation,) for operation in alphabet
    ]
    index = 0
    for first in alphabet:
        for second in alphabet:
            if index % SOUNDNESS_STRIDE == 0:
                sample.append((first, second))
            index += 1
    return sample


def diagnose_limitation(
    world: Mapping[str, object], language: MetaLanguageState, *,
    max_length: int = SEARCH_LENGTH,
) -> dict[str, object]:
    """Prove that the required transformation is outside the constructive image of this language.

    Three independent things, and the verdict needs all of them:

    * the language is **closed** under the affine single-source domain — checked one primitive at a
      time over the whole domain, so induction carries it to any program length and therefore to
      any budget;
    * the abstraction is not lying — concrete slot functions of real programs are re-checked
      against what it predicts;
    * the requirement is outside that domain — a finite certificate refuting every constant, every
      affine map of the position it varies with, and every function of any rival position.

    The exhaustive search is the fourth and weakest item, kept because a reviewer would rather
    re-run something than accept an argument.
    """

    lemma = closure_lemma(language)
    soundness = abstraction_soundness_report(language, _soundness_sample(language))
    certificates = []
    for requirement in world["requirements"]:  # type: ignore[index]
        slot = int(requirement["slot"])  # type: ignore[index]

        def required(inputs: Sequence[int], slot: int = slot) -> int:
            return required_slots(world, inputs)[slot]

        certificates.append(refute_affine_single_source(required, slot))
    search = search_transformation(world, language, max_length=max_length)
    return {
        "world_id": world["world_id"],
        "family": world["family"],
        "invariant": INVARIANT_NAME,
        "statement": INVARIANT_STATEMENT,
        "closure_lemma": lemma,
        "abstraction_soundness": soundness,
        "refutations": certificates,
        "requirement_fan_in": [int(item["fan_in"]) for item in certificates],
        # The whole separation from M089, in one line: this needs ONE input position.
        "requirement_is_single_source": all(item["single_source"] for item in certificates),
        "requirement_outside_the_invariant": all(
            item["outside_affine_single_source"] for item in certificates
        ),
        "exhaustive_search_found_a_program": search.found,
        "exhaustive_search_programs_examined": search.programs_examined,
        "exhaustive_search_distinct_behaviours": search.distinct_behaviours,
        "outside_constructive_image": bool(
            lemma["closed_under_every_primitive"]
            and soundness["abstraction_agrees_with_the_interpreter"]
            and all(item["outside_affine_single_source"] for item in certificates)
            and not search.found
        ),
    }


# ---------------------------------------------------------------------------------------------
# the independent validator
# ---------------------------------------------------------------------------------------------


@dataclass
class Validation:
    accepted: bool
    reasons: list[str] = field(default_factory=list)
    receipt: str = ""
    shape: dict[str, object] = field(default_factory=dict)
    bend_witness: dict[str, object] | None = None
    disposable_trials: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "reasons": self.reasons,
            "receipt": self.receipt,
            "shape": self.shape,
            "bend_witness": self.bend_witness,
            "disposable_trials": self.disposable_trials,
        }


_MACRO_CACHE: dict[tuple[str, ...], frozenset[str]] = {}

_ARGUMENT_DOMAINS: dict[str, tuple[object, ...]] = {
    "const": tuple(CONST_VALUES),
    "input": tuple(range(INPUT_COUNT)),
    "unary_op": tuple(UNARY_OPERATORS),
    "slot": tuple(range(SLOT_COUNT)),
}


def _macro_calls(
    signature: Sequence[str], language: MetaLanguageState,
) -> tuple[tuple[PrimitiveDefinition, tuple[object, ...]], ...]:
    """Every inherited call a macro of this signature may contain, in a deterministic order.

    A macro acts on the primitive's own slot and may pass along the primitive's own input
    parameters, which is the most generous reading of what "an existing composition, named" can
    mean. Being generous here only strengthens the conclusion: the wider this set, the more the
    adopted primitive has to differ from all of it.
    """

    calls: list[tuple[PrimitiveDefinition, tuple[object, ...]]] = []
    for definition in sorted(language.primitives, key=lambda item: item.primitive_id):
        options: list[list[object]] = []
        for index, kind in enumerate(definition.parameter_kinds):
            if index == 0 and kind == "slot":
                options.append(["$0"])
                continue
            choices: list[object] = list(_ARGUMENT_DOMAINS[kind])
            if kind == "input":
                choices.extend(
                    f"${position}" for position, item in enumerate(signature) if item == "input"
                )
            options.append(choices)
        bindings: list[tuple[object, ...]] = [()]
        for choices in options:
            bindings = [item + (choice,) for item in bindings for choice in choices]
        for binding in bindings:
            calls.append((definition, binding))
    return tuple(calls)


def _resolve_call_argument(argument: object, arguments: Sequence[object]) -> object:
    if isinstance(argument, str) and argument.startswith("$"):
        return arguments[int(argument[1:])]
    return argument


def macro_fingerprint(
    calls: Sequence[tuple[PrimitiveDefinition, tuple[object, ...]]], signature: Sequence[str],
) -> str:
    """Fingerprint a composition of inherited calls over the substrate's own probe table.

    Composition is run as a **program** — one call after another on the running slot state —
    rather than by splicing bodies together, because a spliced body would exceed the interpreter's
    length bound and every long macro would collapse to the same "refused" table. That collapse
    would have made the macro test pass for the wrong reason.
    """

    observations: list[object] = []
    for arguments in parameter_bindings(signature):
        for inputs, slots in SEMANTIC_PROBES:
            state = list(slots)
            try:
                for definition, call_arguments in calls:
                    resolved = tuple(
                        _resolve_call_argument(item, arguments) for item in call_arguments
                    )
                    state = run_body(definition.body, resolved, state, inputs)
                observations.append([argument_row(arguments), list(state)])
            except LanguageError:
                observations.append([argument_row(arguments), "refused"])
    return fingerprint(observations)


def inherited_macro_semantics(
    signature: Sequence[str], language: MetaLanguageState,
    max_length: int = MACRO_COMPARISON_LENGTH,
) -> frozenset[str]:
    """Extensional fingerprints of every composition of the inherited language at this signature.

    A primitive whose fingerprint appears here computes something the language already computed,
    however it is spelled and whatever it is called. This is the M055 test done by measurement:
    D019 recorded that M055's acquisition was already inside the closure and bought search cost
    rather than reach. The invariant certificate is the argument that holds at any length; this is
    the bounded check a reviewer can re-run.
    """

    key = tuple(signature)
    if key in _MACRO_CACHE:
        return _MACRO_CACHE[key]

    pieces = _macro_calls(signature, language)
    digests: set[str] = set()
    frontier: list[tuple[tuple[PrimitiveDefinition, tuple[object, ...]], ...]] = [()]
    for _ in range(max_length):
        following: list[tuple[tuple[PrimitiveDefinition, tuple[object, ...]], ...]] = []
        for composition in frontier:
            for piece in pieces:
                extended = composition + (piece,)
                following.append(extended)
                digests.add(macro_fingerprint(extended, signature))
        frontier = following
    result = frozenset(digests)
    _MACRO_CACHE[key] = result
    return result


def no_m055_style_compositional_false_positive(
    definition: PrimitiveDefinition, inherited: MetaLanguageState,
    search_cost: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """The M055 falsifier, as a named report the checker re-derives rather than a hope.

    M055 acquired something already inside its grammar's closure: the candidate count fell from
    737 to 48 and nothing became reachable that was not reachable before. D019 recorded that a
    cheaper search is not a larger capability.

    Three independent things must hold for an extension to escape that verdict, and all three are
    computed here: the primitive must **bend** the invariant the inherited language preserves, with
    a concrete witness rather than an abstract flag; its extensional fingerprint must be absent
    from the closure of inherited compositions; and, when the search-cost record is supplied, the
    gain must be reach rather than a shorter search.
    """

    shape = primitive_shape_report(definition)
    witness = primitive_bend_witness(definition)
    effect = semantics_digest(definition.body, definition.parameter_kinds)
    macros = inherited_macro_semantics(definition.parameter_kinds, inherited)
    cost = dict(search_cost or {})
    reducible = effect in macros
    return {
        "bends_the_invariant": bool(shape["bends_the_affine_invariant"]),
        "bend_witness": witness,
        "bend_is_concretely_witnessed": witness is not None,
        "preserves_single_source": bool(shape["preserves_single_source"]),
        "inherited_compositions_compared": len(macros),
        "macro_reducible_to_the_inherited_language": reducible,
        "gain_was_reach": cost.get("gain_was_reach"),
        "gain_was_search_cost_only": cost.get("gain_was_search_cost_only"),
        "is_an_m055_style_false_positive": bool(
            reducible or witness is None or not shape["bends_the_affine_invariant"]
            or cost.get("gain_was_search_cost_only") is True
        ),
    }


def validate_candidate(
    definition: PrimitiveDefinition, base_language: MetaLanguageState,
    retained_worlds: Sequence[Mapping[str, object]], *, require_bend: bool,
) -> Validation:
    """Independent validation, on a disposable descendant, blind to every qualifying case.

    The builder does not call this on its own behalf and does not see its internals. Nothing here
    asks whether the primitive solves anything: it asks whether the primitive is well formed, safe,
    honest about its own semantics, a real extension rather than a rename, targeted at the
    limitation that was diagnosed rather than at some other one, and harmless to what already
    worked.
    """

    reasons: list[str] = []
    if not well_formed(definition.body, definition.parameter_kinds):
        reasons.append("malformed_or_partial")
        return Validation(False, reasons)
    for capability in definition.capabilities:
        if capability != "pure_slot_write":
            reasons.append("unsafe_capability")
    if _exceeds_resource_bound(definition):
        reasons.append("exceeds_the_resource_bound")
    if reasons:
        return Validation(False, sorted(set(reasons)))

    # A disposable descendant, for every candidate that is well formed and safe: the trial state is
    # registered, searched against, and discarded. It never becomes the live language.
    trials = 1
    trial = base_language.register(definition, "disposable validation descendant")
    for world in retained_worlds:
        before = search_transformation(world, base_language, max_length=2)
        after = search_transformation(world, trial, max_length=2)
        if before.found and not after.found:
            reasons.append("registering_it_loses_a_retained_behaviour")
            break
    if reasons:
        return Validation(False, sorted(set(reasons)), "", {}, None, trials)

    shape = primitive_shape_report(definition)
    if require_bend and not shape["bends_the_affine_invariant"]:
        reasons.append("adds_no_semantics_beyond_the_inherited_invariant")
    if not require_bend and shape["bends_the_affine_invariant"]:
        reasons.append("adds_no_semantics_beyond_the_inherited_invariant")
    if not shape["preserves_single_source"]:
        # M089's primitive lands here. Widening the source fan-in is a different extension from the
        # one that was diagnosed, and an extension nobody proved they needed is overbroad.
        reasons.append("overbroad_widens_the_source_fan_in")

    witness = None
    if require_bend and "adds_no_semantics_beyond_the_inherited_invariant" not in reasons:
        witness = primitive_bend_witness(definition)
        if witness is None:
            # The abstraction over-approximates: it calls every clamp bent even when the branch
            # can never be taken. Without a concrete triple there is no certificate.
            reasons.append("abstract_bend_is_not_observable")

    effect = semantics_digest(definition.body, definition.parameter_kinds)
    macros = inherited_macro_semantics(definition.parameter_kinds, base_language)
    if require_bend and effect in macros:
        reasons.append("macro_equivalent_to_an_inherited_composition")
    if not require_bend and effect not in macros:
        # The macro-only arm's substrate restriction, enforced positively: it may register a
        # composition the inherited language already had, and nothing else.
        reasons.append("macro_equivalent_to_an_inherited_composition")

    accepted = not reasons
    return Validation(
        accepted, sorted(set(reasons)),
        digest_of({
            "primitive": definition.to_dict(),
            "semantics": effect,
            "shape": shape,
            "bend_witness": witness,
            "accepted": True,
        }) if accepted else "",
        shape, witness, trials,
    )


def _exceeds_resource_bound(definition: PrimitiveDefinition) -> bool:
    """Whether the primitive can send a value outside the frozen magnitude bound on its probes."""

    for arguments in parameter_bindings(definition.parameter_kinds):
        for inputs, slots in SEMANTIC_PROBES + RESOURCE_PROBES:
            try:
                after = run_body(definition.body, arguments, list(slots), inputs)
            except LanguageError:
                continue
            if any(abs(int(value)) > RESOURCE_BOUND for value in after):
                return True
    return False


# ---------------------------------------------------------------------------------------------
# construction and adoption
# ---------------------------------------------------------------------------------------------


# The macro-only arm's own target. It is deliberately **inside** the inherited language's
# constructive image and four operations deep, so that memoizing a composition shortens the search
# without adding anything. That is M055's situation exactly — acquisition took the candidate count
# from 737 to 48 while everything remained reachable — and reproducing it here on purpose is what
# makes that arm's later failure informative rather than empty.
MACRO_TARGET_WORLD: dict[str, object] = {
    "world_id": "retained_eightfold_gain",
    "family": "retained",
    "narrative": (
        "The logged channel is reported at eightfold gain: three successive doublings of the raw "
        "reading. Nothing here is beyond the inherited language; it is merely four operations deep."
    ),
    "input_names": ["deviation", "gain", "tolerance"],
    "requirements": [
        {"slot": 0, "expression": ["double", ["double", ["double", ["input", 0]]]]},
    ],
    "invariants": [{"kind": "matches_requirement", "slot": 0}],
    "public_instances": [
        {"payload": {}, "inputs": [-4, 3, 7]},
        {"payload": {}, "inputs": [0, 5, -3]},
        {"payload": {}, "inputs": [6, 1, 0]},
    ],
}

RETAINED_WORLDS: tuple[dict[str, object], ...] = (
    {
        "world_id": "retained_passthrough",
        "family": "retained",
        "narrative": "the calibrated reading reaches the log unchanged",
        "input_names": ["deviation", "gain", "tolerance"],
        "requirements": [{"slot": 1, "expression": ["input", 1]}],
        "invariants": [{"kind": "matches_requirement", "slot": 1}],
        "public_instances": [
            {"payload": {}, "inputs": [-4, 3, 7]},
            {"payload": {}, "inputs": [0, 5, -3]},
        ],
    },
    {
        "world_id": "retained_scaled",
        "family": "retained",
        "narrative": "the reading is logged at double gain",
        "input_names": ["deviation", "gain", "tolerance"],
        "requirements": [{"slot": 2, "expression": ["double", ["input", 2]]}],
        "invariants": [{"kind": "matches_requirement", "slot": 2}],
        "public_instances": [
            {"payload": {}, "inputs": [-4, 3, 7]},
            {"payload": {}, "inputs": [0, 5, -3]},
        ],
    },
)


@dataclass
class Acquisition:
    mode: str
    diagnosis: dict[str, object]
    candidates_assembled: int = 0
    candidates_well_formed: int = 0
    candidates_validated: int = 0
    rejected: list[dict[str, object]] = field(default_factory=list)
    rejection_counts: dict[str, int] = field(default_factory=dict)
    disposable_trials: int = 0
    adopted: PrimitiveDefinition | None = None
    validation: Validation | None = None
    extended: MetaLanguageState | None = None
    program: tuple[tuple[str, tuple[object, ...]], ...] | None = None
    search_cost: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        base = migrated_l0()
        return {
            "mode": self.mode,
            "diagnosis": self.diagnosis,
            "candidates_assembled": self.candidates_assembled,
            "candidates_well_formed": self.candidates_well_formed,
            "candidates_validated": self.candidates_validated,
            "rejected_count": len(self.rejected),
            "rejection_counts": dict(sorted(self.rejection_counts.items())),
            "rejection_classes_observed": sorted(self.rejection_counts),
            "rejected_examples": self.rejected[:12],
            "disposable_trials": self.disposable_trials,
            "adopted_primitive": self.adopted.to_dict() if self.adopted else None,
            "adopted_semantics_digest": (
                self.adopted.semantics_digest() if self.adopted else None
            ),
            "adopted_implementation_digest": (
                implementation_digest(self.adopted.body) if self.adopted else None
            ),
            "adopted_substrate_fingerprint": (
                semantics_digest(self.adopted.body, self.adopted.parameter_kinds)
                if self.adopted else None
            ),
            "validation": self.validation.to_dict() if self.validation else None,
            "l0_digest": base.digest(),
            "l1_digest": self.extended.digest() if self.extended else None,
            "l1_version": self.extended.language_version if self.extended else None,
            "development_program": [
                [name, list(arguments)] for name, arguments in (self.program or ())
            ],
            "search_cost": dict(self.search_cost),
        }


def _record_rejection(
    acquisition: Acquisition, definition: PrimitiveDefinition, reasons: Sequence[str],
) -> None:
    for reason in reasons:
        acquisition.rejection_counts[reason] = acquisition.rejection_counts.get(reason, 0) + 1
    acquisition.rejected.append({
        "implementation_digest": implementation_digest(definition.body),
        "signature": list(definition.parameter_kinds),
        "body_length": len(definition.body),
        "reasons": list(reasons),
    })


def acquire_primitive(
    world: Mapping[str, object], *, mode: str = "expressive",
    assembly_limit: int = 250_000,
) -> Acquisition:
    """Assemble candidates, have them validated elsewhere, adopt the first that closes the gap.

    `mode="macro_only"` is the M055 control. It is a restriction on the **substrate**, not on the
    outcome: the validator inverts its bend requirement, so that arm may assemble, name and reuse
    any composition the inherited language already had, and may not add semantics. It adopts a
    real primitive — an arm that acquires nothing proves nothing — and then fails.

    The selection rule is frozen and is not the answer in disguise: signatures in their declared
    order, bodies shortest first and then in alphabet order, the first that the independent
    validator accepts **and** that makes the diagnosed limitation constructible. Nothing consults
    an identifier, and nothing consults a qualifying case, which does not exist yet.
    """

    if mode not in {"expressive", "macro_only"}:
        raise LineageError(f"unknown acquisition mode {mode!r}")
    base = migrated_l0()
    acquisition = Acquisition(mode, diagnose_limitation(world, base))
    require_bend = mode == "expressive"

    for signature in SIGNATURES:
        for body in enumerate_candidate_bodies(signature):
            acquisition.candidates_assembled += 1
            if acquisition.candidates_assembled > assembly_limit:
                return acquisition
            definition = build_definition(
                PRIMITIVE_ID if require_bend else MACRO_PRIMITIVE_ID, body, signature,
                ("assembled from the frozen extension substrate",),
            )
            # Every assembled body is handed to the validator, including the ill-formed ones. The
            # census of what was refused, and for which reason, is then a real census rather than
            # a report on a population already filtered by the builder's own judgement.
            validation = validate_candidate(
                definition, base, RETAINED_WORLDS, require_bend=require_bend,
            )
            acquisition.candidates_validated += 1
            acquisition.disposable_trials += validation.disposable_trials
            if "malformed_or_partial" not in validation.reasons:
                acquisition.candidates_well_formed += 1
            if not validation.accepted:
                _record_rejection(acquisition, definition, validation.reasons)
                continue
            # A disposable descendant again: registered, searched against, and kept only if the
            # limitation actually closes. Nothing here consults a qualifying case.
            trial = base.register(definition, EXTENSION_REASON if require_bend else MACRO_REASON)
            acquisition.disposable_trials += 1
            found = search_transformation(world, trial)
            if not found.found:
                _record_rejection(
                    acquisition, definition,
                    ["validated_but_does_not_make_the_limitation_constructible"],
                )
                continue
            if not found.uses_acquired_primitive:
                # The shortest transformation ignores it, so registering it changed nothing about
                # what the lineage does. A primitive nobody calls is not an extension.
                _record_rejection(
                    acquisition, definition,
                    ["validated_but_the_constructed_transformation_does_not_use_it"],
                )
                continue
            acquisition.adopted = definition
            acquisition.validation = validation
            acquisition.extended = trial
            acquisition.program = found.program
            acquisition.search_cost = _search_cost(world, base, found)
            return acquisition
    return acquisition


def _search_cost(
    world: Mapping[str, object], base: MetaLanguageState, extended: SearchOutcome,
) -> dict[str, object]:
    """What the extension bought: reach, or merely a shorter search?

    D019 recorded the distinction M055 failed: acquisition there cut the candidate count and
    changed nothing about what was reachable. Both numbers are recorded here for whichever arm
    produced them, so the two cases are told apart by measurement rather than by assertion.
    """

    without = search_transformation(world, base)
    return {
        "without_extension_found": without.found,
        "without_extension_programs_examined": without.programs_examined,
        "without_extension_program_length": len(without.program or ()),
        "with_extension_programs_examined": extended.programs_examined,
        "with_extension_program_length": len(extended.program or ()),
        # True when the inherited language could already do it and the extension only made it
        # cheaper to find. That is a search-cost gain and not an expressive one.
        "gain_was_search_cost_only": bool(without.found),
        "gain_was_reach": not without.found,
    }


def acquire_macro_primitive() -> Acquisition:
    """The macro-only arm's acquisition: it succeeds at acquiring, and that is the point.

    It is given a world the inherited language can already solve four operations deep, so it has
    something worth memoizing, and the adoption rule requires the shortened transformation to
    actually call what it registered. What it cannot do is leave the invariant, and the qualifying
    worlds are outside it.
    """

    return acquire_primitive(MACRO_TARGET_WORLD, mode="macro_only")


# ---------------------------------------------------------------------------------------------
# conservation: the enlarged language must still be the inherited one, exactly
# ---------------------------------------------------------------------------------------------

CONSERVATION_INPUTS: tuple[tuple[int, ...], ...] = ((1, 2, 3), (0, 4, 1), (-2, 5, 7), (9, 0, 6))

# Calls the inherited language refuses. Conservation is not only about what a language accepts:
# M090's amendment A2 was a widened *accepted* domain that a conservation report had excluded, so
# the refusals are checked too, and the space below excludes nothing.
REJECTION_PROBES: tuple[tuple[str, tuple[object, ...]], ...] = (
    ("SET_CONST", (0, 2)),
    ("SET_CONST", (4, 0)),
    ("SET_CONST", (-1, 1)),
    ("COPY_INPUT", (0, 3)),
    ("COPY_INPUT", (2, -1)),
    ("APPLY_UNARY", (0, "identity")),
    ("APPLY_UNARY", (0, "square")),
    ("APPLY_UNARY", (5, "inc")),
    ("SET_CONST", (0,)),
    ("COPY_INPUT", (0, 1, 2)),
)


def _outcome(
    program: Sequence[tuple[str, tuple[object, ...]]], inputs: Sequence[int],
    language: MetaLanguageState,
) -> tuple[object, str | None]:
    try:
        return tuple(execute(program, inputs, language)), None
    except LanguageError as exc:
        return "refused", str(exc)


def conservation_report(
    inherited: MetaLanguageState, enlarged: MetaLanguageState, max_length: int = 2,
) -> dict[str, object]:
    """Every inherited behaviour, and every inherited refusal, must survive the extension unchanged.

    The space is the **complete** cross product of every declared parameter domain, and the report
    says so and is checked on it. An operator excluded from a conservation space is an operator
    whose conservation is unproved, which is exactly how a widened domain hid in M090's first
    draft until external review of PR #138 found it.
    """

    declared: dict[str, int] = {}
    for definition in inherited.primitives:
        declared[definition.primitive_id] = len(parameter_bindings(definition.parameter_kinds))
    alphabet = operation_alphabet(inherited)
    covered: dict[str, int] = {}
    for name, _ in alphabet:
        covered[name] = covered.get(name, 0) + 1

    mismatches: list[dict[str, object]] = []
    checked = 0
    programs: list[tuple[tuple[str, tuple[object, ...]], ...]] = [(item,) for item in alphabet]
    if max_length >= 2:
        programs.extend((first, second) for first in alphabet for second in alphabet)
    for program in programs:
        for inputs in CONSERVATION_INPUTS:
            checked += 1
            before = _outcome(program, inputs, inherited)
            after = _outcome(program, inputs, enlarged)
            if before != after:
                mismatches.append({
                    "program": [[name, list(args)] for name, args in program],
                    "inputs": list(inputs),
                    "inherited": str(before), "enlarged": str(after),
                })

    rejection_mismatches: list[dict[str, object]] = []
    for probe in REJECTION_PROBES:
        for inputs in CONSERVATION_INPUTS[:2]:
            before = _outcome((probe,), inputs, inherited)
            after = _outcome((probe,), inputs, enlarged)
            if before[0] != "refused" or before != after:
                rejection_mismatches.append({
                    "probe": [probe[0], list(probe[1])],
                    "inherited": str(before), "enlarged": str(after),
                })

    definitions_identical = all(
        (enlarged.definition(item.primitive_id).to_dict() if enlarged.definition(item.primitive_id)
         else None) == item.to_dict()
        for item in inherited.primitives
    )
    return {
        "programs_checked": len(programs),
        "calls_checked": checked,
        "max_length": max_length,
        "declared_binding_counts": dict(sorted(declared.items())),
        "covered_binding_counts": dict(sorted(covered.items())),
        "space_excludes_nothing": declared == covered,
        "mismatches": mismatches[:10],
        "mismatch_count": len(mismatches),
        "semantics_conserved": not mismatches and definitions_identical,
        "inherited_definitions_identical": definitions_identical,
        "rejection_probe_count": len(REJECTION_PROBES),
        "rejection_mismatches": rejection_mismatches[:10],
        "rejection_behaviour_conserved": not rejection_mismatches,
        "inherited_primitive_ids": sorted(inherited.primitive_ids),
        "enlarged_primitive_ids": sorted(enlarged.primitive_ids),
    }


# ---------------------------------------------------------------------------------------------
# the state is the execution authority
# ---------------------------------------------------------------------------------------------


def state_authority_report(
    enlarged: MetaLanguageState, programs: Sequence[Sequence[tuple[str, tuple[object, ...]]]],
    acquired_id: str, inherited_id: str = "COPY_INPUT",
) -> dict[str, object]:
    """Delete an operation from the state and the transformation must actually stop working.

    D059's question, asked of the acquired operation as well as an inherited one. M089 answered
    *no* for inherited operations because the interpreter read a module constant; M090 removed that
    split; here both answers must be *yes*, or the registration was decoration.
    """

    inputs = CONSERVATION_INPUTS[0]
    without_acquired = enlarged.without(acquired_id, "authority probe: acquired operation removed")
    without_inherited = enlarged.without(inherited_id, "authority probe: inherited operation removed")
    intact, acquired_removed, inherited_removed = [], [], []
    for program in programs:
        intact.append(_outcome(tuple(program), inputs, enlarged))
        acquired_removed.append(_outcome(tuple(program), inputs, without_acquired))
        inherited_removed.append(_outcome(tuple(program), inputs, without_inherited))
    return {
        "probed_programs": [[[name, list(args)] for name, args in item] for item in programs],
        "outcomes_intact": [str(item) for item in intact],
        "outcomes_with_acquired_removed": [str(item) for item in acquired_removed],
        "outcomes_with_inherited_removed": [str(item) for item in inherited_removed],
        "all_ran_intact": all(item[0] != "refused" for item in intact),
        "removing_the_primitive_from_state_removes_the_transformation": all(
            item[0] == "refused" for item in acquired_removed
        ),
        "removing_an_inherited_primitive_removes_it_too": all(
            item[0] == "refused" for item in inherited_removed
        ),
    }


# ---------------------------------------------------------------------------------------------
# rollback, on both sides of the extension
# ---------------------------------------------------------------------------------------------


def _observe(language: MetaLanguageState, probes: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    observations: list[dict[str, object]] = []
    for probe in probes:
        program = tuple((name, tuple(args)) for name, args in probe["program"])  # type: ignore[index]
        try:
            output: object = list(execute(program, tuple(probe["inputs"]), language))  # type: ignore[arg-type]
            refused, error = False, None
        except LanguageError as exc:
            output, refused, error = None, True, str(exc)
        observations.append({
            "probe_id": probe["probe_id"], "output": output, "refused": refused, "error": error,
        })
    return observations


def _differing(
    before: Sequence[Mapping[str, object]], after: Sequence[Mapping[str, object]],
) -> list[str]:
    lookup = {str(item["probe_id"]): item for item in after}
    return sorted(
        str(item["probe_id"]) for item in before
        if (item["output"], item["refused"]) != (
            lookup[str(item["probe_id"])]["output"], lookup[str(item["probe_id"])]["refused"],
        )
    )


def rollback_proof(
    checkpoint_state: MetaLanguageState, live_state: MetaLanguageState,
    probes: Sequence[Mapping[str, object]], *, fault: str, target: str, label: str,
) -> dict[str, object]:
    """Checkpoint one state, damage a different live one, restore the checkpoint exactly.

    D023 closed M064 over a receipt that compared the saved state to itself; PR #136 found that
    shape in M088 and PR #137 a metadata-only version in M089. Here the checkpoint is serialized
    first and kept apart, the fault strikes the **live** state, the damage is proved by running
    programs rather than by comparing version numbers, and restoration reads the checkpoint bytes.

    Before adoption the live state is the provisional extended language and the checkpoint is the
    inherited one, so restoring is a real reversal rather than an identity.
    """

    checkpoint_bytes = json.dumps(
        checkpoint_state.to_dict(), sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    checkpoint_digest = digest_of(json.loads(checkpoint_bytes.decode("utf-8")))
    checkpoint_observations = _observe(checkpoint_state, probes)

    live = MetaLanguageState.from_dict(json.loads(json.dumps(live_state.to_dict())))
    live_observations = _observe(live, probes)
    if fault == "removal":
        damaged = live.without(target, f"forced fault: removed {target}")
    elif fault == "semantic_mutation":
        damaged = live.with_mutated(
            target, (("PUSH_CONST", 0), ("STORE_SLOT", "$0")), f"forced fault: rewrote {target}",
        )
    else:
        raise LineageError(f"unknown fault class {fault!r}")
    damaged_observations = _observe(damaged, probes)

    restored = MetaLanguageState.from_dict(json.loads(checkpoint_bytes.decode("utf-8")))
    restored_bytes = json.dumps(
        restored.to_dict(), sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    restored_observations = _observe(restored, probes)

    return {
        "label": label,
        "fault_class": fault,
        "fault_target": target,
        "checkpoint_digest": checkpoint_digest,
        "live_digest": live.digest(),
        "damaged_digest": damaged.digest(),
        "live_state_differed_from_the_checkpoint": live.digest() != checkpoint_digest,
        "corruption_detected": damaged.digest() != live.digest(),
        "probes_changed_by_the_fault": _differing(live_observations, damaged_observations),
        "fault_actually_changed_behaviour": bool(
            _differing(live_observations, damaged_observations)
        ),
        "byte_identical_restore": restored_bytes == checkpoint_bytes,
        "restored_digest": restored.digest(),
        "digest_matches": restored.digest() == checkpoint_digest,
        "behaviour_restored": _differing(checkpoint_observations, restored_observations) == [],
        # Before adoption the live state is the provisional extended language, so restoring the
        # checkpoint must take the extension away again. Without this the restore could be an
        # identity dressed as a recovery, which is the shape D023 closed M064 over.
        "probes_changed_by_restoring_the_checkpoint": _differing(
            live_observations, restored_observations
        ),
        "restore_reversed_the_live_state": bool(
            _differing(live_observations, restored_observations)
        ),
        "checkpoint_observations": checkpoint_observations,
        "live_observations": live_observations,
        "damaged_observations": damaged_observations,
        "restored_observations": restored_observations,
    }


# ---------------------------------------------------------------------------------------------
# arms
# ---------------------------------------------------------------------------------------------


def language_for_arm(
    arm: str, acquisition: Acquisition, ceiling_primitive: PrimitiveDefinition | None = None,
) -> tuple[MetaLanguageState, dict[str, object]]:
    """The language each arm faces, and what it was and was not given.

    The ceiling arm's primitive is passed in rather than written here. Nothing on the acquisition
    path may contain the answer as a literal, and the anti-lookup scan checks exactly that, so the
    authored body lives in the runner where the assembler cannot reach it.
    """

    base = migrated_l0()
    notes: dict[str, object] = {
        "acquisition_attempted": False,
        "primitive_built": False,
        "primitive_registered": False,
        "built_but_unregistered_digest": None,
        "handed_an_authored_primitive": False,
    }
    if arm == "evolvable_meta_language":
        if acquisition.extended is None:
            return base, notes
        # Restored from its serialized form rather than rebuilt: persistence, not reconstruction.
        language = MetaLanguageState.from_dict(json.loads(json.dumps(acquisition.extended.to_dict())))
        notes.update(
            acquisition_attempted=True, primitive_built=True, primitive_registered=True,
        )
        return language, notes
    if arm in {"fixed_meta_language", "fresh_agent", "more_budget_same_meta_language"}:
        return base, notes
    if arm == "extension_acquisition_ablated":
        # No acquisition mechanism at all: the arm cannot even attempt to build.
        return base, notes
    if arm == "extension_built_but_not_registered":
        if acquisition.adopted is None:
            return base, notes
        notes.update(
            acquisition_attempted=True, primitive_built=True, primitive_registered=False,
            built_but_unregistered_digest=implementation_digest(acquisition.adopted.body),
            body_runs_on_the_substrate_directly=bool(
                run_body(
                    acquisition.adopted.body, parameter_bindings(
                        acquisition.adopted.parameter_kinds
                    )[0], [0, 0, 0, 0], SOUNDNESS_INPUTS[0],
                ) is not None
            ),
        )
        return base, notes
    if arm == "macro_only_extension":
        macro = acquire_macro_primitive()
        notes.update(
            acquisition_attempted=True,
            primitive_built=macro.adopted is not None,
            primitive_registered=macro.extended is not None,
            macro_primitive=macro.adopted.to_dict() if macro.adopted else None,
            macro_rejected_count=len(macro.rejected),
            macro_search_cost=dict(macro.search_cost),
            macro_gain_was_search_cost_only=bool(macro.search_cost.get("gain_was_search_cost_only")),
        )
        return (macro.extended or base), notes
    if arm == "authored_correct_primitive":
        if ceiling_primitive is None:
            raise LineageError("the ceiling arm was not handed a primitive")
        notes.update(
            handed_an_authored_primitive=True, primitive_registered=True,
            primitive_built=False,
        )
        return base.register(ceiling_primitive, "handed to the ceiling arm by a person"), notes
    raise LineageError(f"unknown arm {arm!r}")


def run_arm(
    arm: str, acquisition: Acquisition, worlds: Sequence[Mapping[str, object]],
    ceiling_primitive: PrimitiveDefinition | None = None,
) -> dict[str, object]:
    if arm not in ARMS:
        raise LineageError(f"unknown arm {arm!r}")
    language, notes = language_for_arm(arm, acquisition, ceiling_primitive)
    budgeted = arm == "more_budget_same_meta_language"
    max_length = BUDGET_SEARCH_LENGTH if budgeted else SEARCH_LENGTH
    repetitions = BUDGET_REPETITIONS if budgeted else 1

    encounters = [
        encounter(world, language, max_length=max_length, repetitions=repetitions)
        for world in worlds
    ]
    correct = [item for item in encounters if item["correct"]]
    return {
        "arm": arm,
        "is_ceiling": arm in CEILING_ARMS,
        "language_digest": language.digest(),
        "language_version": language.language_version,
        "primitive_ids": sorted(language.primitive_ids),
        "acquired_primitive_ids": sorted(
            item.primitive_id for item in language.primitives if item.origin == "acquired"
        ),
        "max_search_length": max_length,
        "repetitions": repetitions,
        "encounters": encounters,
        "correct_worlds": len(correct),
        "encounter_count": len(encounters),
        "families_solved": sorted({str(item["family"]) for item in correct}),
        "total_programs_examined": sum(
            int(item["search"]["programs_examined"]) for item in encounters
        ),
        "total_distinct_behaviours": sum(
            int(item["search"]["distinct_behaviours"]) for item in encounters
        ),
        "uses_acquired_primitive": any(
            item["search"]["uses_acquired_primitive"] for item in encounters
        ),
        **notes,
    }


# ---------------------------------------------------------------------------------------------
# the frozen verdict
# ---------------------------------------------------------------------------------------------

CONDITIONS = (
    "P1_inherited_language_provably_cannot_express_the_transformation",
    "P2_primitive_assembled_from_the_substrate_rather_than_selected",
    "P3_primitive_is_not_reducible_to_a_composition_of_the_inherited_language",
    "P4_an_independent_validator_accepted_it_without_seeing_the_qualification",
    "P5_the_primitive_is_registered_in_the_state_owned_language",
    "P6_the_transformation_is_outside_l0_and_inside_l1",
    "P7_correctness_difference_on_worlds_the_lineage_never_searched",
    "P8_more_budget_in_the_same_language_closes_nothing",
    "P9_a_macro_only_extension_closes_nothing",
    "P10_building_without_registering_closes_nothing",
    "P11_the_inherited_semantics_are_conserved_exactly",
    "P12_rollback_is_exact_and_behavioural_on_both_sides",
    "P13_the_extension_persists_and_is_reused_in_a_fresh_process",
    "P14_chronology_track_a_and_no_leaked_evidence",
)


def evaluate(
    acquisition: Mapping[str, object], arms: Mapping[str, Mapping[str, object]],
    rollback: Mapping[str, Mapping[str, object]], conservation: Mapping[str, object],
    persistence: Mapping[str, object], integrity: Mapping[str, object],
) -> dict[str, object]:
    """Every condition computed, and every one able to make the verdict negative."""

    evolvable = arms["evolvable_meta_language"]
    fixed = arms["fixed_meta_language"]
    ablated = arms["extension_acquisition_ablated"]
    unregistered = arms["extension_built_but_not_registered"]
    macro = arms["macro_only_extension"]
    budgeted = arms["more_budget_same_meta_language"]
    fresh = arms["fresh_agent"]

    diagnosis = acquisition["diagnosis"]
    assert isinstance(diagnosis, Mapping)
    validation = acquisition["validation"]
    adopted = acquisition["adopted_primitive"]

    solved = set(evolvable["families_solved"])
    discordant = sorted(solved - set(fixed["families_solved"]))

    results = {
        "P1_inherited_language_provably_cannot_express_the_transformation": bool(
            diagnosis["outside_constructive_image"] is True
            and diagnosis["closure_lemma"]["closed_under_every_primitive"] is True  # type: ignore[index]
            and diagnosis["abstraction_soundness"]["abstraction_agrees_with_the_interpreter"] is True  # type: ignore[index]
            and diagnosis["requirement_outside_the_invariant"] is True
            and diagnosis["exhaustive_search_found_a_program"] is False
            # The separation from M089: the requirement needs one input position, not two.
            and diagnosis["requirement_is_single_source"] is True
        ),
        "P2_primitive_assembled_from_the_substrate_rather_than_selected": bool(
            adopted is not None
            and int(acquisition["candidates_assembled"]) >= 1000
            and int(acquisition["candidates_validated"]) >= 50
            and int(acquisition["rejected_count"]) >= 40
            and len(list(acquisition["rejection_classes_observed"])) >= 4
            and integrity["adopted_body_is_not_a_literal_in_the_lineage"] is True
        ),
        "P3_primitive_is_not_reducible_to_a_composition_of_the_inherited_language": bool(
            isinstance(validation, Mapping)
            and validation["bend_witness"] is not None
            and validation["shape"]["bends_the_affine_invariant"] is True  # type: ignore[index]
            and validation["shape"]["preserves_single_source"] is True  # type: ignore[index]
            and integrity["adopted_fingerprint_absent_from_the_inherited_closure"] is True
        ),
        "P4_an_independent_validator_accepted_it_without_seeing_the_qualification": bool(
            isinstance(validation, Mapping)
            and validation["accepted"] is True
            and bool(validation["receipt"])
            and int(acquisition["disposable_trials"]) >= 50
            and integrity["validator_cannot_reach_the_qualification"] is True
        ),
        "P5_the_primitive_is_registered_in_the_state_owned_language": bool(
            acquisition["l1_digest"] is not None
            and acquisition["l1_digest"] != acquisition["l0_digest"]
            and int(acquisition["l1_version"] or 0) == 1
            and persistence["removing_the_primitive_from_state_removes_the_transformation"] is True
        ),
        "P6_the_transformation_is_outside_l0_and_inside_l1": bool(
            evolvable["uses_acquired_primitive"] is True
            and evolvable["correct_worlds"] == evolvable["encounter_count"]
            and int(evolvable["encounter_count"]) >= 2
            and fixed["correct_worlds"] == 0
            and ablated["correct_worlds"] == 0
        ),
        "P7_correctness_difference_on_worlds_the_lineage_never_searched": bool(
            len(discordant) >= 2
            and all(
                int(item["hidden_total"]) >= 4 and int(item["hidden_passed"]) == int(item["hidden_total"])
                for item in evolvable["encounters"]  # type: ignore[union-attr]
            )
            and integrity["qualification_materialized_after_the_language_was_frozen"] is True
        ),
        "P8_more_budget_in_the_same_language_closes_nothing": bool(
            budgeted["correct_worlds"] == 0
            and int(budgeted["total_programs_examined"]) > int(fixed["total_programs_examined"])
            and int(budgeted["total_distinct_behaviours"]) > int(fixed["total_distinct_behaviours"])
            and int(budgeted["max_search_length"]) > int(fixed["max_search_length"])
        ),
        "P9_a_macro_only_extension_closes_nothing": bool(
            macro["correct_worlds"] == 0
            # An arm that acquires nothing proves nothing: it must really have extended itself,
            # and what it registered must really have been used.
            and macro["primitive_registered"] is True
            and int(macro["language_version"]) == 1
            # And what it bought must be visibly search cost rather than reach — M055's situation,
            # reproduced deliberately so that its failure here means something.
            and macro["macro_gain_was_search_cost_only"] is True
            and acquisition["search_cost"]["gain_was_reach"] is True  # type: ignore[index]
        ),
        "P10_building_without_registering_closes_nothing": bool(
            unregistered["correct_worlds"] == 0
            and unregistered["primitive_built"] is True
            and unregistered["primitive_registered"] is False
            and unregistered["built_but_unregistered_digest"] is not None
            and unregistered.get("body_runs_on_the_substrate_directly") is True
        ),
        "P11_the_inherited_semantics_are_conserved_exactly": bool(
            conservation["semantics_conserved"] is True
            and conservation["space_excludes_nothing"] is True
            and conservation["rejection_behaviour_conserved"] is True
            and int(conservation["calls_checked"]) >= 1000
        ),
        "P12_rollback_is_exact_and_behavioural_on_both_sides": bool(
            all(_rollback_ok(rollback[side]) for side in ("before_adoption", "after_adoption"))
            and rollback["before_adoption"]["live_state_differed_from_the_checkpoint"] is True
            # The provisional extension really was taken away again, rather than a checkpoint
            # being compared with itself.
            and rollback["before_adoption"]["restore_reversed_the_live_state"] is True
        ),
        "P13_the_extension_persists_and_is_reused_in_a_fresh_process": bool(
            persistence["fresh_process_solves_every_world"] is True
            and persistence["fresh_process_reused_the_same_primitive_semantics"] is True
            and persistence["fresh_process_registered_nothing_new"] is True
            and persistence["fresh_process_imported_no_development_module"] is True
            and persistence["removed_primitive_refused_in_fresh_process"] is True
            and persistence["removing_the_primitive_from_state_removes_the_transformation"] is True
            and persistence["removing_an_inherited_primitive_removes_it_too"] is True
            and fresh["correct_worlds"] == 0
        ),
        "P14_chronology_track_a_and_no_leaked_evidence": bool(
            integrity["model_calls"] == 0
            and integrity["network_calls"] == 0
            and integrity["declared_conditions_match_evaluated_conditions"] is True
            and integrity["qualification_not_reachable_from_the_lineage"] is True
            and integrity["chronology_in_causal_order"] is True
            and integrity["no_lookup_of_the_answer"] is True
        ),
    }
    verdict = all(results.values())
    return {
        "conditions": {name: bool(results[name]) for name in CONDITIONS},
        "verdict": "positive" if verdict else "negative",
        "hypothesis_supported": verdict,
        "discordant_families": discordant,
        "evolvable_families_solved": sorted(solved),
        "fixed_families_solved": sorted(set(fixed["families_solved"])),
        "ceiling_arm_families_solved": sorted(
            set(arms["authored_correct_primitive"]["families_solved"])
        ),
        "failed_conditions": [name for name in CONDITIONS if not results[name]],
    }


def _rollback_ok(proof: Mapping[str, object]) -> bool:
    return bool(
        proof["corruption_detected"]
        and proof["fault_actually_changed_behaviour"]
        and proof["byte_identical_restore"]
        and proof["digest_matches"]
        and proof["behaviour_restored"]
    )


__all__ = [
    "ARMS", "BUDGET_REPETITIONS", "BUDGET_SEARCH_LENGTH", "CEILING_ARMS", "CONDITIONS",
    "CONSERVATION_INPUTS", "EXTENSION_REASON", "MACRO_COMPARISON_LENGTH", "MACRO_PRIMITIVE_ID",
    "MACRO_REASON", "MACRO_TARGET_WORLD", "PRIMITIVE_ID", "REJECTION_CLASSES", "REJECTION_PROBES",
    "RESOURCE_BOUND",
    "RESULT_SCHEMA", "RETAINED_WORLDS", "SEARCH_LENGTH", "Acquisition", "LineageError",
    "SearchOutcome", "Validation", "acquire_macro_primitive", "acquire_primitive",
    "conservation_report", "diagnose_limitation", "evaluate",
    "evaluate_on_hidden", "inherited_macro_semantics", "language_for_arm", "macro_fingerprint",
    "no_m055_style_compositional_false_positive", "operation_alphabet", "rollback_proof",
    "run_arm", "search_transformation", "state_authority_report", "validate_candidate",
]
