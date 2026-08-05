"""Exactly certified Mealy rewrite language for M043 qualification gate Q2.

The language is intentionally independent from the executable DFA rewrite macros used by
M039--M042. Every accepted operation carries an exact structural/behavioural certificate,
and every trace is bound to one concrete indexed parent body for deterministic replay.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Mapping, Sequence, TypeAlias

from metamorphosis.m043_mealy import (
    MealyMachine,
    Word,
    canonicalize_mealy,
    exact_mealy_equivalence,
    mealy_digest,
)

TRACE_VERSION = "m043-mealy-rewrite-trace-v1"


class RewriteError(ValueError):
    """Raised when a rewrite, certificate or trace violates the Q2 contract."""


class EffectKind(str, Enum):
    REACHABLE_CAPACITY_GROWTH = "reachable_capacity_growth"
    FIXED_CAPACITY_OUTPUT_EDIT = "fixed_capacity_output_edit"
    FIXED_CAPACITY_TRANSITION_EDIT = "fixed_capacity_transition_edit"
    UNREACHABLE_CAPACITY_COMPACTION = "unreachable_capacity_compaction"


def _integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RewriteError(f"{field} must be an integer")
    return value


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise RewriteError(f"{field} must be an object")
    return value


def _sequence(value: object, field: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise RewriteError(f"{field} must be a sequence")
    return value


def _fields(data: Mapping[str, object], required: set[str], field: str) -> None:
    if set(data) != required:
        missing = sorted(required - set(data))
        extra = sorted(set(data) - required)
        raise RewriteError(f"invalid {field} fields: missing={missing}, extra={extra}")


def _digest(value: object, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise RewriteError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _state(machine: MealyMachine, value: int, field: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value < machine.n_states
    ):
        raise RewriteError(f"{field} is not a valid state")
    return value


def _symbol_index(machine: MealyMachine, symbol: int) -> int:
    if isinstance(symbol, bool) or not isinstance(symbol, int):
        raise RewriteError("input_symbol must be an integer")
    try:
        return machine.input_alphabet.index(symbol)
    except ValueError as exc:
        raise RewriteError(f"unknown input symbol: {symbol}") from exc


def reachable_states(machine: MealyMachine) -> frozenset[int]:
    seen = {machine.initial}
    queue = deque([machine.initial])
    while queue:
        state = queue.popleft()
        for target in machine.transitions[state]:
            if target not in seen:
                seen.add(target)
                queue.append(target)
    return frozenset(seen)


def exact_body_bytes(machine: MealyMachine) -> bytes:
    """Encode the exact indexed body, including unreachable storage.

    Q1 identities intentionally ignore pure state renaming and unreachable states. Q2
    operations refer to concrete state indices, so trace replay must instead bind to the
    exact declared body.
    """

    return json.dumps(
        machine.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def exact_body_digest(machine: MealyMachine) -> str:
    domain = b"m043-exact-rewrite-body-v1\x00"
    return hashlib.sha256(domain + exact_body_bytes(machine)).hexdigest()


@dataclass(frozen=True)
class DuplicateReachableTarget:
    """Clone one transition target and redirect that entry arc to the clone."""

    entry_state: int
    input_symbol: int
    effect_kind = EffectKind.REACHABLE_CAPACITY_GROWTH

    def to_dict(self) -> dict[str, object]:
        return {
            "op": "duplicate_reachable_target",
            "entry_state": self.entry_state,
            "input_symbol": self.input_symbol,
        }


@dataclass(frozen=True)
class ReplaceEmission:
    state: int
    input_symbol: int
    output_symbol: int
    effect_kind = EffectKind.FIXED_CAPACITY_OUTPUT_EDIT

    def to_dict(self) -> dict[str, object]:
        return {
            "op": "replace_emission",
            "state": self.state,
            "input_symbol": self.input_symbol,
            "output_symbol": self.output_symbol,
        }


@dataclass(frozen=True)
class RedirectTransition:
    state: int
    input_symbol: int
    target_state: int
    effect_kind = EffectKind.FIXED_CAPACITY_TRANSITION_EDIT

    def to_dict(self) -> dict[str, object]:
        return {
            "op": "redirect_transition",
            "state": self.state,
            "input_symbol": self.input_symbol,
            "target_state": self.target_state,
        }


@dataclass(frozen=True)
class PruneUnreachable:
    effect_kind = EffectKind.UNREACHABLE_CAPACITY_COMPACTION

    def to_dict(self) -> dict[str, object]:
        return {"op": "prune_unreachable"}


RewriteOperation: TypeAlias = (
    DuplicateReachableTarget | ReplaceEmission | RedirectTransition | PruneUnreachable
)


def operation_from_dict(data: Mapping[str, object]) -> RewriteOperation:
    raw = _mapping(data, "operation")
    op = raw.get("op")
    if op == "duplicate_reachable_target":
        _fields(raw, {"op", "entry_state", "input_symbol"}, "duplicate operation")
        return DuplicateReachableTarget(
            _integer(raw["entry_state"], "entry_state"),
            _integer(raw["input_symbol"], "input_symbol"),
        )
    if op == "replace_emission":
        _fields(
            raw,
            {"op", "state", "input_symbol", "output_symbol"},
            "emission operation",
        )
        return ReplaceEmission(
            _integer(raw["state"], "state"),
            _integer(raw["input_symbol"], "input_symbol"),
            _integer(raw["output_symbol"], "output_symbol"),
        )
    if op == "redirect_transition":
        _fields(
            raw,
            {"op", "state", "input_symbol", "target_state"},
            "transition operation",
        )
        return RedirectTransition(
            _integer(raw["state"], "state"),
            _integer(raw["input_symbol"], "input_symbol"),
            _integer(raw["target_state"], "target_state"),
        )
    if op == "prune_unreachable":
        _fields(raw, {"op"}, "prune operation")
        return PruneUnreachable()
    raise RewriteError(f"unknown rewrite operation: {op!r}")


def _replace_cell(
    rows: tuple[tuple[int, ...], ...], state: int, index: int, value: int
) -> tuple[tuple[int, ...], ...]:
    changed = [list(row) for row in rows]
    changed[state][index] = value
    return tuple(tuple(row) for row in changed)


def _apply(machine: MealyMachine, operation: RewriteOperation) -> MealyMachine:
    reachable = reachable_states(machine)

    if isinstance(operation, DuplicateReachableTarget):
        entry = _state(machine, operation.entry_state, "entry_state")
        if entry not in reachable:
            raise RewriteError("entry_state must be reachable")
        index = _symbol_index(machine, operation.input_symbol)
        target = machine.transitions[entry][index]
        clone = machine.n_states
        transitions = list(machine.transitions)
        transitions.append(machine.transitions[target])
        transitions[entry] = tuple(
            clone if position == index else old_target
            for position, old_target in enumerate(machine.transitions[entry])
        )
        return MealyMachine(
            machine.input_alphabet,
            machine.output_alphabet,
            tuple(transitions),
            machine.outputs + (machine.outputs[target],),
            machine.initial,
        )

    if isinstance(operation, ReplaceEmission):
        state = _state(machine, operation.state, "state")
        if state not in reachable:
            raise RewriteError("state must be reachable")
        index = _symbol_index(machine, operation.input_symbol)
        if operation.output_symbol not in machine.output_alphabet:
            raise RewriteError("output_symbol is outside the output alphabet")
        if machine.outputs[state][index] == operation.output_symbol:
            raise RewriteError("emission rewrite must not be a no-op")
        return MealyMachine(
            machine.input_alphabet,
            machine.output_alphabet,
            machine.transitions,
            _replace_cell(machine.outputs, state, index, operation.output_symbol),
            machine.initial,
        )

    if isinstance(operation, RedirectTransition):
        state = _state(machine, operation.state, "state")
        if state not in reachable:
            raise RewriteError("state must be reachable")
        target = _state(machine, operation.target_state, "target_state")
        index = _symbol_index(machine, operation.input_symbol)
        if machine.transitions[state][index] == target:
            raise RewriteError("transition rewrite must not be a no-op")
        return MealyMachine(
            machine.input_alphabet,
            machine.output_alphabet,
            _replace_cell(machine.transitions, state, index, target),
            machine.outputs,
            machine.initial,
        )

    if isinstance(operation, PruneUnreachable):
        child = canonicalize_mealy(machine)
        if child.n_states == machine.n_states:
            raise RewriteError("prune operation requires unreachable storage")
        return child

    raise TypeError(f"unsupported rewrite operation: {type(operation)!r}")


@dataclass(frozen=True)
class RewriteCertificate:
    effect_kind: EffectKind
    parent_body_digest: str
    child_body_digest: str
    parent_behaviour_digest: str
    child_behaviour_digest: str
    parent_state_count: int
    child_state_count: int
    parent_reachable_count: int
    child_reachable_count: int
    state_count_delta: int
    reachable_count_delta: int
    behaviour_preserved: bool
    distinguishing_word: Word | None

    def to_dict(self) -> dict[str, object]:
        return {
            "effect_kind": self.effect_kind.value,
            "parent_body_digest": self.parent_body_digest,
            "child_body_digest": self.child_body_digest,
            "parent_behaviour_digest": self.parent_behaviour_digest,
            "child_behaviour_digest": self.child_behaviour_digest,
            "parent_state_count": self.parent_state_count,
            "child_state_count": self.child_state_count,
            "parent_reachable_count": self.parent_reachable_count,
            "child_reachable_count": self.child_reachable_count,
            "state_count_delta": self.state_count_delta,
            "reachable_count_delta": self.reachable_count_delta,
            "behaviour_preserved": self.behaviour_preserved,
            "distinguishing_word": (
                None if self.distinguishing_word is None else list(self.distinguishing_word)
            ),
        }


def _certificate_from_dict(data: Mapping[str, object]) -> RewriteCertificate:
    raw = _mapping(data, "certificate")
    required = {
        "effect_kind",
        "parent_body_digest",
        "child_body_digest",
        "parent_behaviour_digest",
        "child_behaviour_digest",
        "parent_state_count",
        "child_state_count",
        "parent_reachable_count",
        "child_reachable_count",
        "state_count_delta",
        "reachable_count_delta",
        "behaviour_preserved",
        "distinguishing_word",
    }
    _fields(raw, required, "certificate")
    try:
        effect = EffectKind(raw["effect_kind"])
    except (TypeError, ValueError) as exc:
        raise RewriteError("unknown certificate effect kind") from exc
    preserved = raw["behaviour_preserved"]
    if not isinstance(preserved, bool):
        raise RewriteError("behaviour_preserved must be a boolean")
    raw_word = raw["distinguishing_word"]
    word = (
        None
        if raw_word is None
        else tuple(
            _integer(symbol, "distinguishing_word")
            for symbol in _sequence(raw_word, "distinguishing_word")
        )
    )
    certificate = RewriteCertificate(
        effect,
        _digest(raw["parent_body_digest"], "parent_body_digest"),
        _digest(raw["child_body_digest"], "child_body_digest"),
        _digest(raw["parent_behaviour_digest"], "parent_behaviour_digest"),
        _digest(raw["child_behaviour_digest"], "child_behaviour_digest"),
        _integer(raw["parent_state_count"], "parent_state_count"),
        _integer(raw["child_state_count"], "child_state_count"),
        _integer(raw["parent_reachable_count"], "parent_reachable_count"),
        _integer(raw["child_reachable_count"], "child_reachable_count"),
        _integer(raw["state_count_delta"], "state_count_delta"),
        _integer(raw["reachable_count_delta"], "reachable_count_delta"),
        preserved,
        word,
    )
    if min(
        certificate.parent_state_count,
        certificate.child_state_count,
        certificate.parent_reachable_count,
        certificate.child_reachable_count,
    ) < 0:
        raise RewriteError("certificate counts must be non-negative")
    return certificate


def _certify(
    parent: MealyMachine, child: MealyMachine, operation: RewriteOperation
) -> RewriteCertificate:
    equivalent, witness = exact_mealy_equivalence(parent, child)
    parent_reachable = len(reachable_states(parent))
    child_reachable = len(reachable_states(child))
    state_delta = child.n_states - parent.n_states
    reachable_delta = child_reachable - parent_reachable

    if operation.effect_kind is EffectKind.REACHABLE_CAPACITY_GROWTH:
        if state_delta != 1 or reachable_delta != 1 or not equivalent:
            raise RewriteError(
                "duplication must preserve behaviour and add exactly one reachable state"
            )
    elif operation.effect_kind is EffectKind.FIXED_CAPACITY_OUTPUT_EDIT:
        if state_delta != 0 or reachable_delta != 0 or equivalent or witness is None:
            raise RewriteError(
                "emission edit must change behaviour at fixed reachable capacity"
            )
    elif operation.effect_kind is EffectKind.FIXED_CAPACITY_TRANSITION_EDIT:
        if state_delta != 0:
            raise RewriteError("transition edit must preserve physical state count")
    elif operation.effect_kind is EffectKind.UNREACHABLE_CAPACITY_COMPACTION:
        if state_delta >= 0 or reachable_delta != 0 or not equivalent:
            raise RewriteError(
                "pruning must remove only unreachable storage and preserve behaviour"
            )

    return RewriteCertificate(
        operation.effect_kind,
        exact_body_digest(parent),
        exact_body_digest(child),
        mealy_digest(parent, minimise=True),
        mealy_digest(child, minimise=True),
        parent.n_states,
        child.n_states,
        parent_reachable,
        child_reachable,
        state_delta,
        reachable_delta,
        equivalent,
        witness,
    )


def apply_rewrite(
    machine: MealyMachine, operation: RewriteOperation
) -> tuple[MealyMachine, RewriteCertificate]:
    child = _apply(machine, operation)
    return child, _certify(machine, child, operation)


@dataclass(frozen=True)
class RewriteStep:
    operation: RewriteOperation
    certificate: RewriteCertificate

    def to_dict(self) -> dict[str, object]:
        return {
            "operation": self.operation.to_dict(),
            "certificate": self.certificate.to_dict(),
        }


@dataclass(frozen=True)
class RewriteTrace:
    root_body_digest: str
    steps: tuple[RewriteStep, ...]
    final_body_digest: str
    version: str = TRACE_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "root_body_digest": self.root_body_digest,
            "steps": [step.to_dict() for step in self.steps],
            "final_body_digest": self.final_body_digest,
        }


def canonical_trace_bytes(trace: RewriteTrace) -> bytes:
    return json.dumps(
        trace.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def trace_digest(trace: RewriteTrace) -> str:
    return hashlib.sha256(
        b"m043-rewrite-trace-v1\x00" + canonical_trace_bytes(trace)
    ).hexdigest()


def trace_from_bytes(payload: bytes | str) -> RewriteTrace:
    try:
        raw = _mapping(json.loads(payload), "rewrite trace")
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RewriteError("rewrite trace is not valid JSON") from exc
    _fields(
        raw,
        {"version", "root_body_digest", "steps", "final_body_digest"},
        "rewrite trace",
    )
    if raw["version"] != TRACE_VERSION:
        raise RewriteError("unsupported rewrite trace version")
    steps: list[RewriteStep] = []
    for raw_step in _sequence(raw["steps"], "steps"):
        step = _mapping(raw_step, "rewrite step")
        _fields(step, {"operation", "certificate"}, "rewrite step")
        steps.append(
            RewriteStep(
                operation_from_dict(_mapping(step["operation"], "step operation")),
                _certificate_from_dict(
                    _mapping(step["certificate"], "step certificate")
                ),
            )
        )
    return RewriteTrace(
        _digest(raw["root_body_digest"], "root_body_digest"),
        tuple(steps),
        _digest(raw["final_body_digest"], "final_body_digest"),
    )


def build_rewrite_trace(
    parent: MealyMachine, operations: Sequence[RewriteOperation]
) -> tuple[MealyMachine, RewriteTrace]:
    current = parent
    steps: list[RewriteStep] = []
    for operation in operations:
        current, certificate = apply_rewrite(current, operation)
        steps.append(RewriteStep(operation, certificate))
    return current, RewriteTrace(
        exact_body_digest(parent), tuple(steps), exact_body_digest(current)
    )


def replay_rewrite_trace(parent: MealyMachine, trace: RewriteTrace) -> MealyMachine:
    if trace.version != TRACE_VERSION:
        raise RewriteError("unsupported rewrite trace version")
    if exact_body_digest(parent) != trace.root_body_digest:
        raise RewriteError("trace parent does not match the declared root body")
    current = parent
    for index, recorded in enumerate(trace.steps):
        current, certificate = apply_rewrite(current, recorded.operation)
        if certificate != recorded.certificate:
            raise RewriteError(f"rewrite certificate mismatch at step {index}")
    if exact_body_digest(current) != trace.final_body_digest:
        raise RewriteError("trace final body digest mismatch")
    return current
