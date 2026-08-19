"""M094 is a draft under audit, and nothing about it may read as precommitted.

Two things are guarded here.

First, the draft protocol must stay a draft. A protocol that quietly acquires a frozen
status, a hypothesis that quietly acquires support, or qualification data appearing before a
freeze are exactly the failures the project's retry and freeze discipline exists to prevent.

Second, the design audit must remain a working instrument. Its four findings are measured
rather than asserted, so the checks below drive it with synthetic components whose defects are
known, instead of pinning the numbers it currently reports on the real repository.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from audit_m094_design import (
    capability_presence_blindness,
    corrected_measure_threshold_sensitivity,
    indicator_discrimination,
    selection_determinism,
    template_authorship,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
PROTOCOL = REPO_ROOT / "experiments" / "M094" / "PROTOCOL.json"
AUDIT = REPO_ROOT / "experiments" / "M094" / "DESIGN_AUDIT.json"


@pytest.fixture(scope="module")
def protocol() -> dict[str, object]:
    return json.loads(PROTOCOL.read_text(encoding="utf-8"))


# ── The draft must stay a draft ──────────────────────────────────────


def test_protocol_is_frozen_and_says_what_that_binds(protocol: dict[str, object]) -> None:
    """Frozen by the owner, before any qualification data existed.

    A freeze is only worth anything if what it binds is written down. The
    eligible set must be enumerated rather than described, the qualification pool
    must exist and be bound by digest, and the retry discipline must be explicit.
    """

    assert protocol["status"] == "FROZEN"
    assert protocol["frozen_before_any_qualification_data_existed"] is True
    assert protocol["date_frozen"] == "2026-08-18"

    eligible = protocol["eligible_components"]["enumerated"]
    assert eligible == [
        "mira_core/contracts.py",
        "mira_core/memory.py",
        "mira_core/safety.py",
    ], "the eligible set must be enumerated, not described"

    qualification = protocol["qualification"]
    pool = REPO_ROOT / qualification["pool"]
    assert pool.exists(), "the protocol binds a pool that must exist at the freeze"

    committed = json.loads(pool.read_text(encoding="utf-8"))
    assert committed["pool_digest"] == qualification["pool_digest"]
    assert len(committed["entries"]) == qualification["pool_entries"]

    note = protocol["status_note"]
    assert "may not be repaired to save a result" in note


def test_the_freeze_did_not_smuggle_in_a_result() -> None:
    """A protocol frozen after a result is not a precommitment.

    Asserted, until the canonical run of 19 August 2026, by the absence of the artifacts. That
    absence is gone, so the property is asserted where it still lives: the result records the
    commit it ran at, and that commit is a descendant of the freeze rather than the freeze
    itself. A result cannot have been smuggled into a freeze it postdates.
    """

    result_path = PROTOCOL.parent / "RESULT.json"
    if not result_path.exists():
        # Before a run, absence is still the strongest available statement.
        forbidden = ("RESULT.json", "QUALIFICATION.json", "REGISTER_CLAIM.json")
        present = [name for name in forbidden if (PROTOCOL.parent / name).exists()]
        assert present == [], f"qualification artefacts exist at the freeze: {present}"
        return

    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["is_rehearsal"] is False
    assert result["source_commit"], "the result records no commit, so nothing can be ordered"

    freeze = subprocess.run(
        ["git", "rev-parse", "9b69d7f^{commit}"],
        cwd=PROTOCOL.parents[1], capture_output=True, text=True,
    )
    if freeze.returncode != 0:  # a shallow clone cannot order commits
        pytest.skip("the freeze commit is not present in this clone")
    ordered = subprocess.run(
        ["git", "merge-base", "--is-ancestor", freeze.stdout.strip(), result["source_commit"]],
        cwd=PROTOCOL.parents[1], capture_output=True, text=True,
    )
    assert ordered.returncode == 0, (
        "the run's commit does not descend from the freeze, so the freeze is not a "
        "precommitment with respect to it"
    )


def test_a_result_records_the_protocol_it_ran_under() -> None:
    """With four amendments in force, which protocol a verdict belongs to is the question."""

    result_path = PROTOCOL.parent / "RESULT.json"
    if not result_path.exists():
        pytest.skip("no run has been performed")

    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["protocol_raw_sha256"] == hashlib.sha256(
        PROTOCOL.read_bytes()
    ).hexdigest(), "the result was produced under a different protocol than the committed one"
    assert result["amendments_in_force"] == [
        item["id"] for item in json.loads(PROTOCOL.read_text(encoding="utf-8"))["amendments"]
    ]
    assert result["model_calls"] == 0 and result["network_calls"] == 0


def test_hypothesis_is_frozen_but_still_claims_nothing(
    protocol: dict[str, object],
) -> None:
    """A frozen protocol is a precommitment, not a result."""

    hypothesis = protocol["hypothesis"]
    assert hypothesis["id"] == "H39"
    assert "REGISTERED and FROZEN" in hypothesis["registered_status"]
    assert "Not supported" in hypothesis["registered_status"]

    register = (REPO_ROOT / "SCIENTIFIC_HYPOTHESES.md").read_text(encoding="utf-8")
    assert "## H39" in register

    section = register.split("## H39", 1)[1]
    assert "FROZEN AND OPEN" in section
    assert "No qualification run has been performed" in section
    # The register must not read as support anywhere before the boundary section.
    before = section.split("**What it would not establish", 1)[0]
    assert "**SUPPORTED" not in before


def test_every_claim_boundary_flag_is_false(protocol: dict[str, object]) -> None:
    boundary = protocol["claim_boundary"]
    assert set(boundary.values()) == {False}, "a draft may not pre-claim anything"


def test_conditions_and_falsifiers_are_unique(protocol: dict[str, object]) -> None:
    conditions = protocol["conditions"]
    falsifiers = protocol["falsifiers"]
    assert len(conditions) == len(set(conditions)) == 12
    assert len(falsifiers) == len(set(falsifiers))


def test_the_four_audited_defects_are_falsifiers_not_details(
    protocol: dict[str, object],
) -> None:
    """Each audited defect must be able to fail the milestone."""

    falsifiers = " | ".join(protocol["falsifiers"])
    conditions = " | ".join(protocol["conditions"])

    # Defect 1 — an indicator that names one component.
    assert "matches exactly one eligible component" in falsifiers
    assert "P2_the_insufficiency_is_a_measured_property" in conditions

    # Defect 2 — a detector blind to the capability it claims is missing.
    assert "reports a capability missing from a component that defines it" in falsifiers
    assert "P3_the_diagnostic_verdict_inverts" in conditions

    # Defect 3 — an unreachable eligible component.
    assert "cannot be selected under any admissible observation" in falsifiers
    assert "P4_every_eligible_component_is_reachable" in conditions

    # Defect 4 — the repair shipped inside the transformation set.
    assert "contains the adopted repair as a finished body" in falsifiers
    assert "holds one element, so no search occurs" in falsifiers
    assert "P6_the_repair_is_assembled_from_composable_operations" in conditions


def test_ceiling_arm_is_excluded_from_the_verdict(protocol: dict[str, object]) -> None:
    assert protocol["ceiling_arm_is_excluded_from_the_verdict"] is True
    assert set(protocol["ceiling_arms"]) <= set(protocol["arms"])
    assert "authored_target_component" in protocol["ceiling_arms"]


def test_m092_is_not_touched(protocol: dict[str, object]) -> None:
    assert protocol["reattempts_m092"] is False
    assert "H38 and D062 remain unresolved" in protocol["not_a_reattempt_of_m092"]


# ── The audit instrument must actually measure ───────────────────────


def test_audit_report_matches_the_committed_document() -> None:
    report = json.loads(AUDIT.read_text(encoding="utf-8"))
    assert report["status"] == "audit_only_nothing_is_frozen"
    assert report["schema"] == "m094-design-audit-v1"


def test_discrimination_flags_an_indicator_that_names_one_component() -> None:
    rows = indicator_discrimination()
    assert rows["missing_query_method"]["matches_exactly_one_component"] is True
    # A genuinely discriminating indicator must not be flagged.
    assert rows["missing_validation_method"]["matches_exactly_one_component"] is False


def test_the_detector_is_inverted_with_respect_to_the_capability() -> None:
    """The pattern claims `events_by_kind` is missing from a file that defines it."""

    blindness = capability_presence_blindness()
    assert blindness["query_method_is_defined"] is True
    assert blindness["diagnoses_absence_of_a_capability_that_is_present"] is True

    present = blindness["indicator_occurrences_with_method_present"]
    removed = blindness["indicator_occurrences_with_method_removed"]
    assert present > removed, "adding the capability must not raise the missing-capability score"
    assert removed > 0, "the indicator never reaches zero, so it always reports the insufficiency"


def test_an_eligible_component_is_unreachable() -> None:
    selection = selection_determinism()
    assert "mira_core/safety.py" in selection["components_that_can_never_be_selected"]
    assert selection["selected"] == "mira_core/memory.py"


def test_selection_does_not_depend_on_the_authored_weights() -> None:
    """Flattening every severity to 1 selects the same component."""

    selection = selection_determinism()
    assert selection["selection_is_unanimous_across_weightings"] is True


def test_no_authored_constant_can_decide_the_selection() -> None:
    """Defect 5, repaired: the replacement no longer has a knob to sweep.

    `RenderAsMapping.min_fields` was authored, and sweeping it over 2..6 moved
    the selection on three of five values — the constant was deciding, which is
    the defect it was meant to avoid, one level up. Attribution now asks how many
    reachable classes could explain a call site instead. Reintroducing any
    numeric knob into a capability shape turns this red.
    """

    sensitivity = corrected_measure_threshold_sensitivity()

    assert sensitivity["numeric_constants_in_capability_shapes"] == {}
    assert sensitivity["a_constant_can_still_decide_the_winner"] is False
    assert sensitivity["selected"] == "mira_core/contracts.py"


def test_the_superseded_sweep_is_preserved_with_its_outlier() -> None:
    """The earlier selection was an artifact, and the record has to say so.

    `min_fields = 3` chose `mira_core/safety.py`; 2, 4 and 5 all chose
    `mira_core/contracts.py`, which is what the threshold-free rule also
    chooses. The declared value was the outlier, so the earlier headline was a
    property of that constant rather than a finding about the repository.
    """

    superseded = corrected_measure_threshold_sensitivity()["superseded_sweep"]

    assert superseded["constant"] == "RenderAsMapping.min_fields"
    assert superseded["observed"]["3"] == "mira_core/safety.py"
    assert {superseded["observed"][k] for k in ("2", "4", "5")} == {"mira_core/contracts.py"}


def test_defect_five_is_disclosed_in_the_audit_document() -> None:
    document = (PROTOCOL.parent / "DESIGN_AUDIT.md").read_text(encoding="utf-8")
    assert "Defect 5" in document
    assert "the authored constant is what selects" in document
    # The repair, and the correction it forces to the earlier headline.
    assert "the outlier" in document


def test_the_transformation_set_has_no_search_space() -> None:
    authorship = template_authorship()
    assert authorship["template_count"] == 1
    assert authorship["a_single_template_means_no_search"] is True

    only = authorship["templates"][0]
    assert only["name"] == "suggest_query_method"
    assert only["contains_component_specific_branch"] is True
    assert only["emits_fixed_method_name_shape"] is True
