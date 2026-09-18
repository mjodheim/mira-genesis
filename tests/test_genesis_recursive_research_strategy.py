"""DEVELOPMENT regressions for evidence-driven recursive research strategy."""
from __future__ import annotations

from genesis import recursive_research_strategy as research
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis

HOST = tr.provenance("host_written", produced_by="recursive research strategy fixture")


def grade(task, answer):
    return "solved" if answer == task.get("expected") else "unsolved"


def seed_body():
    class Body:
        def attempt(self, task):
            return task.get("input")

    return Body()


def _genesis():
    state = st.create_state(
        body_digest=tr.artifact_digest_of(seed_body)["artifact_digest"],
        components=[
            {
                "name": "operator_table",
                "origin": "seed",
                "certificate": None,
                "provenance": HOST,
            }
        ],
        vocabulary=[{"name": "axis", "origin": "seed", "certificate": None}],
    )
    return Genesis(
        state=state,
        body_factory=seed_body,
        budget=tr.Budget(limits={"generations": 8}),
        isolation=tr.Isolation(),
        grade=grade,
    )


def _zero_outcome(attempt, family, mechanisms, regions, *, parent_kind="champion", depth=0):
    return research.create_outcome(
        attempt=attempt,
        family=family,
        target_axes=("execution_personal_read",),
        mechanisms=mechanisms,
        changed_regions=regions,
        hard_pass=True,
        capability_deltas={
            "execution_personal_read": 0,
            "personal_read": 0,
            "personal_write": 0,
        },
        parent_kind=parent_kind,
        parent_lineage_depth=depth,
        parent_digest="parent-%d" % attempt,
        child_digest="child-%d" % attempt,
        source_digest="result-%d" % attempt,
    )


def _candidates():
    repeated = research.create_candidate(
        candidate_id="another-keyword-pass",
        family="personal-read-routing",
        target_axes=("execution_personal_read",),
        mechanisms=("keyword-routing", "direct-read-short-circuit"),
        changed_regions=("ToolRegistry", "StreamingPipeline"),
        causal_claims=("broaden the lexical gate",),
        local_checks=("compile",),
        risk_flags=(),
        parent_kind="champion",
        parent_lineage_depth=0,
        parent_digest="champion",
    )
    pivot = research.create_candidate(
        candidate_id="typed-action-plan",
        family="typed-action-planning",
        target_axes=("execution_personal_read",),
        mechanisms=("typed-action-plan", "authority-before-execution", "structured-result"),
        changed_regions=("ActionPlanner", "ToolExecutor", "ResponseContext"),
        causal_claims=(
            "separate intent parsing from tool execution",
            "make authorization explicit before execution",
            "carry structured tool output into response generation",
        ),
        local_checks=("compile", "unit-tests", "round-trip-plan"),
        risk_flags=(),
        parent_kind="neutral",
        parent_lineage_depth=1,
        parent_digest="neutral-a",
    )
    return repeated, pivot


def test_repeated_zero_signal_evolves_strategy_and_selects_architectural_pivot():
    genesis = _genesis()
    outcomes = [
        _zero_outcome(
            1,
            "personal-read-routing",
            ("keyword-routing", "direct-read-short-circuit"),
            ("ToolRegistry", "StreamingPipeline"),
        ),
        _zero_outcome(
            2,
            "personal-read-routing",
            ("keyword-routing", "direct-read-short-circuit"),
            ("ToolRegistry", "ProductionPipeline"),
        ),
    ]
    repeated, pivot = _candidates()

    plan = research.adaptive_plan(
        genesis,
        outcomes=outcomes,
        candidates=(repeated, pivot),
        unresolved_axes=("execution_personal_read", "conversation", "personal_write"),
    )

    strategy = research.bound_strategy(genesis)
    assert strategy is not None
    assert strategy["generation"] == 1
    assert strategy["parent_strategy_digest"] == plan["prior_strategy_digest"]
    assert strategy["evidence_memory_digest"] == plan["memory_digest"]
    assert plan["strategy_evolved"] is True
    assert plan["selected_candidate_digest"] == pivot["candidate_digest"]
    assert plan["ranking"][0]["candidate"]["candidate_id"] == "typed-action-plan"
    assert plan["ranking"][0]["components"]["mechanism_pivot"] is False
    assert plan["ranking"][1]["components"]["repeat_penalty"] >= 4

    updates = [
        item
        for item in genesis.state["observations"]
        if item.get("kind") == "recursive_research_strategy_updated"
    ]
    assert len(updates) == 1
    assert updates[0]["memory_digest"] == plan["memory_digest"]


def test_candidate_tournament_is_order_invariant():
    outcomes = [
        _zero_outcome(
            1,
            "personal-read-routing",
            ("keyword-routing",),
            ("ToolRegistry",),
        ),
        _zero_outcome(
            2,
            "personal-read-routing",
            ("keyword-routing", "direct-read-short-circuit"),
            ("ToolRegistry", "StreamingPipeline"),
        ),
    ]
    repeated, pivot = _candidates()

    first = _genesis()
    first_plan = research.adaptive_plan(
        first,
        outcomes=outcomes,
        candidates=(repeated, pivot),
        unresolved_axes=("execution_personal_read",),
    )
    second = _genesis()
    second_plan = research.adaptive_plan(
        second,
        outcomes=outcomes,
        candidates=(pivot, repeated),
        unresolved_axes=("execution_personal_read",),
    )

    assert first_plan["selected_candidate_digest"] == second_plan["selected_candidate_digest"]
    assert [
        item["candidate"]["candidate_digest"] for item in first_plan["ranking"]
    ] == [
        item["candidate"]["candidate_digest"] for item in second_plan["ranking"]
    ]


def test_same_memory_cannot_recursively_inflate_strategy_weights():
    genesis = _genesis()
    outcomes = [
        _zero_outcome(1, "stalled-family", ("mechanism-a",), ("RegionA",)),
        _zero_outcome(2, "stalled-family", ("mechanism-a",), ("RegionB",)),
    ]
    repeated, pivot = _candidates()

    first = research.adaptive_plan(
        genesis,
        outcomes=outcomes,
        candidates=(repeated, pivot),
        unresolved_axes=("execution_personal_read",),
    )
    strategy_after_first = research.bound_strategy(genesis)

    second = research.adaptive_plan(
        genesis,
        outcomes=outcomes,
        candidates=(repeated, pivot),
        unresolved_axes=("execution_personal_read",),
    )
    strategy_after_second = research.bound_strategy(genesis)

    assert strategy_after_first == strategy_after_second
    assert first["strategy_evolved"] is True
    assert second["strategy_evolved"] is False
    assert second["prior_strategy_digest"] == strategy_after_first["strategy_digest"]


def test_new_evidence_can_drive_a_second_strategy_generation():
    genesis = _genesis()
    first_history = [
        _zero_outcome(1, "family-a", ("m1",), ("R1",)),
        _zero_outcome(2, "family-a", ("m1",), ("R2",)),
    ]
    repeated, pivot = _candidates()
    research.adaptive_plan(
        genesis,
        outcomes=first_history,
        candidates=(repeated, pivot),
        unresolved_axes=("execution_personal_read",),
    )
    first = research.bound_strategy(genesis)
    assert first is not None and first["generation"] == 1

    second_history = [
        *first_history,
        _zero_outcome(3, "family-b", ("m2",), ("R3",)),
        _zero_outcome(4, "family-b", ("m2",), ("R4",)),
    ]
    plan = research.adaptive_plan(
        genesis,
        outcomes=second_history,
        candidates=(repeated, pivot),
        unresolved_axes=("execution_personal_read", "conversation"),
    )
    second = research.bound_strategy(genesis)

    assert second is not None
    assert second["generation"] == 2
    assert second["parent_strategy_digest"] == first["strategy_digest"]
    assert second["evidence_memory_digest"] == plan["memory_digest"]
    assert second["weights"]["causal_specificity"] > first["weights"]["causal_specificity"]


def test_research_records_reject_unadmitted_extra_fields():
    outcome = _zero_outcome(1, "family", ("m",), ("R",))
    forged = {**outcome, "hidden_cases": ["secret"]}
    try:
        research.validate_outcome(forged)
    except research.RecursiveResearchError as problem:
        assert "does not reconstruct" in str(problem)
    else:  # pragma: no cover
        raise AssertionError("outcome carrying hidden extra fields was accepted")

    candidate = research.create_candidate(
        candidate_id="c",
        family="f",
        target_axes=("conversation",),
        mechanisms=("m",),
        changed_regions=("R",),
        causal_claims=("claim",),
        local_checks=("compile",),
    )
    forged_candidate = {**candidate, "evaluator_hint": "secret"}
    try:
        research.validate_candidate(forged_candidate)
    except research.RecursiveResearchError as problem:
        assert "does not reconstruct" in str(problem)
    else:  # pragma: no cover
        raise AssertionError("candidate carrying evaluator data was accepted")
