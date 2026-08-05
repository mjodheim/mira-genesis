from __future__ import annotations

import pytest

from metamorphosis.m043_mealy import MealyMachine, minimize_mealy
from metamorphosis.m043_rewrite import (
    DuplicateReachableTarget,
    ReplaceEmission,
)
from metamorphosis.m043_tasks import (
    CatalogueStatus,
    HiddenTargetEvaluator,
    SearchBudget,
    TaskQualificationError,
    build_development_catalogue,
)


def parent() -> MealyMachine:
    return MealyMachine(
        input_alphabet=(0, 1, 2),
        output_alphabet=(0, 1, 2),
        transitions=((0, 1, 0), (0, 1, 1)),
        outputs=((0, 1, 2), (1, 0, 2)),
        initial=0,
    )


def known_target() -> MealyMachine:
    from metamorphosis.m043_rewrite import apply_rewrite

    grown, _ = apply_rewrite(parent(), DuplicateReachableTarget(0, 0))
    target, _ = apply_rewrite(grown, ReplaceEmission(2, 0, 1))
    return target


def budget() -> SearchBudget:
    return SearchBudget(max_depth=2, max_nodes=512, max_states=4)


def test_catalogue_admits_only_necessary_and_reachable_tasks() -> None:
    result = build_development_catalogue(
        parent(), budget=budget(), minimum_entries=3, maximum_candidates=16
    )

    assert result.status is CatalogueStatus.QUALIFIED
    assert len(result.entries) == 3
    for entry in result.entries:
        assert entry.incapacity.required_growth >= 1
        assert entry.constructive_outcome.exact
        assert entry.constructive_outcome.trace is not None
        assert len(entry.controls) == 5
        assert all(control.budget == budget() for control in entry.controls)


def test_every_admitted_trace_grows_then_exploits_new_capacity() -> None:
    result = build_development_catalogue(
        parent(), budget=budget(), minimum_entries=3, maximum_candidates=16
    )

    for entry in result.entries:
        assert entry.constructive_outcome.trace is not None
        operations = [
            step.operation for step in entry.constructive_outcome.trace.steps
        ]
        assert isinstance(operations[0], DuplicateReachableTarget)
        assert isinstance(operations[1], ReplaceEmission)
        assert operations[1].state >= parent().n_states


def test_public_task_surface_exposes_commitment_not_target_or_witness() -> None:
    entry = build_development_catalogue(
        parent(), budget=budget(), minimum_entries=1, maximum_candidates=4
    ).entries[0]
    public = entry.public.to_dict()
    flattened = repr(public).lower()

    assert set(public) == {
        "schema",
        "task_id",
        "parent_exact_digest",
        "target_commitment",
        "input_alphabet",
        "output_alphabet",
        "observation_limit",
        "search_budget",
    }
    for forbidden in (
        "transitions",
        "outputs",
        "trace",
        "operations",
        "replacement_output",
    ):
        assert forbidden not in flattened


def test_hidden_observation_budget_fails_closed() -> None:
    evaluator = HiddenTargetEvaluator(known_target(), observation_limit=1)
    evaluator.observe((0,))
    with pytest.raises(
        TaskQualificationError, match="observation budget exhausted"
    ):
        evaluator.observe((1,))


def test_catalogue_replays_deterministically_at_the_identity_level() -> None:
    first = build_development_catalogue(
        parent(), budget=budget(), minimum_entries=3, maximum_candidates=16
    )
    second = build_development_catalogue(
        parent(), budget=budget(), minimum_entries=3, maximum_candidates=16
    )

    assert first.to_dict() == second.to_dict()
    assert [entry.digest() for entry in first.entries] == [
        entry.digest() for entry in second.entries
    ]


def test_generation_has_explicit_negative_termination() -> None:
    no_variation = MealyMachine((0,), (0,), ((0,),), ((0,),), 0)
    result = build_development_catalogue(
        no_variation,
        budget=SearchBudget(max_depth=2, max_nodes=16, max_states=2),
        minimum_entries=1,
        maximum_candidates=4,
    )

    assert result.status is CatalogueStatus.INSUFFICIENT
    assert result.entries == ()
    assert result.to_dict()["explicit_negative_termination"] is True


def test_catalogue_is_development_only_without_seed_or_canonical_authority() -> None:
    mapping = build_development_catalogue(
        parent(), budget=budget(), minimum_entries=1, maximum_candidates=4
    ).to_dict()

    assert mapping["no_selected_seed"] is True
    assert mapping["no_canonical_workflow"] is True
    assert "selected_index" not in mapping
    assert all(
        key not in mapping for key in ("seed", "selected_seed", "seed_start")
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_depth": 0},
        {"max_nodes": True},
        {"max_states": -1},
    ],
)
def test_malformed_search_budgets_fail_closed(
    kwargs: dict[str, object]
) -> None:
    values = {"max_depth": 2, "max_nodes": 32, "max_states": 4}
    values.update(kwargs)
    with pytest.raises(TaskQualificationError):
        SearchBudget(**values)  # type: ignore[arg-type]


def test_fixed_development_catalogue_is_seed_free_and_qualified() -> None:
    from metamorphosis.m043_tasks import (
        Q3_DEVELOPMENT_BUDGET,
        Q3_DEVELOPMENT_MAXIMUM_CANDIDATES,
        Q3_DEVELOPMENT_MINIMUM_ENTRIES,
        q3_development_parent,
        run_q3_development_catalogue,
    )

    result = run_q3_development_catalogue()

    assert result.status is CatalogueStatus.QUALIFIED
    assert len(result.entries) == Q3_DEVELOPMENT_MINIMUM_ENTRIES == 3
    assert result.maximum_candidates == Q3_DEVELOPMENT_MAXIMUM_CANDIDATES == 32
    assert all(
        entry.public.search_budget == Q3_DEVELOPMENT_BUDGET
        for entry in result.entries
    )
    assert minimize_mealy(q3_development_parent()) == q3_development_parent()
    assert result.to_dict()["no_selected_seed"] is True


@pytest.mark.parametrize("value", [0, True, 1.5])
def test_malformed_observation_limits_fail_closed(value: object) -> None:
    with pytest.raises(TaskQualificationError):
        HiddenTargetEvaluator(
            known_target(), observation_limit=value  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "minimum_entries, maximum_candidates",
    [(True, 4), (1, False), (1.5, 4), (1, 0)],
)
def test_malformed_catalogue_limits_fail_closed(
    minimum_entries: object, maximum_candidates: object
) -> None:
    with pytest.raises(TaskQualificationError):
        build_development_catalogue(
            parent(),
            budget=budget(),
            minimum_entries=minimum_entries,  # type: ignore[arg-type]
            maximum_candidates=maximum_candidates,  # type: ignore[arg-type]
        )
