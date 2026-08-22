from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from metamorphosis import m100_runtime as runtime

ROOT = Path(__file__).resolve().parents[1]


def _migrated_state() -> dict[str, object]:
    result = json.loads((ROOT / "experiments/M097/RESULT.json").read_text(encoding="utf-8"))
    raw = result["scientific_evidence"]["serialized_state"].encode("ascii")
    return runtime.migrate_m097_state(raw)


def _pre_acquisition_state() -> dict[str, object]:
    result = json.loads((ROOT / "experiments/M097/RESULT.json").read_text(encoding="utf-8"))
    state = result["scientific_evidence"]["inherited_language_state"]
    return runtime.migrate_m097_state(runtime.canonical_json(state).encode("ascii"))


def _three_states():
    s1 = _migrated_state()
    acquisition_b = runtime.acquire(s1, (1, 1), 4, register=True)
    s2 = acquisition_b["next_state"]
    acquisition_c = runtime.acquire(s2, (1, 2), 5, register=True)
    return s1, s2, acquisition_c["next_state"], acquisition_b, acquisition_c


def test_cumulative_chain_only_reaches_each_target_after_predecessor_registration() -> None:
    s1, s2, s3, acquisition_b, acquisition_c = _three_states()
    assert runtime.operation_signatures(s1) == {
        "derived-expression-3abd091fefb37019": (1, -1)
    }
    assert acquisition_b["accepted_candidates"] == 2
    assert acquisition_b["shortest_accepted_length"] == 4
    assert acquisition_c["accepted_candidates"] == 6
    assert acquisition_c["shortest_accepted_length"] == 5
    assert list(runtime.operation_signatures(s3).values()) == [(1, -1), (1, 1), (1, 2)]
    assert runtime.acquire(s1, (1, 2), 5, register=False)["accepted_candidates"] == 0
    assert runtime.acquire(s2, (1, 2), 5, register=False)["accepted_candidates"] == 6
    assert runtime.acquire(_pre_acquisition_state(), (1, 1), 4, register=False)[
        "accepted_candidates"
    ] == 0


def test_registration_conserves_every_prior_definition_byte_for_byte() -> None:
    s1, s2, s3, _acquisition_b, _acquisition_c = _three_states()
    assert s2["operations"][:1] == s1["operations"]
    assert s3["operations"][:2] == s2["operations"]
    assert runtime.canonical_json(s2["operations"][:1]) == runtime.canonical_json(s1["operations"])
    assert runtime.canonical_json(s3["operations"][:2]) == runtime.canonical_json(s2["operations"])


def test_new_definition_cannot_use_an_unregistered_or_host_binary_operator() -> None:
    s1 = _migrated_state()
    illegal = runtime._definition(["PUSH_LEFT", "PUSH_RIGHT", "ADD"], [], "m100-cycle")
    state = runtime._state(
        str(s1["inherited_digest"]), str(s1["origin_m097_state_digest"]),
        list(s1["operations"]) + [illegal],
    )
    with pytest.raises(ValueError, match="bypasses prior"):
        runtime.decode_state(runtime.canonical_json(state).encode("ascii"))

    missing = runtime._definition(
        ["PUSH_LEFT", "PUSH_RIGHT", "CALL:not-registered"], ["not-registered"],
        "m100-cycle",
    )
    state["operations"][-1] = missing
    state = runtime._state(
        str(s1["inherited_digest"]), str(s1["origin_m097_state_digest"]), state["operations"]
    )
    with pytest.raises(ValueError, match="bypasses prior|missing or forward"):
        runtime.decode_state(runtime.canonical_json(state).encode("ascii"))


def test_digest_corruption_and_definition_ablation_fail_closed() -> None:
    _s1, _s2, s3, _b, _c = _three_states()
    corrupted = deepcopy(s3)
    corrupted["state_digest"] = "0" * 64
    with pytest.raises(ValueError, match="digest mismatch"):
        runtime.decode_state(runtime.canonical_json(corrupted).encode("ascii"))
    ablated = runtime._state(
        str(s3["inherited_digest"]), str(s3["origin_m097_state_digest"]),
        [s3["operations"][0], s3["operations"][2]],
    )
    with pytest.raises(ValueError, match="bypasses prior|missing or forward"):
        runtime.decode_state(runtime.canonical_json(ablated).encode("ascii"))


def test_live_expansion_retains_transitive_calls() -> None:
    _s1, _s2, s3, _b, _c = _three_states()
    c_id = s3["operations"][2]["operation_id"]
    expression = runtime.live_expression(s3, c_id)
    assert expression[0] == "sub"
    assert "add" not in repr(expression)
    assert runtime.operation_signatures(s3)[c_id] == (1, 2)
    assert s3["operations"][2]["dependency_ids"] == [s3["operations"][1]["operation_id"]]
    assert s3["operations"][1]["dependency_ids"] == [s3["operations"][0]["operation_id"]]
