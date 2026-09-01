"""M118 stages must prove their predecessors were committed, not merely present.

M117 could not claim its route selection was prospectively clean. M118's answer is a proof
obligation rather than a promise: each stage names artifacts that must already exist as commits at
HEAD, byte-identical to the working tree. A file written moments before a request is not a freeze.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from metamorphosis import m118_chronology as chronology
from metamorphosis.m116_chronology import ChronologyError

ROOT = Path(__file__).resolve().parents[1]


def _repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@example.com"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    return tmp_path


def _write(base: Path, relative: Path, text: str) -> None:
    path = base / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _commit(base: Path, message: str = "c") -> None:
    subprocess.run(["git", "-C", str(base), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(base), "commit", "-q", "-m", message], check=True)


# -------------------------------------------------------------------------------------------
# The committed-at-HEAD requirement
# -------------------------------------------------------------------------------------------

def test_an_uncommitted_predecessor_is_refused(tmp_path):
    base = _repo(tmp_path)
    _write(base, chronology.M117_CALIBRATION, "{}")
    _commit(base)
    _write(base, chronology.M117_OUTCOME, "closed")  # present but not committed
    with pytest.raises(ChronologyError, match="not committed at HEAD"):
        chronology.assert_stage_permitted("preregistration", base)


def test_a_predecessor_edited_after_commit_is_refused(tmp_path):
    base = _repo(tmp_path)
    _write(base, chronology.M117_CALIBRATION, "{}")
    _write(base, chronology.M117_OUTCOME, "closed")
    _commit(base)
    _write(base, chronology.M117_OUTCOME, "closed, but edited afterwards")
    with pytest.raises(ChronologyError, match="differs from its committed bytes"):
        chronology.assert_stage_permitted("preregistration", base)


def test_an_absent_predecessor_is_refused(tmp_path):
    base = _repo(tmp_path)
    _write(base, chronology.M117_CALIBRATION, "{}")
    _commit(base)
    with pytest.raises(ChronologyError, match="absent"):
        chronology.assert_stage_permitted("preregistration", base)


def test_a_fully_committed_stage_is_permitted(tmp_path):
    base = _repo(tmp_path)
    _write(base, chronology.M117_CALIBRATION, "{}")
    _write(base, chronology.M117_OUTCOME, "closed")
    _commit(base)
    permission = chronology.assert_stage_permitted("preregistration", base)
    assert permission["permitted"] is True
    assert permission["in_memory_freeze_accepted"] is False
    assert set(permission["committed_predecessors"]) == {
        chronology.M117_CALIBRATION.as_posix(), chronology.M117_OUTCOME.as_posix()}


def test_there_is_no_parameter_for_supplying_a_record():
    """The hole M116 closed must not reopen: no caller may hand in a freeze it just built."""
    import inspect
    for name in ("assert_stage_permitted", "assert_qualifying_generation_permitted",
                 "assert_readiness_passed"):
        params = set(inspect.signature(getattr(chronology, name)).parameters)
        assert params <= {"stage", "root"}, name


# -------------------------------------------------------------------------------------------
# Ordering
# -------------------------------------------------------------------------------------------

def test_every_stage_after_the_first_requires_the_preregistration():
    for stage, predecessors in chronology.STAGES.items():
        if stage in ("preregistration", "admission", "sealing", "reveal", "scoring", "replay"):
            continue
        assert chronology.PREREGISTRATION in predecessors, stage


def test_the_qualifying_generation_requires_the_whole_chain():
    required = set(chronology.STAGES["qualifying_generation"])
    for artifact in (chronology.M117_CALIBRATION, chronology.PREREGISTRATION,
                     chronology.FIXED_ROUTE_MODULE, chronology.READINESS_APPARATUS,
                     chronology.READINESS_RESULT, chronology.ANALYSIS_PLAN,
                     chronology.GENERATOR_SPEC, chronology.TESTED_SYSTEM_FREEZE):
        assert artifact in required, artifact


def test_the_live_repository_permits_only_what_it_has_committed():
    stages = chronology.chronology(ROOT)["stages"]
    assert stages["preregistration"] == "permitted"
    for later in ("qualifying_generation", "admission", "sealing", "reveal", "scoring", "replay"):
        assert stages[later].startswith("blocked"), later


# -------------------------------------------------------------------------------------------
# No scientific observation may pre-exist the generation
# -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("artifact", list(chronology.NO_SCIENTIFIC_ARTIFACT_BEFORE))
def test_a_pre_existing_scientific_artifact_blocks_the_generation(tmp_path, artifact):
    base = _repo(tmp_path)
    _write(base, artifact, "{}")
    with pytest.raises(ChronologyError, match="would not be the first"):
        chronology.assert_no_scientific_observation_yet(base)


def test_a_clean_tree_permits_the_first_generation(tmp_path):
    chronology.assert_no_scientific_observation_yet(_repo(tmp_path))


def test_the_live_repository_has_no_h63_scientific_observation():
    chronology.assert_no_scientific_observation_yet(ROOT)


# -------------------------------------------------------------------------------------------
# The readiness gate cannot be stepped over
# -------------------------------------------------------------------------------------------

def _readiness(base: Path, verdict: str, ready: bool) -> None:
    _write(base, chronology.READINESS_RESULT, json.dumps(
        {"verdict": verdict, "ready": ready, "result_sha256": "d" * 64,
         "plan_sha256": "p" * 64}))
    _commit(base)


def test_a_failed_readiness_stops_h63(tmp_path):
    base = _repo(tmp_path)
    _readiness(base, "not_ready_features", False)
    with pytest.raises(ChronologyError, match="stops before scientific generation"):
        chronology.assert_readiness_passed(base)


def test_a_readiness_result_claiming_ready_without_the_verdict_is_refused(tmp_path):
    base = _repo(tmp_path)
    _readiness(base, "not_ready_stress", True)
    with pytest.raises(ChronologyError, match="did not pass"):
        chronology.assert_readiness_passed(base)


def test_a_passing_readiness_is_accepted(tmp_path):
    base = _repo(tmp_path)
    _readiness(base, "ready", True)
    verdict = chronology.assert_readiness_passed(base)
    assert verdict["readiness_verdict"] == "ready"


def test_an_uncommitted_readiness_result_is_refused(tmp_path):
    base = _repo(tmp_path)
    _write(base, chronology.READINESS_RESULT, json.dumps(
        {"verdict": "ready", "ready": True, "result_sha256": "d" * 64, "plan_sha256": "p" * 64}))
    with pytest.raises(ChronologyError, match="not committed at HEAD"):
        chronology.assert_readiness_passed(base)
