"""Safety boundaries for M096's one-shot local qualification."""

from __future__ import annotations

from copy import deepcopy

import pytest

from scripts import run_m096_qualification as runner
from scripts.author_m096_qualification_pool import digest, load_pool


def test_runner_refuses_draft_protocol() -> None:
    protocol = {
        "status": "draft",
        "qualification_population": {"pool_digest": load_pool()["pool_digest"]},
    }
    with pytest.raises(runner.QualificationRefused, match="not frozen"):
        runner.require_frozen(protocol, load_pool())


def test_materialize_refuses_without_explicit_arming() -> None:
    with pytest.raises(runner.QualificationRefused, match="requires arming"):
        runner.materialize()


def test_runner_refuses_unbound_pool_before_reading_mechanism() -> None:
    pool = load_pool()
    protocol = {
        "status": "frozen",
        "qualification_population": {"pool_digest": "0" * 64},
    }
    with pytest.raises(runner.QualificationRefused, match="pool digest"):
        runner.require_frozen(protocol, pool)


def test_entry_mutation_breaks_its_content_address() -> None:
    changed = deepcopy(load_pool()["entries"][0])
    changed["inner_call_sites"] += 1
    assert changed["entry_digest"] != digest(
        {key: value for key, value in changed.items() if key != "entry_digest"}
    )


def test_exact_and_legacy_records_are_both_required() -> None:
    entry = load_pool()["entries"][0]

    class Evidence:
        facts = {}
        enabling_demonstrated = False
        descended_to = ""
        control = None
        step_a = None
        step_b = None
        counterfactual = None
        step_a_identified_by = "nothing_reached"

        def to_dict(self):
            return {"schema": "synthetic"}

    row = runner.paired_entry_record(entry, Evidence(), Evidence())
    assert set(row) >= {"contract_safe", "legacy_subset"}
    assert row["contract_safe"] is not row["legacy_subset"]
