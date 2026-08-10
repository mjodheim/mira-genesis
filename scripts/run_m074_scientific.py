"""Execute the single frozen M074 scientific refusal-calibration campaign.

The command refuses an existing output file and has no resume mode.  It validates the complete
protocol, code-byte bindings, local tool identities and backend identity before the first model
decision.  Checkpoints are atomically replaced after every completed episode so an interruption
remains visible but can never be resumed as the same scientific attempt.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m074_scientific_runner import (  # noqa: E402
    ScientificRunnerError, execute_campaign, validate_protocol,
)
from mira_core.model import CodexExecBackend, find_codex_executable  # noqa: E402
from mira_core.process import run_utf8_process  # noqa: E402


DEFAULT_PROTOCOL = ROOT / "experiments" / "M074" / "SCIENTIFIC_PROTOCOL.json"
DEFAULT_OUTPUT = ROOT / "experiments" / "M074" / "SCIENTIFIC_RESULT.json"


def _load_protocol(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScientificRunnerError(f"scientific protocol could not be loaded: {exc}") from exc
    if not isinstance(value, dict):
        raise ScientificRunnerError("scientific protocol must contain one JSON object")
    return value


def _version(argv: list[str], label: str) -> str:
    completed = run_utf8_process(argv, timeout_seconds=30)
    if completed.returncode != 0:
        raise ScientificRunnerError(f"{label} version command failed")
    value = completed.stdout.strip()
    if not value:
        raise ScientificRunnerError(f"{label} version command returned no identity")
    return value


def _checkpoint(path: Path, payload: Mapping[str, object]) -> None:
    temporary = path.with_name(f".{path.name}.m074-write")
    rendered = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    temporary.write_text(rendered, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def run(protocol_path: Path, output_path: Path) -> dict[str, object]:
    if output_path.exists():
        raise ScientificRunnerError(
            f"scientific output already exists and cannot be resumed or overwritten: {output_path}"
        )
    protocol = _load_protocol(protocol_path)
    validate_protocol(protocol)
    model = protocol["model"]
    budgets = protocol["budgets"]
    runtime = protocol.get("runtime")
    assert isinstance(model, dict) and isinstance(budgets, dict)
    if not isinstance(runtime, dict):
        raise ScientificRunnerError("scientific protocol lacks its runtime identity")

    executable = find_codex_executable()
    if executable is None:
        raise ScientificRunnerError("the frozen M074 run requires the official Codex CLI")
    codex_version = _version([str(executable), "--version"], "Codex CLI")
    if codex_version != model["codex_cli_version"]:
        raise ScientificRunnerError(
            f"Codex CLI drifted: expected {model['codex_cli_version']!r}, observed {codex_version!r}"
        )
    docker_version = _version(
        ["docker", "version", "--format", "{{.Server.Version}}"], "Docker server",
    )
    if docker_version != runtime.get("docker_server_version"):
        raise ScientificRunnerError(
            "Docker server identity differs from the frozen scientific protocol"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mira-m074-neutral-") as raw_workspace:
        backend = CodexExecBackend(
            executable, Path(raw_workspace), str(model["model"]),
            timeout_seconds=float(budgets["codex_decision_timeout_seconds"]),
        )
        result = asyncio.run(execute_campaign(
            protocol, backend, checkpoint=lambda payload: _checkpoint(output_path, payload),
        ))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    try:
        result = run(arguments.protocol.resolve(), arguments.output.resolve())
    except ScientificRunnerError as exc:
        print(f"M074 refused to execute: {exc}", file=sys.stderr)
        return 2
    verdict = result.get("verdict")
    classification = verdict.get("classification") if isinstance(verdict, dict) else "unknown"
    print(json.dumps({
        "status": result.get("status"),
        "classification": classification,
        "output": str(arguments.output.resolve()),
    }, indent=2, sort_keys=True))
    return 0 if result.get("status") == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
