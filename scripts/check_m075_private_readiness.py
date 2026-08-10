"""Report or enforce M075's fail-closed pre-private readiness boundary."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m075_private_readiness import (  # noqa: E402
    assess_repository_readiness,
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
        help="fail unless every independent pre-private input is present and verified",
    )
    arguments = parser.parse_args()
    report = assess_repository_readiness(ROOT, signature_verifier=_verify_ssh_signature)
    print(json.dumps(report, indent=2, sort_keys=True))
    if arguments.require_ready and report["ready_for_private_payload_reveal"] is not True:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
