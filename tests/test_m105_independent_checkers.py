from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from metamorphosis import m105_runtime as runtime
from scripts import check_m105_definitions as definition_checker
from scripts import check_m105_m104_closure as closure_checker
from scripts import check_m105_semantics as semantic_checker


ROOT = Path(__file__).resolve().parents[1]
PREDECESSOR = ROOT / "experiments" / "M105" / "M104_V3.json"
DEVELOPMENT = ROOT / "experiments" / "M105" / "DEVELOPMENT_FIXTURE.json"
POOL = ROOT / "experiments" / "M105" / "QUALIFICATION_POOL.json"


def final_state() -> dict[str, object]:
    w0 = runtime.create_state(PREDECESSOR.read_bytes())
    development = json.loads(DEVELOPMENT.read_text(encoding="ascii"))
    pool = json.loads(POOL.read_text(encoding="ascii"))
    w1 = runtime.acquire_feature(w0, development, register_result=True)["next_state"]
    w2 = runtime.acquire_consumer(
        w1, pool["json_demand"], register_result=True
    )["next_state"]
    return runtime.acquire_consumer(
        w2, pool["sqlite_demand"], register_result=True
    )["next_state"]


def test_independent_semantic_census_and_feature_validation() -> None:
    state = final_state()
    report = semantic_checker.validate(runtime.semantic_census(), state["features"][0])
    assert report["confirmed"] is True
    assert report["semantic_count"] == 16
    assert report["feature"]["content_address_valid"] is True


def test_independent_definition_validation_checks_live_dependency() -> None:
    state = final_state()
    report = definition_checker.validate(runtime.encode_state(state))
    assert report["confirmed"] is True
    assert [item["family"] for item in report["definitions"]] == [
        "json_document",
        "sqlite",
    ]
    broken = copy.deepcopy(state)
    broken["features"] = []
    payload = {key: value for key, value in broken.items() if key != "state_digest"}
    broken["state_digest"] = runtime.digest(payload)
    with pytest.raises(ValueError, match="live feature dependency is missing"):
        definition_checker.validate(runtime.canonical_json(broken).encode("ascii"))


def test_independent_m104_closure_has_fresh_context_witnesses() -> None:
    report = closure_checker.validate(PREDECESSOR.read_bytes())
    assert report["confirmed"] is True
    assert report["budget_independent"] is True
    assert all(item["fresh_context_absent"] for item in report["definitions"])


def test_independent_checkers_reject_content_mutation() -> None:
    state = final_state()
    broken = copy.deepcopy(state)
    broken["features"][0]["truth_table"][0] = not broken["features"][0][
        "truth_table"
    ][0]
    payload = {key: value for key, value in broken.items() if key != "state_digest"}
    broken["state_digest"] = runtime.digest(payload)
    with pytest.raises(ValueError, match="feature semantics mismatch"):
        definition_checker.validate(runtime.canonical_json(broken).encode("ascii"))
