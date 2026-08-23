"""Build and invoke the pre-freeze M101 execution-only development capsule.

This helper cannot arm a qualification, author a pool, write ``RESULT.json`` or return a
scientific verdict. It only exposes the same two-file fresh-process boundary that a later
frozen runner may bind after independent review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ISOLATED_PYTHON = Path(getattr(sys, "_base_executable", sys.executable)).resolve()


class DevelopmentRefused(RuntimeError):
    pass


def build_capsule(base: Path) -> tuple[Path, dict[str, str]]:
    capsule = base / "m101-execution-capsule"
    capsule.mkdir(parents=True)
    members = {
        "m101_executor.py": ROOT / "metamorphosis" / "m101_executor.py",
        "run.py": ROOT / "scripts" / "run_m101_fresh_process.py",
    }
    digests: dict[str, str] = {}
    for name, source in members.items():
        destination = capsule / name
        shutil.copyfile(source, destination)
        digests[name] = hashlib.sha256(destination.read_bytes()).hexdigest()
    if sorted(path.name for path in capsule.iterdir()) != sorted(members):
        raise DevelopmentRefused("M101 execution capsule contains an unexpected file")
    return capsule, digests


def fresh_execute(
    capsule: Path,
    action: str,
    state: Path,
    world: Path,
    *,
    timeout: int = 30,
) -> dict[str, object]:
    if action not in {"execute-a", "execute-b"}:
        raise DevelopmentRefused("unknown M101 development action")
    completed = subprocess.run(
        [
            str(ISOLATED_PYTHON),
            "-I",
            str(capsule / "run.py"),
            action,
            "--state",
            str(state),
            "--world",
            str(world),
        ],
        cwd=capsule,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        payload = {
            "confirmed": False,
            "parse_error": str(error),
            "stdout_tail": completed.stdout[-500:],
        }
    return {
        "returncode": completed.returncode,
        "runtime": payload,
        "stderr": completed.stderr[-1000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("execute-a", "execute-b"))
    parser.add_argument("--state", required=True)
    parser.add_argument("--world", required=True)
    arguments = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="m101-development-") as temporary:
        capsule, digests = build_capsule(Path(temporary))
        result = fresh_execute(
            capsule,
            arguments.action,
            Path(arguments.state).resolve(),
            Path(arguments.world).resolve(),
        )
        result["capsule_member_digests"] = digests
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["returncode"] == 0 else int(result["returncode"])


if __name__ == "__main__":
    raise SystemExit(main())
