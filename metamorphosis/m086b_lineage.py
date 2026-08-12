"""The M086-B lineage: two phases in separate processes, a real forced fault, and ten conditions.

Phase 1 meets the development limitation, searches its meta-primitives on disposable descendants,
adopts what validates under a transaction that is deliberately faulted, and writes the adopted
mechanism out. It never sees a holdout, because at the time it runs no holdout exists.

Phase 3 reads the holdout artifact and runs every arm against it, scored by an evaluator on hidden
cases. `evaluate` computes P1 through P10 and returns them as a table; a single false is negative.
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from metamorphosis.m047_runtime_sandbox import (
    SoftwareSandboxError,
    SoftwareSandboxJob,
    run_bodies_in_sandbox,
    run_body_in_sandbox,
)
from metamorphosis.m047_software_body import SoftwareBody, SoftwareBodyError, SoftwareCase
from metamorphosis.m086_evolvable_mechanism import (
    Mechanism,
    MechanismError,
    build_mechanism,
    candidate_meta_transformations,
    diagnose,
    generate,
    m0_mechanism,
)
from metamorphosis.m086b_bank import body_from_shape, draw_shape, public_cases_from_shape

SANDBOX_TIMEOUT = 60.0
CYCLES_PER_PHASE = 2
TASK_ONLY_MUTABLE_CYCLE_MULTIPLIER = 3
MAX_CANDIDATES = 64
MAX_REPAIRS = 4

ARMS = ("evolvable_meta", "fixed_meta", "meta_acquisition_ablated", "task_only_mutable")
ARMS_THAT_MAY_ADOPT = ("evolvable_meta", "meta_acquisition_ablated")

CONDITIONS = ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10")


class LineageError(RuntimeError):
    """Raised when an arm, phase or transaction contract is violated."""


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def digest_of(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


# --------------------------------------------------------------------------------------------
# One improvement cycle
# --------------------------------------------------------------------------------------------

@dataclass
class CycleOutcome:
    diagnosed: bool
    modules: tuple[str, ...]
    candidates_generated: int
    adopted_label: str | None
    body: SoftwareBody
    passed: int
    total: int

    def to_dict(self) -> dict[str, object]:
        return {
            "diagnosed": self.diagnosed, "modules": list(self.modules),
            "candidates_generated": self.candidates_generated,
            "adopted_label": self.adopted_label, "passed": self.passed, "total": self.total,
        }


def run_cycle(
    mechanism: Mechanism, body: SoftwareBody, public: Sequence[SoftwareCase],
) -> CycleOutcome:
    incumbent = run_body_in_sandbox(body, public, timeout_seconds=SANDBOX_TIMEOUT)
    if not incumbent.disposable_process:
        raise LineageError("diagnostic execution was not disposable")
    hypothesis = diagnose(mechanism, incumbent.cases)
    if not hypothesis.sufficient:
        return CycleOutcome(False, (), 0, None, body, incumbent.passed_cases, len(public))

    candidates = generate(mechanism, body, hypothesis)[:MAX_CANDIDATES]
    prepared: list[tuple[str, SoftwareBody]] = []
    for label, replacements in candidates:
        if not replacements:
            continue
        try:
            prepared.append((label, body.replace_modules(replacements)))
        except (SoftwareBodyError, MechanismError):
            continue
    if not prepared:
        return CycleOutcome(
            True, hypothesis.modules, len(candidates), None, body,
            incumbent.passed_cases, len(public),
        )

    jobs = tuple(
        SoftwareSandboxJob(f"c{index}", candidate, tuple(public))
        for index, (_, candidate) in enumerate(prepared)
    )
    try:
        results = run_bodies_in_sandbox(jobs, timeout_seconds=SANDBOX_TIMEOUT)
    except SoftwareSandboxError:
        results = {}

    best: tuple[int, str, SoftwareBody] | None = None
    for index, (label, candidate) in enumerate(prepared):
        outcome = results.get(f"c{index}")
        if outcome is None or not outcome.disposable_process:
            continue
        if best is None or outcome.passed_cases > best[0]:
            best = (outcome.passed_cases, label, candidate)

    if best is None or best[0] <= incumbent.passed_cases:
        return CycleOutcome(
            True, hypothesis.modules, len(candidates), None, body,
            incumbent.passed_cases, len(public),
        )
    return CycleOutcome(
        True, hypothesis.modules, len(candidates), best[1], best[2], best[0], len(public),
    )


def solves(body: SoftwareBody, cases: Sequence[SoftwareCase]) -> bool:
    """Evaluator-owned success, from executed behaviour."""

    outcome = run_body_in_sandbox(body, cases, timeout_seconds=SANDBOX_TIMEOUT)
    return outcome.disposable_process and outcome.all_cases_passed


def pursue(
    mechanism: Mechanism, body: SoftwareBody, public: Sequence[SoftwareCase], cycles: int,
) -> tuple[SoftwareBody, list[CycleOutcome]]:
    outcomes: list[CycleOutcome] = []
    current = body
    for _ in range(cycles):
        outcome = run_cycle(mechanism, current, public)
        outcomes.append(outcome)
        current = outcome.body
        if outcome.passed == outcome.total or outcome.adopted_label is None:
            break
    return current, outcomes


# --------------------------------------------------------------------------------------------
# The meta-search, and an adoption transaction that is deliberately faulted
# --------------------------------------------------------------------------------------------

@dataclass
class MetaTrial:
    primitives: tuple[str, ...]
    mechanism_digest: str
    diagnosed: bool
    candidates_generated: int
    solved: bool
    accepted: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "primitives": list(self.primitives), "mechanism_digest": self.mechanism_digest,
            "diagnosed": self.diagnosed, "candidates_generated": self.candidates_generated,
            "solved": self.solved, "accepted": self.accepted,
        }


def meta_search(
    base: Mechanism, body: SoftwareBody, public: Sequence[SoftwareCase],
) -> tuple[Mechanism | None, list[MetaTrial]]:
    """Singles before pairs, alphabetical within a size. Nothing here knows which one works."""

    trials: list[MetaTrial] = []
    adopted: Mechanism | None = None
    for primitives in candidate_meta_transformations():
        candidate = build_mechanism(base, primitives)
        descendant, outcomes = pursue(candidate, copy.deepcopy(body), public, CYCLES_PER_PHASE)
        solved = solves(descendant, public)
        trials.append(MetaTrial(
            primitives=tuple(primitives), mechanism_digest=candidate.digest(),
            diagnosed=any(outcome.diagnosed for outcome in outcomes),
            candidates_generated=sum(outcome.candidates_generated for outcome in outcomes),
            solved=solved, accepted=solved and adopted is None,
        ))
        if solved and adopted is None:
            adopted = candidate
    return adopted, trials


@dataclass
class RollbackEvidence:
    """P8. Every field is recorded so the checker can re-derive the whole transaction."""

    independent_pre_adoption_digest: str
    provisional_adopted_digest: str
    corrupted_digest: str
    fault_detected: bool
    restored_digest: str
    restored_equals_independent_record: bool
    readopted_digest: str

    def to_dict(self) -> dict[str, object]:
        return {
            "independent_pre_adoption_digest": self.independent_pre_adoption_digest,
            "provisional_adopted_digest": self.provisional_adopted_digest,
            "corrupted_digest": self.corrupted_digest,
            "fault_detected": self.fault_detected,
            "restored_digest": self.restored_digest,
            "restored_equals_independent_record": self.restored_equals_independent_record,
            "readopted_digest": self.readopted_digest,
        }


def corrupt(mechanism: Mechanism) -> Mechanism:
    """The declared fault: drop the first rule from the provisional mechanism."""

    if not mechanism.rules:
        raise LineageError("cannot corrupt a mechanism with no rules")
    return Mechanism(
        schema=mechanism.schema, rules=mechanism.rules[1:],
        composes=mechanism.composes, provenance=mechanism.provenance + ("__corrupted__",),
    )


def adopt_with_forced_fault(
    live: Mechanism, candidate: Mechanism, independent_record_digest: str,
) -> tuple[Mechanism, RollbackEvidence]:
    """Adopt under a transaction, inject a fault, restore, and prove the restore byte-identical.

    The comparison is against `independent_record_digest`, written before the transaction by a
    caller this function cannot reach. Comparing a restored state against its own checkpoint is the
    tautology M080 recorded, and it is what this signature exists to prevent.
    """

    checkpoint = copy.deepcopy(live)
    provisional = copy.deepcopy(candidate)
    expected = provisional.digest()

    damaged = corrupt(provisional)
    detected = damaged.digest() != expected

    restored = copy.deepcopy(checkpoint)
    restored_digest = restored.digest()
    matches = restored_digest == independent_record_digest

    readopted = copy.deepcopy(candidate) if detected and matches else restored
    return readopted, RollbackEvidence(
        independent_pre_adoption_digest=independent_record_digest,
        provisional_adopted_digest=expected,
        corrupted_digest=damaged.digest(),
        fault_detected=detected,
        restored_digest=restored_digest,
        restored_equals_independent_record=matches,
        readopted_digest=readopted.digest(),
    )


# --------------------------------------------------------------------------------------------
# Phase 1 — development, meta-search, adoption. No holdout exists while this runs.
# --------------------------------------------------------------------------------------------

def run_phase1_arm(arm: str, salt: bytes, write_independent_record) -> dict[str, object]:
    if arm not in ARMS:
        raise LineageError(f"unknown arm {arm!r}")

    shape = draw_shape(salt, "development")
    body = body_from_shape(shape)
    public = public_cases_from_shape(shape, "development")

    mechanism = m0_mechanism()
    start_digest = mechanism.digest()
    journal: list[dict[str, object]] = [{
        "step": "phase1_entered", "arm": arm, "mechanism": start_digest,
        "body": body.digest(), "public": [case.case_id for case in public],
    }]

    developed, outcomes = pursue(mechanism, body, public, CYCLES_PER_PHASE)
    solved = solves(developed, public)
    journal.append({
        "step": "attempt_with_starting_mechanism",
        "cycles": [outcome.to_dict() for outcome in outcomes],
        "solved": solved,
    })

    trials: list[MetaTrial] = []
    rollback: RollbackEvidence | None = None
    adopted_primitives: tuple[str, ...] = ()

    if arm in ARMS_THAT_MAY_ADOPT and not solved:
        candidate, trials = meta_search(mechanism, body, public)
        journal.append({
            "step": "meta_search",
            "limitation": "the starting mechanism produced no hypothesis for two-stage evidence",
            "trials": [trial.to_dict() for trial in trials],
        })
        if candidate is not None:
            # Written before the transaction, by a caller `adopt_with_forced_fault` cannot reach.
            independent = write_independent_record(arm, mechanism)
            mechanism, rollback = adopt_with_forced_fault(mechanism, candidate, independent)
            adopted_primitives = mechanism.provenance
            journal.append({
                "step": "meta_adoption_under_forced_fault",
                "primitives": list(adopted_primitives),
                "rollback": rollback.to_dict(),
                "mechanism_after": mechanism.digest(),
            })
            developed, _ = pursue(mechanism, body, public, CYCLES_PER_PHASE)
            solved = solves(developed, public)

    after_development = mechanism.digest()
    if arm == "meta_acquisition_ablated":
        mechanism = m0_mechanism()
        journal.append({
            "step": "meta_acquisition_stripped", "mechanism_restored_to": mechanism.digest(),
        })

    record = {
        "arm": arm,
        "mechanism_start_digest": start_digest,
        "mechanism_after_development_digest": after_development,
        "mechanism_carried_to_holdout": mechanism.to_dict(),
        "mechanism_carried_digest": mechanism.digest(),
        "meta_transformations_adopted": 1 if adopted_primitives else 0,
        "adopted_primitives": list(adopted_primitives),
        "rejected_primitives": [
            list(trial.primitives) for trial in trials if not trial.solved
        ],
        "meta_trials": [trial.to_dict() for trial in trials],
        "development_solved": solved,
        "rollback": rollback.to_dict() if rollback else None,
        "journal": journal,
    }
    record["record_digest"] = digest_of(record)
    return record


# --------------------------------------------------------------------------------------------
# Phase 3 — the holdout, read from an artifact that did not exist during phase 1
# --------------------------------------------------------------------------------------------

def run_holdout_arm(
    arm: str, carried: Mechanism, holdout_body: SoftwareBody,
    public: Sequence[SoftwareCase], hidden: Sequence[SoftwareCase],
) -> dict[str, object]:
    cycles = CYCLES_PER_PHASE
    if arm == "task_only_mutable":
        cycles *= TASK_ONLY_MUTABLE_CYCLE_MULTIPLIER

    body, outcomes = pursue(carried, holdout_body, public, cycles)
    public_solved = solves(body, public)
    hidden_solved = public_solved and solves(body, hidden)
    adopted_label = next(
        (outcome.adopted_label for outcome in reversed(outcomes) if outcome.adopted_label), None,
    )
    record = {
        "arm": arm,
        "mechanism_at_holdout_digest": carried.digest(),
        "cycles": [outcome.to_dict() for outcome in outcomes],
        "cycles_used": len(outcomes),
        "holdout_candidates_generated": sum(o.candidates_generated for o in outcomes),
        "holdout_adopted_label": adopted_label,
        "holdout_public_solved": public_solved,
        "holdout_hidden_solved": hidden_solved,
    }
    record["record_digest"] = digest_of(record)
    return record


def enumerate_starting_image(holdout_body: SoftwareBody, public: Sequence[SoftwareCase]) -> dict:
    """The starting mechanism's complete constructive image for the holdout evidence."""

    executed = run_body_in_sandbox(holdout_body, public, timeout_seconds=SANDBOX_TIMEOUT)
    mechanism = m0_mechanism()
    hypothesis = diagnose(mechanism, executed.cases)
    candidates = generate(mechanism, holdout_body, hypothesis)
    return {
        "diagnosed": hypothesis.sufficient,
        "modules": list(hypothesis.modules),
        "candidate_count": len(candidates),
        "candidate_labels": [label for label, _ in candidates],
    }


# --------------------------------------------------------------------------------------------
# The verdict: ten conditions, each computed, a single false is negative
# --------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Verdict:
    conditions: Mapping[str, bool]
    reasons: Mapping[str, str]

    @property
    def positive(self) -> bool:
        return all(self.conditions[name] for name in CONDITIONS)

    def to_dict(self) -> dict[str, object]:
        return {
            "conditions": {name: self.conditions[name] for name in CONDITIONS},
            "reasons": {name: self.reasons[name] for name in CONDITIONS},
            "positive": self.positive,
        }


def evaluate(
    phase1: Mapping[str, Mapping[str, object]],
    holdout: Mapping[str, Mapping[str, object]],
    image: Mapping[str, object],
    chronology: Mapping[str, object],
    differential: Mapping[str, object],
) -> Verdict:
    """P1 through P10. Every one is computed here; none is documentary."""

    conditions: dict[str, bool] = {}
    reasons: dict[str, str] = {}

    def record(name: str, value: bool, reason: str) -> None:
        conditions[name] = bool(value)
        reasons[name] = reason

    evolvable = phase1["evolvable_meta"]
    evolvable_holdout = holdout["evolvable_meta"]

    adopted = evolvable["meta_transformations_adopted"] == 1
    rejected = bool(evolvable["rejected_primitives"])
    record(
        "P1", adopted and rejected,
        f"adopted={evolvable['meta_transformations_adopted']}, "
        f"rejected={len(evolvable['rejected_primitives'])}",
    )
    record(
        "P2", bool(evolvable_holdout["holdout_hidden_solved"]),
        f"evolvable_meta hidden-case success = {evolvable_holdout['holdout_hidden_solved']}",
    )
    record(
        "P3",
        not holdout["fixed_meta"]["holdout_hidden_solved"] and image["candidate_count"] == 0,
        f"fixed_meta solved={holdout['fixed_meta']['holdout_hidden_solved']}, "
        f"starting image={image['candidate_count']} candidates",
    )
    record(
        "P4", not holdout["meta_acquisition_ablated"]["holdout_hidden_solved"],
        f"meta_acquisition_ablated solved="
        f"{holdout['meta_acquisition_ablated']['holdout_hidden_solved']}",
    )
    record(
        "P5", not holdout["task_only_mutable"]["holdout_hidden_solved"],
        f"task_only_mutable solved={holdout['task_only_mutable']['holdout_hidden_solved']}",
    )
    label = evolvable_holdout["holdout_adopted_label"]
    record(
        "P6", bool(label) and label not in set(image["candidate_labels"]),
        f"adopted label {label!r} against a starting image of "
        f"{len(image['candidate_labels'])} labels",
    )

    journal = evolvable["journal"]
    steps = [entry.get("step") for entry in journal]
    required = (
        "phase1_entered", "attempt_with_starting_mechanism", "meta_search",
        "meta_adoption_under_forced_fault",
    )
    record(
        "P7", all(step in steps for step in required)
        and evolvable["mechanism_start_digest"] != evolvable["mechanism_after_development_digest"],
        f"journal steps {steps}",
    )

    rollback = evolvable["rollback"]
    record(
        "P8",
        bool(rollback)
        and bool(rollback["fault_detected"])
        and bool(rollback["restored_equals_independent_record"])
        and rollback["restored_digest"] == rollback["independent_pre_adoption_digest"]
        and rollback["corrupted_digest"] != rollback["provisional_adopted_digest"],
        "no rollback evidence" if not rollback else (
            f"detected={rollback['fault_detected']}, "
            f"restored={rollback['restored_digest'][:12]}, "
            f"independent={rollback['independent_pre_adoption_digest'][:12]}"
        ),
    )
    record(
        "P9", bool(chronology.get("ordered")),
        str(chronology.get("detail", "")),
    )
    record(
        "P10", bool(differential.get("equivalent")),
        f"{differential.get('probes', 0)} differential probes against M047",
    )
    return Verdict(conditions=conditions, reasons=reasons)
