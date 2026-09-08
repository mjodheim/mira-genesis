"""Substrate metamorphosis: carrying a lineage into a body it was not built for.

M042 and M066 already proved a bounded version of substrate change, and this does not redo that.
What the runtime needs is the *continuation* property: a lineage that leaves its current substrate
must arrive able to go on evolving, not merely able to replay what it already knew.

M084 recorded the correction that makes this hard to fake. The agent it carried across four real
substrates replayed an action list computed elsewhere — it perceived nothing, planned nothing and
detected no failure — so "one unchanged agent" was an interface result, not agent competence. A
migration that transports outputs is transported output. A migration that transports the capacity to
acquire is transported intelligence, and only the second one is metamorphosis.

A discovered substrate capability crosses into lineage-owned translation code as inert data, never
as a raw Python callable. A function object carries ambient authority through `__globals__`, closures
and module objects; exposing one discovered operation could therefore reveal every undiscovered
operation living beside it. The host keeps executable adapters private and the lineage receives only
names/tokens it actually earned by probing.
"""
from __future__ import annotations

import copy
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from genesis import state as lineage_state
from genesis.trust_root import artifact_digest_of, digest_of, provenance

MIGRATION_SCHEMA = "genesis-migration-v1"
SUBSTRATE_SCHEMA = "genesis-substrate-v1"
DISCOVERED_OPERATION_SCHEMA = "genesis-discovered-operation-v1"

CARRIED = (
    "acquisitions",
    "tools",
    "components",
    "vocabulary",
    "observations",
)


class MigrationError(RuntimeError):
    """Raised when an arrival cannot be shown to be the same lineage that departed."""


@dataclass
class Substrate:
    """A target body whose semantics the lineage must discover rather than be told.

    Executable operation objects stay host-private. `_discovered` records which private adapters were
    actually found, while the public `discovered` property returns inert capability tokens that can
    be persisted, inspected and passed to translation code without carrying module globals or other
    ambient authority.
    """

    name: str
    operations: Mapping[str, Callable[..., Any]]
    probe_cost: int = 1
    _discovered: dict[str, Callable[..., Any]] = field(default_factory=dict, init=False)

    def probe(self, name: str) -> bool:
        if name in self.operations:
            self._discovered[name] = self.operations[name]
            return True
        return False

    @property
    def discovered(self) -> dict[str, dict[str, str]]:
        return {
            name: {
                "schema": DISCOVERED_OPERATION_SCHEMA,
                "substrate": self.name,
                "operation": name,
            }
            for name in sorted(self._discovered)
        }

    def record(self, *, lineage_visible: bool = False) -> dict[str, Any]:
        payload = {
            "schema": SUBSTRATE_SCHEMA,
            "name": self.name,
            "operations_discovered": sorted(self._discovered),
            "probe_cost": self.probe_cost,
        }
        if lineage_visible:
            return payload
        return {**payload, "operations_available": sorted(self.operations)}


def discover(substrate: Substrate, candidate_names: Sequence[str], budget) -> dict[str, Any]:
    found: list[str] = []
    missing: list[str] = []
    for name in candidate_names:
        budget.spend("probes", substrate.probe_cost)
        if substrate.probe(name):
            found.append(name)
        else:
            missing.append(name)
    return {
        "substrate": substrate.name,
        "probed": list(candidate_names),
        "found": found,
        "missing": missing,
        "probe_cost_each": substrate.probe_cost,
    }


def capability_carried(
    genesis,
    arrived_body_factory: Callable[[], Any],
    tasks: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    from genesis.loop import task_set_digest
    from genesis.sandbox import run_candidate

    evaluated = getattr(genesis, "evaluated_task_digests", None)
    if evaluated is not None and task_set_digest(tasks) not in evaluated:
        raise MigrationError(
            "the translation was offered a task set this lineage has never been evaluated on; "
            "verify a migration against the work the lineage was actually judged by"
        )

    grade = getattr(genesis, "grade", None)
    before = run_candidate(
        genesis.body_factory,
        tasks,
        genesis.isolation,
        admitted_isolation=genesis.admitted_isolation,
        grade=grade,
    )
    after = run_candidate(
        arrived_body_factory,
        tasks,
        genesis.isolation,
        admitted_isolation=genesis.admitted_isolation,
        grade=grade,
    )
    if not (before["completed"] and after["completed"]):
        raise MigrationError(
            "the capability comparison did not run, so the translation cannot be verified: %s"
            % (before.get("reason") or after.get("reason"))
        )

    def solved(run):
        return {row["task_id"] for row in run["outcomes"] if row.get("outcome") == "solved"}

    solved_before, solved_after = solved(before), solved(after)
    lost = sorted(solved_before - solved_after)
    return {
        "measured": True,
        "solved_before": len(solved_before),
        "solved_after": len(solved_after),
        "lost_tasks": lost,
        "preserved": not lost,
        "departure_sandbox_digest": before["result_digest"],
        "arrival_sandbox_digest": after["result_digest"],
    }


def migrate(
    genesis,
    substrate: Substrate,
    translate: Callable[[Mapping[str, Any], Mapping[str, Mapping[str, str]]], Callable[[], Any]],
    *,
    used_operations: Sequence[str],
    tasks: Sequence[Mapping[str, Any]] | None = None,
    permit_capability_loss: bool = False,
    translation_provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Carry a lineage into `substrate`, and prove it arrived as the same lineage.

    Translation code receives a detached departure record plus inert descriptors for only the
    operations that probing discovered. It never receives the private executable registry.
    """
    departing = lineage_state.decode_state(genesis.state)
    departure_head = genesis.journal.head

    discovered = substrate.discovered
    undiscovered = sorted(set(used_operations) - set(discovered))
    if undiscovered:
        raise MigrationError(
            "the translation used operations the lineage never discovered: %s"
            % ", ".join(undiscovered)
        )

    translation_input = copy.deepcopy(departing)
    translation_input_digest = digest_of(translation_input)
    discovered_input = copy.deepcopy(discovered)
    discovered_input_digest = digest_of(discovered_input)
    body_factory = translate(translation_input, discovered_input)
    if digest_of(translation_input) != translation_input_digest:
        raise MigrationError(
            "the translation mutated the departure context it was given; migration inputs are read-only evidence"
        )
    if digest_of(discovered_input) != discovered_input_digest:
        raise MigrationError(
            "the translation mutated the discovered-operation context it was given"
        )
    if not callable(body_factory):
        raise MigrationError("the translation did not produce a body factory")

    body_artifact = artifact_digest_of(body_factory)
    arrived = lineage_state.create_state(
        body_digest=body_artifact["artifact_digest"],
        components=departing["components"],
        vocabulary=departing["vocabulary"],
        tools=departing["tools"],
        acquisitions=departing["acquisitions"],
        observations=departing["observations"],
        generation=departing["generation"],
    )

    carried = carried_intact(departing, arrived)
    if not carried["intact"]:
        raise MigrationError("the lineage did not arrive intact: %s" % "; ".join(carried["lost"]))

    if tasks is None:
        capability = {
            "measured": False,
            "preserved": None,
            "why": "no tasks were supplied, so nothing checked what the translated body can do",
        }
    else:
        capability = capability_carried(genesis, body_factory, tasks)
        if not capability["preserved"] and not permit_capability_loss:
            raise MigrationError(
                "the translation lost capability the lineage had: %s"
                % ", ".join(capability["lost_tasks"])
            )

    genesis.state = arrived
    genesis.body_factory = body_factory
    entry = genesis.journal.append(
        "migration",
        arrived["generation"],
        {
            "substrate": substrate.record(lineage_visible=True),
            "departure_state_digest": departing["state_digest"],
            "arrival_state_digest": arrived["state_digest"],
            "arrival_body_artifact": body_artifact,
            "departure_journal_head": departure_head,
            "used_operations": sorted(used_operations),
            "discovered_operation_tokens": discovered,
            "carried": carried["carried"],
            "capability": capability,
            "provenance": dict(translation_provenance)
            if translation_provenance
            else provenance(
                "host_written",
                produced_by="unattributed translation",
                detail="no translation provenance was supplied, so it is not the lineage's",
            ),
        },
    )

    record = {
        "schema": MIGRATION_SCHEMA,
        "substrate": substrate.record(),
        "departure_state_digest": departing["state_digest"],
        "arrival_state_digest": arrived["state_digest"],
        "arrival_body_artifact": body_artifact,
        "departure_journal_head": departure_head,
        "arrival_journal_entry": entry["entry_digest"],
        "journal_continues": entry["previous_digest"] == departure_head,
        "carried": carried["carried"],
        "capability": capability,
        "used_only_discovered_operations": True,
        "translation_received_inert_operation_tokens": True,
        "evolved_after_migration": False,
    }
    record["migration_digest"] = digest_of(record)
    return record


def carried_intact(departing: Mapping[str, Any], arrived: Mapping[str, Any]) -> dict[str, Any]:
    lost: list[str] = []
    carried: dict[str, Any] = {}
    for field_name in CARRIED:
        before = departing.get(field_name) or []
        after = arrived.get(field_name) or []
        before_ids = [digest_of(item) for item in before]
        after_ids = [digest_of(item) for item in after]
        remaining = Counter(after_ids)
        missing = []
        for identifier in before_ids:
            if remaining.get(identifier):
                remaining[identifier] -= 1
            else:
                missing.append(identifier)
        unexplained = sorted(+remaining)
        carried[field_name] = {
            "departed": len(before_ids),
            "arrived": len(after_ids),
            "missing": len(missing),
            "unexplained_arrivals": len(unexplained),
        }
        if missing:
            lost.append("%s lost %d of %d" % (field_name, len(missing), len(before_ids)))
        if unexplained:
            lost.append("%s gained %d record(s) nobody accounted for" % (field_name, len(unexplained)))
    return {"intact": not lost, "lost": lost, "carried": carried}


def metamorphosis_succeeded(
    migration: Mapping[str, Any], post_migration_cycles: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    accepted = [record for record in post_migration_cycles if record.get("accepted")]
    causal = [
        record
        for record in accepted
        if (record.get("causal_dependency") or {}).get("established")
    ]
    reasons: list[str] = []
    if not migration.get("journal_continues"):
        reasons.append("the post-migration journal does not chain to the departure head")
    if not migration.get("used_only_discovered_operations"):
        reasons.append("the translation used operations the lineage never discovered")
    if any(count["missing"] for count in migration.get("carried", {}).values()):
        reasons.append("the lineage did not arrive intact")
    capability = migration.get("capability") or {}
    if not capability.get("measured"):
        reasons.append(
            "the translation's capability was never measured, so nothing shows the arrival can do "
            "what the departure could"
        )
    elif not capability.get("preserved"):
        reasons.append(
            "the translation lost capability the lineage had: %s"
            % ", ".join(capability.get("lost_tasks") or ["unrecorded tasks"])
        )
    if not accepted:
        reasons.append(
            "the migrated lineage accepted no new candidate, so it replayed rather than evolved"
        )
    elif not causal:
        reasons.append(
            "the migrated lineage accepted a candidate but none was shown to depend on what it "
            "carried across, so the improvement may have nothing to do with the migration"
        )
    return {
        "succeeded": not reasons,
        "reasons": reasons,
        "accepted_after_migration": len(accepted),
        "causally_established_after_migration": len(causal),
        "cycles_after_migration": len(post_migration_cycles),
        "is_transported_intelligence_rather_than_transported_output": bool(causal),
    }
