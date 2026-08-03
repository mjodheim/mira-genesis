"""Frozen comparison primitives for M033 combined control calibration.

These functions compare already-produced public result payloads.  They never construct
or reveal tasks and therefore cannot reach the reserved primary seed block.
"""

from __future__ import annotations

from collections.abc import Mapping


def comparison_key(result: Mapping[str, object]) -> tuple[int, int, int]:
    """Order quality first and deterministic search cost only at equal quality."""

    return (
        int(bool(result["exact"])),
        int(result["held_out_quality_per_mille"]),
        -int(result["total_candidate_evaluations"]),
    )


def paired_outcome(
    complete: Mapping[str, object],
    control: Mapping[str, object],
) -> int:
    """Return 1 for a complete-lineage win, 0 for a tie and -1 for a loss."""

    complete_key = comparison_key(complete)
    control_key = comparison_key(control)
    return (complete_key > control_key) - (complete_key < control_key)
