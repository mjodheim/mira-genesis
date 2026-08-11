"""A wiring control for the M085 domain shim. **Not scientific evidence.**

M075 ran a zero-token wiring control before spending a single model call, for the same reason this
exists: an instrument that has never been exercised end to end will fail on the day it matters, and
the failure will be indistinguishable from a result.

This is a toy in-memory domain that satisfies `m085-domain-adapter-v1` and knows nothing about M084 —
no carriers named `sealed-`, no palette, no grid, no substrate. Driving M084's organism through it
proves the contract is satisfiable from the outside and that the organism's ten former couplings are
genuinely rerouted.

**It proves nothing about transfer, and it is not a domain of the M085 bank.** It is written by this
project, which is exactly what the M085 boundary exists to exclude. The readiness gate does not
consult it, no result cites it, and running it changes no register.
"""
from __future__ import annotations

from typing import Mapping, Sequence

from metamorphosis.m085_cross_domain_intake import ADAPTER_CONTRACT_VERSION
from metamorphosis.m085_domain_shim import DomainDescription

# Deliberately unlike anything in M084: numeric slot names, a colour-word alphabet, and a rejection
# rule that is a numeric range rather than a name prefix.
SLOTS = tuple(f"slot{index}" for index in range(9))
VALUES = ("amber", "indigo", "olive", "rust")
DISCARDING_SLOTS = frozenset({"slot7", "slot8"})

# The discarding slot must be the *cheapest* in its group, or a cost-minimising planner routes
# around it and the repair path never runs. A first version of this control derived costs from a
# modulo of the slot index, which made the trap expensive: every goal passed, no probe or repair
# happened, and the control reported success while exercising none of what it exists to exercise.
CARRIER_COSTS = {
    "slot0": 3, "slot1": 5, "slot2": 2, "slot3": 5, "slot4": 2,
    "slot5": 3, "slot6": 3, "slot7": 1, "slot8": 1,
}


class WiringControlDomain:
    """An in-memory domain. Accepts writes to its discarding slots and silently drops them."""

    domain_id = "wiring-control-not-a-bank-domain"

    def __init__(self) -> None:
        self._state: dict[str, str] = {}
        self.closed = False

    def describe(self) -> DomainDescription:
        return DomainDescription(
            contract_version=ADAPTER_CONTRACT_VERSION,
            carriers=dict(CARRIER_COSTS),
            values=VALUES,
            probe_carriers={
                "probe_trap": "slot7",
                "probe_alt": "slot5",
                "probe_aff": "slot6",
                "seeded": "slot4",
            },
        )

    def observe(self, carriers: Sequence[str]) -> dict[str, str | None]:
        return {name: self._state.get(name) for name in carriers}

    def act(self, kind: str, carrier: str, value: str = "") -> bool:
        """Reports success for a discarded write, which is the behaviour under test."""

        if kind == "put":
            if carrier not in DISCARDING_SLOTS:
                self._state[carrier] = value
            return True
        if kind == "remove":
            self._state.pop(carrier, None)
            return True
        return True

    def evaluate(self, goal_group: Sequence[str], requirement: str, value: str) -> bool:
        """Evaluator-owned, from domain state. The organism never calls this."""

        if requirement == "durable":
            return any(self._state.get(name) == value for name in goal_group)
        return all(self._state.get(name) is None for name in goal_group)

    def close(self) -> None:
        self.closed = True


def wiring_tasks() -> tuple[dict[str, object], ...]:
    """Four tasks in the shape the contract describes. Goals only — no decomposition."""

    return (
        {
            "kind": "repair", "requirement": "durable",
            "group": ("slot7", "slot0", "slot1"), "value": "amber", "reachable": True,
        },
        {
            "kind": "clear", "requirement": "absent",
            "group": ("slot4",), "value": "", "reachable": True,
        },
        {
            "kind": "control", "requirement": "durable",
            "group": ("slot2", "slot3"), "value": "indigo", "reachable": True,
        },
        {
            "kind": "unreachable", "requirement": "durable",
            "group": ("slot8",), "value": "olive", "reachable": False,
        },
    )


def expected_shape() -> Mapping[str, int]:
    """What a correctly wired organism does here, so a silent misrouting is not read as a result."""

    return {
        "reachable_goals": 3,
        "unreachable_goals": 1,
        # A control that walks around the trap proves nothing about the repair path.
        "minimum_diagnostic_probes": 1,
        "minimum_repair_cycles": 1,
    }
