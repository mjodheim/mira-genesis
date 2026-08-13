"""Decisive checker for M090: replay the science rather than read booleans."""
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
    digest_of,
    execute,
)
from metamorphosis.m090_lineage import (  # noqa: E402
    ARMS,
    CONDITIONS,
    Probe,
    evaluate,
    rollback_proof,
    run_arm,
)
from metamorphosis.m090_migration import (  # noqa: E402
    conservation_report,
    migrated_l0,
    with_probe_extension,
)

RESULT = ROOT / "experiments/M090/RESULT.json"
PROTOCOL = ROOT / "experiments/M090/PROTOCOL.json"
CLAIM = ROOT / "experiments/M090/REGISTER_CLAIM.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-result", action="store_true")
    arguments = parser.parse_args()
    if not RESULT.exists():
        print("no M090 result is present", file=sys.stderr)
        return 2 if arguments.require_result else 0

    result = json.loads(RESULT.read_text(encoding="utf-8"))
    problems: list[str] = []
    probes = [
        Probe(
            item["probe_id"],
            tuple((name, tuple(args)) for name, args in item["program"]),
            tuple(item["inputs"]), item["exercises"],
        )
        for item in result["probes"]
    ]

    if result["protocol_raw_sha256"] != hashlib.sha256(PROTOCOL.read_bytes()).hexdigest():
        problems.append("the result does not bind the committed protocol blob")
    if result["attempt"] != 1 or result["retry_used"] is not False:
        problems.append("the result is not a single unretried attempt")
    if result["model_calls"] != 0 or result["network_calls"] != 0:
        problems.append("the scientific run recorded a model or network call")
    if result["reattempts_m089"] is not False:
        problems.append("the result claims to re-attempt M089")
    if set(result["conditions_declared"]) != set(CONDITIONS):
        problems.append("the declared conditions differ from the frozen list")

    conservation = conservation_report(2)
    if conservation["semantics_conserved"] != result["conservation"]["semantics_conserved"]:
        problems.append("the conservation report does not reproduce")
    if conservation["programs_checked"] != result["conservation"]["programs_checked"]:
        problems.append("the conservation program count does not reproduce")

    l0 = migrated_l0()
    l1 = with_probe_extension(l0)
    if l0.digest() != result["l0_digest"] or l1.digest() != result["l1_digest"]:
        problems.append("the recorded language digests do not reproduce")

    for arm in ARMS:
        replayed = run_arm(arm, probes)
        recorded = result["arms"][arm]
        if replayed["behaviour_changed"] != recorded["behaviour_changed"]:
            problems.append(f"{arm}: behaviour_changed does not reproduce")
        if replayed["probes_whose_behaviour_changed"] != recorded[
            "probes_whose_behaviour_changed"
        ]:
            problems.append(f"{arm}: the changed-probe set does not reproduce")

    for key, language, fault, target in (
        ("inherited_removal", l0, "removal", "COPY_INPUT"),
        ("inherited_mutation", l0, "semantic_mutation", "APPLY_UNARY"),
        ("acquired_removal", l1, "removal", "COMBINE_INPUTS"),
    ):
        replayed = rollback_proof(language, probes, fault=fault, target=target, label=key)
        recorded = result["rollback"][key]
        for field in (
            "corruption_detected", "fault_actually_changed_behaviour",
            "byte_identical_restore", "digest_matches", "behaviour_restored",
            "probes_whose_behaviour_changed",
        ):
            if replayed[field] != recorded[field]:
                problems.append(f"rollback {key}/{field} does not reproduce")

    for label, state, key in (
        ("intact", l1, "intact"),
        ("missing", l1.without("COPY_INPUT", "checker negative test"), "with_primitive_removed"),
    ):
        with tempfile.TemporaryDirectory() as scratch:
            state_path = Path(scratch) / "state.json"
            probe_path = Path(scratch) / "probes.json"
            state_path.write_text(json.dumps(state.to_dict(), sort_keys=True), encoding="utf-8")
            probe_path.write_text(
                json.dumps([item.to_dict() for item in probes], sort_keys=True), encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable, str(ROOT / "scripts/run_m090_fresh_process.py"),
                    "--state", str(state_path), "--probes", str(probe_path),
                ],
                capture_output=True, text=True, check=True,
            )
        payload = json.loads(completed.stdout)
        recorded = result["fresh_process"][key]
        if payload["observations"] != recorded["observations"]:
            problems.append(f"fresh process {label}: observations do not reproduce")
        if payload["m089_module_imported"] or payload["migration_module_imported"]:
            problems.append(f"fresh process {label} imported a host semantic source")
        if label == "missing":
            resurrected = [
                item for item in payload["observations"]
                if item["probe_id"] in {"inherited_copy", "inherited_composite"}
                and not item["refused"]
            ]
            if resurrected:
                problems.append("a removed primitive was resurrected in a fresh process")

    for probe in probes:
        for name, _ in probe.program:
            if name not in l1.primitive_ids:
                problems.append(f"{name} is executed but absent from the language state")

    try:
        execute((("NOT_A_PRIMITIVE", ()),), (1, 2, 3), l1)
        problems.append("an unregistered primitive executed")
    except LanguageError:
        pass

    from run_m090_experiment import analyse_ownership, scan_for_host_authority

    scan = scan_for_host_authority()
    if scan["findings"] != result["host_authority_scan"]["findings"]:
        problems.append("the host-authority scan does not reproduce")
    if scan["findings"]:
        problems.append("a host-side semantic authority remains reachable")
    if analyse_ownership()["single_dispatch_path"] is not True:
        problems.append("the interpreter branches on a primitive identifier")

    recomputed = evaluate(
        conservation, result["arms"], result["rollback"], result["fresh_process"],
        result["ownership"], result["host_authority_scan"],
    )
    if recomputed != result["evaluation"]:
        problems.append("the recorded verdict does not reproduce from the preserved artifacts")
    body = {key: value for key, value in result.items() if key != "result_digest"}
    if digest_of(body) != result["result_digest"]:
        problems.append("the result digest does not cover the preserved result")

    claim = json.loads(CLAIM.read_text(encoding="utf-8"))
    if claim["result_digest"] != result["result_digest"]:
        problems.append("the register claim and the result disagree on the digest")
    if claim["verdict"] != result["evaluation"]["verdict"]:
        problems.append("the register claim and the result disagree on the verdict")
    if claim["gate_advanced"] is not False or claim["h35_supported"] is not False:
        problems.append("the register claim overstates the result")

    for problem in problems:
        print(f"blocking: {problem}", file=sys.stderr)
    if problems:
        return 2
    print(
        f"M090 result verified: {result['evaluation']['verdict']}, {len(CONDITIONS)} conditions, "
        f"digest {result['result_digest'][:16]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
