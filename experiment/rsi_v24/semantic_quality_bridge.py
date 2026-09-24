#!/usr/bin/env python3
"""Root-anchored semantic quality bridge for the next RSI L5 attempt.

V23 fed exact G2 an order-preserving percentile-like tier score. That preserved
candidate ordering, but it did not preserve the semantics of the thresholds G2
had acquired at L4: the causal early-stop predicate best >= 780 never fired on
the discovered successor.

V24 keeps the G2 program byte-identical. Instead, this module maps the public
meta-development utility into three prospectively defined semantic regions:

* utility worse than root G2  -> 0..710   (promising / keep searching)
* utility equal to root G2    -> 750      (neutral grey zone)
* utility strictly above G2   -> 780..1000 (strong successor)

Within the worse and better regions, strict development-utility ordering is
preserved. No fresh holdout outcome is read or used here.
"""
from __future__ import annotations

import importlib.util
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V23 = ROOT / "experiment" / "rsi_v23"

PROMISING_MAX = 710
NEUTRAL_QUALITY = 750
STRONG_THRESHOLD = 780
MAX_QUALITY = 1000


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


family = _load("v24_bridge_family", V23 / "l5_policy_family.py")
dev = _load("v24_bridge_dev", V23 / "l5_meta_development.py")


@lru_cache(maxsize=1)
def _public_universe() -> tuple[dict[str, Any], ...]:
    """Evaluate the complete public universe once per process."""
    return tuple(dev.evaluate_universe())


def _rank_scale(values: tuple[tuple[int, ...], ...], lo: int, hi: int) -> dict[tuple[int, ...], int]:
    """Map sorted unique lexicographic utilities monotonically into [lo, hi]."""
    if not values:
        return {}
    if len(values) == 1:
        return {values[0]: hi}
    span = hi - lo
    denom = len(values) - 1
    return {
        value: lo + (span * index) // denom
        for index, value in enumerate(values)
    }


def _utility_quality_map(rows: tuple[dict[str, Any], ...]) -> dict[tuple[int, ...], int]:
    root_digest = family.params_digest(family.ROOT_PARAMS)
    root_rows = [row for row in rows if row["params_digest"] == root_digest]
    if len(root_rows) != 1:
        raise RuntimeError("exactly one G2 root candidate is required")
    root_utility = tuple(root_rows[0]["development_utility"])

    unique = tuple(sorted({tuple(row["development_utility"]) for row in rows}))
    worse = tuple(value for value in unique if value < root_utility)
    better = tuple(value for value in unique if value > root_utility)

    mapping: dict[tuple[int, ...], int] = {}
    mapping.update(_rank_scale(worse, 0, PROMISING_MAX))
    mapping[root_utility] = NEUTRAL_QUALITY
    mapping.update(_rank_scale(better, STRONG_THRESHOLD, MAX_QUALITY))

    if set(mapping) != set(unique):
        raise RuntimeError("semantic bridge failed to cover the complete public utility set")
    for utility, quality in mapping.items():
        if utility < root_utility and not 0 <= quality <= PROMISING_MAX:
            raise RuntimeError("worse-than-root utility escaped the promising region")
        if utility == root_utility and quality != NEUTRAL_QUALITY:
            raise RuntimeError("root-equivalent utility escaped the neutral region")
        if utility > root_utility and not STRONG_THRESHOLD <= quality <= MAX_QUALITY:
            raise RuntimeError("strict successor utility escaped the strong region")
    return mapping


def utility_quality_map() -> dict[tuple[int, ...], int]:
    """Return the public utility -> semantic quality mapping."""
    return _utility_quality_map(_public_universe())


def root_utility() -> tuple[int, ...]:
    rows = _public_universe()
    root_digest = family.params_digest(family.ROOT_PARAMS)
    row = next(row for row in rows if row["params_digest"] == root_digest)
    return tuple(row["development_utility"])


def bridge_candidate(
    candidate: Mapping[str, Any],
    mapping: Mapping[tuple[int, ...], int] | None = None,
) -> dict[str, Any]:
    """Copy one public candidate and replace only its controller-facing score."""
    utility = tuple(candidate["development_utility"])
    quality_map = utility_quality_map() if mapping is None else mapping
    if utility not in quality_map:
        raise ValueError("candidate utility is outside the frozen public development universe")
    out = dict(candidate)
    out["v23_tier_quality_milli"] = int(candidate["quality_milli"])
    out["quality_milli"] = int(quality_map[utility])
    return out


def bridged_universe() -> tuple[dict[str, Any], ...]:
    rows = _public_universe()
    mapping = _utility_quality_map(rows)
    bridged = tuple(bridge_candidate(row, mapping) for row in rows)
    return tuple(sorted(bridged, key=lambda row: row["params_digest"]))
