"""Exact deterministic Mealy-machine kernel for M043 qualification gate Q1.

The module is deliberately independent from the DFA task generators, rewrite language and
canonical seeds used by M038--M042.  It provides only the formal behavioural substrate
needed before any M043 hidden task or development seed may exist.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import hashlib
import json
from typing import Mapping, Sequence

Word = tuple[int, ...]
OutputWord = tuple[int, ...]


class MealyFormatError(ValueError):
    """Raised when a serialised or constructed machine is malformed."""


def _require_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise MealyFormatError(f"{field} must contain integers")
    return value


def _require_sequence(value: object, *, field: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise MealyFormatError(f"{field} must be a sequence")
    return value


@dataclass(frozen=True)
class MealyMachine:
    """A finite deterministic total Mealy machine.

    ``outputs[state][symbol_index]`` is emitted before the transition to
    ``transitions[state][symbol_index]``.  Symbols are integers because M043's first
    bounded domain fixes finite integer alphabets; widening the symbol model requires a
    separately reviewed experiment.
    """

    input_alphabet: tuple[int, ...]
    output_alphabet: tuple[int, ...]
    transitions: tuple[tuple[int, ...], ...]
    outputs: tuple[tuple[int, ...], ...]
    initial: int = 0

    def __post_init__(self) -> None:
        if not self.input_alphabet:
            raise MealyFormatError("input alphabet must not be empty")
        if not self.output_alphabet:
            raise MealyFormatError("output alphabet must not be empty")
        if len(set(self.input_alphabet)) != len(self.input_alphabet):
            raise MealyFormatError("input alphabet symbols must be unique")
        if len(set(self.output_alphabet)) != len(self.output_alphabet):
            raise MealyFormatError("output alphabet symbols must be unique")
        if any(isinstance(symbol, bool) or not isinstance(symbol, int) for symbol in self.input_alphabet):
            raise MealyFormatError("input alphabet must contain integers")
        if any(isinstance(symbol, bool) or not isinstance(symbol, int) for symbol in self.output_alphabet):
            raise MealyFormatError("output alphabet must contain integers")

        state_count = len(self.transitions)
        if state_count == 0 or len(self.outputs) != state_count:
            raise MealyFormatError("invalid Mealy-machine dimensions")
        if isinstance(self.initial, bool) or not isinstance(self.initial, int):
            raise MealyFormatError("initial state must be an integer")
        if not 0 <= self.initial < state_count:
            raise MealyFormatError("invalid initial state")

        width = len(self.input_alphabet)
        if any(len(row) != width for row in self.transitions):
            raise MealyFormatError("transition width mismatch")
        if any(len(row) != width for row in self.outputs):
            raise MealyFormatError("output width mismatch")
        if any(
            isinstance(target, bool)
            or not isinstance(target, int)
            or not 0 <= target < state_count
            for row in self.transitions
            for target in row
        ):
            raise MealyFormatError("invalid transition target")

        allowed_outputs = set(self.output_alphabet)
        if any(
            isinstance(symbol, bool)
            or not isinstance(symbol, int)
            or symbol not in allowed_outputs
            for row in self.outputs
            for symbol in row
        ):
            raise MealyFormatError("emitted symbol is outside the output alphabet")

    @property
    def n_states(self) -> int:
        return len(self.transitions)

    def _symbol_index(self, symbol: int) -> int:
        if isinstance(symbol, bool) or not isinstance(symbol, int):
            raise ValueError(f"unknown input symbol: {symbol!r}")
        try:
            return self.input_alphabet.index(symbol)
        except ValueError as exc:
            raise ValueError(f"unknown input symbol: {symbol}") from exc

    def step(self, state: int, symbol: int) -> tuple[int, int]:
        if isinstance(state, bool) or not isinstance(state, int) or not 0 <= state < self.n_states:
            raise ValueError(f"invalid state: {state!r}")
        index = self._symbol_index(symbol)
        return self.transitions[state][index], self.outputs[state][index]

    def run(self, word: Sequence[int]) -> tuple[int, OutputWord]:
        state = self.initial
        emitted: list[int] = []
        for symbol in word:
            state, output = self.step(state, symbol)
            emitted.append(output)
        return state, tuple(emitted)

    def transduce(self, word: Sequence[int]) -> OutputWord:
        return self.run(word)[1]

    def to_dict(self) -> dict[str, object]:
        return {
            "input_alphabet": list(self.input_alphabet),
            "output_alphabet": list(self.output_alphabet),
            "transitions": [list(row) for row in self.transitions],
            "outputs": [list(row) for row in self.outputs],
            "initial": self.initial,
        }

    @staticmethod
    def from_dict(data: Mapping[str, object]) -> "MealyMachine":
        required = {
            "input_alphabet",
            "output_alphabet",
            "transitions",
            "outputs",
            "initial",
        }
        if set(data) != required:
            missing = sorted(required - set(data))
            extra = sorted(set(data) - required)
            raise MealyFormatError(f"invalid Mealy-machine fields: missing={missing}, extra={extra}")

        raw_inputs = _require_sequence(data["input_alphabet"], field="input_alphabet")
        raw_outputs_alphabet = _require_sequence(
            data["output_alphabet"], field="output_alphabet"
        )
        raw_transitions = _require_sequence(data["transitions"], field="transitions")
        raw_outputs = _require_sequence(data["outputs"], field="outputs")

        transitions: list[tuple[int, ...]] = []
        for row_index, raw_row in enumerate(raw_transitions):
            row = _require_sequence(raw_row, field=f"transitions[{row_index}]")
            transitions.append(
                tuple(
                    _require_int(value, field=f"transitions[{row_index}]")
                    for value in row
                )
            )

        outputs: list[tuple[int, ...]] = []
        for row_index, raw_row in enumerate(raw_outputs):
            row = _require_sequence(raw_row, field=f"outputs[{row_index}]")
            outputs.append(
                tuple(
                    _require_int(value, field=f"outputs[{row_index}]")
                    for value in row
                )
            )

        return MealyMachine(
            input_alphabet=tuple(
                _require_int(value, field="input_alphabet") for value in raw_inputs
            ),
            output_alphabet=tuple(
                _require_int(value, field="output_alphabet")
                for value in raw_outputs_alphabet
            ),
            transitions=tuple(transitions),
            outputs=tuple(outputs),
            initial=_require_int(data["initial"], field="initial"),
        )


def canonicalize_mealy(machine: MealyMachine) -> MealyMachine:
    """Remove unreachable states and assign canonical BFS state numbers.

    Discovery follows the declared input-alphabet order, so every reachable state is named
    by its shortest lexicographically earliest access word.  The result is invariant under
    a pure renaming of source states.
    """

    mapping = {machine.initial: 0}
    order = [machine.initial]
    queue = deque([machine.initial])

    while queue:
        state = queue.popleft()
        for target in machine.transitions[state]:
            if target not in mapping:
                mapping[target] = len(mapping)
                order.append(target)
                queue.append(target)

    transitions = tuple(
        tuple(mapping[target] for target in machine.transitions[old_state])
        for old_state in order
    )
    outputs = tuple(machine.outputs[old_state] for old_state in order)
    return MealyMachine(
        input_alphabet=machine.input_alphabet,
        output_alphabet=machine.output_alphabet,
        transitions=transitions,
        outputs=outputs,
        initial=0,
    )


def exact_mealy_equivalence(
    left: MealyMachine, right: MealyMachine
) -> tuple[bool, Word | None]:
    """Return exact behavioural equivalence and a shortest counterexample.

    Breadth-first product exploration makes the first returned word shortest.  Input
    symbols are expanded in the declared alphabet order, making the counterexample
    deterministic among equal-length alternatives.
    """

    if left.input_alphabet != right.input_alphabet:
        return False, ()
    if left.output_alphabet != right.output_alphabet:
        return False, ()

    initial_pair = (left.initial, right.initial)
    queue = deque([(left.initial, right.initial, ())])
    seen = {initial_pair}

    while queue:
        left_state, right_state, prefix = queue.popleft()
        for index, symbol in enumerate(left.input_alphabet):
            if left.outputs[left_state][index] != right.outputs[right_state][index]:
                return False, prefix + (symbol,)

            pair = (
                left.transitions[left_state][index],
                right.transitions[right_state][index],
            )
            if pair not in seen:
                seen.add(pair)
                queue.append((pair[0], pair[1], prefix + (symbol,)))

    return True, None


def shortest_distinguishing_word(
    left: MealyMachine, right: MealyMachine
) -> Word | None:
    return exact_mealy_equivalence(left, right)[1]


def minimize_mealy(machine: MealyMachine) -> MealyMachine:
    """Return the canonical minimal reachable machine with identical behaviour."""

    machine = canonicalize_mealy(machine)

    def partition_ids(signatures: Sequence[object]) -> tuple[int, ...]:
        known: dict[object, int] = {}
        result: list[int] = []
        for signature in signatures:
            if signature not in known:
                known[signature] = len(known)
            result.append(known[signature])
        return tuple(result)

    current = partition_ids(machine.outputs)
    while True:
        signatures = tuple(
            (
                machine.outputs[state],
                tuple(current[target] for target in machine.transitions[state]),
            )
            for state in range(machine.n_states)
        )
        refined = partition_ids(signatures)
        if refined == current:
            break
        current = refined

    part_count = max(current) + 1
    representatives = [current.index(part) for part in range(part_count)]
    transitions = tuple(
        tuple(current[target] for target in machine.transitions[representative])
        for representative in representatives
    )
    outputs = tuple(machine.outputs[representative] for representative in representatives)

    return canonicalize_mealy(
        MealyMachine(
            input_alphabet=machine.input_alphabet,
            output_alphabet=machine.output_alphabet,
            transitions=transitions,
            outputs=outputs,
            initial=current[machine.initial],
        )
    )


def canonical_mealy_bytes(
    machine: MealyMachine, *, minimise: bool = False
) -> bytes:
    """Encode a state-renaming-invariant canonical JSON body."""

    canonical = minimize_mealy(machine) if minimise else canonicalize_mealy(machine)
    return json.dumps(
        canonical.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")


def mealy_digest(machine: MealyMachine, *, minimise: bool = False) -> str:
    domain = b"m043-minimal-mealy-v1\x00" if minimise else b"m043-mealy-body-v1\x00"
    return hashlib.sha256(domain + canonical_mealy_bytes(machine, minimise=minimise)).hexdigest()
