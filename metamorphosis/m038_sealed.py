"""M038 sealed specification, derived only from an immutable arming head.

Importing this module opens nothing. The canonical task seed is derivable only
after the exact 40-hex arming commit exists. Ordinary tests use synthetic SHAs
and never evaluate the repository's future canonical head.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re

_HEAD_SHA = re.compile(r"\A[0-9a-f]{40}\Z")
_PROTOCOL_SHA256 = re.compile(r"\A[0-9a-f]{64}\Z")
SPEC_VERSION = "m038-sealed-spec/1"


def _full_sha(value: str, *, name: str) -> str:
    candidate = value.strip().lower()
    if not _HEAD_SHA.match(candidate):
        raise ValueError(f"{name} must be a full 40-character lowercase commit SHA")
    return candidate


def _protocol_digest(value: str) -> str:
    candidate = value.strip().lower()
    if not _PROTOCOL_SHA256.match(candidate):
        raise ValueError("protocol SHA-256 must be 64 lowercase hexadecimal characters")
    return candidate


def head_nonce(head_sha: str, protocol_sha256: str) -> str:
    """Bind the unrevealed task nonce to both immutable head and frozen protocol."""

    head = _full_sha(head_sha, name="arming head")
    protocol = _protocol_digest(protocol_sha256)
    payload = f"m038:sealed-head:{head}:protocol:{protocol}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def derive_seed(master_nonce: str, label: str, index: int = 0) -> int:
    if not _PROTOCOL_SHA256.match(master_nonce):
        raise ValueError("master nonce must be a 64-character lowercase hexadecimal digest")
    if not label or ":" in label:
        raise ValueError("seed label must be non-empty and contain no colon")
    if index < 0:
        raise ValueError("seed index must be non-negative")
    raw = f"m038:{master_nonce}:{label}:{index}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")


@dataclass(frozen=True)
class M038SealedSpec:
    arming_head_sha: str
    frozen_parent_sha: str
    protocol_sha256: str
    master_nonce: str
    task_seed: int
    spec_version: str = SPEC_VERSION

    def to_mapping(self) -> dict[str, object]:
        return {
            "spec_version": self.spec_version,
            "arming_head_sha": self.arming_head_sha,
            "frozen_parent_sha": self.frozen_parent_sha,
            "protocol_sha256": self.protocol_sha256,
            "master_nonce": self.master_nonce,
            "task_seed": self.task_seed,
        }

    def digest(self) -> str:
        payload = ":".join(
            (
                self.spec_version,
                self.arming_head_sha,
                self.frozen_parent_sha,
                self.protocol_sha256,
                self.master_nonce,
                str(self.task_seed),
            )
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


def sealed_spec(
    arming_head_sha: str,
    *,
    frozen_parent_sha: str,
    protocol_sha256: str,
) -> M038SealedSpec:
    """Derive the one-task sealed specification from the immutable arming commit."""

    head = _full_sha(arming_head_sha, name="arming head")
    parent = _full_sha(frozen_parent_sha, name="frozen parent")
    protocol = _protocol_digest(protocol_sha256)
    if head == parent:
        raise ValueError("the arming head must be a child of, not equal to, the frozen parent")
    nonce = head_nonce(head, protocol)
    return M038SealedSpec(
        arming_head_sha=head,
        frozen_parent_sha=parent,
        protocol_sha256=protocol,
        master_nonce=nonce,
        task_seed=derive_seed(nonce, "task", 0),
    )
