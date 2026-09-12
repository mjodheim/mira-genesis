"""Canonical DEVELOPMENT reproduction of the Genesis v2 Open Metamorphosis target.

Three fresh Python interpreters are launched around one persistent Genesis checkpoint. The reproducer
supplies only the prospectively fixed environmental campaign plus the initial bounded policy/language.
It never calls a first-extension, recursive-extension or language-application controller directly.
Those architectural hand-offs are owned by ``open_metamorphosis_runtime`` and the persistent campaign
cursor.

Phase 1 executes one campaign stage and dies after the committed prefix. Phase 2 restores and the
cursor selects the later objective; the runtime itself detects that one endogenous language extension
already exists and therefore enters recursive language search. Phase 3 restores the completed campaign
and replays it with zero executed stages and zero new spend.

This is DEVELOPMENT evidence only. It does not claim AGI, generality, unbounded self-improvement,
self-generated goals, arbitrary code generation, or mutability of the trust root/evaluator.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping

from genesis import controller
from genesis import development_bodies as bodies
from genesis import open_metamorphosis_campaign as campaign
from genesis import policies, policy_body_lineage, policy_controller, recovery
from genesis import recursive_policy_fixtures as fixtures
from genesis import recursive_transformation_language as recursive
from genesis import retentive_objectives as retentive
from genesis import state as st
from genesis import transformation_language as tl
from genesis import transformation_language_application as application
from genesis import transformation_language_controller as tlc
from genesis import trust_root as tr
from genesis.loop import Genesis

SCHEMA = "genesis-development-open-metamorphosis-reproduction-v1"
CLASSIFICATION = "DEVELOPMENT_OPEN_METAMORPHOSIS_REPRODUCTION"
HOST = tr.provenance("host_written", produced_by="canonical Genesis v2 reproducer")

OBJECTIVE_ONE = (
    {"task_id": "open-0", "input": -3, "expected": -3},
)
OBJECTIVE_TWO = (
    *OBJECTIVE_ONE,
    {"task_id": "open-1", "input": -5, "expected": -9},
)


def _state() -> dict[str, Any]:
    return st.create_state(
        body_digest=tr.artifact_digest_of(fixtures.null_body)["artifact_digest"],
        components=[
            {
                "name": "operator_table",
                "origin": "seed",
                "certificate": None,
                "provenance": HOST,
            }
        ],
        vocabulary=[{"name": "axis_progress", "origin": "seed", "certificate": None}],
    )


def _genesis() -> Genesis:
    return Genesis(
        state=_state(),
        body_factory=fixtures.null_body,
        budget=tr.Budget(
            limits={
                "generations": 96,
                "policy_updates": 0,
                "policy_evaluations": 0,
                "policy_mutations": 0,
                "language_operator_evaluations": 128,
                "language_body_evaluations": 512,
                "language_application_evaluations": 2,
            }
        ),
        isolation=tr.Isolation(),
        grade=fixtures.grade_expected,
    )


def _world(tasks):
    return controller.world(
        tasks=tasks,
        demands={},
        substrates={},
        probe_registry=bodies.PROBE_REGISTRY,
        component_operations={},
        artifacts={},
        grade=fixtures.grade_expected,
    )


def _stages():
    return (
        campaign.objective(_world(OBJECTIVE_ONE), name="first-open-language-objective"),
        campaign.objective(_world(OBJECTIVE_TWO), name="recursive-open-language-objective"),
    )


def _seed_policy() -> dict[str, Any]:
    return policies.create(
        registry_reference=bodies.PROBE_REGISTRY,
        operation_names=("increment", "negate"),
        max_length=1,
        ceiling_length=3,
        max_candidates=5,
    )


def _seed_language() -> dict[str, Any]:
    deepen = tl.create_step("increase_policy_depth")
    widen = tl.create_step("increase_candidate_limit", amount=5)
    add_triple = tl.create_step("append_policy_operation", operation="triple")
    return tl.create_language(
        (
            tl.create_operator("deepen", (deepen,)),
            tl.create_operator("widen-five", (widen,)),
            tl.create_operator("add-triple", (add_triple,)),
        ),
        max_operator_steps=2,
    )


def _body_record(genesis: Genesis) -> dict[str, Any]:
    body = genesis.body_factory
    configuration = getattr(body, "configuration", None)
    operations = []
    if isinstance(configuration, Mapping):
        operations = list(configuration.get("operations", ()))
    return {
        "artifact": tr.artifact_digest_of(body),
        "target": getattr(body, "target", ""),
        "operations": operations,
    }


def _causal_records(genesis: Genesis) -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in genesis.state.get("observations", [])
        if item.get("schema") == application.CAUSAL_RECORD_SCHEMA
    ]


def _recursive_records(genesis: Genesis) -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in genesis.state.get("observations", [])
        if item.get("schema") == recursive.RECURSION_SCHEMA and item.get("recursive_extension")
    ]


def _extension_records(genesis: Genesis) -> list[dict[str, Any]]:
    return [
        dict(item.get("certificate") or {})
        for item in genesis.state.get("observations", [])
        if item.get("kind") == "transformation_language_extension"
        and isinstance(item.get("certificate"), Mapping)
    ]


def _common_record(genesis: Genesis) -> dict[str, Any]:
    policy = policy_controller.bound_policy(genesis)
    held_language = tlc.bound_language(genesis)
    corpus = retentive.bound_corpus(genesis)
    return {
        "body": _body_record(genesis),
        "policy": policy,
        "policy_digest": "" if policy is None else policy["policy_digest"],
        "language": held_language,
        "language_digest": "" if held_language is None else held_language["language_digest"],
        "budget": genesis.budget.record(),
        "generation": genesis.state["generation"],
        "state_digest": genesis.state["state_digest"],
        "journal_head": genesis.journal.head,
        "admitted_source_sha256": genesis.admitted_source_sha256,
        "evaluation_contract_digest": genesis.evaluation_contract["contract_digest"],
        "admitted_isolation": genesis.admitted_isolation.record(),
        "runtime_isolation": genesis.isolation.record(),
        "allow_self_reported_outcomes": bool(genesis.allow_self_reported_outcomes),
        "extension_records": _extension_records(genesis),
        "causal_records": _causal_records(genesis),
        "recursive_records": _recursive_records(genesis),
        "policy_body_link_digests": [item["link_digest"] for item in policy_body_lineage.links(genesis)],
        "retained_question_digests": [] if corpus is None else list(corpus["question_digests"]),
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _phase_one(checkpoint: Path, result: Path) -> None:
    genesis = _genesis()
    before = _common_record(genesis)
    run = campaign.run(
        genesis,
        _stages(),
        seed_policy=_seed_policy(),
        seed_language=_seed_language(),
        max_policy_steps=64,
        checkpoint_directory=checkpoint,
        max_stages=1,
    )
    if len(run["executed"]) != 1:
        raise RuntimeError("phase 1 did not execute exactly one cursor-selected stage")
    runtime_run = run["executed"][0]["run"]
    extensions = _extension_records(genesis)
    causals = _causal_records(genesis)
    payload = {
        "schema": SCHEMA,
        "phase": 1,
        "before": before,
        "after": _common_record(genesis),
        "campaign_digest": run["campaign_digest"],
        "next_stage": run["next_stage"],
        "completed": run["completed"],
        "executed_indices": [item["index"] for item in run["executed"]],
        "runtime_selected_generation": runtime_run["machinery_generation_selected_by_runtime"],
        "runtime_selected_mode": runtime_run["machinery_mode"],
        "extension_certificate": extensions[-1],
        "causal_record": causals[-1],
        "adopted_body": causals[-1]["adopted_body"],
    }
    _write_json(result, payload)


def _phase_two(checkpoint: Path, result: Path) -> None:
    genesis = recovery.restore_lineage(checkpoint, grade=fixtures.grade_expected)
    before = _common_record(genesis)
    run = campaign.run(
        genesis,
        _stages(),
        max_policy_steps=64,
        checkpoint_directory=checkpoint,
    )
    if [item["index"] for item in run["executed"]] != [1]:
        raise RuntimeError("phase 2 did not resume exactly the persisted second campaign stage")
    runtime_run = run["executed"][0]["run"]
    extensions = _extension_records(genesis)
    causals = _causal_records(genesis)
    recursive_records = _recursive_records(genesis)
    payload = {
        "schema": SCHEMA,
        "phase": 2,
        "before": before,
        "after": _common_record(genesis),
        "campaign_digest": run["campaign_digest"],
        "next_stage": run["next_stage"],
        "completed": run["completed"],
        "executed_indices": [item["index"] for item in run["executed"]],
        "runtime_selected_generation": runtime_run["machinery_generation_selected_by_runtime"],
        "runtime_selected_mode": runtime_run["machinery_mode"],
        "recursive_result": recursive_records[-1],
        "recursive_extension_certificate": extensions[-1],
        "causal_record": causals[-1],
        "adopted_body": causals[-1]["adopted_body"],
    }
    _write_json(result, payload)


def _phase_three(checkpoint: Path, result: Path) -> None:
    genesis = recovery.restore_lineage(checkpoint, grade=fixtures.grade_expected)
    before = _common_record(genesis)
    run = campaign.run(
        genesis,
        _stages(),
        max_policy_steps=64,
        checkpoint_directory=checkpoint,
    )
    after = _common_record(genesis)
    payload = {
        "schema": SCHEMA,
        "phase": 3,
        "before": before,
        "after": after,
        "campaign_digest": run["campaign_digest"],
        "completed": run["completed"],
        "executed": run["executed"],
        "next_stage": run["next_stage"],
    }
    _write_json(result, payload)


def _run_worker(phase: int, checkpoint: Path, result: Path) -> None:
    if phase == 1:
        _phase_one(checkpoint, result)
    elif phase == 2:
        _phase_two(checkpoint, result)
    elif phase == 3:
        _phase_three(checkpoint, result)
    else:  # pragma: no cover
        raise ValueError("unknown phase %r" % phase)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _spent(record: Mapping[str, Any], name: str) -> int:
    return int((record.get("budget") or {}).get("spent", {}).get(name, 0))


def _semantic_report(phase1, phase2, phase3) -> dict[str, Any]:
    l1 = phase1["extension_certificate"]
    l2 = phase2["recursive_extension_certificate"]
    l1_operator = l1["operator"]["operator_digest"]
    invoked = phase2["recursive_result"]["invoked_acquired_operator_digests"]
    reach = phase2["recursive_result"]["dependency_ablation"]["same_round_reach"]
    boundary_records = (
        phase1["before"],
        phase1["after"],
        phase2["before"],
        phase2["after"],
        phase3["before"],
        phase3["after"],
    )
    baseline = boundary_records[0]
    checks = {
        "runtime_owned_first_language_generation": (
            phase1["runtime_selected_generation"] == 1
            and phase1["runtime_selected_mode"] == "first_endogenous_language_extension"
            and phase1["next_stage"] == 1
            and phase1["completed"] is False
            and phase1["executed_indices"] == [0]
        ),
        "first_language_extension_selected_by_evidence": (
            l1["held_language_exhausted"] is True
            and phase1["causal_record"]["language_ablation"]["established"] is True
            and phase1["adopted_body"]["program"]["operations"] == ["negate", "negate"]
        ),
        "fresh_process_restored_exact_committed_prefix": (
            phase2["before"]["state_digest"] == phase1["after"]["state_digest"]
            and phase2["before"]["language_digest"] == phase1["after"]["language_digest"]
            and phase2["before"]["policy_digest"] == phase1["after"]["policy_digest"]
            and phase2["campaign_digest"] == phase1["campaign_digest"]
            and phase2["executed_indices"] == [1]
        ),
        "runtime_owned_recursive_generation": (
            phase2["runtime_selected_generation"] == 2
            and phase2["runtime_selected_mode"] == "recursive_language_extension"
            and phase2["completed"] is True
        ),
        "second_extension_is_lineage_history_recursive": (
            phase2["recursive_result"]["recursive_extension"] is True
            and phase2["recursive_result"]["lineage_history_derived_invocation"] is True
            and phase2["recursive_result"]["caller_supplied_recursive_operator"] is False
            and phase2["recursive_result"]["journal_backed_predecessor_acquisitions"] is True
            and l1_operator in invoked
        ),
        "second_extension_depends_on_first_under_ablation": (
            phase2["recursive_result"]["dependency_ablation"]["established"] is True
            and phase2["recursive_result"]["dependency_ablation"][
                "descendant_reconstructs_without_predecessor"
            ] is False
            and reach["established"] is True
            and reach["complete_candidate_image_measured"] is True
            and reach["strict_reach_loss_without_predecessor"] is True
            and reach["independent_candidate_count"] > 0
            and reach["winner_selection_score"]
            > reach["best_selection_score_without_invoked_predecessor"]
        ),
        "second_extension_enables_new_retaining_body": (
            l2["witness"]["operations"] == ["increment", "increment", "triple"]
            and phase2["adopted_body"]["program"]["operations"]
            == ["increment", "increment", "triple"]
            and len(phase2["after"]["retained_question_digests"]) == 2
        ),
        "two_language_generations_and_two_causal_chains_persist": (
            len(phase2["after"]["extension_records"]) == 2
            and phase2["after"]["language"]["parent_language_digest"]
            == phase1["after"]["language_digest"]
            and len(phase2["after"]["causal_records"]) == 2
            and len(phase2["after"]["policy_body_link_digests"]) >= 2
            and len(phase2["after"]["recursive_records"]) == 1
        ),
        "immutable_authority_boundary_never_changed": (
            all(
                record["admitted_source_sha256"] == baseline["admitted_source_sha256"]
                for record in boundary_records
            )
            and all(
                record["evaluation_contract_digest"] == baseline["evaluation_contract_digest"]
                for record in boundary_records
            )
            and all(
                record["admitted_isolation"] == baseline["admitted_isolation"]
                for record in boundary_records
            )
            and all(
                record["runtime_isolation"] == baseline["runtime_isolation"]
                for record in boundary_records
            )
            and all(
                record["budget"]["limits"] == baseline["budget"]["limits"]
                for record in boundary_records
            )
            and all(record["allow_self_reported_outcomes"] is False for record in boundary_records)
        ),
        "completed_campaign_replays_without_redraw": (
            phase3["campaign_digest"] == phase2["campaign_digest"]
            and phase3["completed"] is True
            and phase3["executed"] == []
            and phase3["before"]["state_digest"] == phase2["after"]["state_digest"]
            and phase3["after"]["state_digest"] == phase3["before"]["state_digest"]
            and phase3["after"]["budget"] == phase3["before"]["budget"]
        ),
        "exactly_two_language_application_revalidations_spent": (
            _spent(phase2["after"], "language_application_evaluations") == 2
        ),
    }
    payload = {
        "schema": SCHEMA,
        "classification": CLASSIFICATION,
        "passed": all(checks.values()),
        "fresh_interpreter_boundaries": 2,
        "checks": checks,
        "campaign_digest": phase3["campaign_digest"],
        "phase_state_digests": [
            phase1["after"]["state_digest"],
            phase2["after"]["state_digest"],
            phase3["after"]["state_digest"],
        ],
        "final_language_digest": phase3["after"]["language_digest"],
        "final_policy_digest": phase3["after"]["policy_digest"],
        "recursive_dependency_evidence_digest": reach["evidence_digest"],
        "trust_root_source_sha256": phase3["after"]["admitted_source_sha256"],
        "evaluation_contract_digest": phase3["after"]["evaluation_contract_digest"],
        "admitted_isolation": phase3["after"]["admitted_isolation"],
        "runtime_isolation": phase3["after"]["runtime_isolation"],
        "budget_limits": phase3["after"]["budget"]["limits"],
        "does_not_demonstrate": [
            "AGI",
            "generality",
            "consciousness",
            "unbounded or open-ended recursive self-improvement",
            "self-generated goals",
            "arbitrary self-programming",
            "mutable trust-root or evaluator authority",
        ],
    }
    payload["reproduction_digest"] = tr.digest_of(payload)
    return payload


def _launch_worker(phase: int, checkpoint: Path, result: Path) -> None:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker-phase",
        str(phase),
        "--checkpoint",
        str(checkpoint),
        "--result",
        str(result),
    ]
    environment = dict(os.environ)
    environment["PYTHONHASHSEED"] = "0"
    subprocess.run(command, check=True, env=environment)


def _orchestrate(output_dir: Path) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    checkpoint = output / "checkpoint"
    paths = [output / "phase-1.json", output / "phase-2.json", output / "phase-3.json"]
    for phase, path in enumerate(paths, start=1):
        _launch_worker(phase, checkpoint, path)
    phase1, phase2, phase3 = (_load_json(path) for path in paths)
    report = _semantic_report(phase1, phase2, phase3)
    _write_json(output / "report.json", report)
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--worker-phase", type=int, choices=(1, 2, 3))
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--result", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.worker_phase is not None:
        if args.checkpoint is None or args.result is None:
            raise SystemExit("worker mode requires --checkpoint and --result")
        _run_worker(args.worker_phase, args.checkpoint, args.result)
        return 0
    if args.output_dir is None:
        raise SystemExit("reproduction mode requires --output-dir")
    report = _orchestrate(args.output_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
