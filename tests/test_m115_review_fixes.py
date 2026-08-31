"""Regression coverage for PR #245's fail-closed reveal and abort-checker review fixes."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from metamorphosis import m115_execution as execution
from scripts import check_m115_result as checker
from scripts import run_m115_qualification as runner
from scripts.check_m113_result import digest


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments/M115"


def _load(name: str) -> dict:
    return json.loads((EXPERIMENT / name).read_text(encoding="utf-8"))


def _fixture_context() -> dict[str, dict]:
    return runner._validated_reveal_context()


def _arm_fixture_execution(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path]:
    result_path = tmp_path / "RESULT.json"
    attempt_path = tmp_path / "REVEAL_ATTEMPT.json"
    context = _fixture_context()
    monkeypatch.setattr(runner, "RESULT_PATH", result_path)
    monkeypatch.setattr(runner, "ATTEMPT_PATH", attempt_path)
    monkeypatch.setattr(runner.execution, "readiness", lambda _root: {
        "phase": "reveal_authorized",
        "ready_for_reveal": True,
        "blockers": [],
    })
    monkeypatch.setattr(runner, "_validated_reveal_context", lambda: context)
    return result_path, attempt_path


def test_invalid_json_atomically_consumes_the_reveal_and_persists_terminal_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    result_path, attempt_path = _arm_fixture_execution(monkeypatch, tmp_path)
    decryptions = 0

    def fixture_decrypt() -> bytes:
        nonlocal decryptions
        decryptions += 1
        return b"fixture response bytes, never the sealed H60 bank"

    attestation = _load("DELIVERY_LEDGER.json")["attempts"][0]["identity_attestation"]
    monkeypatch.setattr(runner, "_decrypt_generation_response", fixture_decrypt)
    monkeypatch.setattr(runner, "_parse_committed_response", lambda _raw: ({}, attestation))
    monkeypatch.setattr(
        runner,
        "_extract_payload",
        lambda _response: (_ for _ in ()).throw(
            runner.QualificationError("the materialized completion is not valid JSON")
        ),
    )

    with pytest.raises(runner.QualificationError, match="not valid JSON"):
        runner.execute()

    assert decryptions == 1
    result = json.loads(result_path.read_text(encoding="ascii"))
    attempt = json.loads(attempt_path.read_text(encoding="ascii"))
    assert result["schema"] == checker.TERMINAL_SCHEMA
    assert result["terminal_failure"] == "invalid_json"
    assert result["verdict"] == "instrument-aborted"
    assert result["hypothesis_status"] == "untested"
    assert result["qualification_started"] is False
    assert result["p1_p22"] == {f"P{index}": "not_computed" for index in range(1, 23)}
    assert result["result_digest"] == digest(
        {key: value for key, value in result.items() if key != "result_digest"}
    )
    assert attempt["irreversibly_consumed"] is True
    assert attempt["state"] == "terminal_result_materialized"
    assert attempt["terminal_failure"] == "invalid_json"
    assert attempt["result_digest"] == result["result_digest"]

    with pytest.raises(runner.QualificationError, match="RESULT.json already exists"):
        runner.execute()
    assert decryptions == 1


@pytest.mark.parametrize(
    ("message", "reason"),
    [
        ("the materialized completion is not a JSON object", "output_schema_violation"),
        (
            "response identity attestation does not match its current body",
            "post_decryption_validation_failure",
        ),
    ],
)
def test_other_post_decryption_failures_also_consume_and_materialize(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    message: str,
    reason: str,
) -> None:
    result_path, attempt_path = _arm_fixture_execution(monkeypatch, tmp_path)
    monkeypatch.setattr(
        runner,
        "_decrypt_generation_response",
        lambda: b"fixture response bytes, never the sealed H60 bank",
    )
    monkeypatch.setattr(
        runner,
        "_parse_committed_response",
        lambda _raw: (_ for _ in ()).throw(runner.QualificationError(message)),
    )

    with pytest.raises(runner.QualificationError, match=message):
        runner.execute()

    result = json.loads(result_path.read_text(encoding="ascii"))
    attempt = json.loads(attempt_path.read_text(encoding="ascii"))
    assert result["terminal_failure"] == reason
    assert result["scientific_retry_permitted"] is False
    assert attempt["irreversibly_consumed"] is True
    assert attempt["state"] == "terminal_result_materialized"


def test_a_consumed_marker_alone_refuses_before_any_decryption(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    result_path = tmp_path / "RESULT.json"
    attempt_path = tmp_path / "REVEAL_ATTEMPT.json"
    attempt_path.write_text("{}\n", encoding="ascii")
    monkeypatch.setattr(runner, "RESULT_PATH", result_path)
    monkeypatch.setattr(runner, "ATTEMPT_PATH", attempt_path)
    monkeypatch.setattr(
        runner,
        "_decrypt_generation_response",
        lambda: pytest.fail("a consumed attempt reached decryption"),
    )

    with pytest.raises(runner.QualificationError, match="already consumed"):
        runner.execute()


def test_a_reveal_start_failure_still_consumes_but_does_not_fabricate_an_admission_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    result_path, attempt_path = _arm_fixture_execution(monkeypatch, tmp_path)
    monkeypatch.setattr(
        runner,
        "_decrypt_generation_response",
        lambda: (_ for _ in ()).throw(runner.QualificationError("fixture decryption failure")),
    )

    with pytest.raises(runner.QualificationError, match="fixture decryption failure"):
        runner.execute()

    assert attempt_path.exists()
    assert not result_path.exists()
    with pytest.raises(runner.QualificationError, match="already consumed"):
        runner.execute()


def test_readiness_cannot_return_reveal_authorized_after_a_consumed_marker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "SYSTEM_PROTOCOL.json").write_text("{}", encoding="ascii")
    (tmp_path / "REVEAL_AUTHORIZATION.json").write_text("{}", encoding="ascii")
    (tmp_path / "REVEAL_ATTEMPT.json").write_text("{}", encoding="ascii")
    monkeypatch.setattr(execution, "SYSTEM_PROTOCOL_PATH", Path("SYSTEM_PROTOCOL.json"))
    monkeypatch.setattr(execution, "REVEAL_AUTHORIZATION_PATH", Path("REVEAL_AUTHORIZATION.json"))
    monkeypatch.setattr(execution, "REVEAL_ATTEMPT_PATH", Path("REVEAL_ATTEMPT.json"))
    monkeypatch.setattr(execution, "RESULT_PATH", Path("RESULT.json"))
    monkeypatch.setattr(execution.sealing, "readiness", lambda _root: {
        "phase": "generated_sealed",
        "blockers": [],
    })
    monkeypatch.setattr(execution, "validate_system_protocol", lambda *args, **kwargs: None)
    monkeypatch.setattr(execution, "validate_reveal_authorization", lambda *args, **kwargs: None)

    state = execution.readiness(tmp_path)
    assert state["phase"] == "reveal_consumed"
    assert state["ready_for_reveal"] is False
    assert state["reveal_attempt_consumed"] is True
    assert any("single reveal attempt is consumed" in blocker for blocker in state["blockers"])


def test_terminal_checker_never_delegates_to_m114_qualification_totals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _load("RESULT.json")
    report = _load("CHECK_REPORT.json")
    monkeypatch.setattr(
        checker.predecessor,
        "check",
        lambda _result: pytest.fail("terminal abort delegated to M114 qualification"),
    )

    assert checker.check(result, report) == report
    assert "per_arm_totals" not in result
    assert report["not_computed"] == [f"P{index}" for index in range(1, 23)]


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("schema",), "m115-result-v1"),
        (("milestone",), "M114"),
        (("hypothesis",), "H59"),
        (("terminal_failure",), "output_schema_violation"),
        (("total_carriers",), 1),
        (("qualifying_carriers",), 1),
        (("distinct_qualifying_structures",), 1),
        (("verdict",), "negative"),
        (("p1_p22", "P22"), False),
        (("custody", "plaintext_generation_response_present"), True),
    ],
)
def test_terminal_checker_fails_closed_on_abort_record_drift(
    path: tuple[str, ...],
    replacement: object,
) -> None:
    result = copy.deepcopy(_load("RESULT.json"))
    target: dict = result
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement

    if path == ("schema",):
        with pytest.raises((KeyError, checker.CheckError)):
            checker.check(result, _load("CHECK_REPORT.json"))
    else:
        with pytest.raises(checker.CheckError):
            checker.check(result, _load("CHECK_REPORT.json"))


def test_terminal_checker_requires_exact_independent_replay_equality() -> None:
    report = copy.deepcopy(_load("CHECK_REPORT.json"))
    report["independent_replay"]["terminal_failure"] = "output_schema_violation"
    report["report_digest"] = digest(
        {key: value for key, value in report.items() if key != "report_digest"}
    )
    with pytest.raises(checker.CheckError, match="independent replay"):
        checker.check(_load("RESULT.json"), report)
