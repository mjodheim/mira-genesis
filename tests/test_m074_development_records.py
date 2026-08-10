from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_m074_development as check  # noqa: E402


def _payload(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_preserved_m074_development_records_recompute_without_docker() -> None:
    result = check.verify()
    assert result["verified"] is True
    assert result["scientific_result"] is False
    assert result["task_count"] == 6
    assert result["episode_count"] == 12


def test_verifier_rejects_a_changed_environment_binding() -> None:
    probe = _payload(check.PROBE_RECORD)
    dryrun = _payload(check.DRYRUN_RECORD)
    changed = deepcopy(probe)
    changed["labels"][0]["environment_sha256"] = "0" * 64  # type: ignore[index]
    with pytest.raises(check.DevelopmentVerificationError, match="environment digest drifted"):
        check.verify(changed, dryrun)


def test_verifier_rejects_selective_episode_removal() -> None:
    probe = _payload(check.PROBE_RECORD)
    dryrun = _payload(check.DRYRUN_RECORD)
    changed = deepcopy(dryrun)
    changed["episodes"] = changed["episodes"][:-1]  # type: ignore[index]
    with pytest.raises(check.DevelopmentVerificationError, match="exact 12 episodes"):
        check.verify(probe, changed)
