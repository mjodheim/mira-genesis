from __future__ import annotations

import hashlib

def derive_runtime_seeds(master_nonce_hex: str, count: int, namespace: str) -> list[int]:
    nonce = bytes.fromhex(master_nonce_hex)
    if len(nonce) < 16:
        raise ValueError("master nonce is too short")
    seeds: list[int] = []
    for index in range(count):
        digest = hashlib.sha256(
            nonce + b"|m012b|" + namespace.encode("utf-8") + b"|" + str(index).encode("ascii")
        ).digest()
        seeds.append(int.from_bytes(digest[:8], "big"))
    return seeds
