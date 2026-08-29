"""Pin the first M115/H60 freeze independently of the mutable plan file.

The analysis plan was promoted byte-for-byte from its reviewed candidate before any H60 bank,
generator-spec freeze, reveal, or qualifying request.  The commitment below is deliberately
hard-coded outside the experiment artifact: recomputing the commitment inside a later-edited plan
must not make CI accept protocol drift after an outcome exists.
"""

from __future__ import annotations

import json

from metamorphosis import m115_carrier_bank as bank


PLAN_COMMITMENT = "95f01bf125a37442bd6748c2b1c018c4c8038553cabc73e9314ee875ce898f5f"


def _read(name: str) -> dict:
    return json.loads((bank.EXPERIMENT_DIRECTORY / name).read_bytes().decode("utf-8"))


def test_the_frozen_m115_plan_commitment_is_pinned_outside_the_plan():
    plan = _read("ANALYSIS_PLAN.json")
    bank.validate_analysis_plan(plan)
    assert plan["plan_commitment_sha256"] == PLAN_COMMITMENT
    assert bank.analysis_plan_commitment(plan) == PLAN_COMMITMENT


def test_the_frozen_m115_plan_is_the_reviewed_candidate_unchanged():
    assert _read("ANALYSIS_PLAN.json") == _read("ANALYSIS_PLAN_CANDIDATE.json")


def test_the_first_freeze_keeps_the_declared_chronology_and_boundaries():
    plan = _read("ANALYSIS_PLAN.json")
    assert plan["milestone"] == "M115"
    assert plan["hypothesis"] == "H60"
    assert plan["frozen_before_generation"] is True
    assert plan["filiation"]["identity_rule_decided_before_m115_freeze"] is True
    assert plan["filiation"]["identity_rule_decided_before_any_m115_bank_existed"] is True
    assert plan["filiation"]["identity_rule_decided_before_any_m115_qualifying_invocation"] is True
    assert plan["provider_selection_rule_adopted_before_any_h60_freeze_or_bank"] is True
    assert plan["predicates_newly_versioned_for_this_milestone"] == []
    assert plan["scientific_target_is_m113s_unchanged"] is True
