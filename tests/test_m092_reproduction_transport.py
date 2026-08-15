"""Pre-arm transport tests for independent M092 reproduction."""
from __future__ import annotations

import json

import pytest

import run_m092_independent_reproduction as runner
from metamorphosis.m092_certificate_verifier import COUNTDOWN_POSTCONDITION
from metamorphosis.m092_criterion_search import CriterionSearchState


def test_reproduction_checkpoint_frequency_does_not_change_trajectory(tmp_path) -> None:
    requirement = COUNTDOWN_POSTCONDITION

    one_chunk_path = tmp_path / "one-chunk.json"
    one_chunk, one_writes = runner.advance_reproduction_with_checkpoints(
        CriterionSearchState.fresh(requirement),
        requirement,
        program_limit=8,
        checkpoint_programs=8,
        output=one_chunk_path,
    )

    chunked_path = tmp_path / "chunked.json"
    chunked, chunked_writes = runner.advance_reproduction_with_checkpoints(
        CriterionSearchState.fresh(requirement),
        requirement,
        program_limit=8,
        checkpoint_programs=1,
        output=chunked_path,
    )

    assert chunked.to_dict() == one_chunk.to_dict()
    assert json.loads(one_chunk_path.read_text(encoding="utf-8")) == one_chunk.to_dict()
    assert json.loads(chunked_path.read_text(encoding="utf-8")) == chunked.to_dict()
    assert one_writes >= 2
    assert chunked_writes >= one_writes


def test_reproduction_checkpoint_exists_before_first_program_can_fail(tmp_path, monkeypatch) -> None:
    requirement = COUNTDOWN_POSTCONDITION
    initial = CriterionSearchState.fresh(requirement)
    checkpoint = tmp_path / "reproduction-checkpoint.json"

    def fail_before_any_completed_program(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("synthetic independent reproduction interruption")

    monkeypatch.setattr(runner, "advance_search", fail_before_any_completed_program)

    with pytest.raises(RuntimeError, match="synthetic independent reproduction interruption"):
        runner.advance_reproduction_with_checkpoints(
            initial,
            requirement,
            program_limit=1,
            checkpoint_programs=1,
            output=checkpoint,
        )

    saved = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert saved == initial.to_dict()
    assert CriterionSearchState.from_dict(saved).to_dict() == initial.to_dict()


def test_reproduction_runner_rejects_nonpositive_checkpoint_width(tmp_path) -> None:
    with pytest.raises(ValueError, match="checkpoint_programs"):
        runner.advance_reproduction_with_checkpoints(
            CriterionSearchState.fresh(COUNTDOWN_POSTCONDITION),
            COUNTDOWN_POSTCONDITION,
            program_limit=1,
            checkpoint_programs=0,
            output=tmp_path / "unused.json",
        )
