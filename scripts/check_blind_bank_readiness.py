"""Report or enforce the M075-B blind sealed-bank reveal gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m075b_blind_readiness import (  # noqa: E402
    assess_blind_bank_readiness,
)


def _verify_ssh_signature(
    message: bytes, signature_path: Path, allowed_signers: Path, identity: str, namespace: str,
) -> bool:
    executable = shutil.which("ssh-keygen")
    if executable is None:
        return False
    completed = subprocess.run(
        [
            executable, "-Y", "verify", "-f", str(allowed_signers), "-I", identity,
            "-n", namespace, "-s", str(signature_path),
        ],
        input=message,
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-ready", action="store_true",
        help="fail unless every pre-reveal artifact is present, bound and unrevealed",
    )
    parser.add_argument(
        "--assert-not-revealed", action="store_true",
        help="fail if a reveal has been authorized or a scientific result exists",
    )
    parser.add_argument(
        "--require-phase", default=None,
        help="fail unless the milestone is in exactly this phase",
    )
    arguments = parser.parse_args()

    report = assess_blind_bank_readiness(ROOT, signature_verifier=_verify_ssh_signature)
    print(json.dumps(report, indent=2, sort_keys=True))

    if arguments.require_ready and report["ready_for_reveal"] is not True:
        return 2
    if arguments.assert_not_revealed and (
        report["reveal_authorized"] is not False
        or report["scientific_result_exists"] is not False
    ):
        # The decisive line in CI. A sealed bank opened, or a result committed, without the
        # ordered chain of freezes must turn the repository red rather than be noticed later.
        print(
            "a reveal has been authorized or a result exists; this must be a deliberate, "
            "separately reviewed change",
            file=sys.stderr,
        )
        return 3
    if arguments.require_phase is not None and report["phase"] != arguments.require_phase:
        print(
            f"expected phase {arguments.require_phase!r}, found {report['phase']!r}",
            file=sys.stderr,
        )
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
