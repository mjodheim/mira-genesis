"""What the M114 freeze consumed, pinned by digest.

A freeze is worth what it can be checked against later. These digests are recorded in the same
commit that creates them and pushed before the first delivery attempt, so the order is verifiable
from the history rather than asserted afterwards, and a subsequent edit to the frozen plan or the
frozen spec breaks this rather than passing unnoticed.

This is the **second** freeze this milestone has consumed. The first, at
`b98116d8e8cf92478876bfb9ba6c48c3d541db4b`, was withdrawn before any delivery attempt and before any
bank existed, because a defect in `P15` was still open when it ran;
`experiments/M114/FREEZE_WITHDRAWN.md` records it and it is never to be rewritten as though it had
not existed. Nothing here erases it: `test_the_withdrawn_freeze_stays_visible` asserts that its
record survives.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from metamorphosis import m114_carrier_bank as bank
from metamorphosis import m114_delivery as delivery

ROOT = Path(bank.EXPERIMENT_DIRECTORY).parents[1]

FROZEN_DIGESTS = {
    "ANALYSIS_PLAN.json":
        "cf7b32e5b06f65f874d9b87ae2a52aba170b37ac1ed6ea326c5e8955b0372415",
    "GENERATOR_SPEC.json":
        "98d7cd80f5bee7c88e042ed646eb06832ab5785ad882ad29c5fe9a8eb1a8f8ee",
}
PLAN_COMMITMENT = "e4c659e5c8f5ab0884a4de862876302d7fefc699d914ff0776fefb322ac026af"
SPEC_COMMITMENT = "e12337a4a78045394e4db7b39cb710d3c6dacbd435d01f9a92530e239c288fc3"
REQUEST_BODY = "02a71fb54e492bed151981f6b3f79ec947e7e404bc999caffa37c2c642beaabc"

WITHDRAWN_FREEZE_COMMIT = "b98116d8e8cf92478876bfb9ba6c48c3d541db4b"
WITHDRAWN_PLAN_COMMITMENT = "d191f74df43526b35e39095c62b2329fe47fb467d9c5167f0eb3bf935b1c0339"
WITHDRAWN_SPEC_COMMITMENT = "85b864426fbb97467062978119b60b5c0c65ea93fbee9fafaa739aa85d697c73"


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


def test_the_frozen_plan_carries_the_delivery_rule_the_versioning_and_the_filiation():
    plan = _read("ANALYSIS_PLAN.json")
    assert plan["hypothesis"] == "H59"
    assert plan["max_delivery_attempts"] == delivery.MAX_DELIVERY_ATTEMPTS
    assert plan["max_bank_materializations"] == delivery.MAX_BANK_MATERIALIZATIONS
    assert plan["retry_wait_seconds"] == delivery.RETRY_WAIT_SECONDS
    assert list(plan["never_retried"]) == list(bank.NEVER_RETRIED)

    # The one predicate this milestone versions, declared inside the commitment.
    assert plan["p15_version"] == bank.P15_VERSION
    assert plan["predicates_versioned_for_this_milestone"] == ["P15"]
    assert list(plan["predicates_retaining_m113_scientific_computations"]) == list(
        bank.PREDICATES_RETAINING_M113_COMPUTATIONS
    )
    assert plan["p15_versioning_gives_no_advantage_to_the_hypothesis"] is True
    assert plan["physical_requests_and_model_calls_are_never_carried_in_one_field"] is True
    assert plan["p22_scientific_computation_is_m113s_unchanged"] is True

    assert plan["filiation"] == bank.FILIATION
    for key in (
        "delivery_rule_decided_after_m113_instrument_failure",
        "delivery_rule_decided_before_any_m114_bank_existed",
        "delivery_rule_decided_without_any_observation_of_the_hypothesis",
        "delivery_rule_was_never_part_of_m113",
    ):
        assert plan["filiation"][key] is True


def test_the_withdrawn_freeze_stays_visible():
    """A withdrawn freeze that vanished from the record would be a rewritten history.

    The commit is reachable from `main`, and the record naming it is still here. Neither is allowed
    to quietly disappear once this milestone has a bank to be judged on.
    """
    withdrawn = bank.EXPERIMENT_DIRECTORY / "FREEZE_WITHDRAWN.md"
    assert withdrawn.is_file(), "the withdrawal record may never be deleted"
    text = withdrawn.read_text(encoding="utf-8")
    assert WITHDRAWN_FREEZE_COMMIT[:8] in text
    assert WITHDRAWN_PLAN_COMMITMENT in text
    assert WITHDRAWN_SPEC_COMMITMENT in text

    # The withdrawn commitments must not be the ones now in force, or nothing was withdrawn.
    assert WITHDRAWN_PLAN_COMMITMENT != PLAN_COMMITMENT
    assert WITHDRAWN_SPEC_COMMITMENT != SPEC_COMMITMENT

    resolved = subprocess.run(
        ["git", "cat-file", "-t", WITHDRAWN_FREEZE_COMMIT],
        cwd=ROOT, capture_output=True, text=True,
    )
    if resolved.returncode == 0:
        assert resolved.stdout.strip() == "commit"
    else:
        pytest.skip("this clone cannot resolve the withdrawn freeze commit")


def test_nothing_downstream_of_the_freeze_exists_before_the_first_delivery_attempt():
    """The freeze is one owner gate, not the last. This pins the moment it was consumed."""
    for name in (
        "PUBLIC_BANK_COMMITMENT.json",
        "SEALED_BANK.json.gpg",
        "SYSTEM_PROTOCOL.json",
        "REVEAL_AUTHORIZATION.json",
        "RESULT.json",
    ):
        assert not (bank.EXPERIMENT_DIRECTORY / name).is_file(), (
            "%s exists; the milestone is past the phase this test pins" % name
        )

    report = bank.assess_carrier_bank_readiness(ROOT)
    assert report["phase"] in ("spec_frozen", "generated_sealed")
    assert report["ready_for_reveal"] is False
    assert report["revealed"] is False
