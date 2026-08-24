from __future__ import annotations

from scripts import build_m105_protocol as builder


def test_candidate_binds_complete_apparatus_and_unique_attempt_policy() -> None:
    value = builder.candidate("experiment/m105-candidate-source-v1")
    payload = {key: item for key, item in value.items() if key != "candidate_digest"}
    assert value["candidate_digest"] == builder.digest(payload)
    assert value["bound_files"] == builder.bound_files()
    assert value["decisive_conditions"] == [f"P{index}" for index in range(1, 17)]
    assert value["canonical_result_policy"]["canonical_attempts"] == 1
    assert value["canonical_result_policy"]["canonical_checker_attempts"] == 1
    assert value["canonical_run_allowed"] is False


def test_final_protocol_can_only_arm_the_bound_candidate() -> None:
    if not builder.CANDIDATE_PATH.exists():
        return
    candidate_value = __import__("json").loads(
        builder.CANDIDATE_PATH.read_text(encoding="ascii")
    )
    value = builder.final_protocol(
        candidate_value,
        "experiment/m105-accepted-protocol-candidate-v1",
        "experiment/m105-frozen-protocol-v1",
    )
    payload = {key: item for key, item in value.items() if key != "protocol_digest"}
    assert value["protocol_digest"] == builder.digest(payload)
    assert value["bound_files"] == candidate_value["bound_files"]
    assert value["status"] == "frozen_protocol_owner_authorized"
    assert value["canonical_run_allowed"] is True
