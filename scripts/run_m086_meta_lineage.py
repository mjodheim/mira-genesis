"""Bind the M086 bank and preserve the first result.

Runs the four arms, enumerates the starting mechanism's constructive image for the holdout evidence
so that the control's failure is shown to be structural, and writes both artifacts once.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m086_evolvable_mechanism import (  # noqa: E402
    ARMS,
    GENERATOR_VERSION,
    META_PRIMITIVES,
    candidate_meta_transformations,
    m0_mechanism,
)
from metamorphosis.m086_meta_lineage import (  # noqa: E402
    DEVELOPMENT_PUBLIC,
    HOLDOUT_HIDDEN,
    HOLDOUT_PUBLIC,
    bank_commitment,
    enumerate_m0_image_on_holdout,
    evaluate,
    run_arm,
    starting_body,
)

BASE = ROOT / "experiments/M086"
PROTOCOL_PATH = BASE / "PROTOCOL.json"
BANK_PATH = BASE / "BANK_COMMITMENT.json"
RESULT_PATH = BASE / "RESULT.json"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def _write_once(path: Path, payload: dict, digest_key: str) -> None:
    payload[digest_key] = hashlib.sha256(_canonical({
        key: value for key, value in payload.items() if key != digest_key
    })).hexdigest()
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get(digest_key) != payload[digest_key]:
            raise SystemExit(
                f"refusing to overwrite {path.name} with a different {digest_key}; "
                "the frozen protocol forbids replacing a materialized artifact"
            )
        print(f"{path.name} already bound and identical: {payload[digest_key]}")
        return
    path.write_bytes(json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    print(f"bound {path.name}: {payload[digest_key]}")


def main() -> int:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol["episode_generation"]["generator_version"] != GENERATOR_VERSION:
        raise SystemExit("generator version drifted from the frozen protocol")
    if protocol["claim_boundary"]["agi_evidence"] is not False:
        raise SystemExit("the claim boundary was weakened before the run")

    bank_payload = {
        "schema": "m086-bank-commitment-v1",
        "generator_version": GENERATOR_VERSION,
        "starting_body_digest": starting_body().digest(),
        "m0_mechanism_digest": m0_mechanism().digest(),
        "meta_primitives": list(META_PRIMITIVES),
        "meta_transformation_search_space": [
            list(item) for item in candidate_meta_transformations()
        ],
        "development_public": [case.to_dict() for case in DEVELOPMENT_PUBLIC],
        "holdout_public": [case.to_dict() for case in HOLDOUT_PUBLIC],
        "holdout_hidden_digest": hashlib.sha256(
            _canonical([case.to_dict() for case in HOLDOUT_HIDDEN]),
        ).hexdigest(),
        "bank_digest": bank_commitment(),
    }
    _write_once(BANK_PATH, bank_payload, "bank_commitment")

    print("enumerating the starting mechanism's image for the holdout ...", flush=True)
    image = enumerate_m0_image_on_holdout()
    print(f"  candidates M0 can emit for the holdout: {image['candidate_count']}")

    arms: dict[str, dict] = {}
    for arm in ARMS:
        print(f"running {arm} ...", flush=True)
        arms[arm] = run_arm(arm).to_dict()

    verdict = evaluate(arms, image)
    result_payload = {
        "schema": "m086-evolvable-improvement-mechanism-result-v1",
        "protocol_commitment": hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest(),
        "bank_commitment": bank_payload["bank_commitment"],
        "attempt": 1,
        "retried": False,
        "external_model_called": False,
        "network_opened": False,
        "python": platform.python_version(),
        "m0_constructive_image_on_holdout": image,
        "arms": arms,
        "verdict": "positive" if verdict.positive else "negative",
        "failed_conditions": list(verdict.reasons),
        "claim_boundary": protocol["claim_boundary"],
    }
    _write_once(RESULT_PATH, result_payload, "result_sha256")

    print(f"\nverdict: {result_payload['verdict']}")
    for arm in ARMS:
        record = arms[arm]
        print(
            f"  {arm:26} meta_adopted={record['meta_transformations_adopted']}"
            f" dev={record['development_solved']}"
            f" holdout_hidden={record['holdout_hidden_solved']}"
            f" patch={record['holdout_adopted_label']}"
        )
    for reason in verdict.reasons:
        print(f"  FAILED: {reason}")
    return 0 if verdict.positive else 1


if __name__ == "__main__":
    raise SystemExit(main())
