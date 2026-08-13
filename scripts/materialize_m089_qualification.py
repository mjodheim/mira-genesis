"""Materialize M089's qualifying tasks in a SEPARATE process, after the language is extended.

PR #136 found the M086-A defect in M088's first draft: the qualification pool sat in a module the
lineage imported, so every possible qualifying case existed in the development process before
adoption. The pool therefore lives here, in a script nothing under `metamorphosis/` imports, and is
drawn by a process the lineage never runs.

Tasks are behaviours rather than programs, so they are drawn as **specifications** and rebuilt by
`task_from_spec`. No specification names an operation, a primitive or a program: each states only
what the finished transformation must do.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ARTIFACT_SCHEMA = "m089-qualification-v1"

# Two materially different structures, neither of which is the development case.
#
# `composed_combination` needs the acquired operation followed by a unary — the primitive composed
# with an existing one. `repeated_combination` needs it twice over different operands, writing two
# slots. Both are stated as target behaviour; neither mentions any operation.
QUALIFICATION_POOL: dict[str, tuple[dict[str, object], ...]] = {
    "composed_combination": (
        {"task_id": "q_composed_neg_30", "family": "composed_combination",
         "kind": "sum_then_unary", "slot": 3, "left": 0, "right": 2, "function": "neg"},
        {"task_id": "q_composed_dbl_12", "family": "composed_combination",
         "kind": "sum_then_unary", "slot": 1, "left": 0, "right": 1, "function": "double"},
        {"task_id": "q_composed_neg_21", "family": "composed_combination",
         "kind": "sum_then_unary", "slot": 2, "left": 1, "right": 2, "function": "neg"},
    ),
    "repeated_combination": (
        {"task_id": "q_repeated_a", "family": "repeated_combination", "kind": "two_sums",
         "first": [0, 0, 1], "second": [2, 1, 2]},
        {"task_id": "q_repeated_b", "family": "repeated_combination", "kind": "two_sums",
         "first": [1, 0, 2], "second": [3, 1, 2]},
        {"task_id": "q_repeated_c", "family": "repeated_combination", "kind": "two_sums",
         "first": [2, 0, 1], "second": [3, 0, 2]},
    ),
}

# Inputs the lineage never searches against. The evaluator holds these.
HIDDEN_INPUT_POOL = (
    (7, 3, 5), (-1, 8, 2), (4, 0, 9), (6, 6, 1), (-3, 2, 11), (10, 5, 0),
)


def _order(items: int, salt: str, tag: str) -> list[int]:
    return sorted(
        range(items),
        key=lambda index: hashlib.sha256(
            f"m089-qualification-v1|{tag}|{salt}|{index}".encode("utf-8")
        ).hexdigest(),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salt", required=True)
    parser.add_argument("--language-digest", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()

    specs = []
    for family, pool in sorted(QUALIFICATION_POOL.items()):
        chosen = _order(len(pool), arguments.salt, family)[0]
        specs.append(pool[chosen])
    hidden_order = _order(len(HIDDEN_INPUT_POOL), arguments.salt, "hidden")[:3]
    artifact = {
        "schema": ARTIFACT_SCHEMA,
        "salt_digest": hashlib.sha256(
            json.dumps(arguments.salt, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "extended_language_digest": arguments.language_digest,
        "materialized_by": "separate process",
        "specifications": specs,
        "hidden_inputs": [list(HIDDEN_INPUT_POOL[index]) for index in sorted(hidden_order)],
    }
    artifact["artifact_digest"] = hashlib.sha256(
        json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    destination = Path(arguments.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(
        json.dumps(artifact, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    )
    print(artifact["artifact_digest"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
