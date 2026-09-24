#!/usr/bin/env python3
"""Finite, content-addressed V23 L5 descendant family around exact frozen G2.

The root source is the exact V22/V22R G2 policy. Descendants may change only
six numeric control parameters already present in that source. The grammar is
finite and frozen before any L5 meta-search is executed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
ROOT_G2 = HERE.parent / "rsi_v22" / "policies" / "g2_search_policy.py"

ROOT_SHA256 = "69d0d725601cd32adff27379dbb25f5c7be29946f9e9c6ac4858a0634cbd5fdf"

AXES: dict[str, tuple[int, ...]] = {
    "stop_quality": (700, 740, 780, 820, 860, 900),
    "promising_quality_max": (630, 670, 710, 750, 790),
    "deep_min_depth": (1, 2, 3),
    "parallelism": (1, 2),
    "max_rounds": (6, 7, 8, 9, 10),
    "stall_rounds": (1, 2, 3, 4),
}
ROOT_PARAMS = {
    "stop_quality": 780,
    "promising_quality_max": 710,
    "deep_min_depth": 2,
    "parallelism": 1,
    "max_rounds": 8,
    "stall_rounds": 3,
}

_METADATA_ROOT = "return (10, 6, 3, 5, 5, 4, 8, 1, 8, 3)"
_STOP_ROOT = "if best >= 780:"
_DEEP_ROOT = 'if int(row["lineage_depth"]) >= 2]'
_PROMISING_ROOT = 'if int(row["outcome"]["quality_milli"]) <= 710'


class L5PolicyFamilyError(ValueError):
    pass


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def params_digest(params: Mapping[str, int]) -> str:
    validated = validate_params(params)
    return hashlib.sha256(_canonical_bytes(validated)).hexdigest()


def validate_params(params: Mapping[str, int]) -> dict[str, int]:
    if set(params) != set(AXES):
        raise L5PolicyFamilyError("candidate parameters do not match frozen L5 axes")
    out: dict[str, int] = {}
    for key, values in AXES.items():
        value = params[key]
        if type(value) is not int or value not in values:
            raise L5PolicyFamilyError(f"{key}={value!r} is outside frozen L5 values")
        out[key] = value
    return out


def root_source() -> str:
    raw = ROOT_G2.read_text(encoding="utf-8")
    got = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    if got != ROOT_SHA256:
        raise L5PolicyFamilyError(f"frozen G2 bytes changed: {got} != {ROOT_SHA256}")
    return raw


def render_source(params: Mapping[str, int]) -> str:
    p = validate_params(params)
    src = root_source()
    metadata = (
        "return (10, 6, 3, 5, 5, 4, 8, "
        f"{p['parallelism']}, {p['max_rounds']}, {p['stall_rounds']})"
    )
    replacements = (
        (_METADATA_ROOT, metadata),
        (_STOP_ROOT, f"if best >= {p['stop_quality']}:"),
        (_DEEP_ROOT, f'if int(row["lineage_depth"]) >= {p["deep_min_depth"]}]'),
        (_PROMISING_ROOT, f'if int(row["outcome"]["quality_milli"]) <= {p["promising_quality_max"]}'),
    )
    # Correct the two bracket-bearing replacements explicitly to avoid a template
    # language that could change anything except the frozen integer literals.
    replacements = (
        (_METADATA_ROOT, metadata),
        (_STOP_ROOT, f"if best >= {p['stop_quality']}:"),
        ('if int(row["lineage_depth"]) >= 2]', f'if int(row["lineage_depth"]) >= {p["deep_min_depth"]}]'),
        ('if int(row["outcome"]["quality_milli"]) <= 710', f'if int(row["outcome"]["quality_milli"]) <= {p["promising_quality_max"]}'),
    )
    for old, new in replacements:
        if src.count(old) != 1:
            raise L5PolicyFamilyError(f"frozen source marker is not unique: {old!r}")
        src = src.replace(old, new)
    if p == ROOT_PARAMS and hashlib.sha256(src.encode()).hexdigest() != ROOT_SHA256:
        raise L5PolicyFamilyError("root rendering is not byte-identical to frozen G2")
    return src


def source_sha256(params: Mapping[str, int]) -> str:
    return hashlib.sha256(render_source(params).encode("utf-8")).hexdigest()


def neighbors(params: Mapping[str, int]) -> tuple[dict[str, Any], ...]:
    current = validate_params(params)
    rows: list[dict[str, Any]] = []
    for axis in sorted(AXES):
        values = AXES[axis]
        index = values.index(current[axis])
        for next_index in (index - 1, index + 1):
            if not 0 <= next_index < len(values):
                continue
            child = dict(current)
            child[axis] = values[next_index]
            rows.append(
                {
                    "axis": axis,
                    "from": current[axis],
                    "to": child[axis],
                    "params": child,
                    "params_digest": params_digest(child),
                    "source_sha256": source_sha256(child),
                }
            )
    rows.sort(key=lambda row: (row["axis"], row["to"], row["source_sha256"]))
    return tuple(rows)


def universe(max_mutation_depth: int = 2) -> tuple[dict[str, Any], ...]:
    if max_mutation_depth < 0:
        raise L5PolicyFamilyError("mutation depth may not be negative")
    seen = {params_digest(ROOT_PARAMS): (dict(ROOT_PARAMS), 0)}
    queue = [(dict(ROOT_PARAMS), 0)]
    while queue:
        parent, depth = queue.pop(0)
        if depth >= max_mutation_depth:
            continue
        for row in neighbors(parent):
            digest = row["params_digest"]
            if digest in seen:
                continue
            child = dict(row["params"])
            seen[digest] = (child, depth + 1)
            queue.append((child, depth + 1))
    out = []
    for digest, (params, depth) in seen.items():
        out.append(
            {
                "params": params,
                "params_digest": digest,
                "source_sha256": source_sha256(params),
                "mutation_depth": depth,
            }
        )
    out.sort(key=lambda row: (row["mutation_depth"], row["params_digest"]))
    return tuple(out)
