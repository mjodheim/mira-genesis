"""Structurally varied post-migration task controls for M033.

This module exposes development-only tasks on seeds 2048+.  It does not expose the
reserved primary block.  Four source scaffolds preserve the pre-migration learned core
rewrite while requiring one additional scaffold-specific post-migration operation.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import random

from .m020_self_rewrite import Case
from .m032_trans_substrate_lifecycle import compile_policy_to_dfa
from .m033_post_migration_plasticity import ControlTask, ControlTaskFamily


STRUCTURAL_CONTROL_SEED_START = 2048
STRUCTURAL_TEMPLATE_COUNT = 4


@dataclass(frozen=True)
class StructuralTaskRecord:
    template_id: int
    task: ControlTask

    def canonical_json(self) -> str:
        return json.dumps(
            {
                "version": "m033-structural-task/1",
                "template_id": self.template_id,
                "task": json.loads(self.task.canonical_json()),
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def _sources(template_id: int) -> tuple[str, str, int]:
    if template_id == 0:
        baseline = """\
def policy(state, symbol):
    return ((state + symbol) % 1) + 0
"""
        target = """\
def policy(state, symbol):
    return ((state * symbol) % 2) + 1
"""
        return baseline, target, 3

    if template_id == 1:
        baseline = """\
def policy(state, symbol):
    value = ((state + symbol) % 1) + 0
    return value + 0
"""
        target = """\
def policy(state, symbol):
    value = ((state * symbol) % 2) + 0
    return value + 1
"""
        return baseline, target, 3

    if template_id == 2:
        baseline = """\
def policy(state, symbol):
    value = ((state + symbol) % 1) + 0
    return value + 1
"""
        target = """\
def policy(state, symbol):
    value = ((state * symbol) % 2) + 0
    return value * 1
"""
        return baseline, target, 2

    if template_id == 3:
        baseline = """\
def policy(state, symbol):
    value = ((state + symbol) % 1) + 0
    return value + 2
"""
        target = """\
def policy(state, symbol):
    value = ((state * symbol) % 2) + 0
    return value % 2
"""
        return baseline, target, 3

    raise ValueError(f"unknown M033 structural template: {template_id}")


def generate_structural_control_task(seed: int) -> StructuralTaskRecord:
    """Generate one structurally varied control task, rejecting all primary seeds."""

    if seed < STRUCTURAL_CONTROL_SEED_START:
        raise ValueError("M033 structural controls require a seed of at least 2048")

    template_id = seed % STRUCTURAL_TEMPLATE_COUNT
    baseline_source, target_source, state_count = _sources(template_id)
    accepting_index = (seed // STRUCTURAL_TEMPLATE_COUNT) % state_count
    accepting_states = tuple(index == accepting_index for index in range(state_count))
    target_dfa = compile_policy_to_dfa(
        target_source,
        "policy",
        state_count=state_count,
        accepting_states=accepting_states,
    )

    development_cases = [
        Case((state, symbol), target_dfa.transitions[state][symbol])
        for state in range(state_count)
        for symbol in (0, 1)
    ]
    rng = random.Random(seed)
    rng.shuffle(development_cases)

    held_out: set[tuple[int, ...]] = set()
    while len(held_out) < 12:
        length = rng.randint(2, 6)
        held_out.add(tuple(rng.randrange(2) for _ in range(length)))

    task = ControlTask(
        seed=seed,
        family=ControlTaskFamily.POSITIVE_TOOL,
        function_name="policy",
        baseline_source=baseline_source,
        target_source=target_source,
        state_count=state_count,
        accepting_states=accepting_states,
        initial_state=0,
        development_cases=tuple(development_cases),
        held_out_words=tuple(sorted(held_out, key=lambda word: (len(word), word))),
        target_dfa=target_dfa,
        max_edits=3,
    )
    return StructuralTaskRecord(template_id=template_id, task=task)
