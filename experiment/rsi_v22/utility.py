#!/usr/bin/env python3
"""Frozen V22 utility. No task semantics or evaluator cases are encoded here."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class TaskOutcome:
    best_quality_milli: int
    represented_requests: int
    rounds: int
    solved_without_regression: bool

    def process_utility(self) -> tuple[int, int, int]:
        return (
            int(self.best_quality_milli),
            -int(self.represented_requests),
            -int(self.rounds),
        )


def global_utility(outcomes: Iterable[TaskOutcome]) -> tuple[int, int, int, int]:
    rows = tuple(outcomes)
    return (
        sum(int(row.solved_without_regression) for row in rows),
        sum(int(row.best_quality_milli) for row in rows),
        -sum(int(row.represented_requests) for row in rows),
        -sum(int(row.rounds) for row in rows),
    )


def strictly_better(a: tuple[int, ...], b: tuple[int, ...]) -> bool:
    return a > b
