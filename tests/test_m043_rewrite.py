from dataclasses import replace
import json
import random

import pytest

from metamorphosis.m043_mealy import MealyMachine, exact_mealy_equivalence
from metamorphosis.m043_rewrite import (
    DuplicateReachableTarget,
    EffectKind,
    PruneUnreachable,
    RedirectTransition,
    ReplaceEmission,
    RewriteError,
    RewriteStep,
    apply_rewrite,
    build_rewrite_trace,
    canonical_trace_bytes,
    exact_body_bytes,
    exact_body_digest,
    operation_from_dict,
    reachable_states,
    replay_rewrite_trace,
    trace_digest,
    trace_from_bytes,
)


def machine() -> MealyMachine:
    return MealyMachine(
        input_alphabet=(0, 1),
        output_alphabet=(0, 1, 2),
        transitions=((0, 1), (0, 1)),
        outputs=((0, 1), (1, 0)),
        initial=0,
    )


def test_duplicate_is_exact_reachable_capacity_growth() -> None:
    parent = machine()
    child, certificate = apply_rewrite(parent, DuplicateReachableTarget(1, 0))

    assert child.n_states == 3
    assert reachable_states(child) == frozenset({0, 1, 2})
    assert exact_mealy_equivalence(parent, child) == (True, None)
    assert certificate.effect_kind is EffectKind.REACHABLE_CAPACITY_GROWTH
    assert certificate.state_count_delta == certificate.reachable_count_delta == 1
    assert certificate.behaviour_preserved


def test_duplicate_rejects_fake_growth_when_original_target_becomes_unreachable() -> None:
    parent = MealyMachine(
        (0,),
        (0,),
        ((1,), (2,), (2,)),
        ((0,), (0,), (0,)),
        0,
    )

    with pytest.raises(RewriteError, match="add exactly one reachable state"):
        apply_rewrite(parent, DuplicateReachableTarget(0, 0))


def test_new_capacity_can_be_exploited_without_editing_original_state() -> None:
    parent = machine()
    grown, _ = apply_rewrite(parent, DuplicateReachableTarget(1, 0))
    specialised, certificate = apply_rewrite(grown, ReplaceEmission(2, 0, 2))

    assert certificate.effect_kind is EffectKind.FIXED_CAPACITY_OUTPUT_EDIT
    assert certificate.state_count_delta == certificate.reachable_count_delta == 0
    assert not certificate.behaviour_preserved
    assert certificate.distinguishing_word == (1, 0, 0)
    assert parent.transduce((0, 0, 0)) == specialised.transduce((0, 0, 0))
    assert parent.transduce((1, 0, 0)) != specialised.transduce((1, 0, 0))


def test_transition_edit_certifies_actual_reachability_effect() -> None:
    grown, _ = apply_rewrite(machine(), DuplicateReachableTarget(1, 0))
    child, certificate = apply_rewrite(grown, RedirectTransition(1, 0, 0))

    assert child.n_states == grown.n_states
    assert certificate.effect_kind is EffectKind.FIXED_CAPACITY_TRANSITION_EDIT
    assert certificate.state_count_delta == 0
    assert certificate.reachable_count_delta == -1


def test_prune_removes_only_unreachable_storage() -> None:
    parent = MealyMachine(
        (0, 1),
        (0, 1),
        ((0, 1), (0, 1), (2, 2)),
        ((0, 1), (1, 0), (1, 1)),
        0,
    )
    child, certificate = apply_rewrite(parent, PruneUnreachable())

    assert parent.n_states == 3 and child.n_states == 2
    assert certificate.state_count_delta == -1
    assert certificate.reachable_count_delta == 0
    assert certificate.behaviour_preserved
    assert exact_body_digest(parent) != exact_body_digest(child)


def test_trace_replays_byte_identically_and_deterministically() -> None:
    operations = (
        DuplicateReachableTarget(1, 0),
        ReplaceEmission(2, 0, 2),
        RedirectTransition(2, 1, 0),
    )

    final, trace = build_rewrite_trace(machine(), operations)
    replayed = replay_rewrite_trace(machine(), trace)
    rebuilt, trace_again = build_rewrite_trace(machine(), operations)

    assert exact_body_bytes(replayed) == exact_body_bytes(final)
    assert exact_body_bytes(rebuilt) == exact_body_bytes(final)
    assert canonical_trace_bytes(trace_again) == canonical_trace_bytes(trace)
    assert trace_digest(trace_again) == trace_digest(trace)


def test_trace_rejects_wrong_parent_and_tampered_certificate() -> None:
    _, trace = build_rewrite_trace(
        machine(), (DuplicateReachableTarget(1, 0),)
    )
    wrong_parent = replace(machine(), outputs=((2, 1), (1, 0)))

    with pytest.raises(RewriteError, match="declared root"):
        replay_rewrite_trace(wrong_parent, trace)

    bad_certificate = replace(trace.steps[0].certificate, child_state_count=99)
    bad_trace = replace(
        trace,
        steps=(RewriteStep(trace.steps[0].operation, bad_certificate),),
    )
    with pytest.raises(RewriteError, match="certificate mismatch"):
        replay_rewrite_trace(machine(), bad_trace)


@pytest.mark.parametrize(
    "payload",
    [
        {
            "op": "duplicate_reachable_target",
            "entry_state": True,
            "input_symbol": 0,
        },
        {
            "op": "replace_emission",
            "state": 0,
            "input_symbol": 0,
            "output_symbol": 1,
            "extra": 0,
        },
        {"op": "redirect_transition", "state": 0, "input_symbol": 0},
        {"op": "unknown"},
    ],
)
def test_operation_parser_fails_closed(payload: dict[str, object]) -> None:
    with pytest.raises(RewriteError):
        operation_from_dict(payload)


def test_operation_round_trip_is_strict() -> None:
    operations = (
        DuplicateReachableTarget(1, 0),
        ReplaceEmission(2, 1, 2),
        RedirectTransition(2, 0, 0),
        PruneUnreachable(),
    )

    for operation in operations:
        encoded = json.loads(json.dumps(operation.to_dict()))
        assert operation_from_dict(encoded) == operation


def test_trace_json_round_trip_is_strict() -> None:
    _, trace = build_rewrite_trace(
        machine(),
        (DuplicateReachableTarget(1, 0), ReplaceEmission(2, 0, 2)),
    )

    decoded = trace_from_bytes(canonical_trace_bytes(trace))

    assert decoded == trace
    assert canonical_trace_bytes(decoded) == canonical_trace_bytes(trace)


@pytest.mark.parametrize(
    "mutator",
    [
        lambda body: body.update({"unexpected": 1}),
        lambda body: body.update({"version": "m043-mealy-rewrite-trace-v2"}),
        lambda body: body.update({"root_body_digest": "not-a-digest"}),
        lambda body: body["steps"][0]["certificate"].update(
            {"behaviour_preserved": 1}
        ),
    ],
)
def test_trace_parser_fails_closed(mutator) -> None:
    _, trace = build_rewrite_trace(
        machine(), (DuplicateReachableTarget(1, 0),)
    )
    body = json.loads(canonical_trace_bytes(trace))
    mutator(body)

    with pytest.raises(RewriteError):
        trace_from_bytes(json.dumps(body))


def test_random_admissible_duplicates_are_exact_neutral_growth() -> None:
    rng = random.Random(243_043)
    successes = 0

    for _ in range(64):
        state_count = rng.randint(2, 6)
        candidate = MealyMachine(
            input_alphabet=(0, 1, 2),
            output_alphabet=(0, 1, 2),
            transitions=tuple(
                tuple(rng.randrange(state_count) for _ in range(3))
                for _ in range(state_count)
            ),
            outputs=tuple(
                tuple(rng.randrange(3) for _ in range(3))
                for _ in range(state_count)
            ),
        )

        for entry in sorted(reachable_states(candidate)):
            for symbol in candidate.input_alphabet:
                try:
                    child, certificate = apply_rewrite(
                        candidate, DuplicateReachableTarget(entry, symbol)
                    )
                except RewriteError:
                    continue
                successes += 1
                assert exact_mealy_equivalence(candidate, child) == (True, None)
                assert certificate.state_count_delta == 1
                assert certificate.reachable_count_delta == 1

    assert successes >= 32
