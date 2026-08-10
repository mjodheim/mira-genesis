"""Verify the byte-preserved, non-scientific M075 public model-development protocol."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m075_model_development_runner import validate_protocol  # noqa: E402


PROTOCOL_PATH = ROOT / "experiments" / "M075" / "MODEL_DEVELOPMENT_PROTOCOL.json"
PROTOCOL_RAW_SHA256 = "5861881457b37b21a8417a579286349611ebfad64f3bc2b5fbc18e1efada177d"


class M075ModelDevelopmentProtocolVerificationError(ValueError):
    """Raised when the committed public development protocol no longer verifies."""


def verify() -> dict[str, object]:
    try:
        raw = PROTOCOL_PATH.read_bytes()
        protocol = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise M075ModelDevelopmentProtocolVerificationError(
            "M075 model-development protocol is malformed"
        ) from exc
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_RAW_SHA256:
        raise M075ModelDevelopmentProtocolVerificationError(
            "raw M075 model-development protocol bytes drifted"
        )
    if not isinstance(protocol, dict):
        raise M075ModelDevelopmentProtocolVerificationError(
            "M075 model-development protocol must be one object"
        )
    try:
        order = validate_protocol(protocol)
    except (RuntimeError, ValueError) as exc:
        raise M075ModelDevelopmentProtocolVerificationError(str(exc)) from exc
    return {
        "schema": "m075-public-model-development-protocol-verification-v1",
        "verified": True,
        "scientific_result": False,
        "public_contaminated_development": True,
        "episode_count": len(order),
        "apparatus_commit": protocol["apparatus_commit"],
        "protocol_commitment_sha256": protocol["protocol_commitment_sha256"],
        "protocol_raw_sha256": PROTOCOL_RAW_SHA256,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
