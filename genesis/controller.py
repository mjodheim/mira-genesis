"""Host-side controller for declarative Genesis evolution intents.

Lineage-owned decision machinery is untrusted. It receives a frozen, inert ``ControllerContext`` and
returns data, while only the host-side executor may spend budget, run probes, mutate state/journal,
migrate, or accept a descendant. The mechanism runs in the same limited subprocess boundary used for
candidate execution, so a read-only value is not mistaken for removal of ambient Python authority.

The current DEVELOPMENT mechanism is still an importable Python symbol rather than a generated policy
artifact. Once admitted, however, its identity is held in lineage state and survives process death and
migration: supplying a different callback is not an implicit policy update. ``ControllerContext`` also
contains bounded inert evidence copied from lineage state/journal, so a later policy can condition a
hypothesis on retained failures instead of seeing only counters.

``GenerateTransform`` is the first transformation surface that does not select a body preinstalled in
``World.artifacts``. The mechanism emits canonical program data, the controller constructs a
``ConfiguredBody`` over the fixed generated-program interpreter, and the existing sandbox/trust-root
path judges it. The generated language is deliberately tiny; endogeneity of candidate construction is
the property under test, not expressiveness.
"""
from __future__ import annotations

import inspect
import json
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping, Sequence

from genesis import probe
from genesis import programs
from genesis import state as lineage_state
from genesis.loop import Genesis, Proposal
from genesis.migration import Substrate, discover, metamorphosis_succeeded, migrate
from genesis.sandbox import run_isolated_callable
from genesis.trust_root import (
    TrustRootError,
    artifact_digest_of,
    canonical_bytes,
    digest_of,
    provenance,
)

CONTROLLER_SCHEMA = "genesis-controller-run-v1"
WORLD_SCHEMA = "genesis-world-v1"
CONTROLLER_CONTEXT_SCHEMA = "genesis-controller-context-v1"
MECHANISM_TOOL_NAME = "controller_mechanism"
MECHANISM_ROLE = "acquisition_policy"


class ControllerError(RuntimeError):
    """Raised when an intent or mechanism asks for authority it was not admitted to."""


@dataclass(frozen=True)
class Transform:
    name: str
    body: str
    rationale: Mapping[str, Any] = field(default_factory=dict)
    depends_on: str = ""


@dataclass(frozen=True)
class GenerateTransform:
    """Construct one new executable program from inert lineage-supplied data."""

    name: str
    operations: tuple[str, ...]
    rationale: Mapping[str, Any] = field(default_factory=dict)
    depends_on: str = ""
    input_field: str = "input"


@dataclass(frozen=True)
class AcquireComponent:
    demand: str
    new_component: str


@dataclass(frozen=True)
class SeparateVocabulary:
    demands: tuple[str, ...]


@dataclass(frozen=True)
class Migrate:
    substrate: str
    probe_for: tuple[str, ...]
    translation: str
    used_operations: tuple[str, ...]


@dataclass(frozen=True)
class Stop:
    reason: str = ""


@dataclass(frozen=True)
class ControllerContext:
    """The inert lineage view supplied to the isolated decision mechanism."""

    schema: str
    state_digest: str
    generation: int
    components: tuple[str, ...]
    vocabulary: tuple[str, ...]
    acquisitions: tuple[str, ...]
    observations: int
    evidence: tuple[Mapping[str, Any], ...]
    budget_remaining: Mapping[str, int]
    evaluated_task_sets: tuple[str, ...]
    body_artifact_digest: str
    mechanism_artifact_digest: str


@dataclass(frozen=True)
class World:
    schema: str
    tasks: tuple[Mapping[str, Any], ...]
    demands: Mapping[str, Sequence[Mapping[str, Any]]]
    substrates: Mapping[str, Substrate]
    probe_registry: str
    component_operations: Mapping[str, Sequence[str]]
    artifacts: Mapping[str, str]
    grade: Callable[[Mapping[str, Any], Any], str]

    def resolve(self, reference: str) -> Callable[[], Any]:
        target = self.artifacts.get(str(reference))
        if target is None:
            raise ControllerError(
                "the lineage named artifact %r, which this world does not contain" % reference
            )
        module_name, separator, qualname = str(target).partition(":")
        if not module_name or not separator or not qualname:
            raise ControllerError("artifact %r has no importable module:symbol target" % reference)
        resolved: Any = import_module(module_name)
        for part in qualname.split("."):
            resolved = getattr(resolved, part)
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


def world(*, tasks, demands, substrates, probe_registry, component_operations, artifacts, grade) -> World:
    return World(
        schema=WORLD_SCHEMA,
        tasks=tuple(dict(task) for task in tasks),
        demands={str(name): [dict(task) for task in value] for name, value in demands.items()},
        substrates=dict(substrates),
        probe_registry=str(probe_registry),
        component_operations={str(k): list(v) for k, v in component_operations.items()},
        artifacts={str(k): str(v) for k, v in artifacts.items()},
        grade=grade,
    )


LINEAGE = provenance("lineage_owned", produced_by="lineage mechanism")
MECHANISM_ADMISSION = provenance(
    "host_written",
    produced_by="Genesis controller admission",
    detail="initial decision mechanism becomes persistent lineage-held machinery",
)


def _transform(genesis: Genesis, here: World, intent: Transform) -> dict[str, Any]:
    proposal = Proposal(
        name=intent.name,
        body_factory=here.resolve(intent.body),
        provenance=LINEAGE,
        rationale=dict(intent.rationale),
        depends_on=intent.depends_on,
    )
    return genesis.cycle(here.tasks, lambda _context, _tasks: proposal)


def _generate_transform(genesis: Genesis, here: World, intent: GenerateTransform) -> dict[str, Any]:
    """Build a body from lineage-supplied program data and judge it through the normal cycle."""
    dependencies = (intent.depends_on,) if intent.depends_on else ()
    try:
        body = programs.artifact(
            registry_reference=here.probe_registry,
            operations=intent.operations,
            input_field=intent.input_field,
            dependencies=dependencies,
        )
    except programs.ProgramError as problem:
        raise ControllerError(str(problem)) from problem
    proposal = Proposal(
        name=intent.name,
        body_factory=body,
        provenance=LINEAGE,
        rationale={
            **dict(intent.rationale),
            "generated_program": {
                "schema": programs.PROGRAM_SCHEMA,
                "operations": list(intent.operations),
                "input_field": intent.input_field,
            },
        },
        depends_on=intent.depends_on,
    )
    record = genesis.cycle(here.tasks, lambda _context, _tasks: proposal)
    return {
        **record,
        "generated_program": {
            "schema": programs.PROGRAM_SCHEMA,
            "operations": list(intent.operations),
            "input_field": intent.input_field,
        },
        "generated_body_artifact": artifact_digest_of(body),
        "selected_from_world_artifacts": False,
    }


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
            {"proposed": False, "detail": found["why_not"], "diagnosis_digest": digest_of(found)},
        )
        return {"acquired": False, "why_not": found["why_not"], "diagnosis": found}
    certificate = probe.certificate_from_experiment(found, new_component=intent.new_component)
    genesis.adopt_component(certificate, provenance=LINEAGE)
    return {
        "acquired": True,
        "component": intent.new_component,
        "probe_is_experimental_not_an_oracle": True,
        "registry_exhausted": found["registry_exhausted"],
        "reachable_with_wider_operations": found["reachable_with_wider_operations"],
        "composition_the_lineage_found": found["resolving_composition"]["operations"],
        "compositions_run": sum(record["attempts"] for record in found["probes"]),
        "probed": [record["component"] for record in found["probes"]],
        "registry_after": lineage_state.component_names(genesis.state),
    }


def _separate_vocabulary(genesis: Genesis, here: World, intent: SeparateVocabulary) -> dict[str, Any]:
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
    record = migrate(
        genesis,
        substrate,
        here.resolve(intent.translation),
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
    GenerateTransform: _generate_transform,
    AcquireComponent: _acquire_component,
    SeparateVocabulary: _separate_vocabulary,
    Migrate: _migrate,
}


def _canonical_record(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(canonical_bytes(dict(value)).decode("utf-8"))


def bound_mechanism_artifact(genesis: Genesis) -> dict[str, Any] | None:
    records = [
        tool
        for tool in genesis.state.get("tools", [])
        if tool.get("name") == MECHANISM_TOOL_NAME and tool.get("role") == MECHANISM_ROLE
    ]
    if not records:
        return None
    if len(records) != 1:
        raise ControllerError("lineage state carries more than one admitted controller mechanism")
    artifact = records[0].get("artifact")
    if not isinstance(artifact, Mapping):
        raise ControllerError("the admitted controller mechanism carries no artifact identity")
    return _canonical_record(artifact)


def _bind_mechanism(genesis: Genesis, artifact: Mapping[str, Any]) -> bool:
    admitted = _canonical_record(artifact)
    current = bound_mechanism_artifact(genesis)
    if current is not None:
        if current != admitted:
            raise ControllerError(
                "this lineage is already admitted under controller mechanism %s; replacing it with "
                "%s requires an explicit evidence-backed machinery update"
                % (current.get("artifact_digest"), admitted.get("artifact_digest"))
            )
        return False

    genesis.state = lineage_state.create_state(
        body_digest=genesis.state["body_digest"],
        components=genesis.state["components"],
        vocabulary=genesis.state["vocabulary"],
        tools=genesis.state["tools"]
        + [
            {
                "name": MECHANISM_TOOL_NAME,
                "role": MECHANISM_ROLE,
                "artifact": admitted,
                "provenance": MECHANISM_ADMISSION,
            }
        ],
        acquisitions=genesis.state["acquisitions"],
        observations=genesis.state["observations"],
        generation=genesis.state["generation"],
    )
    genesis.journal.append(
        "observation",
        genesis.state["generation"],
        {
            "arm": "controller_mechanism_admission",
            "artifact_digest": admitted.get("artifact_digest", ""),
            "new_state_digest": genesis.state["state_digest"],
        },
    )
    return True


def _lineage_evidence(genesis: Genesis) -> tuple[Mapping[str, Any], ...]:
    records: list[dict[str, Any]] = []
    for observation in genesis.state.get("observations", []):
        records.append({"kind": "observation", "record": _canonical_record(observation)})
    for acquisition in genesis.state.get("acquisitions", []):
        records.append({"kind": "acquisition", "record": _canonical_record(acquisition)})
    for component in genesis.state.get("components", []):
        certificate = component.get("certificate")
        if isinstance(certificate, Mapping):
            records.append(
                {
                    "kind": "component_certificate",
                    "name": str(component.get("name", "")),
                    "record": _canonical_record(certificate),
                }
            )
    for feature in genesis.state.get("vocabulary", []):
        certificate = feature.get("certificate")
        if isinstance(certificate, Mapping):
            records.append(
                {
                    "kind": "vocabulary_certificate",
                    "name": str(feature.get("name", "")),
                    "record": _canonical_record(certificate),
                }
            )
    for kind in ("diagnosis", "candidate_rejected", "migration"):
        for entry in genesis.journal.of_kind(kind):
            records.append(
                {
                    "kind": "journal_%s" % kind,
                    "record": _canonical_record(entry.get("payload") or {}),
                    "entry_digest": str(entry.get("entry_digest", "")),
                }
            )
    return tuple(MappingProxyType(_canonical_record(record)) for record in records)


def _controller_context(genesis: Genesis) -> ControllerContext:
    base = genesis.context()
    mechanism = bound_mechanism_artifact(genesis)
    return ControllerContext(
        schema=CONTROLLER_CONTEXT_SCHEMA,
        state_digest=base.state_digest,
        generation=base.generation,
        components=base.components,
        vocabulary=base.vocabulary,
        acquisitions=base.acquisitions,
        observations=base.observations,
        evidence=_lineage_evidence(genesis),
        budget_remaining=base.budget_remaining,
        evaluated_task_sets=base.evaluated_task_sets,
        body_artifact_digest=base.body_artifact_digest,
        mechanism_artifact_digest=""
        if mechanism is None
        else str(mechanism.get("artifact_digest", "")),
    )


def _context_record(context: ControllerContext) -> dict[str, Any]:
    return {
        "schema": context.schema,
        "state_digest": context.state_digest,
        "generation": context.generation,
        "components": list(context.components),
        "vocabulary": list(context.vocabulary),
        "acquisitions": list(context.acquisitions),
        "observations": context.observations,
        "evidence": [dict(record) for record in context.evidence],
        "budget_remaining": dict(context.budget_remaining),
        "evaluated_task_sets": list(context.evaluated_task_sets),
        "body_artifact_digest": context.body_artifact_digest,
        "mechanism_artifact_digest": context.mechanism_artifact_digest,
    }


def _context_from_record(record: Mapping[str, Any]) -> ControllerContext:
    evidence = tuple(
        MappingProxyType(_canonical_record(value))
        for value in record.get("evidence") or []
        if isinstance(value, Mapping)
    )
    return ControllerContext(
        schema=str(record["schema"]),
        state_digest=str(record["state_digest"]),
        generation=int(record["generation"]),
        components=tuple(str(v) for v in record.get("components") or []),
        vocabulary=tuple(str(v) for v in record.get("vocabulary") or []),
        acquisitions=tuple(str(v) for v in record.get("acquisitions") or []),
        observations=int(record.get("observations", 0)),
        evidence=evidence,
        budget_remaining=MappingProxyType(
            {str(k): int(v) for k, v in (record.get("budget_remaining") or {}).items()}
        ),
        evaluated_task_sets=tuple(str(v) for v in record.get("evaluated_task_sets") or []),
        body_artifact_digest=str(record["body_artifact_digest"]),
        mechanism_artifact_digest=str(record.get("mechanism_artifact_digest") or ""),
    )


def _intent_record(intent: Any) -> dict[str, Any]:
    if intent is None:
        return {"type": "none"}
    if isinstance(intent, Transform):
        return {
            "type": "Transform",
            "name": intent.name,
            "body": intent.body,
            "rationale": dict(intent.rationale),
            "depends_on": intent.depends_on,
        }
    if isinstance(intent, GenerateTransform):
        return {
            "type": "GenerateTransform",
            "name": intent.name,
            "operations": list(intent.operations),
            "rationale": dict(intent.rationale),
            "depends_on": intent.depends_on,
            "input_field": intent.input_field,
        }
    if isinstance(intent, AcquireComponent):
        return {
            "type": "AcquireComponent",
            "demand": intent.demand,
            "new_component": intent.new_component,
        }
    if isinstance(intent, SeparateVocabulary):
        return {"type": "SeparateVocabulary", "demands": list(intent.demands)}
    if isinstance(intent, Migrate):
        return {
            "type": "Migrate",
            "substrate": intent.substrate,
            "probe_for": list(intent.probe_for),
            "translation": intent.translation,
            "used_operations": list(intent.used_operations),
        }
    if isinstance(intent, Stop):
        return {"type": "Stop", "reason": intent.reason}
    raise ControllerError("the lineage returned %r, which is not an intent" % (intent,))


def _intent_from_record(record: Mapping[str, Any]) -> Any:
    kind = str(record.get("type") or "")
    if kind == "none":
        return None
    if kind == "Transform":
        return Transform(
            name=str(record["name"]),
            body=str(record["body"]),
            rationale=dict(record.get("rationale") or {}),
            depends_on=str(record.get("depends_on") or ""),
        )
    if kind == "GenerateTransform":
        return GenerateTransform(
            name=str(record["name"]),
            operations=tuple(str(v) for v in record.get("operations") or []),
            rationale=dict(record.get("rationale") or {}),
            depends_on=str(record.get("depends_on") or ""),
            input_field=str(record.get("input_field") or "input"),
        )
    if kind == "AcquireComponent":
        return AcquireComponent(
            demand=str(record["demand"]), new_component=str(record["new_component"])
        )
    if kind == "SeparateVocabulary":
        return SeparateVocabulary(demands=tuple(str(v) for v in record.get("demands") or []))
    if kind == "Migrate":
        return Migrate(
            substrate=str(record["substrate"]),
            probe_for=tuple(str(v) for v in record.get("probe_for") or []),
            translation=str(record["translation"]),
            used_operations=tuple(str(v) for v in record.get("used_operations") or []),
        )
    if kind == "Stop":
        return Stop(reason=str(record.get("reason") or ""))
    raise ControllerError("isolated mechanism returned an unrecognised intent record %r" % kind)


def _resolve_artifact_record(record: Mapping[str, Any]) -> Callable[..., Any]:
    if record.get("kind") != "importable_symbol":
        raise ControllerError("controller mechanisms must be importable symbols in DEVELOPMENT")
    module_name = str(record.get("module") or "")
    qualname = str(record.get("qualname") or "")
    target: Any = import_module(module_name)
    for part in qualname.split("."):
        target = getattr(target, part)
    rebuilt = artifact_digest_of(target)
    if rebuilt["artifact_digest"] != record.get("artifact_digest"):
        raise ControllerError("controller mechanism no longer matches its admitted artifact")
    return target


def _isolated_mechanism_entry(payload: Mapping[str, Any]) -> dict[str, Any]:
    mechanism = _resolve_artifact_record(payload.get("mechanism") or {})
    context = _context_from_record(payload.get("context") or {})
    return _intent_record(mechanism(context))


def _canonical_mechanism(
    mechanism: Callable[[ControllerContext], Any],
) -> Callable[[ControllerContext], Any]:
    if getattr(mechanism, "__module__", "") != "__main__":
        return mechanism
    source = inspect.getsourcefile(mechanism)
    if not source:
        raise ControllerError(
            "a __main__ mechanism has no source path from which to derive an importable identity"
        )
    path = Path(source).resolve()
    root = Path.cwd().resolve()
    try:
        relative = path.relative_to(root).with_suffix("")
    except ValueError as problem:
        raise ControllerError("a __main__ mechanism outside the repository cannot be admitted") from problem
    module_name = ".".join(relative.parts)
    resolved: Any = import_module(module_name)
    for part in str(getattr(mechanism, "__qualname__", "")).split("."):
        resolved = getattr(resolved, part)
    return resolved


def _admit_mechanism(
    genesis: Genesis, mechanism: Callable[[ControllerContext], Any]
) -> tuple[Callable[[ControllerContext], Any], dict[str, Any], bool]:
    admitted = _canonical_mechanism(mechanism)
    artifact = artifact_digest_of(admitted)
    if artifact.get("kind") != "importable_symbol":
        raise ControllerError("controller mechanisms must be content-addressed importable symbols")
    newly_bound = _bind_mechanism(genesis, artifact)
    return admitted, artifact, newly_bound


def _invoke_admitted_mechanism(
    genesis: Genesis,
    mechanism: Callable[[ControllerContext], Any],
    artifact: Mapping[str, Any],
) -> Any:
    current = bound_mechanism_artifact(genesis)
    if current is None or current != _canonical_record(artifact):
        raise ControllerError("the lineage no longer carries the controller mechanism it was admitted under")
    result = run_isolated_callable(
        _isolated_mechanism_entry,
        {"mechanism": artifact, "context": _context_record(_controller_context(genesis))},
        genesis.isolation,
        admitted_isolation=genesis.admitted_isolation,
    )
    if not result["completed"]:
        raise ControllerError(
            "the lineage mechanism did not run under the admitted boundary: %s"
            % (
                result.get("reason")
                or result.get("traceback")
                or "instrument failure"
            )
        )
    value = result.get("value")
    if not isinstance(value, Mapping):
        raise ControllerError("the isolated mechanism returned no intent record")
    return _intent_from_record(value)


def _invoke_mechanism(
    genesis: Genesis, mechanism: Callable[[ControllerContext], Any]
) -> tuple[Any, dict[str, Any]]:
    admitted, artifact, _ = _admit_mechanism(genesis, mechanism)
    return _invoke_admitted_mechanism(genesis, admitted, artifact), artifact


def run(
    genesis: Genesis,
    here: World,
    mechanism: Callable[[ControllerContext], Any],
    *,
    max_steps: int = 32,
    checkpoint_directory: Path | None = None,
) -> dict[str, Any]:
    """Drive one lineage, making each committed controller step durable when storage is supplied."""
    steps: list[dict[str, Any]] = []
    migration_record: Mapping[str, Any] | None = None
    cycles_after_migration: list[Mapping[str, Any]] = []
    admitted, mechanism_artifact, newly_bound = _admit_mechanism(genesis, mechanism)
    checkpoint_path = Path(checkpoint_directory) if checkpoint_directory is not None else None
    admission_checkpoint = ""
    if checkpoint_path is not None and newly_bound:
        admission_checkpoint = genesis.persist(checkpoint_path)["checkpoint"]

    for _ in range(max_steps):
        intent = _invoke_admitted_mechanism(genesis, admitted, mechanism_artifact)
        if intent is None or isinstance(intent, Stop):
            steps.append(
                {"intent": "stop", "reason": getattr(intent, "reason", "no further intent")}
            )
            break
        handler = HANDLERS.get(type(intent))
        if handler is None:
            raise ControllerError("the lineage returned %r, which is not an intent" % (intent,))
        outcome = handler(genesis, here, intent)
        step = {
            "intent": type(intent).__name__,
            **_summary(intent, outcome),
            "lineage": _lineage(genesis),
        }
        if checkpoint_path is not None:
            step["checkpoint_digest"] = genesis.persist(checkpoint_path)["checkpoint"]
            step["durable_before_next_intent"] = True
        else:
            step["durable_before_next_intent"] = False
        steps.append(step)
        if isinstance(intent, Migrate):
            migration_record = outcome["migration"]
        elif isinstance(intent, (Transform, GenerateTransform)) and migration_record is not None:
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
        "mechanism_execution_isolated": True,
        "mechanism_artifact_digest": str(mechanism_artifact.get("artifact_digest") or ""),
        "mechanism_identity_persistent": bound_mechanism_artifact(genesis)
        == _canonical_record(mechanism_artifact),
        "durable_step_persistence": checkpoint_path is not None,
        "mechanism_admission_checkpoint": admission_checkpoint,
    }
    if migration_record is not None:
        record["metamorphosis"] = metamorphosis_succeeded(migration_record, cycles_after_migration)
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
        "mechanism_artifact_digest": str(
            (bound_mechanism_artifact(genesis) or {}).get("artifact_digest", "")
        ),
    }


def _summary(intent: Any, outcome: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(intent, (Transform, GenerateTransform)):
        summary = {
            "name": intent.name,
            "accepted": outcome.get("accepted"),
            "reason": outcome.get("reason", ""),
            "outcomes_are_self_reported": outcome.get("outcomes_are_self_reported"),
            "causal_dependency": outcome.get("causal_dependency"),
            "stopped": outcome.get("stopped", False),
        }
        if isinstance(intent, GenerateTransform):
            summary.update(
                {
                    "generated_program": outcome.get("generated_program"),
                    "generated_body_artifact": outcome.get("generated_body_artifact"),
                    "selected_from_world_artifacts": False,
                }
            )
        return summary
    return {k: v for k, v in outcome.items() if k not in ("migration", "diagnosis")}
