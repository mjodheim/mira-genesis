"""Drive an externally supplied domain with M084's organism.

M084's `Embodiment` abstracted acting and observing. Building this shim showed that was the smaller
half: the organism also reached into M084's own carrier tables for costs, for the integer keys its
bounded memory needs, for the carriers it probes with, and for its value alphabet — ten call sites in
all, none of which an externally written domain supplies.

M084 now routes every one of those through a registered `DomainView`, and this module builds such a
view from a domain that satisfies `m085-domain-adapter-v1`. Nothing about M084's recorded behaviour
changes: its three substrates register views built from the tables they already used, and every arm
re-derives its preserved numbers exactly.

The organism is imported, not reimplemented. The point of M085 is to find out whether *that* organism
transfers, so a second one written here would answer nothing.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence, runtime_checkable

from metamorphosis.m084_persistent_lineage import (
    DomainView,
    Embodiment,
    Goal,
    LineageError,
    register_domain_view,
)
from metamorphosis.m085_cross_domain_intake import ADAPTER_CONTRACT_VERSION

ACTION_KINDS = ("put", "remove", "read", "list")
REQUIRED_PROBE_ROLES = ("probe_trap", "probe_alt", "probe_aff", "seeded")


class DomainContractError(LineageError):
    """Raised when a supplied domain does not satisfy the published adapter contract."""


@runtime_checkable
class ExternalDomain(Protocol):
    """What a maintainer's domain must expose. Deliberately four methods and no more."""

    domain_id: str

    def describe(self) -> "DomainDescription": ...
    def observe(self, carriers: Sequence[str]) -> dict[str, str | None]: ...
    def act(self, kind: str, carrier: str, value: str) -> bool: ...
    def close(self) -> None: ...


@dataclass(frozen=True)
class DomainDescription:
    """Everything the organism needs that is not acting or observing.

    Each field exists because the organism reached for M084's own tables to get it. Naming them here
    is what turns an implicit dependency on one project's environments into a contract an outsider
    can satisfy.
    """

    contract_version: str
    carriers: Mapping[str, int]
    values: tuple[str, ...]
    probe_carriers: Mapping[str, str]
    observes_one_carrier_at_a_time: bool = False

    def validate(self) -> None:
        if self.contract_version != ADAPTER_CONTRACT_VERSION:
            raise DomainContractError(
                f"domain declares contract {self.contract_version!r}, "
                f"but this organism drives {ADAPTER_CONTRACT_VERSION!r}"
            )
        if not self.carriers:
            raise DomainContractError("a domain must declare at least one carrier")
        for name, cost in self.carriers.items():
            if not isinstance(name, str) or not name:
                raise DomainContractError("carrier names must be non-empty strings")
            if not isinstance(cost, int) or isinstance(cost, bool) or cost < 1:
                raise DomainContractError(f"carrier {name!r} has no positive cost")
        if not self.values or any(not isinstance(v, str) or not v for v in self.values):
            raise DomainContractError("a domain must declare a non-empty value alphabet")
        missing = [role for role in REQUIRED_PROBE_ROLES if role not in self.probe_carriers]
        if missing:
            raise DomainContractError(
                f"domain does not nominate carriers for {', '.join(missing)}; the organism probes "
                "with these and cannot invent them"
            )
        unknown = [
            name for name in self.probe_carriers.values() if name not in self.carriers
        ]
        if unknown:
            raise DomainContractError(
                f"probe carriers {sorted(unknown)} are not among the declared carriers"
            )


def view_from_description(
    domain_id: str, context: int, description: DomainDescription,
) -> DomainView:
    """Turn a validated description into the view M084's organism consults."""

    description.validate()
    if not isinstance(context, int) or isinstance(context, bool) or context < 0:
        raise DomainContractError("a domain context must be a non-negative integer")

    carrier_index = {name: index for index, name in enumerate(sorted(description.carriers))}
    probes = dict(description.probe_carriers)
    values = tuple(description.values)

    def carrier_for(_stage: int, role: str) -> str:
        if role not in probes:
            raise DomainContractError(f"domain nominates no carrier for the {role!r} role")
        return probes[role]

    def value_for(salt: bytes, stage: int, tag: int) -> str:
        digest = hashlib.sha256(
            salt + domain_id.encode("utf-8")
            + stage.to_bytes(4, "big") + tag.to_bytes(4, "big"),
        ).digest()
        return values[int.from_bytes(digest[:2], "big") % len(values)]

    return DomainView(
        key=domain_id,
        context=context,
        costs=dict(description.carriers),
        carrier_index=carrier_index,
        observes_one_carrier_at_a_time=description.observes_one_carrier_at_a_time,
        carrier_for=carrier_for,
        value_for=value_for,
    )


class ExternalEmbodiment(Embodiment):
    """M084's embodiment over a domain that knows nothing about M084.

    `Embodiment` counts actions and reads and enforces the budget; all of that is inherited. Only
    the two calls that reached into an M081/M082/M083 environment are redirected.
    """

    def __init__(self, domain: ExternalDomain, *, context: int) -> None:
        description = domain.describe()
        register_domain_view(view_from_description(domain.domain_id, context, description))
        super().__init__(domain, domain.domain_id)
        self.description = description

    def observe(self, carriers: Sequence[str]) -> dict[str, str | None]:
        self.state_reads += 1
        return self.environment.observe(list(dict.fromkeys(carriers)))

    def act(self, kind: str, carrier: str, value: str = "") -> bool:
        if kind not in ACTION_KINDS:
            raise DomainContractError(f"unknown action {kind!r}")
        self.actions += 1
        if self.actions > self.action_budget:
            raise LineageError(
                f"stage exceeded the frozen {self.action_budget}-action safety bound"
            )
        return self.environment.act(kind, carrier, value)


def goals_from_domain(
    domain_id: str, stage: int, tasks: Sequence[Mapping[str, object]],
) -> tuple[Goal, ...]:
    """Convert a maintainer's task list into goals the organism can pursue.

    `reachable` is the evaluator's ground truth and is carried here only so the harness can score.
    `Goal.redacted()` is what the organism sees, and it does not include it.
    """

    goals: list[Goal] = []
    for index, task in enumerate(tasks):
        required = {"requirement", "group", "value", "reachable"}
        if set(task) < required:
            raise DomainContractError(
                f"task {index} of {domain_id!r} is missing {sorted(required - set(task))}"
            )
        requirement = str(task["requirement"])
        if requirement not in ("durable", "absent"):
            raise DomainContractError(f"task {index} has unknown requirement {requirement!r}")
        group = tuple(str(name) for name in task["group"])  # type: ignore[union-attr]
        if not group:
            raise DomainContractError(f"task {index} names no carriers")
        goals.append(Goal(
            stage=stage, index=index, kind=str(task.get("kind", "external")),
            requirement=requirement, group=group, value=str(task["value"]),
            reachable=bool(task["reachable"]),
        ))
    return tuple(goals)
