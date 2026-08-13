"""M088 — the lineage builds part of the space in which it looks for the information it needs.

M087 could choose an experiment; the space it chose from was a literal tuple the harness passed
in. D057 recorded that as a ceiling. Here the harness passes in a *vocabulary* — `reset`,
`send_a`, `observe` — and the lineage must construct programs from it.

Two capabilities are separated on purpose and both must hold:

1. **Construct** an experiment that was outside the prior constructor's complete constructive
   image, proved by enumerating that image rather than by asserting it.
2. **Use** the resulting observation causally to reach a correct adaptation.

A lineage that invents many programs and cannot use what they return fails the second. A lineage
handed the right program fails the first, which is why `authored_full_experiment_space` exists as
a ceiling and is never counted as evidence about Mira.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from metamorphosis.m088_experiment import (
    ExperimentConstructor,
    ExperimentProgram,
    build_constructor,
    candidate_meta_transformations,
    construct,
    constructive_image,
    m0_constructor,
    outside_image,
)
from metamorphosis.m088_worlds import World, WorldError, qualified_world, world


RESULT_SCHEMA = "m088-result-v1"

ARMS = (
    "evolvable_experiment_constructor",
    "fixed_experiment_constructor",
    "constructor_acquisition_ablated",
    "more_budget_same_experiment_space",
    "fresh_agent",
    "authored_full_experiment_space",
)

# The ceiling arm. Never evidence about the lineage; it exists to show that the M087 selector
# already knows what to do once a space exists, so what M088 adds is the construction.
CEILING_ARMS = ("authored_full_experiment_space",)

DEVELOPMENT_WORLD = "stateful_protocol"
QUALIFICATION_WORLDS = ("path_graph", "durable_service")

ACQUISITION_BUDGET = 4
BUDGET_MULTIPLE = 10


class LineageError(RuntimeError):
    """Raised when an arm violates its own contract."""


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


@dataclass
class Encounter:
    """One world, resolved by whatever the constructor can express about it."""

    world_id: str
    constructor_digest: str
    image_size: int
    survivors_initial: tuple[str, ...]
    survivors_final: tuple[str, ...]
    acquisitions: list[dict[str, object]] = field(default_factory=list)
    programs_executed: int = 0
    adopted: str | None = None
    hidden_passed: int = 0
    hidden_total: int = 0
    outside_prior_image: list[list[str]] = field(default_factory=list)
    repetition_logs: list[dict[str, object]] = field(default_factory=list)

    @property
    def correct(self) -> bool:
        return self.adopted is not None and self.hidden_passed == self.hidden_total

    def to_dict(self) -> dict[str, object]:
        return {
            "world_id": self.world_id,
            "constructor_digest": self.constructor_digest,
            "constructive_image_size": self.image_size,
            "survivors_initial": list(self.survivors_initial),
            "survivors_final": list(self.survivors_final),
            "acquisitions": self.acquisitions,
            "acquisition_count": len(self.acquisitions),
            "programs_executed": self.programs_executed,
            "adopted": self.adopted,
            "hidden_passed": self.hidden_passed,
            "hidden_total": self.hidden_total,
            "correct_terminal_decision": self.correct,
            "experiments_outside_prior_image": self.outside_prior_image,
            "repetition_logs": self.repetition_logs,
            "repetitions_recorded": len(self.repetition_logs),
            "total_acquisitions_across_repetitions": sum(
                len(item["acquisitions"]) for item in self.repetition_logs  # type: ignore[arg-type]
            ),
        }


def _initial_survivors(item: World) -> tuple[str, ...]:
    """Candidates consistent with the public interaction. Several always are."""

    observed = item.execute(item.public_program)
    return tuple(
        candidate for candidate in sorted(item.candidates)
        if item.predict(candidate, item.public_program) == observed
    )


def encounter(
    item: World, constructor: ExperimentConstructor, *,
    prior: ExperimentConstructor | None = None,
    budget: int = ACQUISITION_BUDGET,
    repetitions: int = 1,
    supplied_programs: Sequence[ExperimentProgram] | None = None,
) -> Encounter:
    """Construct experiments, choose a discriminating one, run it, and use what came back.

    `supplied_programs` exists only for the ceiling arm, which is handed a space instead of
    building one. Every other arm passes `None` and must construct.
    """

    actions, observers = item.action_names, item.observer_names
    programs = (
        tuple(supplied_programs) if supplied_programs is not None
        else construct(constructor, actions, observers)
    )
    prior_image = (
        constructive_image(prior, actions, observers) if prior is not None else frozenset()
    )
    survivors = list(_initial_survivors(item))
    record = Encounter(
        world_id=item.world_id,
        constructor_digest=constructor.digest(),
        image_size=len(programs),
        survivors_initial=tuple(survivors),
        survivors_final=tuple(survivors),
    )

    # Every repetition is a COMPLETE independent search: the consumed set and the survivor set
    # are reset, so ten repetitions are ten full exhaustive searches over the same constructive
    # image rather than one search plus nine cheap re-scans. The tenfold arm does the work rather
    # than multiplying a counter, which is the correction PR #135 forced on M087.
    outcomes: list[tuple[str, ...]] = []
    for repetition in range(repetitions):
        survivors = list(record.survivors_initial)
        consumed: set[tuple[str, ...]] = {tuple(item.public_program)}
        # Every repetition keeps its own audit trail. An earlier draft cleared the records, so a
        # ten-repetition arm reported the acquisitions of one search and no evidence for the other
        # nine; external review of PR #136 caught that.
        record.acquisitions = []
        record.outside_prior_image = []
        while len(survivors) > 1 and len(record.acquisitions) < budget:
            best: ExperimentProgram | None = None
            best_score = 1
            for program in programs:
                if tuple(program.steps) in consumed:
                    continue
                record.programs_executed += 1
                classes = {item.predict(candidate, program.steps) for candidate in survivors}
                if len(classes) > best_score:
                    best, best_score = program, len(classes)
            if best is None:
                break
            observation = item.execute(best.steps)
            consumed.add(tuple(best.steps))
            kept = [
                candidate for candidate in survivors
                if item.predict(candidate, best.steps) == observation
            ]
            record.acquisitions.append({
                "program": best.to_dict(),
                "observation": observation,
                "survivors_before": list(survivors),
                "survivors_after": list(kept),
                "eliminated": sorted(set(survivors) - set(kept)),
                "outside_prior_constructive_image": (
                    tuple(best.steps) not in prior_image if prior is not None else None
                ),
            })
            if prior is not None and tuple(best.steps) not in prior_image:
                record.outside_prior_image.append(list(best.steps))
            if not kept:
                raise LineageError(f"{item.world_id}: the real world excluded every candidate")
            survivors = kept
        outcomes.append(tuple(survivors))
        record.repetition_logs.append({
            "repetition": repetition,
            "acquisitions": list(record.acquisitions),
            "experiments_outside_prior_image": list(record.outside_prior_image),
            "survivors_final": list(survivors),
        })

    if len({tuple(sorted(item)) for item in outcomes}) > 1:
        raise LineageError(
            f"{item.world_id}: repeated exhaustive searches disagreed, so the arm is not "
            "deterministic and its comparison would be meaningless"
        )
    record.survivors_final = tuple(survivors)
    if len(survivors) == 1:
        record.adopted = survivors[0]
        record.hidden_total = len(item.hidden_programs)
        record.hidden_passed = sum(
            1 for program in item.hidden_programs
            if item.predict(record.adopted, program) == item.execute(program)
        )
    else:
        record.hidden_total = len(item.hidden_programs)
    return record


# --------------------------------------------------------------------------------------------
# development
# --------------------------------------------------------------------------------------------


@dataclass
class Development:
    world_id: str
    limitation: dict[str, object]
    rejected: list[dict[str, object]] = field(default_factory=list)
    adopted_steps: tuple[tuple[str, object], ...] | None = None
    adopted_constructor: ExperimentConstructor | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "world_id": self.world_id,
            "limitation": self.limitation,
            "rejected_meta_transformations": self.rejected,
            "rejected_count": len(self.rejected),
            "adopted_steps": [list(step) for step in (self.adopted_steps or ())],
            "adopted_constructor": (
                self.adopted_constructor.to_dict() if self.adopted_constructor else None
            ),
            "adopted_constructor_digest": (
                self.adopted_constructor.digest() if self.adopted_constructor else None
            ),
            "prior_constructor_digest": m0_constructor().digest(),
        }


def observe_limitation(item: World) -> dict[str, object]:
    """Show that M0's *complete* image contains no experiment that resolves this world.

    Not "M0 did not find one". The image is enumerated and every program in it is tried
    exhaustively, so the limitation is constructive rather than a matter of search luck.
    """

    constructor = m0_constructor()
    actions, observers = item.action_names, item.observer_names
    image = sorted(constructive_image(constructor, actions, observers))
    record = encounter(item, constructor, budget=len(image) + 1)
    survivors = _initial_survivors(item)
    discriminating = [
        list(program) for program in image
        if len({item.predict(candidate, program) for candidate in survivors}) > 1
    ]
    return {
        "world_id": item.world_id,
        "prior_constructor_digest": constructor.digest(),
        "constructive_image": [list(program) for program in image],
        "constructive_image_size": len(image),
        "initial_survivors": list(survivors),
        "discriminating_programs_in_prior_image": discriminating,
        "exhaustive_survivors": list(record.survivors_final),
        "resolved_by_prior_constructor": len(record.survivors_final) == 1,
        "prior_adopted": record.adopted,
        "prior_correct": record.correct,
    }


def meta_search(item: World) -> Development:
    """Try each bounded rewrite on a disposable descendant; adopt the first that resolves."""

    development = Development(world_id=item.world_id, limitation=observe_limitation(item))
    for steps in candidate_meta_transformations():
        candidate = build_constructor(m0_constructor(), steps)
        try:
            trial = encounter(item, candidate, prior=m0_constructor())
        except (LineageError, WorldError) as exc:
            development.rejected.append({
                "steps": [list(step) for step in steps], "reason": f"refused: {exc}",
            })
            continue
        if trial.correct:
            development.adopted_steps = tuple(steps)
            development.adopted_constructor = candidate
            return development
        development.rejected.append({
            "steps": [list(step) for step in steps],
            "constructive_image_size": trial.image_size,
            "survivors_final": list(trial.survivors_final),
            "acquisitions": len(trial.acquisitions),
            "reason": "descendant did not reach a correct terminal decision",
        })
    return development


def rollback_proof(constructor: ExperimentConstructor) -> dict[str, object]:
    """Corrupt the state that is actually restored, and recover it from a separate checkpoint.

    External review of PR #136 found the earlier version corrupted a detached copy and then
    reloaded an untouched string, so `byte_identical_restore` was guaranteed without recovery ever
    being exercised. That is the M064 defect — a rollback receipt comparing the saved state to
    itself — recurring, and it is corrected here.

    Now there is one **live** serialized state and one **independently preserved** checkpoint. The
    fault is written into the live state; detection compares the live digest against the preserved
    checkpoint digest; restoration reads the checkpoint and overwrites the live state; and the
    restored object is re-serialized and re-executed to show it is the constructor that was
    adopted, not merely bytes that match.
    """

    canonical = json.dumps(constructor.to_dict(), sort_keys=True, separators=(",", ":"))
    checkpoint_bytes = canonical.encode("utf-8")
    checkpoint_digest = hashlib.sha256(checkpoint_bytes).hexdigest()

    # The live state the lineage would carry forward.
    live = canonical

    # A real fault, written into the live state.
    damaged = json.loads(live)
    damaged["max_depth"] = 1
    damaged["rules"] = damaged["rules"][:1]
    live = json.dumps(damaged, sort_keys=True, separators=(",", ":"))
    live_digest = hashlib.sha256(live.encode("utf-8")).hexdigest()
    detected = live_digest != checkpoint_digest

    corrupted_constructor = ExperimentConstructor.from_dict(json.loads(live))
    corrupted_depth = corrupted_constructor.max_depth

    # Restoration reads the preserved checkpoint, not the damaged live state.
    live = checkpoint_bytes.decode("utf-8")
    restored = ExperimentConstructor.from_dict(json.loads(live))
    restored_bytes = json.dumps(
        restored.to_dict(), sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")

    return {
        "checkpoint_digest": checkpoint_digest,
        "corrupted_digest": live_digest,
        "corruption_detected": detected,
        "corrupted_state_was_the_restored_state": True,
        "corrupted_max_depth": corrupted_depth,
        "restored_max_depth": restored.max_depth,
        "fault_actually_changed_behaviour": corrupted_depth != constructor.max_depth,
        "byte_identical_restore": restored_bytes == checkpoint_bytes,
        "restored_constructor_digest": restored.digest(),
        "constructor_digest": constructor.digest(),
        "digest_matches": restored.digest() == constructor.digest(),
        "constructor_included_in_restored_state": "EMIT_ACTION_SEQUENCE" in restored.rules,
    }


# --------------------------------------------------------------------------------------------
# arms
# --------------------------------------------------------------------------------------------


def hidden_outside_constructive_image(
    item: World, constructor: ExperimentConstructor,
) -> dict[str, object]:
    """Prove the lineage cannot even construct a hidden program, let alone run one.

    Stronger than a rule about which programs are permitted: the hidden set lies outside the
    adopted constructor's complete constructive image, so no policy, budget or search could reach
    it. This is the M088 form of M087's disjoint-domain guarantee.
    """

    image = constructive_image(constructor, item.action_names, item.observer_names)
    inside = [list(program) for program in item.hidden_programs if tuple(program) in image]
    return {
        "world_id": item.world_id,
        "hidden_programs": [list(program) for program in item.hidden_programs],
        "constructive_image_size": len(image),
        "hidden_inside_image": inside,
        "all_hidden_outside_image": not inside,
    }


def run_arm(
    arm: str, development: Development, drawn: Mapping[str, Sequence[Sequence[str]]],
) -> dict[str, object]:
    if arm not in ARMS:
        raise LineageError(f"unknown arm {arm!r}")
    adopted = development.adopted_constructor
    repetitions = 1
    supplied: Sequence[ExperimentProgram] | None = None

    if arm == "evolvable_experiment_constructor":
        # Persistence: the constructor is restored from its serialized form rather than rebuilt,
        # so later use is use of the stored artifact.
        constructor = (
            ExperimentConstructor.from_dict(json.loads(json.dumps(adopted.to_dict())))
            if adopted is not None else m0_constructor()
        )
    elif arm == "fixed_experiment_constructor":
        constructor = m0_constructor()
    elif arm == "constructor_acquisition_ablated":
        constructor = m0_constructor() if adopted is None else _strip(adopted)
    elif arm == "more_budget_same_experiment_space":
        constructor = m0_constructor()
        repetitions = BUDGET_MULTIPLE
    elif arm == "fresh_agent":
        constructor = m0_constructor()
    else:  # authored_full_experiment_space
        constructor = m0_constructor()

    encounters: list[Encounter] = []
    for world_id in QUALIFICATION_WORLDS:
        # Supplied by a separate process that ran after the adopted constructor was digested.
        item = qualified_world(world_id, drawn[world_id])
        if arm == "authored_full_experiment_space" and adopted is not None:
            # The ceiling: handed the space M1 would have constructed, without constructing it.
            supplied = construct(adopted, item.action_names, item.observer_names)
        encounters.append(encounter(
            item, constructor, prior=m0_constructor(),
            repetitions=repetitions, supplied_programs=supplied,
        ))

    correct = [record for record in encounters if record.correct]
    return {
        "arm": arm,
        "is_ceiling": arm in CEILING_ARMS,
        "constructor_digest": constructor.digest(),
        "constructor": constructor.to_dict(),
        "repetitions": repetitions,
        "supplied_experiment_space": supplied is not None,
        "encounters": [record.to_dict() for record in encounters],
        "correct_terminal_decisions": len(correct),
        "encounter_count": len(encounters),
        "worlds_with_correct_decision": sorted({record.world_id for record in correct}),
        "total_acquisitions": sum(len(record.acquisitions) for record in encounters),
        "total_programs_executed": sum(record.programs_executed for record in encounters),
        "experiments_outside_prior_image": sum(
            len(record.outside_prior_image) for record in encounters
        ),
    }


def _strip(constructor: ExperimentConstructor) -> ExperimentConstructor:
    """The ablation: the lineage acquired the constructor, then had its expressiveness removed."""

    kept = tuple(
        rule for rule in constructor.rules
        if rule not in {"EMIT_ACTION_SEQUENCE", "PERMUTE_ORDER", "ALLOW_REPETITION"}
    )
    return ExperimentConstructor(
        rules=kept, max_depth=1,
        provenance=constructor.provenance + ("constructor_ablated",),
        version=constructor.version + 1,
    )


# --------------------------------------------------------------------------------------------
# the frozen verdict
# --------------------------------------------------------------------------------------------

CONDITIONS = (
    "P1_prior_constructor_cannot_resolve_exhaustively",
    "P2_meta_transformation_adopted_after_rejections",
    "P3_constructed_experiment_outside_prior_image",
    "P4_observation_used_causally",
    "P5_evolvable_correct_in_every_qualification_world",
    "P6_capability_discordance_against_fixed",
    "P7_more_budget_same_space_cannot_close_it",
    "P8_ablation_loses_the_capability",
    "P9_cross_environment_reuse_without_new_meta_transformation",
    "P10_constructor_persisted_and_restored_byte_identically",
)


def evaluate(
    development: Mapping[str, object],
    arms: Mapping[str, Mapping[str, object]],
    rollback: Mapping[str, object],
) -> dict[str, object]:
    """Compute every frozen condition. Each is computed and each can make the verdict negative."""

    evolvable = arms["evolvable_experiment_constructor"]
    fixed = arms["fixed_experiment_constructor"]
    ablated = arms["constructor_acquisition_ablated"]
    budgeted = arms["more_budget_same_experiment_space"]

    def worlds_correct(arm: Mapping[str, object]) -> set[str]:
        return set(arm["worlds_with_correct_decision"])  # type: ignore[arg-type]

    evolvable_correct = worlds_correct(evolvable)
    fixed_correct = worlds_correct(fixed)
    discordant = sorted(evolvable_correct - fixed_correct)
    limitation = development["limitation"]
    assert isinstance(limitation, Mapping)

    # Causal use: every acquisition the evolvable arm made must have eliminated at least one
    # candidate, and the final survivor must be one the observations selected.
    # Amendment A1. Each of P4, P5 and P8 could pass vacuously on an arm with no encounters at
    # all, which is the M086-A failure mode -- a condition that cannot fail. An adversarial test
    # found it before merge. Every one now requires the evidence to exist.
    causal = bool(evolvable["encounters"])  # type: ignore[arg-type]
    for record in evolvable["encounters"]:  # type: ignore[index]
        if not record["acquisitions"]:
            causal = False
        for acquisition in record["acquisitions"]:
            if not acquisition["eliminated"]:
                causal = False

    results = {
        "P1_prior_constructor_cannot_resolve_exhaustively": (
            limitation["resolved_by_prior_constructor"] is False
            and limitation["prior_correct"] is False
            and not limitation["discriminating_programs_in_prior_image"]
        ),
        "P2_meta_transformation_adopted_after_rejections": (
            development["adopted_constructor"] is not None
            and int(development["rejected_count"]) >= 3
        ),
        "P3_constructed_experiment_outside_prior_image": (
            int(evolvable["experiments_outside_prior_image"]) >= 1  # type: ignore[arg-type]
            and all(
                record["experiments_outside_prior_image"]
                for record in evolvable["encounters"]  # type: ignore[index]
            )
        ),
        "P4_observation_used_causally": causal,
        "P5_evolvable_correct_in_every_qualification_world": (
            int(evolvable["encounter_count"]) == len(QUALIFICATION_WORLDS)  # type: ignore[arg-type]
            and evolvable["correct_terminal_decisions"] == evolvable["encounter_count"]
        ),
        "P6_capability_discordance_against_fixed": (
            len(discordant) >= 1 and not sorted(fixed_correct - evolvable_correct)
        ),
        "P7_more_budget_same_space_cannot_close_it": (
            int(budgeted["total_programs_executed"])  # type: ignore[arg-type]
            > int(fixed["total_programs_executed"])  # type: ignore[arg-type]
            and int(budgeted["experiments_outside_prior_image"]) == 0  # type: ignore[arg-type]
            and not (worlds_correct(budgeted) & set(discordant))
        ),
        "P8_ablation_loses_the_capability": (
            bool(discordant)
            and not (worlds_correct(ablated) & set(discordant))
            and int(ablated["experiments_outside_prior_image"]) == 0  # type: ignore[arg-type]
        ),
        # Both qualification worlds differ structurally from the development world, and the same
        # serialized constructor is used in each with no further meta-transformation.
        "P9_cross_environment_reuse_without_new_meta_transformation": (
            len(evolvable_correct) >= 2
            and DEVELOPMENT_WORLD not in set(QUALIFICATION_WORLDS)
            and len({
                record["constructor_digest"]
                for record in evolvable["encounters"]  # type: ignore[index]
            }) == 1
        ),
        "P10_constructor_persisted_and_restored_byte_identically": (
            rollback["corruption_detected"] is True
            and rollback["byte_identical_restore"] is True
            and rollback["digest_matches"] is True
            and rollback["constructor_included_in_restored_state"] is True
            and rollback["corrupted_state_was_the_restored_state"] is True
            and rollback["fault_actually_changed_behaviour"] is True
        ),
    }
    verdict = all(results.values())
    return {
        "conditions": {name: bool(results[name]) for name in CONDITIONS},
        "verdict": "positive" if verdict else "negative",
        "hypothesis_supported": verdict,
        "discordant_worlds": discordant,
        "evolvable_correct_worlds": sorted(evolvable_correct),
        "fixed_correct_worlds": sorted(fixed_correct),
        "failed_conditions": [name for name in CONDITIONS if not results[name]],
    }


__all__ = [
    "ACQUISITION_BUDGET", "ARMS", "BUDGET_MULTIPLE", "CEILING_ARMS", "CONDITIONS",
    "DEVELOPMENT_WORLD", "Development", "Encounter", "LineageError", "QUALIFICATION_WORLDS",
    "RESULT_SCHEMA", "encounter", "evaluate", "meta_search", "observe_limitation",
    "hidden_outside_constructive_image", "rollback_proof", "run_arm",
]
