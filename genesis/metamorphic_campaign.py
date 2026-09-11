"""Persistent runtime-owned campaign across objectives and one executable-form transition.

The metamorphic policy loop already owns body, search-policy and MetaPolicy hand-offs inside one
objective. The form-continuation path already proves that a migrated generated body can keep evolving.
What remained outside the program was the *handoff between those two facts*: a launcher still called
objective 1, manually migrated the body, reconstructed the process and then called objective 2.

This module turns that handoff into versioned runtime state. The environment supplies an ordered
sequence of objective stages and, optionally, one substrate-transition challenge. Genesis persists a
content-addressed cursor after every completed stage, so process death resumes the same campaign
instead of asking a launcher which architectural step comes next.

The migration adapter is deliberately fixed DEVELOPMENT apparatus. It probes only the admitted
``rebind_program`` substrate capability and uses the existing canonical generated-program translator;
the world no longer supplies a translation artifact for this path. That is enough to remove human
architectural intervention between the stages, but it is not a claim that Genesis synthesised a new
migration algorithm or substrate interface.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from genesis import controller
from genesis.artifacts import ConfiguredBody
from genesis import meta_policy_controller as meta
from genesis import metamorphic_form_runtime as form_runtime
from genesis import migration, objective_policy_controller as opc, policies, policy_controller
from genesis import program_forms, programs
from genesis import state as lineage_state
from genesis.trust_root import artifact_digest_of, digest_of, provenance

CAMPAIGN_SCHEMA = "genesis-persistent-metamorphic-campaign-v1"
STAGE_SCHEMA = "genesis-metamorphic-campaign-stage-v1"
CURSOR_SCHEMA = "genesis-metamorphic-campaign-cursor-v1"
CURSOR_TOOL_NAME = "metamorphic_campaign_cursor"
CURSOR_ROLE = "persistent_campaign_progress"
FORM_REBIND_STRATEGY = "rebind_current_generated_program_v1"
TRANSITION_PROBE_ROUND_SCHEMA = "genesis-architectural-transition-probe-round-v1"
TRANSITION_PROBE_ROUND_KIND = "architectural_transition_probe_round"
_TRANSITION_RESERVED = "reserved"
_TRANSITION_CHARGED = "charged"
_TRANSITION_COMPLETED = "completed"
_TRANSITION_CRASH_INCOMPLETE = "crash_incomplete"


class MetamorphicCampaignError(RuntimeError):
    """Raised when a campaign cannot continue as the same admitted lineage/program."""


class _PrepaidProbeBudget:
    """Consume probe slots that were already durably charged to the real lineage budget."""

    def __init__(self, base, allowance: int):
        self._base = base
        self._allowance = int(allowance)
        self.limits = base.limits
        self.spent = base.spent

    def remaining(self, dimension: str) -> int:
        if dimension == "probes":
            return self._allowance
        return self._base.remaining(dimension)

    def spend(self, dimension: str, amount: int = 1) -> int:
        if amount < 0:
            raise MetamorphicCampaignError("cannot spend a negative prepaid probe amount")
        if dimension != "probes":
            return self._base.spend(dimension, amount)
        if self._allowance < amount:
            raise MetamorphicCampaignError(
                "architectural transition exhausted its durably prepaid probe reservation"
            )
        self._allowance -= amount
        return self._allowance

    def record(self) -> dict[str, Any]:
        return self._base.record()

    def unused(self) -> int:
        return self._allowance


@dataclass(frozen=True)
class ObjectiveStage:
    """One environmental objective to be worked by the integrated body/machinery loop."""

    world: controller.World
    name: str = ""


@dataclass(frozen=True)
class FormMigrationStage:
    """An explicit host-authored form transition kept for backwards-compatible DEVELOPMENT runs."""

    world: controller.World
    substrate: str
    name: str = ""


@dataclass(frozen=True)
class FormRequirementStage:
    """Environmental form constraint; the runtime chooses whether to stay or migrate."""

    world: controller.World
    allowed_targets: tuple[str, ...]
    name: str = ""


def objective(world: controller.World, *, name: str = "") -> ObjectiveStage:
    return ObjectiveStage(world=world, name=str(name))


def form_migration(
    world: controller.World, substrate: str, *, name: str = ""
) -> FormMigrationStage:
    return FormMigrationStage(world=world, substrate=str(substrate), name=str(name))


def require_form(
    world: controller.World, allowed_targets: Sequence[str], *, name: str = ""
) -> FormRequirementStage:
    targets = tuple(sorted({str(target) for target in allowed_targets if str(target)}))
    if not targets:
        raise MetamorphicCampaignError("a form requirement admits no executable target")
    return FormRequirementStage(world=world, allowed_targets=targets, name=str(name))


def _assert_world_registry_matches_policy(genesis, world: controller.World, seed_policy=None) -> None:
    """Refuse a world that would execute candidates under a registry other than held machinery."""
    held = policy_controller.bound_policy(genesis)
    candidate = held
    if candidate is None and seed_policy is not None:
        candidate = policies.validate(seed_policy)
    if candidate is None:
        return
    if str(candidate["registry_reference"]) != str(world.probe_registry):
        raise MetamorphicCampaignError(
            "campaign world registry %r differs from held search-policy registry %r"
            % (world.probe_registry, candidate["registry_reference"])
        )


def _substrate_identity(substrate: migration.Substrate) -> dict[str, Any]:
    operations: dict[str, Any] = {}
    for name in sorted(substrate.operations):
        operation = substrate.operations[name]
        operations[str(name)] = artifact_digest_of(operation)
    payload = {
        "name": substrate.name,
        "probe_cost": int(substrate.probe_cost),
        "operations": operations,
    }
    return {**payload, "substrate_identity_digest": digest_of(payload)}


def _target_artifact(reference: str) -> dict[str, Any]:
    try:
        resolved = ConfiguredBody(target=str(reference)).resolve()
    except Exception as problem:
        raise MetamorphicCampaignError(
            "form requirement names an executable target that cannot be resolved: %s" % reference
        ) from problem
    return artifact_digest_of(resolved)


def _configured_target_artifact(record: Mapping[str, Any], *, what: str) -> dict[str, Any]:
    if record.get("kind") != "configured_artifact":
        raise MetamorphicCampaignError(f"{what} is not a reconstructible configured executable")
    configured = record.get("configuration")
    if not isinstance(configured, Mapping):
        raise MetamorphicCampaignError(f"{what} carries no configured executable identity")
    target = configured.get("target_artifact")
    if not isinstance(target, Mapping):
        raise MetamorphicCampaignError(f"{what} carries no interpreter artifact identity")
    return dict(target)


def _stage_record(
    genesis, stage: ObjectiveStage | FormMigrationStage | FormRequirementStage
) -> dict[str, Any]:
    if isinstance(stage, ObjectiveStage):
        objective_record = opc.objective_record(genesis, stage.world)
        payload = {
            "schema": STAGE_SCHEMA,
            "type": "objective",
            "name": stage.name,
            "objective": objective_record,
            "probe_registry": str(stage.world.probe_registry),
        }
    elif isinstance(stage, FormMigrationStage):
        substrate = stage.world.substrates.get(stage.substrate)
        if substrate is None:
            raise MetamorphicCampaignError(
                "campaign migration stage names absent substrate %r" % stage.substrate
            )
        payload = {
            "schema": STAGE_SCHEMA,
            "type": "form_migration",
            "name": stage.name,
            "verification_objective": opc.objective_record(genesis, stage.world),
            "probe_registry": str(stage.world.probe_registry),
            "substrate": _substrate_identity(substrate),
            "strategy": FORM_REBIND_STRATEGY,
            "required_operation": program_forms.REBIND_OPERATION,
            "destination_form_artifact": dict(program_forms.PORTABLE_PROGRAM_ARTIFACT),
        }
    elif isinstance(stage, FormRequirementStage):
        allowed = [
            {"target": target, "artifact": _target_artifact(target)}
            for target in stage.allowed_targets
        ]
        allowed.sort(key=lambda item: (item["artifact"]["artifact_digest"], item["target"]))
        substrates = [_substrate_identity(value) for value in stage.world.substrates.values()]
        substrates.sort(key=lambda item: item["substrate_identity_digest"])
        payload = {
            "schema": STAGE_SCHEMA,
            "type": "form_requirement",
            "name": stage.name,
            "verification_objective": opc.objective_record(genesis, stage.world),
            "probe_registry": str(stage.world.probe_registry),
            "allowed_forms": allowed,
            "substrates": substrates,
            "strategy": FORM_REBIND_STRATEGY,
            "required_operation": program_forms.REBIND_OPERATION,
        }
    else:  # pragma: no cover - public typing plus explicit runtime refusal
        raise MetamorphicCampaignError("campaign contains an unrecognised stage")
    return {**payload, "stage_digest": digest_of(payload)}


def campaign_record(
    genesis, stages: Sequence[ObjectiveStage | FormMigrationStage | FormRequirementStage]
) -> dict[str, Any]:
    if not stages:
        raise MetamorphicCampaignError("a metamorphic campaign contains no stages")
    records = [_stage_record(genesis, stage) for stage in stages]
    payload = {
        "schema": CAMPAIGN_SCHEMA,
        "stages": records,
        "stage_digests": [record["stage_digest"] for record in records],
        "evaluation_contract_digest": genesis.evaluation_contract["contract_digest"],
    }
    return {**payload, "campaign_digest": digest_of(payload)}


def _cursor_tool(genesis) -> Mapping[str, Any] | None:
    matches = [
        tool
        for tool in genesis.state.get("tools", [])
        if tool.get("name") == CURSOR_TOOL_NAME and tool.get("role") == CURSOR_ROLE
    ]
    if not matches:
        return None
    if len(matches) != 1:
        raise MetamorphicCampaignError("lineage carries more than one metamorphic campaign cursor")
    return matches[0]


def _validate_migration_record(genesis, record: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if record is None:
        return None
    value = dict(record)
    expected = digest_of({key: item for key, item in value.items() if key != "migration_digest"})
    if value.get("migration_digest") != expected:
        raise MetamorphicCampaignError("persisted campaign migration does not reproduce its digest")
    entry_digest = str(value.get("arrival_journal_entry") or "")
    if not entry_digest or not any(
        entry.get("kind") == "migration" and entry.get("entry_digest") == entry_digest
        for entry in genesis.journal
    ):
        raise MetamorphicCampaignError(
            "persisted campaign migration is not present in the lineage journal"
        )
    return value


def _validate_cursor_progress_journal(
    genesis, campaign: Mapping[str, Any], artifact: Mapping[str, Any], next_stage: int
) -> None:
    """Require the persisted cursor to be backed by every runtime transition that reached it."""
    evidence: list[Mapping[str, Any]] = []
    for entry in genesis.journal.of_kind("observation"):
        payload = entry.get("payload") or {}
        if not isinstance(payload, Mapping):
            continue
        if payload.get("arm") != "metamorphic_campaign_cursor":
            continue
        if str(payload.get("campaign_digest") or "") != str(campaign["campaign_digest"]):
            continue
        evidence.append(payload)

    actual_indices: list[int] = []
    for payload in evidence:
        try:
            actual_indices.append(int(payload.get("next_stage", -1)))
        except (TypeError, ValueError) as problem:
            raise MetamorphicCampaignError(
                "campaign cursor journal carries a malformed stage index"
            ) from problem
    expected_indices = list(range(int(next_stage) + 1))
    if actual_indices != expected_indices:
        raise MetamorphicCampaignError(
            "campaign cursor progression is not backed by an exact journal transition sequence"
        )
    if not evidence or str(evidence[-1].get("cursor_digest") or "") != str(
        artifact.get("cursor_digest") or ""
    ):
        raise MetamorphicCampaignError(
            "campaign cursor head is not backed by its journaled transition"
        )
    stage_digests = list(campaign["stage_digests"])
    for index, payload in enumerate(evidence):
        expected_completed = "" if index == 0 else str(stage_digests[index - 1])
        if str(payload.get("completed_stage_digest") or "") != expected_completed:
            raise MetamorphicCampaignError(
                "campaign cursor journal does not bind the stage it claims to have completed"
            )


def _validate_cursor(genesis, campaign: Mapping[str, Any]) -> dict[str, Any] | None:
    tool = _cursor_tool(genesis)
    if tool is None:
        return None
    artifact = tool.get("artifact")
    if not isinstance(artifact, Mapping) or artifact.get("schema") != CURSOR_SCHEMA:
        raise MetamorphicCampaignError("campaign cursor carries no recognised artifact")
    stage_digests = list(campaign["stage_digests"])
    payload = {
        "schema": CURSOR_SCHEMA,
        "campaign_digest": str(artifact.get("campaign_digest") or ""),
        "stage_digests": list(artifact.get("stage_digests") or []),
        "completed_stage_digests": list(artifact.get("completed_stage_digests") or []),
        "next_stage": int(artifact.get("next_stage", -1)),
        "migration": artifact.get("migration"),
        "acquisition_count_at_migration": artifact.get("acquisition_count_at_migration"),
    }
    if artifact.get("cursor_digest") != digest_of(payload):
        raise MetamorphicCampaignError("campaign cursor does not reproduce its own digest")
    if payload["campaign_digest"] != campaign["campaign_digest"]:
        raise MetamorphicCampaignError(
            "this lineage is already progressing through a different campaign"
        )
    if payload["stage_digests"] != stage_digests:
        raise MetamorphicCampaignError("campaign cursor stage identities changed across restart")
    next_stage = payload["next_stage"]
    if next_stage < 0 or next_stage > len(stage_digests):
        raise MetamorphicCampaignError("campaign cursor next-stage index is outside its campaign")
    if payload["completed_stage_digests"] != stage_digests[:next_stage]:
        raise MetamorphicCampaignError(
            "campaign cursor does not describe an exact completed prefix of its stage sequence"
        )
    _validate_cursor_progress_journal(genesis, campaign, artifact, next_stage)
    payload["migration"] = _validate_migration_record(genesis, payload["migration"])
    count = payload["acquisition_count_at_migration"]
    if count is not None:
        count = int(count)
        if count < 0 or count > len(genesis.state.get("acquisitions", [])):
            raise MetamorphicCampaignError("campaign migration acquisition frontier is impossible")
        payload["acquisition_count_at_migration"] = count
    return {**payload, "cursor_digest": artifact["cursor_digest"]}


def _write_cursor(
    genesis,
    campaign: Mapping[str, Any],
    *,
    next_stage: int,
    migration_record: Mapping[str, Any] | None,
    acquisition_count_at_migration: int | None,
    initial: bool = False,
) -> dict[str, Any]:
    stage_digests = list(campaign["stage_digests"])
    payload = {
        "schema": CURSOR_SCHEMA,
        "campaign_digest": campaign["campaign_digest"],
        "stage_digests": stage_digests,
        "completed_stage_digests": stage_digests[: int(next_stage)],
        "next_stage": int(next_stage),
        "migration": dict(migration_record) if migration_record is not None else None,
        "acquisition_count_at_migration": acquisition_count_at_migration,
    }
    cursor = {**payload, "cursor_digest": digest_of(payload)}
    tools = []
    replaced = False
    for tool in genesis.state.get("tools", []):
        if tool.get("name") == CURSOR_TOOL_NAME and tool.get("role") == CURSOR_ROLE:
            if replaced:
                raise MetamorphicCampaignError("lineage carries duplicate campaign cursors")
            tools.append(
                {
                    "name": CURSOR_TOOL_NAME,
                    "role": CURSOR_ROLE,
                    "artifact": cursor,
                    "provenance": provenance(
                        "host_written" if initial else "lineage_owned",
                        produced_by=(
                            "metamorphic campaign admission"
                            if initial
                            else "persistent metamorphic campaign runtime"
                        ),
                        detail=campaign["campaign_digest"],
                    ),
                }
            )
            replaced = True
        else:
            tools.append(tool)
    if not replaced:
        tools.append(
            {
                "name": CURSOR_TOOL_NAME,
                "role": CURSOR_ROLE,
                "artifact": cursor,
                "provenance": provenance(
                    "host_written" if initial else "lineage_owned",
                    produced_by=(
                        "metamorphic campaign admission"
                        if initial
                        else "persistent metamorphic campaign runtime"
                    ),
                    detail=campaign["campaign_digest"],
                ),
            }
        )
    genesis.state = lineage_state.create_state(
        body_digest=genesis.state["body_digest"],
        components=genesis.state["components"],
        vocabulary=genesis.state["vocabulary"],
        tools=tools,
        acquisitions=genesis.state["acquisitions"],
        observations=genesis.state["observations"],
        generation=genesis.state["generation"],
    )
    genesis.journal.append(
        "observation",
        genesis.state["generation"],
        {
            "arm": "metamorphic_campaign_cursor",
            "campaign_digest": campaign["campaign_digest"],
            "next_stage": int(next_stage),
            "completed_stage_digest": ""
            if int(next_stage) == 0
            else str(stage_digests[int(next_stage) - 1]),
            "cursor_digest": cursor["cursor_digest"],
            "new_state_digest": genesis.state["state_digest"],
        },
    )
    return cursor


def _post_migration_cycles(genesis, cursor: Mapping[str, Any]) -> list[dict[str, Any]]:
    count = cursor.get("acquisition_count_at_migration")
    if count is None:
        return []
    acquisitions = list(genesis.state.get("acquisitions", []))[int(count) :]
    return [
        {
            "accepted": True,
            "name": str(item.get("name") or ""),
            "generation": int(item.get("generation", -1)),
            "verdict_digest": str(item.get("verdict_digest") or ""),
            "causal_dependency": dict(item.get("causal_dependency") or {}),
        }
        for item in acquisitions
    ]


def _replace_observations(genesis, observations) -> None:
    genesis.state = lineage_state.create_state(
        body_digest=genesis.state["body_digest"],
        components=genesis.state["components"],
        vocabulary=genesis.state["vocabulary"],
        tools=genesis.state["tools"],
        acquisitions=genesis.state["acquisitions"],
        observations=observations,
        generation=genesis.state["generation"],
    )


def _transition_probe_round_payload(
    genesis,
    *,
    identity: Mapping[str, Any],
    current: Mapping[str, Any],
    destination: Mapping[str, Any],
    substrate_records: Sequence[Mapping[str, Any]],
    probe_cost_required: int,
) -> dict[str, Any]:
    return {
        "schema": TRANSITION_PROBE_ROUND_SCHEMA,
        "stage_digest": str(identity["stage_digest"]),
        "body_artifact_digest": artifact_digest_of(genesis.body_factory)["artifact_digest"],
        "current_target_artifact_digest": str(current["artifact_digest"]),
        "destination_target_artifact_digest": str(destination["artifact_digest"]),
        "substrate_identity_digests": [
            str(item["substrate_identity_digest"]) for item in substrate_records
        ],
        "required_operation": program_forms.REBIND_OPERATION,
        "probe_cost_required": int(probe_cost_required),
    }


def _transition_probe_round_digest(payload: Mapping[str, Any]) -> str:
    return digest_of(dict(payload))


def _transition_probe_round_records(genesis, round_digest: str) -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in genesis.state.get("observations", [])
        if isinstance(item, Mapping)
        and item.get("kind") == TRANSITION_PROBE_ROUND_KIND
        and item.get("round_digest") == round_digest
    ]


def _transition_probe_round_record(
    payload: Mapping[str, Any],
    *,
    status: str,
    budget_before: int,
    budget_after: int | None = None,
    selection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    record = {
        "kind": TRANSITION_PROBE_ROUND_KIND,
        **dict(payload),
        "round_digest": _transition_probe_round_digest(payload),
        "status": status,
        "budget_before": int(budget_before),
        "budget_after": None if budget_after is None else int(budget_after),
        "selection": dict(selection) if selection is not None else None,
    }
    record["record_digest"] = digest_of(record)
    return record


def _validate_transition_probe_round_record(
    item: Mapping[str, Any], expected_payload: Mapping[str, Any]
) -> dict[str, Any]:
    record = dict(item)
    recorded_digest = record.pop("record_digest", "")
    if recorded_digest != digest_of(record):
        raise MetamorphicCampaignError(
            "architectural transition probe round does not reproduce its record digest"
        )
    if record.get("kind") != TRANSITION_PROBE_ROUND_KIND:
        raise MetamorphicCampaignError("architectural transition probe round has wrong kind")
    for key, value in expected_payload.items():
        if record.get(key) != value:
            raise MetamorphicCampaignError(
                "architectural transition probe round does not reproduce current %s" % key
            )
    if record.get("round_digest") != _transition_probe_round_digest(expected_payload):
        raise MetamorphicCampaignError("architectural transition probe round identity changed")
    if record.get("status") not in {
        _TRANSITION_RESERVED,
        _TRANSITION_CHARGED,
        _TRANSITION_COMPLETED,
        _TRANSITION_CRASH_INCOMPLETE,
    }:
        raise MetamorphicCampaignError("architectural transition probe round has unknown status")
    if record.get("status") == _TRANSITION_COMPLETED:
        selection = record.get("selection")
        if not isinstance(selection, Mapping):
            raise MetamorphicCampaignError(
                "completed architectural transition probe round carries no selection"
            )
        selection_copy = dict(selection)
        selection_digest = selection_copy.pop("selection_digest", "")
        if selection_digest != digest_of(selection_copy):
            raise MetamorphicCampaignError(
                "persisted architectural transition selection does not reproduce its digest"
            )
        if selection.get("stage_digest") != expected_payload["stage_digest"]:
            raise MetamorphicCampaignError(
                "persisted architectural transition selection names another stage"
            )
        if selection.get("durable_probe_round_digest") != record.get("round_digest"):
            raise MetamorphicCampaignError(
                "persisted architectural transition selection names another probe round"
            )
    return dict(item)


def _install_transition_probe_round(genesis, record: Mapping[str, Any]) -> None:
    target = str(record["round_digest"])
    observations = []
    replaced = False
    for item in genesis.state.get("observations", []):
        if (
            isinstance(item, Mapping)
            and item.get("kind") == TRANSITION_PROBE_ROUND_KIND
            and item.get("round_digest") == target
        ):
            if replaced:
                raise MetamorphicCampaignError(
                    "lineage carries duplicate architectural transition probe rounds"
                )
            observations.append(dict(record))
            replaced = True
        else:
            observations.append(item)
    if not replaced:
        observations.append(dict(record))
    _replace_observations(genesis, observations)


def _prepare_transition_probe_round(
    genesis,
    *,
    identity: Mapping[str, Any],
    current: Mapping[str, Any],
    destination: Mapping[str, Any],
    substrate_records: Sequence[Mapping[str, Any]],
    probe_cost_required: int,
    checkpoint_directory: Path | None,
) -> dict[str, Any]:
    if checkpoint_directory is None or probe_cost_required <= 0:
        if probe_cost_required > genesis.budget.remaining("probes"):
            raise MetamorphicCampaignError(
                "complete architectural transition comparison requires %d probe units but only %d remain"
                % (probe_cost_required, genesis.budget.remaining("probes"))
            )
        return {
            "budget": genesis.budget,
            "round_digest": "",
            "replay_selection": None,
            "durable": False,
        }

    payload = _transition_probe_round_payload(
        genesis,
        identity=identity,
        current=current,
        destination=destination,
        substrate_records=substrate_records,
        probe_cost_required=probe_cost_required,
    )
    round_digest = _transition_probe_round_digest(payload)
    existing = _transition_probe_round_records(genesis, round_digest)
    if len(existing) > 1:
        raise MetamorphicCampaignError(
            "lineage carries duplicate architectural transition probe rounds"
        )

    if not existing:
        remaining = genesis.budget.remaining("probes")
        if remaining < probe_cost_required:
            raise MetamorphicCampaignError(
                "complete architectural transition comparison requires %d probe units but only %d remain"
                % (probe_cost_required, remaining)
            )
        before = int(genesis.budget.spent.get("probes", 0))
        reserved = _transition_probe_round_record(
            payload,
            status=_TRANSITION_RESERVED,
            budget_before=before,
        )
        _install_transition_probe_round(genesis, reserved)
        genesis.persist(Path(checkpoint_directory))
        record = reserved
    else:
        record = _validate_transition_probe_round_record(existing[0], payload)

    status = record["status"]
    if status == _TRANSITION_COMPLETED:
        return {
            "budget": genesis.budget,
            "round_digest": round_digest,
            "replay_selection": dict(record["selection"]),
            "durable": True,
        }
    if status == _TRANSITION_CRASH_INCOMPLETE:
        raise MetamorphicCampaignError(
            "prior architectural transition crashed after its probe budget was charged; redraw is refused"
        )
    if status == _TRANSITION_CHARGED:
        crashed = dict(record)
        crashed.pop("record_digest", None)
        crashed["status"] = _TRANSITION_CRASH_INCOMPLETE
        crashed["record_digest"] = digest_of(crashed)
        _install_transition_probe_round(genesis, crashed)
        genesis.persist(Path(checkpoint_directory))
        raise MetamorphicCampaignError(
            "prior architectural transition crashed after its probe budget was charged; redraw is refused"
        )
    if status != _TRANSITION_RESERVED:
        raise MetamorphicCampaignError("architectural transition probe round cannot be charged")

    genesis.budget.spend("probes", probe_cost_required)
    after = int(genesis.budget.spent.get("probes", 0))
    charged = _transition_probe_round_record(
        payload,
        status=_TRANSITION_CHARGED,
        budget_before=int(record["budget_before"]),
        budget_after=after,
    )
    _install_transition_probe_round(genesis, charged)
    genesis.persist(Path(checkpoint_directory))
    return {
        "budget": _PrepaidProbeBudget(genesis.budget, probe_cost_required),
        "round_digest": round_digest,
        "replay_selection": None,
        "durable": True,
    }


def _complete_transition_probe_round(
    genesis, round_digest: str, selection: Mapping[str, Any]
) -> None:
    if not round_digest:
        return
    records = _transition_probe_round_records(genesis, round_digest)
    if len(records) != 1:
        raise MetamorphicCampaignError(
            "architectural transition completion has no unique durable probe round"
        )
    record = dict(records[0])
    recorded_digest = record.pop("record_digest", "")
    if recorded_digest != digest_of(record):
        raise MetamorphicCampaignError(
            "architectural transition completion found a corrupt probe round"
        )
    selection_copy = dict(selection)
    selection_digest = selection_copy.pop("selection_digest", "")
    if selection_digest != digest_of(selection_copy):
        raise MetamorphicCampaignError(
            "architectural transition completion received a selection whose digest does not reproduce"
        )
    if selection.get("durable_probe_round_digest") != round_digest:
        raise MetamorphicCampaignError(
            "architectural transition selection does not belong to its durable probe round"
        )
    if record.get("status") == _TRANSITION_COMPLETED:
        stored = record.get("selection")
        if not isinstance(stored, Mapping) or stored.get("selection_digest") != selection.get(
            "selection_digest"
        ):
            raise MetamorphicCampaignError(
                "completed architectural transition probe round names another selection"
            )
        return
    if record.get("status") != _TRANSITION_CHARGED:
        raise MetamorphicCampaignError(
            "architectural transition probe round completed from a non-charged state"
        )
    record["status"] = _TRANSITION_COMPLETED
    record["selection"] = dict(selection)
    record["record_digest"] = digest_of(record)
    _install_transition_probe_round(genesis, record)


def _select_form_transition(
    genesis,
    stage: FormRequirementStage,
    identity: Mapping[str, Any],
    *,
    checkpoint_directory: Path | None = None,
) -> dict[str, Any]:
    """Select stay vs admitted substrate migration by complete capability-aware comparison.

    Target compatibility alone is not migration viability.  Every migration whose target would
    otherwise score positively must first establish the fixed ``rebind_program`` capability through
    the ordinary probe mechanism.  The complete relevant probe cost is checked before the first
    probe so host/container ordering cannot decide which candidate gets measured when budget is
    tight.  Candidates whose target is already incompatible need no probe because the missing
    capability cannot change their zero score.
    """
    current = _configured_target_artifact(
        artifact_digest_of(genesis.body_factory), what="architectural transition current body"
    )
    allowed = [dict(item["artifact"]) for item in identity.get("allowed_forms", [])]
    candidates: list[dict[str, Any]] = []

    stay_payload = {
        "kind": "stay",
        "target_artifact": current,
        "substrate": "",
        "stage_digest": identity["stage_digest"],
    }
    candidates.append(
        {
            **stay_payload,
            "candidate_digest": digest_of(stay_payload),
            "capability_probe": None,
            "required_capability_available": None,
            "compatibility_score": 1 if current in allowed else 0,
        }
    )

    destination = dict(program_forms.PORTABLE_PROGRAM_ARTIFACT)
    migration_target_relevant = destination in allowed and destination != current
    substrate_records = [dict(item) for item in identity.get("substrates", [])]
    probe_cost_required = (
        sum(int(item.get("probe_cost", 0)) for item in substrate_records)
        if migration_target_relevant
        else 0
    )
    durable_round = {
        "budget": genesis.budget,
        "round_digest": "",
        "replay_selection": None,
        "durable": False,
    }
    if migration_target_relevant and probe_cost_required:
        durable_round = _prepare_transition_probe_round(
            genesis,
            identity=identity,
            current=current,
            destination=destination,
            substrate_records=substrate_records,
            probe_cost_required=probe_cost_required,
            checkpoint_directory=checkpoint_directory,
        )
        if durable_round["replay_selection"] is not None:
            return dict(durable_round["replay_selection"])
    elif probe_cost_required:
        remaining = genesis.budget.remaining("probes")
        if remaining < probe_cost_required:
            raise MetamorphicCampaignError(
                "complete architectural transition comparison requires %d probe units but only %d remain"
                % (probe_cost_required, remaining)
            )

    probe_budget = durable_round["budget"]
    probe_results: dict[str, dict[str, Any]] = {}
    if migration_target_relevant:
        # ``identity['substrates']`` is already canonicalised by substrate identity digest.  Verify
        # that the executable World still reproduces those identities before spending anything on
        # each candidate, then probe every relevant candidate exactly once.
        for substrate_record in substrate_records:
            name = str(substrate_record.get("name") or "")
            substrate = stage.world.substrates.get(name)
            if substrate is None:
                raise MetamorphicCampaignError(
                    "architectural transition candidate substrate %r disappeared before scoring" % name
                )
            if _substrate_identity(substrate) != substrate_record:
                raise MetamorphicCampaignError(
                    "architectural transition candidate substrate %r no longer matches campaign identity"
                    % name
                )
            probe_results[name] = migration.discover(
                substrate,
                [program_forms.REBIND_OPERATION],
                probe_budget,
            )

    if isinstance(probe_budget, _PrepaidProbeBudget) and probe_budget.unused() != 0:
        raise MetamorphicCampaignError(
            "architectural transition did not consume its complete durably prepaid probe round"
        )

    for substrate_record in substrate_records:
        name = str(substrate_record["name"])
        payload = {
            "kind": "migrate",
            "target_artifact": destination,
            "substrate": name,
            "substrate_identity_digest": str(substrate_record["substrate_identity_digest"]),
            "strategy": FORM_REBIND_STRATEGY,
            "stage_digest": identity["stage_digest"],
        }
        probing = probe_results.get(name)
        capability_available = (
            probing is not None
            and probing.get("probed") == [program_forms.REBIND_OPERATION]
            and probing.get("found") == [program_forms.REBIND_OPERATION]
        )
        candidates.append(
            {
                **payload,
                "candidate_digest": digest_of(payload),
                "capability_probe": probing,
                "required_capability_available": capability_available
                if migration_target_relevant
                else None,
                "compatibility_score": 1
                if migration_target_relevant and capability_available
                else 0,
            }
        )

    candidates.sort(key=lambda item: item["candidate_digest"])
    best = max(int(item["compatibility_score"]) for item in candidates)
    winners = [item for item in candidates if int(item["compatibility_score"]) == best]
    if best <= 0:
        selected = None
        reason = "no_viable_architectural_transition"
    elif len(winners) != 1:
        selected = None
        reason = "ambiguous_no_strict_maximum"
    else:
        selected = winners[0]
        reason = "unique_strict_maximum"

    record = {
        "schema": "genesis-architectural-transition-selection-v2",
        "stage_digest": identity["stage_digest"],
        "selection_rule": "unique_strict_maximum_form_compatibility_with_capability_probe_v1",
        "candidates": candidates,
        "complete_relevant_candidate_set_probed": True,
        "probe_cost_required": probe_cost_required,
        "durable_probe_round_digest": str(durable_round["round_digest"]),
        "probe_budget_precommitted": bool(durable_round["round_digest"]),
        "selection_reason": reason,
        "accepted": selected is not None,
        "selected_candidate_digest": "" if selected is None else selected["candidate_digest"],
        "selected_kind": "" if selected is None else selected["kind"],
        "selected_substrate": "" if selected is None else selected.get("substrate", ""),
    }
    record["selection_digest"] = digest_of(record)
    genesis.journal.append(
        "observation",
        genesis.state["generation"],
        {
            "arm": "architectural_transition_selection",
            "stage_digest": identity["stage_digest"],
            "selection_digest": record["selection_digest"],
            "selection_rule": record["selection_rule"],
            "selection_reason": reason,
            "selected_candidate_digest": record["selected_candidate_digest"],
            "candidate_digests": [item["candidate_digest"] for item in candidates],
            "probe_cost_required": probe_cost_required,
            "durable_probe_round_digest": record["durable_probe_round_digest"],
        },
    )
    return record

def _run_form_migration(
    genesis,
    stage: FormMigrationStage,
    *,
    preflight_probe: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not programs.program_operations_of(genesis.body_factory):
        raise MetamorphicCampaignError(
            "fixed form-rebind strategy requires a reconstructible generated-program current body"
        )
    departure_artifact = artifact_digest_of(genesis.body_factory)
    departure_target = _configured_target_artifact(
        departure_artifact, what="campaign migration departure body"
    )
    destination_target = dict(program_forms.PORTABLE_PROGRAM_ARTIFACT)
    if departure_target == destination_target:
        raise MetamorphicCampaignError(
            "fixed form-rebind strategy would not change the executable interpreter artifact"
        )
    substrate = stage.world.substrates.get(stage.substrate)
    if substrate is None:
        raise MetamorphicCampaignError("migration substrate disappeared before execution")
    if preflight_probe is None:
        probing = migration.discover(
            substrate,
            [program_forms.REBIND_OPERATION],
            genesis.budget,
        )
    else:
        probing = dict(preflight_probe)
        if (
            probing.get("substrate") != substrate.name
            or probing.get("probed") != [program_forms.REBIND_OPERATION]
            or probing.get("found") != [program_forms.REBIND_OPERATION]
            or program_forms.REBIND_OPERATION not in substrate.discovered
        ):
            raise MetamorphicCampaignError(
                "selected migration has no matching capability probe from architectural scoring"
            )
    if probing["found"] != [program_forms.REBIND_OPERATION]:
        raise MetamorphicCampaignError(
            "target substrate does not expose the fixed generated-program rebind capability"
        )
    record = migration.migrate(
        genesis,
        substrate,
        program_forms.translate_current_program,
        used_operations=[program_forms.REBIND_OPERATION],
        tasks=stage.world.tasks,
        translation_provenance=provenance(
            "host_written",
            produced_by="fixed metamorphic campaign form-rebind adapter",
            detail=FORM_REBIND_STRATEGY,
        ),
    )
    arrival_artifact = artifact_digest_of(genesis.body_factory)
    arrival_target = _configured_target_artifact(
        arrival_artifact, what="campaign migration arrival body"
    )
    if arrival_target != destination_target:
        raise MetamorphicCampaignError(
            "campaign migration arrived under an executable interpreter other than the admitted form"
        )
    if arrival_target == departure_target:
        raise MetamorphicCampaignError(
            "campaign migration changed a label but not the executable interpreter artifact"
        )
    return {
        "type": "form_migration",
        "strategy": FORM_REBIND_STRATEGY,
        "probing": probing,
        "migration": record,
        "form_transition": {
            "departure_target_artifact": departure_target,
            "arrival_target_artifact": arrival_target,
            "destination_form_artifact": destination_target,
            "executable_target_changed": True,
            "destination_matches_admitted_artifact": True,
        },
    }

def run(
    genesis,
    stages: Sequence[ObjectiveStage | FormMigrationStage | FormRequirementStage],
    *,
    seed_policy: Mapping[str, Any] | None = None,
    seed_meta_policy: Mapping[str, Any] | None = None,
    max_rounds_per_objective: int = 64,
    checkpoint_directory: Path | None = None,
    max_stages: int | None = None,
) -> dict[str, Any]:
    """Run or resume one content-addressed environmental campaign.

    ``max_stages`` is an execution bound, not a stage selector. It exists so a test or supervisor may
    kill the process after a committed prefix and verify that the next process resumes from the
    persisted cursor. The cursor, not the caller, decides which stage comes next.
    """
    campaign = campaign_record(genesis, stages)
    cursor = _validate_cursor(genesis, campaign)
    checkpoint_path = Path(checkpoint_directory) if checkpoint_directory is not None else None
    if cursor is None:
        cursor = _write_cursor(
            genesis,
            campaign,
            next_stage=0,
            migration_record=None,
            acquisition_count_at_migration=None,
            initial=True,
        )
        if checkpoint_path is not None:
            genesis.persist(checkpoint_path)

    start = int(cursor["next_stage"])
    limit = len(stages) - start if max_stages is None else max(0, int(max_stages))
    executed: list[dict[str, Any]] = []
    migration_record = cursor.get("migration")
    acquisition_frontier = cursor.get("acquisition_count_at_migration")

    for index in range(start, min(len(stages), start + limit)):
        stage = stages[index]
        identity = campaign["stages"][index]
        if isinstance(stage, ObjectiveStage):
            _assert_world_registry_matches_policy(genesis, stage.world, seed_policy=seed_policy)
            held_policy = policy_controller.bound_policy(genesis)
            held_meta = meta.bound_meta_policy(genesis)
            run_record = form_runtime.run_objective(
                genesis,
                stage.world,
                seed_policy=seed_policy if held_policy is None else None,
                seed_meta_policy=seed_meta_policy if held_meta is None else None,
                max_rounds=max_rounds_per_objective,
                checkpoint_directory=checkpoint_path,
            )
            executed.append(
                {
                    "index": index,
                    "stage_digest": identity["stage_digest"],
                    "type": "objective",
                    "body_adopted": bool(run_record.get("body_adopted")),
                    "run": run_record,
                }
            )
        elif isinstance(stage, FormMigrationStage):
            if migration_record is not None:
                raise MetamorphicCampaignError(
                    "v1 persistent metamorphic campaign admits one form transition only"
                )
            _assert_world_registry_matches_policy(genesis, stage.world, seed_policy=seed_policy)
            migration_result = _run_form_migration(genesis, stage)
            migration_record = migration_result["migration"]
            acquisition_frontier = len(genesis.state.get("acquisitions", []))
            executed.append(
                {
                    "index": index,
                    "stage_digest": identity["stage_digest"],
                    **migration_result,
                }
            )
        elif isinstance(stage, FormRequirementStage):
            _assert_world_registry_matches_policy(genesis, stage.world, seed_policy=seed_policy)
            selection = _select_form_transition(
                genesis, stage, identity, checkpoint_directory=checkpoint_path
            )
            entry: dict[str, Any] = {
                "index": index,
                "stage_digest": identity["stage_digest"],
                "type": "form_requirement",
                "transition_selection": selection,
            }
            executed.append(entry)
            if not selection["accepted"]:
                entry["stopped"] = True
                entry["reason"] = selection["selection_reason"]
                _complete_transition_probe_round(
                    genesis,
                    str(selection.get("durable_probe_round_digest") or ""),
                    selection,
                )
                if checkpoint_path is not None:
                    entry["campaign_checkpoint_digest"] = genesis.persist(checkpoint_path)["checkpoint"]
                    entry["durable_before_next_stage"] = True
                else:
                    entry["campaign_checkpoint_digest"] = ""
                    entry["durable_before_next_stage"] = False
                break
            if selection["selected_kind"] == "migrate":
                if migration_record is not None:
                    raise MetamorphicCampaignError(
                        "v1 persistent metamorphic campaign admits one form transition only"
                    )
                selected_substrate = str(selection["selected_substrate"])
                migration_stage = FormMigrationStage(
                    world=stage.world, substrate=selected_substrate, name=stage.name
                )
                selected_candidates = [
                    item
                    for item in selection["candidates"]
                    if item["candidate_digest"] == selection["selected_candidate_digest"]
                ]
                if len(selected_candidates) != 1:
                    raise MetamorphicCampaignError(
                        "architectural selection does not identify exactly one measured candidate"
                    )
                migration_result = _run_form_migration(
                    genesis,
                    migration_stage,
                    preflight_probe=selected_candidates[0].get("capability_probe"),
                )
                migration_record = migration_result["migration"]
                acquisition_frontier = len(genesis.state.get("acquisitions", []))
                entry["migration_result"] = migration_result
                entry["selected_action"] = "migrate:%s" % selected_substrate
            elif selection["selected_kind"] == "stay":
                entry["selected_action"] = "stay"
            else:  # pragma: no cover - selected kinds are constructed above
                raise MetamorphicCampaignError("transition selector returned an unknown action")
        else:  # pragma: no cover
            raise MetamorphicCampaignError("campaign contains an unrecognised stage")

        if isinstance(stage, FormRequirementStage):
            _complete_transition_probe_round(
                genesis,
                str(selection.get("durable_probe_round_digest") or ""),
                selection,
            )

        cursor = _write_cursor(
            genesis,
            campaign,
            next_stage=index + 1,
            migration_record=migration_record,
            acquisition_count_at_migration=acquisition_frontier,
        )
        if checkpoint_path is not None:
            checkpoint = genesis.persist(checkpoint_path)["checkpoint"]
            executed[-1]["campaign_checkpoint_digest"] = checkpoint
            executed[-1]["durable_before_next_stage"] = True
        else:
            executed[-1]["campaign_checkpoint_digest"] = ""
            executed[-1]["durable_before_next_stage"] = False

    cursor = _validate_cursor(genesis, campaign)
    if cursor is None:  # pragma: no cover
        raise MetamorphicCampaignError("campaign cursor vanished after execution")
    post_cycles = _post_migration_cycles(genesis, cursor)
    metamorphosis = None
    if cursor.get("migration") is not None:
        metamorphosis = migration.metamorphosis_succeeded(cursor["migration"], post_cycles)

    record = {
        "schema": CAMPAIGN_SCHEMA,
        "campaign_digest": campaign["campaign_digest"],
        "stage_digests": list(campaign["stage_digests"]),
        "executed": executed,
        "next_stage": cursor["next_stage"],
        "completed": int(cursor["next_stage"]) == len(stages),
        "cursor_digest": cursor["cursor_digest"],
        "migration": cursor.get("migration"),
        "post_migration_cycles": post_cycles,
        "metamorphosis": metamorphosis,
        "final_generation": genesis.state["generation"],
        "final_state_digest": genesis.state["state_digest"],
        "current_body_artifact": artifact_digest_of(genesis.body_factory),
        "current_policy": policy_controller.bound_policy(genesis),
        "current_meta_policy": meta.bound_meta_policy(genesis),
    }
    record["run_digest"] = digest_of(record)
    return record
