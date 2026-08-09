from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

import check_m069_frozen_protocol as freeze


def _runtime(mode: str, handle: str | None = None, *, cwd: Path | None = None):
    command = [sys.executable, str(freeze.RUNTIME_PATH), mode]
    if handle is not None:
        command.append(handle)
    completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=30)
    return completed, json.loads(completed.stdout)


def test_frozen_protocol_matches_runtime_and_live_bank() -> None:
    frozen = freeze.validate_frozen_protocol()
    assert frozen["protocol_sha256"] == "2da6abe85d0830f32a67415f1e4faef3316bd1ab1cf3cb461799e3c9a85fb499"
    assert frozen["target_runtime_lf_sha256"] == "6e2d1e0c510a72b4634c7bdfffcab164f82d7349531177adaa23b572d0618639"
    assert frozen["task_bank_attestation"]["task_bank_commitment"] == "66b7c7ffe87ecbf5c9cc42d14850b122dd933aa6235647d8dcdf6887464061ed"


def test_evaluator_has_no_network_or_process_authority() -> None:
    source = freeze.RUNTIME_PATH.read_text(encoding="utf-8")
    for forbidden in (
        "import socket", "import requests", "import urllib", "import subprocess",
        "from socket", "from requests", "from urllib", "fetch(",
    ):
        assert forbidden not in source
    assert "external_task_authorship_claimed" in source
    assert "hidden_cases_disclosed" in source


def test_runtime_drift_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    changed = tmp_path / "changed.py"
    changed.write_bytes(freeze.RUNTIME_PATH.read_bytes() + b"\n# drift\n")
    monkeypatch.setattr(freeze, "RUNTIME_PATH", changed)
    with pytest.raises(freeze.M069FreezeError, match="drifted"):
        freeze.validate_frozen_protocol()


def test_protocol_digest_covers_repair_language(tmp_path: Path) -> None:
    value = json.loads(freeze.FROZEN_PATH.read_text(encoding="utf-8"))
    value["protocol"]["candidate_replacements"][0] = "return 42"
    changed = tmp_path / "changed.json"
    changed.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(freeze.M069FreezeError, match="digest mismatch"):
        freeze.validate_frozen_protocol(changed)


def test_materialization_discloses_no_cases_or_solution(tmp_path: Path) -> None:
    frozen = freeze.validate_frozen_protocol()
    for handle in frozen["protocol"]["task_handles"]:
        completed, response = _runtime("materialize", handle)
        assert completed.returncode == 0
        result = response["result"]
        assert set(result) == {"task_handle", "goal_id", "instruction", "files"}
        assert set(result["files"]) == {"solution.py"}
        assert "public" not in json.dumps(result).lower()
        assert "hidden" not in json.dumps(result).lower()


def test_unmodified_compatible_sources_fail_public_evaluation(tmp_path: Path) -> None:
    frozen = freeze.validate_frozen_protocol()
    handles = frozen["protocol"]["task_handles"][:4]
    for index, handle in enumerate(handles):
        workspace = tmp_path / str(index)
        workspace.mkdir()
        _completed, materialized = _runtime("materialize", handle)
        (workspace / "solution.py").write_text(
            materialized["result"]["files"]["solution.py"], encoding="utf-8",
        )
        completed, response = _runtime("public", handle, cwd=workspace)
        assert completed.returncode == 1
        assert response["result"]["status"] == "failed"
        assert response["result"]["passed"] == 0
        assert response["result"]["total"] == 3


def test_incompatible_task_has_no_repair_marker(tmp_path: Path) -> None:
    handle = freeze.validate_frozen_protocol()["protocol"]["task_handles"][-1]
    completed, response = _runtime("materialize", handle)
    assert completed.returncode == 0
    source = response["result"]["files"]["solution.py"]
    assert "MIRA_REPAIR_SLOT" not in source


def test_lf_hash_is_checkout_portable() -> None:
    data = freeze.RUNTIME_PATH.read_bytes()
    assert freeze._lf_sha256(freeze.RUNTIME_PATH) == freeze._lf_sha256(freeze.RUNTIME_PATH)
    assert b"\r\n" not in data or freeze._lf_sha256(freeze.RUNTIME_PATH) == freeze.validate_frozen_protocol()["target_runtime_lf_sha256"]
