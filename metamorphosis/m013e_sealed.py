from __future__ import annotations

from dataclasses import dataclass
import hashlib
import secrets


def runtime_nonce() -> str:
    return secrets.token_hex(32)


def derive_seed(master_nonce: str, label: str, index: int) -> int:
    raw = f"m013e:{master_nonce}:{label}:{index}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")


@dataclass(frozen=True)
class SealedSpec:
    passport_seeds: tuple[int, ...]
    machine_seeds: tuple[int, ...]
    machine_families: tuple[int, ...]
    search_seeds: tuple[int, ...]
    hidden_seeds: tuple[int, ...]
    negative_seeds: tuple[int, ...]
    negative_kinds: tuple[int, ...]


def sealed_spec(master_nonce: str) -> SealedSpec:
    return SealedSpec(
        passport_seeds=tuple(derive_seed(master_nonce, "passport", index) for index in range(12)),
        machine_seeds=tuple(derive_seed(master_nonce, "machine", index) for index in range(3)),
        machine_families=(0, 1, 2),
        search_seeds=tuple(derive_seed(master_nonce, "search", index) for index in range(3)),
        hidden_seeds=tuple(derive_seed(master_nonce, "hidden", index) for index in range(12)),
        negative_seeds=tuple(derive_seed(master_nonce, "negative", index) for index in range(12)),
        negative_kinds=tuple(index % 3 for index in range(12)),
    )
