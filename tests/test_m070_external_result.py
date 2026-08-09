from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_m070_preserves_negative_external_result_without_agi_claim() -> None:
    result = json.loads(
        (ROOT / "experiments" / "M070" / "EXTERNAL_RESULT.json").read_text(
            encoding="utf-8"
        )
    )
    assert result["status"] == "failed_falsifiable_threshold"
    assert result["claim_passed"] is False
    assert [trial["reward"] for trial in result["trials"]] == [0.0, 0.0]
    assert [trial["scientific_retries"] for trial in result["trials"]] == [0, 0]
    assert all(trial["harbor_exception"] is False for trial in result["trials"])
    assert result["diagnosis"]["transport_fix_applied_to_m070"] is False
