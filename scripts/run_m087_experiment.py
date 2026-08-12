"""Run M087 once, in the frozen order, and write the preserved result.

The chronology is enforced rather than described: the adopted policy is digested and recorded
before `--salt` is consumed, and the qualification cases are drawn from that salt afterwards. A
run that reached the salt first would produce a different recorded order and fail P10.

No model is called and no network is opened. Every decision in the scientific path is made by the
frozen interpreter over the lineage's own serialized policy.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m087_evidence import digest_of, leak_problems  # noqa: E402
from metamorphosis.m087_families import (  # noqa: E402
    QUALIFICATION_POOL,
    family,
    materialize_qualification,
    qualified_family,
)
from metamorphosis.m087_lineage import (  # noqa: E402
    ARMS,
    CONDITIONS,
    DEVELOPMENT_FAMILY,
    QUALIFICATION_FAMILIES,
    RESULT_SCHEMA,
    evaluate,
    meta_search,
    rollback_proof,
    run_arm,
)
from metamorphosis.m087_selection_policy import m0_policy  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salt", required=True, help="qualification salt, released after adoption")
    parser.add_argument("--protocol", default="experiments/M087/PROTOCOL.json")
    parser.add_argument("--output", default="experiments/M087/RESULT.json")
    arguments = parser.parse_args()

    protocol_path = ROOT / arguments.protocol
    protocol_bytes = protocol_path.read_bytes()
    protocol = json.loads(protocol_bytes.decode("utf-8"))
    chronology: list[dict[str, object]] = []

    def mark(step: str, **payload: object) -> None:
        chronology.append({"step": step, "index": len(chronology), **payload})

    mark("T0_protocol_frozen", protocol_digest=digest_of(protocol))
    mark("T1_m0_policy_recorded", policy_digest=m0_policy().digest())

    development_family = family(DEVELOPMENT_FAMILY)
    mark(
        "T2_development_materialized",
        family=DEVELOPMENT_FAMILY,
        public_digest=digest_of([case.to_dict() for case in development_family.public_cases]),
    )

    development = meta_search(development_family)
    mark("T3_limitation_observed", **{
        "equivalent_candidates": development.limitation["observationally_equivalent_count"],
        "m0_adopted": development.limitation["m0_adopted_label"],
        "m0_correct": development.limitation["m0_correct"],
    })
    mark("T4_meta_transformations_rejected", rejected=len(development.rejected))
    if development.adopted_policy is None:
        mark("T5_no_meta_transformation_validated")
    else:
        mark("T5_disposable_descendant_validated", steps=len(development.adopted_steps or ()))
    adopted_digest = (
        development.adopted_policy.digest() if development.adopted_policy else None
    )
    mark("T6_policy_adopted_and_serialized", policy_digest=adopted_digest)

    # Only now is the salt consumed. Everything above is recorded and digested first.
    mark("T7_qualification_materialized", salt_digest=digest_of(arguments.salt), draws={
        family_id: [case.to_dict() for case in materialize_qualification(family_id, arguments.salt)]
        for family_id in QUALIFICATION_FAMILIES
    })

    arms: dict[str, dict[str, object]] = {}
    for arm in ARMS:
        arms[arm] = run_arm(arm, development, arguments.salt)
    mark("T8_arms_executed", arms=list(ARMS))
    mark("T9_hidden_evaluation_sealed")

    rollback = rollback_proof(
        development.adopted_policy if development.adopted_policy else m0_policy()
    )
    mark("T10_rollback_proved", byte_identical=rollback["byte_identical_restore"])

    leak: list[str] = []
    for arm, record in arms.items():
        for family_id, log in zip(QUALIFICATION_FAMILIES, record["acquisition_logs"]):
            fam = qualified_family(family_id, arguments.salt)
            leak += [
                f"{arm}/{family_id}: {problem}"
                for problem in leak_problems(
                    log, fam.spaces, [case.request for case in fam.hidden_cases],
                )
            ]
    mark("T11_leak_checked", findings=len(leak))

    ordered = [entry["step"] for entry in chronology]
    expected_prefix = [
        "T0_protocol_frozen", "T1_m0_policy_recorded", "T2_development_materialized",
        "T3_limitation_observed", "T4_meta_transformations_rejected",
    ]
    chronology_record = {
        "steps": chronology,
        "order": ordered,
        # The property P10 checks: adoption is recorded strictly before the salt is consumed.
        "adoption_precedes_qualification": (
            ordered.index("T6_policy_adopted_and_serialized")
            < ordered.index("T7_qualification_materialized")
        ),
        "ordered": ordered[:5] == expected_prefix and (
            ordered.index("T6_policy_adopted_and_serialized")
            < ordered.index("T7_qualification_materialized")
            < ordered.index("T8_arms_executed")
            < ordered.index("T9_hidden_evaluation_sealed")
        ),
    }

    verdict = evaluate(development.to_dict(), arms, rollback, leak, chronology_record)
    result = {
        "schema": RESULT_SCHEMA,
        "milestone": "M087",
        "hypothesis": "H33",
        "protocol_digest": digest_of(protocol),
        "protocol_raw_sha256": __import__("hashlib").sha256(protocol_bytes).hexdigest(),
        "salt_digest": digest_of(arguments.salt),
        "development": development.to_dict(),
        "arms": arms,
        "rollback": rollback,
        "leak_findings": leak,
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
    destination.write_bytes(
        json.dumps(result, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    )
    print(json.dumps(verdict, indent=2, sort_keys=True))
    print(f"\nwritten to {arguments.output}")
    print(f"result digest {result['result_digest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
