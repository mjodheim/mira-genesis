"""The selection/acquisition policy as a serialized program, and the language that rewrites it.

D054 named the part of M086 that was never mutable: "the greedy first-past-the-post over public
score that picks the adopted candidate is frozen and human-authored". `m086_meta_lineage.run_cycle`
implements it in four lines — `if best is None or passed > best[0]` over enumeration order — and
because the comparison is strict, a tie silently keeps whichever candidate the generator emitted
first. `TOOL_EXPRESSIONS` begins with `midpoint`, so M086-C adopted `midpoint`.

That is the object M087 makes mutable. It is stored as an ordered instruction program executed by
a fixed interpreter, not as a configuration flag: `{"use_active_learning": true}` would move a
human decision into a JSON file rather than into the lineage.

M0 is exactly M086's rule, `[SCORE_PUBLIC, ARGMAX_FIRST]`, and a differential regression drives it
against the real `run_cycle` selection to prove it is the rule the repository actually froze rather
than a strawman written for the occasion.

The interpreter is the ceiling and is named honestly: the instruction set and the meta-primitives
are authored. What is not authored is which program resolves a limitation, whether one exists, or
that the lineage will find it — several compositions are viable, several are plausible and wrong,
and the search finds out by running them.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Callable, Mapping, Sequence

from metamorphosis.m087_evidence import (
    AcquisitionLog,
    EvidenceError,
    Observation,
)


POLICY_SCHEMA = "m087-selection-acquisition-policy-v1"

# The complete instruction set. Every one is a general operation over candidates, predictions and
# experiments; none names a family, a probe, a candidate or a truth.
INSTRUCTIONS = (
    "SCORE_PUBLIC",          # count public cases each candidate passes
    "KEEP_TOP_SCORING",      # retain every candidate at the maximum score
    "ARGMAX_FIRST",          # collapse to the first candidate in emission order
    "PROJECT_PREDICTIONS",   # compute each survivor's prediction over the experiment space
    "PARTITION_SURVIVORS",   # group survivors by identical prediction vectors
    "GUARD_AMBIGUOUS",       # stop the program when more than one class survives
    "ENUMERATE_EXPERIMENTS", # list the experiments still available
    "SCORE_EXPERIMENTS",     # rank experiments by the policy's scoring rule
    "ACQUIRE_BEST",          # observe the top-ranked experiment on the reference source
    "FILTER_BY_ACQUIRED",    # drop candidates whose prediction contradicts an observation
    "LOOP_ACQUISITION",      # repeat enumerate/score/acquire/filter within budget
    "ADOPT_UNIQUE",          # adopt iff exactly one candidate survives
    "DEFER_INSUFFICIENT",    # emit INSUFFICIENT_EVIDENCE rather than choose arbitrarily
)

# Experiment scoring rules. Three are sound, two are decoys that a plausible meta-transformation
# might install and that do not resolve ambiguity. The search must find out which is which by
# validating descendants, not by being told.
SCORING_RULES = (
    "partition_size",          # maximise the number of prediction classes the experiment splits
    "expected_information_gain",  # maximise entropy of the induced partition
    "disagreement_count",      # maximise the number of disagreeing candidate pairs
    "first_index",             # decoy: take the first experiment in space order
    "constant",                # decoy: score every experiment equally, so order decides
)

SOUND_SCORING_RULES = ("partition_size", "expected_information_gain", "disagreement_count")

TERMINAL_STATES = ("adopted", "deferred_insufficient_evidence", "no_candidate")


class PolicyError(RuntimeError):
    """Raised when a policy program or meta-transformation violates the interpreter's contract."""


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


@dataclass(frozen=True)
class Instruction:
    opcode: str
    argument: str | int | None = None

    def __post_init__(self) -> None:
        if self.opcode not in INSTRUCTIONS:
            raise PolicyError(f"unknown instruction {self.opcode!r}")
        if self.opcode == "SCORE_EXPERIMENTS" and self.argument not in SCORING_RULES:
            raise PolicyError(f"unknown experiment scoring rule {self.argument!r}")
        if self.opcode == "LOOP_ACQUISITION" and not (
            isinstance(self.argument, int) and not isinstance(self.argument, bool)
            and self.argument >= 1
        ):
            raise PolicyError("an acquisition loop needs a positive bound")

    def to_dict(self) -> dict[str, object]:
        return {"opcode": self.opcode, "argument": self.argument}


@dataclass(frozen=True)
class SelectionPolicy:
    """The mutable artifact: an ordered program plus its provenance."""

    program: tuple[Instruction, ...]
    acquisition_budget: int = 0
    provenance: tuple[str, ...] = ()
    version: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": POLICY_SCHEMA,
            "program": [instruction.to_dict() for instruction in self.program],
            "acquisition_budget": self.acquisition_budget,
            "provenance": list(self.provenance),
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "SelectionPolicy":
        if set(data) != {
            "schema", "program", "acquisition_budget", "provenance", "version",
        } or data.get("schema") != POLICY_SCHEMA:
            raise PolicyError("serialized selection policy fields differ from the closed schema")
        raw = data["program"]
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
            raise PolicyError("serialized policy program is malformed")
        program = []
        for item in raw:
            if not isinstance(item, Mapping) or set(item) != {"opcode", "argument"}:
                raise PolicyError("serialized instruction fields differ from the closed schema")
            program.append(Instruction(str(item["opcode"]), item["argument"]))  # type: ignore[arg-type]
        provenance = data["provenance"]
        if not isinstance(provenance, Sequence) or isinstance(provenance, (str, bytes)):
            raise PolicyError("serialized policy provenance is malformed")
        return cls(
            tuple(program), int(data["acquisition_budget"]),  # type: ignore[arg-type]
            tuple(str(item) for item in provenance), int(data["version"]),  # type: ignore[arg-type]
        )

    def digest(self) -> str:
        return hashlib.sha256(_canonical(self.to_dict())).hexdigest()

    @property
    def opcodes(self) -> tuple[str, ...]:
        return tuple(instruction.opcode for instruction in self.program)

    @property
    def can_acquire(self) -> bool:
        """Whether this policy possesses an informational action at all."""

        return "ACQUIRE_BEST" in self.opcodes and self.acquisition_budget > 0


def m0_policy() -> SelectionPolicy:
    """M086's frozen selection rule, expressed as a program.

    `run_cycle` computes each candidate's passed-case count and keeps the first maximum. That is
    `SCORE_PUBLIC` then `ARGMAX_FIRST` and nothing else. It has no representation for two
    candidates being indistinguishable and no action that could obtain more evidence.
    """

    return SelectionPolicy(
        program=(Instruction("SCORE_PUBLIC"), Instruction("ARGMAX_FIRST")),
        acquisition_budget=0,
        provenance=(),
        version=0,
    )


# --------------------------------------------------------------------------------------------
# the fixed interpreter
# --------------------------------------------------------------------------------------------


@dataclass
class SelectionOutcome:
    terminal_state: str
    selected: str | None
    survivors: tuple[str, ...]
    classes: tuple[tuple[str, ...], ...]
    acquisitions: int
    ambiguity_detected: bool
    experiments_scored: int
    trace: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "terminal_state": self.terminal_state,
            "selected": self.selected,
            "survivors": list(self.survivors),
            "classes": [list(item) for item in self.classes],
            "acquisitions": self.acquisitions,
            "ambiguity_detected": self.ambiguity_detected,
            "experiments_scored": self.experiments_scored,
            "trace": list(self.trace),
        }


def _partition(
    survivors: Sequence[str], predictions: Mapping[str, Mapping[str, str]],
    requests: Sequence[str],
) -> tuple[tuple[str, ...], ...]:
    buckets: dict[tuple[str, ...], list[str]] = {}
    for label in survivors:
        key = tuple(predictions[label].get(request, "") for request in requests)
        buckets.setdefault(key, []).append(label)
    return tuple(tuple(group) for _, group in sorted(buckets.items()))


def _score_experiment(
    rule: str, survivors: Sequence[str], predictions: Mapping[str, Mapping[str, str]],
    request: str,
) -> float:
    keys = [predictions[label].get(request, "") for label in survivors]
    classes: dict[str, int] = {}
    for key in keys:
        classes[key] = classes.get(key, 0) + 1
    if rule == "partition_size":
        return float(len(classes))
    if rule == "disagreement_count":
        total = len(keys)
        same = sum(count * (count - 1) // 2 for count in classes.values())
        return float(total * (total - 1) // 2 - same)
    if rule == "expected_information_gain":
        total = len(keys)
        if total == 0:
            return 0.0
        entropy = 0.0
        for count in classes.values():
            share = count / total
            entropy -= share * (share and _log2(share))
        return entropy
    if rule == "first_index":
        return 0.0
    if rule == "constant":
        return 1.0
    raise PolicyError(f"unknown experiment scoring rule {rule!r}")


def _log2(value: float) -> float:
    from math import log2

    return log2(value)


def execute_policy(
    policy: SelectionPolicy,
    *,
    candidates: Sequence[str],
    public_scores: Mapping[str, int],
    incumbent_score: int,
    experiment_space: Sequence[str],
    predict: Callable[[str, str], Observation],
    acquire: Callable[[str], Observation],
    log: AcquisitionLog | None = None,
) -> SelectionOutcome:
    """Run a policy program. The interpreter is fixed; the program is the lineage's artifact.

    `predict` and `acquire` are supplied by the runtime and are different objects: `predict` runs a
    candidate the lineage built, `acquire` runs the authorized reference source. A policy has no
    way to reach the evaluator, because no evaluator function is passed in.
    """

    trace: list[str] = []
    survivors = list(candidates)
    predictions: dict[str, dict[str, str]] = {}
    projected: list[str] = []
    classes: tuple[tuple[str, ...], ...] = tuple((label,) for label in survivors)
    ambiguity = False
    acquisitions = 0
    experiments_scored = 0
    ranked: list[str] = []
    consumed: set[str] = set()

    if not survivors:
        return SelectionOutcome("no_candidate", None, (), (), 0, False, 0, ("no candidates",))

    index = 0
    while index < len(policy.program):
        instruction = policy.program[index]
        opcode = instruction.opcode
        index += 1

        if opcode == "SCORE_PUBLIC":
            trace.append("scored public cases")
            continue

        if opcode == "KEEP_TOP_SCORING":
            best = max(public_scores.get(label, -1) for label in survivors)
            survivors = [label for label in survivors if public_scores.get(label, -1) == best]
            classes = tuple((label,) for label in survivors)
            trace.append(f"kept {len(survivors)} candidates at public score {best}")
            continue

        if opcode == "ARGMAX_FIRST":
            best_label: str | None = None
            best_score = incumbent_score
            for label in survivors:
                score = public_scores.get(label, -1)
                if best_label is None and score > best_score:
                    best_label, best_score = label, score
                elif best_label is not None and score > best_score:
                    best_label, best_score = label, score
            if best_label is None:
                return SelectionOutcome(
                    "no_candidate", None, tuple(survivors), classes, acquisitions,
                    ambiguity, experiments_scored, tuple(trace + ["no candidate improved"]),
                )
            trace.append(f"argmax kept the first maximum {best_label!r}")
            return SelectionOutcome(
                "adopted", best_label, tuple(survivors), classes, acquisitions,
                ambiguity, experiments_scored, tuple(trace),
            )

        if opcode == "PROJECT_PREDICTIONS":
            projected = [
                request for request in experiment_space if request not in consumed
            ]
            for label in survivors:
                predictions.setdefault(label, {})
                for request in projected:
                    if request not in predictions[label]:
                        predictions[label][request] = predict(label, request).key()
            trace.append(f"projected {len(survivors)} candidates over {len(projected)} experiments")
            continue

        if opcode == "PARTITION_SURVIVORS":
            if not predictions:
                trace.append("partition without projections leaves one class")
                classes = (tuple(survivors),)
            else:
                classes = _partition(survivors, predictions, projected)
            trace.append(f"partitioned into {len(classes)} prediction classes")
            continue

        if opcode == "GUARD_AMBIGUOUS":
            ambiguity = len(survivors) > 1
            trace.append(
                f"ambiguity {'detected' if ambiguity else 'absent'} over {len(survivors)} survivors"
            )
            if not ambiguity:
                continue
            continue

        if opcode == "ENUMERATE_EXPERIMENTS":
            ranked = [request for request in experiment_space if request not in consumed]
            trace.append(f"enumerated {len(ranked)} available experiments")
            continue

        if opcode == "SCORE_EXPERIMENTS":
            rule = str(instruction.argument)
            if not ranked:
                trace.append("no experiment to score")
                continue
            scored = sorted(
                ranked,
                key=lambda request: (
                    -_score_experiment(rule, survivors, predictions, request),
                    experiment_space.index(request),
                ),
            )
            ranked = scored
            experiments_scored += len(scored)
            trace.append(f"scored {len(scored)} experiments by {rule}")
            continue

        if opcode == "ACQUIRE_BEST":
            if not ranked:
                trace.append("acquisition skipped: no ranked experiment")
                continue
            if acquisitions >= policy.acquisition_budget:
                trace.append("acquisition skipped: budget exhausted")
                continue
            request = ranked[0]
            try:
                observation = acquire(request)
            except EvidenceError as exc:
                trace.append(f"acquisition refused: {exc}")
                continue
            if log is not None:
                log.record(observation)
            predictions.setdefault("__observed__", {})[request] = observation.key()
            consumed.add(request)
            ranked = ranked[1:]
            acquisitions += 1
            trace.append(f"acquired {request!r} -> {observation.key()}")
            continue

        if opcode == "FILTER_BY_ACQUIRED":
            observed = predictions.get("__observed__", {})
            if not observed:
                trace.append("filter skipped: nothing acquired")
                continue
            kept = []
            for label in survivors:
                agrees = True
                for request, key in observed.items():
                    predicted = predictions.get(label, {}).get(request)
                    if predicted is None:
                        predicted = predict(label, request).key()
                        predictions.setdefault(label, {})[request] = predicted
                    if predicted != key:
                        agrees = False
                        break
                if agrees:
                    kept.append(label)
            trace.append(f"acquired evidence eliminated {len(survivors) - len(kept)} candidates")
            survivors = kept or survivors[:0]
            classes = tuple((label,) for label in survivors)
            continue

        if opcode == "LOOP_ACQUISITION":
            bound = int(instruction.argument or 1)
            if len(survivors) > 1 and acquisitions < min(bound, policy.acquisition_budget):
                # Re-enter the acquisition block. The block is the contiguous run of instructions
                # from the first ENUMERATE_EXPERIMENTS preceding this loop.
                target = _loop_target(policy, index - 1)
                if target is not None:
                    trace.append("looping acquisition")
                    index = target
                    continue
            trace.append("acquisition loop finished")
            continue

        if opcode == "ADOPT_UNIQUE":
            improving = [
                label for label in survivors if public_scores.get(label, -1) > incumbent_score
            ]
            if len(improving) == 1:
                trace.append(f"adopted the unique surviving candidate {improving[0]!r}")
                return SelectionOutcome(
                    "adopted", improving[0], tuple(survivors), classes, acquisitions,
                    ambiguity, experiments_scored, tuple(trace),
                )
            if not improving:
                return SelectionOutcome(
                    "no_candidate", None, tuple(survivors), classes, acquisitions,
                    ambiguity, experiments_scored, tuple(trace + ["no candidate improved"]),
                )
            trace.append(f"{len(improving)} candidates remain indistinguishable")
            continue

        if opcode == "DEFER_INSUFFICIENT":
            trace.append("deferred: evidence does not justify a choice")
            return SelectionOutcome(
                "deferred_insufficient_evidence", None, tuple(survivors), classes,
                acquisitions, True, experiments_scored, tuple(trace),
            )

    trace.append("program ended without a terminal instruction")
    return SelectionOutcome(
        "deferred_insufficient_evidence", None, tuple(survivors), classes, acquisitions,
        ambiguity, experiments_scored, tuple(trace),
    )


def _loop_target(policy: SelectionPolicy, loop_index: int) -> int | None:
    for position in range(loop_index - 1, -1, -1):
        if policy.program[position].opcode == "ENUMERATE_EXPERIMENTS":
            return position
    return None


# --------------------------------------------------------------------------------------------
# meta-primitives: bounded operations over a policy program
# --------------------------------------------------------------------------------------------

META_PRIMITIVES = (
    "add_prediction_projection",
    "add_equivalence_partition",
    "add_ambiguity_guard",
    "add_experiment_enumerator",
    "add_scoring_rule",
    "add_acquisition_transition",
    "add_survivor_filter",
    "add_defer_condition",
    "set_acquisition_budget",
)


def apply_meta_primitive(
    policy: SelectionPolicy, primitive: str, argument: str | int | None = None,
) -> SelectionPolicy:
    """Apply one bounded rewrite. None of these installs a working acquisition loop on its own."""

    if primitive not in META_PRIMITIVES:
        raise PolicyError(f"unknown meta-primitive {primitive!r}")
    program = list(policy.program)
    budget = policy.acquisition_budget

    def _insert_before_terminal(instruction: Instruction) -> None:
        terminal = {"ARGMAX_FIRST", "ADOPT_UNIQUE", "DEFER_INSUFFICIENT"}
        for position, existing in enumerate(program):
            if existing.opcode in terminal:
                program.insert(position, instruction)
                return
        program.append(instruction)

    if primitive == "add_prediction_projection":
        _insert_before_terminal(Instruction("PROJECT_PREDICTIONS"))
    elif primitive == "add_equivalence_partition":
        _insert_before_terminal(Instruction("PARTITION_SURVIVORS"))
    elif primitive == "add_ambiguity_guard":
        # Keeping every top-scoring candidate is what makes a tie visible at all: M086 collapsed
        # to one candidate before anything could notice there had been a choice.
        program = [Instruction("SCORE_PUBLIC"), Instruction("KEEP_TOP_SCORING")] + [
            item for item in program if item.opcode not in {"SCORE_PUBLIC", "KEEP_TOP_SCORING"}
        ]
        program = [
            Instruction("ADOPT_UNIQUE") if item.opcode == "ARGMAX_FIRST" else item
            for item in program
        ]
        _insert_before_terminal(Instruction("GUARD_AMBIGUOUS"))
    elif primitive == "add_experiment_enumerator":
        _insert_before_terminal(Instruction("ENUMERATE_EXPERIMENTS"))
    elif primitive == "add_scoring_rule":
        rule = str(argument or "partition_size")
        _insert_before_terminal(Instruction("SCORE_EXPERIMENTS", rule))
    elif primitive == "add_acquisition_transition":
        _insert_before_terminal(Instruction("ACQUIRE_BEST"))
        if budget == 0:
            budget = 1
    elif primitive == "add_survivor_filter":
        _insert_before_terminal(Instruction("FILTER_BY_ACQUIRED"))
        _insert_before_terminal(Instruction("LOOP_ACQUISITION", 4))
    elif primitive == "add_defer_condition":
        if not any(item.opcode == "DEFER_INSUFFICIENT" for item in program):
            program.append(Instruction("DEFER_INSUFFICIENT"))
    elif primitive == "set_acquisition_budget":
        budget = int(argument or 1)

    return SelectionPolicy(
        program=tuple(program),
        acquisition_budget=budget,
        provenance=policy.provenance + (
            primitive if argument is None else f"{primitive}:{argument}",
        ),
        version=policy.version + 1,
    )


def build_policy(
    base: SelectionPolicy, steps: Sequence[tuple[str, str | int | None]],
) -> SelectionPolicy:
    policy = base
    for primitive, argument in steps:
        policy = apply_meta_primitive(policy, primitive, argument)
    return policy


def candidate_meta_transformations() -> tuple[tuple[tuple[str, str | int | None], ...], ...]:
    """The bounded meta-search space, in a deterministic order that ranks nothing.

    Ordered shortest first, then lexicographically. Nothing here knows which composition works.
    Several are plausible and fail: a guard alone defers forever, an enumerator without an
    acquisition transition cannot observe anything, and two of the five scoring rules pick an
    experiment that does not discriminate.
    """

    partial: list[tuple[tuple[str, str | int | None], ...]] = [
        (("add_ambiguity_guard", None),),
        (("add_defer_condition", None),),
        (("add_prediction_projection", None),),
        (("add_ambiguity_guard", None), ("add_defer_condition", None)),
        (
            ("add_ambiguity_guard", None), ("add_experiment_enumerator", None),
            ("add_acquisition_transition", None),
        ),
        (
            ("add_ambiguity_guard", None), ("add_prediction_projection", None),
            ("add_equivalence_partition", None),
        ),
    ]
    complete: list[tuple[tuple[str, str | int | None], ...]] = []
    for rule in SCORING_RULES:
        complete.append((
            ("add_ambiguity_guard", None),
            ("add_prediction_projection", None),
            ("add_equivalence_partition", None),
            ("add_experiment_enumerator", None),
            ("add_scoring_rule", rule),
            ("add_acquisition_transition", None),
            ("add_survivor_filter", None),
            ("set_acquisition_budget", 4),
            ("add_defer_condition", None),
        ))
    return tuple(partial + complete)


__all__ = [
    "INSTRUCTIONS", "META_PRIMITIVES", "POLICY_SCHEMA", "SCORING_RULES",
    "SOUND_SCORING_RULES", "TERMINAL_STATES", "Instruction", "PolicyError",
    "SelectionOutcome", "SelectionPolicy", "apply_meta_primitive", "build_policy",
    "candidate_meta_transformations", "execute_policy", "m0_policy",
]
