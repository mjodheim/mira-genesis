"""Data contracts and exact certificates for M043 qualification gate Q3."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from typing import Sequence

from metamorphosis.m043_mealy import (
    MealyMachine,
    Word,
    exact_mealy_equivalence,
    mealy_digest,
    minimize_mealy,
)
from metamorphosis.m043_rewrite import (
    RewriteTrace,
    exact_body_digest,
    trace_digest,
)


class TaskQualificationError(ValueError):
    """Raised when a Q3 task, budget or control surface is malformed."""


class OperationKind(str, Enum):
    DUPLICATE = "duplicate"
    REPLACE_EMISSION = "replace_emission"
    REDIRECT_TRANSITION = "redirect_transition"


class SearchStatus(str, Enum):
    FOUND = "found"
    EXHAUSTED = "exhausted"
    DEPTH_LIMIT_REACHED = "depth_limit_reached"
    NODE_BUDGET_EXHAUSTED = "node_budget_exhausted"


class CatalogueStatus(str, Enum):
    QUALIFIED = "qualified"
    INSUFFICIENT = "insufficient"


class ControlArm(str, Enum):
    COMPLETE = "complete"
    FRESH = "fresh"
    UNCHANGED_PARENT = "unchanged_parent"
    OUTPUT_ONLY = "output_only"
    LEARNING_STATE_ABLATED = "learning_state_ablated"
    TOOL_ABLATED = "tool_ablated"


@dataclass(frozen=True)
class SearchBudget:
    max_depth: int = 2
    max_nodes: int = 512
    max_states: int = 8

    def __post_init__(self) -> None:
        for field_name, value in (
            ("max_depth", self.max_depth),
            ("max_nodes", self.max_nodes),
            ("max_states", self.max_states),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise TaskQualificationError(
                    f"{field_name} must be a positive integer"
                )

    def to_dict(self) -> dict[str, int]:
        return {
            "max_depth": self.max_depth,
            "max_nodes": self.max_nodes,
            "max_states": self.max_states,
        }


@dataclass(frozen=True)
class SearchCapabilities:
    arm: ControlArm
    allowed: tuple[OperationKind, ...]
    priority: tuple[OperationKind, ...]
    composed_split_tool: bool
    learning_state_active: bool

    def __post_init__(self) -> None:
        if len(set(self.allowed)) != len(self.allowed):
            raise TaskQualificationError("allowed operation kinds must be unique")
        if set(self.priority) != set(self.allowed):
            raise TaskQualificationError(
                "priority must order every allowed operation kind"
            )

    def causal_surface(self) -> tuple[object, ...]:
        return (
            self.allowed,
            self.priority,
            self.composed_split_tool,
            self.learning_state_active,
        )


def control_capabilities() -> dict[ControlArm, SearchCapabilities]:
    default = (
        OperationKind.REPLACE_EMISSION,
        OperationKind.REDIRECT_TRANSITION,
        OperationKind.DUPLICATE,
    )
    learned = (
        OperationKind.DUPLICATE,
        OperationKind.REPLACE_EMISSION,
        OperationKind.REDIRECT_TRANSITION,
    )
    all_kinds = default
    return {
        ControlArm.COMPLETE: SearchCapabilities(
            ControlArm.COMPLETE, all_kinds, learned, True, True
        ),
        ControlArm.FRESH: SearchCapabilities(
            ControlArm.FRESH, all_kinds, default, False, False
        ),
        ControlArm.UNCHANGED_PARENT: SearchCapabilities(
            ControlArm.UNCHANGED_PARENT, (), (), False, False
        ),
        ControlArm.OUTPUT_ONLY: SearchCapabilities(
            ControlArm.OUTPUT_ONLY,
            (OperationKind.REPLACE_EMISSION,),
            (OperationKind.REPLACE_EMISSION,),
            False,
            False,
        ),
        ControlArm.LEARNING_STATE_ABLATED: SearchCapabilities(
            ControlArm.LEARNING_STATE_ABLATED, all_kinds, default, True, False
        ),
        ControlArm.TOOL_ABLATED: SearchCapabilities(
            ControlArm.TOOL_ABLATED, all_kinds, learned, False, True
        ),
    }


def validate_control_surfaces(
    surfaces: dict[ControlArm, SearchCapabilities], budget: SearchBudget
) -> None:
    if set(surfaces) != set(ControlArm):
        raise TaskQualificationError("all six Q3 control arms are required")
    seen: dict[tuple[object, ...], ControlArm] = {}
    for arm in ControlArm:
        capability = surfaces[arm]
        if capability.arm is not arm:
            raise TaskQualificationError(
                "control capability is registered under the wrong arm"
            )
        surface = capability.causal_surface()
        if surface in seen:
            raise TaskQualificationError(
                f"control surfaces collapse: {seen[surface].value} and {arm.value}"
            )
        seen[surface] = arm
    if not isinstance(budget, SearchBudget):
        raise TaskQualificationError("controls require one shared SearchBudget")


@dataclass(frozen=True)
class StructuralIncapacityCertificate:
    parent_exact_digest: str
    parent_behaviour_digest: str
    target_behaviour_digest: str
    parent_physical_states: int
    parent_minimal_states: int
    target_minimal_states: int
    required_growth: int
    theorem: str = "minimal-target-state-count-exceeds-declared-parent-capacity"

    def to_dict(self) -> dict[str, object]:
        return {
            "theorem": self.theorem,
            "parent_exact_digest": self.parent_exact_digest,
            "parent_behaviour_digest": self.parent_behaviour_digest,
            "target_behaviour_digest": self.target_behaviour_digest,
            "parent_physical_states": self.parent_physical_states,
            "parent_minimal_states": self.parent_minimal_states,
            "target_minimal_states": self.target_minimal_states,
            "required_growth": self.required_growth,
        }


def prove_structural_incapacity(
    parent: MealyMachine, target: MealyMachine
) -> StructuralIncapacityCertificate:
    if parent.input_alphabet != target.input_alphabet:
        raise TaskQualificationError("parent and target input alphabets differ")
    if parent.output_alphabet != target.output_alphabet:
        raise TaskQualificationError("parent and target output alphabets differ")
    canonical_parent = minimize_mealy(parent)
    if canonical_parent != parent:
        raise TaskQualificationError(
            "the declared parent must already be canonical, reachable and minimal"
        )
    target_minimal = minimize_mealy(target).n_states
    if target_minimal <= parent.n_states:
        raise TaskQualificationError(
            "target does not exceed the declared parent's exact state capacity"
        )
    return StructuralIncapacityCertificate(
        parent_exact_digest=exact_body_digest(parent),
        parent_behaviour_digest=mealy_digest(parent, minimise=True),
        target_behaviour_digest=mealy_digest(target, minimise=True),
        parent_physical_states=parent.n_states,
        parent_minimal_states=canonical_parent.n_states,
        target_minimal_states=target_minimal,
        required_growth=target_minimal - parent.n_states,
    )


class HiddenTargetEvaluator:
    """Evaluator-side target holder exposing observations, never a body mapping."""

    __slots__ = ("__target", "_observations", "observation_limit")

    def __init__(self, target: MealyMachine, *, observation_limit: int = 64) -> None:
        if (
            isinstance(observation_limit, bool)
            or not isinstance(observation_limit, int)
            or observation_limit <= 0
        ):
            raise TaskQualificationError(
                "observation_limit must be a positive integer"
            )
        self.__target = target
        self._observations = 0
        self.observation_limit = observation_limit

    @property
    def target_commitment(self) -> str:
        return mealy_digest(self.__target, minimise=True)

    def observe(self, word: Sequence[int]) -> tuple[int, ...]:
        if self._observations >= self.observation_limit:
            raise TaskQualificationError("hidden-task observation budget exhausted")
        self._observations += 1
        return self.__target.transduce(word)

    def _evaluate_exact(self, candidate: MealyMachine) -> tuple[bool, Word | None]:
        return exact_mealy_equivalence(candidate, self.__target)


@dataclass(frozen=True)
class PublicTaskView:
    schema: str
    task_id: str
    parent_exact_digest: str
    target_commitment: str
    input_alphabet: tuple[int, ...]
    output_alphabet: tuple[int, ...]
    observation_limit: int
    search_budget: SearchBudget

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "task_id": self.task_id,
            "parent_exact_digest": self.parent_exact_digest,
            "target_commitment": self.target_commitment,
            "input_alphabet": list(self.input_alphabet),
            "output_alphabet": list(self.output_alphabet),
            "observation_limit": self.observation_limit,
            "search_budget": self.search_budget.to_dict(),
        }


@dataclass(frozen=True)
class SearchOutcome:
    arm: ControlArm
    status: SearchStatus
    budget: SearchBudget
    nodes_seen: int
    paths_considered: int
    maximum_depth_reached: int
    trace: RewriteTrace | None
    final_behaviour_digest: str | None

    @property
    def exact(self) -> bool:
        return self.status is SearchStatus.FOUND

    def to_dict(self, *, include_trace_identity: bool = True) -> dict[str, object]:
        value: dict[str, object] = {
            "arm": self.arm.value,
            "status": self.status.value,
            "budget": self.budget.to_dict(),
            "nodes_seen": self.nodes_seen,
            "paths_considered": self.paths_considered,
            "maximum_depth_reached": self.maximum_depth_reached,
            "exact": self.exact,
            "final_behaviour_digest": self.final_behaviour_digest,
        }
        if include_trace_identity:
            value["trace_digest"] = (
                None if self.trace is None else trace_digest(self.trace)
            )
        return value


@dataclass(frozen=True)
class AdmittedConstructiveTask:
    public: PublicTaskView
    incapacity: StructuralIncapacityCertificate
    constructive_outcome: SearchOutcome
    controls: tuple[SearchOutcome, ...]
    target_minimal_states: int
    evaluator: HiddenTargetEvaluator = field(repr=False, compare=False)

    def evaluator_mapping(self) -> dict[str, object]:
        return {
            "public": self.public.to_dict(),
            "incapacity": self.incapacity.to_dict(),
            "constructive_outcome": self.constructive_outcome.to_dict(),
            "controls": [control.to_dict() for control in self.controls],
            "target_minimal_states": self.target_minimal_states,
            "target_table_exposed_to_public_surface": False,
            "witness_trace_exposed_to_public_surface": False,
        }

    def digest(self) -> str:
        body = json.dumps(
            self.evaluator_mapping(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(
            b"m043-q3-admitted-task-v1\x00" + body
        ).hexdigest()


@dataclass(frozen=True)
class CatalogueResult:
    status: CatalogueStatus
    entries: tuple[AdmittedConstructiveTask, ...]
    candidates_considered: int
    rejection_reasons: tuple[str, ...]
    minimum_entries: int
    maximum_candidates: int

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "entry_count": len(self.entries),
            "entry_digests": [entry.digest() for entry in self.entries],
            "candidates_considered": self.candidates_considered,
            "rejection_reasons": list(self.rejection_reasons),
            "minimum_entries": self.minimum_entries,
            "maximum_candidates": self.maximum_candidates,
            "explicit_negative_termination": (
                self.status is CatalogueStatus.INSUFFICIENT
            ),
            "no_selected_seed": True,
            "no_canonical_workflow": True,
        }
