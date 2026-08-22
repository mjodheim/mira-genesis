from __future__ import annotations

import hashlib
import json
from copy import deepcopy

from scripts import check_m098_result as checker
from scripts.author_m098_qualification_pool import digest, load_pool
from scripts.run_m095_qualification import file_set_digest
from scripts.run_m098_qualification import stable_projection


def _runtime(
    *, confirmed: bool, returncode: int, pid: int, extensions: int = 1,
    raw: str = "canonical-raw", failed_closed: bool = False,
) -> dict[str, object]:
    m097 = json.loads(checker.M097_RESULT_PATH.read_text(encoding="utf-8"))
    state_digest = m097["scientific_evidence"]["extended_language_state"]["state_digest"]
    runtime = {
        "pid": pid,
        "isolated_mode": True,
        "confirmed": confirmed,
        "extensions_loaded": extensions,
        "extensions_tested": extensions,
        "cases": 4,
        "state_digest": state_digest,
        "state_raw_sha256": raw,
        "imported_project_modules": [],
        "search_path": ["C:/isolated-python", "C:/temporary-capsule"],
    }
    if failed_closed:
        runtime["failed_closed"] = True
    return {"returncode": returncode, "runtime": runtime, "stderr": ""}


def _evidence():
    protocol = json.loads(checker.PROTOCOL_PATH.read_text(encoding="utf-8"))
    pool = load_pool()
    m097 = json.loads(checker.M097_RESULT_PATH.read_text(encoding="utf-8"))
    m097_state = m097["scientific_evidence"]["extended_language_state"]
    capsule_digests = {
        "m098_runtime.py": hashlib.sha256(
            (checker.ROOT / "metamorphosis" / "m098_runtime.py").read_bytes()
        ).hexdigest(),
        "run.py": hashlib.sha256(
            (checker.ROOT / "scripts" / "run_m098_fresh_process.py").read_bytes()
        ).hexdigest(),
    }
    worlds = [
        {
            "entry": entry["id"],
            "entry_digest": entry["entry_digest"],
            "fresh": _runtime(confirmed=True, returncode=0, pid=101 + index),
        }
        for index, entry in enumerate(pool["entries"])
    ]
    inherited = _runtime(confirmed=False, returncode=1, pid=104, extensions=0)
    inherited["runtime"]["extensions_tested"] = 0
    mutation = _runtime(
        confirmed=False, returncode=1, pid=105, raw="mutated-raw"
    )
    corrupt = _runtime(confirmed=False, returncode=3, pid=106, failed_closed=True)
    during = _runtime(
        confirmed=False, returncode=1, pid=107, raw="mutated-raw"
    )
    after = _runtime(confirmed=True, returncode=0, pid=108)
    replay = {
        "producer": {
            "producer_pid": 1,
            "producer_returncode": 0,
            "producer_process_is_terminated": True,
            "producer_stdout_matches_manifest": True,
            "m097_result_digest": m097["result_digest"],
            "state_digest": m097_state["state_digest"],
            "state_raw_sha256": "canonical-raw",
            "bytes_written": 123,
        },
        "capsule": {
            "members": ["m098_runtime.py", "run.py"],
            "member_digests": capsule_digests,
            "contains_only_runtime_and_entrypoint": True,
        },
        "state": {
            "raw_sha256": "canonical-raw",
            "bytes": 123,
            "state_digest": m097_state["state_digest"],
            "extensions": 1,
        },
        "post_restart_worlds": worlds,
        "controls": {
            "inherited_without_extension": inherited,
            "semantic_mutation": mutation,
            "corrupt_digest": corrupt,
        },
        "rollback": {
            "before_fault_sha256": "canonical-raw",
            "during_fault": during,
            "restored_bytes_equal": True,
            "after_restore_sha256": "canonical-raw",
            "after_restore": after,
        },
        "process_boundary": {
            "producer_terminated_before_consumers": True,
            "producer_pid": 1,
            "consumer_pids": list(range(101, 109)),
            "fresh_process_invocations": 8,
            "consumer_pid_records_present": True,
            "all_consumers_are_distinct_from_producer": True,
        },
    }
    mechanism, mechanism_members = checker.mechanism_digest(protocol)
    apparatus, apparatus_members = file_set_digest(protocol, "qualification_apparatus")
    result = {
        "schema": "m098-result-v1",
        "milestone": "M098",
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
        "m097_state_digest": m097_state["state_digest"],
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


def _failed_after(mutator) -> set[str]:
    protocol, pool, replay, result = _evidence()
    mutator(result, replay)
    return {
        item.id
        for item in checker.run_conditions(protocol, pool, result, replay)
        if item.passed is False
    }


def test_synthetic_baseline_passes_all_run_conditions() -> None:
    protocol, pool, replay, result = _evidence()
    assert all(
        item.passed for item in checker.run_conditions(protocol, pool, result, replay)
    )


def test_every_run_condition_can_fail() -> None:
    mutations = {
        "P3": lambda _result, replay: replay["producer"].update(
            producer_process_is_terminated=False
        ),
        "P4": lambda _result, replay: replay["capsule"].update(
            members=["m098_runtime.py", "run.py", "acquisition.py"]
        ),
        "P5": lambda _result, replay: replay["post_restart_worlds"][0]["fresh"]["runtime"].update(
            confirmed=False
        ),
        "P6": lambda _result, replay: replay["post_restart_worlds"][0]["fresh"]["runtime"].update(
            imported_project_modules=["metamorphosis.m097_acquisition"]
        ),
        "P7": lambda _result, replay: replay["controls"]["inherited_without_extension"]["runtime"].update(
            extensions_loaded=1
        ),
        "P8": lambda _result, replay: replay["controls"]["corrupt_digest"].update(
            returncode=0
        ),
        "P9": lambda _result, replay: replay["process_boundary"].update(
            fresh_process_invocations=7
        ),
        "P10": lambda _result, replay: replay["rollback"]["during_fault"]["runtime"].update(
            confirmed=True
        ),
        "P11": lambda _result, replay: replay["rollback"].update(
            restored_bytes_equal=False
        ),
        "P12": lambda result, _replay: result.update(track="B"),
    }
    for expected, mutate in mutations.items():
        assert expected in _failed_after(mutate), expected
