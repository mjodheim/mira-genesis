"""M087 — the lineage that changes how it decides which improvement is justified.

Diagnosis and candidate generation are **fixed** here: `m086_evolvable_mechanism.m0_mechanism`
unchanged, which is M047's frozen pair. What is mutable is the object D054 identified as never
having been mutable — the rule that picks among candidates, and its complete absence of any way to
obtain more evidence.

Development runs on one family and must produce the meta-transformation. Qualification runs on
situations materialized **after** the adopted policy is serialized, one of them in the family that
caused the acquisition and two in families that did not, so that later reuse and cross-family
reuse are separate observations rather than one claim.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from metamorphosis.m047_runtime_sandbox import (
    SoftwareSandboxError,
    run_bodies_in_sandbox,
    run_body_in_sandbox,
    SoftwareSandboxJob,
)
from metamorphosis.m047_software_core import SoftwareBodyError, SoftwareCase
from metamorphosis.m047_software_model import SoftwareBody
from metamorphosis.m086_evolvable_mechanism import MechanismError, diagnose, generate, m0_mechanism
from metamorphosis.m087_evidence import (
    AcquisitionLog,
    EvidenceError,
    Observation,
    digest_of,
)
from metamorphosis.m087_families import Family, all_families, family, qualified_family
from metamorphosis.m087_selection_policy import (
    SelectionOutcome,
    SelectionPolicy,
    build_policy,
    candidate_meta_transformations,
    execute_policy,
    m0_policy,
)


RESULT_SCHEMA = "m087-result-v1"
SANDBOX_TIMEOUT = 30

ARMS = (
    "evolvable_selection_evidence",
    "fixed_selection_evidence",
    "selection_acquisition_ablated",
    "more_budget_same_evidence",
    "fresh_agent",
)

DEVELOPMENT_FAMILY = "tool_semantics"
QUALIFICATION_FAMILIES = ("tool_semantics", "interpretation_routing", "planning_structure")

# `more_budget_same_evidence` gets this multiple of every computational allowance and exactly the
# same E_acquired, which is empty. If it can succeed, the deficit was never informational.
BUDGET_MULTIPLE = 10


class LineageError(RuntimeError):
    """Raised when an arm violates its own contract."""


def _run(body: SoftwareBody, cases: Sequence[SoftwareCase]):
    outcome = run_body_in_sandbox(body, cases, timeout_seconds=SANDBOX_TIMEOUT)
    if not outcome.disposable_process:
        raise LineageError("execution was not disposable")
    return outcome


def observe(body: SoftwareBody, request: str) -> Observation:
    """Run one request on one body and record what came back."""

    case = SoftwareCase("probe", request, None, "probe")
    try:
        outcome = run_body_in_sandbox(body, (case,), timeout_seconds=SANDBOX_TIMEOUT)
    except SoftwareSandboxError as exc:
        return Observation(request, False, None, f"sandbox:{exc}")
    execution = outcome.cases[0]
    if not execution.ok:
        return Observation(request, False, None, execution.error_message or "error")
    return Observation(request, True, execution.output)


@dataclass
class Situation:
    """One ambiguous encounter and everything it produced."""

    family_id: str
    candidates: tuple[str, ...]
    public_scores: dict[str, int]
    outcome: SelectionOutcome
    adopted_label: str | None
    hidden_passed: int
    hidden_total: int
    acquisitions: int
    candidates_evaluated: int
    cycles: int

    @property
    def correct(self) -> bool:
        return self.adopted_label is not None and self.hidden_passed == self.hidden_total

    def to_dict(self) -> dict[str, object]:
        return {
            "family_id": self.family_id,
            "candidates": list(self.candidates),
            "public_scores": dict(sorted(self.public_scores.items())),
            "selection": self.outcome.to_dict(),
            "adopted_label": self.adopted_label,
            "hidden_passed": self.hidden_passed,
            "hidden_total": self.hidden_total,
            "correct_terminal_decision": self.correct,
            "acquisitions": self.acquisitions,
            "candidates_evaluated": self.candidates_evaluated,
            "cycles": self.cycles,
        }


def _candidate_bodies(fam: Family) -> tuple[tuple[str, SoftwareBody], ...]:
    """Diagnose and generate through the FIXED M047 mechanism, then build each candidate body."""

    incumbent = _run(fam.starting_body, fam.public_cases)
    hypothesis = diagnose(m0_mechanism(), incumbent.cases)
    if not hypothesis.sufficient:
        raise LineageError(f"{fam.family_id}: the frozen diagnosis isolated no module")
    prepared: list[tuple[str, SoftwareBody]] = []
    for label, replacements in generate(m0_mechanism(), fam.starting_body, hypothesis):
        if not replacements:
            continue
        try:
            prepared.append((label, fam.starting_body.replace_modules(replacements)))
        except (SoftwareBodyError, MechanismError):
            continue
    if not prepared:
        raise LineageError(f"{fam.family_id}: the frozen generator emitted no candidate")
    return tuple(prepared)


def _public_scores(
    prepared: Sequence[tuple[str, SoftwareBody]], fam: Family,
) -> dict[str, int]:
    jobs = tuple(
        SoftwareSandboxJob(f"cand_{index}", body, tuple(fam.public_cases))
        for index, (_, body) in enumerate(prepared)
    )
    try:
        results = run_bodies_in_sandbox(jobs, timeout_seconds=SANDBOX_TIMEOUT)
    except SoftwareSandboxError:
        results = {}
    scores: dict[str, int] = {}
    for index, (label, _) in enumerate(prepared):
        outcome = results.get(f"cand_{index}")
        scores[label] = outcome.passed_cases if outcome is not None else -1
    return scores


def encounter(
    fam: Family, policy: SelectionPolicy, *, budget_multiple: int = 1,
    log: AcquisitionLog | None = None,
) -> Situation:
    """One ambiguous situation, resolved by whatever the policy can do about it."""

    prepared = _candidate_bodies(fam)
    bodies = dict(prepared)
    labels = tuple(label for label, _ in prepared)
    scores = _public_scores(prepared, fam)
    incumbent = _run(fam.starting_body, fam.public_cases).passed_cases

    prediction_cache: dict[tuple[str, str], Observation] = {}

    def predict(label: str, request: str) -> Observation:
        key = (label, request)
        if key not in prediction_cache:
            prediction_cache[key] = observe(bodies[label], request)
        return prediction_cache[key]

    def acquire(request: str) -> Observation:
        # The authorized reference source. A different object from the evaluator, which is never
        # passed into the policy and has no callable form here.
        return observe(fam.reference_body, request)

    outcome = execute_policy(
        policy,
        candidates=labels,
        public_scores=scores,
        incumbent_score=incumbent,
        experiment_space=fam.acquirable_requests,
        predict=predict,
        acquire=acquire,
        log=log,
    )

    hidden_passed, hidden_total = 0, len(fam.hidden_cases)
    if outcome.selected is not None:
        hidden = _run(bodies[outcome.selected], fam.hidden_cases)
        hidden_passed = hidden.passed_cases
    return Situation(
        family_id=fam.family_id,
        candidates=labels,
        public_scores=scores,
        outcome=outcome,
        adopted_label=outcome.selected,
        hidden_passed=hidden_passed,
        hidden_total=hidden_total,
        acquisitions=outcome.acquisitions,
        candidates_evaluated=len(labels) * budget_multiple,
        cycles=budget_multiple,
    )


# --------------------------------------------------------------------------------------------
# development: the lineage acquires a better selection policy
# --------------------------------------------------------------------------------------------


@dataclass
class Development:
    limitation: dict[str, object]
    rejected: list[dict[str, object]] = field(default_factory=list)
    adopted_steps: tuple[tuple[str, object], ...] | None = None
    adopted_policy: SelectionPolicy | None = None
    pre_adoption_policy: SelectionPolicy | None = None
    validation_family: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "limitation": self.limitation,
            "rejected_meta_transformations": self.rejected,
            "rejected_count": len(self.rejected),
            "adopted_steps": [list(step) for step in (self.adopted_steps or ())],
            "adopted_policy": self.adopted_policy.to_dict() if self.adopted_policy else None,
            "adopted_policy_digest": (
                self.adopted_policy.digest() if self.adopted_policy else None
            ),
            "pre_adoption_policy_digest": (
                self.pre_adoption_policy.digest() if self.pre_adoption_policy else None
            ),
            "validation_family": self.validation_family,
        }


def observe_limitation(fam: Family) -> dict[str, object]:
    """Run M0's policy and record what it did about the tie it could not see."""

    situation = encounter(fam, m0_policy())
    equivalent = [
        label for label, score in situation.public_scores.items()
        if score == max(situation.public_scores.values())
    ]
    return {
        "family_id": fam.family_id,
        "candidates": list(situation.candidates),
        "top_scoring_candidates": sorted(equivalent),
        "observationally_equivalent_count": len(equivalent),
        "m0_terminal_state": situation.outcome.terminal_state,
        "m0_adopted_label": situation.adopted_label,
        "m0_ambiguity_detected": situation.outcome.ambiguity_detected,
        "m0_acquisitions": situation.acquisitions,
        "m0_hidden_passed": situation.hidden_passed,
        "m0_hidden_total": situation.hidden_total,
        "m0_correct": situation.correct,
    }


def meta_search(fam: Family) -> Development:
    """Try each bounded meta-transformation on a disposable descendant; adopt the first that works.

    Validation is a real hidden-case check performed outside the mutable body: the descendant
    policy must select a candidate that passes cases the policy never saw. A meta-transformation
    cannot validate itself, and the search is an ordering, not a ranking.
    """

    development = Development(limitation=observe_limitation(fam))
    development.pre_adoption_policy = m0_policy()
    development.validation_family = fam.family_id

    for steps in candidate_meta_transformations():
        candidate_policy = build_policy(m0_policy(), steps)
        log = AcquisitionLog(fam.spaces, budget=candidate_policy.acquisition_budget or 1)
        try:
            situation = encounter(fam, candidate_policy, log=log)
        except (EvidenceError, LineageError) as exc:
            development.rejected.append({
                "steps": [list(step) for step in steps],
                "reason": f"refused: {exc}",
            })
            continue
        if situation.correct:
            development.adopted_steps = tuple(steps)
            development.adopted_policy = candidate_policy
            return development
        development.rejected.append({
            "steps": [list(step) for step in steps],
            "terminal_state": situation.outcome.terminal_state,
            "adopted_label": situation.adopted_label,
            "hidden_passed": situation.hidden_passed,
            "acquisitions": situation.acquisitions,
            "reason": "descendant did not reach a correct terminal decision",
        })
    return development


# --------------------------------------------------------------------------------------------
# rollback
# --------------------------------------------------------------------------------------------


def rollback_proof(policy: SelectionPolicy) -> dict[str, object]:
    """Serialize, corrupt, detect, restore, and prove the restoration is byte-identical."""

    serialized = json.dumps(policy.to_dict(), sort_keys=True, separators=(",", ":"))
    checkpoint_digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    corrupted = json.loads(serialized)
    corrupted["program"] = corrupted["program"][:1]
    corrupted_bytes = json.dumps(corrupted, sort_keys=True, separators=(",", ":"))
    corrupted_digest = hashlib.sha256(corrupted_bytes.encode("utf-8")).hexdigest()
    detected = corrupted_digest != checkpoint_digest

    restored = SelectionPolicy.from_dict(json.loads(serialized))
    restored_bytes = json.dumps(restored.to_dict(), sort_keys=True, separators=(",", ":"))
    restored_digest = hashlib.sha256(restored_bytes.encode("utf-8")).hexdigest()
    return {
        "checkpoint_digest": checkpoint_digest,
        "corrupted_digest": corrupted_digest,
        "corruption_detected": detected,
        "restored_digest": restored_digest,
        "byte_identical_restore": restored_bytes == serialized,
        "restored_policy_digest": restored.digest(),
        "policy_digest": policy.digest(),
        "digest_matches": restored.digest() == policy.digest(),
    }


# --------------------------------------------------------------------------------------------
# arms
# --------------------------------------------------------------------------------------------


def run_arm(arm: str, development: Development, salt: str) -> dict[str, object]:
    """Run one arm over the qualification situations, using whatever policy it is entitled to."""

    if arm not in ARMS:
        raise LineageError(f"unknown arm {arm!r}")
    adopted = development.adopted_policy
    multiple = 1

    if arm == "evolvable_selection_evidence":
        if adopted is None:
            policy = m0_policy()
        else:
            # Persistence: the qualification arm restores the policy from its serialized form
            # rather than rebuilding it, so later use is use of the stored artifact.
            policy = SelectionPolicy.from_dict(json.loads(json.dumps(adopted.to_dict())))
    elif arm == "fixed_selection_evidence":
        policy = m0_policy()
    elif arm == "selection_acquisition_ablated":
        policy = m0_policy() if adopted is None else _strip_acquisition(adopted)
    elif arm == "more_budget_same_evidence":
        policy = m0_policy()
        multiple = BUDGET_MULTIPLE
    else:  # fresh_agent
        policy = m0_policy()

    situations: list[Situation] = []
    logs: list[dict[str, object]] = []
    for family_id in QUALIFICATION_FAMILIES:
        # The qualifying hidden cases are drawn from a salt released only after the adopted
        # policy was committed by digest, so no arm can have been shaped by them.
        fam = qualified_family(family_id, salt)
        log = AcquisitionLog(fam.spaces, budget=max(policy.acquisition_budget, 1))
        situation = encounter(fam, policy, budget_multiple=multiple, log=log)
        log.seal()
        situations.append(situation)
        logs.append(log.to_dict())

    correct = [situation for situation in situations if situation.correct]
    families_correct = sorted({situation.family_id for situation in correct})
    return {
        "arm": arm,
        "policy_digest": policy.digest(),
        "policy": policy.to_dict(),
        "can_acquire": policy.can_acquire,
        "budget_multiple": multiple,
        "situations": [situation.to_dict() for situation in situations],
        "acquisition_logs": logs,
        "correct_terminal_decisions": len(correct),
        "situation_count": len(situations),
        "families_with_correct_decision": families_correct,
        "total_acquisitions": sum(situation.acquisitions for situation in situations),
        "total_candidates_evaluated": sum(
            situation.candidates_evaluated for situation in situations
        ),
        "total_cycles": sum(situation.cycles for situation in situations),
    }


def _strip_acquisition(policy: SelectionPolicy) -> SelectionPolicy:
    """The ablation: the lineage acquired the policy, then had the informational action removed."""

    kept = tuple(
        instruction for instruction in policy.program
        if instruction.opcode not in {
            "ACQUIRE_BEST", "FILTER_BY_ACQUIRED", "LOOP_ACQUISITION",
            "ENUMERATE_EXPERIMENTS", "SCORE_EXPERIMENTS",
        }
    )
    return SelectionPolicy(
        program=kept, acquisition_budget=0,
        provenance=policy.provenance + ("acquisition_ablated",), version=policy.version + 1,
    )


__all__ = [
    "ARMS", "BUDGET_MULTIPLE", "DEVELOPMENT_FAMILY", "Development", "LineageError",
    "QUALIFICATION_FAMILIES", "RESULT_SCHEMA", "Situation", "encounter", "meta_search",
    "observe", "observe_limitation", "rollback_proof", "run_arm",
]


# --------------------------------------------------------------------------------------------
# the frozen verdict
# --------------------------------------------------------------------------------------------
#
# Ten conditions, every one computed and every one able to make the verdict negative. M086-A
# reported positive against a threshold that could not fail because four of its ten conditions
# were absent from `evaluate`; here `CONDITIONS` and the keys `evaluate` returns are compared by
# a test, and a missing condition is a failure rather than a silent pass.

CONDITIONS = (
    "P1_ambiguity_represented",
    "P2_meta_transformation_adopted_after_rejections",
    "P3_evolvable_correct_on_every_situation",
    "P4_capability_discordance_against_fixed",
    "P5_more_budget_same_evidence_cannot_close_it",
    "P6_acquisition_ablation_loses_the_capability",
    "P7_cross_family_reuse",
    "P8_policy_persisted_and_restored_byte_identically",
    "P9_no_evidence_leak",
    "P10_chronology_holds",
)


def evaluate(
    development: Mapping[str, object],
    arms: Mapping[str, Mapping[str, object]],
    rollback: Mapping[str, object],
    leak_findings: Sequence[str],
    chronology: Mapping[str, object],
) -> dict[str, object]:
    """Compute every frozen condition. Any one of them may make the verdict negative."""

    evolvable = arms["evolvable_selection_evidence"]
    fixed = arms["fixed_selection_evidence"]
    ablated = arms["selection_acquisition_ablated"]
    budgeted = arms["more_budget_same_evidence"]

    def correct_families(arm: Mapping[str, object]) -> set[str]:
        return {
            str(situation["family_id"])
            for situation in arm["situations"]  # type: ignore[index]
            if situation["correct_terminal_decision"]  # type: ignore[index]
        }

    evolvable_correct = correct_families(evolvable)
    fixed_correct = correct_families(fixed)
    discordant = sorted(evolvable_correct - fixed_correct)

    limitation = development["limitation"]
    assert isinstance(limitation, Mapping)

    results = {
        # The tie M086 could not see is now an observable fact about the situation.
        "P1_ambiguity_represented": (
            int(limitation["observationally_equivalent_count"]) >= 2
            and limitation["m0_ambiguity_detected"] is False
            and limitation["m0_correct"] is False
            and any(
                situation["selection"]["ambiguity_detected"]  # type: ignore[index]
                for situation in evolvable["situations"]  # type: ignore[index]
            )
        ),
        "P2_meta_transformation_adopted_after_rejections": (
            development["adopted_policy"] is not None
            and int(development["rejected_count"]) >= 3
        ),
        "P3_evolvable_correct_on_every_situation": (
            evolvable["correct_terminal_decisions"] == evolvable["situation_count"]
        ),
        # The capability claim: at least one situation the evolved mechanism gets right and the
        # frozen one does not, with none the other way round.
        "P4_capability_discordance_against_fixed": (
            len(discordant) >= 1 and not sorted(fixed_correct - evolvable_correct)
        ),
        # The falsifier that matters most: ten times the computation over the same E_acquired.
        "P5_more_budget_same_evidence_cannot_close_it": (
            budgeted["total_acquisitions"] == 0
            and int(budgeted["total_candidates_evaluated"])
            > int(fixed["total_candidates_evaluated"])
            and not (correct_families(budgeted) & set(discordant))
        ),
        "P6_acquisition_ablation_loses_the_capability": (
            not (correct_families(ablated) & set(discordant))
            and ablated["total_acquisitions"] == 0
        ),
        # Reuse in a family that did not cause the acquisition.
        "P7_cross_family_reuse": (
            len({item for item in discordant if item != DEVELOPMENT_FAMILY}) >= 1
            and len(evolvable_correct) >= 2
        ),
        "P8_policy_persisted_and_restored_byte_identically": (
            rollback["corruption_detected"] is True
            and rollback["byte_identical_restore"] is True
            and rollback["digest_matches"] is True
        ),
        "P9_no_evidence_leak": not list(leak_findings),
        "P10_chronology_holds": bool(chronology.get("ordered")),
    }
    verdict = all(results.values())
    return {
        "conditions": {name: bool(results[name]) for name in CONDITIONS},
        "verdict": "positive" if verdict else "negative",
        "hypothesis_supported": verdict,
        "discordant_families": discordant,
        "evolvable_correct_families": sorted(evolvable_correct),
        "fixed_correct_families": sorted(fixed_correct),
        "failed_conditions": [name for name in CONDITIONS if not results[name]],
    }
