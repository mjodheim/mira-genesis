"""M111 - a lineage that spends an experiment where its observation runs out.

These tests exercise the probe, the policy language, the acquisition and the expressibility lemma on
small authored worlds. They never touch the canonical population, the frozen protocol or the
preserved result.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from metamorphosis import m107_runtime as expr
from metamorphosis import m109_runtime as machinery
from metamorphosis import m110_runtime as consumer
from metamorphosis import m111_runtime as runtime

ROOT = Path(__file__).resolve().parents[1]
PRODUCER_RESULT = ROOT / "experiments" / "M109" / "RESULT.json"


def _evidence() -> dict:
    return json.loads(PRODUCER_RESULT.read_text(encoding="ascii"))["scientific_evidence"]


@pytest.fixture(scope="module")
def restored() -> dict:
    evidence = _evidence()
    first = machinery.decode_rule(evidence["generation_one"]["acquisition"]["adopted_rule"])
    second = machinery.decode_rule(evidence["generation_two"]["acquisition"]["adopted_rule"])
    terminal = evidence["stage_two_resolution"]
    name = terminal["construction"]["witness"]["children"][0]["operator"]
    matches = [
        item
        for item in expr.operator_space()
        if "ACQUIRED_%s" % item["operator_id"][-8:] == name
    ]
    acquired = expr.operator_definition(name, matches[0]["arity"], matches[0]["truth_table"])
    base = machinery.create_state()
    return {
        "rules": [first, second],
        "acquired": acquired,
        "terminal": machinery.create_state(
            base["operators"] + [acquired],
            signal_width=terminal["final_signal_width"],
            candidate_space=terminal["final_candidate_space"],
            rules=[first, second],
        ),
        "monotone": machinery.create_state(
            base["operators"], signal_width=terminal["final_signal_width"],
            candidate_space=machinery.MONOTONE_SPACE, rules=[first],
        ),
        "recorded_terminal_digest": terminal["final_state_digest"],
    }


# ---------------------------------------------------------------------------------------------
# Provenance: the terminal state is the lineage's own, and it carries an operator it chose.
# ---------------------------------------------------------------------------------------------


def test_the_m109_terminal_state_is_reproduced_byte_exactly(restored: dict) -> None:
    assert restored["terminal"]["state_digest"] == restored["recorded_terminal_digest"]


def test_the_operator_the_lineage_adopted_is_non_monotone(restored: dict) -> None:
    assert not expr._operator_is_monotone(restored["acquired"])
    assert [bool(value) for value in restored["acquired"]["truth_table"]] == [True, False]


def test_the_registry_extends_the_producer_triple_by_exactly_one() -> None:
    assert tuple(runtime.COMPONENTS) == tuple(machinery.COMPONENTS) + ("diagnostic_policy",)
    assert runtime.FEATURE_NAMES is machinery.FEATURE_NAMES


# ---------------------------------------------------------------------------------------------
# The expressibility lemma.
# ---------------------------------------------------------------------------------------------


def test_no_monotone_program_separates_row_three_from_row_seven(restored: dict) -> None:
    certificate = runtime.expressibility_certificate(restored["monotone"], 3, 7)
    assert certificate["lower_below_upper_componentwise"] is True
    assert certificate["every_held_operator_is_monotone"] is True
    assert certificate["separating_program_count"] == 0
    assert certificate["rule_space_size"] == 18
    assert certificate["closed_by_monotonicity_lemma"] is True


def test_the_terminal_state_can_separate_them(restored: dict) -> None:
    certificate = runtime.expressibility_certificate(restored["terminal"], 3, 7)
    assert certificate["rule_space_size"] > 18
    assert certificate["separating_program_count"] > 0


def test_non_monotone_operators_live_only_in_the_complete_candidate_space() -> None:
    monotone = machinery.candidate_operators(machinery.MONOTONE_SPACE)
    complete = machinery.candidate_operators(machinery.COMPLETE_SPACE)
    assert all(expr._operator_is_monotone(item) for item in monotone)
    assert any(not expr._operator_is_monotone(item) for item in complete)


# ---------------------------------------------------------------------------------------------
# The probe is an experiment, not an adoption.
# ---------------------------------------------------------------------------------------------


def _world(seed: int) -> dict:
    from scripts.author_m111_population import generate_world  # noqa: PLC0415

    return generate_world("test", seed)


def _state(restored: dict, *, cascade: list | None = None, policy=None, budget: int = 1) -> dict:
    rules = cascade if cascade is not None else []
    return runtime.create_state(
        machinery.create_state(machinery.create_state()["operators"], rules=rules),
        consumer.create_state(rules=rules),
        policy=policy,
        probe_budget=budget,
    )


def test_a_probe_leaves_the_serialized_state_byte_identical(restored: dict) -> None:
    world = _world(2000)
    state = _state(restored)
    before = runtime.encode_state(state)
    for component in (
        runtime.COMPONENT_SIGNALS,
        runtime.COMPONENT_CANDIDATES,
        runtime.COMPONENT_OPERATORS,
    ):
        record = runtime.probe(state, world, [0] * consumer.DOCUMENT_COUNT, component)
        assert record["state_unchanged"] is True
        assert record["is_an_adoption"] is False
    assert runtime.encode_state(state) == before


def test_a_probe_naming_an_unregistered_component_is_refused(restored: dict) -> None:
    with pytest.raises(ValueError):
        runtime.probe(_state(restored), _world(2000), [0] * consumer.DOCUMENT_COUNT, "nonsense")


# ---------------------------------------------------------------------------------------------
# State identity and failing closed.
# ---------------------------------------------------------------------------------------------


def test_state_round_trips_and_rejects_a_tampered_budget(restored: dict) -> None:
    state = _state(restored)
    payload = json.loads(runtime.encode_state(state).decode("ascii"))
    assert runtime.decode_state(payload)["state_digest"] == state["state_digest"]
    payload["probe_budget"] = payload["probe_budget"] + 1
    with pytest.raises(ValueError):
        runtime.decode_state(payload)


def test_a_state_whose_two_cascades_disagree_is_refused(restored: dict) -> None:
    first = restored["rules"][0]
    with pytest.raises(ValueError):
        runtime.create_state(
            machinery.create_state(machinery.create_state()["operators"], rules=[first]),
            consumer.create_state(rules=[]),
        )


def test_a_negative_probe_budget_is_refused(restored: dict) -> None:
    with pytest.raises(ValueError):
        runtime.create_state(machinery.create_state(), consumer.create_state(), probe_budget=-1)


def test_a_changed_registry_fails_closed(restored: dict) -> None:
    payload = json.loads(runtime.encode_state(_state(restored)).decode("ascii"))
    payload["component_registry"] = list(payload["component_registry"])[:3]
    with pytest.raises(ValueError):
        runtime.decode_state(payload)


def test_a_tampered_policy_identity_fails_closed(restored: dict) -> None:
    policy = runtime.diagnostic_policy(
        {"node": "SIGNAL", "index": 1}, [False, False, False, True] * 2, 3
    )
    state = _state(restored, policy=policy)
    payload = json.loads(runtime.encode_state(state).decode("ascii"))
    payload["policy"]["policy_id"] = "policy-0000000000000000"
    with pytest.raises(ValueError):
        runtime.decode_state(payload)


# ---------------------------------------------------------------------------------------------
# The record the lineage produces, and what it can derive from it.
# ---------------------------------------------------------------------------------------------


def test_an_undetermined_row_is_one_the_record_shows_resolving_two_ways() -> None:
    episodes = [
        {
            "usable": True,
            "features": {"row_index": 3},
            "component": "candidate_space",
        },
        {"usable": True, "features": {"row_index": 3}, "component": "signal_interface"},
        {"usable": True, "features": {"row_index": 1}, "component": "operator_table"},
        {"usable": False, "features": {"row_index": 7}, "component": None},
    ]
    survey = runtime.undetermined_rows(episodes)
    assert survey["undetermined"] == [3]
    assert survey["determined"] == [1]


def test_a_record_with_no_undetermined_row_yields_no_policy(restored: dict) -> None:
    episodes = [{"usable": True, "features": {"row_index": 1}, "component": "operator_table"}]
    report = runtime.acquire_policy(_state(restored), episodes, register_result=False)
    assert report["confirmed"] is False
    assert report["reason"] == "the_record_shows_no_undetermined_row"


def test_the_policy_language_is_the_lineage_own_operator_table(restored: dict) -> None:
    monotone = runtime.policy_rule_space(restored["monotone"])
    terminal = runtime.policy_rule_space(restored["terminal"])
    assert len(monotone) == 18
    assert len(terminal) > len(monotone)


def test_policy_fires_reads_the_truth_table() -> None:
    policy = runtime.diagnostic_policy(
        {"node": "SIGNAL", "index": 0},
        [False, False, False, True, False, False, False, False],
        3,
    )
    assert runtime.policy_fires(policy, 3) is True
    assert runtime.policy_fires(policy, 7) is False
    assert runtime.policy_fires(None, 3) is False
