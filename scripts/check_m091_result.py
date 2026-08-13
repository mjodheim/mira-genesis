"""Decisive checker for M091: replay the science rather than read booleans.

Everything load-bearing is re-derived. The acquisition is re-run from the frozen substrate and must
adopt the same body; the refutation certificates are re-verified against the requirement itself;
the bend witness is re-run against the body; the macro closure is recomputed; the qualification is
re-materialized from a salt recomputed from the extended language's digest; every arm is re-run;
the rollbacks and the fresh processes are repeated; and the verdict is recomputed from the
preserved artifacts and compared with the recorded one.

It reproduces a negative exactly as readily as a positive. If a condition failed, this must say so.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from metamorphosis.m090_language import (  # noqa: E402
    LanguageError,
    MetaLanguageState,
    PrimitiveDefinition,
    digest_of,
    execute,
)
from metamorphosis.m090_migration import migrated_l0  # noqa: E402
from metamorphosis.m091_expressivity import (  # noqa: E402
    closure_lemma,
    refute_affine_single_source,
    verify_bend_witness,
    verify_refutation,
)
from metamorphosis.m091_lineage import (  # noqa: E402
    ARMS,
    CEILING_ARMS,
    CONDITIONS,
    RETAINED_WORLDS,
    acquire_primitive,
    conservation_report,
    evaluate,
    inherited_macro_semantics,
    rollback_proof,
    run_arm,
    state_authority_report,
    validate_candidate,
)
from metamorphosis.m091_substrate import (  # noqa: E402
    implementation_digest,
    semantics_digest,
    substrate_manifest,
)
from metamorphosis.m091_worlds import development_world, required_slots  # noqa: E402

EXPERIMENT = ROOT / "experiments/M091"
RESULT = EXPERIMENT / "RESULT.json"
PROTOCOL = EXPERIMENT / "PROTOCOL.json"
QUALIFICATION = EXPERIMENT / "QUALIFICATION.json"
CLAIM = EXPERIMENT / "REGISTER_CLAIM.json"


def main() -> int:  # noqa: C901 - a checker is a long list of independent checks
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-result", action="store_true")
    # There is deliberately no flag for skipping the depth-six budget arm. A checker with an
    # escape hatch reports "verified" while having skipped the most expensive falsifier, which is
    # the shape D053 disqualified M086-A over: an instrument that exists without being decisive.
    arguments = parser.parse_args()
    if not RESULT.exists():
        print("no M091 result is present", file=sys.stderr)
        return 2 if arguments.require_result else 0

    result = json.loads(RESULT.read_text(encoding="utf-8"))
    problems: list[str] = []

    # ---------------------------------------------------------------- provenance and bindings
    if result["protocol_raw_sha256"] != hashlib.sha256(PROTOCOL.read_bytes()).hexdigest():
        problems.append("the result does not bind the committed protocol blob")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if sorted(protocol["conditions"]) != sorted(CONDITIONS):
        problems.append("the protocol's conditions differ from the evaluated ones")
    if sorted(result["conditions_declared"]) != sorted(CONDITIONS):
        problems.append("the declared conditions differ from the frozen list")
    if sorted(result["evaluation"]["conditions"]) != sorted(CONDITIONS):
        problems.append("the evaluated conditions differ from the declared ones")
    if sorted(protocol["arms"]) != sorted(ARMS):
        problems.append("the protocol's arms differ from the implemented ones")
    if sorted(protocol["ceiling_arms"]) != sorted(CEILING_ARMS):
        problems.append("the protocol's ceiling arms differ from the excluded ones")

    preserved = sorted(path.name for path in EXPERIMENT.glob("WITHDRAWN_RESULT_*.json"))
    recorded = sorted(str(item["artifact"]) for item in result.get("prior_attempts", []))
    if recorded != preserved:
        problems.append("the recorded prior attempts do not match the preserved artifacts")
    if result["attempt"] != len(preserved) + 1:
        problems.append("the recorded attempt number does not match the preserved history")
    if result["retry_used"] is not bool(preserved):
        problems.append("retry_used does not match the preserved history")
    for item in result.get("prior_attempts", []):
        path = EXPERIMENT / str(item["artifact"])
        if not path.is_file():
            problems.append(f"a recorded prior attempt is missing: {item['artifact']}")
            continue
        superseded = json.loads(path.read_text(encoding="utf-8"))
        if superseded["result_digest"] != item["result_digest"]:
            problems.append(f"prior attempt digest does not match: {item['artifact']}")
    if result["model_calls"] != 0 or result["network_calls"] != 0:
        problems.append("the scientific run recorded a model or network call")
    if result["reattempts_m089"] is not False or result["h35_supported"] is not False:
        problems.append("the result claims M089 territory")

    # ---------------------------------------------------------------- the inherited language
    l0 = migrated_l0()
    if l0.digest() != result["l0_digest"]:
        problems.append("the inherited language digest does not reproduce")
    if sorted(l0.primitive_ids) != sorted(protocol["inherited_language_L0"]["primitives"]):
        problems.append("the inherited language differs from the protocol's")
    if digest_of(substrate_manifest()) != digest_of(result["substrate_manifest"]):
        problems.append("the extension substrate manifest does not reproduce")

    # ---------------------------------------------------------------- the insufficiency proof
    world = development_world()
    if digest_of(world) != digest_of(result["development_world"]):
        problems.append("the development world does not reproduce")
    lemma = closure_lemma(l0)
    recorded_diagnosis = result["acquisition"]["diagnosis"]
    if lemma["closed_under_every_primitive"] is not True:
        problems.append("the inherited language is not closed under the declared invariant")
    if lemma["escape_count"] != recorded_diagnosis["closure_lemma"]["escape_count"]:
        problems.append("the closure lemma does not reproduce")
    for certificate in recorded_diagnosis["refutations"]:
        slot = int(certificate["slot"])

        def required(inputs, slot=slot):
            return required_slots(world, inputs)[slot]

        for failure in verify_refutation(certificate, required):
            problems.append(f"refutation certificate: {failure}")
        replayed = refute_affine_single_source(required, slot)
        if replayed["outside_affine_single_source"] is not True:
            problems.append("the requirement is not outside the invariant on replay")
        if int(replayed["fan_in"]) != 1:
            problems.append("the requirement is not single-source, which is M089's gap not this one")

    # ---------------------------------------------------------------- the acquisition, re-run
    replayed_acquisition = acquire_primitive(world)
    recorded_acquisition = result["acquisition"]
    if replayed_acquisition.adopted is None:
        problems.append("the acquisition adopts nothing on replay")
    else:
        adopted = replayed_acquisition.adopted
        if adopted.to_dict() != recorded_acquisition["adopted_primitive"]:
            problems.append("the adopted primitive does not reproduce from the frozen substrate")
        if implementation_digest(adopted.body) != recorded_acquisition[
            "adopted_implementation_digest"
        ]:
            problems.append("the adopted implementation digest does not reproduce")
        for field in (
            "candidates_assembled", "candidates_well_formed", "candidates_validated",
            "rejected_count", "disposable_trials", "rejection_counts", "search_cost",
        ):
            if replayed_acquisition.to_dict()[field] != recorded_acquisition[field]:
                problems.append(f"acquisition/{field} does not reproduce")

        # Not a macro, by both certificates: the concrete bend witness and the extensional closure.
        witness = recorded_acquisition["validation"]["bend_witness"]
        if witness is None:
            problems.append("no bend witness is recorded for the adopted primitive")
        else:
            for failure in verify_bend_witness(adopted, witness):
                problems.append(f"bend witness: {failure}")
        macros = inherited_macro_semantics(adopted.parameter_kinds, l0)
        if semantics_digest(adopted.body, adopted.parameter_kinds) in macros:
            problems.append("the adopted primitive is inside the inherited closure")
        if len(macros) < 50:
            problems.append("the macro closure comparison is suspiciously small")

        # The validator, re-run, and its own positive controls.
        replayed_validation = validate_candidate(
            adopted, l0, RETAINED_WORLDS, require_bend=True,
        )
        if replayed_validation.accepted is not True:
            problems.append("the independent validator rejects the adopted primitive on replay")
        from metamorphosis.m090_migration import PROBE_EXTENSION

        m089_shaped = validate_candidate(
            PROBE_EXTENSION, l0, RETAINED_WORLDS, require_bend=True,
        )
        if m089_shaped.accepted is not False:
            problems.append("the validator accepts an M089-shaped primitive")
        if "overbroad_widens_the_source_fan_in" not in m089_shaped.reasons:
            problems.append("the validator does not refuse fan-in widening as overbroad")

        # Renaming must change nothing. Success is never an identifier comparison.
        from dataclasses import replace as _replace

        renamed = _replace(adopted, primitive_id="a_different_name_entirely")
        if renamed.semantics_digest() != adopted.semantics_digest():
            problems.append("renaming the primitive changed its semantics digest")
        if validate_candidate(renamed, l0, RETAINED_WORLDS, require_bend=True).accepted is not True:
            problems.append("the validator depends on the primitive's identifier")

    # ---------------------------------------------------------------- the enlarged language
    if replayed_acquisition.extended is None:
        problems.append("no extended language was produced on replay")
        l1 = l0
    else:
        l1 = MetaLanguageState.from_dict(
            json.loads(json.dumps(replayed_acquisition.extended.to_dict()))
        )
    if l1.digest() != result["l1_digest"]:
        problems.append("the extended language digest does not reproduce")
    if l1.digest() == l0.digest():
        problems.append("the extension did not change the language digest")

    conservation = conservation_report(l0, l1)
    for field in (
        "semantics_conserved", "space_excludes_nothing", "rejection_behaviour_conserved",
        "calls_checked", "programs_checked", "declared_binding_counts", "covered_binding_counts",
    ):
        if conservation[field] != result["conservation"][field]:
            problems.append(f"conservation/{field} does not reproduce")
    if conservation["declared_binding_counts"] != conservation["covered_binding_counts"]:
        problems.append("the conservation space excludes part of a declared domain")

    # ---------------------------------------------------------------- the qualification draw
    qualification = result["qualification"]
    if QUALIFICATION.exists():
        committed = json.loads(QUALIFICATION.read_text(encoding="utf-8"))
        if committed["artifact_digest"] != qualification["artifact_digest"]:
            problems.append("the committed qualification differs from the one in the result")
    adopted_semantics = recorded_acquisition["adopted_semantics_digest"]
    salt = hashlib.sha256(
        f"m091|{l1.digest()}|{adopted_semantics}".encode("utf-8")
    ).hexdigest()
    from materialize_m091_qualification import materialize

    redrawn = materialize(salt, l1.digest())
    if redrawn["artifact_digest"] != qualification["artifact_digest"]:
        problems.append("the qualification draw does not reproduce from the derived salt")
    if qualification["extended_language_digest"] != l1.digest():
        problems.append("the qualification is not bound to the extended language")
    worlds = list(qualification["worlds"])
    if len({str(item["family"]) for item in worlds}) < 2:
        problems.append("the qualification does not span two families")
    for item in worlds:
        if len(item.get("hidden_instances", ())) < 4:
            problems.append(f"{item['world_id']} holds out too little")
        if item["family"] == world["family"]:
            problems.append("a qualifying world repeats the development family")

    # ---------------------------------------------------------------- the arms
    from run_m091_experiment import (
        ceiling_primitive,
        fresh_process,
        import_graph_report,
        scan_for_lookup,
    )

    replayed_arms: dict[str, dict[str, object]] = {}
    for arm in ARMS:
        replayed_arms[arm] = run_arm(arm, replayed_acquisition, worlds, ceiling_primitive())
        recorded_arm = result["arms"][arm]
        for field in (
            "correct_worlds", "encounter_count", "families_solved", "uses_acquired_primitive",
            "total_programs_examined", "total_distinct_behaviours", "max_search_length",
            "repetitions", "language_digest", "language_version",
        ):
            if replayed_arms[arm][field] != recorded_arm[field]:
                problems.append(f"{arm}/{field} does not reproduce")
        for index, item in enumerate(replayed_arms[arm]["encounters"]):  # type: ignore[index]
            other = recorded_arm["encounters"][index]
            if item["search"]["program"] != other["search"]["program"]:
                problems.append(f"{arm}: a constructed program does not reproduce")
            if item["hidden_passed"] != other["hidden_passed"]:
                problems.append(f"{arm}: a hidden score does not reproduce")

    # Every program the evolvable arm constructed must really run through the language state.
    constructed = [
        tuple((name, tuple(args)) for name, args in item["search"]["program"])
        for item in result["arms"]["evolvable_meta_language"]["encounters"]
        if item["search"]["found"]
    ]
    if len(constructed) < 2:
        problems.append("the evolvable arm constructed fewer than two transformations")
    for program in constructed:
        if not any(name == recorded_acquisition["adopted_primitive"]["primitive_id"]
                   for name, _ in program):
            problems.append("a constructed transformation does not use the acquired primitive")
        try:
            execute(program, (1, 2, 3), l0)
            problems.append("a constructed transformation runs under the inherited language")
        except LanguageError:
            pass

    authority = state_authority_report(
        l1, constructed, str(recorded_acquisition["adopted_primitive"]["primitive_id"]),
    )
    for field in (
        "all_ran_intact", "removing_the_primitive_from_state_removes_the_transformation",
        "removing_an_inherited_primitive_removes_it_too",
    ):
        if authority[field] != result["persistence"][field]:
            problems.append(f"state authority/{field} does not reproduce")
        if authority[field] is not True:
            problems.append(f"state authority/{field} is false: the state is not the authority")

    # ---------------------------------------------------------------- rollback
    probes = result["probes"]
    replayed_rollback = {
        "before_adoption": rollback_proof(
            l0, replayed_acquisition.extended or l0, probes,
            fault="semantic_mutation", target="APPLY_UNARY", label="replay",
        ),
        "after_adoption": rollback_proof(
            l1, l1, probes, fault="removal",
            target=str(recorded_acquisition["adopted_primitive"]["primitive_id"]), label="replay",
        ),
    }
    for side, proof in replayed_rollback.items():
        for field in (
            "corruption_detected", "fault_actually_changed_behaviour", "byte_identical_restore",
            "digest_matches", "behaviour_restored", "probes_changed_by_the_fault",
            "live_state_differed_from_the_checkpoint", "restore_reversed_the_live_state",
            "probes_changed_by_restoring_the_checkpoint",
        ):
            if proof[field] != result["rollback"][side][field]:
                problems.append(f"rollback {side}/{field} does not reproduce")

    # ---------------------------------------------------------------- persistence
    for label, state, key in (
        ("intact", l1, "intact"),
        (
            "primitive_removed",
            l1.without(
                str(recorded_acquisition["adopted_primitive"]["primitive_id"]), "checker probe",
            ),
            "with_primitive_removed",
        ),
        ("fresh_agent", l0, "fresh_agent_process"),
    ):
        payload = fresh_process(state, worlds, label)
        recorded_payload = result["persistence"][key]
        if payload["correct_worlds"] != recorded_payload["correct_worlds"]:
            problems.append(f"fresh process {label}: the score does not reproduce")
        if payload["development_modules_imported"] is not False:
            problems.append(f"fresh process {label} imported a development module")
        if label == "intact" and payload["correct_worlds"] != len(worlds):
            problems.append("the extension does not survive into a fresh process")
        if label != "intact" and payload["correct_worlds"] != 0:
            problems.append(f"fresh process {label} solved a world it should not have")
        if label == "intact" and payload["acquired_semantics_digests"] != [adopted_semantics]:
            problems.append("the fresh process did not reuse the same primitive semantics")
        if label == "intact" and payload["language_version"] != 1:
            problems.append("the fresh process registered something new")

    # ---------------------------------------------------------------- integrity
    lookup = scan_for_lookup(
        replayed_acquisition.adopted, constructed + [replayed_acquisition.program or ()],
        qualification,
        [
            recorded_acquisition["adopted_implementation_digest"],
            recorded_acquisition["adopted_semantics_digest"],
        ],
    )
    if lookup["findings"]:
        problems.append(f"a disguised lookup was found: {lookup['findings']}")
    graph = import_graph_report()
    if graph["offending_imports"]:
        problems.append("the lineage can reach the qualification material")
    order = result["chronology"]["order"]
    if order.index("T11_qualification_materialized_separately") <= order.index(
        "T8_extension_adopted_and_serialized"
    ):
        problems.append("the qualification was materialized before the language was frozen")
    if order.index("T4_limitation_diagnosed") >= order.index("T6_primitive_adopted"):
        problems.append("the primitive was adopted before the limitation was diagnosed")

    # ---------------------------------------------------------------- the verdict
    recomputed = evaluate(
        result["acquisition"], result["arms"], result["rollback"], result["conservation"],
        result["persistence"], result["integrity"],
    )
    if recomputed != result["evaluation"]:
        problems.append("the recorded verdict does not reproduce from the preserved artifacts")
    replayed_verdict = evaluate(
        replayed_acquisition.to_dict(), replayed_arms, replayed_rollback, conservation,
        result["persistence"], result["integrity"],
    )
    if replayed_verdict["verdict"] != result["evaluation"]["verdict"]:
        problems.append("the verdict does not reproduce from a fresh replay")

    body = {key: value for key, value in result.items() if key != "result_digest"}
    if digest_of(body) != result["result_digest"]:
        problems.append("the result digest does not cover the preserved result")

    if CLAIM.exists():
        claim = json.loads(CLAIM.read_text(encoding="utf-8"))
        if claim["result_digest"] != result["result_digest"]:
            problems.append("the register claim and the result disagree on the digest")
        if claim["verdict"] != result["evaluation"]["verdict"]:
            problems.append("the register claim and the result disagree on the verdict")
        if claim["attempt"] != result["attempt"] or claim["retry_used"] != result["retry_used"]:
            problems.append("the register claim misstates the attempt provenance")
        for forbidden in (
            "gate_advanced", "h35_supported", "self_hosting_interpreter",
            "extension_substrate_endogenous",
        ):
            if claim.get(forbidden) is not False:
                problems.append(f"the register claim overstates the result: {forbidden}")
    elif arguments.require_result:
        problems.append("no register claim is present")

    for problem in problems:
        print(f"blocking: {problem}", file=sys.stderr)
    if problems:
        return 2
    print(
        f"M091 result verified: {result['evaluation']['verdict']}, {len(CONDITIONS)} conditions, "
        f"attempt {result['attempt']}, retry_used {result['retry_used']}, "
        f"digest {result['result_digest'][:16]}"
    )
    if result["evaluation"]["failed_conditions"]:
        print(f"failed conditions: {result['evaluation']['failed_conditions']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
