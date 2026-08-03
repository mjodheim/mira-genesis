"""M033 fail-closed transaction for post-migration adaptation controls."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Sequence

from .m020_self_rewrite import Case, evaluate_source
from .m033_memory_controls import execute_memory_guided_task
from .m033_post_migration_plasticity import (
    ControlTask,
    PostMigrationLineage,
    execute_control_task,
)


@dataclass(frozen=True)
class PostMigrationTransaction:
    committed: bool
    reason: str
    task_result_json: str
    lineage_before_sha256: str
    lineage_after_sha256: str
    regression_passed: int
    regression_total: int

    def canonical_json(self) -> str:
        return json.dumps(
            {
                "version": "m033-post-migration-transaction/1",
                "committed": self.committed,
                "reason": self.reason,
                "task_result_json": self.task_result_json,
                "lineage_before_sha256": self.lineage_before_sha256,
                "lineage_after_sha256": self.lineage_after_sha256,
                "regression_passed": self.regression_passed,
                "regression_total": self.regression_total,
            },
            sort_keys=True,
            separators=(",", ":"),
        )


def execute_post_migration_transaction(
    lineage: PostMigrationLineage,
    task: ControlTask,
    regression_cases: Sequence[Case],
    *,
    memory_guided: bool = False,
) -> PostMigrationTransaction:
    """Adapt after migration and commit only if an independent regression gate passes."""

    body_snapshot = (
        lineage.body.active_source,
        list(lineage.body.archive),
        list(lineage.body.adopted_digests),
    )
    learned_snapshot = list(lineage.registry.learned)
    learning_snapshot = lineage.learning_state
    cost_snapshot = lineage.construction_cost
    before_sha256 = lineage.snapshot_sha256()

    def restore() -> None:
        lineage.body.active_source = body_snapshot[0]
        lineage.body.archive[:] = body_snapshot[1]
        lineage.body.adopted_digests[:] = body_snapshot[2]
        lineage.registry.learned[:] = learned_snapshot
        lineage.learning_state = learning_snapshot
        lineage.construction_cost = cost_snapshot

    try:
        if memory_guided:
            result = execute_memory_guided_task(lineage, task)
        else:
            result = execute_control_task(lineage, task)
        regression = evaluate_source(
            result.final_source,
            task.function_name,
            regression_cases,
        )
        committed = bool(result.exact and regression.perfect)
        reason = (
            "post_migration_rewrite_committed"
            if committed
            else "post_migration_regression_gate_failed"
        )
        if not committed:
            restore()
    except Exception:
        restore()
        raise

    after_sha256 = lineage.snapshot_sha256()
    if not committed and after_sha256 != before_sha256:
        raise RuntimeError("M033 rollback did not restore the lineage exactly")

    return PostMigrationTransaction(
        committed=committed,
        reason=reason,
        task_result_json=result.canonical_json(),
        lineage_before_sha256=before_sha256,
        lineage_after_sha256=after_sha256,
        regression_passed=regression.passed,
        regression_total=regression.total,
    )
