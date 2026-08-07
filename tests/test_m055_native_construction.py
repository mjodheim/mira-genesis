"""M055 falsifications.

The central claim of this experiment is refuted by its own ablation, and these tests pin the
refutation as firmly as they pin the parts that hold. A negative result that is not pinned can
be quietly reinterpreted later.
"""
from __future__ import annotations

import json
import subprocess
import sys

import pytest

from metamorphosis.m055_native_construction import (
    ADMISSIBLE_SPACE, ATOMS, M055_PROTOCOL, M055Error, OPERATORS,
)


@pytest.fixture(scope="module")
def manifest():
    from metamorphosis.m055_native_construction import run_m055_native_construction

    return run_m055_native_construction()


@pytest.fixture(scope="module")
def lineage():
    from metamorphosis.m055_native_construction import reconstruct_m048_version_eight

    return reconstruct_m048_version_eight()


def test_the_declared_parameters_are_pinned():
    from metamorphosis.m055_native_construction import expression_space_size

    assert ATOMS == ("previous", "current")
    assert OPERATORS == ("add", "subtract", "minimum", "maximum", "multiply")
    assert M055_PROTOCOL.max_expression_depth == 3
    assert M055_PROTOCOL.construction_budget == 1024
    assert M055_PROTOCOL.beam_width == 12
    assert ADMISSIBLE_SPACE == expression_space_size(3) == 29330422
    # The budget cannot enumerate even the depth-two space.
    assert M055_PROTOCOL.construction_budget < expression_space_size(2) == 2422


def test_the_inherited_lineage_is_the_accepted_m048_state(lineage):
    """Requirement 1 of #72: continue the qualified lineage rather than start fresh."""
    assert lineage.version() == 8
    assert lineage.source_retained_count == 28
    assert len(lineage.retained) == 32
    names = [module["name"] for module in lineage.body()["modules"]]
    assert "tool_max" in names, "the capability learned after the first migration must be present"
    assert "tool_mean" in names, "the capability learned before the first migration must be present"


def test_the_inherited_state_identity_is_reproducible_across_processes():
    """Publishable since D018. It was not when this experiment was first written."""
    from metamorphosis.m055_native_construction import _state_digest, reconstruct_m048_version_eight

    script = (
        "from metamorphosis.m055_native_construction import "
        "reconstruct_m048_version_eight as r, _state_digest; print(_state_digest(r().state))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
    )
    other = completed.stdout.decode("utf-8").strip().splitlines()[-1]

    assert _state_digest(reconstruct_m048_version_eight().state) == other


def test_construction_happens_inside_the_migrated_body_without_enumerating(manifest):
    value = manifest.to_dict()

    assert value["creation_expression"] == "maximum(subtract(current,previous),subtract(previous,current))"
    assert value["creation_formation_depth"] == 2
    assert 0 < value["creation_candidates_constructed"] < 2422
    assert value["creation_candidates_constructed"] <= value["construction_budget"]
    assert value["admissible_space"] == ADMISSIBLE_SPACE
    assert "tool_variation" in value["creation_changed_modules"]


def test_every_inherited_capability_is_executed_not_assumed(manifest):
    """Requirement 7 of #77: the inherited-regression check is measured."""
    value = manifest.to_dict()

    assert value["creation_retained_total"] == 32
    assert value["creation_retained_passed"] == 32
    assert value["creation_inherited_regression_passed"] is True
    assert value["reuse_retained_total"] == 37
    assert value["reuse_inherited_regression_passed"] is True


def test_the_second_task_uses_the_acquired_expression_as_material(manifest):
    value = manifest.to_dict()

    assert value["reuse_uses_acquired_expression"] is True
    assert "ACQUIRED" in value["reuse_expression"]
    assert value["reuse_hidden_passed"] is True


def test_the_ablation_refutes_the_capability_claim(manifest):
    """The negative result, pinned.

    The from-scratch arm is given the same composition power as the continued lineage and the
    same budget. It solves the reuse task anyway. The acquisition therefore made the search
    cheaper and made nothing newly reachable.
    """
    value = manifest.to_dict()

    assert value["ablation_status"] == "constructed"
    assert value["capability_gain_claim_supported"] is False
    assert value["status"] == "negative_on_capability_gain"


def test_the_acquisition_buys_search_cost_and_that_is_all(manifest):
    value = manifest.to_dict()

    with_acquisition = value["reuse_candidates_constructed_with_acquisition"]
    without = value["ablation_candidates_constructed"]

    assert with_acquisition < without
    assert value["search_cost_gain_observed"] is True
    # Cheaper by an order of magnitude, and still not a capability gain.
    assert with_acquisition * 10 < without


def test_ambiguous_evidence_is_refused(manifest):
    assert manifest.to_dict()["refusal_status"] != "constructed"


def test_an_unvalidated_candidate_cannot_be_adopted(lineage):
    from metamorphosis.m055_native_construction import adopt

    with pytest.raises(M055Error, match="unvalidated"):
        adopt(lineage.state, lineage.body(), {"accepted": False, "inherited_regression_passed": True})
    with pytest.raises(M055Error, match="inherited regression"):
        adopt(lineage.state, lineage.body(), {"accepted": True, "inherited_regression_passed": False})


def test_an_intact_state_reports_no_fault(lineage):
    """The detector must be able to answer no, or detecting a fault proves nothing."""
    from metamorphosis.m055_native_construction import _state_digest, detect_fault

    assert detect_fault(lineage.state, _state_digest(lineage.state)) is False


def test_a_tampered_state_is_detected_and_restored_byte_for_byte(lineage):
    from metamorphosis.m055_native_construction import (
        _state_digest, corrupt_state, detect_fault, restore, snapshot_state,
    )

    digest = _state_digest(lineage.state)
    snapshot = snapshot_state(lineage.state)

    faulted = corrupt_state(lineage.state)

    assert detect_fault(faulted, digest) is True

    restored = restore(snapshot, digest)

    assert _state_digest(restored) == digest
    assert snapshot_state(restored) == snapshot
    assert detect_fault(restored, digest) is False


def test_restore_refuses_a_snapshot_that_does_not_match_its_digest(lineage):
    from metamorphosis.m055_native_construction import (
        _state_digest, corrupt_state, restore, snapshot_state,
    )

    with pytest.raises(M055Error, match="does not match its digest"):
        restore(snapshot_state(corrupt_state(lineage.state)), _state_digest(lineage.state))


def test_the_manifest_records_the_fault_rollback_and_boundaries(manifest):
    value = manifest.to_dict()

    assert value["accepted_version"] == 9
    assert value["forced_fault"] == "accepted_native_body_tampering"
    assert value["fault_detected"] is True
    assert value["rollback_exact"] is True
    assert value["replay_identical"] is True
    assert value["semantic_delegation_to_python"] is False
    assert value["arbitrary_code_generation"] is False
    assert value["network_authority"] is False
    assert value["repository_authority"] is False
    assert value["credential_authority"] is False
    assert value["deployment_authority"] is False
    assert value["canonical"] is False


def test_the_manifest_is_reproducible_across_processes(manifest):
    script = (
        "from metamorphosis.m055_native_construction import "
        "run_m055_native_construction as r; print(r().digest())"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
    )
    other = completed.stdout.decode("utf-8").strip().splitlines()[-1]

    assert manifest.digest() == other
