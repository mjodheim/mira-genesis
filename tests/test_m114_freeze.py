"""What the M114 freeze consumed, pinned by digest.

A freeze is worth what it can be checked against later. These digests are recorded in the same
commit that creates them, before any delivery attempt exists to be judged against them, so a
subsequent edit to the frozen plan or the frozen spec breaks this rather than passing unnoticed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from metamorphosis import m114_carrier_bank as bank
from metamorphosis import m114_delivery as delivery

ROOT = Path(bank.EXPERIMENT_DIRECTORY).parents[1]

FROZEN_DIGESTS = {
    "ANALYSIS_PLAN.json":
        "cd359081dabb3ba8c57133de0538bea648159bef1e97d8f4a8f59819adb868d9",
    "GENERATOR_SPEC.json":
        "bb56275a5ed115a607346a0a8210ca1122c8787f78a1d3238a981576d7b523dd",
}
PLAN_COMMITMENT = "d191f74df43526b35e39095c62b2329fe47fb467d9c5167f0eb3bf935b1c0339"
SPEC_COMMITMENT = "85b864426fbb97467062978119b60b5c0c65ea93fbee9fafaa739aa85d697c73"
REQUEST_BODY = "02a71fb54e492bed151981f6b3f79ec947e7e404bc999caffa37c2c642beaabc"


def _read(name: str) -> dict:
    return json.loads((bank.EXPERIMENT_DIRECTORY / name).read_bytes().decode("utf-8"))


@pytest.mark.parametrize("name,digest", sorted(FROZEN_DIGESTS.items()))
def test_the_frozen_artifacts_are_exactly_what_the_freeze_wrote(name, digest):
    path = bank.EXPERIMENT_DIRECTORY / name
    assert path.is_file(), "%s was frozen and must not disappear" % name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest


def test_the_frozen_plan_and_spec_validate_against_their_own_contracts():
    plan = _read("ANALYSIS_PLAN.json")
    spec = _read("GENERATOR_SPEC.json")
    bank.validate_analysis_plan(plan)
    bank.validate_generator_spec(
        spec, root=ROOT, plan_commitment_sha256=plan["plan_commitment_sha256"]
    )
    assert plan["plan_commitment_sha256"] == PLAN_COMMITMENT
    assert spec["spec_commitment_sha256"] == SPEC_COMMITMENT
    assert spec["analysis_plan_commitment_sha256"] == PLAN_COMMITMENT
    assert spec["frozen_before_generation"] is True
    assert "unset_before_freeze" not in spec


def test_the_frozen_plan_is_the_candidate_unchanged():
    """The freeze consumed a plan written before it, rather than writing one at the freeze."""
    assert _read("ANALYSIS_PLAN.json") == _read("ANALYSIS_PLAN_CANDIDATE.json")


def test_the_freeze_changed_the_specs_status_and_nothing_it_will_send():
    candidate = _read("GENERATOR_SPEC_CANDIDATE.json")
    frozen = _read("GENERATOR_SPEC.json")
    moved = {key for key in set(frozen) | set(candidate) if frozen.get(key) != candidate.get(key)}
    assert moved == {
        "frozen_at", "frozen_before_generation", "spec_commitment_sha256", "unset_before_freeze",
    }, "the freeze may change the instrument's status, never the request it will send"
    assert frozen["canonical_request_body"] == candidate["canonical_request_body"]
    assert frozen["canonical_request_body_sha256"] == REQUEST_BODY


def test_the_frozen_spec_is_the_predecessors_identity():
    """M114 replicates M113's instrument. A different identity would be a different experiment."""
    m113 = json.loads(
        (Path("experiments/M113") / "GENERATOR_SPEC.json").read_bytes().decode("utf-8")
    )
    frozen = _read("GENERATOR_SPEC.json")
    for key in ("generator_identity", "sampling", "routing", "canonical_request_body"):
        assert frozen[key] == m113[key], "M114 moved %r away from M113's instrument" % key


def test_the_frozen_plan_carries_the_delivery_rule_and_the_filiation():
    plan = _read("ANALYSIS_PLAN.json")
    assert plan["hypothesis"] == "H59"
    assert plan["max_delivery_attempts"] == delivery.MAX_DELIVERY_ATTEMPTS
    assert plan["max_bank_materializations"] == delivery.MAX_BANK_MATERIALIZATIONS
    assert plan["retry_wait_seconds"] == delivery.RETRY_WAIT_SECONDS
    assert list(plan["never_retried"]) == list(bank.NEVER_RETRIED)
    assert plan["filiation"] == bank.FILIATION
    for key in (
        "delivery_rule_decided_after_m113_instrument_failure",
        "delivery_rule_decided_before_any_m114_bank_existed",
        "delivery_rule_decided_without_any_observation_of_the_hypothesis",
        "delivery_rule_was_never_part_of_m113",
    ):
        assert plan["filiation"][key] is True


def test_no_bank_reveal_or_result_exists_under_this_freeze():
    """The freeze is the second owner gate, not the last. Nothing downstream of it may exist yet."""
    for name in (
        "DELIVERY_LEDGER.json",
        "GENERATION_RESPONSE.json",
        "PUBLIC_BANK_COMMITMENT.json",
        "SEALED_BANK.json.gpg",
        "SYSTEM_PROTOCOL.json",
        "REVEAL_AUTHORIZATION.json",
        "RESULT.json",
        "CHECK_REPORT.json",
    ):
        assert not (bank.EXPERIMENT_DIRECTORY / name).is_file(), (
            "%s exists; the milestone is past the phase this test pins" % name
        )

    report = bank.assess_carrier_bank_readiness(ROOT)
    assert report["phase"] == "spec_frozen"
    assert report["ready_for_reveal"] is False
    assert report["revealed"] is False
