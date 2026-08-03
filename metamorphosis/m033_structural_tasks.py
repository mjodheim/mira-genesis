"""Structurally varied post-migration task controls for M033.

This module exposes three disjoint development-only blocks.  Seeds 2048–3071 retain the
original learned-tool structural calibration, seeds 3072–4095 exercise the combined
memory-and-tool execution path, and seeds 4096+ repeat that comparison with each lineage
anchored on the body it actually migrated.  No block exposes the reserved primary seeds.

The embodied block exists because the first two anchor every lineage on the task's own
baseline source.  Under that anchor the migrated body is never read, so the
unchanged-parent control and the learned-tool ablation present identical surfaces and
Gate 8 loses one of its four required controls.
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
COMBINED_CONTROL_SEED_START = 3072
EMBODIED_CONTROL_SEED_START = 4096
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


@dataclass(frozen=True)
class CombinedControlTaskRecord:
    template_id: int
    task: ControlTask

    def canonical_json(self) -> str:
        return json.dumps(
            {
                "version": "m033-combined-control-task/1",
                "template_id": self.template_id,
                "task": json.loads(self.task.canonical_json()),
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EmbodiedControlTaskRecord:
    template_id: int
    task: ControlTask

    def canonical_json(self) -> str:
        return json.dumps(
            {
                "version": "m033-embodied-control-task/1",
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


def _generate_structural_task(seed: int) -> tuple[int, ControlTask]:
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
    return template_id, task


def generate_structural_control_task(seed: int) -> StructuralTaskRecord:
    """Generate an original structural control task on the closed 2048–3071 block."""

    if seed < STRUCTURAL_CONTROL_SEED_START or seed >= COMBINED_CONTROL_SEED_START:
        raise ValueError("M033 structural controls require a seed from 2048 through 3071")

    template_id, task = _generate_structural_task(seed)
    return StructuralTaskRecord(template_id=template_id, task=task)


def generate_combined_control_task(seed: int) -> CombinedControlTaskRecord:
    """Generate a combined control task on the closed 3072–4095 block."""

    if seed < COMBINED_CONTROL_SEED_START or seed >= EMBODIED_CONTROL_SEED_START:
        raise ValueError("M033 combined controls require a seed from 3072 through 4095")

    template_id, task = _generate_structural_task(seed)
    return CombinedControlTaskRecord(template_id=template_id, task=task)


def generate_embodied_control_task(seed: int) -> EmbodiedControlTaskRecord:
    """Generate a body-anchored control task, rejecting all earlier blocks."""

    if seed < EMBODIED_CONTROL_SEED_START:
        raise ValueError("M033 embodied controls require a seed of at least 4096")

    template_id, task = _generate_structural_task(seed)
    return EmbodiedControlTaskRecord(template_id=template_id, task=task)
