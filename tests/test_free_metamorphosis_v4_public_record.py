from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOT = ROOT / "docs" / "free-metamorphosis-v4"
SUMMARY = PUBLIC_ROOT / "campaign-summary.json"


def test_v4_public_summary_is_sanitized_and_private_host_stays_private() -> None:
    payload = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert payload["schema"] == "genesis-free-metamorphosis-v4-public-summary-v1"
    assert payload["host_visibility"] == "private"
    assert payload["public_record_only"] is True
    assert payload["policy_id"] == "GENESIS_FREE_METAMORPHOSIS_OPEN_EMPIRICAL_V4_2026-09-12"
    assert payload["campaign_status"] == "paused_after_attempt_004"
    assert payload["attempt_budget"] == {"used": 4, "maximum": 24, "remaining_unspent": 20}

    serialized = json.dumps(payload, sort_keys=True)
    forbidden_private_evaluator_fields = (
        "required_all",
        "required_any",
        "forbidden_tools",
        "api_log_tail",
        "stdout_tail",
        "stderr_tail",
        "evaluator_image_id",
        "evaluation_commands",
        "evaluator_case",
        "case_message",
        "expected_label",
        "observed_label",
    )
    for field in forbidden_private_evaluator_fields:
        assert field not in serialized

    assert payload["redaction"] == {
        "private_source_published": False,
        "raw_patches_published": False,
        "private_paths_published": False,
        "evaluator_cases_published": False,
        "raw_logs_published": False,
        "credentials_or_environment_values_published": False,
        "campaign_state_archives_published": False,
        "proposer_bundles_published": False,
    }


def test_v4_attempt_records_do_not_publish_private_host_paths_or_live_urls() -> None:
    attempts = sorted((PUBLIC_ROOT / "attempts").glob("*.md"))
    assert [path.name for path in attempts] == ["001.md", "002.md", "003.md", "004.md"]

    forbidden_fragments = (
        "backend/",
        "Mira.Agents",
        "Mira.Tests",
        "runner.temp",
        "actions/artifacts",
        "githubusercontent.com",
        "http://",
        "https://",
    )
    for path in attempts:
        text = path.read_text(encoding="utf-8")
        for fragment in forbidden_fragments:
            assert fragment not in text, (path, fragment)


def test_v4_public_lineage_records_retained_and_neutral_distinction() -> None:
    payload = json.loads(SUMMARY.read_text(encoding="utf-8"))
    attempts = {item["attempt"]: item for item in payload["attempts"]}

    assert attempts[1]["status"] == "retained"
    assert attempts[1]["parent_generation"] == 0
    assert attempts[1]["resulting_retained_generation"] == 1
    assert attempts[1]["improvements"] == {"personal_write": 1}

    for number in (2, 3, 4):
        assert attempts[number]["status"] == "neutral_archived"
        assert attempts[number]["parent_generation"] == 1
        assert attempts[number]["resulting_retained_generation"] == 1
        assert attempts[number]["improvements"] == {}
        assert attempts[number]["regressions"] == {}

    assert payload["final_retained_state"]["generation"] == 1
    assert payload["final_retained_state"]["tree_digest"] == "b720efef4e9550b7156d05a10a828d8196fb3333a040a0e55a19b43998f918a2"
    assert payload["closure"]["v4_results_will_not_be_rescored"] is True
