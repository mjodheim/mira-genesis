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
3. **The journal continues.** The post-migration chain links to the pre-migration head, so the
   descent is one lineage rather than two that resemble each other.

And the bar that decides the whole thing: `metamorphosis_succeeded` is false until the migrated
lineage has **accepted a new candidate in its new form**. Arriving intact is not success; arriving
and going on evolving is.
"""
from __future__ import annotations

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

    def record(self) -> dict[str, Any]:
        return {
            "schema": SUBSTRATE_SCHEMA,
            "name": self.name,
            "operations_available": sorted(self.operations),
            "operations_discovered": sorted(self._discovered),
            "probe_cost": self.probe_cost,
        }


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


def migrate(
    genesis,
    substrate: Substrate,
    translate: Callable[[Mapping[str, Any], Mapping[str, Callable[..., Any]]], Callable[[], Any]],
    *,
    used_operations: Sequence[str],
) -> dict[str, Any]:
    """Carry a lineage into `substrate`, and prove it arrived as the same lineage.

    `translate` receives the departing state and **only the discovered operations**. It returns a
    body factory for the new substrate. `used_operations` declares what the translation relied on,
    and every one of them must have been discovered by probing.
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

    genesis.state = arrived
    genesis.body_factory = body_factory
    entry = genesis.journal.append(
        "migration",
        arrived["generation"],
        {
            "substrate": substrate.record(),
            "departure_state_digest": departing["state_digest"],
            "arrival_state_digest": arrived["state_digest"],
            "departure_journal_head": departure_head,
            "used_operations": sorted(used_operations),
            "carried": carried["carried"],
            "provenance": provenance("lineage_owned", produced_by="lineage migration"),
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
        before_ids = [digest_of(item) for item in before]
        after_ids = [digest_of(item) for item in after]
        missing = [
            identifier for identifier in before_ids if identifier not in after_ids
        ]
        carried[field_name] = {
            "departed": len(before_ids),
            "arrived": len(after_ids),
            "missing": len(missing),
        }
        if missing:
            lost.append("%s lost %d of %d" % (field_name, len(missing), len(before_ids)))
    return {"intact": not lost, "lost": lost, "carried": carried}


def metamorphosis_succeeded(
    migration: Mapping[str, Any], post_migration_cycles: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Metamorphosis is not arriving intact. It is arriving and then evolving again.

    M084's correction is the reason this function exists: a lineage that only replays what it knew
    has transported its output, and transported output is not transported intelligence.
    """
    accepted = [record for record in post_migration_cycles if record.get("accepted")]
    reasons: list[str] = []
    if not migration.get("journal_continues"):
        reasons.append("the post-migration journal does not chain to the departure head")
    if not migration.get("used_only_discovered_operations"):
        reasons.append("the translation used operations the lineage never discovered")
    if any(count["missing"] for count in migration.get("carried", {}).values()):
        reasons.append("the lineage did not arrive intact")
    if not accepted:
        reasons.append(
            "the migrated lineage accepted no new candidate, so it replayed rather than evolved"
        )
    return {
        "succeeded": not reasons,
        "reasons": reasons,
        "accepted_after_migration": len(accepted),
        "cycles_after_migration": len(post_migration_cycles),
        "is_transported_intelligence_rather_than_transported_output": bool(accepted),
    }
