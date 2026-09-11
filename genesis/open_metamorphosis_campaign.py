"""Persistent runtime-owned campaign for Genesis v2 Open Metamorphosis.

The environment supplies an ordered sequence of distinct objectives.  Once admitted, a content-
addressed cursor decides which objective is next across process death.  Within each objective,
``open_metamorphosis_runtime`` decides whether current body machinery suffices, whether the first
transformation-language extension is required, or whether later recursive language machinery must be
used.  The launcher therefore does not choose the language generation or the winning operator.

``max_stages`` is only a kill/execution bound used to demonstrate recovery from a committed prefix;
it cannot select a stage.  A completed campaign replay executes zero objective stages and spends no
new search/evaluation budget.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from genesis import controller
from genesis import objective_policy_controller as opc
from genesis import open_metamorphosis_runtime as runtime
from genesis import policies, policy_controller
from genesis import state as lineage_state
from genesis import transformation_language as language
from genesis import transformation_language_controller as language_controller
from genesis.trust_root import digest_of, provenance

CAMPAIGN_SCHEMA = "genesis-open-metamorphosis-campaign-v1"
STAGE_SCHEMA = "genesis-open-metamorphosis-stage-v1"
CURSOR_SCHEMA = "genesis-open-metamorphosis-cursor-v1"
CURSOR_TOOL_NAME = "open_metamorphosis_campaign_cursor"
CURSOR_ROLE = "persistent_open_metamorphosis_progress"


class OpenMetamorphosisCampaignError(RuntimeError):
    """Raised when a v2 campaign cannot resume as the same admitted program."""


@dataclass(frozen=True)
class ObjectiveStage:
    world: controller.World
    name: str = ""


def objective(world: controller.World, *, name: str = "") -> ObjectiveStage:
    return ObjectiveStage(world=world, name=str(name))


def _stage_record(genesis, stage: ObjectiveStage) -> dict[str, Any]:
    goal = opc.objective_record(genesis, stage.world)
    payload = {
        "schema": STAGE_SCHEMA,
        "type": "objective",
        "name": stage.name,
        "objective": goal,
        "probe_registry": str(stage.world.probe_registry),
    }
    return {**payload, "stage_digest": digest_of(payload)}


def campaign_record(genesis, stages: Sequence[ObjectiveStage]) -> dict[str, Any]:
    if not stages:
        raise OpenMetamorphosisCampaignError("open-metamorphosis campaign contains no objectives")
    records = [_stage_record(genesis, stage) for stage in stages]
    objective_digests = [item["objective"]["objective_digest"] for item in records]
    if len(set(objective_digests)) != len(objective_digests):
        raise OpenMetamorphosisCampaignError(
            "open-metamorphosis campaign requires distinct objective identities"
        )
    payload = {
        "schema": CAMPAIGN_SCHEMA,
        "stages": records,
        "stage_digests": [item["stage_digest"] for item in records],
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
        raise OpenMetamorphosisCampaignError("lineage carries duplicate open-metamorphosis cursors")
    return matches[0]


def _cursor_journal_indices(genesis, campaign_digest: str) -> list[int]:
    indices = []
    for entry in genesis.journal.of_kind("observation"):
        payload = entry.get("payload") or {}
        if (
            isinstance(payload, Mapping)
            and payload.get("arm") == "open_metamorphosis_campaign_cursor"
            and payload.get("campaign_digest") == campaign_digest
        ):
            indices.append(int(payload.get("next_stage", -1)))
    return indices


def _validate_cursor(genesis, campaign) -> dict[str, Any] | None:
    tool = _cursor_tool(genesis)
    if tool is None:
        return None
    artifact = tool.get("artifact")
    if not isinstance(artifact, Mapping) or artifact.get("schema") != CURSOR_SCHEMA:
        raise OpenMetamorphosisCampaignError("open-metamorphosis cursor carries no recognised artifact")
    payload = {
        "schema": CURSOR_SCHEMA,
        "campaign_digest": str(artifact.get("campaign_digest") or ""),
        "stage_digests": list(artifact.get("stage_digests") or []),
        "completed_stage_digests": list(artifact.get("completed_stage_digests") or []),
        "next_stage": int(artifact.get("next_stage", -1)),
    }
    if artifact.get("cursor_digest") != digest_of(payload):
        raise OpenMetamorphosisCampaignError("open-metamorphosis cursor does not reproduce")
    if payload["campaign_digest"] != campaign["campaign_digest"]:
        raise OpenMetamorphosisCampaignError("lineage is already bound to another v2 campaign")
    if payload["stage_digests"] != list(campaign["stage_digests"]):
        raise OpenMetamorphosisCampaignError("v2 campaign stage identities changed across restart")
    next_stage = payload["next_stage"]
    if next_stage < 0 or next_stage > len(campaign["stages"]):
        raise OpenMetamorphosisCampaignError("v2 campaign cursor is outside the admitted stage range")
    if payload["completed_stage_digests"] != list(campaign["stage_digests"][:next_stage]):
        raise OpenMetamorphosisCampaignError("v2 cursor is not an exact completed campaign prefix")
    expected_indices = list(range(next_stage + 1))
    if _cursor_journal_indices(genesis, campaign["campaign_digest"]) != expected_indices:
        raise OpenMetamorphosisCampaignError(
            "v2 cursor progression is not backed by an exact append-only journal sequence"
        )
    return {**payload, "cursor_digest": artifact["cursor_digest"]}


def _write_cursor(genesis, campaign, *, next_stage: int, initial: bool = False) -> dict[str, Any]:
    stage_digests = list(campaign["stage_digests"])
    payload = {
        "schema": CURSOR_SCHEMA,
        "campaign_digest": campaign["campaign_digest"],
        "stage_digests": stage_digests,
        "completed_stage_digests": stage_digests[: int(next_stage)],
        "next_stage": int(next_stage),
    }
    cursor = {**payload, "cursor_digest": digest_of(payload)}
    tools = []
    replaced = False
    for tool in genesis.state.get("tools", []):
        if tool.get("name") == CURSOR_TOOL_NAME and tool.get("role") == CURSOR_ROLE:
            if replaced:
                raise OpenMetamorphosisCampaignError("lineage carries duplicate v2 campaign cursors")
            tools.append(
                {
                    "name": CURSOR_TOOL_NAME,
                    "role": CURSOR_ROLE,
                    "artifact": cursor,
                    "provenance": provenance(
                        "host_written" if initial else "lineage_owned",
                        produced_by=(
                            "open-metamorphosis campaign admission"
                            if initial
                            else "open-metamorphosis persistent runtime"
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
                        "open-metamorphosis campaign admission"
                        if initial
                        else "open-metamorphosis persistent runtime"
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
            "arm": "open_metamorphosis_campaign_cursor",
            "campaign_digest": campaign["campaign_digest"],
            "next_stage": int(next_stage),
            "completed_stage_digest": (
                "" if int(next_stage) == 0 else stage_digests[int(next_stage) - 1]
            ),
            "cursor_digest": cursor["cursor_digest"],
            "new_state_digest": genesis.state["state_digest"],
        },
    )
    return cursor


def _assert_registry(genesis, stage, seed_policy=None) -> None:
    held = policy_controller.bound_policy(genesis)
    candidate = held
    if candidate is None and seed_policy is not None:
        candidate = policies.validate(seed_policy)
    if candidate is not None and str(candidate["registry_reference"]) != str(stage.world.probe_registry):
        raise OpenMetamorphosisCampaignError(
            "objective registry differs from the lineage's held body-search registry"
        )


def run(
    genesis,
    stages: Sequence[ObjectiveStage],
    *,
    seed_policy: Mapping[str, Any] | None = None,
    seed_language: Mapping[str, Any] | None = None,
    max_policy_steps: int = 64,
    checkpoint_directory: Path | None = None,
    max_stages: int | None = None,
) -> dict[str, Any]:
    """Run/resume the persistent campaign; the cursor and runtime own all architectural hand-offs."""
    campaign = campaign_record(genesis, stages)
    cursor = _validate_cursor(genesis, campaign)
    checkpoint = Path(checkpoint_directory) if checkpoint_directory is not None else None
    if cursor is None:
        cursor = _write_cursor(genesis, campaign, next_stage=0, initial=True)
        if checkpoint is not None:
            genesis.persist(checkpoint)

    start = int(cursor["next_stage"])
    limit = len(stages) - start if max_stages is None else max(0, int(max_stages))
    executed: list[dict[str, Any]] = []

    for index in range(start, min(len(stages), start + limit)):
        stage = stages[index]
        identity = campaign["stages"][index]
        _assert_registry(genesis, stage, seed_policy=seed_policy)
        run_record = runtime.run_objective(
            genesis,
            stage.world,
            seed_policy=seed_policy if policy_controller.bound_policy(genesis) is None else None,
            seed_language=(
                seed_language if language_controller.bound_language(genesis) is None else None
            ),
            max_policy_steps=max_policy_steps,
            checkpoint_directory=checkpoint,
        )
        entry = {
            "index": index,
            "stage_digest": identity["stage_digest"],
            "type": "objective",
            "body_adopted": bool(run_record.get("body_adopted")),
            "machinery_generation_selected_by_runtime": run_record.get(
                "machinery_generation_selected_by_runtime"
            ),
            "machinery_mode": run_record.get("machinery_mode"),
            "run": run_record,
        }
        executed.append(entry)
        if not run_record.get("body_adopted"):
            entry["stopped"] = True
            entry["reason"] = "objective exhausted admitted v2 machinery without an accepted body"
            if checkpoint is not None:
                entry["campaign_checkpoint_digest"] = genesis.persist(checkpoint)["checkpoint"]
            break

        cursor = _write_cursor(genesis, campaign, next_stage=index + 1)
        if checkpoint is not None:
            entry["campaign_checkpoint_digest"] = genesis.persist(checkpoint)["checkpoint"]
            entry["durable_before_next_stage"] = True
        else:
            entry["campaign_checkpoint_digest"] = ""
            entry["durable_before_next_stage"] = False

    cursor = _validate_cursor(genesis, campaign)
    if cursor is None:  # pragma: no cover
        raise OpenMetamorphosisCampaignError("v2 campaign cursor vanished")
    record = {
        "schema": CAMPAIGN_SCHEMA,
        "campaign_digest": campaign["campaign_digest"],
        "stage_digests": list(campaign["stage_digests"]),
        "executed": executed,
        "next_stage": cursor["next_stage"],
        "completed": int(cursor["next_stage"]) == len(stages),
        "cursor_digest": cursor["cursor_digest"],
        "final_state_digest": genesis.state["state_digest"],
        "current_policy": policy_controller.bound_policy(genesis),
        "current_language": language_controller.bound_language(genesis),
    }
    record["run_digest"] = digest_of(record)
    return record
