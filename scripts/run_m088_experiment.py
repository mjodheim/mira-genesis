"""Run M088 once, in the frozen order, and write the preserved result.

The chronology is enforced: the adopted constructor is digested and recorded before `--salt` is
consumed, and the qualification programs are drawn from that salt afterwards. No model is called
and no network is opened.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m088_experiment import m0_constructor  # noqa: E402
from metamorphosis.m088_lineage import (  # noqa: E402
    ARMS,
    CONDITIONS,
    DEVELOPMENT_WORLD,
    QUALIFICATION_WORLDS,
    RESULT_SCHEMA,
    evaluate,
    hidden_outside_constructive_image,
    meta_search,
    rollback_proof,
    run_arm,
)
from metamorphosis.m088_worlds import qualified_world, world  # noqa: E402


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salt", required=True)
    parser.add_argument("--protocol", default="experiments/M088/PROTOCOL.json")
    parser.add_argument("--output", default="experiments/M088/RESULT.json")
    arguments = parser.parse_args()

    protocol_bytes = (ROOT / arguments.protocol).read_bytes()
    protocol = json.loads(protocol_bytes.decode("utf-8"))
    chronology: list[dict[str, object]] = []

    def mark(step: str, **payload: object) -> None:
        chronology.append({"step": step, "index": len(chronology), **payload})

    mark("T0_protocol_frozen", protocol_digest=_digest(protocol))
    mark("T1_m0_constructor_committed", constructor_digest=m0_constructor().digest())

    development_world = world(DEVELOPMENT_WORLD)
    mark("T2_development_world_materialized", world=DEVELOPMENT_WORLD)

    development = meta_search(development_world)
    limitation = development.limitation
    mark(
        "T4_prior_image_enumerated_and_exhausted",
        image_size=limitation["constructive_image_size"],
        discriminating_in_image=len(limitation["discriminating_programs_in_prior_image"]),
        resolved=limitation["resolved_by_prior_constructor"],
    )
    mark("T5_meta_candidates_rejected", rejected=len(development.rejected))
    adopted_digest = (
        development.adopted_constructor.digest() if development.adopted_constructor else None
    )
    mark("T7_constructor_adopted", constructor_digest=adopted_digest)
    mark("T8_constructor_serialized", constructor_digest=adopted_digest)

    # Only now is the salt consumed, and it is consumed by a SEPARATE PROCESS that owns the pool.
    # This process has never held a qualifying program, in memory or on disk.
    import subprocess

    artifact_path = ROOT / "experiments/M088/QUALIFICATION.json"
    subprocess.run(
        [
            sys.executable, str(ROOT / "scripts/materialize_m088_qualification.py"),
            "--salt", arguments.salt,
            "--adopted-constructor-digest", str(adopted_digest),
            "--worlds", ",".join(QUALIFICATION_WORLDS),
            "--output", str(artifact_path),
        ],
        capture_output=True, text=True, check=True,
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    if artifact["adopted_constructor_digest"] != adopted_digest:
        raise SystemExit("the qualification artifact was drawn for a different constructor")
    drawn = {key: [tuple(item) for item in value] for key, value in artifact["programs"].items()}
    mark(
        "T9_qualification_materialized",
        salt_digest=_digest(arguments.salt),
        materialized_by="separate process",
        artifact_digest=artifact["artifact_digest"],
        pool_present_in_this_process=False,
        draws={key: [list(item) for item in value] for key, value in drawn.items()},
    )

    arms = {arm: run_arm(arm, development, drawn) for arm in ARMS}
    mark("T11_arms_executed", arms=list(ARMS))
    mark("T14_hidden_evaluation_complete")

    rollback = rollback_proof(
        development.adopted_constructor if development.adopted_constructor else m0_constructor()
    )
    mark("T15_rollback_proved", byte_identical=rollback["byte_identical_restore"])

    no_leak = [
        hidden_outside_constructive_image(
            qualified_world(world_id, drawn[world_id]),
            development.adopted_constructor or m0_constructor(),
        )
        for world_id in QUALIFICATION_WORLDS
    ]
    leak_findings = [
        f"{item['world_id']}: hidden program inside the constructive image"
        for item in no_leak if not item["all_hidden_outside_image"]
    ]

    order = [entry["step"] for entry in chronology]
    chronology_record = {
        "steps": chronology,
        "order": order,
        "adoption_precedes_qualification": (
            order.index("T8_constructor_serialized") < order.index("T9_qualification_materialized")
        ),
        "ordered": (
            order.index("T1_m0_constructor_committed")
            < order.index("T4_prior_image_enumerated_and_exhausted")
            < order.index("T7_constructor_adopted")
            < order.index("T9_qualification_materialized")
            < order.index("T11_arms_executed")
            < order.index("T14_hidden_evaluation_complete")
        ),
    }

    verdict = evaluate(development.to_dict(), arms, rollback)
    result = {
        "schema": RESULT_SCHEMA,
        "milestone": "M088",
        "hypothesis": "H34",
        "protocol_digest": _digest(protocol),
        "protocol_raw_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
        "salt_digest": _digest(arguments.salt),
        "qualification_artifact": artifact,
        "development": development.to_dict(),
        "arms": arms,
        "rollback": rollback,
        "no_leak": no_leak,
        "leak_findings": leak_findings,
        "chronology": chronology_record,
        "conditions_declared": list(CONDITIONS),
        "evaluation": verdict,
        "model_calls": 0,
        "network_calls": 0,
        "attempt": 1,
        "retry_used": False,
    }
    result["result_digest"] = _digest(
        {key: value for key, value in result.items() if key != "result_digest"}
    )
    destination = ROOT / arguments.output
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(json.dumps(result, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    print(json.dumps(verdict, indent=2, sort_keys=True))
    print(f"\nresult digest {result['result_digest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
