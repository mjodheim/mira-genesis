from __future__ import annotations

from dataclasses import dataclass
import hashlib
import secrets


def runtime_nonce() -> str:
    return secrets.token_hex(32)


def derive_seed(master_nonce: str, label: str, index: int) -> int:
    raw = f"m014b:{master_nonce}:{label}:{index}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")


@dataclass(frozen=True)
class SealedSpec:
    base_passport_seeds: tuple[int, ...]
    machine_seeds: tuple[int, ...]
    machine_families: tuple[int, ...]
    update_seeds: tuple[int, ...]
    search_seeds: tuple[int, ...]
    hidden_old_seeds: tuple[int, ...]
    hidden_new_seeds: tuple[int, ...]
    negative_base_seeds: tuple[int, ...]
    negative_update_seeds: tuple[int, ...]
    negative_kinds: tuple[int, ...]


def sealed_spec(master_nonce: str) -> SealedSpec:
    return SealedSpec(
        base_passport_seeds=tuple(derive_seed(master_nonce, "base", index) for index in range(12)),
        machine_seeds=tuple(derive_seed(master_nonce, "machine", index) for index in range(3)),
        machine_families=(0, 1, 2),
        update_seeds=tuple(derive_seed(master_nonce, "update", index) for index in range(12)),
        search_seeds=tuple(derive_seed(master_nonce, "search", index) for index in range(12)),
        hidden_old_seeds=tuple(derive_seed(master_nonce, "hidden-old", index) for index in range(12)),
        hidden_new_seeds=tuple(derive_seed(master_nonce, "hidden-new", index) for index in range(12)),
        negative_base_seeds=tuple(derive_seed(master_nonce, "negative-base", index) for index in range(12)),
        negative_update_seeds=tuple(derive_seed(master_nonce, "negative-update", index) for index in range(12)),
        negative_kinds=tuple(index // 4 for index in range(12)),
    )
