from pathlib import Path

from scripts import audit_m105_boundaries

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "M105"

# The audit is a PRE-FREEZE instrument. One of its checks asserts that no canonical evidence exists
# yet. M105's unique attempt has since run, so that single check is now correctly false and stays
# false forever: it records a phase the milestone has left, not a defect. Every other check is a
# substantive boundary claim that must still hold, so the assertions below keep their full teeth
# rather than skipping the test once evidence appears.
_PHASE_CHECK = "canonical_evidence_absent_before_attempt"


def _canonical_evidence_exists() -> bool:
    return (EXPERIMENT / "RESULT.json").exists() or (EXPERIMENT / "CHECK_REPORT.json").exists()


def test_m105_adversarial_boundary_audit_still_holds() -> None:
    report = audit_m105_boundaries.audit()
    checks = report["checks"]

    substantive = {key: value for key, value in checks.items() if key != _PHASE_CHECK}
    assert all(substantive.values()), [key for key, value in substantive.items() if not value]
    assert report["fresh_semantic_classes"] == {
        "json_document": 4,
        "sqlite": 4,
    }

    if _canonical_evidence_exists():
        assert checks[_PHASE_CHECK] is False
        assert report["confirmed"] is False
    else:
        assert checks[_PHASE_CHECK] is True
        assert report["confirmed"] is True
