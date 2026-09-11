"""Canonical DEVELOPMENT reproduction of the bounded Genesis metamorphosis milestone.

This is a reproduction driver, not a scientific gate runner. It deliberately launches
three fresh Python interpreters around the persistent checkpoint so process-local state
cannot carry the demonstrated lineage across the reconstruction boundaries.
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
from genesis import meta_policy_controller as meta
from genesis import metamorphic_campaign as campaign
from genesis import migration, policies, policy_controller, policy_mutations, program_forms
from genesis import recovery
from genesis import recursive_policy_fixtures as fixtures
from genesis import retentive_objectives as retentive
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis

SCHEMA = "genesis-development-metamorphosis-reproduction-v1"
HOST = tr.provenance("host_written", produced_by="canonical DEVELOPMENT metamorphosis reproducer")

OBJECTIVE_ONE = (
    {"task_id": "m0", "input": 1, "expected": 1},
)
OBJECTIVE_TWO = (
    *OBJECTIVE_ONE,
    {"task_id": "m1", "input": 2, "expected": 16},
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
                "policy_mutations": 64,
                "policy_evaluations": 256,
                "meta_policy_candidates": 64,
                "meta_policy_evaluations": 256,
                "probes": 8,
            }
        ),
        isolation=tr.Isolation(),
        grade=fixtures.grade_expected,
    )


def _world(tasks, *, with_portable_substrate: bool = False):
    substrates = {}
    if with_portable_substrate:
        substrates["portable-generated-program"] = migration.Substrate(
            "portable-generated-program",
            {program_forms.REBIND_OPERATION: program_forms.portable_target_for},
        )
    return controller.world(
        tasks=tasks,
        demands={},
        substrates=substrates,
        probe_registry=bodies.PROBE_REGISTRY,
        component_operations={},
        artifacts={},
        grade=fixtures.grade_expected,
    )


def _stages():
    return (
        campaign.objective(_world(OBJECTIVE_ONE), name="learn-square"),
        campaign.require_form(
            _world(OBJECTIVE_ONE, with_portable_substrate=True),
            (program_forms.PORTABLE_PROGRAM_TARGET,),
            name="adapt-form-from-environmental-constraint",
        ),
        campaign.objective(_world(OBJECTIVE_TWO), name="extend-after-selected-transition"),
    )


def _seed_policy() -> dict[str, Any]:
    return policies.create(
        registry_reference=bodies.PROBE_REGISTRY,
        operation_names=("increment",),
        max_length=1,
        ceiling_length=2,
        max_candidates=64,
    )


def _seed_meta() -> dict[str, Any]:
    return meta.create_meta_policy(
        (policy_mutations.create("add_operation", operation="negate"),)
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


def _machinery_record(genesis: Genesis) -> dict[str, Any]:
    policy = policy_controller.bound_policy(genesis)
    meta_policy = meta.bound_meta_policy(genesis)
    return {
        "policy": policy,
        "policy_digest": "" if policy is None else tr.digest_of(policy),
        "meta_policy": meta_policy,
        "meta_policy_digest": "" if meta_policy is None else tr.digest_of(meta_policy),
    }


def _common_record(genesis: Genesis) -> dict[str, Any]:
    return {
        "body": _body_record(genesis),
        "machinery": _machinery_record(genesis),
        "budget": genesis.budget.record(),
        "generation": genesis.state["generation"],
        "state_digest": genesis.state["state_digest"],
        "admitted_source_sha256": genesis.admitted_source_sha256,
        "evaluation_contract_digest": genesis.evaluation_contract["contract_digest"],
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
        seed_meta_policy=_seed_meta(),
        max_rounds_per_objective=96,
        checkpoint_directory=checkpoint,
        max_stages=2,
    )
    decision = run["executed"][1]
    payload = {
        "schema": SCHEMA,
        "phase": 1,
        "before": before,
        "after": _common_record(genesis),
        "campaign_digest": run["campaign_digest"],
        "next_stage": run["next_stage"],
        "completed": run["completed"],
        "executed_types": [item["type"] for item in run["executed"]],
        "architectural_selection": decision["transition_selection"],
        "selected_action": decision.get("selected_action", ""),
        "migration": run["migration"],
        "metamorphosis": run["metamorphosis"],
    }
    _write_json(result, payload)


def _phase_two(checkpoint: Path, result: Path) -> None:
    genesis = recovery.restore_lineage(checkpoint, grade=fixtures.grade_expected)
    before = _common_record(genesis)
    run = campaign.run(
        genesis,
        _stages(),
        max_rounds_per_objective=96,
        checkpoint_directory=checkpoint,
    )
    causal = genesis.state["acquisitions"][-1].get("causal_dependency", {})
    corpus = retentive.bound_corpus(genesis)
    payload = {
        "schema": SCHEMA,
        "phase": 2,
        "before": before,
        "after": _common_record(genesis),
        "campaign_digest": run["campaign_digest"],
        "next_stage": run["next_stage"],
        "completed": run["completed"],
        "executed_indices": [item["index"] for item in run["executed"]],
        "executed_types": [item["type"] for item in run["executed"]],
        "metamorphosis": run["metamorphosis"],
        "causal_dependency": causal,
        "retained_question_digests": list(corpus["question_digests"]),
    }
    _write_json(result, payload)


def _phase_three(checkpoint: Path, result: Path) -> None:
    genesis = recovery.restore_lineage(checkpoint, grade=fixtures.grade_expected)
    before = _common_record(genesis)
    run = campaign.run(genesis, _stages(), checkpoint_directory=checkpoint)
    payload = {
        "schema": SCHEMA,
        "phase": 3,
        "before": before,
        "after": _common_record(genesis),
        "campaign_digest": run["campaign_digest"],
        "completed": run["completed"],
        "executed": run["executed"],
        "metamorphosis": run["metamorphosis"],
    }
    _write_json(result, payload)


def _run_worker(phase: int, checkpoint: Path, result: Path) -> None:
    if phase == 1:
        _phase_one(checkpoint, result)
    elif phase == 2:
        _phase_two(checkpoint, result)
    elif phase == 3:
        _phase_three(checkpoint, result)
    else:  # pragma: no cover - argparse constrains this
        raise ValueError(f"unknown phase: {phase}")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _semantic_report(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
) -> dict[str, Any]:
    checks = {
        "phase1_stops_at_persisted_post_migration_cursor": (
            phase1["next_stage"] == 2 and phase1["completed"] is False
        ),
        "runtime_selected_migration_by_unique_strict_maximum": (
            phase1["selected_action"] == "migrate:portable-generated-program"
            and phase1["architectural_selection"]["selection_reason"] == "unique_strict_maximum"
        ),
        "migration_preserved_measured_capability": (
            phase1["migration"]["capability"]["preserved"] is True
        ),
        "fresh_process_restored_same_campaign": (
            phase2["campaign_digest"] == phase1["campaign_digest"]
        ),
        "fresh_process_completed_later_objective": (
            phase2["completed"] is True
            and phase2["executed_indices"] == [2]
            and phase2["executed_types"] == ["objective"]
        ),
        "continued_in_migrated_executable_form": (
            phase2["after"]["body"]["target"] == program_forms.PORTABLE_PROGRAM_TARGET
            and phase2["after"]["body"]["operations"] == ["square", "square"]
        ),
        "retained_both_objective_questions": (
            len(phase2["retained_question_digests"]) == 2
        ),
        "later_improvement_has_runtime_ablation_dependency": (
            phase2["causal_dependency"].get("established") is True
            and phase2["causal_dependency"].get("newly_solved_lost_without_acquisition") == ["m1"]
        ),
        "metamorphosis_verdict_succeeded": (
            phase2["metamorphosis"]["succeeded"] is True
            and phase2["metamorphosis"]["causally_established_after_migration"] == 1
        ),
        "trust_root_and_evaluation_contract_unchanged": (
            phase1["before"]["admitted_source_sha256"]
            == phase2["after"]["admitted_source_sha256"]
            and phase1["before"]["evaluation_contract_digest"]
            == phase2["after"]["evaluation_contract_digest"]
        ),
        "third_fresh_process_replays_completion_without_work": (
            phase3["completed"] is True
            and phase3["executed"] == []
            and phase3["campaign_digest"] == phase2["campaign_digest"]
            and phase3["metamorphosis"] == phase2["metamorphosis"]
            and phase3["after"]["budget"] == phase2["after"]["budget"]
            and phase3["after"]["body"] == phase2["after"]["body"]
        ),
    }
    evidence = {
        "campaign_digest": phase2["campaign_digest"],
        "initial_body": phase1["before"]["body"],
        "post_migration_body": phase1["after"]["body"],
        "final_body": phase2["after"]["body"],
        "final_policy_digest": phase2["after"]["machinery"]["policy_digest"],
        "final_meta_policy_digest": phase2["after"]["machinery"]["meta_policy_digest"],
        "final_budget": phase2["after"]["budget"],
        "metamorphosis": phase2["metamorphosis"],
        "causal_dependency": phase2["causal_dependency"],
        "retained_question_digests": phase2["retained_question_digests"],
        "admitted_source_sha256": phase2["after"]["admitted_source_sha256"],
        "evaluation_contract_digest": phase2["after"]["evaluation_contract_digest"],
    }
    report = {
        "schema": SCHEMA,
        "classification": "DEVELOPMENT_REPRODUCTION",
        "passed": all(checks.values()),
        "checks": checks,
        "evidence": evidence,
        "claim_boundary": {
            "demonstrates": (
                "bounded persistent empirical metamorphosis under the prospectively admitted "
                "DEVELOPMENT apparatus"
            ),
            "does_not_demonstrate": [
                "AGI",
                "generality",
                "consciousness",
                "open-ended evolution",
                "self-generated goals",
                "arbitrary self-programming",
                "lineage-generated migration algorithms",
            ],
        },
        "fresh_interpreter_boundaries": 2,
    }
    digest_payload = {
        key: value for key, value in report.items() if key != "reproduction_digest"
    }
    report["reproduction_digest"] = tr.digest_of(digest_payload)
    return report


def _invoke_worker(phase: int, checkpoint: Path, result: Path) -> None:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker-phase",
        str(phase),
        "--checkpoint-dir",
        str(checkpoint),
        "--result-file",
        str(result),
    ]
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = "0"
    subprocess.run(command, check=True, env=env)


def run_reproduction(output_dir: Path) -> dict[str, Any]:
    """Run the canonical three-interpreter DEVELOPMENT reproduction."""
    output_dir = output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError(f"output directory must be empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    checkpoint = output_dir / "checkpoint"
    phase_paths = [output_dir / f"phase-{number}.json" for number in (1, 2, 3)]
    for number, result in enumerate(phase_paths, start=1):
        _invoke_worker(number, checkpoint, result)

    phase1, phase2, phase3 = (_load_json(path) for path in phase_paths)
    report = _semantic_report(phase1, phase2, phase3)
    _write_json(output_dir / "report.json", report)
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Reproduce the bounded Genesis DEVELOPMENT metamorphosis campaign across "
            "fresh Python interpreter boundaries."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Empty directory where checkpoint, phase records and report.json are written.",
    )
    parser.add_argument("--worker-phase", type=int, choices=(1, 2, 3), help=argparse.SUPPRESS)
    parser.add_argument("--checkpoint-dir", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--result-file", type=Path, help=argparse.SUPPRESS)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.worker_phase is not None:
        if args.checkpoint_dir is None or args.result_file is None:
            raise SystemExit("worker mode requires --checkpoint-dir and --result-file")
        _run_worker(args.worker_phase, args.checkpoint_dir, args.result_file)
        return 0

    if args.output_dir is None:
        raise SystemExit("--output-dir is required")
    report = run_reproduction(args.output_dir)
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
