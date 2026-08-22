from __future__ import annotations

import hashlib
import json
from copy import deepcopy

from metamorphosis import m100_runtime as runtime
from scripts import check_m100_result as checker
from scripts.author_m100_qualification_pool import digest, load_pool
from scripts.run_m095_qualification import file_set_digest
from scripts.run_m100_qualification import stable_projection


def _states_evidence() -> dict[str, object]:
    m097 = json.loads(checker.M097_RESULT_PATH.read_text(encoding="utf-8"))
    s1 = runtime.migrate_m097_state(
        runtime.canonical_json(m097["scientific_evidence"]["extended_language_state"]).encode(
            "ascii"
        )
    )
    s2 = runtime.acquire(s1, (1, 1), 4, register=True)["next_state"]
    s3 = runtime.acquire(s2, (1, 2), 5, register=True)["next_state"]
    s0 = runtime.migrate_m097_state(
        runtime.canonical_json(m097["scientific_evidence"]["inherited_language_state"]).encode(
            "ascii"
        )
    )
    return {
        "states": {
            name: {
                "state": state,
                "raw_sha256": hashlib.sha256(runtime.canonical_json(state).encode("ascii")).hexdigest(),
            }
            for name, state in (("S0", s0), ("S1", s1), ("S2", s2), ("S3", s3))
        } | {
            "s1_prefix_conserved_in_s2": s2["operations"][:1] == s1["operations"],
            "s2_prefix_conserved_in_s3": s3["operations"][:2] == s2["operations"],
        }
    }


def test_independent_checker_accepts_the_exact_conserved_chain() -> None:
    evidence = _states_evidence()
    assert checker.check_p4(evidence).passed is True
    assert checker.check_p7(evidence).passed is True
    tampered = deepcopy(evidence)
    tampered["states"]["s2_prefix_conserved_in_s3"] = False
    assert checker.check_p4(tampered).passed is False


def _p12_fixture():
    protocol = json.loads(checker.PROTOCOL_PATH.read_text(encoding="utf-8"))
    pool = load_pool()
    m097 = json.loads(checker.M097_RESULT_PATH.read_text(encoding="utf-8"))
    m099 = json.loads(checker.M099_RESULT_PATH.read_text(encoding="utf-8"))
    m099_check = json.loads(checker.M099_CHECK_PATH.read_text(encoding="utf-8"))
    evidence = {
        "process_boundary": {
            "process_pids": [101, 102],
            "fresh_process_invocations": 2,
            "all_invocations_isolated": True,
        },
        "outcome": {"confirmed": True},
    }
    mechanism, mechanism_members = checker.mechanism_digest(protocol)
    apparatus, apparatus_members = file_set_digest(protocol, "qualification_apparatus")
    result = {
        "schema": "m100-result-v1",
        "milestone": "M100",
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
        "m097_extended_state_digest": m097["scientific_evidence"]["extended_language_state"][
            "state_digest"
        ],
        "m097_inherited_state_digest": m097["scientific_evidence"]["inherited_language_state"][
            "state_digest"
        ],
        "m099_result_digest": m099["result_digest"],
        "m099_checker_digest": m099_check["report_digest"],
        "mechanism_digest": mechanism,
        "mechanism_members": mechanism_members,
        "qualification_apparatus_digest": apparatus,
        "qualification_apparatus_members": apparatus_members,
        "scientific_evidence": deepcopy(evidence),
        "stable_evidence_digest": digest(stable_projection(evidence)),
        "elapsed_seconds": 0.1,
    }
    result["result_digest"] = digest(result)
    return protocol, pool, evidence, result


def test_stable_replay_accepts_pid_changes_but_rejects_scientific_changes() -> None:
    protocol, pool, replay, result = _p12_fixture()
    replay["process_boundary"]["process_pids"] = [901, 902]
    assert checker.check_p12(protocol, pool, result, replay).passed is True
    replay["outcome"]["confirmed"] = False
    condition = checker.check_p12(protocol, pool, result, replay)
    assert condition.passed is False
    assert "stable evidence differs" in condition.evidence
