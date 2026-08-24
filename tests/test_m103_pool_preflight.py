from __future__ import annotations

import json
from pathlib import Path

from metamorphosis import m103_runtime as runtime
from scripts import author_m103_qualification_pool as author


ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / "experiments" / "M103" / "QUALIFICATION_POOL.json"
DEVELOPMENT = ROOT / "experiments" / "M103" / "DEVELOPMENT_FIXTURE.json"
VALIDATED_S_PRIME_FEATURES = {
    "OBSERVE_CONTEXT",
    "PARTITION_EQUAL",
    "SYNTHESIZE_PARTITIONS",
    "EMIT_GUARDED",
}


def test_pool_is_exact_deterministic_complete_population() -> None:
    raw = POOL.read_bytes()
    assert raw == runtime.canonical_json(author.build_pool()).encode("ascii")
    pool = json.loads(raw)
    payload = {key: value for key, value in pool.items() if key != "pool_digest"}
    assert pool["pool_digest"] == runtime.digest(payload)
    assert pool["pool_digest"] == "1f1b5d4289685f8401564d0f0e5d7c4f8ffda10561fbeba9ec8a36114e22b59e"
    assert pool["record_count"] == 11
    assert pool["hidden_case_count"] == 16
    assert len(pool["configuration"]["hidden_worlds"]) == 4
    assert len(pool["filesystem"]["hidden_worlds"]) == 4


def test_pool_is_separate_from_development_producer_content() -> None:
    pool_text = POOL.read_text(encoding="ascii").lower()
    for producer_identity in ("north", "south", "amber", "violet", '"outcome"'):
        assert producer_identity not in pool_text
    development = json.loads(DEVELOPMENT.read_text(encoding="ascii"))
    pool = json.loads(POOL.read_text(encoding="ascii"))
    assert pool["development_fixture_digest"] == development["fixture_digest"]
    assert pool["producer_fixture_included"] is False
    assert pool["qualification_only"] is True


def test_pool_contains_no_constructor_solution_identity() -> None:
    text = POOL.read_text(encoding="ascii").lower()
    assert "constructor-s-prime" not in text
    assert "observe_context" not in text
    assert "partition_equal" not in text
    assert "synthesize_partitions" not in text
    assert "emit_guarded" not in text
    assert "accepted_body" not in text
    assert "target_digest" not in text


def test_every_hidden_world_is_real_and_context_decisive() -> None:
    pool = json.loads(POOL.read_text(encoding="ascii"))
    for family in ("configuration", "filesystem"):
        demand = runtime.decode_demand(pool[family]["acquisition"])
        s_prime = runtime.constructor_definition(runtime.S_PRIME_ORIGIN, VALIDATED_S_PRIME_FEATURES)
        acquired = runtime.construct_hypothesis(s_prime, demand)
        assert acquired["confirmed"] is True
        m102_state = json.loads(
            (ROOT / "experiments" / "M102" / "RESULT.json").read_text(encoding="utf-8")
        )["scientific_evidence"]["states"]["U2"]["state"]
        v0 = runtime.create_state(runtime.canonical_json(m102_state).encode("ascii"))
        v1 = runtime.replace_constructor(v0, s_prime)
        consumer_state = runtime.acquire_consumer(v1, demand, register_result=True)["next_state"]
        for world in pool[family]["hidden_worlds"]:
            assert runtime.execute_world(consumer_state, world)["confirmed"] is True


def test_qualification_ambiguity_control_refuses() -> None:
    pool = json.loads(POOL.read_text(encoding="ascii"))
    s_prime = runtime.constructor_definition(runtime.S_PRIME_ORIGIN, VALIDATED_S_PRIME_FEATURES)
    result = runtime.construct_hypothesis(s_prime, pool["ambiguous_control"])
    assert result["confirmed"] is False
    assert result["reason"] == "ambiguous_public_semantics"
    assert result["semantic_classes"] == 2
