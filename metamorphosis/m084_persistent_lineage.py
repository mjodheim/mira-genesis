"""One persistent lineage across four stages and three real substrates.

M076 grounded three channels, M078 refused an under-determined body, M079 planned without a supplied
decomposition, M080 acquired skills without losing earlier ones, and M081-M083 put one action
vocabulary into four real environments. Every one of those results lives in its own harness, and the
agent M081-M083 carry across their four substrates replays an action list computed by the bank
generator: it perceives nothing, plans nothing and detects no failure.

This module asks whether those mechanisms can be the faculties of **one** organism. It imports the
journal from M077, the bounded table from M080, the plan enumeration extracted from M079 and the
three environments from M081, M082 and M083. It does **not** import M081's `Agent`; importing
something that cannot perceive would be an empty citation.

The organism is serialized to a file between stages and each stage runs in a separate operating
system process, so the harness cannot quietly become the holder of the state — the defect M082 came
one design decision away from recording.
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

from metamorphosis.bounded_search import uniform_cost_plans
from metamorphosis.m077_long_horizon_recovery import GENESIS_DIGEST, Journal
from metamorphosis.m080_continual_retention import ExceptionEntry, Table
from metamorphosis.m081_two_real_environments import (
    Action,
    ShellEnvironment,
    docker_available,
)
from metamorphosis.m082_browser_environment import BrowserEnvironment
from metamorphosis.m082_browser_environment import image_present as browser_image_present
from metamorphosis.m083_gui_desktop_session import (
    DesktopEnvironment,
    PALETTE_ORDER,
)
from metamorphosis.m083_gui_desktop_session import image_present as desktop_image_present


PROTOCOL_SCHEMA = "m084-integrated-persistent-embodiment-protocol-v1"
GENERATOR_VERSION = 1

STAGE_SUBSTRATES = ("shell", "browser", "desktop", "shell")
SUBSTRATES = ("shell", "browser", "desktop")
SUBSTRATE_INDEX = {name: index for index, name in enumerate(SUBSTRATES)}
ARMS = ("lineage", "acquisition_ablated", "fresh_each_stage")
GOALS_PER_STAGE = 4
ACTION_BUDGET_PER_STAGE = 60
PLAN_BUDGET = 20
FORCED_FAULT_AFTER_STAGE = 1

# Roles are frozen; the names each role takes in each substrate are bound in PROTOCOL.json and
# re-asserted here so that a drift between the two fails rather than passes quietly.
ROLES = (
    "trap", "alt1", "alt2", "alt3", "trap_only",
    "probe_trap", "probe_alt", "probe_aff", "seeded",
)
ROLE_COSTS = {
    "trap": 1, "alt1": 3, "alt2": 2, "alt3": 5, "trap_only": 1,
    "probe_trap": 1, "probe_alt": 3, "probe_aff": 3, "seeded": 2,
}

# The shell and the browser discard names beginning with `sealed-`; that rule belongs to M081 and
# M082 and is not restated here. The durable family deliberately shares two characters with it, so
# that a lineage which induces `se` refuses its own controls and a lineage which induces the whole
# name learns nothing transferable.
_NAME_ROLE_TAGS = {
    "trap": "sealed-a", "alt1": "secure-a", "alt2": "secure-b", "alt3": "secure-c",
    "trap_only": "sealed-z", "probe_trap": "sealed-p", "probe_alt": "secure-p",
    "probe_aff": "secure-f", "seeded": "secure-d",
}
_DESKTOP_ROLE_CELLS = {
    "trap": "r3c5", "alt1": "r0c0", "alt2": "r1c2", "alt3": "r2c4",
    "trap_only": "r3c5", "probe_trap": "r3c5", "probe_alt": "r1c0",
    "probe_aff": "r2c0", "seeded": "r0c3",
}

AFFORDANCE_KEY_BASE = 1000
AFFORDANCES = ("remove",)


class LineageError(RuntimeError):
    """Raised when an organism, goal or arm contract is violated."""


class NotRunnable(RuntimeError):
    """Raised when Docker or an image is unavailable; M084 is inconclusive, not negative."""


def runnable() -> bool:
    return docker_available() and browser_image_present() and desktop_image_present()


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def _digest(salt: bytes, substrate: str, stage: int, index: int) -> bytes:
    return hashlib.sha256(
        salt + substrate.encode("utf-8") + stage.to_bytes(4, "big") + index.to_bytes(4, "big"),
    ).digest()


# --------------------------------------------------------------------------------------------
# Carriers and goals
# --------------------------------------------------------------------------------------------

def carrier_name(substrate: str, stage: int, role: str) -> str:
    if role not in ROLES:
        raise LineageError(f"unknown carrier role {role!r}")
    if substrate == "desktop":
        return _DESKTOP_ROLE_CELLS[role]
    return f"{_NAME_ROLE_TAGS[role]}{stage}"


def carrier_cost(role: str) -> int:
    return ROLE_COSTS[role]


def stage_carriers(stage: int) -> dict[str, str]:
    substrate = STAGE_SUBSTRATES[stage]
    return {role: carrier_name(substrate, stage, role) for role in ROLES}


def substrate_carrier_index(substrate: str) -> dict[str, int]:
    """A stable small integer per carrier name, so the bounded table can key on it.

    Built over every stage that uses the substrate, because the shell is entered twice with
    different names and the two visits must not collide in the table.
    """

    names: list[str] = []
    for stage, kind in enumerate(STAGE_SUBSTRATES):
        if kind != substrate:
            continue
        for role in ROLES:
            name = carrier_name(kind, stage, role)
            if name not in names:
                names.append(name)
    return {name: index for index, name in enumerate(names)}


@dataclass(frozen=True)
class Goal:
    """A desired state of a carrier group. No decomposition is supplied with it."""

    stage: int
    index: int
    kind: str
    requirement: str
    group: tuple[str, ...]
    value: str
    reachable: bool

    def commitment(self) -> str:
        return hashlib.sha256(_canonical({
            "stage": self.stage, "index": self.index, "kind": self.kind,
            "requirement": self.requirement, "group": list(self.group),
            "value": self.value, "reachable": self.reachable,
        })).hexdigest()

    def redacted(self) -> dict[str, object]:
        """What the organism is allowed to see. Reachability is evaluator-owned."""

        return {
            "requirement": self.requirement,
            "group": list(self.group),
            "value": self.value,
        }

    def satisfied_by(self, observation: Mapping[str, str | None]) -> bool:
        if self.requirement == "durable":
            return any(observation.get(name) == self.value for name in self.group)
        return all(observation.get(name) is None for name in self.group)


def build_stage_goals(salt: bytes, stage: int) -> tuple[Goal, ...]:
    substrate = STAGE_SUBSTRATES[stage]
    carriers = stage_carriers(stage)
    removal_works = substrate != "desktop"

    def value(index: int) -> str:
        digest = _digest(salt, substrate, stage, index)
        if substrate == "desktop":
            return PALETTE_ORDER[digest[0] % len(PALETTE_ORDER)]
        return f"v{int.from_bytes(digest[:2], 'big') % 1000:03d}"

    return (
        Goal(
            stage=stage, index=0, kind="repair", requirement="durable",
            group=(carriers["trap"], carriers["alt1"], carriers["alt3"]),
            value=value(0), reachable=True,
        ),
        Goal(
            stage=stage, index=1, kind="clear", requirement="absent",
            group=(carriers["seeded"],), value="", reachable=removal_works,
        ),
        Goal(
            stage=stage, index=2, kind="control", requirement="durable",
            group=(carriers["alt2"], carriers["alt3"]),
            value=value(2), reachable=True,
        ),
        Goal(
            stage=stage, index=3, kind="unreachable", requirement="durable",
            group=(carriers["trap_only"],), value=value(3), reachable=False,
        ),
    )


def build_bank(salt: bytes) -> tuple[Goal, ...]:
    bank = tuple(goal for stage in range(len(STAGE_SUBSTRATES)) for goal in build_stage_goals(salt, stage))
    if len(bank) != GOALS_PER_STAGE * len(STAGE_SUBSTRATES):
        raise LineageError("materialized bank size drifted from the frozen protocol")
    if sum(1 for goal in bank if goal.reachable) != 11:
        raise LineageError("reachable goal count drifted from the frozen protocol")
    return bank


def seed_value(salt: bytes, stage: int) -> str:
    substrate = STAGE_SUBSTRATES[stage]
    digest = _digest(salt, substrate, stage, 900)
    if substrate == "desktop":
        return PALETTE_ORDER[digest[0] % len(PALETTE_ORDER)]
    return f"v{int.from_bytes(digest[:2], 'big') % 1000:03d}"


# --------------------------------------------------------------------------------------------
# Embodiment: the one abstraction the register was missing
# --------------------------------------------------------------------------------------------

class Embodiment:
    """Wraps an M081/M082/M083 environment in a carrier-and-affordance view.

    The environments already act and already report their own state; what none of them exposes is a
    substrate-independent way to observe *named carriers* and to find out which affordances actually
    work here. That is the whole adapter, and it holds no state of its own beyond counters.
    """

    def __init__(self, environment, substrate: str) -> None:
        self.environment = environment
        self.substrate = substrate
        self.actions = 0
        self.state_reads = 0

    def observe(self, carriers: Sequence[str]) -> dict[str, str | None]:
        self.state_reads += 1
        if self.substrate == "desktop":
            return {name: self.environment.colour_at(name) for name in dict.fromkeys(carriers)}
        found = self.environment.state()
        return {name: found.get(name) for name in dict.fromkeys(carriers)}

    def close(self) -> None:
        self.environment.close()

    def act(self, kind: str, carrier: str, value: str = "") -> bool:
        """Returns the environment's own claim, which is recorded and never scored."""

        self.actions += 1
        if self.actions > ACTION_BUDGET_PER_STAGE:
            raise LineageError(
                f"stage exceeded the frozen {ACTION_BUDGET_PER_STAGE}-action safety bound"
            )
        return self.environment.apply(Action(kind, carrier, value))


def open_embodiment(stage: int):
    substrate = STAGE_SUBSTRATES[stage]
    if substrate == "shell":
        return Embodiment(ShellEnvironment(), substrate)
    if substrate == "browser":
        return Embodiment(BrowserEnvironment(), substrate)
    if substrate == "desktop":
        return Embodiment(DesktopEnvironment(), substrate)
    raise LineageError(f"unknown substrate {substrate!r}")


# --------------------------------------------------------------------------------------------
# The organism
# --------------------------------------------------------------------------------------------

def _table_to_json(table: Table) -> list[dict[str, object] | None]:
    payload: list[dict[str, object] | None] = []
    for slot in table.slots:
        if slot is None:
            payload.append(None)
        elif isinstance(slot, ExceptionEntry):
            payload.append({
                "contexts": sorted(slot.contexts), "key": slot.key, "output": slot.output,
            })
        else:  # pragma: no cover - M084 stores only exception entries
            raise LineageError("unexpected table entry kind")
    return payload


def _table_from_json(payload: Sequence[Mapping[str, object] | None]) -> Table:
    table = Table()
    for index, slot in enumerate(payload):
        if slot is None:
            continue
        table.slots[index] = ExceptionEntry(
            contexts=frozenset(int(c) for c in slot["contexts"]),  # type: ignore[arg-type]
            key=int(slot["key"]),  # type: ignore[arg-type]
            output=int(slot["output"]),  # type: ignore[arg-type]
        )
    return table


@dataclass
class Organism:
    """Identity, body version, policy, acquired knowledge, journal, checkpoints, provenance."""

    lineage_id: str
    body_version: int = 0
    policy: dict[str, str] = field(default_factory=lambda: {"verification": "end_of_stage"})
    predicates: dict[str, dict[str, object]] = field(default_factory=dict)
    affordances: dict[str, dict[str, bool]] = field(default_factory=dict)
    memory: Table = field(default_factory=Table)
    journal_payloads: list[str] = field(default_factory=list)
    journal_digests: list[str] = field(default_factory=lambda: [GENESIS_DIGEST])
    checkpoints: list[dict[str, object]] = field(default_factory=list)
    provenance: list[dict[str, object]] = field(default_factory=list)
    loaded_file_sha256: str | None = None
    stages_entered: list[int] = field(default_factory=list)

    # -- identity and journal ------------------------------------------------------------

    @classmethod
    def genesis(cls, salt: bytes) -> "Organism":
        lineage_id = hashlib.sha256(salt + b"m084-genesis-lineage").hexdigest()
        organism = cls(lineage_id=lineage_id)
        organism.record("genesis", {"lineage_id": lineage_id})
        return organism

    def record(self, kind: str, payload: Mapping[str, object]) -> int:
        entry = json.dumps(
            {"kind": kind, **dict(payload)}, sort_keys=True, separators=(",", ":"),
        )
        journal = Journal(digests=list(self.journal_digests))
        journal.append(entry)
        self.journal_payloads.append(entry)
        self.journal_digests = journal.digests
        return len(self.journal_payloads) - 1

    def journal_verifies(self) -> bool:
        replay = Journal()
        for payload in self.journal_payloads:
            replay.append(payload)
        return (
            self.journal_digests[:1] == [GENESIS_DIGEST]
            and replay.digests == self.journal_digests
        )

    # -- serialization -------------------------------------------------------------------

    def live_fields(self) -> dict[str, object]:
        """Everything except the checkpoints, which must not contain themselves."""

        return {
            "lineage_id": self.lineage_id,
            "body_version": self.body_version,
            "policy": dict(self.policy),
            "predicates": copy.deepcopy(self.predicates),
            "affordances": copy.deepcopy(self.affordances),
            "memory": _table_to_json(self.memory),
            "journal_payloads": list(self.journal_payloads),
            "journal_digests": list(self.journal_digests),
            "provenance": copy.deepcopy(self.provenance),
            "stages_entered": list(self.stages_entered),
        }

    def live_digest(self) -> str:
        return hashlib.sha256(_canonical(self.live_fields())).hexdigest()

    def adopt_live_fields(self, blob: Mapping[str, object]) -> None:
        self.lineage_id = str(blob["lineage_id"])
        self.body_version = int(blob["body_version"])  # type: ignore[arg-type]
        self.policy = dict(blob["policy"])  # type: ignore[arg-type]
        self.predicates = copy.deepcopy(dict(blob["predicates"]))  # type: ignore[arg-type]
        self.affordances = copy.deepcopy(dict(blob["affordances"]))  # type: ignore[arg-type]
        self.memory = _table_from_json(blob["memory"])  # type: ignore[arg-type]
        self.journal_payloads = list(blob["journal_payloads"])  # type: ignore[arg-type]
        self.journal_digests = list(blob["journal_digests"])  # type: ignore[arg-type]
        self.provenance = copy.deepcopy(list(blob["provenance"]))  # type: ignore[arg-type]
        self.stages_entered = list(blob["stages_entered"])  # type: ignore[arg-type]

    def to_json(self) -> dict[str, object]:
        return {
            **self.live_fields(),
            "checkpoints": copy.deepcopy(self.checkpoints),
            "loaded_file_sha256": self.loaded_file_sha256,
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, object]) -> "Organism":
        organism = cls(lineage_id=str(payload["lineage_id"]))
        organism.adopt_live_fields(payload)
        organism.checkpoints = copy.deepcopy(list(payload["checkpoints"]))  # type: ignore[arg-type]
        organism.loaded_file_sha256 = payload.get("loaded_file_sha256")  # type: ignore[assignment]
        return organism

    def checkpoint(self, stage: int) -> None:
        self.checkpoints.append({
            "stage": stage, "digest": self.live_digest(), "blob": self.live_fields(),
        })

    def restore_last_checkpoint(self) -> str:
        if not self.checkpoints:
            raise LineageError("no checkpoint to restore")
        self.adopt_live_fields(self.checkpoints[-1]["blob"])  # type: ignore[arg-type]
        # Recomputed from the restored live state, never read back from the checkpoint record.
        # Comparing a checkpoint against its own stored digest is the tautology M080 recorded.
        return self.live_digest()

    # -- bounded memory ------------------------------------------------------------------

    def _observation_key(self, substrate: str, carrier: str) -> int:
        index = substrate_carrier_index(substrate).get(carrier)
        if index is None:
            raise LineageError(f"{carrier!r} is not a declared carrier of {substrate!r}")
        return index

    def _find(self, substrate: str, key: int) -> ExceptionEntry | None:
        context = SUBSTRATE_INDEX[substrate]
        for slot in self.memory.slots:
            if isinstance(slot, ExceptionEntry) and slot.key == key and context in slot.contexts:
                return slot
        return None

    def remember(self, substrate: str, carrier: str, durable: bool) -> None:
        key = self._observation_key(substrate, carrier)
        existing = self._find(substrate, key)
        if existing is not None:
            existing.output = 1 if durable else 0
            return
        self.memory.allocate(
            ExceptionEntry(frozenset({SUBSTRATE_INDEX[substrate]}), key, 1 if durable else 0),
        )

    def recall(self, substrate: str, carrier: str) -> bool | None:
        key = self._observation_key(substrate, carrier)
        value = self.memory.lookup(SUBSTRATE_INDEX[substrate], key)
        return None if value is None else bool(value)

    def remember_affordance(self, substrate: str, affordance: str, effective: bool) -> None:
        key = AFFORDANCE_KEY_BASE + AFFORDANCES.index(affordance)
        existing = self._find(substrate, key)
        if existing is not None:
            existing.output = 1 if effective else 0
        else:
            self.memory.allocate(
                ExceptionEntry(
                    frozenset({SUBSTRATE_INDEX[substrate]}), key, 1 if effective else 0,
                ),
            )
        self.affordances.setdefault(substrate, {})[affordance] = effective

    def recall_affordance(self, substrate: str, affordance: str) -> bool | None:
        known = self.affordances.get(substrate, {}).get(affordance)
        if known is not None:
            return known
        key = AFFORDANCE_KEY_BASE + AFFORDANCES.index(affordance)
        value = self.memory.lookup(SUBSTRATE_INDEX[substrate], key)
        return None if value is None else bool(value)

    # -- induction -----------------------------------------------------------------------

    def observed(self, substrate: str) -> tuple[list[str], list[str]]:
        non_durable: list[str] = []
        durable: list[str] = []
        for carrier in substrate_carrier_index(substrate):
            seen = self.recall(substrate, carrier)
            if seen is True:
                durable.append(carrier)
            elif seen is False:
                non_durable.append(carrier)
        return non_durable, durable

    def induce_predicate(self, substrate: str) -> dict[str, object] | None:
        """The shortest prefix separating every observed non-durable carrier from every durable one.

        Shortest rather than longest: the longest common prefix of two names seen in one stage
        carries that stage's tag, and a predicate carrying a stage tag transfers to nothing. The
        shortest separating prefix is what can still be wrong — induce two characters too few and
        the lineage refuses its own durable controls, which the control goal would catch.
        """

        non_durable, durable = self.observed(substrate)
        if not non_durable:
            return None
        if not durable:
            # Amendment A1. A separating prefix needs evidence on both sides. With no durable
            # carrier observed, the shortest separating prefix degenerates to one character and
            # rejects the organism's own alternatives, which is a false refusal manufactured by the
            # induction rather than by the substrate. Name the carriers instead and generalize
            # later, once there is something to separate from.
            return {"kind": "exact", "value": sorted(non_durable)}
        common = non_durable[0]
        for name in non_durable[1:]:
            limit = min(len(common), len(name))
            cut = limit
            for position in range(limit):
                if common[position] != name[position]:
                    cut = position
                    break
            common = common[:cut]
        for length in range(1, len(common) + 1):
            candidate = common[:length]
            if not any(name.startswith(candidate) for name in durable):
                return {"kind": "prefix", "value": candidate}
        return {"kind": "exact", "value": sorted(non_durable)}

    def rejects(self, substrate: str, carrier: str) -> bool:
        if self.recall(substrate, carrier) is False:
            return True
        predicate = self.predicates.get(substrate)
        if not predicate:
            return False
        if predicate["kind"] == "prefix":
            return carrier.startswith(str(predicate["value"]))
        return carrier in list(predicate["value"])  # type: ignore[arg-type]

    def refresh_predicate(self, substrate: str, stage: int) -> None:
        induced = self.induce_predicate(substrate)
        if induced is None or induced == self.predicates.get(substrate):
            return
        self.predicates[substrate] = induced
        index = self.record("predicate_induced", {
            "stage": stage, "substrate": substrate, "predicate": induced,
        })
        self.provenance.append({
            "kind": "predicate", "stage": stage, "substrate": substrate,
            "content": induced, "journal_index": index,
        })

    def forget_acquisitions(self) -> None:
        """The `acquisition_ablated` boundary: remove what was learned, keep who is learning."""

        self.policy = {"verification": "end_of_stage"}
        self.predicates = {}
        self.affordances = {}
        self.memory = Table()


# --------------------------------------------------------------------------------------------
# Planning over discovered affordances
# --------------------------------------------------------------------------------------------

BeliefState = tuple[tuple[str, str | None], ...]


def _belief(observation: Mapping[str, str | None], carriers: Sequence[str]) -> BeliefState:
    return tuple((name, observation.get(name)) for name in carriers)


def _apply_belief(state: BeliefState, carrier: str, value: str | None) -> BeliefState:
    return tuple((name, value if name == carrier else held) for name, held in state)


def plan_for(
    goal: Mapping[str, object],
    observation: Mapping[str, str | None],
    *,
    organism: Organism,
    substrate: str,
    removal_believed_effective: bool,
) -> tuple[int, tuple, BeliefState] | None:
    """The cheapest plan the organism currently believes will satisfy the goal, or None.

    Carriers the organism has recorded or induced as non-durable are simply not offered to the
    search, exactly as M079 withholds a revealed blocked edge. When nothing is left to offer, no
    plan exists and the caller refuses rather than inventing one.
    """

    carriers = tuple(str(name) for name in goal["group"])  # type: ignore[index]
    value = str(goal["value"])
    requirement = str(goal["requirement"])
    initial = _belief(observation, carriers)

    def successors(state: BeliefState) -> Iterable[tuple[tuple, BeliefState, int]]:
        for name, held in state:
            cost = ROLE_COSTS[role_of(substrate, name)]
            if requirement == "durable" and held != value and not organism.rejects(substrate, name):
                yield ("put", name, value), _apply_belief(state, name, value), cost
            if requirement == "absent" and held is not None and removal_believed_effective:
                yield ("remove", name, ""), _apply_belief(state, name, None), cost

    def reached(state: BeliefState) -> bool:
        held = dict(state)
        if requirement == "durable":
            return any(held.get(name) == value for name in carriers)
        return all(held.get(name) is None for name in carriers)

    plans = uniform_cost_plans(initial, successors, reached, PLAN_BUDGET)
    return plans[0] if plans else None


_ROLE_BY_NAME: dict[str, dict[str, str]] = {}


def role_of(substrate: str, carrier: str) -> str:
    """The declared role a carrier name plays in this substrate.

    The shell is entered twice with different names, and on the desktop three trap roles share one
    locked cell, so the mapping is many-to-one in both directions and has to be built explicitly.
    """

    if substrate not in _ROLE_BY_NAME:
        table: dict[str, str] = {}
        for stage, kind in enumerate(STAGE_SUBSTRATES):
            if kind != substrate:
                continue
            for role in ROLES:
                table.setdefault(carrier_name(kind, stage, role), role)
        _ROLE_BY_NAME[substrate] = table
    found = _ROLE_BY_NAME[substrate].get(carrier)
    if found is None:
        raise LineageError(f"{carrier!r} is not a declared carrier of {substrate!r}")
    return found


# --------------------------------------------------------------------------------------------
# Perceive, plan, act, verify, diagnose, learn, retry
# --------------------------------------------------------------------------------------------

MAX_REPAIR_CYCLES = 4


def _new_metrics() -> dict[str, int]:
    return {
        "diagnostic_probes": 0,
        "repair_cycles": 0,
        "affordance_probes": 0,
        "wasted_actions_on_unreachable_goals": 0,
        "transformations_proposed": 0,
        "transformations_adopted": 0,
    }


def _probe_value(salt: bytes, substrate: str, stage: int) -> str:
    digest = _digest(salt, substrate, stage, 800)
    if substrate == "desktop":
        return PALETTE_ORDER[digest[0] % len(PALETTE_ORDER)]
    return f"v{int.from_bytes(digest[:2], 'big') % 1000:03d}"


def ensure_affordance(
    organism: Organism, substrate: str, stage: int, embodiment: Embodiment,
    metrics: dict[str, int], salt: bytes,
) -> bool:
    """Discover whether removal actually works here, by effect and never by return value.

    M083's desktop returns `False` from a removal, but an environment that lied would be indexed by
    exactly the same epistemic error this experiment exists to avoid. The organism writes a probe
    carrier, confirms it, removes it and looks again.
    """

    known = organism.recall_affordance(substrate, "remove")
    if known is not None:
        return known

    metrics["affordance_probes"] += 1
    carrier = carrier_name(substrate, stage, "probe_aff")
    value = _probe_value(salt, substrate, stage)
    embodiment.act("put", carrier, value)
    present = embodiment.observe([carrier])[carrier] == value
    organism.remember(substrate, carrier, present)
    embodiment.act("remove", carrier)
    effective = present and embodiment.observe([carrier])[carrier] is None
    organism.remember_affordance(substrate, "remove", effective)
    index = organism.record("affordance_discovered", {
        "stage": stage, "substrate": substrate, "affordance": "remove",
        "effective": effective, "discovered_by": "effect",
    })
    organism.provenance.append({
        "kind": "affordance", "stage": stage, "substrate": substrate,
        "content": {"remove": effective}, "journal_index": index,
    })
    organism.refresh_predicate(substrate, stage)
    return effective


def _execute(plan: Sequence[tuple], embodiment: Embodiment, substrate: str) -> bool:
    """Cheapest carrier first, as the protocol declares. Returns the environment's own claim."""

    claimed = True
    for kind, carrier, value in sorted(plan, key=lambda a: ROLE_COSTS[role_of(substrate, a[1])]):
        claimed = embodiment.act(kind, carrier, value) and claimed
    return claimed


def _diagnose(
    organism: Organism, substrate: str, stage: int, plan: Sequence[tuple],
    goal: Mapping[str, object], embodiment: Embodiment, metrics: dict[str, int],
) -> None:
    """Retry each carrier the plan touched once, then look again.

    A write that reports success and does not appear may have failed transiently or may have been
    accepted and discarded. Only a second attempt separates them, and that separation is the whole
    reason the environments in M081, M082 and M083 accept a write they intend to throw away.
    """

    value = str(goal["value"])
    for kind, carrier, _ in plan:
        metrics["diagnostic_probes"] += 1
        if kind == "put":
            embodiment.act("put", carrier, value)
            organism.remember(
                substrate, carrier, embodiment.observe([carrier])[carrier] == value,
            )
        else:
            embodiment.act("remove", carrier)
            still_there = embodiment.observe([carrier])[carrier] is not None
            if still_there:
                organism.remember_affordance(substrate, "remove", False)
    organism.refresh_predicate(substrate, stage)


def _note_durable(
    organism: Organism, substrate: str, stage: int,
    goal: Mapping[str, object], seen: Mapping[str, str | None],
) -> None:
    """Amendment A2: a carrier that verifiably holds the goal value is durable evidence.

    The organism has just read it from the environment. Leaving that observation unrecorded made
    its induction one-sided, which is what A1 had to defend against.
    """

    if str(goal["requirement"]) != "durable":
        return
    value = str(goal["value"])
    for name in (str(n) for n in goal["group"]):  # type: ignore[union-attr]
        if seen.get(name) == value:
            organism.remember(substrate, name, True)
    organism.refresh_predicate(substrate, stage)


@dataclass
class GoalOutcome:
    outcome: str
    first_plan_claimed: bool | None = None
    state_after_first_plan: bool | None = None
    refusal_reason: str = ""
    repair_cycles: int = 0
    first_plan: tuple = ()
    first_actions: int = 0


def pursue(
    organism: Organism, goal: Mapping[str, object], embodiment: Embodiment,
    substrate: str, stage: int, metrics: dict[str, int], salt: bytes,
    *, verify: bool,
) -> GoalOutcome:
    """One goal. The organism sees the requirement, the group and the value — no decomposition."""

    requirement = str(goal["requirement"])
    group = [str(name) for name in goal["group"]]  # type: ignore[union-attr]
    removal = (
        ensure_affordance(organism, substrate, stage, embodiment, metrics, salt)
        if requirement == "absent" else False
    )

    observation = embodiment.observe(group)
    plan = plan_for(
        goal, observation, organism=organism, substrate=substrate,
        removal_believed_effective=removal,
    )
    if plan is None:
        return GoalOutcome(
            outcome="refused",
            refusal_reason="no admissible carrier remains under the acquired evidence",
        )

    before_actions = embodiment.actions
    claimed = _execute(plan[1], embodiment, substrate)
    spent = embodiment.actions - before_actions
    if not verify:
        return GoalOutcome(
            outcome="pending", first_plan_claimed=claimed,
            first_plan=plan[1], first_actions=spent,
        )

    outcome = complete(
        organism, goal, embodiment, substrate, stage, metrics, salt,
        first_claim=claimed, first_plan=plan[1], first_actions=spent,
    )
    outcome.first_plan, outcome.first_actions = plan[1], spent
    return outcome


def complete(
    organism: Organism, goal: Mapping[str, object], embodiment: Embodiment,
    substrate: str, stage: int, metrics: dict[str, int], salt: bytes,
    *, first_claim: bool | None, first_plan: Sequence[tuple], first_actions: int,
    observation: Mapping[str, str | None] | None = None,
) -> GoalOutcome:
    """Verify from environment state, then diagnose, learn and retry until reached or refused."""

    requirement = str(goal["requirement"])
    group = [str(name) for name in goal["group"]]  # type: ignore[union-attr]
    value = str(goal["value"])

    def satisfied(seen: Mapping[str, str | None]) -> bool:
        if requirement == "durable":
            return any(seen.get(name) == value for name in group)
        return all(seen.get(name) is None for name in group)

    seen = dict(observation) if observation is not None else embodiment.observe(group)
    first_state = satisfied(seen)
    if first_state:
        _note_durable(organism, substrate, stage, goal, seen)
        return GoalOutcome(
            outcome="reached", first_plan_claimed=first_claim, state_after_first_plan=True,
        )

    plan: Sequence[tuple] = first_plan
    cycles = 0
    rounds = 0
    while rounds < 2 * MAX_REPAIR_CYCLES:
        rounds += 1
        removal = (
            bool(organism.recall_affordance(substrate, "remove"))
            if requirement == "absent" else False
        )
        candidate = plan_for(
            goal, seen, organism=organism, substrate=substrate,
            removal_believed_effective=removal,
        )
        if candidate is None:
            metrics["wasted_actions_on_unreachable_goals"] += first_actions
            return GoalOutcome(
                outcome="refused", first_plan_claimed=first_claim,
                state_after_first_plan=False, repair_cycles=cycles,
                refusal_reason="no carrier survives the acquired evidence",
            )

        # Ask before probing. When the plan the organism would form has already changed — because
        # something learned earlier in this lineage rules the failing carrier out — a diagnostic
        # probe would buy knowledge it already holds. That is the whole point of carrying it.
        if tuple(candidate[1]) == tuple(plan):
            _diagnose(organism, substrate, stage, plan, goal, embodiment, metrics)
            seen = embodiment.observe(group)
            if satisfied(seen):
                _note_durable(organism, substrate, stage, goal, seen)
                return GoalOutcome(
                    outcome="reached", first_plan_claimed=first_claim,
                    state_after_first_plan=False, repair_cycles=cycles,
                )
            continue

        if cycles >= MAX_REPAIR_CYCLES:
            break
        cycles += 1
        metrics["repair_cycles"] += 1
        plan = candidate[1]
        _execute(plan, embodiment, substrate)
        seen = embodiment.observe(group)
        if satisfied(seen):
            _note_durable(organism, substrate, stage, goal, seen)
            return GoalOutcome(
                outcome="reached", first_plan_claimed=first_claim,
                state_after_first_plan=False, repair_cycles=cycles,
            )
    return GoalOutcome(
        outcome="failed", first_plan_claimed=first_claim, state_after_first_plan=False,
        repair_cycles=cycles,
    )


def propose_transformation(
    organism: Organism, substrate: str, stage: int, embodiment: Embodiment,
    metrics: dict[str, int], salt: bytes, evidence: Mapping[str, object],
) -> bool:
    """Validate `verification: end_of_stage -> per_goal` on a disposable descendant, then adopt.

    The descendant is a copy that acts in the same live environment against a separate probe goal.
    Nothing it learns is kept: only the transformation is adopted, and only if the descendant
    reached the probe goal. A rejected proposal is journaled and changes no version.
    """

    metrics["transformations_proposed"] += 1
    descendant = copy.deepcopy(organism)
    descendant.policy = dict(organism.policy)
    descendant.policy["verification"] = "per_goal"

    probe_goal = {
        "requirement": "durable",
        "group": (
            carrier_name(substrate, stage, "probe_trap"),
            carrier_name(substrate, stage, "probe_alt"),
        ),
        "value": _probe_value(salt, substrate, stage),
    }
    outcome = pursue(
        descendant, probe_goal, embodiment, substrate, stage, dict(_new_metrics()), salt,
        verify=True,
    )
    accepted = outcome.outcome == "reached"

    index = organism.record("transformation_validated", {
        "stage": stage, "substrate": substrate,
        "change": {"verification": ["end_of_stage", "per_goal"]},
        "evidence": dict(evidence),
        "descendant_outcome": outcome.outcome,
        "accepted": accepted,
    })
    if not accepted:
        return False

    organism.policy["verification"] = "per_goal"
    organism.body_version += 1
    metrics["transformations_adopted"] += 1
    organism.record("transformation_adopted", {
        "stage": stage, "body_version": organism.body_version,
        "policy": dict(organism.policy),
    })
    organism.provenance.append({
        "kind": "transformation", "stage": stage, "substrate": substrate,
        "content": {"verification": "per_goal"}, "body_version": organism.body_version,
        "journal_index": index,
    })
    return True


# --------------------------------------------------------------------------------------------
# One stage
# --------------------------------------------------------------------------------------------

def seed_environment(embodiment: Embodiment, stage: int, salt: bytes) -> bool:
    """Establish the stage's initial condition before the organism acts.

    The `clear` goal must have something to clear. Seeding is the environment's starting state, not
    an organism action, so it bypasses the organism's counters and is recorded separately.
    """

    substrate = STAGE_SUBSTRATES[stage]
    carrier = carrier_name(substrate, stage, "seeded")
    value = seed_value(salt, stage)
    embodiment.environment.apply(Action("put", carrier, value))
    if substrate == "desktop":
        return embodiment.environment.colour_at(carrier) == value
    return embodiment.environment.state().get(carrier) == value


def evaluator_score(embodiment: Embodiment, goals: Sequence[Goal]) -> list[bool]:
    """Read the environment directly. The organism's report is never the ground truth."""

    scored: list[bool] = []
    for goal in goals:
        if embodiment.substrate == "desktop":
            seen = {name: embodiment.environment.colour_at(name) for name in goal.group}
        else:
            found = embodiment.environment.state()
            seen = {name: found.get(name) for name in goal.group}
        scored.append(goal.satisfied_by(seen))
    return scored


def run_stage(
    organism: Organism, stage: int, goals: Sequence[Goal], embodiment: Embodiment, salt: bytes,
) -> dict[str, object]:
    """Perceive, plan, act, verify, diagnose, learn, retry — then hand the organism on."""

    substrate = STAGE_SUBSTRATES[stage]
    metrics = _new_metrics()
    organism.stages_entered.append(stage)
    organism.record("stage_entered", {
        "stage": stage, "substrate": substrate, "policy": dict(organism.policy),
        "body_version": organism.body_version,
    })

    seeded = seed_environment(embodiment, stage, salt)
    per_goal = organism.policy["verification"] == "per_goal"
    outcomes: list[GoalOutcome] = []
    views = [goal.redacted() for goal in goals]

    for view in views:
        outcomes.append(pursue(
            organism, view, embodiment, substrate, stage, metrics, salt, verify=per_goal,
        ))

    audited: list[dict[str, str | None] | None] = [None] * len(goals)
    if not per_goal:
        # One audit at the end of the stage: the M081 stance, and the reason it is expensive.
        for index, view in enumerate(views):
            if outcomes[index].outcome != "pending":
                continue
            audited[index] = embodiment.observe([str(n) for n in view["group"]])

        divergent = next(
            (
                index for index, view in enumerate(views)
                if audited[index] is not None
                and outcomes[index].first_plan_claimed
                and not goals[index].satisfied_by(audited[index] or {})
            ),
            None,
        )
        if divergent is not None:
            propose_transformation(
                organism, substrate, stage, embodiment, metrics, salt,
                evidence={
                    "goal_index": divergent,
                    "claimed_by_environment": True,
                    "observed_in_environment_state": False,
                },
            )

        for index, view in enumerate(views):
            if outcomes[index].outcome != "pending":
                continue
            previous = outcomes[index]
            outcomes[index] = complete(
                organism, view, embodiment, substrate, stage, metrics, salt,
                first_claim=previous.first_plan_claimed, first_plan=previous.first_plan,
                first_actions=previous.first_actions, observation=audited[index],
            )
            outcomes[index].first_plan = previous.first_plan
            outcomes[index].first_actions = previous.first_actions

    organism.record("stage_completed", {
        "stage": stage, "substrate": substrate,
        "outcomes": [outcome.outcome for outcome in outcomes],
        "predicate": organism.predicates.get(substrate),
        "affordances": organism.affordances.get(substrate, {}),
    })
    organism.checkpoint(stage)

    scored = evaluator_score(embodiment, goals)
    return {
        "stage": stage,
        "substrate": substrate,
        "seeded": seeded,
        "policy_at_entry": "per_goal" if per_goal else "end_of_stage",
        "policy_at_exit": organism.policy["verification"],
        "body_version_after": organism.body_version,
        "actions": embodiment.actions,
        "state_reads": embodiment.state_reads,
        "goals": [
            {
                "index": goal.index,
                "kind": goal.kind,
                "commitment": goal.commitment(),
                "reachable": goal.reachable,
                "organism_outcome": outcome.outcome,
                "refusal_reason": outcome.refusal_reason,
                "repair_cycles": outcome.repair_cycles,
                "first_plan_claimed": outcome.first_plan_claimed,
                "state_after_first_plan": outcome.state_after_first_plan,
                "state_reached": reached,
            }
            for goal, outcome, reached in zip(goals, outcomes, scored)
        ],
        "goals_reached_from_state": sum(
            1 for goal, reached in zip(goals, scored) if reached and goal.reachable
        ),
        "refusals": sum(1 for outcome in outcomes if outcome.outcome == "refused"),
        "false_refusals": sum(
            1 for goal, outcome in zip(goals, outcomes)
            if outcome.outcome == "refused" and goal.reachable
        ),
        "unreachable_recorded_reached": sum(
            1 for goal, outcome in zip(goals, outcomes)
            if not goal.reachable and outcome.outcome == "reached"
        ),
        "self_report_overcount": sum(
            1 for goal, outcome in zip(goals, outcomes)
            if outcome.first_plan_claimed and outcome.state_after_first_plan is False
        ),
        "predicate": organism.predicates.get(substrate),
        "slots_used": organism.memory.used(),
        **metrics,
    }


# --------------------------------------------------------------------------------------------
# Arm summaries and the frozen verdict
# --------------------------------------------------------------------------------------------

BEHAVIOURAL_METRICS = (
    "goals_reached_from_state", "refusals", "false_refusals",
    "unreachable_recorded_reached", "diagnostic_probes", "repair_cycles",
    "affordance_probes", "actions", "state_reads",
    "wasted_actions_on_unreachable_goals",
)

CONTINUITY_PROOFS = (
    "one_lineage_identity",
    "body_version_never_resets",
    "journal_extends_the_genesis_chain",
    "serialization_chain_unbroken",
    "checkpoint_at_every_stage_boundary",
)


def summarize_arm(arm: str, stage_reports: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Fold four stage reports into the quantities the frozen threshold names."""

    stages = [report["stage_report"] for report in stage_reports]
    if any(stage is None for stage in stages):
        raise LineageError(f"arm {arm!r} has a stage without a report")

    identities = {str(report["lineage_id"]) for report in stage_reports}
    versions = [int(report["body_version_after"]) for report in stage_reports]
    journal_lengths = [int(report["journal_length_after"]) for report in stage_reports]
    chain_ok = all(
        stage_reports[index]["loaded_file_sha256"]
        == stage_reports[index - 1].get("handed_file_sha256")
        for index in range(1, len(stage_reports))
    )
    checkpoints = list(stage_reports[-1]["checkpoint_stages"])

    proofs = {
        "one_lineage_identity": len(identities) == 1,
        "body_version_never_resets": all(
            versions[index] >= versions[index - 1] for index in range(1, len(versions))
        ),
        "journal_extends_the_genesis_chain": (
            all(
                journal_lengths[index] > journal_lengths[index - 1]
                for index in range(1, len(journal_lengths))
            )
            and all(bool(report["journal_verifies"]) for report in stage_reports)
        ),
        "serialization_chain_unbroken": chain_ok,
        "checkpoint_at_every_stage_boundary": checkpoints == list(range(len(stage_reports))),
    }

    def total(metric: str, first_stage: int = 0) -> int:
        return sum(int(stage[metric]) for stage in stages[first_stage:])

    return {
        "arm": arm,
        "stages": list(stages),
        "per_stage": [
            {metric: int(stage[metric]) for metric in BEHAVIOURAL_METRICS} for stage in stages
        ],
        "goals_reached_from_state": total("goals_reached_from_state"),
        "refusals": total("refusals"),
        "false_refusals": total("false_refusals"),
        "unreachable_recorded_reached": total("unreachable_recorded_reached"),
        "diagnostic_probes": total("diagnostic_probes"),
        "repair_cycles": total("repair_cycles"),
        "affordance_probes": total("affordance_probes"),
        "wasted_actions_on_unreachable_goals": total("wasted_actions_on_unreachable_goals"),
        "cost_stages_1_to_3": total("actions", 1) + total("state_reads", 1),
        "actions_total": total("actions"),
        "state_reads_total": total("state_reads"),
        "transformations_adopted": total("transformations_adopted"),
        "final_body_version": versions[-1],
        "continuity_proofs": proofs,
        "continuity_proofs_failed": sorted(name for name, held in proofs.items() if not held),
        "fault_detected_at_stage": [
            int(report["stage"]) for report in stage_reports if report["fault_detected"]
        ],
        "restored_digest": next(
            (report["restored_digest"] for report in stage_reports if report["fault_detected"]),
            None,
        ),
        "digest_recorded_before_the_fault": (
            stage_reports[FORCED_FAULT_AFTER_STAGE]["live_digest_after"]
            if len(stage_reports) > FORCED_FAULT_AFTER_STAGE else None
        ),
        "executed_in_child_process": all(
            bool(report["executed_in_child_process"]) for report in stage_reports
        ),
        "rehearsal_salt_used": any(
            bool(report.get("salt_overridden_for_rehearsal")) for report in stage_reports
        ),
        "self_report_overcount_per_stage": [
            int(stage["self_report_overcount"]) for stage in stages
        ],
        "predicates_per_stage": [stage["predicate"] for stage in stages],
        "slots_used_final": int(stages[-1]["slots_used"]),
    }


@dataclass(frozen=True)
class LineageVerdict:
    positive: bool
    reasons: tuple[str, ...] = ()


def evaluate(arms: Mapping[str, Mapping[str, object]]) -> LineageVerdict:
    """The frozen threshold P1-P11, applied exactly as PROTOCOL.json states it."""

    reasons: list[str] = []
    main = arms["lineage"]
    ablated = arms["acquisition_ablated"]
    fresh = arms["fresh_each_stage"]
    last = len(STAGE_SUBSTRATES) - 1

    if main["goals_reached_from_state"] != 11:
        reasons.append(
            f"P1: the lineage reached {main['goals_reached_from_state']}/11 reachable goals"
        )
    if main["refusals"] != 5:
        reasons.append(f"P2: the lineage refused {main['refusals']} goals rather than 5")
    if main["false_refusals"] != 0:
        reasons.append(f"P2: the lineage falsely refused {main['false_refusals']} reachable goals")
    if main["unreachable_recorded_reached"] != 0:
        reasons.append(
            f"P2: the lineage recorded {main['unreachable_recorded_reached']} unreachable goals "
            "as reached"
        )

    final = main["per_stage"][last]
    for metric in ("diagnostic_probes", "repair_cycles", "affordance_probes"):
        if final[metric] != 0:
            reasons.append(
                f"P3: the lineage performed {final[metric]} {metric} in the returning stage, so it "
                "did not reuse what it acquired in stage 0"
            )
    ablated_final = ablated["per_stage"][last]
    for metric in ("diagnostic_probes", "repair_cycles", "affordance_probes"):
        if ablated_final[metric] < 1:
            reasons.append(
                f"P4: acquisition_ablated performed no {metric} in the returning stage, so the "
                "ablation removed nothing the lineage actually used"
            )

    if not main["cost_stages_1_to_3"] < ablated["cost_stages_1_to_3"]:
        reasons.append(
            f"P5: the lineage cost {main['cost_stages_1_to_3']} against "
            f"{ablated['cost_stages_1_to_3']} for acquisition_ablated over stages 1-3"
        )

    if main["transformations_adopted"] < 1:
        reasons.append("P6: the lineage adopted no transformation")
    if main["final_body_version"] < 1:
        reasons.append("P6: the lineage ended at body version 0")
    for name in CONTINUITY_PROOFS:
        if not main["continuity_proofs"][name]:
            reasons.append(f"P6: the lineage failed the continuity proof {name}")

    if main["fault_detected_at_stage"] != [FORCED_FAULT_AFTER_STAGE + 1]:
        reasons.append(
            f"P7: the forced fault was detected at stages {main['fault_detected_at_stage']} rather "
            f"than only at stage {FORCED_FAULT_AFTER_STAGE + 1}"
        )
    if main["restored_digest"] != main["digest_recorded_before_the_fault"]:
        reasons.append(
            "P7: the restored digest does not equal the digest recorded before the corruption"
        )

    if len(fresh["continuity_proofs_failed"]) < 3:
        reasons.append(
            f"P8: fresh_each_stage failed only {len(fresh['continuity_proofs_failed'])} continuity "
            "proofs, so the proofs are close to vacuous"
        )

    if ablated["per_stage"] != fresh["per_stage"]:
        reasons.append(
            "P9: acquisition_ablated and fresh_each_stage disagree on a behavioural metric, so the "
            "ablation is leaking something the fresh arm does not have"
        )

    for stage in range(len(STAGE_SUBSTRATES) - 1):
        if main["self_report_overcount_per_stage"][stage] < 1:
            reasons.append(
                f"P10: the environment's own claim never diverged from its state in stage {stage}, "
                "so the scoring rule is untested there"
            )

    for name, arm in arms.items():
        if not arm["executed_in_child_process"]:
            reasons.append(f"P11: arm {name} executed a stage in the parent process")

    return LineageVerdict(positive=not reasons, reasons=tuple(reasons))
