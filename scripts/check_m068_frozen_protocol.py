"""Verify the pre-learner M068 target-bank freeze and live opaque attestation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
FROZEN_PATH = ROOT / "experiments" / "M068" / "FROZEN_PROTOCOL.json"
RUNTIME_PATH = ROOT / "metamorphosis" / "m068_external_body_bank.mjs"
RESPONSE_SCHEMA = "m068-external-body-response-v1"


class M068FreezeError(ValueError):
    """Raised when the committed M068 target bank differs from its pre-learner freeze."""


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _lf_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _protocol_digest(protocol: object) -> str:
    return hashlib.sha256(b"m068-protocol-v1\0" + _canonical_json(protocol)).hexdigest()


def _attest(runtime_path: Path) -> Mapping[str, object]:
    completed = subprocess.run(
        ["node", str(runtime_path), "attest"], input=b"{}", capture_output=True,
        timeout=30, check=False,
    )
    try:
        response = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise M068FreezeError("M068 target runtime returned malformed attestation") from exc
    if completed.returncode != 0 or not isinstance(response, Mapping) or response.get("fatal_error"):
        raise M068FreezeError(f"M068 target runtime failed: {response.get('fatal_error')}")
    if response.get("schema") != RESPONSE_SCHEMA or response.get("mode") != "attest":
        raise M068FreezeError("M068 target runtime identity mismatch")
    result = response.get("result")
    if not isinstance(result, Mapping):
        raise M068FreezeError("M068 target attestation is not an object")
    return result


def validate_frozen_protocol(path: Path = FROZEN_PATH) -> Mapping[str, object]:
    try:
        frozen = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise M068FreezeError("M068 frozen protocol is absent or malformed") from exc
    if frozen.get("schema") != "m068-frozen-protocol/1":
        raise M068FreezeError("M068 frozen protocol schema mismatch")
    protocol = frozen.get("protocol")
    if not isinstance(protocol, Mapping):
        raise M068FreezeError("M068 executable protocol is absent")
    if frozen.get("protocol_sha256") != _protocol_digest(protocol):
        raise M068FreezeError("M068 executable protocol digest mismatch")
    if frozen.get("target_runtime_lf_sha256") != _lf_sha256(RUNTIME_PATH):
        raise M068FreezeError("M068 target runtime drifted after freeze")
    attestation = _attest(RUNTIME_PATH)
    if frozen.get("body_bank_attestation") != attestation:
        raise M068FreezeError("M068 live body-bank attestation differs from the freeze")
    if any(
        protocol.get(field) is not False
        for field in (
            "command_words_disclosed", "semantic_assignments_disclosed",
            "descriptor_grammar_disclosed", "complete_target_adapter_disclosed",
            "external_target_authorship_claimed", "network_authority", "repository_authority",
            "credential_authority", "deployment_authority", "canonical",
        )
    ):
        raise M068FreezeError("M068 claim or authority boundary widened")
    if protocol.get("target_bank_frozen_before_discovery_engine") is not True:
        raise M068FreezeError("M068 freeze order is not declared")
    return frozen


def main() -> int:
    try:
        frozen = validate_frozen_protocol()
    except M068FreezeError as error:
        print(f"M068 frozen protocol failure: {error}")
        return 1
    print(json.dumps({
        "status": "m068_target_bank_frozen",
        "protocol_sha256": frozen["protocol_sha256"],
        "body_bank_commitment": frozen["body_bank_attestation"]["body_bank_commitment"],
        "target_runtime_lf_sha256": frozen["target_runtime_lf_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
