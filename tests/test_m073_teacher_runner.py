from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

import run_m073_teacher as teacher_runner


ROOT = Path(__file__).resolve().parents[1]
EXECUTION_PROTOCOL = ROOT / "experiments" / "M073" / "TEACHER_EXECUTION_PROTOCOL.json"


def test_teacher_execution_protocol_is_pre_call_and_single_attempt() -> None:
    protocol = json.loads(EXECUTION_PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["schema"] == "m073-teacher-execution-protocol-v1"
    assert protocol["status"] == "frozen_before_any_teacher_call"
    assert protocol["teacher_runner_commit"] == "4351fc007a95d341b017e10511de730e20651947"
    assert protocol["request_set_commit"] == "521895af33e30320c06437d4d9fbd83dee581a47"
    assert protocol["calls"]["count"] == 4
    assert protocol["calls"]["attempts_per_task"] == 1
    assert protocol["calls"]["scientifically_valid_retry_permitted"] is False
    assert protocol["calls"]["replacement_permitted"] is False
    assert protocol["teacher_context"]["repository_visible"] is False
    assert protocol["teacher_context"]["skill_induction_implementation_visible"] is False
    assert protocol["teacher_context"]["holdout_content_visible"] is False
    assert protocol["teacher_calls_executed"] is False
    assert protocol["teacher_responses_exist"] is False


def test_teacher_runner_source_does_not_import_skill_induction_or_holdout_artifact() -> None:
    source = (ROOT / "scripts" / "run_m073_teacher.py").read_text(encoding="utf-8")
    assert "mira_core.skills" not in source
    assert "TRAINING_TASKS.json" not in source
    assert "HOLDOUT_TASKS.json" not in source
    assert "TEACHER_REQUESTS.json" in source


def test_frozen_teacher_prompt_contains_only_declared_inputs() -> None:
    request_set = teacher_runner.load_requests()
    first = request_set["requests"][0]
    prompt = teacher_runner.build_prompt(request_set, first)
    assert "M073 EXTERNAL TEACHER REQUEST" in prompt
    assert first["source"] in prompt
    assert "PUBLIC_CASES_JSON" in prompt
    assert "mira_core" not in prompt
    assert "source_pattern" not in prompt
    assert "target_template" not in prompt
    assert "holdout" not in prompt.lower()


def test_teacher_runner_collects_four_raw_responses_in_neutral_workspace(tmp_path: Path) -> None:
    request_set = teacher_runner.load_requests()
    executable = tmp_path / "codex"
    executable.write_text("fixture", encoding="utf-8")
    calls: list[tuple[list[str], str]] = []

    def fake_runner(argv, *, input_text, timeout_seconds):
        calls.append((list(argv), input_text))
        output_path = Path(argv[argv.index("--output-last-message") + 1])
        source_start = input_text.index("SOURCE_MODULE\n") + len("SOURCE_MODULE\n")
        source = input_text[source_start:]
        head, return_line = source.rsplit("    return ", 1)
        expression = return_line.strip()
        denominator = expression.split(" / ", 1)[1]
        repaired = head + (
            f"    return {expression} if {denominator} != 0 else 0\n"
        )
        output_path.write_text(repaired, encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, "", "")

    neutral = tmp_path / "neutral"
    neutral.mkdir()
    result = teacher_runner.collect_responses(
        request_set, executable=executable, neutral_workspace=neutral,
        process_runner=fake_runner,
    )
    assert result["model"] == "gpt-5.6-sol"
    assert result["call_count"] == 4
    assert result["scientific_retries"] == 0
    assert result["repository_context_visible_to_teacher"] is False
    assert result["skill_induction_implementation_visible_to_teacher"] is False
    assert result["holdout_content_visible_to_teacher"] is False
    assert result["capsule_exists"] is False
    assert result["holdout_materialized"] is False
    assert len(calls) == 4
    assert all("--sandbox" in argv and "read-only" in argv for argv, _ in calls)
    assert all("--model" in argv and "gpt-5.6-sol" in argv for argv, _ in calls)
    assert all("mira_core" not in prompt for _, prompt in calls)


def test_teacher_response_contract_rejects_markdown_and_non_python() -> None:
    with pytest.raises(ValueError, match="markdown"):
        teacher_runner._validate_raw_response("```python\ndef x(a,b): return 0\n```")
    with pytest.raises(ValueError, match="complete Python"):
        teacher_runner._validate_raw_response("Here is the fix")
