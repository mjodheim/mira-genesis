"""Run the five frozen G2 arms once against the bound suite and preserve the first result.

The script refuses to overwrite an existing result. The frozen protocol forbids a retry of the first
materialized suite, so a second observation would have to be a separately named experiment.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.g2_multimodal_grounding import (  # noqa: E402
    ARMS,
    BLIND_GUESS_MAX_PER_FAMILY,
    BLIND_GUESS_MAX_TOTAL,
    DECISIVE_CHANNEL,
    EPISODES_PER_FAMILY,
    FAMILIES,
    evaluate_dissociation,
    materialize_suite,
    run_arm,
)

PROTOCOL_PATH = ROOT / "experiments/G2_GROUNDING/PROTOCOL.json"
COMMITMENT_PATH = ROOT / "experiments/G2_GROUNDING/EPISODE_COMMITMENT.json"
RESULT_PATH = ROOT / "experiments/G2_GROUNDING/RESULT.json"


def main() -> int:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    commitment = json.loads(COMMITMENT_PATH.read_text(encoding="utf-8"))
    salt = bytes.fromhex(protocol["episode_generation"]["salt_hex"])

    suite = materialize_suite(salt)
    replay = [episode.commitment() for episode in suite]
    bound = [record["commitment"] for record in commitment["episodes"]]
    if replay != bound:
        raise SystemExit("the replayed suite does not match the bound episode commitment")

    arms = {arm: run_arm(suite, arm, salt) for arm in ARMS}
    verdict = evaluate_dissociation(arms)
    threshold = protocol["positive_threshold"]

    payload = {
        "schema": "g2-multimodal-grounding-result-v1",
        "protocol_commitment": hashlib.sha256(
            PROTOCOL_PATH.read_bytes(),
        ).hexdigest(),
        "suite_commitment": commitment["suite_commitment"],
        "attempt": 1,
        "retried": False,
        "external_model_called": False,
        "network_used": False,
        "third_party_attestation_present": False,
        "python": platform.python_version(),
        "episode_count": len(suite),
        "evaluation_count": len(suite) * len(ARMS),
        "arms": arms,
        "decisive_channel": DECISIVE_CHANNEL,
        "dissociation_positive": verdict.positive,
        "dissociation_reasons": list(verdict.reasons),
        "threshold_applied": {
            "full_arm_exact_successes_required": threshold[
                "full_arm_exact_successes_required"
            ],
            "ablated_dependent_family_max_successes": threshold[
                "ablated_dependent_family_max_successes"
            ],
            "blind_guess_max_total_successes": BLIND_GUESS_MAX_TOTAL,
            "blind_guess_max_per_family_successes": BLIND_GUESS_MAX_PER_FAMILY,
        },
        "claim_boundary": protocol["claim_boundary"],
    }
    payload["result_sha256"] = hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()

    if RESULT_PATH.exists():
        existing = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
        if existing.get("result_sha256") != payload["result_sha256"]:
            raise SystemExit(
                "refusing to overwrite the preserved first result; the frozen protocol "
                "forbids retrying the first materialized suite"
            )
        print("result already preserved and identical:", payload["result_sha256"])
        return 0

    RESULT_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )

    print(f"dissociation positive: {verdict.positive}")
    for arm in ARMS:
        record = arms[arm]
        per_family = record["successes_per_family"]
        cells = "  ".join(
            f"{family}={per_family[family]:2}/{EPISODES_PER_FAMILY}" for family in FAMILIES
        )
        print(f"  {arm:18} total={record['successes_total']:2}/36  {cells}")
    print("result sha256:", payload["result_sha256"])
    return 0 if verdict.positive else 1


if __name__ == "__main__":
    raise SystemExit(main())
