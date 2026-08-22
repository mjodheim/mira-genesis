"""Adversarial mutations for every run-dependent M096 checker condition."""

from __future__ import annotations

import hashlib
from copy import deepcopy

from scripts import check_m096_result as checker
from scripts.author_m096_qualification_pool import digest, load_pool


def _arm(entry: dict, *, exact: bool) -> dict:
    positive = bool(entry["expected_relation"])
    legacy_success = positive and (
        exact or entry["structure"] == "complete_minimal_contract"
    )
    demonstrated = positive if exact else legacy_success
    requirement = [["left", "primary", None], ["right", "secondary", None]]
    method = "def as_mapping(self):\n    return {'left': self.primary, 'right': self.secondary}"
    return {
        "entry": entry["id"],
        "entry_digest": entry["entry_digest"],
        "structure": entry["structure"],
        "arrangement": entry["arrangement"],
        "expected_relation": positive,
        "expected_descent": entry["expected_descent"],
        "world": {"inner_call_sites": entry["inner_call_sites"]},
        "enabling_demonstrated": demonstrated,
        "descent_used": bool(entry["expected_descent"]) if demonstrated else False,
        "control_b_from_s0_reached": False,
        "a_reached": True if demonstrated else None,
        "a_identified_by": (
            "the_nested_operation_became_applicable" if demonstrated else "nothing_reached"
        ),
        "b_reached": True if demonstrated else False,
        "b_confirmed_by_execution": 1 if demonstrated else 0,
        "counterfactual_b_without_a_reached": False,
        "same_bound_control_to_b": 4,
        "same_bound_step_b": 4,
        "same_operations_offered_control": 8,
        "same_operations_offered_step_b": 8,
        "chain": {
            "step_a": {
                "adopted_method": method if demonstrated else None,
                "requirement": requirement if demonstrated else [],
            }
        },
    }


def _evidence() -> tuple[dict, dict, list[dict], dict]:
    pool = load_pool()
    rows = [
        {
            "entry": entry["id"],
            "entry_digest": entry["entry_digest"],
            "structure": entry["structure"],
            "arrangement": entry["arrangement"],
            "expected_relation": entry["expected_relation"],
            "expected_descent": entry["expected_descent"],
            "contract_safe": _arm(entry, exact=True),
            "legacy_subset": _arm(entry, exact=False),
        }
        for entry in pool["entries"]
    ]
    result = {
        "entries": deepcopy(rows),
        "track": "A",
        "model_calls": 0,
        "network_calls": 0,
        "remote_execution": False,
        "working_tree_was_dirty_at_recording": False,
        "population_is_exhaustive": True,
        "pool_digest": pool["pool_digest"],
        "protocol_raw_sha256": hashlib.sha256(checker.PROTOCOL_PATH.read_bytes()).hexdigest(),
        "prior_attempts": [],
        "attempt": 1,
    }
    result["result_digest"] = digest(result)
    return {}, pool, rows, result


def _failed_after(mutator) -> set[str]:
    protocol, pool, replay, result = _evidence()
    mutator(result, replay)
    return {
        condition.id
        for condition in checker.run_conditions(protocol, pool, result, replay)
        if condition.passed is False
    }


def test_synthetic_positive_baseline_passes_every_run_condition() -> None:
    protocol, pool, replay, result = _evidence()
    conditions = checker.run_conditions(protocol, pool, result, replay)
    assert all(condition.passed for condition in conditions)


def test_every_run_condition_has_an_adversarial_failure() -> None:
    mutations = {
        "P3": lambda _result, replay: replay[0]["contract_safe"].update(
            enabling_demonstrated=False
        ),
        "P4": lambda _result, replay: next(
            row for row in replay if not row["expected_relation"]
        )["contract_safe"].update(enabling_demonstrated=True),
        "P5": lambda _result, replay: replay[0]["contract_safe"].update(descent_used=True),
        "P6": lambda _result, replay: replay[0]["contract_safe"].update(
            control_b_from_s0_reached=True
        ),
        "P7": lambda _result, replay: replay[0]["contract_safe"]["chain"]["step_a"].update(
            adopted_method=(
                "def as_mapping(self):\n"
                "    return {'left': self.primary, 'right': self.secondary, 'extra': self.extra}"
            )
        ),
        "P8": lambda _result, replay: next(
            row
            for row in replay
            if row["structure"] == "complete_minimal_contract" and row["expected_relation"]
        )["legacy_subset"].update(enabling_demonstrated=False),
        "P9": lambda result, _replay: result["entries"][0]["contract_safe"]["chain"].update(
            tampered=True
        ),
        "P10": lambda result, _replay: result.update(track="B"),
    }
    for expected, mutate in mutations.items():
        assert expected in _failed_after(mutate), expected
