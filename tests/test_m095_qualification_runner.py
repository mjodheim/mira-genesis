"""Safety boundaries and adversarial mutations for M095's qualification apparatus."""

from __future__ import annotations

import json
from copy import deepcopy

import pytest

from scripts import check_m095_result as checker
from scripts import run_m095_qualification as runner
from scripts.author_m095_qualification_pool import digest, load_pool


def test_runner_refuses_a_draft_protocol() -> None:
    protocol = {
        "status": "draft",
        "qualification_population": {"pool_digest": load_pool()["pool_digest"]},
    }
    with pytest.raises(runner.QualificationRefused, match="not frozen"):
        runner.require_frozen(protocol, load_pool())


def test_materializing_without_arming_is_refused_before_any_world_runs() -> None:
    with pytest.raises(runner.QualificationRefused, match="requires arming"):
        runner.materialize()


def test_runner_refuses_a_moved_pool() -> None:
    pool = load_pool()
    pool["status"] = "frozen"
    protocol = {
        "status": "frozen",
        "qualification_population": {"pool_digest": "0" * 64},
        "mechanism": {"files": ["metamorphosis/m095_chain.py"], "digest": "0" * 64},
    }
    with pytest.raises(runner.QualificationRefused, match="pool digest"):
        runner.require_frozen(protocol, pool)


def test_an_entry_mutation_breaks_its_content_address() -> None:
    pool = load_pool()
    changed = deepcopy(pool["entries"][0])
    changed["inner_call_sites"] += 1
    assert changed["entry_digest"] != digest(
        {key: value for key, value in changed.items() if key != "entry_digest"}
    )


def test_pool_json_has_no_result_fields_before_the_run() -> None:
    pool = json.loads(runner.POOL_PATH.read_text(encoding="utf-8"))
    forbidden = {"enabling_demonstrated", "a_reached", "b_reached", "verdict"}
    assert forbidden.isdisjoint(pool)
    assert all(forbidden.isdisjoint(entry) for entry in pool["entries"])


def _synthetic_evidence() -> tuple[dict, dict, list[dict], dict]:
    pool = load_pool()
    protocol = json.loads(checker.PROTOCOL_PATH.read_text(encoding="utf-8"))
    rows = []
    for entry in pool["entries"]:
        positive = bool(entry["expected_relation"])
        rows.append({
            "entry": entry["id"],
            "entry_digest": entry["entry_digest"],
            "structure": entry["structure"],
            "arrangement": entry["arrangement"],
            "expected_relation": positive,
            "expected_descent": entry["expected_descent"],
            "world": {"inner_call_sites": entry["inner_call_sites"]},
            "enabling_demonstrated": positive,
            "descent_used": bool(entry["expected_descent"]),
            "control_b_from_s0_reached": False,
            "a_reached": True if positive else None,
            "a_identified_by": (
                "the_nested_operation_became_applicable" if positive else "nothing_reached"
            ),
            "b_reached": True if positive else False,
            "b_confirmed_by_execution": 1 if positive else 0,
            "counterfactual_b_without_a_reached": False,
            "same_bound_control_to_b": 4,
            "same_bound_step_b": 4,
            "same_operations_offered_control": 8,
            "same_operations_offered_step_b": 8,
            "chain": {"entry": entry["id"]},
        })
    replayed_arms = {
        "arrangement": {
            "outcome": "satisfied", "demonstrated": 6,
            "demonstrated_without_descending": 4,
        },
        "more_budget_same_operations": {
            "outcome": "satisfied", "the_searcher_was_shown_alive": True,
        },
        "random_target_ceiling": {
            "outcome": "unrunnable", "rivals_that_could_touch_them": 0,
        },
    }
    result = {
        "entries": deepcopy(rows),
        "development_arms": deepcopy(replayed_arms),
        "random_target_is_non_decisive": True,
        "track": "A",
        "model_calls": 0,
        "network_calls": 0,
        "working_tree_was_dirty_at_recording": False,
        "population_is_exhaustive": True,
        "pool_digest": pool["pool_digest"],
        "protocol_raw_sha256": __import__("hashlib").sha256(
            checker.PROTOCOL_PATH.read_bytes()
        ).hexdigest(),
        "prior_attempts": [],
        "attempt": 1,
    }
    result["result_digest"] = digest(result)
    return protocol, pool, rows, {"result": result, "arms": replayed_arms}


def _failed_after(mutator) -> set[str]:
    protocol, pool, rows, evidence = _synthetic_evidence()
    result = evidence["result"]
    replayed_arms = evidence["arms"]
    mutator(result, rows, replayed_arms)
    conditions = checker.run_conditions(protocol, pool, result, rows, replayed_arms)
    return {condition.id for condition in conditions if condition.passed is False}


def test_every_run_condition_has_an_adversarial_failure() -> None:
    protocol, pool, rows, evidence = _synthetic_evidence()
    baseline = checker.run_conditions(protocol, pool, evidence["result"], rows, evidence["arms"])
    assert all(condition.passed for condition in baseline)

    mutations = {
        "P3": lambda _result, replay, _arms: replay[0].update(enabling_demonstrated=False),
        "P4": lambda _result, replay, _arms: next(
            row for row in replay if not row["expected_relation"]
        ).update(enabling_demonstrated=True),
        "P5": lambda _result, replay, _arms: replay[0].update(descent_used=True),
        "P6": lambda _result, replay, _arms: replay[0].update(control_b_from_s0_reached=True),
        "P7": lambda result, _replay, _arms: result["entries"][0]["chain"].update(tampered=True),
        "P8": lambda _result, _replay, arm: arm["arrangement"].update(outcome="refuted"),
        "P9": lambda _result, _replay, arm: arm["more_budget_same_operations"].update(
            outcome="refuted"
        ),
        "P10": lambda result, _replay, _arms: result.update(random_target_is_non_decisive=False),
        "P11": lambda result, _replay, _arms: result.update(track="B"),
    }
    for expected, mutate in mutations.items():
        assert expected in _failed_after(mutate), expected
