from __future__ import annotations

import json
from pathlib import Path

from scripts import audit_m103_boundaries as boundary
from scripts import author_m103_predecessor_conservation as conservation_author
from scripts import build_m103_protocol as protocol_builder


ROOT = Path(__file__).resolve().parents[1]
CONSERVATION = ROOT / "experiments" / "M103" / "PREDECESSOR_CONSERVATION.json"


def test_boundary_audit_is_clean_and_winning_subset_is_not_in_producer_runtime() -> None:
    report = boundary.audit()
    assert report["confirmed"] is True
    assert report["exact_winning_literals_in_runtime"] == []
    assert report["checks"]["every_adopted_feature_is_operationally_necessary"] is True
    assert report["checks"]["canonical_result_absent"] is True


def test_predecessor_conservation_fixture_is_exact_and_complete() -> None:
    fixture = json.loads(CONSERVATION.read_text(encoding="ascii"))
    assert fixture == conservation_author.build_fixture()
    assert fixture["fixture_digest"] == (
        "7bfb93b917f78f5f1c2e2c16cee587f8eb50bdd7f9f98d7e922b6ae6506a51ea"
    )
    assert [entry["action"] for entry in fixture["entries"]].count("execute-m100") == 3


def test_protocol_candidate_builder_binds_clean_apparatus_without_arming_run() -> None:
    candidate = protocol_builder.build_candidate()
    assert candidate["schema"] == "m103-protocol-candidate-v1"
    assert candidate["canonical_run_allowed"] is False
    assert candidate["qualification_pool_digest"] == (
        "1f1b5d4289685f8401564d0f0e5d7c4f8ffda10561fbeba9ec8a36114e22b59e"
    )
    assert candidate["adversarial_review"]["unresolved_decisive_falsifiers"] == 0
    payload = {key: value for key, value in candidate.items() if key != "candidate_digest"}
    assert candidate["candidate_digest"] == protocol_builder.digest(payload)
