#!/usr/bin/env python3
"""Assemble the first M073 scientific result from already-preserved phase artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
M073 = ROOT / "experiments" / "M073"
PROTOCOL_PATH = M073 / "PROTOCOL.json"
INDUCTION_PATH = M073 / "CAPSULE_INDUCTION.json"
HOLDOUT_PATH = M073 / "HOLDOUT_TASKS.json"
LINEAGE_PATH = M073 / "HOLDOUT_LINEAGE_RESULT.json"
CONTROL_PATH = M073 / "HOLDOUT_CONTROL_RESULT.json"
OUTPUT_PATH = M073 / "RESULT.json"


def _read(path: Path, schema: str) -> dict[str, object]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if value.get("schema") != schema:
        raise ValueError(f"unexpected M073 schema in {path.name}")
    return value


def _canonical_sha(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def assemble(
    protocol_path: Path = PROTOCOL_PATH, induction_path: Path = INDUCTION_PATH,
    holdout_path: Path = HOLDOUT_PATH, lineage_path: Path = LINEAGE_PATH,
    control_path: Path = CONTROL_PATH,
) -> dict[str, object]:
    protocol = _read(protocol_path, "m073-skill-appropriation-protocol-v1")
    induction = _read(induction_path, "m073-capsule-induction-v1")
    holdout = _read(holdout_path, "m073-holdout-task-materialization-v1")
    lineage = _read(lineage_path, "m073-holdout-lineage-result-v1")
    controls = _read(control_path, "m073-holdout-control-result-v1")
    threshold = protocol.get("preregistered_positive_threshold")
    if not isinstance(threshold, dict):
        raise ValueError("M073 protocol lacks its positive threshold")

    holdout_digest = holdout.get("holdout_materialization_sha256")
    if lineage.get("holdout_materialization_sha256") != holdout_digest:
        raise ValueError("M073 lineage result targets a different holdout materialization")
    if controls.get("holdout_materialization_sha256") != holdout_digest:
        raise ValueError("M073 control result targets a different holdout materialization")
    if lineage.get("capsule_sha256") != induction.get("capsule_sha256"):
        raise ValueError("M073 lineage result used a different capsule")
    if holdout.get("capsule_sha256") != induction.get("capsule_sha256"):
        raise ValueError("M073 holdouts were materialized for a different capsule")

    observed = {
        "teacher_valid_repairs": induction.get("teacher_valid_repairs"),
        "unique_capsules_induced": induction.get("unique_capsules_induced"),
        "complete_lineage_holdouts_passed": lineage.get("holdouts_passed"),
        "complete_lineage_holdouts_total": lineage.get("holdouts_total"),
        "complete_lineage_case_failures": lineage.get("case_failures"),
        "no_capsule_holdouts_passed": controls.get("no_capsule_holdouts_passed"),
        "memorizer_holdouts_passed": controls.get("memorizer_holdouts_passed"),
        "corrupted_teacher_capsules_induced": induction.get("corrupted_teacher_capsules_induced"),
        "holdout_model_calls": lineage.get("teacher_calls"),
        "capsule_committed_before_holdout_materialization": bool(
            holdout.get("capsule_commit") and holdout.get("capsule_blob")
        ),
    }
    checks = {
        "teacher_valid_repairs": observed["teacher_valid_repairs"] == threshold.get("teacher_valid_repairs"),
        "unique_capsules_induced": observed["unique_capsules_induced"] == threshold.get("unique_capsules_induced"),
        "complete_lineage_holdouts_passed": (
            observed["complete_lineage_holdouts_passed"]
            == threshold.get("complete_lineage_holdouts_passed")
        ),
        "complete_lineage_holdouts_total": (
            observed["complete_lineage_holdouts_total"]
            == threshold.get("complete_lineage_holdouts_total")
        ),
        "complete_lineage_case_failures": (
            observed["complete_lineage_case_failures"]
            == threshold.get("complete_lineage_case_failures")
        ),
        "no_capsule_holdouts_passed_max": (
            isinstance(observed["no_capsule_holdouts_passed"], int)
            and observed["no_capsule_holdouts_passed"]
            <= int(threshold.get("no_capsule_holdouts_passed_max", -1))
        ),
        "memorizer_holdouts_passed_max": (
            isinstance(observed["memorizer_holdouts_passed"], int)
            and observed["memorizer_holdouts_passed"]
            <= int(threshold.get("memorizer_holdouts_passed_max", -1))
        ),
        "corrupted_teacher_capsules_induced": (
            observed["corrupted_teacher_capsules_induced"]
            == threshold.get("corrupted_teacher_capsules_induced")
        ),
        "holdout_model_calls": observed["holdout_model_calls"] == threshold.get("holdout_model_calls"),
        "capsule_committed_before_holdout_materialization": (
            observed["capsule_committed_before_holdout_materialization"]
            is threshold.get("capsule_committed_before_holdout_materialization")
        ),
        "lineage_did_not_read_teacher_responses": lineage.get("teacher_responses_read") is False,
        "lineage_did_not_read_training_tasks": lineage.get("training_tasks_read") is False,
        "lineage_external_model_absent": lineage.get("external_model_imported_or_invoked") is False,
        "memorizer_has_no_holdout_hash_hit": controls.get("memorizer_exact_training_hash_hits") == 0,
        "teacher_calls_during_controls": controls.get("teacher_calls_during_controls") == 0,
    }
    claim_passed = all(checks.values())
    result: dict[str, object] = {
        "schema": "m073-result-v1",
        "status": "passed_preregistered_threshold" if claim_passed else "failed_preregistered_threshold",
        "claim_passed": claim_passed,
        "observed": observed,
        "checks": checks,
        "capsule_sha256": induction.get("capsule_sha256"),
        "holdout_materialization_sha256": holdout_digest,
        "lineage_result_sha256": lineage.get("lineage_result_sha256"),
        "control_result_sha256": controls.get("control_result_sha256"),
        "attribution": {
            "teacher_is_external_and_not_lineage_owned": True,
            "holdout_transformations_are_model_free": lineage.get("teacher_calls") == 0,
            "supported_claim_if_positive": (
                "bounded model-to-lineage skill appropriation mechanism evidence"
            ),
            "genesis_gate_2_or_3_completed": False,
            "general_software_engineering_claim": False,
            "agi_claim": False,
            "safe_deployment_claim": False,
        },
    }
    result["result_sha256"] = _canonical_sha(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=PROTOCOL_PATH)
    parser.add_argument("--induction", type=Path, default=INDUCTION_PATH)
    parser.add_argument("--holdouts", type=Path, default=HOLDOUT_PATH)
    parser.add_argument("--lineage", type=Path, default=LINEAGE_PATH)
    parser.add_argument("--controls", type=Path, default=CONTROL_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("M073 scientific result already exists; refusing overwrite")
    result = assemble(
        args.protocol, args.induction, args.holdouts, args.lineage, args.controls,
    )
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        "claim_passed": result["claim_passed"],
        "result_sha256": result["result_sha256"],
        "status": result["status"],
    }, sort_keys=True))
    return 0 if result["claim_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
