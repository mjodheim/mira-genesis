"""Fail-closed loader for the immutable M092-A base bundle used by adoption."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

from metamorphosis.m092_runtime import RuntimeLanguage
from metamorphosis.m092_substrate_state import SubstrateState

CHECKPOINT_SCHEMA = "m092a-checkpoint-v1"
BASE_RELATIVE = "experiments/M092/SUBSTRATE_A.json"


class CheckpointError(ValueError):
    """CHECKPOINT_A does not bind the base runtime bytes being adopted from."""


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_frozen_base(
    *,
    root: Path = Path("."),
    checkpoint_relative: str = "experiments/M092/CHECKPOINT_A.json",
    base_relative: str = BASE_RELATIVE,
) -> tuple[RuntimeLanguage, SubstrateState, str, Mapping[str, object]]:
    checkpoint_path = root / checkpoint_relative
    base_path = root / base_relative
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    if not isinstance(checkpoint, dict) or checkpoint.get("schema") != CHECKPOINT_SCHEMA:
        raise CheckpointError("CHECKPOINT_A schema differs")
    if checkpoint.get("milestone") != "M092" or checkpoint.get("stage") != "A":
        raise CheckpointError("CHECKPOINT_A identity differs")
    if checkpoint.get("status") != "frozen_before_any_extension_search_or_qualification":
        raise CheckpointError("CHECKPOINT_A is not the frozen pre-extension state")

    artifacts = checkpoint.get("artifacts")
    if not isinstance(artifacts, dict):
        raise CheckpointError("CHECKPOINT_A artifact manifest is malformed")
    record = artifacts.get(base_relative)
    if not isinstance(record, dict):
        raise CheckpointError("CHECKPOINT_A does not bind SUBSTRATE_A")
    if record.get("immutable") is not True or record.get("role") != "serialized language and substrate bundle":
        raise CheckpointError("SUBSTRATE_A is not the immutable runtime bundle in CHECKPOINT_A")

    raw = base_path.read_bytes()
    exact_sha = _sha256(raw)
    if record.get("sha256") != exact_sha:
        raise CheckpointError("SUBSTRATE_A bytes differ from CHECKPOINT_A SHA-256")
    if record.get("bytes") != len(raw):
        raise CheckpointError("SUBSTRATE_A byte count differs from CHECKPOINT_A")

    bundle = json.loads(raw)
    if not isinstance(bundle, dict) or "language" not in bundle or "substrate" not in bundle:
        raise CheckpointError("SUBSTRATE_A bundle is malformed")
    language = RuntimeLanguage.from_dict(bundle["language"])
    substrate = SubstrateState.from_dict(bundle["substrate"])
    if bundle.get("expected_substrate_digest") != substrate.digest():
        raise CheckpointError("SUBSTRATE_A internal substrate digest differs")

    commitments = checkpoint.get("semantic_commitments")
    if not isinstance(commitments, dict):
        raise CheckpointError("CHECKPOINT_A semantic commitments are malformed")
    if commitments.get("substrate_digest") != substrate.digest():
        raise CheckpointError("CHECKPOINT_A substrate digest differs from loaded S0")
    if commitments.get("language_digest") != language.digest():
        raise CheckpointError("CHECKPOINT_A language digest differs from loaded L0")
    if commitments.get("acquired_operations") != 0:
        raise CheckpointError("CHECKPOINT_A is not pre-acquisition")

    return language, substrate, exact_sha, checkpoint


__all__ = ["BASE_RELATIVE", "CHECKPOINT_SCHEMA", "CheckpointError", "load_frozen_base"]
