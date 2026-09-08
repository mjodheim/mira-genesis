"""The controller: a lineage proposes intents, the host-side executor is the only thing that acts.

The demonstration script used to *be* the architecture. It called the probe functions, assigned
`genesis.state`, appended to the journal, invoked the migration and chose every proposal. The
primitives ran in one process, but the sequencing that the objective is about lived in a host script
— so what the run demonstrated was that a person can call the pieces in the right order.

Here the lineage-owned mechanism is a function of one argument:

    mechanism(LineageContext) -> Intent

It receives a frozen value and returns **data**. It cannot spend budget, run a probe, touch the
journal, replace the body or commit a state. Every one of those is done by the executor below, which
validates the intent first and records what it did. That is the capability boundary the hardening
design asks for; a frozen dataclass that still held references to runtime services would be a naming
convention rather than a boundary.

What the host supplies is a `World`: the task stream, the demands the lineage may investigate, the
substrates it may discover, the operation registry probes are composed from, and the resolver that
turns an artifact reference into something runnable. The lineage chooses **what to attempt**; the
world bounds **what exists**. Neither is the other.

**A limitation, stated rather than implied.** Intents name bodies by importable artifact reference,
so in this DEVELOPMENT apparatus a lineage can only propose transformations that already exist as
importable symbols. A lineage that generates its own code needs content-addressed payloads the
executor can build and run, which this does not yet do. What is closed here is the authority
question — the mechanism cannot reach the runtime — not the code-generation question.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any, Callable, Mapping, Sequence

from genesis import probe
from genesis import state as lineage_state
from genesis.loop import Genesis, LineageContext, Proposal
from genesis.migration import Substrate, discover, metamorphosis_succeeded, migrate
from genesis.trust_root import TrustRootError, digest_of, provenance

CONTROLLER_SCHEMA = "genesis-controller-run-v1"
WORLD_SCHEMA = "genesis-world-v1"


class ControllerError(RuntimeError):
    """Raised when an intent asks for something the lineage is not entitled to."""


# ---------------------------------------------------------------------------------------------
# The intent vocabulary: what a lineage may ask for, as data
# ---------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Transform:
    """Propose a candidate body, and name the earlier acquisition it claims to have needed.

    There is no field for an ablation arm. The runtime builds the counterfactual from the
    candidate's own configuration and checks that it is the candidate minus exactly `depends_on`; an
    arm chosen by the proposer is the proposer's account of what the counterfactual is.
    """

    name: str
    body: str
    rationale: Mapping[str, Any] = field(default_factory=dict)
    depends_on: str = ""


@dataclass(frozen=True)
class AcquireComponent:
    """Ask for an experimental diagnosis, and name the class it would license."""

    demand: str
    new_component: str


@dataclass(frozen=True)
class SeparateVocabulary:
    """Ask whether two demands the current vocabulary reads alike have different measured causes."""

    demands: tuple[str, ...]


@dataclass(frozen=True)
class Migrate:
    """Ask to discover a substrate and carry the lineage into it."""

    substrate: str
    probe_for: tuple[str, ...]
    translation: str
    used_operations: tuple[str, ...]


@dataclass(frozen=True)
class Stop:
    """The lineage has nothing further to attempt."""

    reason: str = ""


@dataclass(frozen=True)
class World:
    """What exists, as the host admits it. The lineage may reach nothing outside this.

    `artifacts` maps an artifact reference to an importable symbol. Resolution happens here rather
    than in the mechanism, so a lineage names what it wants and the executor decides whether that
    name is something it may have.
    """

    schema: str
    tasks: tuple[Mapping[str, Any], ...]
    demands: Mapping[str, Sequence[Mapping[str, Any]]]
    substrates: Mapping[str, Substrate]
    probe_registry: str
    component_operations: Mapping[str, Sequence[str]]
    artifacts: Mapping[str, str]
    grade: Callable[[Mapping[str, Any], Any], str]

    def resolve(self, reference: str) -> Callable[[], Any]:
        """Turn an artifact reference into something runnable, or refuse."""
        target = self.artifacts.get(str(reference))
        if target is None:
            raise ControllerError(
                "the lineage named artifact %r, which this world does not contain" % reference
            )
        module_name, _, symbol = str(target).partition(":")
        resolved = getattr(import_module(module_name), symbol)
        if not callable(resolved):
            raise ControllerError("artifact %r does not resolve to something runnable" % reference)
        return resolved

    def record(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "tasks": len(self.tasks),
            "demands": sorted(self.demands),
            "substrates": sorted(self.substrates),
            "artifacts": sorted(self.artifacts),
        }


def world(
    *,
    tasks: Sequence[Mapping[str, Any]],
    demands: Mapping[str, Sequence[Mapping[str, Any]]],
    substrates: Mapping[str, Substrate],
    probe_registry: str,
    component_operations: Mapping[str, Sequence[str]],
    artifacts: Mapping[str, str],
    grade: Callable[[Mapping[str, Any], Any], str],
) -> World:
    return World(
        schema=WORLD_SCHEMA,
        tasks=tuple(dict(task) for task in tasks),
        demands={name: [dict(task) for task in value] for name, value in demands.items()},
        substrates=dict(substrates),
        probe_registry=str(probe_registry),
        component_operations={k: list(v) for k, v in component_operations.items()},
        artifacts=dict(artifacts),
        grade=grade,
    )


# ---------------------------------------------------------------------------------------------
# The executor: the only thing that acts
# ---------------------------------------------------------------------------------------------
LINEAGE = provenance("lineage_owned", produced_by="lineage mechanism")


def _transform(genesis: Genesis, here: World, intent: Transform) -> dict[str, Any]:
    body = here.resolve(intent.body)
    proposal = Proposal(
        name=intent.name,
        body_factory=body,
        provenance=LINEAGE,
        rationale=dict(intent.rationale),
        depends_on=intent.depends_on,
    )
    return genesis.cycle(here.tasks, lambda _context, _tasks: proposal)


def _acquire_component(genesis: Genesis, here: World, intent: AcquireComponent) -> dict[str, Any]:
    demand = here.demands.get(intent.demand)
    if demand is None:
        raise ControllerError("no demand named %r in this world" % intent.demand)
    found = probe.diagnose_by_experiment(
        genesis.state,
        registry_reference=here.probe_registry,
        component_operations=here.component_operations,
        tasks=demand,
        isolation=genesis.isolation,
        budget=genesis.budget,
    )
    if not found["licenses_naming_a_new_component"]:
        genesis.journal.append(
            "diagnosis",
            genesis.state["generation"],
            {"proposed": False, "detail": found["why_not"]},
        )
        return {"acquired": False, "why_not": found["why_not"], "diagnosis": found}
    certificate = probe.certificate_from_experiment(found, new_component=intent.new_component)
    genesis.adopt_component(certificate, provenance=LINEAGE)
    return {
        "acquired": True,
        "component": intent.new_component,
        # Nothing here answered "does this component resolve the demand". Compositions were built,
        # run in isolation and judged on raw per-task rows.
        "probe_is_experimental_not_an_oracle": True,
        "registry_exhausted": found["registry_exhausted"],
        "reachable_with_wider_operations": found["reachable_with_wider_operations"],
        "composition_the_lineage_found": found["resolving_composition"]["operations"],
        "compositions_run": sum(record["attempts"] for record in found["probes"]),
        "probed": [record["component"] for record in found["probes"]],
        "registry_after": lineage_state.component_names(genesis.state),
    }


def _separate_vocabulary(
    genesis: Genesis, here: World, intent: SeparateVocabulary
) -> dict[str, Any]:
    demands = []
    for name in intent.demands:
        demand = here.demands.get(name)
        if demand is None:
            raise ControllerError("no demand named %r in this world" % name)
        demands.append(demand)
    pair = probe.find_confusable_pair_by_experiment(
        genesis.state,
        demands,
        registry_reference=here.probe_registry,
        component_operations=here.component_operations,
        isolation=genesis.isolation,
        budget=genesis.budget,
    )
    if pair is None:
        genesis.journal.append(
            "diagnosis",
            genesis.state["generation"],
            {"proposed": False, "detail": "no measured confusable pair"},
        )
        return {"extended": False, "why_not": "no measured confusable pair among these demands"}
    certificate = probe.vocabulary_certificate_from_experiment(genesis.state, pair)
    genesis.adopt_vocabulary(certificate, provenance=LINEAGE)
    return {
        "extended": True,
        # The separating feature was read out of two measurements, not chosen and then justified.
        "rests_on_a_host_supplied_oracle": False,
        "shared_prior_row": pair["shared_prior_row"],
        "limiting_components": pair["limiting_components"],
        "resolving_operations": [m["resolving_operations"] for m in pair["measurements"]],
        "feature_read_out_of_the_measurements": certificate["new_feature"],
        "vocabulary_after": lineage_state.vocabulary_names(genesis.state),
    }


def _migrate(genesis: Genesis, here: World, intent: Migrate) -> dict[str, Any]:
    substrate = here.substrates.get(intent.substrate)
    if substrate is None:
        raise ControllerError("no substrate named %r in this world" % intent.substrate)
    probing = discover(substrate, list(intent.probe_for), genesis.budget)
    # The artifact *is* the translator, called with the departure copy and the capability handles.
    # Wrapping a body factory in a lambda that ignored both would have declared operations the
    # translation never touched, which the migration now derives rather than believes.
    translation = here.resolve(intent.translation)
    record = migrate(
        genesis,
        substrate,
        translation,
        used_operations=list(intent.used_operations),
        tasks=here.tasks,
        translation_provenance=provenance(
            "host_written",
            produced_by="world-supplied translation artifact",
            detail=str(intent.translation),
        ),
    )
    return {
        "found": probing["found"],
        "missing": probing["missing"],
        "journal_continues": record["journal_continues"],
        "nothing_lost": all(c["missing"] == 0 for c in record["carried"].values()),
        "capability_measured": record["capability"]["measured"],
        "capability_preserved": record["capability"]["preserved"],
        "solved_before_and_after": [
            record["capability"]["solved_before"],
            record["capability"]["solved_after"],
        ],
        "migration": record,
    }


HANDLERS = {
    Transform: _transform,
    AcquireComponent: _acquire_component,
    SeparateVocabulary: _separate_vocabulary,
    Migrate: _migrate,
}


def run(
    genesis: Genesis,
    here: World,
    mechanism: Callable[[LineageContext], Any],
    *,
    max_steps: int = 32,
) -> dict[str, Any]:
    """Drive the lineage until it stops, its budget refuses, or the step bound is reached.

    The mechanism sees `genesis.context()` and nothing else. Every effect below this line is the
    executor's, which is what makes the sequencing a property of the runtime rather than of whoever
    wrote the script that called it.
    """
    steps: list[dict[str, Any]] = []
    migration_record: Mapping[str, Any] | None = None
    cycles_after_migration: list[Mapping[str, Any]] = []

    for _ in range(max_steps):
        intent = mechanism(genesis.context())
        if intent is None or isinstance(intent, Stop):
            steps.append(
                {"intent": "stop", "reason": getattr(intent, "reason", "no further intent")}
            )
            break
        handler = HANDLERS.get(type(intent))
        if handler is None:
            raise ControllerError("the lineage returned %r, which is not an intent" % (intent,))
        outcome = handler(genesis, here, intent)
        steps.append(
            {
                "intent": type(intent).__name__,
                **_summary(intent, outcome),
                # What the lineage looked like after this intent. A rejection that is kept as an
                # observation, an acquisition that entered the registry, a generation that advanced:
                # all of it is read from the state the executor committed, not narrated by a script.
                "lineage": _lineage(genesis),
            }
        )
        if isinstance(intent, Migrate):
            migration_record = outcome["migration"]
        elif isinstance(intent, Transform) and migration_record is not None:
            cycles_after_migration.append(outcome)
        if outcome.get("stopped"):
            break

    record = {
        "schema": CONTROLLER_SCHEMA,
        "world": here.record(),
        "steps": steps,
        "final_generation": genesis.state["generation"],
        "final_components": lineage_state.component_names(genesis.state),
        "final_vocabulary": lineage_state.vocabulary_names(genesis.state),
        "causal_chain": genesis.causal_chain(),
        "budget": genesis.budget.record(),
    }
    if migration_record is not None:
        record["metamorphosis"] = metamorphosis_succeeded(
            migration_record, cycles_after_migration
        )
    record["run_digest"] = digest_of(record)
    return record


def _lineage(genesis: Genesis) -> dict[str, Any]:
    return {
        "generation": genesis.state["generation"],
        "components": lineage_state.component_names(genesis.state),
        "vocabulary": lineage_state.vocabulary_names(genesis.state),
        "acquisitions": len(genesis.state["acquisitions"]),
        "observations_kept": len(genesis.state["observations"]),
        "state_digest": genesis.state["state_digest"],
    }


def _summary(intent: Any, outcome: Mapping[str, Any]) -> dict[str, Any]:
    """Keep the campaign record readable without copying whole sandbox results into it."""
    if isinstance(intent, Transform):
        return {
            "name": intent.name,
            "accepted": outcome.get("accepted"),
            "reason": outcome.get("reason", ""),
            "outcomes_are_self_reported": outcome.get("outcomes_are_self_reported"),
            "causal_dependency": outcome.get("causal_dependency"),
            "stopped": outcome.get("stopped", False),
        }
    return {k: v for k, v in outcome.items() if k not in ("migration", "diagnosis")}
