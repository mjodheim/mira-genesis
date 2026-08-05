"""Hidden task construction and generator-independent proposal admission for M046."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
import hashlib
import itertools
import json
from typing import TypeVar

from metamorphosis.m043_mealy import MealyMachine, mealy_digest, minimize_mealy
from metamorphosis.m043_rewrite import (
    DuplicateReachableTarget,
    ReplaceEmission,
    RewriteError,
    apply_rewrite,
    build_rewrite_trace,
    exact_body_digest,
    reachable_states,
)
from metamorphosis.m043_task_model import (
    AdmittedConstructiveTask,
    ControlArm,
    HiddenTargetEvaluator,
    PublicTaskView,
    SearchOutcome,
    SearchStatus,
    StructuralIncapacityCertificate,
    prove_structural_incapacity,
)
from metamorphosis.m046_search import (
    HeuristicProposal,
    ProposalSearchResult,
    ProposalSearchStatus,
    ScalableResourceBudget,
)


class ScalableTaskError(ValueError):
    """Raised when the hidden task or independent validator fails closed."""


class StopAction(str, Enum):
    CONTINUE = "continue"
    ADOPT = "adopt"
    TERMINATE_INSUFFICIENT_EVIDENCE = "terminate_insufficient_evidence"
    TERMINATE_RESOURCE_BUDGET = "terminate_resource_budget"


@dataclass(frozen=True)
class StopDecision:
    action: StopAction
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {"action": self.action.value, "reason": self.reason}


class ProposalStopPolicy:
    """Fixed fail-closed policy applied outside the proposal generator."""

    def decide(
        self,
        *,
        accepted: bool,
        attempts: int,
        remaining: int,
        search_status: ProposalSearchStatus,
        budget: ScalableResourceBudget,
    ) -> StopDecision:
        if accepted:
            return StopDecision(StopAction.ADOPT, "independent exact validation accepted")
        if search_status is ProposalSearchStatus.RESOURCE_BUDGET_EXHAUSTED:
            return StopDecision(
                StopAction.TERMINATE_RESOURCE_BUDGET,
                "proposal search exhausted an explicit resource bound",
            )
        if attempts >= budget.max_validation_attempts:
            return StopDecision(
                StopAction.TERMINATE_INSUFFICIENT_EVIDENCE,
                "independent validation attempt budget exhausted",
            )
        if remaining > 0:
            return StopDecision(
                StopAction.CONTINUE,
                "additional ranked proposals remain inside the validation budget",
            )
        return StopDecision(
            StopAction.TERMINATE_INSUFFICIENT_EVIDENCE,
            "no independently validated proposal remains",
        )


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def _digest(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + _canonical_json(value)).hexdigest()


@dataclass(frozen=True)
class HiddenScalableTask:
    public: PublicTaskView
    incapacity: StructuralIncapacityCertificate
    target_minimal_states: int
    family: str
    required_growth: int
    evaluator: HiddenTargetEvaluator = field(repr=False, compare=False)

    def public_mapping(self) -> dict[str, object]:
        return {
            "public": self.public.to_dict(),
            "incapacity": self.incapacity.to_dict(),
            "target_minimal_states": self.target_minimal_states,
            "family": self.family,
            "required_growth": self.required_growth,
            "target_body_exposed_to_generator": False,
            "witness_trace_exposed_to_generator": False,
        }

    def digest(self) -> str:
        return _digest(b"m046-hidden-scalable-task-v1\x00", self.public_mapping())


@dataclass(frozen=True)
class IndependentValidationAttempt:
    proposal_digest: str
    template_id: str
    accepted: bool
    reason: str
    candidate_body_digest: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "proposal_digest": self.proposal_digest,
            "template_id": self.template_id,
            "accepted": self.accepted,
            "reason": self.reason,
            "candidate_body_digest": self.candidate_body_digest,
        }


@dataclass(frozen=True)
class IndependentSelectionResult:
    decision: StopDecision
    attempts: tuple[IndependentValidationAttempt, ...]
    selected_proposal: HeuristicProposal | None
    admitted_task: AdmittedConstructiveTask | None = field(
        repr=False, compare=False
    )

    @property
    def accepted(self) -> bool:
        return (
            self.decision.action is StopAction.ADOPT
            and self.selected_proposal is not None
            and self.admitted_task is not None
        )

    @property
    def rejected_templates(self) -> tuple[str, ...]:
        return tuple(
            attempt.template_id
            for attempt in self.attempts
            if not attempt.accepted
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "decision": self.decision.to_dict(),
            "attempts": [attempt.to_dict() for attempt in self.attempts],
            "selected_proposal_digest": (
                None
                if self.selected_proposal is None
                else self.selected_proposal.digest()
            ),
            "accepted": self.accepted,
        }

    def digest(self) -> str:
        return _digest(b"m046-independent-selection-v1\x00", self.to_dict())


def _sequential_incapacity(
    parent: MealyMachine, target: MealyMachine
) -> StructuralIncapacityCertificate:
    canonical_parent = minimize_mealy(parent)
    if canonical_parent.n_states != parent.n_states:
        raise ScalableTaskError("M046 parent contains redundant physical capacity")
    base = prove_structural_incapacity(canonical_parent, target)
    return replace(
        base,
        parent_exact_digest=exact_body_digest(parent),
        parent_physical_states=parent.n_states,
        parent_minimal_states=canonical_parent.n_states,
    )


def _safe_growths(
    parent: MealyMachine,
) -> tuple[tuple[int, int, MealyMachine], ...]:
    values: list[tuple[int, int, MealyMachine]] = []
    for state in sorted(reachable_states(parent)):
        for symbol in parent.input_alphabet:
            try:
                grown, _ = apply_rewrite(
                    parent, DuplicateReachableTarget(state, symbol)
                )
            except (RewriteError, ValueError):
                continue
            values.append((state, symbol, grown))
    return tuple(values)


def _row_variants(
    original: tuple[int, ...],
    output_alphabet: tuple[int, ...],
    distance: int,
) -> tuple[tuple[int, ...], ...]:
    if not 1 <= distance <= len(original):
        raise ScalableTaskError("invalid hidden row distance")
    variants: list[tuple[int, ...]] = []
    for positions in itertools.combinations(range(len(original)), distance):
        choices = [
            tuple(value for value in output_alphabet if value != original[position])
            for position in positions
        ]
        for replacements in itertools.product(*choices):
            row = list(original)
            for position, value in zip(positions, replacements, strict=True):
                row[position] = value
            variants.append(tuple(row))
    return tuple(sorted(set(variants)))


_T = TypeVar("_T")


def _rotate(values: tuple[_T, ...], material: bytes) -> tuple[_T, ...]:
    if not values:
        return values
    offset = int.from_bytes(hashlib.sha256(material).digest()[:8], "big") % len(values)
    return values[offset:] + values[:offset]


def _construct_one_growth(
    parent: MealyMachine,
    *,
    ordinal: int,
    edit_distance: int,
) -> MealyMachine:
    growths = _rotate(
        _safe_growths(parent),
        f"growth:{exact_body_digest(parent)}:{ordinal}".encode("ascii"),
    )
    for entry_state, entry_symbol, grown in growths:
        clone = grown.n_states - 1
        variants = _rotate(
            _row_variants(
                grown.outputs[clone], grown.output_alphabet, edit_distance
            ),
            (
                f"row:{exact_body_digest(parent)}:{ordinal}:"
                f"{entry_state}:{entry_symbol}"
            ).encode("ascii"),
        )
        occupied = set(grown.outputs[:-1])
        for row in variants:
            if row in occupied:
                continue
            target = grown
            try:
                for index, output in enumerate(row):
                    if output == target.outputs[clone][index]:
                        continue
                    target, _ = apply_rewrite(
                        target,
                        ReplaceEmission(
                            clone,
                            target.input_alphabet[index],
                            output,
                        ),
                    )
            except (RewriteError, ValueError):
                continue
            if minimize_mealy(target).n_states == parent.n_states + 1:
                return target
    raise ScalableTaskError("could not construct a bounded hidden growth task")


def _task_id(
    parent: MealyMachine,
    target_commitment: str,
    ordinal: int,
    protocol_digest: str,
) -> str:
    return _digest(
        b"m046-task-id-v1\x00",
        {
            "schema": "m046-task-id-v1",
            "protocol_digest": protocol_digest,
            "ordinal": ordinal,
            "parent_body_digest": exact_body_digest(parent),
            "target_commitment": target_commitment,
        },
    )


def build_hidden_scalable_task(
    parent: MealyMachine,
    *,
    ordinal: int,
    protocol_digest: str,
    budget: ScalableResourceBudget,
    required_growth: int = 1,
) -> HiddenScalableTask:
    """Construct a hidden task family without returning its body or rewrite recipe."""

    if required_growth not in {1, 2}:
        raise ScalableTaskError("M046 development tasks fix growth to one or two")
    target = parent
    families: list[str] = []
    for step in range(required_growth):
        distance = 1 if (ordinal + step) % 2 else 2
        target = _construct_one_growth(
            target,
            ordinal=ordinal * 10 + step,
            edit_distance=distance,
        )
        families.append(f"split_emit_{distance}")
    if target.n_states > budget.max_states:
        raise ScalableTaskError("hidden task exceeds the fixed state budget")

    commitment = mealy_digest(target, minimise=True)
    incapacity = _sequential_incapacity(parent, target)
    evaluator = HiddenTargetEvaluator(
        target, observation_limit=budget.max_observations
    )
    public = PublicTaskView(
        schema="m046-public-task-v1",
        task_id=_task_id(parent, commitment, ordinal, protocol_digest),
        parent_exact_digest=exact_body_digest(parent),
        target_commitment=commitment,
        input_alphabet=parent.input_alphabet,
        output_alphabet=parent.output_alphabet,
        observation_limit=budget.max_observations,
        search_budget=budget.search_budget(),
    )
    return HiddenScalableTask(
        public=public,
        incapacity=incapacity,
        target_minimal_states=minimize_mealy(target).n_states,
        family="+".join(families),
        required_growth=required_growth,
        evaluator=evaluator,
    )


def validate_ranked_proposals_independently(
    parent: MealyMachine,
    hidden_task: HiddenScalableTask,
    search: ProposalSearchResult,
    budget: ScalableResourceBudget,
    *,
    stop_policy: ProposalStopPolicy | None = None,
) -> IndependentSelectionResult:
    """Admit a proposal only after exact evaluator-side validation.

    The proposal generator receives neither the exact result nor a distinguishing witness.
    It only supplies a ranked list built from bounded observations.
    """

    policy = stop_policy or ProposalStopPolicy()
    if search.status is not ProposalSearchStatus.READY:
        decision = policy.decide(
            accepted=False,
            attempts=0,
            remaining=0,
            search_status=search.status,
            budget=budget,
        )
        return IndependentSelectionResult(decision, (), None, None)

    attempts: list[IndependentValidationAttempt] = []
    for index, proposal in enumerate(search.proposals):
        if index >= budget.max_validation_attempts:
            break
        candidate = None
        trace = None
        reason = "independent exact target mismatch"
        try:
            if proposal.parent_body_digest != exact_body_digest(parent):
                raise ScalableTaskError("proposal is stale for the current parent")
            if len(proposal.operations) > budget.max_trace_depth:
                raise ScalableTaskError("proposal exceeds the trace-depth budget")
            candidate, trace = build_rewrite_trace(parent, proposal.operations)
            if candidate.n_states > budget.max_states:
                raise ScalableTaskError("proposal exceeds the state budget")
            exact, witness = hidden_task.evaluator._evaluate_exact(candidate)
            accepted = exact and witness is None
            if accepted:
                reason = "independent exact target match"
        except (RewriteError, ScalableTaskError, ValueError) as exc:
            accepted = False
            reason = str(exc)

        attempts.append(
            IndependentValidationAttempt(
                proposal_digest=proposal.digest(),
                template_id=proposal.template_id,
                accepted=accepted,
                reason=reason,
                candidate_body_digest=(
                    None if candidate is None else exact_body_digest(candidate)
                ),
            )
        )
        remaining = len(search.proposals) - index - 1
        decision = policy.decide(
            accepted=accepted,
            attempts=len(attempts),
            remaining=remaining,
            search_status=search.status,
            budget=budget,
        )
        if decision.action is StopAction.ADOPT:
            if candidate is None or trace is None:
                raise ScalableTaskError(
                    "accepted independent validation lacks a candidate trace"
                )
            outcome = SearchOutcome(
                arm=ControlArm.COMPLETE,
                status=SearchStatus.FOUND,
                budget=budget.search_budget(),
                nodes_seen=max(1, search.generated_candidates),
                paths_considered=search.generated_candidates,
                maximum_depth_reached=len(trace.steps),
                trace=trace,
                final_behaviour_digest=mealy_digest(candidate, minimise=True),
            )
            task = AdmittedConstructiveTask(
                public=hidden_task.public,
                incapacity=hidden_task.incapacity,
                constructive_outcome=outcome,
                controls=(),
                target_minimal_states=hidden_task.target_minimal_states,
                evaluator=hidden_task.evaluator,
            )
            return IndependentSelectionResult(
                decision, tuple(attempts), proposal, task
            )
        if decision.action is not StopAction.CONTINUE:
            return IndependentSelectionResult(
                decision, tuple(attempts), None, None
            )

    decision = policy.decide(
        accepted=False,
        attempts=len(attempts),
        remaining=0,
        search_status=search.status,
        budget=budget,
    )
    return IndependentSelectionResult(decision, tuple(attempts), None, None)


__all__ = [
    "HiddenScalableTask",
    "IndependentSelectionResult",
    "IndependentValidationAttempt",
    "ProposalStopPolicy",
    "ScalableTaskError",
    "StopAction",
    "StopDecision",
    "build_hidden_scalable_task",
    "validate_ranked_proposals_independently",
]
