"""Least-privilege action admission for every Mira body."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

from mira_core.contracts import Action


class Authority(StrEnum):
    COMPUTE = "compute"
    EPHEMERAL_MEMORY = "ephemeral_memory"
    PERSISTENT_MEMORY = "persistent_memory"
    FILESYSTEM_READ = "filesystem_read"
    FILESYSTEM_WRITE = "filesystem_write"
    NETWORK = "network"
    REPOSITORY_WRITE = "repository_write"
    CREDENTIAL = "credential"
    DEPLOYMENT = "deployment"
    PERMISSION_CHANGE = "permission_change"
    PHYSICAL_ACTUATION = "physical_actuation"


HIGH_IMPACT_AUTHORITIES = frozenset({
    Authority.NETWORK,
    Authority.REPOSITORY_WRITE,
    Authority.CREDENTIAL,
    Authority.DEPLOYMENT,
    Authority.PERMISSION_CHANGE,
    Authority.PHYSICAL_ACTUATION,
})


@dataclass(frozen=True)
class SafetyDecision:
    allowed: bool
    reason: str
    missing_authorities: tuple[str, ...] = ()
    human_release_required: bool = False


@dataclass(frozen=True)
class SafetyPolicy:
    """An immutable authority set; no action can expand it from inside the agent loop."""

    granted: frozenset[Authority] = frozenset({Authority.COMPUTE, Authority.EPHEMERAL_MEMORY})
    require_human_release_for_high_impact: bool = True

    @classmethod
    def from_authorities(cls, authorities: Iterable[Authority]) -> "SafetyPolicy":
        return cls(frozenset(authorities))

    def decide(self, action: Action) -> SafetyDecision:
        try:
            required = frozenset(Authority(value) for value in action.required_authorities)
        except ValueError as exc:
            return SafetyDecision(False, f"unknown authority: {exc}")
        missing = tuple(sorted(authority.value for authority in required - self.granted))
        if missing:
            return SafetyDecision(False, "required authority was not granted", missing)
        high_impact = bool(required & HIGH_IMPACT_AUTHORITIES)
        if high_impact and self.require_human_release_for_high_impact:
            return SafetyDecision(
                False,
                "high-impact action requires a separate authenticated human release",
                human_release_required=True,
            )
        return SafetyDecision(True, "action is inside the immutable authority envelope")

    def can_expand_to(self, proposed: Iterable[Authority]) -> bool:
        """Agents may reduce authority for descendants, never grant themselves more."""
        return frozenset(proposed) <= self.granted
