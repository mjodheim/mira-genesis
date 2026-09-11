"""Canonical DEVELOPMENT reproduction of the Genesis v2 Open Metamorphosis target.

The driver launches three fresh Python interpreters.  The only continuity between phases is the
persistent Genesis checkpoint:

1. exhaust L0, construct and select L1, apply L1 through ordinary policy/body machinery;
2. restore in a fresh interpreter, exhaust the retained+new objective, derive recursive primitives
   from lineage history, construct L2 using L1 as an invoked primitive, and apply L2 normally;
3. restore once more and verify the final lineage, causal records and budgets without executing any
   new search or transformation work.

This is a DEVELOPMENT reproducer.  It does not claim AGI, generality, unbounded self-improvement,
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
from genesis import objective_policy_controller as opc
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


def _seed_policy() -> dict[str, Any]:
    return policies.create(
        registry_reference=bodies.PROBE_REGISTRY,
        operation_names=("increment", "negate"),
        max_length=1,
        ceiling_length=3,
        max_candidates=5,
    )


def _deepen() -> dict[str, Any]:
    return tl.create_step("increase_policy_depth")


def _widen_five() -> dict[str, Any]:
    return tl.create_step("increase_candidate_limit", amount=5)


def _add_triple() -> dict[str, Any]:
    return tl.create_step("append_policy_operation", operation="triple")


def _seed_language() -> dict[str, Any]:
    return tl.create_language(
        (
            tl.create_operator("deepen", (_deepen(),)),
            tl.create_operator("widen-five", (_widen_five(),)),
            tl.create_operator("add-triple", (_add_triple(),)),
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
    language = tlc.bound_language(genesis)
    corpus = retentive.bound_corpus(genesis)
    return {
        "body": _body_record(genesis),
        "policy": policy,
        "policy_digest": "" if policy is None else policy["policy_digest"],
        "language": language,
        "language_digest": "" if language is None else language["language_digest"],
        "budget": genesis.budget.record(),
        "generation": genesis.state["generation"],
        "state_digest": genesis.state["state_digest"],
        "journal_head": genesis.journal.head,
        "admitted_source_sha256": genesis.admitted_source_sha256,
        "evaluation_contract_digest": genesis.evaluation_contract["contract_digest"],
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
    here = _world(OBJECTIVE_ONE)
    before = _common_record(genesis)
    exhausted = retentive.run_policy(
        genesis,
        here,
        seed_policy=_seed_policy(),
        max_steps=32,
        checkpoint_directory=checkpoint,
    )
    if not opc.exhausted(genesis, here):
        raise RuntimeError("phase 1 seed policy did not exhaust")
    extension = tlc.run_extension_search(
        genesis,
        here,
        admitted_steps=(_deepen(), _widen_five(), _add_triple()),
        seed_language=_seed_language(),
        checkpoint_directory=checkpoint,
    )
    applied = application.apply_acquired_extension(
        genesis,
        here,
        max_policy_steps=32,
        checkpoint_directory=checkpoint,
    )
    payload = {
        "schema": SCHEMA,
        "phase": 1,
        "before": before,
        "after": _common_record(genesis),
        "seed_policy_exhausted": True,
        "seed_policy_attempts": [
            step for step in exhausted["steps"] if step.get("intent") == "GenerateTransform"
        ],
        "extension_status": extension["status"],
        "extension_certificate": extension["certificate"],
        "application_digest": applied["application_digest"],
        "causal_record": applied["causal_record"],
        "adopted_body": applied["causal_record"]["adopted_body"],
    }
    _write_json(result, payload)


def _phase_two(checkpoint: Path, result: Path) -> None:
    genesis = recovery.restore_lineage(checkpoint, grade=fixtures.grade_expected)
    here = _world(OBJECTIVE_TWO)
    before = _common_record(genesis)
    exhausted = retentive.run_policy(
        genesis,
        here,
        max_steps=64,
        checkpoint_directory=checkpoint,
    )
    if not opc.exhausted(genesis, here):
        raise RuntimeError("phase 2 inherited policy did not exhaust on the retained objective")
    recursive_run = recursive.run_recursive_extension_search(
        genesis,
        here,
        checkpoint_directory=checkpoint,
    )
    if not recursive_run.get("recursive_extension"):
        raise RuntimeError("phase 2 produced no recursive transformation-language extension")
    applied = application.apply_acquired_extension(
        genesis,
        here,
        max_policy_steps=64,
        checkpoint_directory=checkpoint,
    )
    payload = {
        "schema": SCHEMA,
        "phase": 2,
        "before": before,
        "after": _common_record(genesis),
        "inherited_policy_exhausted": True,
        "inherited_policy_attempts": [
            step for step in exhausted["steps"] if step.get("intent") == "GenerateTransform"
        ],
        "recursive_result": {
            key: value for key, value in recursive_run.items() if key != "extension_run"
        },
        "recursive_extension_certificate": recursive_run["extension_run"]["certificate"],
        "application_digest": applied["application_digest"],
        "causal_record": applied["causal_record"],
        "adopted_body": applied["causal_record"]["adopted_body"],
    }
    _write_json(result, payload)


def _phase_three(checkpoint: Path, result: Path) -> None:
    genesis = recovery.restore_lineage(checkpoint, grade=fixtures.grade_expected)
    before = _common_record(genesis)
    # Intentionally execute no search, mutation or body work.  The final phase is a pure
    # reconstruction/inspection of the persistent lineage after a second process death.
    after = _common_record(genesis)
    payload = {
        "schema": SCHEMA,
        "phase": 3,
        "before": before,
        "after": after,
        "executed_search_rounds": 0,
        "executed_body_evaluations": 0,
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
    checks = {
        "first_language_extension_selected_by_evidence": (
            phase1["extension_status"] == "unique_strict_maximum"
            and l1["held_language_exhausted"] is True
        ),
        "first_language_extension_was_used_not_directly_installed_as_body": (
            phase1["causal_record"]["language_ablation"]["established"] is True
            and phase1["adopted_body"]["program"]["operations"] == ["negate", "negate"]
        ),
        "fresh_process_restored_l1_exactly": (
            phase2["before"]["language_digest"] == phase1["after"]["language_digest"]
            and phase2["before"]["policy_digest"] == phase1["after"]["policy_digest"]
            and phase2["before"]["body"]["artifact"] == phase1["after"]["body"]["artifact"]
        ),
        "second_extension_is_recursive": (
            phase2["recursive_result"]["recursive_extension"] is True
            and phase2["recursive_result"]["lineage_history_derived_invocation"] is True
            and phase2["recursive_result"]["caller_supplied_recursive_operator"] is False
            and l1_operator in invoked
        ),
        "second_extension_depends_on_first_under_ablation": (
            phase2["recursive_result"]["dependency_ablation"]["established"] is True
            and phase2["recursive_result"]["dependency_ablation"][
                "descendant_reconstructs_without_predecessor"
            ] is False
        ),
        "second_extension_enables_new_retaining_body": (
            l2["witness"]["operations"] == ["increment", "increment", "triple"]
            and phase2["adopted_body"]["program"]["operations"]
            == ["increment", "increment", "triple"]
            and len(phase2["after"]["retained_question_digests"]) == 2
        ),
        "language_lineage_is_two_generations_deep": (
            len(phase2["after"]["extension_records"]) == 2
            and phase2["after"]["language"]["parent_language_digest"]
            == phase1["after"]["language_digest"]
        ),
        "causal_language_to_policy_to_body_chain_repeated_twice": (
            len(phase2["after"]["causal_records"]) == 2
            and len(phase2["after"]["policy_body_link_digests"]) >= 2
            and len(phase2["after"]["recursive_records"]) == 1
        ),
        "trust_root_and_evaluation_contract_never_changed": (
            phase1["before"]["admitted_source_sha256"]
            == phase1["after"]["admitted_source_sha256"]
            == phase2["before"]["admitted_source_sha256"]
            == phase2["after"]["admitted_source_sha256"]
            == phase3["after"]["admitted_source_sha256"]
            and phase1["before"]["evaluation_contract_digest"]
            == phase1["after"]["evaluation_contract_digest"]
            == phase2["before"]["evaluation_contract_digest"]
            == phase2["after"]["evaluation_contract_digest"]
            == phase3["after"]["evaluation_contract_digest"]
        ),
        "third_interpreter_reconstructs_without_redraw": (
            phase3["before"]["state_digest"] == phase2["after"]["state_digest"]
            and phase3["after"]["state_digest"] == phase3["before"]["state_digest"]
            and phase3["after"]["budget"] == phase3["before"]["budget"]
            and phase3["executed_search_rounds"] == 0
            and phase3["executed_body_evaluations"] == 0
        ),
        "exactly_two_language_application_evaluations_spent": (
            _spent(phase2["after"], "language_application_evaluations") == 2
        ),
    }
    report_payload = {
        "schema": SCHEMA,
        "classification": CLASSIFICATION,
        "passed": all(checks.values()),
        "fresh_interpreter_boundaries": 2,
        "checks": checks,
        "phase_state_digests": [
            phase1["after"]["state_digest"],
            phase2["after"]["state_digest"],
            phase3["after"]["state_digest"],
        ],
        "final_language_digest": phase3["after"]["language_digest"],
        "final_policy_digest": phase3["after"]["policy_digest"],
        "trust_root_source_sha256": phase3["after"]["admitted_source_sha256"],
        "evaluation_contract_digest": phase3["after"]["evaluation_contract_digest"],
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
    report_payload["reproduction_digest"] = tr.digest_of(report_payload)
    return report_payload


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
