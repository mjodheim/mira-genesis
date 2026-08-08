from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from metamorphosis.m064_real_substrate_completion import M064_PROTOCOL
from check_m064_frozen_protocol import FrozenProtocolError, validate_frozen_protocol


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "generator.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    frozen = tmp_path / "FROZEN_PROTOCOL.json"
    frozen.write_text(
        json.dumps(
            {
                "schema": "m064-frozen-protocol/1",
                "protocol": M064_PROTOCOL.to_dict(),
                "protocol_sha256": M064_PROTOCOL.digest(),
                "task_bank_commitment": M064_PROTOCOL.task_bank_commitment,
                "task_bank_entry_count": 4,
                "file_sha256": {
                    str(source): hashlib.sha256(source.read_bytes()).hexdigest()
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return frozen, source


def test_repository_frozen_protocol_matches_all_committed_bytes() -> None:
    value = validate_frozen_protocol()
    assert value["protocol_sha256"] == M064_PROTOCOL.digest()
    assert len(value["file_sha256"]) == 21


def test_executable_protocol_drift_is_rejected(tmp_path: Path) -> None:
    frozen, _source = _fixture(tmp_path)
    value = json.loads(frozen.read_text(encoding="utf-8"))
    value["protocol"]["expression_node_limit"] = 8
    frozen.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(FrozenProtocolError, match="mapping differs"):
        validate_frozen_protocol(frozen)


def test_committed_generator_byte_drift_is_rejected(tmp_path: Path) -> None:
    frozen, source = _fixture(tmp_path)
    source.write_text("VALUE = 2\n", encoding="utf-8")
    with pytest.raises(FrozenProtocolError, match="committed source drifted"):
        validate_frozen_protocol(frozen)


def test_task_bank_commitment_drift_is_rejected(tmp_path: Path) -> None:
    frozen, _source = _fixture(tmp_path)
    value = json.loads(frozen.read_text(encoding="utf-8"))
    value["task_bank_commitment"] = "0" * 64
    frozen.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(FrozenProtocolError, match="task-bank commitment"):
        validate_frozen_protocol(frozen)
