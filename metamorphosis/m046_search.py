"""Resource-bounded heuristic proposal generation for M046.

This module is intentionally target-blind beyond the public observation interface.  It
never calls exact equivalence and never receives a hidden target body or witness trace.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import time
from typing import Sequence

from metamorphosis.m043_mealy import MealyMachine
from metamorphosis.m043_rewrite import (
    DuplicateReachableTarget,
    ReplaceEmission,
    RewriteError,
    RewriteOperation,
    apply_rewrite,
    build_rewrite_trace,
    exact_body_digest,
    reachable_states,
)
from metamorphosis.m043_task_model import HiddenTargetEvaluator, SearchBudget


class ScalableSearchError(ValueError):
    """Raised when an M046 search contract or resource bound is violated."""


class ProposalSearchStatus(str, Enum):
    READY = "ready"
    INSUFFICIENT_OBSERVATIONS = "insufficient_observations"
    RESOURCE_BUDGET_EXHAUSTED = "resource_budget_exhausted"


@dataclass(frozen=True)
class ScalableResourceBudget:
    max_observations: int = 128
    max_generated_candidates: int = 48
    max_validation_attempts: int = 8
    max_trace_depth: int = 3
    max_states: int = 10
    max_working_memory_bytes: int = 262_144
    max_causal_memory_bytes: int = 262_144
    max_search_seconds: float = 30.0

    def __post_init__(self) -> None:
        integer_fields = (
            ("max_observations", self.max_observations),
            ("max_generated_candidates", self.max_generated_candidates),
            ("max_validation_attempts", self.max_validation_attempts),
            ("max_trace_depth", self.max_trace_depth),
            ("max_states", self.max_states),
            ("max_working_memory_bytes", self.max_working_memory_bytes),
            ("max_causal_memory_bytes", self.max_causal_memory_bytes),
        )
        for name, value in integer_fields:
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ScalableSearchError(f"{name} must be a positive integer")
        if (
            isinstance(self.max_search_seconds, bool)
            or not isinstance(self.max_search_seconds, (int, float))
            or self.max_search_seconds <= 0
        ):
            raise ScalableSearchError("max_search_seconds must be positive")
        if self.max_trace_depth < 2:
            raise ScalableSearchError("M046 requires room for capacity growth and specialisation")

    def search_budget(self) -> SearchBudget:
        return SearchBudget(
            max_depth=self.max_trace_depth,
            max_nodes=self.max_generated_candidates,
            max_states=self.max_states,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "max_observations": self.max_observations,
            "max_generated_candidates": self.max_generated_candidates,
            "max_validation_attempts": self.max_validation_attempts,
            "max_trace_depth": self.max_trace_depth,
            "max_states": self.max_states,
            "max_working_memory_bytes": self.max_working_memory_bytes,
            "max_causal_memory_bytes": self.max_causal_memory_bytes,
            "max_search_seconds": self.max_search_seconds,
        }


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def _digest(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + _canonical_json(value)).hexdigest()


@dataclass(frozen=True)
class ProposalEpisode:
    task_id: str
    outcome: str
    selected_template: str | None
    exact_rejected_templates: tuple[str, ...]
    dominated_templates: tuple[str, ...]
    generated_candidates: int
    validation_attempts: int
    reason: str

    def __post_init__(self) -> None:
        if self.outcome not in {"accepted", "insufficient_evidence"}:
            raise ScalableSearchError("unsupported proposal episode outcome")
        if self.generated_candidates < 0 or self.validation_attempts < 0:
            raise ScalableSearchError("proposal episode counters must be non-negative")

    def to_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "outcome": self.outcome,
            "selected_template": self.selected_template,
            "exact_rejected_templates": list(self.exact_rejected_templates),
            "dominated_templates": list(self.dominated_templates),
            "generated_candidates": self.generated_candidates,
            "validation_attempts": self.validation_attempts,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class CausalProposalMemory:
    episodes: tuple[ProposalEpisode, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "m046-causal-proposal-memory-v1",
            "episodes": [episode.to_dict() for episode in self.episodes],
        }

    def to_bytes(self) -> bytes:
        return _canonical_json(self.to_dict())

    def digest(self) -> str:
        return hashlib.sha256(
            b"m046-causal-proposal-memory-v1\x00" + self.to_bytes()
        ).hexdigest()

    def append(
        self, episode: ProposalEpisode, *, maximum_bytes: int
    ) -> "CausalProposalMemory":
        updated = CausalProposalMemory(self.episodes + (episode,))
        if len(updated.to_bytes()) > maximum_bytes:
            raise ScalableSearchError("causal proposal memory budget exhausted")
        return updated

    def template_bias(self, template_id: str) -> int:
        successes = 0
        exact_rejections = 0
        dominated = 0
        for episode in self.episodes:
            if (
                episode.outcome == "accepted"
                and episode.selected_template == template_id
            ):
                successes += 1
            exact_rejections += episode.exact_rejected_templates.count(template_id)
            dominated += episode.dominated_templates.count(template_id)
        return successes * 25 - exact_rejections * 30 - dominated

    def has_success(self, template_id: str) -> bool:
        return any(
            episode.outcome == "accepted"
            and episode.selected_template == template_id
            for episode in self.episodes
        )

    @property
    def accepted_episodes(self) -> int:
        return sum(episode.outcome == "accepted" for episode in self.episodes)

    @property
    def failure_evidence_count(self) -> int:
        return sum(
            len(episode.exact_rejected_templates)
            + len(episode.dominated_templates)
            + (1 if episode.outcome == "insufficient_evidence" else 0)
            for episode in self.episodes
        )


@dataclass(frozen=True)
class DiagnosticObservation:
    entry_state: int
    entry_symbol: int
    probe_symbol: int
    word: tuple[int, ...]
    parent_output: tuple[int, ...]
    target_output: tuple[int, ...]

    @property
    def direct_last_mismatch(self) -> bool:
        return (
            len(self.parent_output) == len(self.target_output)
            and bool(self.parent_output)
            and self.parent_output[:-1] == self.target_output[:-1]
            and self.parent_output[-1] != self.target_output[-1]
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "entry_state": self.entry_state,
            "entry_symbol": self.entry_symbol,
            "probe_symbol": self.probe_symbol,
            "word": list(self.word),
            "parent_output": list(self.parent_output),
            "target_output": list(self.target_output),
            "direct_last_mismatch": self.direct_last_mismatch,
        }


@dataclass(frozen=True)
class HeuristicProposal:
    template_id: str
    operations: tuple[RewriteOperation, ...]
    parent_body_digest: str
    final_body_digest: str
    score_matches: int
    score_total: int
    memory_bias: int
    evidence_words: tuple[tuple[int, ...], ...]

    def __post_init__(self) -> None:
        if self.score_total <= 0 or not 0 <= self.score_matches <= self.score_total:
            raise ScalableSearchError("invalid proposal observation score")
        if not self.operations:
            raise ScalableSearchError("proposal must contain at least one operation")

    @property
    def ranking_score(self) -> int:
        return (self.score_matches * 1000) // self.score_total + self.memory_bias

    def to_dict(self) -> dict[str, object]:
        return {
            "template_id": self.template_id,
            "operations": [operation.to_dict() for operation in self.operations],
            "parent_body_digest": self.parent_body_digest,
            "final_body_digest": self.final_body_digest,
            "score_matches": self.score_matches,
            "score_total": self.score_total,
            "memory_bias": self.memory_bias,
            "ranking_score": self.ranking_score,
            "evidence_words": [list(word) for word in self.evidence_words],
        }

    def digest(self) -> str:
        return _digest(b"m046-heuristic-proposal-v1\x00", self.to_dict())


@dataclass(frozen=True)
class ProposalSearchResult:
    status: ProposalSearchStatus
    observations: tuple[DiagnosticObservation, ...]
    proposals: tuple[HeuristicProposal, ...]
    generated_candidates: int
    invalid_candidates: int
    candidate_space_lower_bound: int
    exploration_fraction_ppm: int
    reused_causal_memory: bool
    working_memory_bytes: int
    time_budget_respected: bool
    complete_candidate_space_enumerated: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "observation_count": len(self.observations),
            "direct_mismatch_count": sum(
                observation.direct_last_mismatch
                for observation in self.observations
            ),
            "proposal_digests": [proposal.digest() for proposal in self.proposals],
            "generated_candidates": self.generated_candidates,
            "invalid_candidates": self.invalid_candidates,
            "candidate_space_lower_bound": self.candidate_space_lower_bound,
            "exploration_fraction_ppm": self.exploration_fraction_ppm,
            "reused_causal_memory": self.reused_causal_memory,
            "working_memory_bytes": self.working_memory_bytes,
            "time_budget_respected": self.time_budget_respected,
            "complete_candidate_space_enumerated": self.complete_candidate_space_enumerated,
        }

    def digest(self) -> str:
        return _digest(b"m046-proposal-search-result-v1\x00", self.to_dict())


def _access_words(machine: MealyMachine) -> dict[int, tuple[int, ...]]:
    access: dict[int, tuple[int, ...]] = {machine.initial: ()}
    queue = deque([machine.initial])
    while queue:
        state = queue.popleft()
        prefix = access[state]
        for index, symbol in enumerate(machine.input_alphabet):
            target = machine.transitions[state][index]
            if target not in access:
                access[target] = prefix + (symbol,)
                queue.append(target)
    return access


def _diagnostic_observations(
    parent: MealyMachine,
    evaluator: HiddenTargetEvaluator,
    budget: ScalableResourceBudget,
    deadline: float,
) -> tuple[tuple[DiagnosticObservation, ...], bool]:
    observations: list[DiagnosticObservation] = []
    access = _access_words(parent)
    exhausted_time = False
    stop = False
    for state in sorted(access):
        if stop:
            break
        for entry_symbol in parent.input_alphabet:
            if stop:
                break
            for probe_symbol in parent.input_alphabet:
                if time.monotonic() > deadline:
                    exhausted_time = True
                    stop = True
                    break
                if len(observations) >= budget.max_observations:
                    stop = True
                    break
                word = access[state] + (entry_symbol, probe_symbol)
                observations.append(
                    DiagnosticObservation(
                        entry_state=state,
                        entry_symbol=entry_symbol,
                        probe_symbol=probe_symbol,
                        word=word,
                        parent_output=parent.transduce(word),
                        target_output=evaluator.observe(word),
                    )
                )
    return tuple(observations), exhausted_time


def _proposal_score(
    candidate: MealyMachine, observations: Sequence[DiagnosticObservation]
) -> tuple[int, int]:
    matches = 0
    total = 0
    for observation in observations:
        produced = candidate.transduce(observation.word)
        total += len(observation.target_output)
        matches += sum(
            left == right
            for left, right in zip(produced, observation.target_output, strict=True)
        )
    return matches, total


def _safe_duplicate_count(parent: MealyMachine) -> int:
    count = 0
    for state in sorted(reachable_states(parent)):
        for symbol in parent.input_alphabet:
            try:
                apply_rewrite(parent, DuplicateReachableTarget(state, symbol))
            except (RewriteError, ValueError):
                continue
            count += 1
    return count


def candidate_space_lower_bound(
    parent: MealyMachine, budget: ScalableResourceBudget
) -> int:
    """Count a valid depth-three subset without enumerating the complete space."""

    safe_duplicates = _safe_duplicate_count(parent)
    cells = (parent.n_states + 1) * len(parent.input_alphabet)
    alternatives = len(parent.output_alphabet) - 1
    first_edits = cells * alternatives
    second_edits_on_another_cell = max(0, cells - 1) * alternatives
    if budget.max_trace_depth < 3:
        return safe_duplicates * first_edits
    return safe_duplicates * first_edits * second_edits_on_another_cell


def _candidate_subsets(
    edits: tuple[tuple[int, int], ...], maximum_edits: int
) -> tuple[tuple[tuple[int, int], ...], ...]:
    # M046 deliberately constructs only evidence-backed single edits and the complete
    # observed edit set.  It does not enumerate the powerset or unseen output values.
    values: list[tuple[tuple[int, int], ...]] = []
    for edit in edits:
        values.append((edit,))
    if 1 < len(edits) <= maximum_edits:
        values.append(edits)
    return tuple(dict.fromkeys(values))


def heuristic_proposal_search(
    parent: MealyMachine,
    evaluator: HiddenTargetEvaluator,
    memory: CausalProposalMemory,
    budget: ScalableResourceBudget,
) -> ProposalSearchResult:
    """Generate and rank a small evidence-backed proposal set under fixed resources."""

    started = time.monotonic()
    deadline = started + float(budget.max_search_seconds)
    observations, exhausted_time = _diagnostic_observations(
        parent, evaluator, budget, deadline
    )
    direct = [
        observation
        for observation in observations
        if observation.direct_last_mismatch
    ]
    groups: dict[tuple[int, int], dict[int, int]] = {}
    evidence: dict[tuple[int, int], list[tuple[int, ...]]] = {}
    for observation in direct:
        key = (observation.entry_state, observation.entry_symbol)
        groups.setdefault(key, {})[observation.probe_symbol] = (
            observation.target_output[-1]
        )
        evidence.setdefault(key, []).append(observation.word)

    ordered_groups = sorted(
        groups.items(),
        key=lambda item: (-len(item[1]), item[0][0], item[0][1]),
    )
    proposals: list[HeuristicProposal] = []
    invalid = 0
    seen_final: set[str] = set()
    maximum_edits = budget.max_trace_depth - 1

    for (entry_state, entry_symbol), raw_edits in ordered_groups:
        if time.monotonic() > deadline:
            exhausted_time = True
            break
        edits = tuple(sorted(raw_edits.items()))
        for subset in _candidate_subsets(edits, maximum_edits):
            if len(proposals) >= budget.max_generated_candidates:
                break
            operations: tuple[RewriteOperation, ...] = (
                DuplicateReachableTarget(entry_state, entry_symbol),
            ) + tuple(
                ReplaceEmission(parent.n_states, symbol, output)
                for symbol, output in subset
            )
            try:
                candidate, trace = build_rewrite_trace(parent, operations)
            except (RewriteError, ValueError):
                invalid += 1
                continue
            if candidate.n_states > budget.max_states:
                invalid += 1
                continue
            if trace.final_body_digest in seen_final:
                continue
            seen_final.add(trace.final_body_digest)
            matches, total = _proposal_score(candidate, observations)
            template_id = f"split_emit_{len(subset)}"
            proposals.append(
                HeuristicProposal(
                    template_id=template_id,
                    operations=operations,
                    parent_body_digest=exact_body_digest(parent),
                    final_body_digest=trace.final_body_digest,
                    score_matches=matches,
                    score_total=total,
                    memory_bias=memory.template_bias(template_id),
                    evidence_words=tuple(sorted(evidence[(entry_state, entry_symbol)])),
                )
            )
        if len(proposals) >= budget.max_generated_candidates:
            break

    proposals.sort(
        key=lambda proposal: (
            -proposal.ranking_score,
            -proposal.score_matches,
            proposal.score_total,
            proposal.digest(),
        )
    )
    lower_bound = candidate_space_lower_bound(parent, budget)
    explored = len(proposals) + invalid
    fraction = (
        1_000_000
        if lower_bound <= 0
        else min(1_000_000, (explored * 1_000_000) // lower_bound)
    )
    working_bytes = len(
        _canonical_json(
            {
                "observations": [
                    observation.to_dict() for observation in observations
                ],
                "proposals": [proposal.to_dict() for proposal in proposals],
            }
        )
    )
    if working_bytes > budget.max_working_memory_bytes:
        return ProposalSearchResult(
            status=ProposalSearchStatus.RESOURCE_BUDGET_EXHAUSTED,
            observations=observations,
            proposals=(),
            generated_candidates=len(proposals),
            invalid_candidates=invalid,
            candidate_space_lower_bound=lower_bound,
            exploration_fraction_ppm=fraction,
            reused_causal_memory=False,
            working_memory_bytes=working_bytes,
            time_budget_respected=not exhausted_time,
        )

    if exhausted_time:
        status = ProposalSearchStatus.RESOURCE_BUDGET_EXHAUSTED
    elif not proposals:
        status = ProposalSearchStatus.INSUFFICIENT_OBSERVATIONS
    else:
        status = ProposalSearchStatus.READY
    reused = any(
        memory.has_success(proposal.template_id) for proposal in proposals
    )
    return ProposalSearchResult(
        status=status,
        observations=observations,
        proposals=tuple(proposals),
        generated_candidates=len(proposals),
        invalid_candidates=invalid,
        candidate_space_lower_bound=lower_bound,
        exploration_fraction_ppm=fraction,
        reused_causal_memory=reused,
        working_memory_bytes=working_bytes,
        time_budget_respected=not exhausted_time,
    )


__all__ = [
    "CausalProposalMemory",
    "DiagnosticObservation",
    "HeuristicProposal",
    "ProposalEpisode",
    "ProposalSearchResult",
    "ProposalSearchStatus",
    "ScalableResourceBudget",
    "ScalableSearchError",
    "candidate_space_lower_bound",
    "heuristic_proposal_search",
]
