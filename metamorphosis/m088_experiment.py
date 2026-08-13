"""The experiment constructor as a serialized program, and the language that rewrites it.

M087 ended with the lineage able to *choose* an experiment and unable to *build* one: its
`experiment_space` was a literal tuple of strings the harness handed in, and the policy filtered
and ranked it. D057 recorded that as one of two remaining ceilings.

Here the space is not handed in. The world offers a small vocabulary of interaction primitives —
`reset`, `send_a`, `observe` and so on — and the lineage must construct programs out of them. An
experiment is an `ExperimentProgram`: an ordered sequence of steps with a construction trace, not
an index into a list.

`m0_constructor()` is legitimately limited rather than a strawman. It builds every program of the
shape *reset, one action, observe* — which is exactly the depth at which M087's request/value
probes lived, one interaction deep. Its constructive image is finite and is **enumerated** by
`constructive_image`, so "M1 built something M0 could not" is proved by exhaustion rather than
asserted.

The meta-language rewrites the constructor. No primitive means "build the discriminating
experiment": the operations add a composition depth, a sequencing rule, a validity rule, a
projection or a deduplication, and several combinations are plausible and useless.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from typing import Mapping, Sequence


CONSTRUCTOR_SCHEMA = "m088-experiment-constructor-v1"

# What a constructor may be told to do. Every entry is a general operation over an interaction
# vocabulary; none names a world, a candidate, a truth or a particular program.
CONSTRUCTOR_RULES = (
    "PREFIX_RESET",          # every program starts from a known state
    "EMIT_SINGLE_ACTION",    # one action between reset and observation
    "EMIT_ACTION_SEQUENCE",  # compose several actions before observing
    "PERMUTE_ORDER",         # treat two orderings of the same actions as different programs
    "ALLOW_REPETITION",      # a program may use one action more than once
    "SUFFIX_OBSERVE",        # end by reading the world
    "DEDUPLICATE",           # drop programs whose step lists coincide
    "REQUIRE_OBSERVATION",   # refuse a program that never observes anything
)

MAX_SUPPORTED_DEPTH = 4


class ConstructorError(RuntimeError):
    """Raised when a constructor program or meta-transformation breaks the contract."""


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


@dataclass(frozen=True)
class ExperimentProgram:
    """An experiment as an executable plan, with the trace of how it was built."""

    steps: tuple[str, ...]
    construction_trace: tuple[str, ...]
    depth: int

    @property
    def program_id(self) -> str:
        return hashlib.sha256(_canonical(list(self.steps))).hexdigest()[:16]

    def to_dict(self) -> dict[str, object]:
        return {
            "program_id": self.program_id,
            "steps": list(self.steps),
            "depth": self.depth,
            "construction_trace": list(self.construction_trace),
        }


@dataclass(frozen=True)
class ExperimentConstructor:
    """The mutable artifact: which rules are active, and how deep composition may go."""

    rules: tuple[str, ...]
    max_depth: int
    provenance: tuple[str, ...] = ()
    version: int = 0

    def __post_init__(self) -> None:
        for rule in self.rules:
            if rule not in CONSTRUCTOR_RULES:
                raise ConstructorError(f"unknown constructor rule {rule!r}")
        if not 1 <= self.max_depth <= MAX_SUPPORTED_DEPTH:
            raise ConstructorError("constructor depth is out of range")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": CONSTRUCTOR_SCHEMA,
            "rules": list(self.rules),
            "max_depth": self.max_depth,
            "provenance": list(self.provenance),
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "ExperimentConstructor":
        if set(data) != {
            "schema", "rules", "max_depth", "provenance", "version",
        } or data.get("schema") != CONSTRUCTOR_SCHEMA:
            raise ConstructorError("serialized constructor fields differ from the closed schema")
        rules = data["rules"]
        provenance = data["provenance"]
        if not isinstance(rules, Sequence) or isinstance(rules, (str, bytes)):
            raise ConstructorError("serialized constructor rules are malformed")
        if not isinstance(provenance, Sequence) or isinstance(provenance, (str, bytes)):
            raise ConstructorError("serialized constructor provenance is malformed")
        return cls(
            tuple(str(item) for item in rules), int(data["max_depth"]),  # type: ignore[arg-type]
            tuple(str(item) for item in provenance), int(data["version"]),  # type: ignore[arg-type]
        )

    def digest(self) -> str:
        return hashlib.sha256(_canonical(self.to_dict())).hexdigest()


def m0_constructor() -> ExperimentConstructor:
    """One action between a reset and an observation. Exactly M087's depth, made explicit.

    This is not a weakened mechanism invented for the occasion. M087's probes were single
    request/value pairs — one interaction each — and its policy could rank them but never compose
    them. Writing that as a constructor makes the assumption visible and, crucially, enumerable.
    """

    return ExperimentConstructor(
        rules=("PREFIX_RESET", "EMIT_SINGLE_ACTION", "SUFFIX_OBSERVE", "REQUIRE_OBSERVATION"),
        max_depth=1,
        provenance=(),
        version=0,
    )


def construct(
    constructor: ExperimentConstructor, actions: Sequence[str], observers: Sequence[str],
) -> tuple[ExperimentProgram, ...]:
    """Build every experiment this constructor can express over this vocabulary.

    Deterministic and total: the same constructor over the same vocabulary always yields the same
    programs in the same order. That is what makes `constructive_image` a proof rather than a
    sample.
    """

    if "REQUIRE_OBSERVATION" in constructor.rules and not observers:
        return ()
    observer = observers[0] if observers else None
    body_actions = [item for item in actions if item != "reset"]
    if not body_actions:
        return ()

    depths = range(1, constructor.max_depth + 1)
    if "EMIT_ACTION_SEQUENCE" not in constructor.rules:
        depths = range(1, 2)

    repetition = "ALLOW_REPETITION" in constructor.rules
    ordered = "PERMUTE_ORDER" in constructor.rules

    produced: list[ExperimentProgram] = []
    seen: set[tuple[str, ...]] = set()
    for depth in depths:
        if depth == 1:
            combinations: list[tuple[str, ...]] = [(item,) for item in body_actions]
        elif ordered and repetition:
            combinations = list(itertools.product(body_actions, repeat=depth))
        elif ordered:
            combinations = list(itertools.permutations(body_actions, depth))
        elif repetition:
            combinations = [
                tuple(sorted(item))
                for item in itertools.combinations_with_replacement(body_actions, depth)
            ]
        else:
            combinations = [tuple(sorted(item)) for item in itertools.combinations(
                body_actions, depth,
            )]
        for combination in combinations:
            steps: list[str] = []
            trace: list[str] = []
            if "PREFIX_RESET" in constructor.rules and "reset" in actions:
                steps.append("reset")
                trace.append("PREFIX_RESET")
            steps.extend(combination)
            trace.append(
                "EMIT_SINGLE_ACTION" if depth == 1 else f"EMIT_ACTION_SEQUENCE:{depth}"
            )
            if "SUFFIX_OBSERVE" in constructor.rules and observer is not None:
                steps.append(observer)
                trace.append("SUFFIX_OBSERVE")
            if "REQUIRE_OBSERVATION" in constructor.rules and (
                observer is None or observer not in steps
            ):
                continue
            key = tuple(steps)
            if "DEDUPLICATE" in constructor.rules:
                if key in seen:
                    continue
                seen.add(key)
            produced.append(ExperimentProgram(tuple(steps), tuple(trace), depth))
    return tuple(produced)


def constructive_image(
    constructor: ExperimentConstructor, actions: Sequence[str], observers: Sequence[str],
) -> frozenset[tuple[str, ...]]:
    """Every program this constructor can build, as a set of step sequences.

    The whole inexpressibility argument rests on this being complete rather than sampled. The
    spaces are small and finite by construction, so it is computed by exhaustion.
    """

    return frozenset(item.steps for item in construct(constructor, actions, observers))


def outside_image(
    program: Sequence[str], constructor: ExperimentConstructor,
    actions: Sequence[str], observers: Sequence[str],
) -> bool:
    """Whether a program lies outside a constructor's complete constructive image."""

    return tuple(program) not in constructive_image(constructor, actions, observers)


# --------------------------------------------------------------------------------------------
# meta-primitives over the constructor
# --------------------------------------------------------------------------------------------

META_PRIMITIVES = (
    "add_sequence_constructor",
    "increase_composition_depth",
    "add_order_sensitivity",
    "allow_action_repetition",
    "add_candidate_deduplication",
    "add_experiment_validity_rule",
    "add_reset_prefix_rule",
)


def apply_meta_primitive(
    constructor: ExperimentConstructor, primitive: str, argument: int | None = None,
) -> ExperimentConstructor:
    """Apply one bounded rewrite. None of these builds an experiment or names a world."""

    if primitive not in META_PRIMITIVES:
        raise ConstructorError(f"unknown meta-primitive {primitive!r}")
    rules = list(constructor.rules)
    depth = constructor.max_depth

    def _add(rule: str) -> None:
        if rule not in rules:
            rules.append(rule)

    if primitive == "add_sequence_constructor":
        _add("EMIT_ACTION_SEQUENCE")
        depth = max(depth, 2)
    elif primitive == "increase_composition_depth":
        depth = min(MAX_SUPPORTED_DEPTH, depth + int(argument or 1))
    elif primitive == "add_order_sensitivity":
        _add("PERMUTE_ORDER")
    elif primitive == "allow_action_repetition":
        _add("ALLOW_REPETITION")
    elif primitive == "add_candidate_deduplication":
        _add("DEDUPLICATE")
    elif primitive == "add_experiment_validity_rule":
        _add("REQUIRE_OBSERVATION")
    elif primitive == "add_reset_prefix_rule":
        _add("PREFIX_RESET")

    return ExperimentConstructor(
        rules=tuple(rules), max_depth=depth,
        provenance=constructor.provenance + (
            primitive if argument is None else f"{primitive}:{argument}",
        ),
        version=constructor.version + 1,
    )


def build_constructor(
    base: ExperimentConstructor, steps: Sequence[tuple[str, int | None]],
) -> ExperimentConstructor:
    constructor = base
    for primitive, argument in steps:
        constructor = apply_meta_primitive(constructor, primitive, argument)
    return constructor


def candidate_meta_transformations() -> tuple[tuple[tuple[str, int | None], ...], ...]:
    """The bounded meta-search space, shortest first. It ranks nothing.

    Several entries are plausible and useless. Deduplication alone changes no reachable program.
    Repetition without sequencing still emits one action. Order sensitivity without sequencing has
    nothing to order. Only compositions that actually extend the reachable set can help, and the
    search finds out by validating descendants.
    """

    singles: list[tuple[tuple[str, int | None], ...]] = [
        ((primitive, None),) for primitive in sorted(META_PRIMITIVES)
    ]
    pairs: list[tuple[tuple[str, int | None], ...]] = [
        (("add_candidate_deduplication", None), ("allow_action_repetition", None)),
        (("add_experiment_validity_rule", None), ("add_reset_prefix_rule", None)),
        (("add_sequence_constructor", None), ("add_candidate_deduplication", None)),
        (("add_sequence_constructor", None), ("add_order_sensitivity", None)),
    ]
    triples: list[tuple[tuple[str, int | None], ...]] = [
        (
            ("add_sequence_constructor", None), ("add_order_sensitivity", None),
            ("add_candidate_deduplication", None),
        ),
        (
            ("add_sequence_constructor", None), ("add_order_sensitivity", None),
            ("allow_action_repetition", None),
        ),
        (
            ("add_sequence_constructor", None), ("add_order_sensitivity", None),
            ("increase_composition_depth", 1),
        ),
    ]
    return tuple(singles + pairs + triples)


__all__ = [
    "CONSTRUCTOR_RULES", "CONSTRUCTOR_SCHEMA", "ConstructorError", "ExperimentConstructor",
    "ExperimentProgram", "MAX_SUPPORTED_DEPTH", "META_PRIMITIVES", "apply_meta_primitive",
    "build_constructor", "candidate_meta_transformations", "construct", "constructive_image",
    "m0_constructor", "outside_image",
]
