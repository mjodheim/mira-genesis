"""An absent router field must never be recorded as an observed empty one.

`safe_router_metadata` initialised `attempts` and `pipeline` to `[]` and filled them only when the
source key was a list, so a field the API never emitted was rendered as one observed to be empty.
`attest_router_metadata` then tested that fabricated list, which made three of its checks
structurally true: a response carrying no routing evidence at all passed exactly as one carrying
positive evidence, and it passed in the direction that flatters the route.

M117 established that this API emits neither key, on success or on failure, so every such empty
list in the project's record is manufactured rather than observed.

The verdict these checks produced is not disputed and is deliberately preserved: a direct strategy
with routing attempt 1 and exactly one selected endpoint does exclude fallback. What changes is
that the verdict now rests on evidence the API actually emits.
"""

from __future__ import annotations

import pytest

from metamorphosis.m115_identity import (
    CANONICAL_CHECKPOINT,
    REQUESTED_MODEL,
    SELECTED_PROVIDER,
    attest_router_metadata,
    safe_router_metadata,
)


def _raw(**overrides):
    base = {
        "attempt": 1, "strategy": "direct", "requested": REQUESTED_MODEL, "is_byok": False,
        "endpoints": {"total": 30, "available": [
            {"model": CANONICAL_CHECKPOINT, "provider": SELECTED_PROVIDER, "selected": True}]},
    }
    base.update(overrides)
    return base


# -------------------------------------------------------------------------------------------
# The projection
# -------------------------------------------------------------------------------------------

def test_an_absent_field_stays_absent():
    projected = safe_router_metadata(_raw())
    assert projected["attempts"] is None
    assert projected["pipeline"] is None


def test_an_observed_empty_list_stays_an_empty_list():
    projected = safe_router_metadata(_raw(attempts=[], pipeline=[]))
    assert projected["attempts"] == []
    assert projected["pipeline"] == []


def test_absent_and_observed_empty_are_distinguishable():
    """The whole point: these two must not collapse to the same record."""
    assert safe_router_metadata(_raw())["attempts"] \
        != safe_router_metadata(_raw(attempts=[]))["attempts"]


def test_a_populated_attempt_list_still_projects_its_records():
    projected = safe_router_metadata(_raw(
        attempts=[{"provider": SELECTED_PROVIDER, "model": CANONICAL_CHECKPOINT, "status": 200}]))
    assert projected["attempts"] == [
        {"provider": SELECTED_PROVIDER, "model": CANONICAL_CHECKPOINT, "status": 200}]


def test_the_projection_still_drops_unknown_fields():
    """Credentials and arbitrary provider metadata must not survive, absence fix or not."""
    projected = safe_router_metadata(_raw(api_key="sk-live-000", account={"id": 1}))
    assert "api_key" not in projected
    assert "account" not in projected
    assert "sk-live-000" not in str(projected)


# -------------------------------------------------------------------------------------------
# The verdict is preserved, on real evidence
# -------------------------------------------------------------------------------------------

def test_the_verdict_is_unchanged_whether_the_fields_are_absent_or_observed_empty():
    absent = attest_router_metadata(safe_router_metadata(_raw()))
    observed = attest_router_metadata(safe_router_metadata(_raw(attempts=[], pipeline=[])))
    assert absent["holds"] is True
    assert observed["holds"] is True
    assert absent["failed_checks"] == observed["failed_checks"] == []


def test_the_projection_is_where_observed_and_inferred_are_distinguished():
    """Not the attestation: it is compared for full equality against a closed milestone's record."""
    assert safe_router_metadata(_raw())["attempts"] is None
    assert safe_router_metadata(_raw(attempts=[]))["attempts"] == []


def test_the_attestation_gains_no_key_that_would_break_a_committed_comparison():
    """M115 verification requires the recomputed attestation to equal the one it committed."""
    absent = attest_router_metadata(safe_router_metadata(_raw()))
    assert set(absent) == {"identity_version", "requested_model", "canonical_checkpoint",
                           "selected_provider", "checks", "failed_checks", "holds",
                           "is_byok_observed"}
    assert set(absent["checks"]) == {
        "router_metadata_present", "requested_alias_exact", "direct_strategy",
        "one_router_attempt", "one_selected_endpoint", "selected_provider_exact",
        "selected_checkpoint_exact", "no_fallback_attested", "pipeline_present_as_list",
        "no_pipeline_intervention"}


# -------------------------------------------------------------------------------------------
# No-fallback now requires evidence rather than a fabricated list
# -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("override,clause", [
    ({"strategy": "fallback"}, "direct_strategy"),
    ({"attempt": 2}, "one_router_attempt"),
])
def test_absent_attempts_no_longer_excuse_a_missing_routing_fact(override, clause):
    """Previously the fabricated [] carried no_fallback regardless of these."""
    attestation = attest_router_metadata(safe_router_metadata(_raw(**override)))
    assert attestation["holds"] is False
    assert clause in attestation["failed_checks"]
    assert "no_fallback_attested" in attestation["failed_checks"]


def test_two_selected_endpoints_defeat_no_fallback_when_attempts_are_absent():
    metadata = _raw()
    metadata["endpoints"]["available"].append(
        {"model": CANONICAL_CHECKPOINT, "provider": "Other", "selected": True})
    attestation = attest_router_metadata(safe_router_metadata(metadata))
    assert attestation["holds"] is False
    assert "no_fallback_attested" in attestation["failed_checks"]


def test_a_populated_attempt_list_is_still_judged_on_its_records():
    bad = attest_router_metadata(safe_router_metadata(_raw(
        attempts=[{"provider": SELECTED_PROVIDER, "model": CANONICAL_CHECKPOINT, "status": 200},
                  {"provider": "Other", "model": "x", "status": 503}])))
    assert bad["holds"] is False
    assert "no_fallback_attested" in bad["failed_checks"]


def test_a_reported_pipeline_intervention_still_fails():
    attestation = attest_router_metadata(
        safe_router_metadata(_raw(pipeline=[{"type": "moderation", "name": "x"}])))
    assert attestation["holds"] is False
    assert "no_pipeline_intervention" in attestation["failed_checks"]


def test_missing_metadata_entirely_still_fails_closed():
    assert attest_router_metadata(None)["holds"] is False
    assert "router_metadata_present" in attest_router_metadata(None)["failed_checks"]
