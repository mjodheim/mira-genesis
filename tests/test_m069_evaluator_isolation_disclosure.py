from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DISCLOSURE = ROOT / "experiments" / "M069" / "EVALUATOR_ISOLATION_DISCLOSURE.json"
STATUS = ROOT / "experiments" / "M069" / "STATUS.md"


def test_m069_interface_falsifier_is_recorded_without_accusing_the_learner() -> None:
    record = json.loads(DISCLOSURE.read_text(encoding="utf-8"))

    assert record["hidden_evidence_resident_in_evaluator_process"] is True
    assert record["public_evaluator_exposes_output"] is True
    assert record["recorded_learner_exploits_leak"] is False
    assert record["verdict_reclassified"] is True
    assert "post-hoc disqualified" in record["verdict_decision"]
    assert record["frozen_artifacts_rewritten"] is False


def test_m069_current_status_cannot_be_mistaken_for_the_historical_verdict() -> None:
    status = STATUS.read_text(encoding="utf-8")

    assert "POST-HOC DISQUALIFIED DEVELOPMENT RESULT" in status
    assert "Historical run record" in status
    assert "no evidence that the frozen learner exploited" in status
