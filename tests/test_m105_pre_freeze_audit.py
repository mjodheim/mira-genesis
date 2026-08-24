from scripts import audit_m105_boundaries


def test_m105_adversarial_pre_freeze_audit_is_clean() -> None:
    report = audit_m105_boundaries.audit()
    assert report["confirmed"] is True
    assert all(report["checks"].values())
    assert report["fresh_semantic_classes"] == {
        "json_document": 4,
        "sqlite": 4,
    }
