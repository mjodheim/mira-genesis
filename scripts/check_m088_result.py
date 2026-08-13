"""Decisive checker for M088: reconstruct the verdict from the preserved artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m088_experiment import constructive_image, m0_constructor  # noqa: E402
from metamorphosis.m088_lineage import (  # noqa: E402
    CEILING_ARMS,
    CONDITIONS,
    DEVELOPMENT_WORLD,
    QUALIFICATION_WORLDS,
    evaluate,
    hidden_outside_constructive_image,
)
from metamorphosis.m088_worlds import qualified_world  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))

RESULT = ROOT / "experiments/M088/RESULT.json"
PROTOCOL = ROOT / "experiments/M088/PROTOCOL.json"
CLAIM = ROOT / "experiments/M088/REGISTER_CLAIM.json"
SALT = "m088-qualification-salt-2026-08-13"
QUALIFICATION = ROOT / "experiments/M088/QUALIFICATION.json"


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-result", action="store_true")
    arguments = parser.parse_args()
    if not RESULT.exists():
        print("no M088 result is present", file=sys.stderr)
        return 2 if arguments.require_result else 0

    result = json.loads(RESULT.read_text(encoding="utf-8"))
    problems: list[str] = []

    if result["protocol_raw_sha256"] != hashlib.sha256(PROTOCOL.read_bytes()).hexdigest():
        problems.append("the result does not bind the committed protocol blob")
    if result["attempt"] != 1 or result["retry_used"] is not False:
        problems.append("the result is not a single unretried attempt")
    if result["model_calls"] != 0 or result["network_calls"] != 0:
        problems.append("the scientific run recorded a model or network call")
    if set(result["conditions_declared"]) != set(CONDITIONS):
        problems.append("the declared conditions differ from the frozen list")
    if set(result["evaluation"]["conditions"]) != set(CONDITIONS):
        problems.append("the verdict does not compute every frozen condition")

    order = result["chronology"]["order"]
    if order.index("T8_constructor_serialized") >= order.index("T9_qualification_materialized"):
        problems.append("qualification was materialized before the constructor was digested")
    if result["chronology"]["ordered"] is not True:
        problems.append("the recorded chronology is out of order")

    # The inexpressibility claim, re-derived rather than trusted.
    development = result["development"]
    limitation = development["limitation"]
    from metamorphosis.m088_worlds import world as _world

    item = _world(DEVELOPMENT_WORLD)
    image = constructive_image(m0_constructor(), item.action_names, item.observer_names)
    if {tuple(program) for program in limitation["constructive_image"]} != image:
        problems.append("the recorded prior constructive image does not reproduce")
    if limitation["discriminating_programs_in_prior_image"]:
        problems.append("the prior image contained a discriminating program after all")
    if limitation["resolved_by_prior_constructor"] is not False:
        problems.append("the prior constructor resolved the development world")

    artifact = json.loads(QUALIFICATION.read_text(encoding="utf-8"))
    if artifact != result["qualification_artifact"]:
        problems.append("the committed qualification artifact differs from the recorded one")
    if artifact["adopted_constructor_digest"] != development["adopted_constructor_digest"]:
        problems.append("the qualification was drawn for a different constructor")
    if artifact["materialized_by"] != "separate process":
        problems.append("the qualification was not materialized by a separate process")
    # The pool must not be reachable from anything the lineage imports.
    import metamorphosis.m088_worlds as _worlds

    if hasattr(_worlds, "QUALIFICATION_POOL"):
        problems.append("the qualification pool is importable by the lineage")
    drawn = {key: [tuple(item) for item in value] for key, value in artifact["programs"].items()}

    evolvable = result["arms"]["evolvable_experiment_constructor"]
    for record in evolvable["encounters"]:
        world_item = qualified_world(record["world_id"], drawn[record["world_id"]])
        prior = constructive_image(
            m0_constructor(), world_item.action_names, world_item.observer_names,
        )
        for steps in record["experiments_outside_prior_image"]:
            if tuple(steps) in prior:
                problems.append(f"{record['world_id']}: a claimed novel experiment is in M0's image")
        for acquisition in record["acquisitions"]:
            if not acquisition["eliminated"]:
                problems.append(f"{record['world_id']}: an acquisition eliminated nothing")
            observed = world_item.execute(tuple(acquisition["program"]["steps"]))
            if observed != acquisition["observation"]:
                problems.append(f"{record['world_id']}: a recorded observation does not reproduce")

    for world_id in QUALIFICATION_WORLDS:
        proof = hidden_outside_constructive_image(
            qualified_world(world_id, drawn[world_id]),
            __import__("metamorphosis.m088_experiment", fromlist=["ExperimentConstructor"])
            .ExperimentConstructor.from_dict(development["adopted_constructor"]),
        )
        if not proof["all_hidden_outside_image"]:
            problems.append(f"{world_id}: a hidden program is inside the constructive image")

    for arm in CEILING_ARMS:
        if not result["arms"][arm]["is_ceiling"]:
            problems.append(f"{arm} is not flagged as a ceiling")
        if arm in json.dumps(result["evaluation"]):
            problems.append(f"{arm} appears in the verdict")

    budgeted = result["arms"]["more_budget_same_experiment_space"]
    fixed = result["arms"]["fixed_experiment_constructor"]
    if budgeted["total_programs_executed"] <= fixed["total_programs_executed"]:
        problems.append("the tenfold arm did not execute more programs than the fixed arm")
    if budgeted["experiments_outside_prior_image"]:
        problems.append("the tenfold arm gained expressiveness it should not have")
    for record in budgeted["encounters"]:
        if record["repetitions_recorded"] != 10:
            problems.append(f"{record['world_id']}: the tenfold arm preserved "
                            f"{record['repetitions_recorded']} repetition logs, not 10")
    if not result["rollback"]["corrupted_state_was_the_restored_state"]:
        problems.append("rollback corrupted a copy rather than the state it restored")
    if not result["rollback"]["fault_actually_changed_behaviour"]:
        problems.append("the injected fault did not change the constructor's behaviour")

    if evaluate(development, result["arms"], result["rollback"]) != result["evaluation"]:
        problems.append("the recorded verdict does not reproduce from the preserved arms")
    body = {key: value for key, value in result.items() if key != "result_digest"}
    if _digest(body) != result["result_digest"]:
        problems.append("the result digest does not cover the preserved result")

    claim = json.loads(CLAIM.read_text(encoding="utf-8"))
    if claim["result_digest"] != result["result_digest"]:
        problems.append("the register claim and the result disagree on the digest")
    if claim["verdict"] != result["evaluation"]["verdict"]:
        problems.append("the register claim and the result disagree on the verdict")
    if claim["gate_advanced"] is not False:
        problems.append("a generality gate was recorded as advanced")

    for problem in problems:
        print(f"blocking: {problem}", file=sys.stderr)
    if problems:
        return 2
    print(f"M088 result verified: {result['evaluation']['verdict']}, {len(CONDITIONS)} conditions, "
          f"digest {result['result_digest'][:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
