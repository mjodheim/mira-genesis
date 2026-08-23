"""Build and invoke pre-freeze M102 development capsules.

This helper cannot load a qualification pool, arm a canonical attempt, write a result,
or compute a scientific verdict.  It exists to test the frozen-style physical process
boundaries on DEVELOPMENT fixtures only.
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
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ISOLATED_PYTHON = Path(getattr(sys, "_base_executable", sys.executable)).resolve()

CAPSULE_SOURCES = {
    "acquisition": {
        "m101_runtime.py": "metamorphosis/m101_runtime.py",
        "m102_runtime.py": "metamorphosis/m102_runtime.py",
        "run.py": "scripts/run_m102_acquisition_process.py",
    },
    "execution": {
        "m101_executor.py": "metamorphosis/m101_executor.py",
        "m102_executor.py": "metamorphosis/m102_executor.py",
        "run.py": "scripts/run_m102_fresh_process.py",
    },
    "definition_checker": {
        "check_m101_definitions.py": "scripts/check_m101_definitions.py",
        "check_m102_definitions.py": "scripts/check_m102_definitions.py",
    },
}


class DevelopmentRefused(RuntimeError):
    pass


def capsule_binding(sources: dict[str, str]) -> tuple[str, dict[str, str]]:
    members = {
        destination: hashlib.sha256((ROOT / source).read_bytes()).hexdigest()
        for destination, source in sources.items()
    }
    return hashlib.sha256(
        json.dumps(members, sort_keys=True, separators=(",", ":")).encode("ascii")
    ).hexdigest(), members


def build_capsules(base: Path) -> tuple[dict[str, Path], dict[str, dict[str, Any]]]:
    capsules: dict[str, Path] = {}
    reports: dict[str, dict[str, Any]] = {}
    for name, sources in CAPSULE_SOURCES.items():
        capsule = base / f"m102-{name}-capsule"
        capsule.mkdir(parents=True)
        for destination, source in sources.items():
            shutil.copyfile(ROOT / source, capsule / destination)
        if sorted(path.name for path in capsule.iterdir()) != sorted(sources):
            raise DevelopmentRefused(f"unexpected member in M102 {name} capsule")
        capsule_digest, members = capsule_binding(sources)
        reports[name] = {
            "members": sorted(sources),
            "member_digests": members,
            "capsule_digest": capsule_digest,
        }
        capsules[name] = capsule
    return capsules, reports


def fresh(
    capsule: Path, entry: str, arguments: list[str], *, timeout: int = 90
) -> dict[str, Any]:
    completed = subprocess.run(
        [str(ISOLATED_PYTHON), "-I", str(capsule / entry), *arguments],
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


def acquisition(capsule: Path, action: str, *arguments: str) -> dict[str, Any]:
    return fresh(capsule, "run.py", [action, *arguments])


def execution(capsule: Path, action: str, *arguments: str) -> dict[str, Any]:
    return fresh(capsule, "run.py", [action, *arguments])


def definition_check(capsule: Path, *arguments: str) -> dict[str, Any]:
    return fresh(capsule, "check_m102_definitions.py", list(arguments))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capsule", choices=("acquisition", "execution", "definition_checker"))
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    options = parser.parse_args()
    forwarded = list(options.arguments)
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]
    with tempfile.TemporaryDirectory(prefix="m102-development-") as temporary:
        capsules, reports = build_capsules(Path(temporary))
        if options.capsule == "definition_checker":
            invocation = definition_check(capsules[options.capsule], *forwarded)
        else:
            if not forwarded:
                raise DevelopmentRefused("an action is required")
            action, *arguments = forwarded
            invoke = acquisition if options.capsule == "acquisition" else execution
            invocation = invoke(capsules[options.capsule], action, *arguments)
        result = {
            "schema": "m102-development-invocation-v1",
            "scientific_verdict": False,
            "capsule": reports[options.capsule],
            "invocation": invocation,
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return int(invocation["returncode"])


if __name__ == "__main__":
    raise SystemExit(main())
