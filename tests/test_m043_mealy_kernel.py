from __future__ import annotations

from itertools import product
import json
import random

import pytest

from metamorphosis.m043_mealy import (
    MealyFormatError,
    MealyMachine,
    canonical_mealy_bytes,
    canonicalize_mealy,
    exact_mealy_equivalence,
    mealy_digest,
    minimize_mealy,
    shortest_distinguishing_word,
)


def _sample_machine() -> MealyMachine:
    return MealyMachine(
        input_alphabet=(0, 1, 2),
        output_alphabet=(0, 1, 2),
        transitions=(
            (1, 2, 0),
            (1, 2, 0),
            (0, 2, 1),
            (3, 3, 3),  # unreachable and intentionally discarded by canonicalisation
        ),
        outputs=(
            (0, 1, 2),
            (1, 2, 0),
            (2, 0, 1),
            (2, 2, 2),
        ),
        initial=0,
    )


def _rename(machine: MealyMachine, old_to_new: tuple[int, ...]) -> MealyMachine:
    assert sorted(old_to_new) == list(range(machine.n_states))
    transitions: list[tuple[int, ...] | None] = [None] * machine.n_states
    outputs: list[tuple[int, ...] | None] = [None] * machine.n_states
    for old_state, new_state in enumerate(old_to_new):
        transitions[new_state] = tuple(
            old_to_new[target] for target in machine.transitions[old_state]
        )
        outputs[new_state] = machine.outputs[old_state]
    return MealyMachine(
        input_alphabet=machine.input_alphabet,
        output_alphabet=machine.output_alphabet,
        transitions=tuple(row for row in transitions if row is not None),
        outputs=tuple(row for row in outputs if row is not None),
        initial=old_to_new[machine.initial],
    )


def _words(alphabet: tuple[int, ...], max_length: int):
    for length in range(1, max_length + 1):
        yield from product(alphabet, repeat=length)


def test_transduction_emits_one_symbol_per_input() -> None:
    machine = _sample_machine()

    final_state, output = machine.run((0, 1, 2, 0))

    assert final_state == 1
    assert output == (0, 2, 1, 1)
    assert machine.transduce((0, 1, 2, 0)) == output


def test_step_rejects_unknown_state_and_symbol() -> None:
    machine = _sample_machine()

    with pytest.raises(ValueError, match="invalid state"):
        machine.step(99, 0)
    with pytest.raises(ValueError, match="unknown input symbol"):
        machine.step(0, 99)
    with pytest.raises(ValueError, match="unknown input symbol"):
        machine.step(0, True)


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"input_alphabet": ()}, "input alphabet must not be empty"),
        ({"output_alphabet": ()}, "output alphabet must not be empty"),
        ({"input_alphabet": (0, 0)}, "input alphabet symbols must be unique"),
        ({"output_alphabet": (0, 0)}, "output alphabet symbols must be unique"),
        ({"transitions": ()}, "invalid Mealy-machine dimensions"),
        ({"outputs": ((0, 0), (0, 0))}, "invalid Mealy-machine dimensions"),
        ({"initial": 4}, "invalid initial state"),
        ({"transitions": ((0,),)}, "transition width mismatch"),
        ({"outputs": ((0,),)}, "output width mismatch"),
        ({"transitions": ((0, 2),)}, "invalid transition target"),
        ({"outputs": ((0, 9),)}, "emitted symbol is outside the output alphabet"),
    ],
)
def test_constructor_rejects_malformed_machines(
    kwargs: dict[str, object], message: str
) -> None:
    base: dict[str, object] = {
        "input_alphabet": (0, 1),
        "output_alphabet": (0, 1),
        "transitions": ((0, 0),),
        "outputs": ((0, 1),),
        "initial": 0,
    }
    base.update(kwargs)

    with pytest.raises(MealyFormatError, match=message):
        MealyMachine(**base)  # type: ignore[arg-type]


def test_bool_is_not_accepted_as_an_integer_symbol_or_target() -> None:
    with pytest.raises(MealyFormatError, match="input alphabet must contain integers"):
        MealyMachine((0, True), (0, 1), ((0, 0),), ((0, 1),), 0)

    with pytest.raises(MealyFormatError, match="invalid transition target"):
        MealyMachine((0, 1), (0, 1), ((0, True),), ((0, 1),), 0)


def test_canonicalisation_is_invariant_under_state_renaming() -> None:
    machine = _sample_machine()
    renamed = _rename(machine, (2, 0, 3, 1))

    canonical = canonicalize_mealy(machine)
    renamed_canonical = canonicalize_mealy(renamed)

    assert canonical == renamed_canonical
    assert canonical.n_states == 3
    assert canonical.initial == 0
    assert canonical_mealy_bytes(machine) == canonical_mealy_bytes(renamed)
    assert mealy_digest(machine) == mealy_digest(renamed)


def test_canonical_json_round_trips_strictly() -> None:
    canonical = canonicalize_mealy(_sample_machine())
    encoded = canonical_mealy_bytes(canonical)

    decoded = MealyMachine.from_dict(json.loads(encoded))

    assert decoded == canonical
    assert canonical_mealy_bytes(decoded) == encoded


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {
            "input_alphabet": [0, 1],
            "output_alphabet": [0, 1],
            "transitions": [[0, 0]],
            "outputs": [[0, 1]],
            # initial deliberately missing
        },
        {
            "input_alphabet": [0, 1],
            "output_alphabet": [0, 1],
            "transitions": "not-a-table",
            "outputs": [[0, 1]],
            "initial": 0,
        },
        {
            "input_alphabet": [0, 1],
            "output_alphabet": [0, 1],
            "transitions": [[0, True]],
            "outputs": [[0, 1]],
            "initial": 0,
        },
        {
            "input_alphabet": [0, 1],
            "output_alphabet": [0, 1],
            "transitions": [[0, 0]],
            "outputs": [[0, 1]],
            "initial": 0,
            "unexpected": 1,
        },
    ],
)
def test_from_dict_fails_closed(payload: dict[str, object]) -> None:
    with pytest.raises(MealyFormatError):
        MealyMachine.from_dict(payload)


def test_exact_equivalence_returns_shortest_distinguishing_word() -> None:
    left = MealyMachine(
        input_alphabet=(0, 1),
        output_alphabet=(0, 1, 2),
        transitions=((1, 0), (1, 1)),
        outputs=((0, 0), (0, 1)),
    )
    right = MealyMachine(
        input_alphabet=(0, 1),
        output_alphabet=(0, 1, 2),
        transitions=((1, 0), (1, 1)),
        outputs=((0, 0), (0, 2)),
    )

    equivalent, witness = exact_mealy_equivalence(left, right)

    assert not equivalent
    assert witness == (0, 1)
    assert shortest_distinguishing_word(left, right) == witness
    assert left.transduce(witness) != right.transduce(witness)
    assert left.transduce((0,)) == right.transduce((0,))
    assert left.transduce((1,)) == right.transduce((1,))


def test_alphabet_mismatch_fails_before_product_exploration() -> None:
    left = MealyMachine((0, 1), (0, 1), ((0, 0),), ((0, 1),))
    different_input = MealyMachine((0, 2), (0, 1), ((0, 0),), ((0, 1),))
    different_output = MealyMachine((0, 1), (0, 1, 2), ((0, 0),), ((0, 1),))

    assert exact_mealy_equivalence(left, different_input) == (False, ())
    assert exact_mealy_equivalence(left, different_output) == (False, ())


def test_minimisation_merges_equivalent_reachable_states() -> None:
    machine = MealyMachine(
        input_alphabet=(0, 1),
        output_alphabet=(0, 1, 2),
        transitions=(
            (1, 2),
            (1, 1),
            (2, 2),
            (3, 3),  # unreachable
        ),
        outputs=(
            (0, 0),
            (1, 2),
            (1, 2),
            (2, 2),
        ),
    )

    minimal = minimize_mealy(machine)

    assert minimal.n_states == 2
    assert exact_mealy_equivalence(machine, minimal) == (True, None)
    assert minimize_mealy(minimal) == minimal


def test_minimal_identity_is_invariant_under_renaming() -> None:
    machine = _sample_machine()
    renamed = _rename(machine, (1, 3, 0, 2))

    assert minimize_mealy(machine) == minimize_mealy(renamed)
    assert canonical_mealy_bytes(machine, minimise=True) == canonical_mealy_bytes(
        renamed, minimise=True
    )
    assert mealy_digest(machine, minimise=True) == mealy_digest(renamed, minimise=True)


def test_product_equivalence_agrees_with_exhaustive_small_machine_checks() -> None:
    rng = random.Random(43_043)
    alphabet = (0, 1)
    output_alphabet = (0, 1, 2)

    for _ in range(64):
        left_states = rng.randint(1, 4)
        right_states = rng.randint(1, 4)
        left = MealyMachine(
            input_alphabet=alphabet,
            output_alphabet=output_alphabet,
            transitions=tuple(
                tuple(rng.randrange(left_states) for _ in alphabet)
                for _ in range(left_states)
            ),
            outputs=tuple(
                tuple(rng.choice(output_alphabet) for _ in alphabet)
                for _ in range(left_states)
            ),
        )
        right = MealyMachine(
            input_alphabet=alphabet,
            output_alphabet=output_alphabet,
            transitions=tuple(
                tuple(rng.randrange(right_states) for _ in alphabet)
                for _ in range(right_states)
            ),
            outputs=tuple(
                tuple(rng.choice(output_alphabet) for _ in alphabet)
                for _ in range(right_states)
            ),
        )

        exhaustive_witness = next(
            (
                word
                for word in _words(alphabet, left_states * right_states)
                if left.transduce(word) != right.transduce(word)
            ),
            None,
        )
        equivalent, product_witness = exact_mealy_equivalence(left, right)

        assert equivalent is (exhaustive_witness is None)
        assert product_witness == exhaustive_witness


def test_minimisation_preserves_all_words_through_product_equivalence() -> None:
    rng = random.Random(143_043)
    alphabet = (0, 1, 2)
    output_alphabet = (0, 1, 2)

    for _ in range(32):
        state_count = rng.randint(1, 6)
        machine = MealyMachine(
            input_alphabet=alphabet,
            output_alphabet=output_alphabet,
            transitions=tuple(
                tuple(rng.randrange(state_count) for _ in alphabet)
                for _ in range(state_count)
            ),
            outputs=tuple(
                tuple(rng.choice(output_alphabet) for _ in alphabet)
                for _ in range(state_count)
            ),
            initial=rng.randrange(state_count),
        )

        minimal = minimize_mealy(machine)

        assert exact_mealy_equivalence(machine, minimal) == (True, None)
        assert minimal.n_states <= canonicalize_mealy(machine).n_states
        assert minimize_mealy(minimal) == minimal
