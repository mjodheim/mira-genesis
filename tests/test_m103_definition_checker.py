from __future__ import annotations

import pytest

from metamorphosis import m103_runtime as runtime
from scripts import check_m103_definitions as checker
from tests.test_m103_runtime import (
    configuration_demand,
    development_demand,
    filesystem_demand,
    m102_u2_bytes,
)


M102_U2_RAW_SHA256 = "3bad4d5400e8d9a11b15ba596336925823ffb4064a5bbe38f93f64b7384a198d"
M102_U2_STATE_DIGEST = "fbf7b0232aa8adf4e67513719c63f19f28c1b7e8b86437af1135ff18335d3a0e"
M101_T2_RAW_SHA256 = "cd5b5994e5a252599807e9ddc2b5733efaf176fe23dd05055b50d883bde0b7a0"
M100_S3_RAW_SHA256 = "fba316a10f294fea4124e460e5a7987cc00b46d3d0e32260ea8cad80b39cf9ac"


def v3_bytes() -> bytes:
    v0 = runtime.create_state(m102_u2_bytes())
    v1 = runtime.acquire_constructor(v0, development_demand(), register_result=True)["next_state"]
    v2 = runtime.acquire_consumer(v1, configuration_demand(), register_result=True)["next_state"]
    v3 = runtime.acquire_consumer(v2, filesystem_demand(), register_result=True)["next_state"]
    return runtime.encode_state(v3)


def validate(raw: bytes) -> dict[str, object]:
    return checker.validate(
        raw,
        expected_m102_sha256=M102_U2_RAW_SHA256,
        expected_m102_state_digest=M102_U2_STATE_DIGEST,
        expected_m101_sha256=M101_T2_RAW_SHA256,
        expected_m100_sha256=M100_S3_RAW_SHA256,
    )


def test_checker_independently_validates_v3_graph() -> None:
    report = validate(v3_bytes())
    assert report["confirmed"] is True
    assert report["scientific_verdict"] is False
    assert report["constructor"]["required_feature_set_complete"] is True
    assert report["definition_count"] == 2
    assert [item["family"] for item in report["definitions"]] == [
        "configuration",
        "filesystem",
    ]
    assert all(item["context_conditioned"] for item in report["definitions"])
    assert all(item["acquired_by_current_constructor"] for item in report["definitions"])
    assert report["independent_of_m103_runtime_search_and_qualification"] is True


def test_checker_rejects_mutated_definition_even_with_outer_digest_repaired() -> None:
    value = runtime.decode_state(v3_bytes())
    value["definitions"][0]["dispatch"][0]["body"] = value["definitions"][0]["dispatch"][1][
        "body"
    ]
    payload = {key: item for key, item in value.items() if key != "state_digest"}
    value["state_digest"] = runtime.digest(payload)
    with pytest.raises(ValueError, match="definition content address mismatch"):
        validate(runtime.canonical_json(value).encode("ascii"))


def test_checker_rejects_out_of_vocabulary_consumer_feature() -> None:
    value = runtime.decode_state(v3_bytes())
    value["constructor"]["features"] = ["filesystem"]
    constructor_payload = {
        "schema": value["constructor"]["schema"],
        "origin": value["constructor"]["origin"],
        "features": value["constructor"]["features"],
    }
    value["constructor"]["constructor_id"] = (
        f"constructor-s-prime-{runtime.digest(constructor_payload)[:16]}"
    )
    payload = {key: item for key, item in value.items() if key != "state_digest"}
    value["state_digest"] = runtime.digest(payload)
    with pytest.raises(ValueError, match="feature set is invalid"):
        validate(runtime.canonical_json(value).encode("ascii"))
