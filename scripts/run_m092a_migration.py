"""M092-A — run the migration, prove conservation, and try to break the authority claim.

This produces `SUBSTRATE_A.json` (the serialized state plus the probe set a fresh process replays)
and `M092A_REPORT.json` (everything below). It deliberately stops **before** any frozen checkpoint:
the digest is computed and reported, not sealed.

The adversarial half matters more than the conservation half. Conservation says the migration did not
change meaning; the falsifiers say the migration moved *authority*. A migration that copied semantics
into state while still executing them from host code would pass the first and fail the second.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from typing import Sequence

# `execute` and `LanguageError` are the FROZEN REFERENCE ORACLE, used here for conservation only.
# This is migration/conservation tooling, not the runtime path; no runtime module imports them.
from metamorphosis.m090_language import LanguageError, execute
from metamorphosis.m092_runtime import RefusalCode, SubstrateError
from metamorphosis.m092_invariant import (
    GERM_VARIABLE, MaxCertificate, germ_constant, germ_of_body, invariant_manifest,
    verify_max_certificate,
)
from metamorphosis import m092_kernel
from metamorphosis.m092_kernel import fuel_policy_provenance, kernel_manifest
from metamorphosis.m091_substrate import SIGNATURES, enumerate_candidate_bodies
from metamorphosis.m092_migration import (
    CONSERVATION_STATES, adversarial_conservation, capability_conservation,
    enumerate_bodies, exhaustive_legal_conservation, exhaustive_representation_conservation,
    inherited_l1,
    intractable_dimension, language_conservation, migrated_l0, migrated_substrate,
    observe_state, refusal_conservation, refusal_taxonomy_can_fail, serialization_conservation,
    signature_conservation, stack_depth_certificate, to_runtime_language,
)
from metamorphosis.m092_substrate_state import (
    SubstrateState, execute_from_state, registered_reach_report, run_body_from_state,
)

ARTIFACTS = os.path.join("experiments", "M092")
PROBE_INPUTS = ((3, 1, -2), (0, 0, 0), (-5, 4, 7), (9, -9, 2))


def build_probes(language) -> list[dict[str, object]]:
    """A deterministic probe set generated from the language itself, not from a fixture file."""

    probes: list[dict[str, object]] = []
    index = 0
    for definition in language.primitives:
        bindings: list[tuple[object, ...]] = []
        if definition.parameter_kinds == ("slot",):
            bindings = [(slot,) for slot in range(4)]
        elif definition.parameter_kinds == ("slot", "const"):
            bindings = [(slot, value) for slot in range(4) for value in (0, 1)]
        elif definition.parameter_kinds == ("slot", "input"):
            bindings = [(slot, source) for slot in range(4) for source in range(3)]
        elif definition.parameter_kinds == ("slot", "unary_op"):
            bindings = [
                (slot, op) for slot in range(4) for op in ("inc", "dec", "neg", "double")
            ]
        for binding in bindings:
            for inputs in PROBE_INPUTS:
                probes.append({
                    "id": f"p{index}",
                    "program": [[definition.primitive_id, list(binding)]],
                    "inputs": list(inputs),
                })
                index += 1
    # composite programs, including one that exercises the acquired M091 primitive
    composites = [
        [["COPY_INPUT", [0, 0]], ["APPLY_UNARY", [0, "neg"]], ["CLAMP_FLOOR", [0]]],
        [["COPY_INPUT", [1, 1]], ["APPLY_UNARY", [1, "double"]], ["CLAMP_FLOOR", [1]]],
        [["SET_CONST", [2, 1]], ["APPLY_UNARY", [2, "dec"]], ["CLAMP_FLOOR", [2]],
         ["APPLY_UNARY", [2, "inc"]]],
        [["COPY_INPUT", [3, 2]], ["APPLY_UNARY", [3, "neg"]], ["CLAMP_FLOOR", [3]],
         ["APPLY_UNARY", [3, "neg"]]],
    ]
    for program in composites:
        for inputs in PROBE_INPUTS:
            probes.append({
                "id": f"p{index}", "program": program, "inputs": list(inputs),
            })
            index += 1
    return probes


def expected_outcomes(probes, language, substrate) -> dict[str, object]:
    outcomes = {}
    for probe in probes:
        program = [(name, tuple(args)) for name, args in probe["program"]]
        try:
            outcomes[probe["id"]] = list(
                execute_from_state(program, probe["inputs"], language, substrate)
            )
        except SubstrateError:
            outcomes[probe["id"]] = None
    return outcomes


def write_state(path: str, language, substrate, probes, bind_digest: bool = True) -> None:
    payload = {
        "language": to_runtime_language(language).to_dict(),
        "substrate": substrate.to_dict(),
        "probes": probes,
    }
    if bind_digest:
        payload["expected_substrate_digest"] = substrate.digest()
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)


def isolated_process(state_path: str) -> dict[str, object]:
    """Physical isolation: a runtime built from files that do not include `m090_language.py`."""

    completed = subprocess.run(
        [sys.executable, "-m", "scripts.run_m092a_isolation", "--state", state_path],
        capture_output=True, text=True,
    )
    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError:
        report = {"status": "unparseable", "stderr": completed.stderr[-2000:]}
    report["exit_code"] = completed.returncode
    return report


def fresh_process(state_path: str, sabotage: bool = False) -> dict[str, object]:
    command = [sys.executable, "-m", "scripts.run_m092a_fresh_process", "--state", state_path]
    if sabotage:
        command.append("--sabotage-legacy")
    completed = subprocess.run(command, capture_output=True, text=True)
    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError:
        report = {"status": "unparseable", "stdout": completed.stdout[-2000:],
                  "stderr": completed.stderr[-2000:]}
    report["exit_code"] = completed.returncode
    return report


# --------------------------------------------------------------------------- authority falsifiers


def authority_falsifiers(language, substrate: SubstrateState) -> dict[str, object]:
    """Each of these must break something. A migration that survives them all is not authoritative."""

    results: list[dict[str, object]] = []

    def probe(state: SubstrateState, program, inputs=(3, 1, -2)):
        try:
            return list(execute_from_state(program, inputs, language, state))
        except SubstrateError as error:
            return f"refused: {type(error).__name__}"

    clamp = [("COPY_INPUT", (0, 0)), ("APPLY_UNARY", (0, "neg")), ("CLAMP_FLOOR", (0,))]
    unary = [("COPY_INPUT", (0, 0)), ("APPLY_UNARY", (0, "neg"))]

    baseline_clamp = probe(substrate, clamp)
    baseline_unary = probe(substrate, unary)

    # 1. removing a serialized inherited operation removes the capability
    without_max = substrate.without("BINOP:max")
    results.append({
        "falsifier": "removing_binop_max_removes_the_clamp",
        "baseline": baseline_clamp,
        "after": probe(without_max, clamp),
        "broke_the_capability": probe(without_max, clamp) != baseline_clamp,
        "unrelated_operation_still_works": probe(without_max, unary) == baseline_unary,
    })

    # 2. corrupting a program changes or rejects its semantics
    corrupted = substrate.replacing("UNOP:neg", [
        ("SPOP", 0), ("LOADI", 1, 7), ("ADD", 2, 0, 1), ("SPUSH", 2), ("HALT",),
    ])
    results.append({
        "falsifier": "corrupting_unop_neg_changes_semantics",
        "baseline": baseline_unary,
        "after": probe(corrupted, unary),
        "semantics_changed": probe(corrupted, unary) != baseline_unary,
    })

    # 3. a structurally invalid program is rejected rather than silently ignored
    try:
        substrate.replacing("UNOP:neg", [("NOT_AN_OPCODE", 0)])
        rejected = False
    except SubstrateError:
        rejected = True
    results.append({
        "falsifier": "invalid_program_is_rejected_at_registration",
        "rejected": rejected,
    })

    # 4. an unknown operation cannot fall through to legacy host semantics
    unknown_body = (("NO_SUCH_OP", 0),)
    try:
        run_body_from_state(unknown_body, (), [0] * 4, [0] * 3, substrate)
        fell_through = True
    except SubstrateError:
        fell_through = False
    # and a REMOVED but otherwise legal operation must not be recovered from host code
    without_push = substrate.without("PUSH_SLOT")
    try:
        run_body_from_state((("PUSH_SLOT", 0),), (), [0] * 4, [0] * 3, without_push)
        removed_recovered = True
    except SubstrateError:
        removed_recovered = False
    results.append({
        "falsifier": "no_fallback_to_legacy_host_semantics",
        "unknown_operation_fell_through": fell_through,
        "removed_operation_was_recovered": removed_recovered,
        "passes": not fell_through and not removed_recovered,
    })

    # 5. the reference oracle and the state are genuinely different code paths
    mutated = substrate.replacing("UNOP:double", [
        ("SPOP", 0), ("LOADI", 1, 3), ("MUL", 2, 0, 1), ("SPUSH", 2), ("HALT",),
    ])
    body = (("PUSH_SLOT", 0), ("UNOP", "double"), ("STORE_SLOT", 0))
    from metamorphosis.m090_language import run_body as reference_run_body
    reference = reference_run_body(body, (), [5, 0, 0, 0], [0, 0, 0])
    state_side = run_body_from_state(body, (), [5, 0, 0, 0], [0, 0, 0], mutated)
    results.append({
        "falsifier": "state_diverges_from_the_oracle_when_state_is_edited",
        "reference": list(reference),
        "state_owned": list(state_side),
        "diverged": list(reference) != list(state_side),
    })

    return {
        "falsifiers": results,
        "all_behaved_as_required": all(
            row.get("broke_the_capability", True)
            and row.get("unrelated_operation_still_works", True)
            and row.get("semantics_changed", True)
            and row.get("rejected", True)
            and row.get("passes", True)
            and row.get("diverged", True)
            for row in results
        ),
    }


def fuel_insensitivity(substrate: SubstrateState) -> dict[str, object]:
    """Vary the fuel constants over two orders of magnitude; the result must not move.

    This is the demonstration that the fuel policy was not fitted. If any conservation number
    changed when the constants changed, the policy would be carrying part of the semantics.
    """

    base, slope = m092_kernel.FUEL_BASE, m092_kernel.FUEL_SLOPE
    rows = []
    signatures = set()
    try:
        for candidate_base, candidate_slope in (
            (16, 0), (64, 1), (256, 4), (1024, 16), (4096, 64),
        ):
            m092_kernel.FUEL_BASE, m092_kernel.FUEL_SLOPE = candidate_base, candidate_slope
            report = exhaustive_representation_conservation(substrate, 2)
            signature = (
                report["comparisons"], report["agreeing_values"],
                report["agreeing_refusals"], report["mismatches"],
                tuple(sorted(report["refusals_by_code"].items())),
            )
            signatures.add(signature)
            rows.append({
                "fuel_base": candidate_base, "fuel_slope": candidate_slope,
                "comparisons": report["comparisons"], "mismatches": report["mismatches"],
            })
    finally:
        m092_kernel.FUEL_BASE, m092_kernel.FUEL_SLOPE = base, slope

    return {
        "settings_tried": rows,
        "distinct_result_signatures": len(signatures),
        "result_is_independent_of_the_fuel_policy": len(signatures) == 1,
        "restored_base": m092_kernel.FUEL_BASE,
        "restored_slope": m092_kernel.FUEL_SLOPE,
    }


def rollback_report(substrate: SubstrateState) -> dict[str, object]:
    """Exact rollback to the M092-A state after deliberate damage, compared by bytes."""

    original_text = substrate.serialize()
    original_digest = substrate.digest()

    damaged = substrate.without("BINOP:max").replacing("UNOP:inc", [
        ("SPOP", 0), ("SPUSH", 0), ("HALT",),
    ])
    restored = SubstrateState.deserialize(original_text)

    behavioural = mismatches = 0
    for body in enumerate_bodies(2):
        for inputs, slots in CONSERVATION_STATES[:4]:
            def observe(state):
                try:
                    return tuple(run_body_from_state(body, (), list(slots), inputs, state))
                except SubstrateError:
                    return "refused"
            behavioural += 1
            if observe(substrate) != observe(restored):
                mismatches += 1

    return {
        "damaged_digest_differs": damaged.digest() != original_digest,
        "restored_bytes_identical": restored.serialize() == original_text,
        "restored_digest_identical": restored.digest() == original_digest,
        "behavioural_comparisons": behavioural,
        "behavioural_mismatches": mismatches,
        "exact": (
            restored.serialize() == original_text
            and restored.digest() == original_digest
            and mismatches == 0
        ),
    }


def m091_rollback(substrate: SubstrateState) -> dict[str, object]:
    """M092-A must be able to hand execution back to the M091 arrangement, behaviour identical."""

    language = inherited_l1()
    runtime = to_runtime_language(language)
    comparisons = mismatches = 0
    for definition in language.primitives:
        for slot in range(4):
            for inputs, _ in CONSERVATION_STATES:
                program = [(definition.primitive_id, (slot,))] if definition.arity == 1 else None
                if program is None:
                    continue
                try:
                    reference: object = execute(program, inputs, language)
                except SubstrateError:
                    reference = "refused"
                try:
                    observed: object = execute_from_state(program, inputs, language, substrate)
                except SubstrateError:
                    observed = "refused"
                comparisons += 1
                if reference != observed:
                    mismatches += 1
    return {
        "language_digest_unchanged_by_m092a": language.digest() == inherited_l1().digest(),
        "comparisons": comparisons,
        "mismatches": mismatches,
        "behaviour_identical": mismatches == 0,
    }


def invariant_machine_check(max_length: int = 3) -> dict[str, object]:
    """Machine-check M092-I's `max` branch selection over the frozen assembly space."""

    total = verified = failed = trivial = 0
    findings: list[str] = []
    for signature in SIGNATURES:
        for body in enumerate_candidate_bodies(signature, max_length):
            certificates: list[MaxCertificate] = []
            try:
                germ_of_body(
                    body, tuple(0 for _ in signature),
                    [germ_constant(0)] * 4,
                    [GERM_VARIABLE, germ_constant(3), germ_constant(-4)],
                    certificates,
                )
            except LanguageError:
                continue
            for certificate in certificates:
                total += 1
                outcome = verify_max_certificate(certificate)
                if outcome["identically_equal"]:
                    trivial += 1
                if outcome["algebraically_verified"]:
                    verified += 1
                else:
                    failed += 1
                    if len(findings) < 5:
                        findings.extend(str(item) for item in outcome["findings"])
    return {
        "max_certificates": total,
        "algebraically_verified": verified,
        "failed": failed,
        "identically_equal_cases": trivial,
        "findings": findings,
        "all_verified": failed == 0 and total > 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body-length", type=int, default=3)
    parser.add_argument("--program-length", type=int, default=2)
    arguments = parser.parse_args()

    os.makedirs(ARTIFACTS, exist_ok=True)
    substrate = migrated_substrate()
    l0, l1 = migrated_l0(), inherited_l1()
    probes = build_probes(l1)
    runtime_l1 = to_runtime_language(l1)

    state_path = os.path.join(ARTIFACTS, "SUBSTRATE_A.json")
    write_state(state_path, l1, substrate, probes)
    expected = expected_outcomes(probes, runtime_l1, substrate)

    # ---- fresh-process variants
    # Deliberately damaged states are written outside the repository. They are regenerable, and a
    # corrupted substrate sitting next to the real one is exactly the sort of artifact a reviewer
    # could mistake for evidence.
    scratch = tempfile.mkdtemp(prefix="m092a-damaged-")

    full = fresh_process(state_path)
    sabotaged = fresh_process(state_path, sabotage=True)

    minus_path = os.path.join(scratch, "minus_max.json")
    write_state(minus_path, l1, substrate.without("BINOP:max"), probes)
    minus = fresh_process(minus_path)

    corrupt_path = os.path.join(scratch, "corrupt_neg.json")
    write_state(corrupt_path, l1, substrate.replacing("UNOP:neg", [
        ("SPOP", 0), ("LOADI", 1, 7), ("ADD", 2, 0, 1), ("SPUSH", 2), ("HALT",),
    ]), probes)
    corrupt = fresh_process(corrupt_path)

    stale_path = os.path.join(scratch, "stale_digest.json")
    write_state(stale_path, l1, substrate, probes, bind_digest=False)
    with open(stale_path, encoding="utf-8") as handle:
        stale_payload = json.load(handle)
    stale_payload["expected_substrate_digest"] = "0" * 64
    with open(stale_path, "w", encoding="utf-8") as handle:
        json.dump(stale_payload, handle, indent=2, sort_keys=True)
    stale = fresh_process(stale_path)
    isolated = isolated_process(state_path)

    def matches_expected(report) -> bool:
        if report.get("status") != "ok":
            return False
        return all(
            (row["slots"] if row["status"] == "value" else None) == expected[row["id"]]
            for row in report["outcomes"]
        )

    def differs_from_expected(report) -> int:
        if report.get("status") != "ok":
            return -1
        return sum(
            1 for row in report["outcomes"]
            if (row["slots"] if row["status"] == "value" else None) != expected[row["id"]]
        )

    fresh_summary = {
        "full_state": {
            "exit_code": full.get("exit_code"), "values": full.get("values"),
            "refusals": full.get("refusals"), "matches_expected": matches_expected(full),
            "import_census_clean": full.get("import_census_clean"),
            "forbidden_modules_present": full.get("forbidden_modules_present"),
            "import_census": full.get("import_census"),
        },
        "legacy_sabotaged": {
            "exit_code": sabotaged.get("exit_code"),
            "matches_expected": matches_expected(sabotaged),
            "identical_to_full": sabotaged.get("outcomes") == full.get("outcomes"),
        },
        "minus_binop_max": {
            "exit_code": minus.get("exit_code"),
            "probes_that_changed": differs_from_expected(minus),
            "refusals": minus.get("refusals"),
            "capability_disappeared": differs_from_expected(minus) > 0,
        },
        "corrupted_unop_neg": {
            "exit_code": corrupt.get("exit_code"),
            "probes_that_changed": differs_from_expected(corrupt),
            "semantics_changed": differs_from_expected(corrupt) > 0,
        },
        "physically_isolated": {
            "exit_code": isolated.get("exit_code"),
            "findings": isolated.get("findings"),
            "m090_language_present_in_root": isolated.get("m090_language_present_in_root"),
            "permitted_runtime_modules": isolated.get("permitted_runtime_modules"),
            "loaded_project_modules": isolated.get("loaded_project_modules"),
            "modules_outside_the_isolated_root_or_stdlib": isolated.get(
                "modules_outside_the_isolated_root_or_stdlib"
            ),
            "removed_meta_path_finders": isolated.get("removed_meta_path_finders"),
            "matches_expected": all(
                (row["slots"] if row["status"] == "value" else None) == expected[row["id"]]
                for row in isolated.get("outcomes", [])
            ) and bool(isolated.get("outcomes")),
        },
        "stale_digest": {
            "exit_code": stale.get("exit_code"),
            "status": stale.get("status"),
            "failed_closed": stale.get("exit_code") == 2,
        },
    }

    report = {
        "schema": "m092a-report-v1",
        "frozen": False,
        "note": "M092-A checkpoint is NOT frozen; this run reports the digest, it does not seal it",
        "substrate_digest": substrate.digest(),
        "kernel": kernel_manifest(),
        "fuel_policy_provenance": fuel_policy_provenance(),
        "fuel_insensitivity": fuel_insensitivity(substrate),
        "invariant": invariant_manifest(),
        "registered_reach": registered_reach_report(substrate),
        "signature_conservation": signature_conservation(substrate),
        "capability_conservation": capability_conservation(substrate),
        "serialization_conservation": serialization_conservation(substrate),
        "refusal_conservation": refusal_conservation(substrate),
        "stack_depth_certificate": stack_depth_certificate(),
        "exhaustive_legal_conservation": exhaustive_legal_conservation(substrate),
        "exhaustive_representation_conservation": exhaustive_representation_conservation(
            substrate, arguments.body_length,
        ),
        "intractable_dimension": intractable_dimension(),
        "adversarial_conservation": adversarial_conservation(substrate),
        "refusal_taxonomy_can_fail": refusal_taxonomy_can_fail(substrate),
        "language_conservation_l0": language_conservation(substrate, l0, arguments.program_length),
        "language_conservation_l1": language_conservation(substrate, l1, arguments.program_length),
        "authority_falsifiers": authority_falsifiers(runtime_l1, substrate),
        "fresh_process": fresh_summary,
        "rollback_to_m092a": rollback_report(substrate),
        "rollback_to_m091": m091_rollback(substrate),
        "invariant_machine_check": invariant_machine_check(arguments.body_length),
    }

    with open(os.path.join(ARTIFACTS, "M092A_REPORT.json"), "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)

    # ------------------------------------------------------------------------------- human summary
    print("== M092-A: state-owned substrate migration ==\n")
    print(f"substrate digest      : {report['substrate_digest']}")
    reach = report["registered_reach"]
    print(f"registered operations : {reach['operations']}, acquired {reach['acquired_operations']}, "
          f"loop-free {reach['every_registered_program_is_loop_free']}")
    for key in ("exhaustive_legal_conservation", "exhaustive_representation_conservation"):
        bc = report[key]
        print(f"{key:<38}: {bc['comparisons']} comparisons "
              f"({bc['agreeing_values']} values, {bc['agreeing_refusals']} refusals), "
              f"{bc['mismatches']} mismatches")
    sc = report["stack_depth_certificate"]
    print(f"stack depth certificate               : max reachable {sc['max_reachable_stack_depth']} "
          f"vs bound {sc['declared_stack_bound']}, reachable={sc['bound_is_reachable']}")
    tf = report["refusal_taxonomy_can_fail"]
    print(f"refusal taxonomy can fail             : {tf['all_detected']} "
          f"({tf['cases_where_both_refused_differently']} cases refused differently)")
    ac = report["adversarial_conservation"]
    print(f"adversarial sweep     : {ac['trials']} trials at lengths 4-{ac['body_lengths'][1]} "
          f"({ac['reference_values']} values, {ac['reference_refusals']} refusals), "
          f"{ac['mismatches']} mismatches")
    for key in ("language_conservation_l0", "language_conservation_l1"):
        lc = report[key]
        print(f"{key:<22}: {lc['programs']} programs, {lc['comparisons']} comparisons, "
              f"{lc['mismatches']} mismatches, coverage complete {lc['coverage_is_complete']}")
    rc = report["refusal_conservation"]
    print(f"refusal conservation  : {rc['count']} cases, {rc['disagreements']} disagreements")
    print(f"authority falsifiers  : all behaved as required "
          f"{report['authority_falsifiers']['all_behaved_as_required']}")
    for name, row in fresh_summary.items():
        print(f"  fresh/{name:<20} {row}")
    print(f"rollback to M092-A    : {report['rollback_to_m092a']['exact']}")
    print(f"rollback to M091      : {report['rollback_to_m091']['behaviour_identical']}")
    fi = report["fuel_insensitivity"]
    print(f"fuel insensitivity    : {fi['distinct_result_signatures']} distinct signature(s) over "
          f"{len(fi['settings_tried'])} fuel settings -> "
          f"independent={fi['result_is_independent_of_the_fuel_policy']}")
    imc = report["invariant_machine_check"]
    print(f"max certificates      : {imc['max_certificates']} checked, "
          f"{imc['algebraically_verified']} verified, {imc['failed']} failed")

    ok = (
        report["exhaustive_legal_conservation"]["mismatches"] == 0
        and report["exhaustive_representation_conservation"]["mismatches"] == 0
        and report["adversarial_conservation"]["mismatches"] == 0
        and report["refusal_taxonomy_can_fail"]["all_detected"]
        and not report["stack_depth_certificate"]["bound_is_reachable"]
        and not report["stack_depth_certificate"]["effect_disagreements"]
        and report["language_conservation_l0"]["mismatches"] == 0
        and report["language_conservation_l1"]["mismatches"] == 0
        and rc["disagreements"] == 0
        and report["authority_falsifiers"]["all_behaved_as_required"]
        and fresh_summary["full_state"]["matches_expected"]
        and fresh_summary["full_state"]["import_census_clean"]
        and fresh_summary["legacy_sabotaged"]["identical_to_full"]
        and fresh_summary["minus_binop_max"]["capability_disappeared"]
        and fresh_summary["corrupted_unop_neg"]["semantics_changed"]
        and fresh_summary["stale_digest"]["failed_closed"]
        and fresh_summary["physically_isolated"]["exit_code"] == 0
        and fresh_summary["physically_isolated"]["matches_expected"]
        and not fresh_summary["physically_isolated"]["findings"]
        and report["rollback_to_m092a"]["exact"]
        and report["rollback_to_m091"]["behaviour_identical"]
        and imc["all_verified"]
        and report["fuel_insensitivity"]["result_is_independent_of_the_fuel_policy"]
        and report["signature_conservation"]["nothing_acquired"]
    )
    print(f"\nM092-A complete and unfrozen: {ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
