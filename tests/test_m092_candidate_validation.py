"""M092-B candidate validation stays structural, target-neutral and fail-closed."""
from __future__ import annotations

import ast
import copy
from pathlib import Path

from metamorphosis.m092_candidate_validation import (
    ALLOWED_OPCODES,
    CANDIDATE_LITERAL_SET,
    FORBIDDEN_OPCODES,
    run_anti_cheating_selftest,
    validate_candidate_artifacts,
)
from metamorphosis.m092_kernel import INSTRUCTION_SET, Program, program_digest


COUNTDOWN: Program = (
    ("SPOP", 0),
    ("LOADI", 1, 1),
    ("JZ", 0, 5),
    ("SUB", 0, 0, 1),
    ("JMP", 2),
    ("SPUSH", 0),
    ("HALT",),
)


def _certificate(program: Program = COUNTDOWN) -> dict[str, object]:
    return {"program_digest": program_digest(program), "obligations": []}


def test_clean_neutral_candidate_passes_without_execution() -> None:
    report = validate_candidate_artifacts(COUNTDOWN, _certificate())
    assert report["accepted"] is True
    assert report["candidate_executed"] is False
    assert report["qualification_read"] is False
    assert report["structural_findings"]["refusals"] == []
    assert report["anti_cheating_findings"]["refusals"] == []


def test_all_five_frozen_positive_controls_refuse_and_restore_clean_state() -> None:
    report = run_anti_cheating_selftest()
    assert report["all_five_rejected"] is True
    assert report["clean_state_restored"] is True
    assert report["clean_candidate_accepted_after_fixtures"] is True
    assert [item["fixture"] for item in report["fixtures"]] == [
        "direct output table",
        "encoded bit mask",
        "equality-chain lookup",
        "host callback",
        "wrong-program-digest certificate",
    ]
    assert all(item["rejected"] for item in report["fixtures"])


def test_callback_is_detected_but_never_called() -> None:
    calls = 0

    def callback(_: int) -> int:
        nonlocal calls
        calls += 1
        return 0

    report = validate_candidate_artifacts(
        COUNTDOWN, _certificate(), support_artifacts=[{"host_callback": callback}],
    )
    assert report["accepted"] is False
    assert calls == 0
    assert "host_callback_or_import" in {
        item["code"] for item in report["anti_cheating_findings"]["refusals"]
    }


def test_wrong_digest_refuses_even_when_every_scan_is_clean() -> None:
    certificate = _certificate()
    certificate["program_digest"] = "0" * 64
    report = validate_candidate_artifacts(COUNTDOWN, certificate)
    assert report["accepted"] is False
    assert report["anti_cheating_findings"]["refusals"] == []
    assert report["structural_findings"]["refusals"] == [{
        "code": "wrong_program_digest",
        "path": "certificate.program_digest",
        "detail": "certificate digest differs from the exact canonical K1 program",
    }]


def test_scanner_report_is_deterministic_and_does_not_mutate_inputs() -> None:
    certificate = _certificate()
    artifacts = [{"search_statistics": {"generated": 17, "survivors": 1}}]
    before_certificate = copy.deepcopy(certificate)
    before_artifacts = copy.deepcopy(artifacts)
    first = validate_candidate_artifacts(COUNTDOWN, certificate, support_artifacts=artifacts)
    second = validate_candidate_artifacts(COUNTDOWN, certificate, support_artifacts=artifacts)
    assert first == second
    assert certificate == before_certificate
    assert artifacts == before_artifacts


def test_frozen_opcode_and_literal_partitions_are_exact() -> None:
    assert set(ALLOWED_OPCODES) | set(FORBIDDEN_OPCODES) == set(INSTRUCTION_SET)
    assert not set(ALLOWED_OPCODES) & set(FORBIDDEN_OPCODES)
    assert CANDIDATE_LITERAL_SET == (-1, 0, 1)


def test_forbidden_literal_and_host_opcode_fail_structurally() -> None:
    forbidden_literal: Program = (("LOADI", 0, 2), ("HALT",))
    literal_report = validate_candidate_artifacts(
        forbidden_literal, _certificate(forbidden_literal),
    )
    assert {item["code"] for item in literal_report["structural_findings"]["refusals"]} == {
        "forbidden_literal",
    }

    host_channel: Program = (("ARG", 0), ("SPUSH", 0), ("HALT",))
    host_report = validate_candidate_artifacts(host_channel, _certificate(host_channel))
    assert {item["code"] for item in host_report["structural_findings"]["refusals"]} == {
        "forbidden_opcode",
    }


def test_malformed_candidate_refuses_without_crashing_or_execution() -> None:
    malformed: Program = ((),)
    report = validate_candidate_artifacts(malformed, {"program_digest": "0" * 64})
    assert report["accepted"] is False
    assert report["candidate_executed"] is False
    assert {item["code"] for item in report["structural_findings"]["refusals"]} == {
        "forbidden_opcode",
        "malformed_program",
        "wrong_program_digest",
    }


def test_scanner_project_import_boundary_is_kernel_and_runtime_only() -> None:
    import metamorphosis.m092_candidate_validation as module

    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    project_imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("metamorphosis")
    }
    assert project_imports == {
        "metamorphosis.m092_kernel",
        "metamorphosis.m092_runtime",
    }
