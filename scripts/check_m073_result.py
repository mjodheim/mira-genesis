#!/usr/bin/env python3
"""Recompute the preserved M073 result from its frozen and phase-bound artifacts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import assemble_m073_result as result_assembler
import induce_m073_capsule as induction_runner
import materialize_m073_holdouts as holdout_materializer
import run_m073_holdout_controls as control_runner
import run_m073_holdout_lineage as lineage_runner
import run_m073_teacher as teacher_runner


ROOT = Path(__file__).resolve().parents[1]
M073 = ROOT / "experiments" / "M073"
EXPECTED_PROTOCOL_COMMIT = "78d53d733bdf77eab773414e8d273ed70e31391d"
EXPECTED_RESPONSE_SET_SHA256 = "e01b062a9fead119b40cc35906d0aa9d8584391cba4f79be36c48a4d1ac0ce7e"
EXPECTED_CAPSULE_COMMIT = "760803c4eee9c03caf25d2403c5f072343e17572"
EXPECTED_CAPSULE_SHA256 = "444a8a548d6955ac85795fe9d4fd18d4a0a0aa6d731a94dbd3a4ca0f560f8620"
EXPECTED_HOLDOUT_SHA256 = "dddd19ac48985312d5b218bb56a8de9c7706e24b1a97faeb5a65294d6c18de0c"
EXPECTED_RESULT_SHA256 = "edaf03b4cf922890d010ecdd838de67c9569342b27a6848fae34ab430db03a2e"


def _read(name: str, schema: str) -> dict[str, object]:
    value = json.loads((M073 / name).read_text(encoding="utf-8"))
    if value.get("schema") != schema:
        raise ValueError(f"unexpected M073 schema in {name}")
    return value


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _result_digest(result: dict[str, object]) -> str:
    payload = dict(result)
    payload.pop("result_sha256", None)
    return _canonical_digest(payload)


def verify_result() -> dict[str, object]:
    protocol = _read("PROTOCOL.json", "m073-skill-appropriation-protocol-v1")
    requests = _read("TEACHER_REQUESTS.json", "m073-teacher-request-set-v1")
    responses = _read("TEACHER_RESPONSES.json", "m073-teacher-response-set-v1")
    capsule = _read("SKILL_CAPSULE.json", "mira-skill-capsule-v1")
    induction = _read("CAPSULE_INDUCTION.json", "m073-capsule-induction-v1")
    holdouts = _read("HOLDOUT_TASKS.json", "m073-holdout-task-materialization-v1")
    lineage = _read("HOLDOUT_LINEAGE_RESULT.json", "m073-holdout-lineage-result-v1")
    controls = _read("HOLDOUT_CONTROL_RESULT.json", "m073-holdout-control-result-v1")
    result = _read("RESULT.json", "m073-result-v1")

    if protocol.get("status") != (
        "protocol_frozen_before_capsule_implementation_teacher_demonstrations_or_"
        "holdout_materialization"
    ):
        raise ValueError("M073 frozen protocol status drifted")
    for field in (
        "scientific_result_exists", "teacher_demonstrations_exist", "capsule_exists",
        "holdout_materialized",
    ):
        if protocol.get(field) is not False:
            raise ValueError(f"M073 preregistration was rewritten after observation: {field}")
    if protocol.get("epistemic_bridge", {}).get("genesis_gate_2_claim_permitted") is not False:
        raise ValueError("M073 protocol improperly widens Genesis ownership")

    if requests.get("protocol_commit") != EXPECTED_PROTOCOL_COMMIT:
        raise ValueError("M073 teacher requests no longer bind the frozen protocol")
    if requests.get("teacher_responses_exist") is not False:
        raise ValueError("M073 teacher requests were rewritten after response collection")
    frozen_requests = requests.get("requests")
    response_records = responses.get("responses")
    if not isinstance(frozen_requests, list) or not isinstance(response_records, list):
        raise ValueError("M073 request or response records are malformed")
    if len(frozen_requests) != 4 or len(response_records) != 4:
        raise ValueError("M073 requires exactly four frozen single teacher calls")
    if responses.get("scientific_retries") != 0 or responses.get("call_count") != 4:
        raise ValueError("M073 teacher call count or retry record drifted")
    if responses.get("model") != "gpt-5.6-sol":
        raise ValueError("M073 teacher identity drifted")
    if _canonical_digest(responses) != EXPECTED_RESPONSE_SET_SHA256:
        raise ValueError("M073 preserved teacher responses have semantic drift")
    by_task = {record.get("task_id"): record for record in frozen_requests}
    for response in response_records:
        if not isinstance(response, dict):
            raise ValueError("M073 teacher response record is malformed")
        request = by_task.get(response.get("task_id"))
        if not isinstance(request, dict):
            raise ValueError("M073 response is not bound to a frozen request")
        prompt = teacher_runner.build_prompt(requests, request)
        if response.get("prompt_sha256") != hashlib.sha256(prompt.encode("utf-8")).hexdigest():
            raise ValueError("M073 teacher prompt digest drifted")
        body = response.get("response")
        if not isinstance(body, str):
            raise ValueError("M073 teacher response body is absent")
        if response.get("response_sha256") != hashlib.sha256(body.encode("utf-8")).hexdigest():
            raise ValueError("M073 teacher response body digest drifted")

    recomputed_capsule, recomputed_induction = induction_runner.induce()
    if capsule != recomputed_capsule or induction != recomputed_induction:
        raise ValueError("M073 capsule or induction record differs from frozen demonstrations")
    if capsule.get("capsule_sha256") != EXPECTED_CAPSULE_SHA256:
        raise ValueError("M073 skill capsule digest drifted")
    if induction.get("corrupted_teacher_capsules_induced") != 0:
        raise ValueError("M073 corrupted-teacher control no longer rejects")

    recomputed_holdouts = holdout_materializer.materialize()
    if holdouts != recomputed_holdouts:
        raise ValueError("M073 holdouts differ from their post-capsule materialization")
    if holdouts.get("capsule_commit") != EXPECTED_CAPSULE_COMMIT:
        raise ValueError("M073 holdouts no longer follow the committed capsule boundary")
    if holdouts.get("holdout_materialization_sha256") != EXPECTED_HOLDOUT_SHA256:
        raise ValueError("M073 holdout materialization digest drifted")

    recomputed_lineage = lineage_runner.run()
    recomputed_controls = control_runner.run()
    if lineage != recomputed_lineage:
        raise ValueError("M073 model-free lineage result differs from recomputation")
    if controls != recomputed_controls:
        raise ValueError("M073 holdout controls differ from recomputation")
    if lineage.get("teacher_calls") != 0:
        raise ValueError("M073 holdout execution called the external teacher")
    if lineage.get("holdouts_passed") != 12 or lineage.get("case_failures") != 0:
        raise ValueError("M073 model-free holdout result drifted")
    if controls.get("no_capsule_holdouts_passed") != 0:
        raise ValueError("M073 no-capsule control unexpectedly passes")
    if controls.get("memorizer_holdouts_passed") != 0:
        raise ValueError("M073 memorizer control unexpectedly passes")

    recomputed_result = result_assembler.assemble()
    if result != recomputed_result:
        raise ValueError("M073 preserved result differs from its precommitted assembler")
    if result.get("status") != "passed_preregistered_threshold":
        raise ValueError("M073 result status drifted")
    if result.get("claim_passed") is not True or not all(result.get("checks", {}).values()):
        raise ValueError("M073 preregistered conjunction no longer passes")
    if result.get("result_sha256") != EXPECTED_RESULT_SHA256:
        raise ValueError("M073 result digest field drifted")
    if _result_digest(result) != EXPECTED_RESULT_SHA256:
        raise ValueError("M073 preserved result has semantic drift")
    attribution = result.get("attribution")
    if not isinstance(attribution, dict):
        raise ValueError("M073 attribution record is malformed")
    for field in (
        "agi_claim", "general_software_engineering_claim", "genesis_gate_2_or_3_completed",
        "safe_deployment_claim",
    ):
        if attribution.get(field) is not False:
            raise ValueError(f"M073 improperly widens attribution field {field}")

    return {
        "status": result["status"],
        "claim_passed": True,
        "teacher_valid_repairs": 4,
        "holdouts_passed": 12,
        "holdouts_total": 12,
        "holdout_case_failures": 0,
        "holdout_model_calls": 0,
        "no_capsule_holdouts_passed": 0,
        "memorizer_holdouts_passed": 0,
        "capsule_sha256": EXPECTED_CAPSULE_SHA256,
        "result_sha256": EXPECTED_RESULT_SHA256,
    }


def main() -> int:
    print(json.dumps(verify_result(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
