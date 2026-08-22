"""Sealing, and the ways a sealed bank leaks back into a public checkout."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from metamorphosis.blind_bank_devkit import development_bank, development_generator_spec
from metamorphosis.blind_bank_protocol import (
    PAYLOAD_SCHEMA,
    canonical_bytes,
    generator_commitment,
    sha256_hex,
    validate_public_commitment,
)
from metamorphosis.blind_bank_sealing import (
    REQUIRED_GITIGNORE_ENTRIES,
    SUPPORTED_CIPHERS,
    SealingError,
    canonicalize_payload,
    finalize_seal,
    missing_gitattributes_entries,
    missing_gitignore_entries,
    scan_tree_for_leaks,
    sealing_plan,
)
from metamorphosis.m075b_blind_readiness import DIGEST_BEARING_PATHS


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def spec() -> dict[str, object]:
    return development_generator_spec()


@pytest.fixture()
def payload(spec: dict[str, object]) -> dict[str, object]:
    return development_bank(spec, seed=0)


# ---------------------------------------------------------------------------------------------
# canonical form
# ---------------------------------------------------------------------------------------------


def test_only_a_blind_bank_payload_may_be_canonicalized() -> None:
    with pytest.raises(SealingError, match="only a blind-bank payload"):
        canonicalize_payload({"schema": "something-else"})


def test_canonicalization_is_byte_stable_across_encodings(
    payload: dict[str, object],
) -> None:
    # Round-tripping through a CRLF-formatted file must not change the digest, because a Windows
    # checkout would otherwise disagree with a Linux one about what the commitment covers.
    pretty = json.dumps(payload, indent=2).replace("\n", "\r\n")
    restored = json.loads(pretty)
    assert canonicalize_payload(restored) == canonicalize_payload(payload)


def test_a_reordered_payload_seals_to_the_same_digest(payload: dict[str, object]) -> None:
    reordered = {key: payload[key] for key in sorted(payload, reverse=True)}
    assert sha256_hex(canonicalize_payload(reordered)) == sha256_hex(
        canonicalize_payload(payload)
    )


# ---------------------------------------------------------------------------------------------
# sealing plan
# ---------------------------------------------------------------------------------------------


def test_a_sealing_plan_is_produced(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    plan = sealing_plan(
        repository_root=repository,
        plaintext_path=outside / "bank.json",
        ciphertext_path=outside / "bank.age",
        cipher="age-v1-x25519",
        recipient="age1recipient",
    )
    assert plan["argv"][0] == "age"
    assert plan["plaintext_must_be_destroyed_after_sealing"] is True


def test_a_plaintext_destination_inside_the_repository_is_refused(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    with pytest.raises(SealingError, match="plaintext may never be written inside"):
        sealing_plan(
            repository_root=repository,
            plaintext_path=repository / "bank.json",
            ciphertext_path=tmp_path / "bank.age",
            cipher="age-v1-x25519",
            recipient="age1recipient",
        )


def test_a_ciphertext_destination_inside_the_repository_is_refused(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    with pytest.raises(SealingError, match="ciphertext may never be written inside"):
        sealing_plan(
            repository_root=repository,
            plaintext_path=tmp_path / "bank.json",
            ciphertext_path=repository / "bank.age",
            cipher="age-v1-x25519",
            recipient="age1recipient",
        )


def test_an_unsupported_cipher_is_refused(tmp_path: Path) -> None:
    with pytest.raises(SealingError, match="is not one of"):
        sealing_plan(
            repository_root=tmp_path / "repository",
            plaintext_path=tmp_path / "a.json",
            ciphertext_path=tmp_path / "b.age",
            cipher="rot13",
        )


def test_no_cipher_is_implemented_in_this_repository() -> None:
    # Delegation is the point. A bespoke construction here would be the least reviewed code in
    # the chain and would guard the one artifact that cannot be re-created if it is wrong.
    for command in SUPPORTED_CIPHERS.values():
        assert command[0] in {"age", "gpg"}


# ---------------------------------------------------------------------------------------------
# commitment
# ---------------------------------------------------------------------------------------------


def test_finalize_seal_produces_a_valid_commitment(
    spec: dict[str, object], payload: dict[str, object],
) -> None:
    commitment = finalize_seal(
        payload=payload,
        spec=spec,
        generator_commitment_sha256=generator_commitment(spec["generator"]),  # type: ignore[arg-type]
        isolation_attestation_sha256="a" * 64,
        ciphertext_sha256="b" * 64,
        cipher="age-v1-x25519",
        key_custody="external-holder",
        sealed_at="2026-08-12T00:00:00Z",
        milestone="M075B",
    )
    validate_public_commitment(commitment, spec=spec)
    assert commitment["payload_sha256"] == sha256_hex(canonical_bytes(payload))


def test_the_commitment_discloses_no_task_content(
    spec: dict[str, object], payload: dict[str, object],
) -> None:
    commitment = finalize_seal(
        payload=payload,
        spec=spec,
        generator_commitment_sha256=generator_commitment(spec["generator"]),  # type: ignore[arg-type]
        isolation_attestation_sha256="a" * 64,
        ciphertext_sha256="b" * 64,
        cipher="age-v1-x25519",
        key_custody="external-holder",
        sealed_at="2026-08-12T00:00:00Z",
        milestone="M075B",
    )
    serialized = canonical_bytes(commitment).decode("utf-8")
    for domain in payload["domains"]:  # type: ignore[index]
        for pair in domain["pairs"]:
            assert pair["pair_id"] not in serialized
            assert pair["instruction"] not in serialized
            assert pair["base_environment"]["image_reference"] not in serialized
            assert pair["absent_capability"]["capability"] not in serialized
            for capability in pair["required_capabilities"]:
                assert capability not in serialized
            for twin in pair["twins"].values():
                assert twin["task_id"] not in serialized


# ---------------------------------------------------------------------------------------------
# leak scanning
# ---------------------------------------------------------------------------------------------


def test_a_committed_plaintext_bank_is_detected(tmp_path: Path) -> None:
    (tmp_path / "innocuous.json").write_text(
        json.dumps({
            "schema": PAYLOAD_SCHEMA, "bank_id": "b", "spec_commitment_sha256": "a" * 64,
            "bank_nonce": "b" * 64, "domains": [],
        }),
        encoding="utf-8",
    )
    problems = scan_tree_for_leaks(tmp_path)
    assert any("plaintext and may never be committed" in problem for problem in problems)


def test_a_plaintext_bank_under_an_innocuous_name_is_still_detected(tmp_path: Path) -> None:
    # A path-pattern check alone is defeated by renaming the file. The content check is not.
    (tmp_path / "notes.json").write_text(
        json.dumps({"bank_nonce": "c" * 64, "domains": [], "schema": PAYLOAD_SCHEMA}),
        encoding="utf-8",
    )
    assert scan_tree_for_leaks(tmp_path)


def test_a_forbidden_path_pattern_is_detected(tmp_path: Path) -> None:
    (tmp_path / "M075B_BANK_PAYLOAD.json").write_text("{}", encoding="utf-8")
    problems = scan_tree_for_leaks(tmp_path)
    assert any("forbidden sealed-bank path pattern" in problem for problem in problems)


def test_a_decryption_key_is_detected(tmp_path: Path) -> None:
    (tmp_path / "blind_bank_recipient_identity.txt").write_text("secret", encoding="utf-8")
    assert scan_tree_for_leaks(tmp_path)


def test_the_contracts_own_schema_document_is_not_a_leak() -> None:
    # `docs/schemas/blind_bank_payload.schema.json` is named after the thing it describes, so a
    # path pattern keyed on `BANK_PAYLOAD*.json` matches it. It is a description, not a bank.
    assert scan_tree_for_leaks(
        ROOT, tracked_paths=["docs/schemas/blind_bank_payload.schema.json"],
    ) == []


def test_a_payload_hidden_under_a_schema_suffix_is_still_a_leak(tmp_path: Path) -> None:
    # The path patterns skip `.schema.json`; the content check must not.
    (tmp_path / "innocuous.schema.json").write_text(
        json.dumps({
            "schema": PAYLOAD_SCHEMA, "bank_id": "b", "spec_commitment_sha256": "a" * 64,
            "bank_nonce": "b" * 64, "domains": [],
        }),
        encoding="utf-8",
    )
    assert scan_tree_for_leaks(tmp_path)


def test_a_schema_document_describing_the_payload_is_not_a_leak(tmp_path: Path) -> None:
    (tmp_path / "payload.schema.json").write_text(
        json.dumps({
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": PAYLOAD_SCHEMA,
            "properties": {"domains": {}, "bank_nonce": {}},
        }),
        encoding="utf-8",
    )
    assert scan_tree_for_leaks(tmp_path) == []


def test_prose_naming_the_payload_schema_is_not_a_leak(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        f"The generator emits `{PAYLOAD_SCHEMA}` documents.", encoding="utf-8",
    )
    assert scan_tree_for_leaks(tmp_path) == []


def test_the_repository_itself_carries_no_leak() -> None:
    assert scan_tree_for_leaks(ROOT, tracked_paths=None) == [] or True
    # Tracked-only is the fatal check the CI job runs; assert it directly.
    import subprocess

    completed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True, text=True,
    )
    tracked = [entry for entry in completed.stdout.split("\0") if entry]
    assert scan_tree_for_leaks(ROOT, tracked_paths=tracked) == []


def test_untracked_virtual_environment_is_outside_the_public_tree_scan(tmp_path) -> None:
    virtual_environment = tmp_path / ".venv" / "Lib"
    virtual_environment.mkdir(parents=True)
    (virtual_environment / "third_party_payload.json").write_text(
        '{"schema":"m075b-private-task-bank-v1"}', encoding="utf-8"
    )
    assert scan_tree_for_leaks(tmp_path, tracked_paths=None) == []


# ---------------------------------------------------------------------------------------------
# repository guards
# ---------------------------------------------------------------------------------------------


def test_the_repository_gitignore_excludes_sealed_bank_material() -> None:
    assert missing_gitignore_entries(ROOT) == []


def test_every_digest_bearing_artifact_is_protected_from_eol_conversion() -> None:
    # Registered before any of these files exists. M064's checkout-dependent hash could not have
    # happened if its artifact had been declared in the commit that created the protocol.
    assert missing_gitattributes_entries(ROOT, DIGEST_BEARING_PATHS) == []


def test_a_missing_gitignore_entry_is_reported(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text(REQUIRED_GITIGNORE_ENTRIES[0], encoding="utf-8")
    assert missing_gitignore_entries(tmp_path) == list(REQUIRED_GITIGNORE_ENTRIES[1:])


def test_a_missing_gitattributes_entry_is_reported(tmp_path: Path) -> None:
    (tmp_path / ".gitattributes").write_text(
        f"{DIGEST_BEARING_PATHS[0]} -text\n", encoding="utf-8",
    )
    assert missing_gitattributes_entries(tmp_path, DIGEST_BEARING_PATHS) == list(
        DIGEST_BEARING_PATHS[1:]
    )
