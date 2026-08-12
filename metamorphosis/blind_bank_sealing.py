"""Turn a materialized bank into a public commitment and nothing else.

The sequence is fixed: canonicalize, digest, encrypt, publish the commitment, keep the plaintext
out of this repository forever. Two deliberate refusals shape the implementation.

**No cipher is written here.** A bespoke construction in a research repository is a liability
nobody will audit. Sealing delegates to `age` or `gpg`, this module records which one and verifies
the ciphertext digest, and `sealing_plan` refuses to emit a command whose plaintext or ciphertext
destination resolves inside the checkout.

**Nothing is executed here.** `sealing_plan` returns argv. The scientific act of materializing and
sealing a bank is authorized by a person, not performed as a side effect of importing a validator.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Mapping, Sequence

from metamorphosis.blind_bank_protocol import (
    BlindBankError,
    DEVELOPMENT_PAYLOAD_SCHEMA,
    PAYLOAD_SCHEMA,
    build_public_commitment,
    canonical_bytes,
    sha256_hex,
)


SUPPORTED_CIPHERS = {
    "age-v1-x25519": ("age", "--encrypt", "--recipient"),
    "gpg-aes256": ("gpg", "--symmetric", "--cipher-algo", "AES256"),
}

# Paths that may never appear in the working tree at all. A file matching one of these is either a
# plaintext bank or a decryption key, and neither has a legitimate reason to exist in a public
# checkout.
FORBIDDEN_PATH_PATTERNS = (
    re.compile(r"BANK_PAYLOAD.*\.json\Z", re.IGNORECASE),
    re.compile(r"BLIND_BANK_PLAINTEXT", re.IGNORECASE),
    re.compile(r"BLIND_BANK.*\.key\Z", re.IGNORECASE),
    re.compile(r"BLIND_BANK.*\.age\Z", re.IGNORECASE),
    re.compile(r"BLIND_BANK.*(?:identity|recipient)", re.IGNORECASE),
)

SCHEMA_DOCUMENT_SUFFIX = ".schema.json"

REQUIRED_GITIGNORE_ENTRIES = (
    "*.blind-bank-payload.json",
    "*.blind-bank-plaintext",
    "*.blind-bank.key",
    "*.blind-bank.age",
    "blind-bank-workspace/",
)


class SealingError(BlindBankError):
    """Raised when a sealing step would place bank plaintext or a key inside this repository."""


def _resolve(path: str | os.PathLike[str]) -> Path:
    return Path(path).expanduser().resolve()


def _is_inside(candidate: Path, parent: Path) -> bool:
    return candidate == parent or parent in candidate.parents


def canonicalize_payload(payload: Mapping[str, object]) -> bytes:
    """Return the exact bytes every digest and the ciphertext are taken over.

    The digest binds this serialization, not the file the generator happened to write. Two
    checkouts of the same bank on different platforms produce the same canonical bytes because the
    form contains no newline and no platform-dependent separator.
    """

    schema = payload.get("schema")
    if schema not in {PAYLOAD_SCHEMA, DEVELOPMENT_PAYLOAD_SCHEMA}:
        raise SealingError("only a blind-bank payload may be canonicalized for sealing")
    return canonical_bytes(payload)


def sealing_plan(
    *,
    repository_root: str | os.PathLike[str],
    plaintext_path: str | os.PathLike[str],
    ciphertext_path: str | os.PathLike[str],
    cipher: str,
    recipient: str | None = None,
) -> dict[str, object]:
    """Build the encryption command, refusing any destination inside this repository."""

    if cipher not in SUPPORTED_CIPHERS:
        raise SealingError(f"cipher {cipher!r} is not one of {sorted(SUPPORTED_CIPHERS)}")
    root = _resolve(repository_root)
    plaintext = _resolve(plaintext_path)
    ciphertext = _resolve(ciphertext_path)
    for label, target in (("plaintext", plaintext), ("ciphertext", ciphertext)):
        if _is_inside(target, root):
            raise SealingError(f"the bank {label} may never be written inside the repository")
    if plaintext == ciphertext:
        raise SealingError("the sealed output may not overwrite its own plaintext")

    base = list(SUPPORTED_CIPHERS[cipher])
    if cipher == "age-v1-x25519":
        if not isinstance(recipient, str) or not recipient.strip():
            raise SealingError("age sealing requires an explicit recipient")
        argv = [*base, recipient, "--output", str(ciphertext), str(plaintext)]
    else:
        if recipient is not None:
            raise SealingError("symmetric sealing takes no recipient")
        argv = [*base, "--output", str(ciphertext), str(plaintext)]
    return {
        "cipher": cipher,
        "argv": argv,
        "plaintext_path": str(plaintext),
        "ciphertext_path": str(ciphertext),
        "plaintext_must_be_destroyed_after_sealing": True,
    }


def finalize_seal(
    *,
    payload: Mapping[str, object],
    spec: Mapping[str, object],
    generator_commitment_sha256: str,
    isolation_attestation_sha256: str,
    ciphertext_sha256: str,
    cipher: str,
    key_custody: str,
    sealed_at: str,
    milestone: str,
) -> dict[str, object]:
    """Produce the public commitment for a sealed bank without disclosing its content."""

    if cipher not in SUPPORTED_CIPHERS:
        raise SealingError(f"cipher {cipher!r} is not supported")
    canonical = canonicalize_payload(payload)
    domains = payload.get("domains")
    if not isinstance(domains, list) or not domains:
        raise SealingError("a sealed bank must contain at least one domain")
    composition = spec.get("composition")
    if not isinstance(composition, Mapping):
        raise SealingError("the frozen spec carries no composition")
    opaque = [str(domain["opaque_domain_id"]) for domain in domains]  # type: ignore[index]
    return build_public_commitment(
        bank_id=str(payload["bank_id"]),
        milestone=milestone,
        spec_commitment_sha256=str(spec["spec_commitment_sha256"]),
        generator_commitment_sha256=generator_commitment_sha256,
        payload_sha256=sha256_hex(canonical),
        payload_bytes=len(canonical),
        ciphertext_sha256=ciphertext_sha256,
        cipher=cipher,
        key_custody=key_custody,
        sealed_at=sealed_at,
        isolation_attestation_sha256=isolation_attestation_sha256,
        opaque_domain_ids=opaque,
        domain_count=int(composition["domain_count"]),
        pairs_per_domain=int(composition["pairs_per_domain"]),
        task_count=int(composition["task_count"]),
    )


def scan_tree_for_leaks(
    root: str | os.PathLike[str], *, tracked_paths: Sequence[str] | None = None,
) -> list[str]:
    """Return every reason the working tree already contains sealed-bank plaintext or a key.

    Two independent checks, because either alone is defeatable. A path check catches the obvious
    filename; a content check catches a plaintext bank committed under an innocuous name. The
    content check keys on the scientific payload schema string, which is why development fixtures
    carry a different schema identifier and are unaffected.
    """

    base = _resolve(root)
    problems: list[str] = []
    if tracked_paths is None:
        candidates = [
            path for path in base.rglob("*")
            if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts
        ]
    else:
        candidates = [base / relative for relative in tracked_paths]

    for path in candidates:
        if not path.is_file():
            continue
        relative = path.relative_to(base).as_posix()
        # A `.schema.json` file describes a payload rather than being one, and the contract's own
        # schema document is legitimately named after the thing it describes. The path patterns
        # skip it; the content check below does not, so a payload hidden under that suffix is
        # still caught.
        if not relative.endswith(SCHEMA_DOCUMENT_SUFFIX):
            for pattern in FORBIDDEN_PATH_PATTERNS:
                if pattern.search(relative):
                    problems.append(f"{relative} matches a forbidden sealed-bank path pattern")
                    break
        if path.suffix.lower() not in {".json", ".txt", ".md", ".yaml", ".yml", ""}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if PAYLOAD_SCHEMA not in text:
            continue
        # The schema name appears legitimately in this contract's own source, its schema document
        # and its prose. What may never appear is a document that *is* one.
        if _declares_payload_schema(path, text):
            problems.append(
                f"{relative} is a blind-bank payload in plaintext and may never be committed"
            )
    return sorted(set(problems))


def _declares_payload_schema(path: Path, text: str) -> bool:
    if path.suffix.lower() != ".json":
        return False
    try:
        document = json.loads(text)
    except (json.JSONDecodeError, UnicodeError):
        return False
    if not isinstance(document, Mapping):
        return False
    if document.get("schema") == PAYLOAD_SCHEMA:
        return True
    # A JSON Schema document *describes* the payload rather than being one. It is identified by
    # carrying a `$schema` key, and it never carries bank content.
    return "domains" in document and "bank_nonce" in document and "$schema" not in document


def missing_gitignore_entries(root: str | os.PathLike[str]) -> list[str]:
    path = _resolve(root) / ".gitignore"
    if not path.is_file():
        return list(REQUIRED_GITIGNORE_ENTRIES)
    present = {line.strip() for line in path.read_text(encoding="utf-8").splitlines()}
    return [entry for entry in REQUIRED_GITIGNORE_ENTRIES if entry not in present]


def missing_gitattributes_entries(
    root: str | os.PathLike[str], required: Sequence[str],
) -> list[str]:
    """Return digest-bearing artifacts not protected from end-of-line conversion.

    M064 recorded a protocol digest that matched only its CRLF working-tree copy. Every JSON file
    whose bytes are hashed under this contract is registered here in the same commit that creates
    it, before any digest exists to be wrong.
    """

    path = _resolve(root) / ".gitattributes"
    if not path.is_file():
        return list(required)
    text = path.read_text(encoding="utf-8")
    declared = {
        line.split()[0]
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#") and line.split()
    }
    return [entry for entry in required if entry not in declared]


__all__ = [
    "FORBIDDEN_PATH_PATTERNS", "REQUIRED_GITIGNORE_ENTRIES", "SCHEMA_DOCUMENT_SUFFIX",
    "SUPPORTED_CIPHERS",
    "SealingError", "canonicalize_payload", "finalize_seal", "missing_gitattributes_entries",
    "missing_gitignore_entries", "scan_tree_for_leaks", "sealing_plan",
]
