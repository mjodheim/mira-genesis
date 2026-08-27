"""M114's delivery record, pinned. Three capacity rejections, no bank, H59 untested.

The sequence ran to the end of its frozen budget and materialized nothing. This file makes that
outcome immutable in the same way `tests/test_m113_record_is_closed.py` makes its predecessor's
immutable: by digest, and by refusing the existence of anything downstream of it.

An aborted milestone is the one most likely to be quietly reopened later -- there is no result to
contradict, only an absence, and an absence is easy to fill. So the absence is asserted.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from metamorphosis import m114_carrier_bank as bank
from metamorphosis import m114_delivery as delivery
from scripts import check_m114_result as checker

ROOT = Path(bank.EXPERIMENT_DIRECTORY).parents[1]

LEDGER_DIGEST = "96c77d492e20b0621c6dfc3bc06dbb7d6b3c00c3537c204b1a28039d913ebac8"
LEDGER_DIGEST_BEFORE_REDACTION = "6a0684f75e8a9af0e180ebcff7e76b988ae56c5963e92aa1ed5adf8d9e999ebe"
RESPONSE_DIGEST = "f0a0b94cf22fdeeee8fb28abffc34bff0fdc4c74e771c033fa0113e4e4920713"

# The provider's account-identifier shape. Matched, never quoted.
ACCOUNT_IDENTIFIER = re.compile(r"user_[A-Za-z0-9]{16,}")
SPEC_COMMITMENT = "e12337a4a78045394e4db7b39cb710d3c6dacbd435d01f9a92530e239c288fc3"
REQUEST_BODY = "02a71fb54e492bed151981f6b3f79ec947e7e404bc999caffa37c2c642beaabc"


def _ledger() -> dict:
    return json.loads(
        (bank.EXPERIMENT_DIRECTORY / "DELIVERY_LEDGER.json").read_bytes().decode("utf-8")
    )


def test_the_delivery_ledger_is_exactly_what_the_sequence_wrote():
    assert delivery.ledger_digest(_ledger()) == LEDGER_DIGEST


def test_three_attempts_three_capacity_rejections_and_no_bank():
    ledger = _ledger()
    assert [a["outcome"] for a in ledger["attempts"]] == ["capacity_rejected"] * 3
    assert ledger["bank_materialization_index"] is None

    summary = delivery.delivery_summary(ledger)
    assert summary["delivery_attempts"] == delivery.MAX_DELIVERY_ATTEMPTS
    assert summary["capacity_rejections"] == 3
    assert summary["bank_materializations"] == 0
    assert summary["within_budget"] is True


def test_the_record_is_valid_in_full_under_the_frozen_rule():
    """An abort is not a violation. The distinction is the whole reason both verdicts exist."""
    delivery.validate_delivery_ledger(
        _ledger(),
        spec_commitment_sha256=SPEC_COMMITMENT,
        request_body_sha256=REQUEST_BODY,
    )


def test_every_attempt_sent_the_frozen_body_and_nothing_was_served():
    ledger = _ledger()
    assert {a["request_body_sha256"] for a in ledger["attempts"]} == {REQUEST_BODY}
    # Nothing was served, so nothing could have been substituted.
    assert all(a["served_model"] is None for a in ledger["attempts"])
    assert all(a["served_provider"] is None for a in ledger["attempts"])


def test_the_frozen_wait_was_honoured_and_far_exceeded_what_the_provider_asked():
    """The rejection is not a burst a longer pause would have cleared."""
    ledger = _ledger()
    waits = [a["waited_seconds_before_this_attempt"] for a in ledger["attempts"]]
    assert waits == [0, delivery.RETRY_WAIT_SECONDS, delivery.RETRY_WAIT_SECONDS]

    for attempt in ledger["attempts"]:
        metadata = ((attempt["error_body"] or {}).get("error") or {}).get("metadata") or {}
        assert metadata.get("retry_after_seconds") == 1
        assert metadata.get("provider_error_code") == "service_overloaded"
        assert metadata.get("limit_source") == "upstream_provider_shared_pool"


def test_the_three_responses_are_byte_identical():
    """One distinct digest across three attempts a minute apart: the same rejection, reproduced."""
    ledger = _ledger()
    digests = {a["response_sha256"] for a in ledger["attempts"]}
    assert digests == {RESPONSE_DIGEST}


def test_no_attempt_reached_the_model():
    ledger = _ledger()
    assert all(a["completion_present"] is False for a in ledger["attempts"])
    assert all(a["model_execution_cannot_be_excluded"] is False for a in ledger["attempts"])
    assert all(a["status"] == delivery.RETRYABLE_STATUS for a in ledger["attempts"])


def test_the_budget_is_spent_and_no_further_attempt_is_permitted():
    ledger = _ledger()
    assert delivery.retry_permitted("capacity_rejected", len(ledger["attempts"])) is False
    assert ledger["attempts"][-1]["retry_permitted_by_the_frozen_rule"] is False


@pytest.mark.parametrize("name", [
    "GENERATION_RESPONSE.json",
    "PUBLIC_BANK_COMMITMENT.json",
    "SEALED_BANK.json.gpg",
    "SYSTEM_PROTOCOL.json",
    "REVEAL_AUTHORIZATION.json",
    "RESULT.json",
    "CHECK_REPORT.json",
])
def test_nothing_downstream_of_a_bank_may_ever_exist(name):
    """There is no bank, so nothing that presupposes one may appear under this frozen spec."""
    assert not (bank.EXPERIMENT_DIRECTORY / name).is_file(), (
        "%s exists, but M114 materialized no bank; the frozen spec can never authorize one" % name
    )


def test_the_phase_machine_reaches_the_abort_and_no_further():
    report = bank.assess_carrier_bank_readiness(ROOT)
    assert report["phase"] == "spec_frozen"
    assert report["ready_for_reveal"] is False
    assert report["revealed"] is False
    assert any("materialized a bank" in blocker for blocker in report["blockers"])
    assert report["delivery_summary"]["bank_materializations"] == 0


def test_the_corrective_p15_refuses_this_record_for_the_right_reason():
    """The generator half fails; the qualification and delivery halves do not.

    An abort must be distinguishable from a violation and from a negative. If this record ever
    started failing for a delivery reason, the rule would have changed underneath a closed sequence.
    """
    result = {
        "is_a_canonical_attempt": True,
        "model_calls_in_qualification": 0,
        "network_calls_in_qualification": 0,
        "remote_execution_calls_in_qualification": 0,
        "network_guard_selftest_intercepted": True,
        "delivery_ledger": _ledger(),
        "physical_delivery_attempts": 3,
        "bank_materializations": 0,
        "frozen_instrument": {
            "spec_commitment_sha256": SPEC_COMMITMENT,
            "canonical_request_body_sha256": REQUEST_BODY,
            "model": "deepseek/deepseek-v4-flash-0731",
            "provider": "Morph",
            "routing": json.loads(
                (bank.EXPERIMENT_DIRECTORY / "GENERATOR_SPEC.json").read_bytes().decode("utf-8")
            )["routing"],
        },
    }
    boundary = checker.phase_boundary(result)
    assert boundary["qualification_phase"]["holds"] is True
    assert boundary["delivery_phase"]["holds"] is True
    assert boundary["generation_phase"]["holds"] is False
    assert boundary["holds"] is False
    # The two quantities, still separate at the end of the sequence.
    assert boundary["physical_delivery_attempts"] == 3
    assert boundary["bank_materializations"] == 0


def test_the_hypothesis_is_untested_and_the_outcome_record_says_so():
    outcome = (bank.EXPERIMENT_DIRECTORY / "OUTCOME.md").read_text(encoding="utf-8")
    assert "instrument-aborted" in outcome
    assert "H59" in outcome and "untested" in outcome
    assert "not a negative result" in outcome
    assert LEDGER_DIGEST in outcome


def test_the_account_identifier_is_redacted_and_the_redaction_is_recorded():
    """The 429 body is preserved in full as evidence -- of the failure, not of the caller.

    OpenRouter's error envelope carries a `user_id`. It is not the API key and grants no access, but
    it identifies the account and this record is published. It is replaced, the replacement is
    recorded inside the record it touches, and the client now strips such fields at capture so no
    future ledger carries one.
    """
    # Matched by shape, never by value. A test that hard-codes the identifier in order to assert
    # its absence puts the identifier back in the repository -- which is what the first form of
    # this test did, and it is the same defect one level up.
    raw = (bank.EXPERIMENT_DIRECTORY / "DELIVERY_LEDGER.json").read_text(encoding="utf-8")
    assert not ACCOUNT_IDENTIFIER.search(raw), (
        "an account identifier is back in a published artifact"
    )

    redaction = _ledger()["redactions"]
    assert redaction["fields"] == ["error_body.user_id"]
    assert redaction["ledger_digest_before_redaction"] == LEDGER_DIGEST_BEFORE_REDACTION
    assert redaction["client_now_strips_these_fields_at_capture"] is True

    for attempt in _ledger()["attempts"]:
        assert attempt["error_body"]["user_id"].startswith("[redacted")


def test_the_redaction_touched_no_quantity_the_frozen_rule_reads():
    """A redaction that moved a measured value would be an edit to the evidence, not a redaction."""
    for attempt in _ledger()["attempts"]:
        metadata = ((attempt["error_body"] or {}).get("error") or {}).get("metadata") or {}
        assert attempt["status"] == 429
        assert attempt["request_body_sha256"] == REQUEST_BODY
        assert attempt["response_sha256"] == RESPONSE_DIGEST
        assert attempt["completion_present"] is False
        assert attempt["model_execution_cannot_be_excluded"] is False
        assert attempt["outcome"] == "capacity_rejected"
        # The cause the provider named survives the redaction; only the caller is gone.
        assert metadata["provider_error_code"] == "service_overloaded"
        assert metadata["limit_source"] == "upstream_provider_shared_pool"
        assert metadata["is_byok"] is False


def test_the_client_strips_identity_from_any_future_error_body():
    from scripts.run_m114_generation import _without_identity

    stripped = _without_identity({
        "error": {"code": 429, "metadata": {"provider_name": "Morph"}},
        "user_id": "user_secret",
        "nested": [{"account_id": "acct_secret", "keep": 1}],
    })
    assert stripped["user_id"].startswith("[redacted")
    assert stripped["nested"][0]["account_id"].startswith("[redacted")
    assert stripped["nested"][0]["keep"] == 1
    assert stripped["error"]["metadata"]["provider_name"] == "Morph"
