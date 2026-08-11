"""Run exactly one M084 stage, in this process, on the organism found at a file path.

The parent never executes a stage. It writes an organism file, starts this script, and reads back a
metrics report. Everything the lineage carries lives in the file this script loads and rewrites, so
the harness cannot silently become the holder of the state — the failure M082 came one design
decision away from recording, where a fresh browser profile per action would have left the harness
holding the browser's memory while every test stayed green.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m084_persistent_lineage import (  # noqa: E402
    STAGE_SUBSTRATES,
    LineageError,
    Organism,
    build_stage_goals,
    open_embodiment,
    run_stage,
)

PROTOCOL_PATH = ROOT / "experiments/M084/PROTOCOL.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--organism", required=True)
    parser.add_argument("--stage", type=int, required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--parent-pid", type=int, required=True)
    parser.add_argument("--arm", required=True)
    parser.add_argument(
        "--fresh", action="store_true",
        help="start a new genesis organism instead of loading the file",
    )
    parser.add_argument(
        "--forget", action="store_true",
        help="clear what the lineage acquired, keeping identity, version and journal",
    )
    parser.add_argument(
        "--salt-hex", default=None,
        help=(
            "rehearsal override only. The protocol salt is the default; the runner never passes "
            "this, and the checker fails the result if it appears in the preserved command."
        ),
    )
    arguments = parser.parse_args()

    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    salt = bytes.fromhex(arguments.salt_hex or protocol["episode_generation"]["salt_hex"])
    report_salt_overridden = arguments.salt_hex is not None
    stage = arguments.stage
    path = Path(arguments.organism)

    report: dict[str, object] = {
        "stage": stage,
        "arm": arguments.arm,
        "substrate": STAGE_SUBSTRATES[stage],
        "pid": os.getpid(),
        "parent_pid": arguments.parent_pid,
        "executed_in_child_process": os.getpid() != arguments.parent_pid,
        "fault_detected": False,
        "restored_digest": None,
        "acquisitions_cleared": bool(arguments.forget),
        "salt_overridden_for_rehearsal": report_salt_overridden,
    }

    if arguments.fresh:
        organism = Organism.genesis(salt + b"fresh" + stage.to_bytes(4, "big"))
        report["loaded_file_sha256"] = None
    else:
        raw = path.read_bytes()
        organism = Organism.from_json(json.loads(raw.decode("utf-8")))
        organism.loaded_file_sha256 = hashlib.sha256(raw).hexdigest()
        report["loaded_file_sha256"] = organism.loaded_file_sha256

        # The organism audits its own chain. A parent that repaired this for it would be holding
        # the very state the experiment claims the organism carries.
        if not organism.journal_verifies():
            report["fault_detected"] = True
            report["restored_digest"] = organism.restore_last_checkpoint()
            organism.record("fault_restored", {
                "stage": stage, "restored_digest": report["restored_digest"],
            })

    if arguments.forget:
        organism.forget_acquisitions()
        organism.record("acquisitions_cleared", {"stage": stage, "arm": arguments.arm})

    report["lineage_id"] = organism.lineage_id
    report["live_digest_before"] = organism.live_digest()
    report["journal_length_before"] = len(organism.journal_payloads)

    goals = build_stage_goals(salt, stage)
    try:
        embodiment = open_embodiment(stage)
    except Exception as error:  # noqa: BLE001 - not runnable is inconclusive, not negative
        report["inconclusive"] = f"{type(error).__name__}: {error}"
        Path(arguments.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
        return 3

    try:
        report["stage_report"] = run_stage(organism, stage, goals, embodiment, salt)
    except LineageError as error:
        report["stage_error"] = str(error)
        report["stage_report"] = None
    finally:
        embodiment.close()

    report["live_digest_after"] = organism.live_digest()
    report["journal_length_after"] = len(organism.journal_payloads)
    report["journal_verifies"] = organism.journal_verifies()
    report["body_version_after"] = organism.body_version
    report["checkpoint_stages"] = [
        int(checkpoint["stage"]) for checkpoint in organism.checkpoints
    ]

    written = json.dumps(organism.to_json(), indent=2, sort_keys=True).encode("utf-8")
    path.write_bytes(written)
    report["written_file_sha256"] = hashlib.sha256(written).hexdigest()

    Path(arguments.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report.get("stage_report") else 1


if __name__ == "__main__":
    raise SystemExit(main())
