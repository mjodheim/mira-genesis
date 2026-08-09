"""Verify the pre-policy M069 terminal-task freeze and live evaluator attestation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Mapping

import metamorphosis.m069_terminal_task_bank as _task_bank


ROOT = Path(__file__).resolve().parents[1]
FROZEN_PATH = ROOT / "experiments" / "M069" / "FROZEN_PROTOCOL.json"
RUNTIME_PATH = Path(_task_bank.__file__).resolve()
RESPONSE_SCHEMA = "m069-terminal-task-response-v1"


class M069FreezeError(ValueError):
    """Raised when the M069 evaluator differs from its pre-policy freeze."""


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _lf_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _protocol_digest(protocol: object) -> str:
    return hashlib.sha256(b"m069-protocol-v1\0" + _canonical_json(protocol)).hexdigest()


def _attest(runtime_path: Path) -> Mapping[str, object]:
    completed = subprocess.run(
        [sys.executable, str(runtime_path), "attest"], capture_output=True,
        timeout=30, check=False,
    )
    try:
        response = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise M069FreezeError("M069 evaluator returned malformed attestation") from exc
    if completed.returncode != 0 or not isinstance(response, Mapping) or response.get("fatal_error"):
        raise M069FreezeError(f"M069 evaluator failed: {response.get('fatal_error')}")
    if response.get("schema") != RESPONSE_SCHEMA or response.get("mode") != "attest":
        raise M069FreezeError("M069 evaluator response identity mismatch")
    result = response.get("result")
    if not isinstance(result, Mapping):
        raise M069FreezeError("M069 evaluator attestation is not an object")
    return result


def validate_frozen_protocol(path: Path = FROZEN_PATH) -> Mapping[str, object]:
    try:
        frozen = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise M069FreezeError("M069 frozen protocol is absent or malformed") from exc
    if frozen.get("schema") != "m069-frozen-protocol/1":
        raise M069FreezeError("M069 frozen protocol schema mismatch")
    protocol = frozen.get("protocol")
    if not isinstance(protocol, Mapping):
        raise M069FreezeError("M069 executable protocol is absent")
    if frozen.get("protocol_sha256") != _protocol_digest(protocol):
        raise M069FreezeError("M069 executable protocol digest mismatch")
    if frozen.get("target_runtime_lf_sha256") != _lf_sha256(RUNTIME_PATH):
        raise M069FreezeError("M069 evaluator runtime drifted after freeze")
    attestation = _attest(RUNTIME_PATH)
    if frozen.get("task_bank_attestation") != attestation:
        raise M069FreezeError("M069 live task-bank attestation differs from the freeze")
    if protocol.get("task_bank_frozen_before_policy") is not True:
        raise M069FreezeError("M069 freeze order is not declared")
    if protocol.get("real_filesystem_process_body") is not True:
        raise M069FreezeError("M069 real terminal boundary is not declared")
    false_fields = (
        "policy_has_hidden_input", "evaluator_source_available_to_policy",
        "operating_system_security_sandbox_claimed", "external_task_authorship_claimed",
        "open_ended_code_generation_claimed", "network_authority", "repository_authority",
        "credential_authority", "deployment_authority", "permission_change_authority",
        "physical_actuation_authority", "general_intelligence_claimed", "canonical",
    )
    if any(protocol.get(field) is not False for field in false_fields):
        raise M069FreezeError("M069 claim or authority boundary widened")
    if len(protocol.get("candidate_replacements", ())) != 11:
        raise M069FreezeError("M069 frozen repair language drifted")
    return frozen


def main() -> int:
    try:
        frozen = validate_frozen_protocol()
    except M069FreezeError as error:
        print(f"M069 frozen protocol failure: {error}")
        return 1
    print(json.dumps({
        "status": "m069_task_bank_frozen",
        "protocol_sha256": frozen["protocol_sha256"],
        "task_bank_commitment": frozen["task_bank_attestation"]["task_bank_commitment"],
        "target_runtime_lf_sha256": frozen["target_runtime_lf_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
