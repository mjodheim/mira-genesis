"""Bind the M084 goal bank and preserve the first result.

This process never executes a stage. It writes a genesis organism, starts one child process per
stage with a file path, applies the two declared parent interventions — the `acquisition_ablated`
boundary and the forced fault after stage 1 — and reads back metrics. Everything the lineage carries
travels in the organism file.

Requires Docker, the M082 browser image and the M083 desktop image. Without them the experiment is
inconclusive rather than negative, and this script says so instead of recording a failure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m084_persistent_lineage import (  # noqa: E402
    ARMS,
    FORCED_FAULT_AFTER_STAGE,
    GENERATOR_VERSION,
    STAGE_SUBSTRATES,
    Organism,
    build_bank,
    evaluate,
    runnable,
    summarize_arm,
)

BASE = ROOT / "experiments/M084"
PROTOCOL_PATH = BASE / "PROTOCOL.json"
BANK_PATH = BASE / "BANK_COMMITMENT.json"
RESULT_PATH = BASE / "RESULT.json"
STAGE_SCRIPT = ROOT / "scripts/run_m084_stage.py"
STAGE_TIMEOUT = 2400.0


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def _seal(payload: dict, digest_key: str) -> dict:
    payload[digest_key] = hashlib.sha256(_canonical({
        key: value for key, value in payload.items() if key != digest_key
    })).hexdigest()
    return payload


def _write_once(path: Path, payload: dict, digest_key: str) -> None:
    _seal(payload, digest_key)
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get(digest_key) != payload[digest_key]:
            raise SystemExit(
                f"refusing to overwrite {path.name} with a different {digest_key}; "
                "the frozen protocol forbids replacing a materialized artifact"
            )
        print(f"{path.name} already bound and identical: {payload[digest_key]}")
        return
    path.write_bytes(
        json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n",
    )
    print(f"bound {path.name}: {payload[digest_key]}")


def apply_forced_fault(path: Path) -> str:
    """The declared corruption: break the chain and erase one acquisition, outside the checkpoint.

    The stage child must notice and restore. Nothing here repairs anything; a parent that repaired
    the organism would be holding the state the organism is supposed to carry.
    """

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["journal_digests"] = list(payload["journal_digests"]) + ["0" * 64]
    payload["predicates"] = {
        key: value for key, value in payload["predicates"].items() if key != "browser"
    }
    written = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    path.write_bytes(written)
    return hashlib.sha256(written).hexdigest()


def run_arm(arm: str, salt: bytes, workspace: Path, *, rehearsal: bool = False) -> list[dict]:
    organism_path = workspace / f"{arm}.organism.json"
    reports: list[dict] = []

    if arm != "fresh_each_stage":
        genesis = Organism.genesis(salt)
        organism_path.write_bytes(
            json.dumps(genesis.to_json(), indent=2, sort_keys=True).encode("utf-8"),
        )

    for stage in range(len(STAGE_SUBSTRATES)):
        report_path = workspace / f"{arm}.stage{stage}.report.json"
        command = [
            sys.executable, str(STAGE_SCRIPT),
            "--organism", str(organism_path),
            "--stage", str(stage),
            "--report", str(report_path),
            "--parent-pid", str(os.getpid()),
            "--arm", arm,
        ]
        if arm == "fresh_each_stage":
            command.append("--fresh")
        if arm == "acquisition_ablated" and stage > 0:
            command.append("--forget")
        if rehearsal:
            command += ["--salt-hex", salt.hex()]

        print(f"  {arm} stage {stage} ({STAGE_SUBSTRATES[stage]}) ...", flush=True)
        completed = subprocess.run(
            command, capture_output=True, timeout=STAGE_TIMEOUT, check=False,
        )
        if not report_path.exists():
            raise SystemExit(
                f"{arm} stage {stage} produced no report:\n"
                f"{completed.stderr.decode('utf-8', 'replace')[-2000:]}"
            )
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report.get("inconclusive"):
            raise SystemExit(f"INCONCLUSIVE: {report['inconclusive']}")
        if completed.returncode != 0:
            raise SystemExit(
                f"{arm} stage {stage} failed: {report.get('stage_error')}\n"
                f"{completed.stderr.decode('utf-8', 'replace')[-2000:]}"
            )

        handed = report["written_file_sha256"]
        if arm == "lineage" and stage == FORCED_FAULT_AFTER_STAGE:
            handed = apply_forced_fault(organism_path)
            report["forced_fault_applied"] = True
        report["handed_file_sha256"] = handed
        reports.append(report)

    return reports


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rehearse", default=None, metavar="SALT_HEX",
        help=(
            "run the complete pipeline on a throwaway salt without binding the bank or preserving "
            "a result. Used once before materialization so that the recorded run can be attempt 1 "
            "with no retry."
        ),
    )
    arguments = parser.parse_args()
    rehearsal = arguments.rehearse is not None

    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol["episode_generation"]["generator_version"] != GENERATOR_VERSION:
        raise SystemExit("generator version drifted from the frozen protocol")
    if protocol["claim_boundary"]["agi_evidence"] is not False:
        raise SystemExit("the claim boundary was weakened before the run")
    if not runnable():
        print(
            "INCONCLUSIVE: Docker, the M082 browser image or the M083 desktop image is "
            "unavailable, so M084 is not runnable rather than negative"
        )
        return 3

    salt = bytes.fromhex(arguments.rehearse or protocol["episode_generation"]["salt_hex"])
    bank = build_bank(salt)

    bank_payload = {
        "schema": "m084-bank-commitment-v1",
        "generator_version": GENERATOR_VERSION,
        "salt_sha256": hashlib.sha256(salt).hexdigest(),
        "stage_substrates": list(STAGE_SUBSTRATES),
        "goal_count": len(bank),
        "reachable_count": sum(1 for goal in bank if goal.reachable),
        "goals": [
            {
                "stage": goal.stage, "index": goal.index, "kind": goal.kind,
                "requirement": goal.requirement, "group": list(goal.group),
                "value": goal.value, "reachable": goal.reachable,
                "commitment": goal.commitment(),
            }
            for goal in bank
        ],
    }
    _seal(bank_payload, "bank_commitment")
    if not rehearsal:
        _write_once(BANK_PATH, bank_payload, "bank_commitment")

    arms: dict[str, dict] = {}
    with tempfile.TemporaryDirectory(prefix="m084-") as directory:
        workspace = Path(directory)
        for arm in ARMS:
            print(f"{arm}:", flush=True)
            arms[arm] = summarize_arm(
                arm, run_arm(arm, salt, workspace, rehearsal=rehearsal),
            )

    verdict = evaluate(arms)
    result_payload = {
        "schema": "m084-integrated-persistent-embodiment-result-v1",
        "protocol_commitment": hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest(),
        "bank_commitment": bank_payload["bank_commitment"],
        "attempt": 1,
        "retried": False,
        "external_model_called": False,
        "network_opened": False,
        "python": platform.python_version(),
        "arms": arms,
        "verdict": "positive" if verdict.positive else "negative",
        "failed_conditions": list(verdict.reasons),
        "claim_boundary": protocol["claim_boundary"],
        "rehearsal": rehearsal,
    }
    if rehearsal:
        print("REHEARSAL — no bank bound and no result preserved")
    else:
        _write_once(RESULT_PATH, result_payload, "result_sha256")

    print(f"\nverdict: {result_payload['verdict']}")
    for arm in ARMS:
        record = arms[arm]
        print(
            f"  {arm:22} reached={record['goals_reached_from_state']}/11"
            f" refused={record['refusals']}"
            f" false_refusals={record['false_refusals']}"
            f" probes={record['diagnostic_probes']}"
            f" repairs={record['repair_cycles']}"
            f" cost(1-3)={record['cost_stages_1_to_3']}"
            f" version={record['final_body_version']}"
        )
        print(f"    per-stage probes/repairs/afford: " + ", ".join(
            f"{s['diagnostic_probes']}/{s['repair_cycles']}/{s['affordance_probes']}"
            for s in record["per_stage"]
        ))
    for reason in verdict.reasons:
        print(f"  FAILED: {reason}")
    return 0 if verdict.positive else 1


if __name__ == "__main__":
    raise SystemExit(main())
