"""Independently recompute the preserved G2 grounding result from its frozen inputs.

The checker rebuilds the episode suite from the committed salt, re-derives every arm, re-verifies the
matched-ablation invariants and the double dissociation, and recomputes the preserved digest. It
fails closed on any drift.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m076_multimodal_grounding import (  # noqa: E402
    ARMS,
    BLIND_GUESS_MAX_PER_FAMILY,
    BLIND_GUESS_MAX_TOTAL,
    DECISIVE_CHANNEL,
    EPISODES_PER_FAMILY,
    FAMILIES,
    MARKER_EFFECTOR,
    MARKER_TARGET,
    _locate_uniform_cell,
    ablated_raster,
    evaluate_dissociation,
    materialize_suite,
    observe,
    run_arm,
)

BASE = ROOT / "experiments/M076"
PROTOCOL_PATH = BASE / "PROTOCOL.json"
COMMITMENT_PATH = BASE / "EPISODE_COMMITMENT.json"
RESULT_PATH = BASE / "RESULT.json"


def _fail(failures: list[str], condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    commitment = json.loads(COMMITMENT_PATH.read_text(encoding="utf-8"))
    preserved = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    salt = bytes.fromhex(protocol["episode_generation"]["salt_hex"])

    suite = materialize_suite(salt)
    _fail(
        failures,
        [episode.commitment() for episode in suite]
        == [record["commitment"] for record in commitment["episodes"]],
        "replayed suite does not match the bound episode commitment",
    )
    _fail(
        failures,
        len(suite) == protocol["episode_generation"]["episode_count"],
        "episode count drifted from the frozen protocol",
    )

    # The pixel family must be the only family carrying markers, otherwise a dial family could be
    # solved from the raster and the dissociation would be an artefact.
    for episode in suite:
        carries = _locate_uniform_cell(episode.raster, MARKER_TARGET) is not None
        _fail(
            failures,
            carries == (episode.family == "pixel_target"),
            f"marker presence leaked into {episode.family}",
        )

    ablated = ablated_raster(salt)
    for triple, label in ((MARKER_TARGET, "target"), (MARKER_EFFECTOR, "effector")):
        _fail(
            failures,
            _locate_uniform_cell(ablated, triple) is None,
            f"pixel ablation leaked the {label} marker",
        )

    for arm in (a for a in ARMS if a != "blind_guess"):
        for episode in suite:
            observation = observe(episode, arm, salt)
            _fail(
                failures,
                len(observation.pixels) == len(episode.raster)
                and list(observation.structured) == list(episode.structured)
                and len(observation.language.split()) == len(episode.instruction.split()),
                f"{arm} broke a matched-ablation invariant",
            )

    arms = {arm: run_arm(suite, arm, salt) for arm in ARMS}
    for arm in ARMS:
        _fail(
            failures,
            preserved["arms"][arm]["successes_per_family"]
            == arms[arm]["successes_per_family"],
            f"{arm} per-family scores do not reproduce",
        )

    full = arms["full"]["successes_per_family"]
    for family in FAMILIES:
        _fail(
            failures,
            full[family] == EPISODES_PER_FAMILY,
            f"full arm did not reach exact success on {family}",
        )

    ablation_for = {
        "pixels": "pixel_ablated",
        "structured": "structure_ablated",
        "language": "language_ablated",
    }
    for family in FAMILIES:
        arm = ablation_for[DECISIVE_CHANNEL[family]]
        scores = arms[arm]["successes_per_family"]
        _fail(failures, scores[family] == 0, f"{arm} preserved its dependent family {family}")
        for other in FAMILIES:
            if other != family:
                _fail(
                    failures,
                    scores[other] == full[other],
                    f"{arm} changed non-dependent family {other}",
                )

    blind = arms["blind_guess"]
    _fail(
        failures,
        blind["successes_total"] <= BLIND_GUESS_MAX_TOTAL,
        "blind floor exceeded its amended total bound",
    )
    for family in FAMILIES:
        _fail(
            failures,
            blind["successes_per_family"][family] <= BLIND_GUESS_MAX_PER_FAMILY,
            f"blind floor exceeded its per-family bound on {family}",
        )

    for amendment in protocol.get("amendments", []):
        _fail(
            failures,
            amendment["applied_before_episode_materialization"] is True
            and amendment["applied_before_any_recorded_result"] is True,
            f"amendment {amendment.get('id')} claims a post-materialization change",
        )

    recomputed = dict(preserved)
    recomputed.pop("result_sha256", None)
    digest = hashlib.sha256(json.dumps(
        recomputed, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()
    _fail(
        failures,
        digest == preserved["result_sha256"],
        "preserved result digest does not recompute",
    )

    _fail(failures, preserved["attempt"] == 1, "preserved result is not the first attempt")
    _fail(failures, preserved["retried"] is False, "preserved result records a retry")
    _fail(
        failures,
        preserved["external_model_called"] is False,
        "an external model was recorded for this endogenous result",
    )
    boundary = preserved["claim_boundary"]
    for key in ("agi_evidence", "closes_generality_gate_g2", "genesis_gate_2_evidence"):
        _fail(failures, boundary[key] is False, f"claim boundary weakened on {key}")

    verdict = evaluate_dissociation(arms)
    _fail(failures, verdict.positive, f"dissociation not positive: {verdict.reasons}")

    print(json.dumps({
        "schema": "m076-grounding-check-v1",
        "suite_commitment": commitment["suite_commitment"],
        "result_sha256": preserved["result_sha256"],
        "arms": {arm: arms[arm]["successes_per_family"] for arm in ARMS},
        "dissociation_positive": verdict.positive,
        "failures": failures,
        "ok": not failures,
    }, indent=2, sort_keys=True))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
