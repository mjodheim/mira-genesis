#!/usr/bin/env python3
"""Execute the frozen M073 teacher requests in a neutral Codex workspace.

This script deliberately does not import the M073 skill induction module.  The external model sees
only the frozen instruction, public examples and one training source module at a time.  It never
receives repository context or holdout content.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Callable, Mapping

from mira_core.model import find_codex_executable
from mira_core.process import run_utf8_process


ROOT = Path(__file__).resolve().parents[1]
REQUESTS_PATH = ROOT / "experiments" / "M073" / "TEACHER_REQUESTS.json"
OUTPUT_PATH = ROOT / "experiments" / "M073" / "TEACHER_RESPONSES.json"


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_requests(path: Path = REQUESTS_PATH) -> dict[str, object]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if value.get("schema") != "m073-teacher-request-set-v1":
        raise ValueError("unexpected M073 teacher-request schema")
    if value.get("status") != "frozen_before_any_teacher_response":
        raise ValueError("M073 teacher requests are not frozen")
    if value.get("teacher_responses_exist") is not False:
        raise ValueError("M073 teacher request artifact already claims responses")
    requests = value.get("requests")
    if not isinstance(requests, list) or len(requests) != 4:
        raise ValueError("M073 requires exactly four teacher requests")
    if any(request.get("teacher_response_sha256") is not None for request in requests):
        raise ValueError("M073 frozen teacher requests already contain a response")
    return value


def build_prompt(request_set: Mapping[str, object], request: Mapping[str, object]) -> str:
    instruction = request_set.get("instruction")
    public_cases = request_set.get("public_cases")
    source = request.get("source")
    if not isinstance(instruction, str) or not isinstance(public_cases, list):
        raise ValueError("M073 teacher request instruction/public cases are malformed")
    if not isinstance(source, str):
        raise ValueError("M073 teacher request source is malformed")
    cases = json.dumps(public_cases, sort_keys=True, separators=(",", ":"))
    return (
        "M073 EXTERNAL TEACHER REQUEST\n"
        f"{instruction}\n\n"
        f"PUBLIC_CASES_JSON\n{cases}\n\n"
        f"SOURCE_MODULE\n{source}"
    )


def _validate_raw_response(response: str) -> str:
    normalized = response.strip() + "\n"
    if "```" in normalized:
        raise ValueError("teacher response contains forbidden markdown fences")
    if not normalized.startswith("def "):
        raise ValueError("teacher response is not a complete Python function module")
    try:
        compile(normalized, "<m073-teacher-response>", "exec", dont_inherit=True)
    except SyntaxError as exc:
        raise ValueError("teacher response is not valid Python") from exc
    return normalized


def collect_responses(
    request_set: Mapping[str, object], *, executable: Path, neutral_workspace: Path,
    timeout_seconds: float = 180.0,
    process_runner: Callable[..., object] = run_utf8_process,
) -> dict[str, object]:
    teacher = request_set["teacher"]
    if not isinstance(teacher, dict):
        raise ValueError("M073 teacher identity is malformed")
    model = teacher.get("model")
    if model != "gpt-5.6-sol":
        raise ValueError("M073 teacher model differs from the frozen identity")
    requests = request_set["requests"]
    assert isinstance(requests, list)
    records: list[dict[str, object]] = []
    for request in requests:
        if not isinstance(request, dict):
            raise ValueError("M073 teacher request entry is malformed")
        prompt = build_prompt(request_set, request)
        with tempfile.TemporaryDirectory(prefix="mira-m073-teacher-output-") as raw_temp:
            output_path = Path(raw_temp) / "teacher.txt"
            argv = [
                str(executable), "exec", "--ephemeral", "--ignore-user-config", "--ignore-rules",
                "--skip-git-repo-check", "--sandbox", "read-only", "--model", str(model),
                "--cd", str(neutral_workspace.resolve()),
                "--output-last-message", str(output_path), "-",
            ]
            completed = process_runner(
                argv, input_text=prompt, timeout_seconds=timeout_seconds,
            )
            returncode = int(getattr(completed, "returncode"))
            if returncode != 0:
                detail = str(getattr(completed, "stderr", "") or getattr(completed, "stdout", ""))
                raise RuntimeError(
                    f"M073 teacher call {request['call_index']} failed with {returncode}: {detail[-1000:]}"
                )
            if not output_path.is_file():
                raise RuntimeError("M073 teacher did not produce its declared output")
            response = _validate_raw_response(output_path.read_text(encoding="utf-8"))
        records.append({
            "call_index": request["call_index"],
            "task_id": request["task_id"],
            "source_sha256": request["source_sha256"],
            "prompt_sha256": _sha256_text(prompt),
            "response": response,
            "response_sha256": _sha256_text(response),
        })
    return {
        "schema": "m073-teacher-response-set-v1",
        "status": "four_frozen_teacher_calls_completed",
        "request_set_commit": "521895af33e30320c06437d4d9fbd83dee581a47",
        "model": model,
        "call_count": len(records),
        "scientific_retries": 0,
        "neutral_workspace": True,
        "repository_context_visible_to_teacher": False,
        "skill_induction_implementation_visible_to_teacher": False,
        "holdout_content_visible_to_teacher": False,
        "responses": records,
        "capsule_exists": False,
        "holdout_materialized": False,
        "scientific_result_exists": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=Path, default=REQUESTS_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    args = parser.parse_args()
    if Path(args.output).exists():
        raise SystemExit("M073 teacher-response output already exists; refusing overwrite")
    executable = find_codex_executable()
    if executable is None:
        raise SystemExit("official Codex CLI is unavailable on PATH")
    with tempfile.TemporaryDirectory(prefix="mira-m073-neutral-teacher-") as directory:
        responses = collect_responses(
            load_requests(Path(args.requests)), executable=executable,
            neutral_workspace=Path(directory), timeout_seconds=args.timeout_seconds,
        )
    Path(args.output).write_text(
        json.dumps(responses, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        "call_count": responses["call_count"],
        "model": responses["model"],
        "output": str(Path(args.output)),
        "status": responses["status"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
