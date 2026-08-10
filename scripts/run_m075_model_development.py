"""Run the committed public M075 baseline/context model-development comparison once."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m075_model_development_runner import (  # noqa: E402
    M075ModelDevelopmentError, execute_public_development, validate_protocol,
)
from mira_core.model import CodexExecBackend, find_codex_executable  # noqa: E402
from mira_core.process import run_utf8_process  # noqa: E402


DEFAULT_PROTOCOL = ROOT / "experiments" / "M075" / "MODEL_DEVELOPMENT_PROTOCOL.json"
DEFAULT_OUTPUT = ROOT / "experiments" / "M075" / "MODEL_DEVELOPMENT_RESULT.json"


def _checkpoint(path: Path, payload: Mapping[str, object]) -> None:
    temporary = path.with_name(f".{path.name}.m075-write")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n",
    )
    os.replace(temporary, path)


def run(protocol_path: Path, output_path: Path) -> dict[str, object]:
    if output_path.exists():
        raise M075ModelDevelopmentError(f"development output already exists: {output_path}")
    value = json.loads(protocol_path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise M075ModelDevelopmentError("model-development protocol must be one object")
    validate_protocol(value)
    runtime = value.get("runtime")
    if not isinstance(runtime, dict):
        raise M075ModelDevelopmentError("model-development protocol lacks runtime identity")
    executable = find_codex_executable()
    if executable is None:
        raise M075ModelDevelopmentError("M075 development requires the official Codex CLI")
    version = run_utf8_process([str(executable), "--version"], timeout_seconds=30)
    if version.returncode != 0 or version.stdout.strip() != value["model"]["codex_cli_version"]:
        raise M075ModelDevelopmentError("Codex CLI identity differs from development protocol")
    docker_version = run_utf8_process(
        ["docker", "version", "--format", "{{.Server.Version}}"], timeout_seconds=30,
    )
    if docker_version.returncode != 0 or docker_version.stdout.strip() != runtime.get(
        "docker_server_version"
    ):
        raise M075ModelDevelopmentError("Docker server identity differs from development protocol")
    if (
        platform.python_version() != runtime.get("python_version")
        or platform.system() != runtime.get("host_system")
    ):
        raise M075ModelDevelopmentError("host runtime differs from development protocol")
    with tempfile.TemporaryDirectory(prefix="mira-m075-neutral-") as raw_workspace:
        backend = CodexExecBackend(
            executable, Path(raw_workspace), str(value["model"]["model"]),
            timeout_seconds=float(value["budgets"]["codex_decision_timeout_seconds"]),
        )
        return asyncio.run(execute_public_development(
            value, backend, checkpoint=lambda payload: _checkpoint(output_path, payload),
        ))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        result = run(args.protocol.resolve(), args.output.resolve())
    except (M075ModelDevelopmentError, OSError, json.JSONDecodeError) as exc:
        print(f"M075 development refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "status": result["status"], "episodes": len(result["episodes"]),
        "live_model_decisions": result["live_model_decisions"],
        "output": str(args.output.resolve()),
    }, indent=2, sort_keys=True))
    return 0 if result["status"] == "development_complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
