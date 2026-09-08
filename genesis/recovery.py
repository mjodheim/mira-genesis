"""Restore a Genesis lineage without asking the caller to recreate its executable body.

``Genesis.restore`` historically accepted a ``body_factory`` and then verified that its artifact
identity matched the checkpoint. That is fail-closed, but a generated descendant still depends on an
outside caller remembering how to reconstruct the exact factory after process death.

For reconstructible artifact kinds the checkpoint already contains enough canonical data. This
module verifies the checkpoint manifest *before resolving anything*, reconstructs the committed body
from that authenticated artifact record, and then delegates all state/journal/budget/isolation and
evaluation-contract checks to ``Genesis.restore``.

The current generated-program body is a configured artifact, so its interpreter target and complete
program configuration survive process death without a host-supplied body factory. Artifact kinds that
cannot be reconstructed exactly remain refused rather than guessed.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping

from genesis.artifacts import ArtifactError, reconstruct
from genesis.loop import CHECKPOINT_NAME, PREVIOUS_CHECKPOINT_NAME, Genesis
from genesis.trust_root import Budget, Isolation, TrustRootError, digest_of


def _manifest(directory: Path, *, superseded: bool) -> dict[str, Any]:
    path = Path(directory) / (PREVIOUS_CHECKPOINT_NAME if superseded else CHECKPOINT_NAME)
    if not path.exists():
        raise TrustRootError("no committed checkpoint at %s" % path)
    value = json.loads(path.read_bytes().decode("utf-8"))
    if not isinstance(value, dict):
        raise TrustRootError("checkpoint manifest is not a record")
    expected = digest_of({key: item for key, item in value.items() if key != "checkpoint_digest"})
    if value.get("checkpoint_digest") != expected:
        raise TrustRootError("the checkpoint manifest does not reproduce its own digest")
    return value


def restore_lineage(
    directory: Path,
    *,
    grade: Callable[[Mapping[str, Any], Any], str] | None = None,
    budget: Budget | None = None,
    isolation: Isolation | None = None,
    allow_self_reported_outcomes: bool = False,
    superseded: bool = False,
) -> Genesis:
    """Restore the executable body named by one authenticated checkpoint.

    No body factory is accepted here by design. If the committed artifact kind is not reconstructible
    by Genesis itself, this surface refuses and the lower-level ``Genesis.restore`` remains available
    for DEVELOPMENT callers that explicitly supply an external resolver.
    """
    manifest = _manifest(Path(directory), superseded=superseded)
    artifact = manifest.get("body_artifact")
    if not isinstance(artifact, Mapping):
        raise TrustRootError("checkpoint carries no executable body artifact")
    try:
        body_factory = reconstruct(artifact)
    except ArtifactError as problem:
        raise TrustRootError("checkpoint body cannot be reconstructed: %s" % problem) from problem
    return Genesis.restore(
        directory,
        body_factory=body_factory,
        grade=grade,
        budget=budget,
        isolation=isolation,
        allow_self_reported_outcomes=allow_self_reported_outcomes,
        superseded=superseded,
    )
