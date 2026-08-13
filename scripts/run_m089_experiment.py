"""Run M089 once, in the frozen order, and write the preserved result.

The chronology is enforced rather than described: the extended language is digested and serialized
before the salt is consumed, and the qualifying tasks are drawn by a separate process that owns the
pool. No model is called and no network is opened.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m089_lineage import (  # noqa: E402
    ARMS,
    CONDITIONS,
    DEVELOPMENT_TASK,
    RESULT_SCHEMA,
    acquire_primitive,
    evaluate,
    rollback_proof,
    run_arm,
)
from metamorphosis.m089_meta_language import digest_of, l0_language  # noqa: E402
from metamorphosis.m089_substrate import primitive_max_source_fanout  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salt", required=True)
    parser.add_argument("--protocol", default="experiments/M089/PROTOCOL.json")
    parser.add_argument("--output", default="experiments/M089/RESULT.json")
    arguments = parser.parse_args()

    protocol_bytes = (ROOT / arguments.protocol).read_bytes()
    protocol = json.loads(protocol_bytes.decode("utf-8"))
    chronology: list[dict[str, object]] = []

    def mark(step: str, **payload: object) -> None:
        chronology.append({"step": step, "index": len(chronology), **payload})

    mark("T0_protocol_frozen", protocol_digest=digest_of(protocol))
    mark("T2_l0_digest_frozen", l0_digest=l0_language().digest())
    mark("T3_substrate_frozen", substrate=protocol["extension_substrate_S"]["micro_operations"])
    mark("T4_development_materialized", task_id=DEVELOPMENT_TASK.task_id)

    development = acquire_primitive(DEVELOPMENT_TASK)
    proof = development.proof
    mark(
        "T5_l0_proved_insufficient",
        max_sources_reachable=proof["l0_max_sources_reachable"],
        required_sources=proof["task_required_sources"],
        exhaustive_search_found=proof["l0_exhaustive_search_found_program"],
    )
    mark(
        "T6_primitive_candidates_constructed",
        constructed=development.candidates_constructed,
        validated=development.candidates_validated,
    )
    mark("T7_disposable_validation", rejected=len(development.rejected))
    if development.adopted is None:
        mark("T8_no_primitive_adopted")
        raise SystemExit("no primitive was adopted; the result would be negative by P2")
    mark(
        "T8_primitive_selected",
        implementation_digest=development.adopted.implementation_digest,
        semantics_digest=development.adopted.semantics_digest,
        max_source_fanout=primitive_max_source_fanout(development.adopted),
    )

    rollback = rollback_proof(l0_language(), development.l1)
    mark("T10_rollback_before_extension", ok=rollback["before_extension"]["byte_identical_restore"])
    mark("T11_l1_adopted", l1_version=development.l1.version)
    language_digest = development.l1.digest()
    mark("T12_l1_serialized", l1_digest=language_digest)

    # Only now is the salt consumed, by a separate process that owns the qualification pool.
    artifact_path = ROOT / "experiments/M089/QUALIFICATION.json"
    subprocess.run(
        [
            sys.executable, str(ROOT / "scripts/materialize_m089_qualification.py"),
            "--salt", arguments.salt, "--language-digest", language_digest,
            "--output", str(artifact_path),
        ],
        capture_output=True, text=True, check=True,
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    if artifact["extended_language_digest"] != language_digest:
        raise SystemExit("the qualification artifact was drawn against a different language")
    specs = artifact["specifications"]
    hidden = [tuple(item) for item in artifact["hidden_inputs"]]
    mark(
        "T13_qualification_materialized",
        salt_digest=digest_of(arguments.salt),
        materialized_by="separate process",
        artifact_digest=artifact["artifact_digest"],
        pool_present_in_this_process=False,
        task_ids=[str(item["task_id"]) for item in specs],
    )

    arms = {arm: run_arm(arm, development, specs, hidden) for arm in ARMS}
    mark("T14_arms_executed", arms=list(ARMS))
    mark("T15_hidden_evaluation_complete")
    mark("T17_rollback_after_extension", ok=rollback["after_extension"]["byte_identical_restore"])

    order = [entry["step"] for entry in chronology]
    chronology_record = {
        "steps": chronology,
        "order": order,
        "adoption_precedes_qualification": (
            order.index("T12_l1_serialized") < order.index("T13_qualification_materialized")
        ),
        "ordered": (
            order.index("T2_l0_digest_frozen")
            < order.index("T5_l0_proved_insufficient")
            < order.index("T8_primitive_selected")
            < order.index("T12_l1_serialized")
            < order.index("T13_qualification_materialized")
            < order.index("T14_arms_executed")
            < order.index("T15_hidden_evaluation_complete")
        ),
    }

    verdict = evaluate(development.to_dict(), arms, rollback)
    result = {
        "schema": RESULT_SCHEMA,
        "milestone": "M089",
        "hypothesis": "H35",
        "protocol_digest": digest_of(protocol),
        "protocol_raw_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
        "salt_digest": digest_of(arguments.salt),
        "qualification_artifact": artifact,
        "development": development.to_dict(),
        "adopted_primitive_max_source_fanout": primitive_max_source_fanout(development.adopted),
        "arms": arms,
        "rollback": rollback,
        "chronology": chronology_record,
        "conditions_declared": list(CONDITIONS),
        "evaluation": verdict,
        "model_calls": 0,
        "network_calls": 0,
        "attempt": 1,
        "retry_used": False,
    }
    result["result_digest"] = digest_of(
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
