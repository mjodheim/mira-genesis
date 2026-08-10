"""Verify the immutable pre-execution M074 scientific protocol."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m074_scientific_runner import (  # noqa: E402
    ScientificRunnerError, protocol_commitment, validate_protocol,
)


PROTOCOL_PATH = ROOT / "experiments" / "M074" / "SCIENTIFIC_PROTOCOL.json"
PROTOCOL_RAW_SHA256 = "5a4e12a9d6cd188723f2ae9771293298917a9397f3fa20d8725da713b2261e7c"
APPARATUS_COMMIT = "55a34a90bdc0033c7f1eb811a315516dea14acff"


class ScientificProtocolVerificationError(ValueError):
    """Raised when the frozen M074 contract no longer matches its committed apparatus."""


def _load() -> dict[str, object]:
    try:
        value = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScientificProtocolVerificationError("M074 protocol is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ScientificProtocolVerificationError("M074 protocol must be one JSON object")
    return value


def verify(
    protocol_payload: Mapping[str, object] | None = None, *, verify_files: bool = True,
) -> dict[str, object]:
    if protocol_payload is None:
        if hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest() != PROTOCOL_RAW_SHA256:
            raise ScientificProtocolVerificationError("raw M074 protocol bytes drifted")
        protocol = _load()
    else:
        protocol = dict(protocol_payload)
    try:
        order = validate_protocol(protocol, verify_code_files=verify_files)
    except ScientificRunnerError as exc:
        raise ScientificProtocolVerificationError(str(exc)) from exc
    if protocol.get("apparatus_commit") != APPARATUS_COMMIT:
        raise ScientificProtocolVerificationError("M074 apparatus commit identity drifted")
    if protocol.get("protocol_commitment_sha256") != protocol_commitment(protocol):
        raise ScientificProtocolVerificationError("M074 protocol commitment drifted")
    return {
        "schema": "m074-scientific-protocol-verification-v1",
        "verified": True,
        "scientific_result_exists_in_protocol": False,
        "episode_count": len(order),
        "apparatus_commit": APPARATUS_COMMIT,
        "protocol_raw_sha256": PROTOCOL_RAW_SHA256,
        "protocol_commitment_sha256": protocol["protocol_commitment_sha256"],
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
