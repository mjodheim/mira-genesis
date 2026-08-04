"""M040 sealed specification derived only from an immutable marker-only arming head.

Importing this module derives nothing and opens no block. Permanent tests use synthetic
canonical SHAs. The real canonical task seed exists only after the arming commit is immutable.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re

_HEAD_SHA = re.compile(r"\A[0-9a-f]{40}\Z")
_PROTOCOL_SHA256 = re.compile(r"\A[0-9a-f]{64}\Z")
SPEC_VERSION = "m040-sealed-spec/1"


def _full_sha(value: str, *, name: str) -> str:
    if not _HEAD_SHA.match(value):
        raise ValueError(f"{name} must be a full 40-character lowercase commit SHA")
    return value


def _protocol_digest(value: str) -> str:
    if not _PROTOCOL_SHA256.match(value):
        raise ValueError("protocol SHA-256 must be 64 lowercase hexadecimal characters")
    return value


def head_nonce(head_sha: str, protocol_sha256: str) -> str:
    head = _full_sha(head_sha, name="arming head")
    protocol = _protocol_digest(protocol_sha256)
    return hashlib.sha256(
        f"m040:sealed-head:{head}:protocol:{protocol}".encode("utf-8")
    ).hexdigest()


def derive_seed(master_nonce: str, label: str, index: int = 0) -> int:
    if not _PROTOCOL_SHA256.match(master_nonce):
        raise ValueError("master nonce must be canonical lowercase SHA-256 hexadecimal")
    if not label or ":" in label:
        raise ValueError("seed label must be non-empty and contain no colon")
    if index < 0:
        raise ValueError("seed index must be non-negative")
    digest = hashlib.sha256(
        f"m040:{master_nonce}:{label}:{index}".encode("utf-8")
    ).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


@dataclass(frozen=True)
class M040SealedSpec:
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
) -> M040SealedSpec:
    head = _full_sha(arming_head_sha, name="arming head")
    parent = _full_sha(frozen_parent_sha, name="frozen parent")
    protocol = _protocol_digest(protocol_sha256)
    if head == parent:
        raise ValueError("the arming head must be a child of the frozen parent")
    nonce = head_nonce(head, protocol)
    return M040SealedSpec(
        arming_head_sha=head,
        frozen_parent_sha=parent,
        protocol_sha256=protocol,
        master_nonce=nonce,
        task_seed=derive_seed(nonce, "task", 0),
    )
