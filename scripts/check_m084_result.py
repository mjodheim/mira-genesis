"""Independently re-verify the preserved M084 result.

Checked unconditionally: the bank replays from the committed salt, the qualified mechanisms are
imported rather than restated, M081's `Agent` is still absent by design, no stage ran in the parent
process, the rehearsal salt never reached the recorded run, the acquisition that stage 0 induced is
the one stage 3 used, the forced fault was detected by a stage child and restored to a digest
recorded before the corruption, the frozen threshold recomputes from the preserved arms, and the
preserved digests recompute.

The live re-derivation is a complete second execution across three real substrates and takes tens of
minutes, so it is opt-in through MIRA_M084_LIVE_CHECK=1 rather than automatic.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m084_persistent_lineage import (  # noqa: E402
    ARMS,
    CONTINUITY_PROOFS,
    FORCED_FAULT_AFTER_STAGE,
    STAGE_SUBSTRATES,
    build_bank,
    evaluate,
    runnable,
)

BASE = ROOT / "experiments/M084"
MODULE = ROOT / "metamorphosis/m084_persistent_lineage.py"
RUNNER = ROOT / "scripts/run_m084_lineage.py"
CHILD = ROOT / "scripts/run_m084_stage.py"
PROTOCOL_PATH = BASE / "PROTOCOL.json"
BANK_PATH = BASE / "BANK_COMMITMENT.json"
RESULT_PATH = BASE / "RESULT.json"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def _fail(failures: list[str], condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def _import_map(path: Path) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module:
            found.setdefault(node.module, set()).update(alias.name for alias in node.names)
    return found


def main() -> int:
    failures: list[str] = []
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    bound = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    preserved = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    salt = bytes.fromhex(protocol["episode_generation"]["salt_hex"])

    _fail(
        failures,
        hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest() == preserved["protocol_commitment"],
        "protocol bytes no longer match the recorded commitment",
    )

    bank = build_bank(salt)
    _fail(
        failures,
        [goal.commitment() for goal in bank] == [row["commitment"] for row in bound["goals"]],
        "replayed bank does not match the bound commitment",
    )
    _fail(
        failures,
        hashlib.sha256(_canonical({
            key: value for key, value in bound.items() if key != "bank_commitment"
        })).hexdigest() == bound["bank_commitment"],
        "bank commitment does not recompute",
    )
    _fail(
        failures, sum(1 for goal in bank if goal.reachable) == 11,
        "the reachable goal count drifted from the frozen protocol",
    )

    # --- the mechanisms are composed, not restated -------------------------------------------
    imported = _import_map(MODULE)
    for module, names in (
        ("metamorphosis.m077_long_horizon_recovery", {"Journal", "GENESIS_DIGEST"}),
        ("metamorphosis.m080_continual_retention", {"Table", "ExceptionEntry"}),
        ("metamorphosis.bounded_search", {"uniform_cost_plans"}),
        ("metamorphosis.m081_two_real_environments", {"ShellEnvironment"}),
        ("metamorphosis.m082_browser_environment", {"BrowserEnvironment"}),
        ("metamorphosis.m083_gui_desktop_session", {"DesktopEnvironment"}),
    ):
        _fail(
            failures, names <= imported.get(module, set()),
            f"{sorted(names)} is no longer imported from {module}",
        )
    defined = {
        node.name for node in ast.walk(ast.parse(MODULE.read_text(encoding="utf-8")))
        if isinstance(node, ast.ClassDef)
    }
    for name in ("Journal", "Table", "ShellEnvironment", "BrowserEnvironment",
                 "DesktopEnvironment"):
        _fail(failures, name not in defined, f"{name} is redefined instead of reused")
    _fail(
        failures,
        "Agent" not in imported.get("metamorphosis.m081_two_real_environments", set()),
        "M081's Agent is imported, which would claim a reuse this experiment does not have",
    )
    _fail(
        failures,
        "uniform_cost_plans" in _import_map(
            ROOT / "metamorphosis/m079_planning_clarification.py"
        ).get("metamorphosis.bounded_search", set()),
        "M079 no longer shares its search with M084",
    )

    # --- the harness is not the state holder --------------------------------------------------
    runner_source = RUNNER.read_text(encoding="utf-8")
    called = {
        node.func.id for node in ast.walk(ast.parse(runner_source))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    for forbidden in ("run_stage", "pursue", "complete", "plan_for", "open_embodiment"):
        _fail(
            failures, forbidden not in called,
            f"the runner calls {forbidden} in the parent process",
        )
    _fail(failures, "subprocess.run" in runner_source, "the runner no longer starts a child process")
    child_source = CHILD.read_text(encoding="utf-8")
    for marker in ("loaded_file_sha256", "written_file_sha256", "journal_verifies"):
        _fail(failures, marker in child_source, f"the stage child no longer records {marker}")

    # --- the recorded run is the first, and not a rehearsal ------------------------------------
    _fail(failures, preserved["attempt"] == 1, "the preserved result is not attempt 1")
    _fail(failures, preserved["retried"] is False, "the preserved result records a retry")
    _fail(failures, preserved["rehearsal"] is False, "the preserved result is a rehearsal")
    _fail(
        failures, preserved["external_model_called"] is False,
        "the preserved result records an external model call",
    )
    for arm in ARMS:
        _fail(
            failures, preserved["arms"][arm]["rehearsal_salt_used"] is False,
            f"arm {arm} ran on the rehearsal salt",
        )

    # --- descent of an acquisition, not a coincidence ------------------------------------------
    lineage = preserved["arms"]["lineage"]
    predicates = lineage["predicates_per_stage"]
    _fail(
        failures, predicates[0] is not None and predicates[0] == predicates[3],
        "the predicate the lineage used on its return is not the one it induced in stage 0",
    )
    _fail(
        failures,
        preserved["arms"]["acquisition_ablated"]["predicates_per_stage"][3] == predicates[3],
        "the ablated arm did not re-derive the same predicate, so the two arms differ in what "
        "they knew rather than in when they learned it",
    )
    _fail(
        failures, lineage["continuity_proofs_failed"] == [],
        f"the lineage failed continuity proofs {lineage['continuity_proofs_failed']}",
    )
    fresh_failed = set(preserved["arms"]["fresh_each_stage"]["continuity_proofs_failed"])
    _fail(
        failures, fresh_failed <= set(CONTINUITY_PROOFS) and len(fresh_failed) >= 3,
        "the fresh arm did not fail at least three continuity proofs, so they are near vacuous",
    )
    _fail(
        failures,
        lineage["fault_detected_at_stage"] == [FORCED_FAULT_AFTER_STAGE + 1]
        and lineage["restored_digest"] == lineage["digest_recorded_before_the_fault"],
        "the forced fault was not detected by the stage child and restored to the digest recorded "
        "before the corruption",
    )

    # --- the frozen threshold ------------------------------------------------------------------
    verdict = evaluate(preserved["arms"])
    _fail(
        failures, (preserved["verdict"] == "positive") == verdict.positive,
        "the recomputed verdict disagrees with the preserved verdict",
    )
    _fail(
        failures, list(verdict.reasons) == preserved["failed_conditions"],
        "the recomputed failure list disagrees with the preserved one",
    )

    boundary = preserved["claim_boundary"]
    for key in (
        "establishes_cross_domain_transfer", "closes_generality_gate_g4",
        "closes_generality_gate_g6", "closes_generality_gate_g7",
        "establishes_general_desktop_competence", "establishes_open_ended_evolution",
        "establishes_general_autonomy", "genesis_gate_2_evidence", "agi_evidence",
    ):
        _fail(failures, boundary[key] is False, f"claim boundary weakened on {key}")

    _fail(
        failures,
        hashlib.sha256(_canonical({
            key: value for key, value in preserved.items() if key != "result_sha256"
        })).hexdigest() == preserved["result_sha256"],
        "preserved result digest does not recompute",
    )

    live = "skipped"
    if os.getenv("MIRA_M084_LIVE_CHECK") == "1" and runnable():
        completed = subprocess.run(
            [sys.executable, str(RUNNER), "--rehearse", salt.hex()],
            capture_output=True, timeout=14400, check=False,
        )
        transcript = completed.stdout.decode("utf-8", "replace")
        live = "performed"
        _fail(
            failures, "verdict: " + preserved["verdict"] in transcript,
            "a live re-derivation on the committed salt disagreed with the preserved verdict",
        )

    print(json.dumps({
        "schema": "m084-persistent-lineage-check-v1",
        "bank_commitment": bound["bank_commitment"],
        "result_sha256": preserved["result_sha256"],
        "verdict": preserved["verdict"],
        "stage_substrates": list(STAGE_SUBSTRATES),
        "predicate_carried_from_stage_0_to_stage_3": predicates[0] == predicates[3],
        "live_rederivation": live,
        "failures": failures,
        "ok": not failures,
    }, indent=2, sort_keys=True))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
