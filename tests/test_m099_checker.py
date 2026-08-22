from __future__ import annotations

import hashlib
import json
from copy import deepcopy

from scripts import check_m099_result as checker
from scripts.author_m099_qualification_pool import digest, load_pool
from scripts.run_m095_qualification import file_set_digest
from scripts.run_m099_qualification import stable_projection


def _fixture():
    protocol = json.loads(checker.PROTOCOL_PATH.read_text(encoding="utf-8"))
    pool = load_pool()
    m097 = json.loads(checker.M097_RESULT_PATH.read_text(encoding="utf-8"))
    m098 = json.loads(checker.M098_RESULT_PATH.read_text(encoding="utf-8"))
    m098_check = json.loads(checker.M098_CHECK_PATH.read_text(encoding="utf-8"))
    replay = deepcopy(m098["scientific_evidence"])
    mechanism, mechanism_members = checker.mechanism_digest(protocol)
    apparatus, apparatus_members = file_set_digest(protocol, "qualification_apparatus")
    result = {
        "schema": "m099-result-v1",
        "milestone": "M099",
        "track": "A",
        "attempt": 1,
        "prior_attempts": [],
        "source_commit": "synthetic",
        "working_tree_was_dirty_at_recording": False,
        "model_calls": 0,
        "network_calls": 0,
        "remote_execution": False,
        "protocol_raw_sha256": hashlib.sha256(checker.PROTOCOL_PATH.read_bytes()).hexdigest(),
        "pool_digest": pool["pool_digest"],
        "m097_result_digest": m097["result_digest"],
        "m097_state_digest": m097["scientific_evidence"]["extended_language_state"]["state_digest"],
        "m098_result_digest": m098["result_digest"],
        "m098_checker_digest": m098_check["report_digest"],
        "mechanism_digest": mechanism,
        "mechanism_members": mechanism_members,
        "qualification_apparatus_digest": apparatus,
        "qualification_apparatus_members": apparatus_members,
        "scientific_evidence": deepcopy(replay),
        "stable_evidence_digest": digest(stable_projection(replay)),
        "elapsed_seconds": 0.1,
    }
    result["result_digest"] = digest(result)
    return protocol, pool, replay, result


def test_stable_p12_accepts_ephemeral_pid_changes() -> None:
    protocol, pool, replay, result = _fixture()
    replay["producer"]["producer_pid"] = 999001
    replay["process_boundary"]["producer_pid"] = 999001
    replay["process_boundary"]["consumer_pids"] = list(range(999010, 999018))
    for index, row in enumerate(replay["post_restart_worlds"]):
        row["fresh"]["runtime"]["pid"] = 999100 + index
    assert checker.check_p12(protocol, pool, result, replay).passed is True


def test_stable_p12_rejects_a_scientific_outcome_change() -> None:
    protocol, pool, replay, result = _fixture()
    replay["rollback"]["restored_bytes_equal"] = False
    condition = checker.check_p12(protocol, pool, result, replay)
    assert condition.passed is False
    assert "stable evidence differs" in condition.evidence
