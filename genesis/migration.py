"""Substrate metamorphosis: carrying a lineage into a body it was not built for.

M042 and M066 already proved a bounded version of substrate change, and this does not redo that.
What the runtime needs is the *continuation* property: a lineage that leaves its current substrate
must arrive able to go on evolving, not merely able to replay what it already knew.

M084 recorded the correction that makes this hard to fake. The agent it carried across four real
substrates replayed an action list computed elsewhere — it perceived nothing, planned nothing and
detected no failure — so "one unchanged agent" was an interface result, not agent competence. A
migration that transports outputs is transported output. A migration that transports the capacity to
acquire is transported intelligence, and only the second one is metamorphosis.

Three rules follow, and each is checked rather than asserted:

1. **The new substrate's semantics are discovered, not declared.** A translation may only use
   operations the lineage found by probing. Using an operation nobody discovered means the host
   redesigned the body for the new substrate, which is precisely what Genesis gate 7 forbids.
2. **Everything the lineage owned arrives with it** — acquisitions, tools, the component registry
   with its extension certificates, the diagnostic vocabulary, useful memory and the causal journal.
   The check is by name and digest, not by count.
3. **What the lineage could do arrives too, measured on work it was actually judged by.** Rule 2
   compares what the lineage *recorded*; for a long time nothing compared what it could still *do*,
   so a translation could drop every capability and the record would say nothing was lost — because
   nothing being counted had been. Both bodies are now run over the same tasks and the arrival is
   refused if it solves strictly less, unless a lossy arrival is explicitly intended. And the
   verification set may not be one the caller invented for the occasion: a migration checked against
   tasks the lineage never faced measures the set rather than the translation, so the set has to be
   one the lineage was evaluated on.
4. **The journal continues.** The post-migration chain links to the pre-migration head, so the
   descent is one lineage rather than two that resemble each other.

And the bar that decides the whole thing: `metamorphosis_succeeded` is false until the migrated
lineage has **accepted a new candidate in its new form**. Arriving intact is not success; arriving
and going on evolving is.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from genesis import state as lineage_state
from genesis.journal import Journal
from genesis.trust_root import digest_of, provenance

MIGRATION_SCHEMA = "genesis-migration-v1"
SUBSTRATE_SCHEMA = "genesis-substrate-v1"

#: What a lineage must carry across. Losing any of these makes the arrival a different lineage.
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

    `operations` is what the substrate really supports. It is deliberately **not** handed to the
    translator: the lineage learns what is there by probing, and `discovered` records what it
    actually found. A translation that reaches past `discovered` is refused.
    """

    name: str
    operations: Mapping[str, Callable[..., Any]]
    probe_cost: int = 1
    _discovered: dict[str, Callable[..., Any]] = field(default_factory=dict, init=False)

    def probe(self, name: str) -> bool:
        """Ask whether the substrate supports an operation. This is the only way to learn."""
        if name in self.operations:
            self._discovered[name] = self.operations[name]
            return True
        return False

    @property
    def discovered(self) -> dict[str, Callable[..., Any]]:
        return dict(self._discovered)

    def record(self, *, lineage_visible: bool = False) -> dict[str, Any]:
        """What is known about this substrate. `lineage_visible` limits it to what was discovered.

        The full record lists `operations_available`, and `migrate` wrote it into the lineage's own
        journal — so once a lineage could read its history, the record told it the names of
        capabilities it had never found by probing. Discovery costs budget precisely so that
        knowing is earned; a free list in the history undoes that.
        """
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
    """Probe the substrate for each candidate operation, spending budget for each probe.

    Nothing here tells the lineage which names to try. That list is the lineage's business; this
    function only makes each guess cost something, so a lineage cannot enumerate a substrate for
    free and call the result discovery.
    """
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
    """Measure whether the translated body can still do what the departing body could.

    `carried_intact` compares what the lineage *recorded* — components, vocabulary, acquisitions,
    observations. It says nothing about what the lineage can still *do*, and for a long time nothing
    else did either: a translation could drop every capability the lineage had and the migration
    record would report that nothing was lost, because nothing that was being counted had been.

    That is the transported-output-versus-transported-intelligence distinction M084 forced on this
    project, arriving one level lower down. So both bodies are run over the same tasks under the same
    isolation and the comparison is made on raw per-task outcomes.
    """
    from genesis.loop import task_set_digest
    from genesis.sandbox import run_candidate

    # Hati's third blocking correction. The caller chose these tasks, and a caller who wants the
    # migration to pass can choose tasks the translation happens to handle. A verification set the
    # lineage was never actually evaluated on measures the set, not the translation.
    evaluated = getattr(genesis, "evaluated_task_digests", None)
    if evaluated is not None and task_set_digest(tasks) not in evaluated:
        raise MigrationError(
            "the translation was offered a task set this lineage has never been evaluated on; "
            "verify a migration against the work the lineage was actually judged by"
        )

    grade = getattr(genesis, "grade", None)
    before = run_candidate(
        genesis.body_factory, tasks, genesis.isolation,
        admitted_isolation=genesis.admitted_isolation, grade=grade,
    )
    after = run_candidate(
        arrived_body_factory, tasks, genesis.isolation,
        admitted_isolation=genesis.admitted_isolation, grade=grade,
    )
    if not (before["completed"] and after["completed"]):
        # A comparison that could not run is not a comparison that passed.
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
    translate: Callable[[Mapping[str, Any], Mapping[str, Callable[..., Any]]], Callable[[], Any]],
    *,
    used_operations: Sequence[str],
    tasks: Sequence[Mapping[str, Any]] | None = None,
    permit_capability_loss: bool = False,
    translation_provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Carry a lineage into `substrate`, and prove it arrived as the same lineage.

    `translate` receives the departing state and **only the discovered operations**. It returns a
    body factory for the new substrate. `used_operations` declares what the translation relied on,
    and every one of them must have been discovered by probing.

    Supply `tasks` to have the translation verified: both bodies are run over them and the migration
    refuses a translation that solves strictly less, unless `permit_capability_loss` says a lossy
    arrival is intended. Without `tasks` the record reports `capability.measured: false` and claims
    nothing about what arrived, which is the honest reading of a migration nobody checked.
    """
    departing = lineage_state.decode_state(genesis.state)
    departure_head = genesis.journal.head

    undiscovered = sorted(set(used_operations) - set(substrate.discovered))
    if undiscovered:
        raise MigrationError(
            "the translation used operations the lineage never discovered: %s"
            % ", ".join(undiscovered)
        )

    body_factory = translate(departing, substrate.discovered)
    if not callable(body_factory):
        raise MigrationError("the translation did not produce a body factory")

    arrived = lineage_state.create_state(
        body_digest=digest_of(
            {"substrate": substrate.name, "from": departing["body_digest"], "via": sorted(used_operations)}
        ),
        components=departing["components"],
        vocabulary=departing["vocabulary"],
        tools=departing["tools"],
        acquisitions=departing["acquisitions"],
        observations=departing["observations"],
        generation=departing["generation"],
    )

    # Defensive, and deliberately untested: `arrived` is built above out of `departing`'s own fields,
    # so nothing can be dropped between them. The *comparison* is tested directly (see
    # tests/test_genesis_guards.py); this raise stays an assertion about an invariant the lines above
    # already establish. `scripts/check_genesis_guards_are_tested.py` reports it as a surviving
    # mutant; that is correct and expected.
    carried = carried_intact(departing, arrived)
    if not carried["intact"]:
        raise MigrationError("the lineage did not arrive intact: %s" % "; ".join(carried["lost"]))

    # Measured before anything is assigned, so a refused migration does not leave the lineage half
    # moved into a substrate it was not verified against.
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
            "departure_journal_head": departure_head,
            "used_operations": sorted(used_operations),
            "carried": carried["carried"],
            "capability": capability,
            # Measured, not asserted. This said `lineage_owned` whatever produced the translation,
            # so a host-authored translator was recorded as the lineage's own work — which is the
            # one distinction the provenance vocabulary exists to keep.
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
        "departure_journal_head": departure_head,
        "arrival_journal_entry": entry["entry_digest"],
        "journal_continues": entry["previous_digest"] == departure_head,
        "carried": carried["carried"],
        "capability": capability,
        "used_only_discovered_operations": True,
        "evolved_after_migration": False,
    }
    record["migration_digest"] = digest_of(record)
    return record


def carried_intact(departing: Mapping[str, Any], arrived: Mapping[str, Any]) -> dict[str, Any]:
    """Compare what left with what arrived, by identity rather than by count."""
    lost: list[str] = []
    carried: dict[str, Any] = {}
    for field_name in CARRIED:
        before = departing.get(field_name) or []
        after = arrived.get(field_name) or []
        # Multiset identity, not membership. Testing `identifier in after_ids` meant a record that
        # departed twice and arrived once counted as present both times, and an unexplained extra
        # arrival counted as nothing at all. "The same lineage arrived" is a claim about what there
        # is, not about what can be found.
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
    """Metamorphosis is not arriving intact. It is arriving and then evolving again.

    M084's correction is the reason this function exists: a lineage that only replays what it knew
    has transported its output, and transported output is not transported intelligence.

    Hati's fourth blocking correction is that "accepted a candidate" was too weak a proxy for that.
    Any acceptance counted, including one whose dependence on anything the lineage brought with it
    was never examined — so a migrated lineage that improved for unrelated reasons scored the same
    as one that built on what it carried. At least one post-migration acceptance must now have its
    causal dependency **established** by the ablation the cycle already runs. That is a bar the
    runtime measures rather than a stronger word for the same observation.
    """
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
    # Carrying the record is not carrying the capability. A migration whose executable capability was
    # never measured, or one explicitly permitted to lose it, cannot satisfy an objective whose whole
    # point is that what was acquired is kept.
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
