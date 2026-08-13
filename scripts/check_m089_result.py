"""Decisive checker for M089: reconstruct the verdict and every structural claim from artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import replace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m089_lineage import (  # noqa: E402
    CEILING_ARMS,
    EXTENSION_REASON,
    CONDITIONS,
    DEVELOPMENT_TASK,
    evaluate,
    macro_reducible_to_l0,
    prove_l0_insufficient,
    rollback_proof,
    search_transformation,
    task_from_spec,
    validate_primitive,
)
from metamorphosis.m089_meta_language import (  # noqa: E402
    MetaLanguageState,
    PrimitiveContract,
    digest_of,
    enumerate_l0_reachable_signatures,
    l0_language,
)
from metamorphosis.m089_substrate import (  # noqa: E402
    primitive_max_source_fanout,
    semantics_digest,
)

RESULT = ROOT / "experiments/M089/RESULT.json"
PROTOCOL = ROOT / "experiments/M089/PROTOCOL.json"
QUALIFICATION = ROOT / "experiments/M089/QUALIFICATION.json"
CLAIM = ROOT / "experiments/M089/REGISTER_CLAIM.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-result", action="store_true")
    arguments = parser.parse_args()
    if not RESULT.exists():
        print("no M089 result is present", file=sys.stderr)
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

    order = result["chronology"]["order"]
    if order.index("T12_l1_serialized") >= order.index("T13_qualification_materialized"):
        problems.append("qualification was materialized before the language was serialized")
    if result["chronology"]["ordered"] is not True:
        problems.append("the recorded chronology is out of order")

    # L0's insufficiency, re-derived rather than trusted.
    reproof = prove_l0_insufficient(DEVELOPMENT_TASK)
    recorded = result["development"]["insufficiency_proof"]
    for key in (
        "l0_max_sources_reachable", "task_required_sources",
        "task_outside_l0_constructive_image", "l0_exhaustive_search_found_program",
    ):
        if reproof[key] != recorded[key]:
            problems.append(f"the insufficiency proof does not reproduce on {key}")
    signatures = enumerate_l0_reachable_signatures(3)
    if max(max((len(item) for item in sig), default=0) for sig in signatures) != 1:
        problems.append("L0's single-source invariant does not hold on re-enumeration")

    development = result["development"]
    if development["adopted_primitive"] is None:
        problems.append("no primitive was adopted")
    else:
        primitive = PrimitiveContract.from_dict(development["adopted_primitive"])
        if semantics_digest(primitive.body, primitive.parameter_kinds) != primitive.semantics_digest:
            problems.append("the adopted primitive's semantics digest does not reproduce")
        if macro_reducible_to_l0(primitive):
            problems.append("the adopted primitive is macro-reducible to L0")
        if primitive_max_source_fanout(primitive) != result["adopted_primitive_max_source_fanout"]:
            problems.append("the recorded source fanout does not reproduce")
        if primitive.capabilities != ("pure_slot_write",):
            problems.append("the adopted primitive holds capabilities beyond a pure slot write")

        # Rerun the independent validation rather than trusting the stored verdict. PR #137 found
        # that a stale or forged `accepted` flag would otherwise satisfy P4 unchallenged.
        from metamorphosis.m089_lineage import PUBLIC_INPUTS, Task, _spec_sum_into

        retained = [Task("retained_copy", "retained", _spec_sum_into(1, 1, 1), PUBLIC_INPUTS)]
        revalidation = validate_primitive(
            replace(primitive, validation_receipt=""), l0_language(), retained, [(7, 3, 5)],
        )
        recorded_validation = development["validation"]
        if revalidation.accepted is not True:
            problems.append(
                "the adopted primitive does not revalidate: " + "; ".join(revalidation.reasons)
            )
        if recorded_validation is None or recorded_validation["accepted"] is not True:
            problems.append("the recorded validation does not report acceptance")
        elif revalidation.receipt != recorded_validation["receipt"]:
            problems.append("the recorded validation receipt does not recompute")
        if primitive.validation_receipt != revalidation.receipt:
            problems.append("the primitive's stored receipt does not match a fresh validation")

        base = l0_language()
        extended = base.register(primitive, EXTENSION_REASON)
        if extended.digest() != development["l1_digest"]:
            problems.append("the recorded L1 digest does not reproduce from L0 plus the primitive")
        if base.digest() != development["l0_digest"]:
            problems.append("the recorded L0 digest does not reproduce")

        # The two halves of the claim, re-derived on the qualifying tasks themselves.
        artifact = json.loads(QUALIFICATION.read_text(encoding="utf-8"))
        if artifact != result["qualification_artifact"]:
            problems.append("the committed qualification artifact differs from the recorded one")
        if artifact["materialized_by"] != "separate process":
            problems.append("qualification was not materialized by a separate process")
        if artifact["extended_language_digest"] != development["l1_digest"]:
            problems.append("qualification was drawn against a different language")
        import metamorphosis.m089_lineage as lineage_module

        if hasattr(lineage_module, "QUALIFICATION_POOL"):
            problems.append("the qualification pool is importable by the lineage")
        for spec in artifact["specifications"]:
            task = task_from_spec(spec)
            if search_transformation(task, base).found:
                problems.append(f"{task.task_id} is constructible under L0 after all")
            under_l1 = search_transformation(task, extended)
            if not under_l1.found or not under_l1.uses_registered_primitive:
                problems.append(f"{task.task_id} is not constructible under L1 via the primitive")

    for arm in CEILING_ARMS:
        if not result["arms"][arm]["is_ceiling"]:
            problems.append(f"{arm} is not flagged as a ceiling")
        if arm in json.dumps(result["evaluation"]):
            problems.append(f"{arm} appears in the verdict")

    budgeted = result["arms"]["more_budget_same_meta_language"]
    fixed = result["arms"]["fixed_meta_language"]
    if budgeted["total_programs_examined"] <= fixed["total_programs_examined"]:
        problems.append("the high-budget arm did not examine more programs than the fixed arm")
    if budgeted["uses_registered_primitive"]:
        problems.append("the high-budget arm escaped Closure(L0)")
    unregistered = result["arms"]["extension_built_but_not_registered"]
    if unregistered["primitive_built_but_not_registered"] is None:
        problems.append("the unregistered-extension arm did not build a primitive")
    if unregistered["language_version"] != 0:
        problems.append("the unregistered-extension arm registered something after all")

    # The checker reproduces the rollback record; it does not require the rollback to have
    # succeeded. A negative result must be verifiable exactly as faithfully as a positive one,
    # and P10 is where a failed rollback makes the verdict negative.
    if development["adopted_primitive"] is not None:
        recomputed = rollback_proof(
            l0_language(),
            l0_language().register(
                PrimitiveContract.from_dict(development["adopted_primitive"]), EXTENSION_REASON,
            ),
        )
        for side in ("before_extension", "after_extension"):
            for field in (
                "corruption_detected", "corrupted_state_was_the_restored_state",
                "fault_actually_changed_behaviour", "byte_identical_restore",
                "restored_behaviour_matches_intact", "damaged_refused_the_probe",
            ):
                if recomputed[side][field] != result["rollback"][side][field]:
                    problems.append(f"rollback {side}/{field} does not reproduce")
            if not result["rollback"][side]["corrupted_state_was_the_restored_state"]:
                problems.append(f"rollback {side} corrupted a copy rather than the restored state")

    if evaluate(development, result["arms"], result["rollback"]) != result["evaluation"]:
        problems.append("the recorded verdict does not reproduce from the preserved arms")
    body = {key: value for key, value in result.items() if key != "result_digest"}
    if digest_of(body) != result["result_digest"]:
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
    print(f"M089 result verified: {result['evaluation']['verdict']}, {len(CONDITIONS)} conditions, "
          f"digest {result['result_digest'][:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
