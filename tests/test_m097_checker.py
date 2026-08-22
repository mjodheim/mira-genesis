from __future__ import annotations

import hashlib
from copy import deepcopy

from scripts import check_m097_result as checker
from scripts.author_m097_qualification_pool import digest, load_pool


def _evidence():
    pool = load_pool()
    rows = [
        {
            "entry": entry["id"],
            "entry_digest": entry["entry_digest"],
            "inherited": {"execution_confirmed": False},
            "extended": {"execution_confirmed": True},
        }
        for entry in pool["entries"]
    ]
    replay = {
        "inherited_insufficiency": {"outside_constructive_image_at_any_bound": True},
        "inherited_before": {"execution_confirmed": False},
        "acquisition": {
            "candidates_assembled": 2800,
            "accepted_candidates": 1,
            "rejection_counts": {"malformed": 2799},
            "adopted": {"body": ["PUSH_LEFT", "PUSH_RIGHT", "SUB"]},
        },
        "independent_validation": {"accepted": True, "cases_passed": 5},
        "inherited_language_state": {"state_digest": "before", "extensions": []},
        "extended_language_state": {"state_digest": "after", "extensions": [{}]},
        "development_after_registration": {"execution_confirmed": True},
        "qualification": rows,
        "controls": {
            "more_budget_same_language": {"same_language_more_budget_cannot_help": True},
            "acquisition_ablated_correct_worlds": 0,
        },
        "built_not_registered": {"execution_confirmed": False},
        "restored_state_equals_extended": True,
        "conservation": {
            "inherited_unchanged": True,
            "extensions_before": 0,
            "extensions_after": 1,
        },
    }
    result = {
        "scientific_evidence": deepcopy(replay),
        "track": "A",
        "model_calls": 0,
        "network_calls": 0,
        "remote_execution": False,
        "working_tree_was_dirty_at_recording": False,
        "pool_digest": pool["pool_digest"],
        "protocol_raw_sha256": hashlib.sha256(checker.PROTOCOL_PATH.read_bytes()).hexdigest(),
        "prior_attempts": [],
        "attempt": 1,
    }
    result["result_digest"] = digest(result)
    return {}, pool, replay, result


def _failed_after(mutator) -> set[str]:
    protocol, pool, replay, result = _evidence()
    mutator(result, replay)
    return {
        item.id
        for item in checker.run_conditions(protocol, pool, result, replay)
        if item.passed is False
    }


def test_synthetic_baseline_passes_all_run_conditions() -> None:
    protocol, pool, replay, result = _evidence()
    assert all(
        item.passed
        for item in checker.run_conditions(protocol, pool, result, replay)
    )


def test_every_run_condition_can_fail() -> None:
    mutations = {
        "P3": lambda _result, replay: replay["inherited_insufficiency"].update(
            outside_constructive_image_at_any_bound=False
        ),
        "P4": lambda _result, replay: replay["acquisition"].update(
            candidates_assembled=2799
        ),
        "P5": lambda _result, replay: replay["independent_validation"].update(
            accepted=False
        ),
        "P6": lambda _result, replay: replay["extended_language_state"].update(
            extensions=[]
        ),
        "P7": lambda _result, replay: replay["development_after_registration"].update(
            execution_confirmed=False
        ),
        "P8": lambda _result, replay: replay["qualification"][0]["extended"].update(
            execution_confirmed=False
        ),
        "P9": lambda _result, replay: replay["controls"].update(
            acquisition_ablated_correct_worlds=1
        ),
        "P10": lambda _result, replay: replay["built_not_registered"].update(
            execution_confirmed=True
        ),
        "P11": lambda _result, replay: replay["conservation"].update(
            inherited_unchanged=False
        ),
        "P12": lambda result, _replay: result.update(track="B"),
    }
    for expected, mutate in mutations.items():
        assert expected in _failed_after(mutate), expected
