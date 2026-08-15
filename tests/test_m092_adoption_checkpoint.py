from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from metamorphosis.m092_adoption_checkpoint import (
    CheckpointError,
    load_frozen_base,
)


def test_frozen_base_loader_matches_checkpoint_a() -> None:
    language, substrate, bundle_sha, checkpoint = load_frozen_base()
    record = checkpoint["artifacts"]["experiments/M092/SUBSTRATE_A.json"]
    assert bundle_sha == record["sha256"]
    assert substrate.digest() == checkpoint["semantic_commitments"]["substrate_digest"]
    assert language.digest() == checkpoint["semantic_commitments"]["language_digest"]
    assert checkpoint["semantic_commitments"]["acquired_operations"] == 0


def test_rehashed_or_tampered_base_cannot_substitute_for_checkpoint_bytes(tmp_path: Path) -> None:
    checkpoint_source = Path("experiments/M092/CHECKPOINT_A.json")
    base_source = Path("experiments/M092/SUBSTRATE_A.json")
    target_dir = tmp_path / "experiments" / "M092"
    target_dir.mkdir(parents=True)
    shutil.copy2(checkpoint_source, target_dir / "CHECKPOINT_A.json")
    raw = bytearray(base_source.read_bytes())
    raw[-2] = raw[-2] ^ 1
    (target_dir / "SUBSTRATE_A.json").write_bytes(bytes(raw))

    with pytest.raises(CheckpointError):
        load_frozen_base(root=tmp_path)


def test_checkpoint_manifest_cannot_be_rewritten_to_bless_different_base(tmp_path: Path) -> None:
    checkpoint_source = Path("experiments/M092/CHECKPOINT_A.json")
    base_source = Path("experiments/M092/SUBSTRATE_A.json")
    target_dir = tmp_path / "experiments" / "M092"
    target_dir.mkdir(parents=True)
    shutil.copy2(base_source, target_dir / "SUBSTRATE_A.json")
    checkpoint = json.loads(checkpoint_source.read_text(encoding="utf-8"))
    checkpoint["semantic_commitments"]["acquired_operations"] = 1
    (target_dir / "CHECKPOINT_A.json").write_text(
        json.dumps(checkpoint, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    with pytest.raises(CheckpointError):
        load_frozen_base(root=tmp_path)
