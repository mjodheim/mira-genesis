"""Stable contracts shared by Mira policies, bodies and evaluators."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol, Sequence, runtime_checkable


JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


@dataclass(frozen=True)
class Goal:
    goal_id: str
    instruction: str
    success_criteria: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.goal_id or not self.instruction.strip():
            raise ValueError("a Mira goal requires a stable identifier and instruction")


@dataclass(frozen=True)
class Action:
    action_id: str
    kind: str
    payload: Mapping[str, JsonValue] = field(default_factory=dict)
    required_authorities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.action_id or not self.kind:
            raise ValueError("a Mira action requires an identifier and kind")
        if len(set(self.required_authorities)) != len(self.required_authorities):
            raise ValueError("action authorities must be unique")


@dataclass(frozen=True)
class Observation:
    observation_id: str
    state: Mapping[str, JsonValue]
    terminal: bool = False
    success: bool = False
    error: str | None = None

    def __post_init__(self) -> None:
        if not self.observation_id:
            raise ValueError("an observation requires an identifier")
        if self.success and not self.terminal:
            raise ValueError("a successful observation must be terminal")


@runtime_checkable
class Body(Protocol):
    @property
    def body_id(self) -> str: ...

    def reset(self, goal: Goal) -> Observation: ...

    def act(self, action: Action) -> Observation: ...


@runtime_checkable
class AuthorityAwareBody(Protocol):
    """Optional body contract preventing policies from under-declaring action authority."""

    def required_authorities(self, action: Action) -> tuple[str, ...]: ...


@runtime_checkable
class Policy(Protocol):
    @property
    def policy_id(self) -> str: ...

    def propose(
        self, goal: Goal, observation: Observation, history: Sequence[Mapping[str, JsonValue]],
    ) -> Action | None: ...
