"""Regressions for the independent-maintainer intake kit.

The kit exists to lower the cost of the pre-private boundary, never to lower the boundary. These
tests pin the second half: it cannot sign, cannot accept a project author and cannot touch payload.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from metamorphosis.m075_private_readiness import (
    ENVELOPE_SCHEMA,
    MINIMUM_DOMAINS,
    MINIMUM_MATCHED_CAPABILITY_PAIRS,
    SIGNATURE_NAMESPACE,
    M075PrivateReadinessError,
    validate_private_envelope,
)
from metamorphosis.m075_intake_kit import (
    instructions,
    project_identities,
    template,
    validate,
)


def filled(**overrides: object) -> dict:
    envelope = template()
    envelope.update({
        "bank_id": "bank-2026-08",
        "created_at": "2026-08-10",
        "maintainer_identity": "Dana Okonkwo",
        "conflicts_disclosed": "none",
        "payload_sha256": "a" * 64,
        "payload_bytes": 4096,
        "maintainer_public_key_sha256": "b" * 64,
    })
    envelope.update(overrides)
    return envelope


def test_template_is_structurally_valid_once_filled() -> None:
    validate_private_envelope(filled(), signature_verified=True)


def test_template_meets_the_declared_minimums() -> None:
    envelope = filled()
    assert len(envelope["domains"]) >= MINIMUM_DOMAINS
    assert envelope["matched_capability_pairs"] >= MINIMUM_MATCHED_CAPABILITY_PAIRS
    assert envelope["task_count"] == envelope["matched_capability_pairs"] * 2
    assert envelope["schema"] == ENVELOPE_SCHEMA
    assert envelope["signature_namespace"] == SIGNATURE_NAMESPACE


def test_template_domain_ids_have_the_required_opaque_shape() -> None:
    for domain in template()["domains"]:
        identifier = domain["opaque_domain_id"]
        assert len(identifier) == 23
        assert identifier.startswith("opaque-")
        assert all(character in "0123456789abcdef" for character in identifier[7:])


@pytest.mark.parametrize("identity", sorted(project_identities()))
def test_a_project_author_cannot_attest_independence(identity: str) -> None:
    """The load-bearing guard: the kit must not become a self-attestation path."""

    with pytest.raises(M075PrivateReadinessError):
        validate_private_envelope(filled(maintainer_identity=identity), signature_verified=True)


@pytest.mark.parametrize("identity", ["Anthony Mets", "ANTHONY METS", "  mjodheim  "])
def test_project_identity_rejection_ignores_case_and_padding(identity: str) -> None:
    with pytest.raises(M075PrivateReadinessError):
        validate_private_envelope(filled(maintainer_identity=identity), signature_verified=True)


def test_an_unverified_signature_is_never_accepted() -> None:
    with pytest.raises(M075PrivateReadinessError):
        validate_private_envelope(filled(), signature_verified=False)


def test_payload_must_stay_in_external_custody() -> None:
    with pytest.raises(M075PrivateReadinessError):
        validate_private_envelope(
            filled(payload_custody="handed-to-project"), signature_verified=True,
        )
    with pytest.raises(M075PrivateReadinessError):
        validate_private_envelope(
            filled(payload_revealed_to_policy_authors=True), signature_verified=True,
        )


def test_thin_coverage_is_rejected() -> None:
    with pytest.raises(M075PrivateReadinessError):
        validate_private_envelope(
            filled(domains=template()["domains"][:2], matched_capability_pairs=4, task_count=8),
            signature_verified=True,
        )


def test_domain_pair_counts_must_reconcile() -> None:
    domains = [dict(domain) for domain in template()["domains"]]
    domains[0]["matched_capability_pairs"] = 3
    with pytest.raises(M075PrivateReadinessError):
        validate_private_envelope(filled(domains=domains), signature_verified=True)


def test_validate_rejects_a_template_still_holding_placeholders(tmp_path: Path) -> None:
    candidate = tmp_path / "envelope.json"
    candidate.write_text(json.dumps(template()), encoding="utf-8")
    assert validate(candidate, signature_verified=True) == 2


def test_validate_accepts_a_filled_envelope(tmp_path: Path) -> None:
    candidate = tmp_path / "envelope.json"
    candidate.write_text(json.dumps(filled()), encoding="utf-8")
    assert validate(candidate, signature_verified=True) == 0


def test_validate_reports_a_missing_file(tmp_path: Path) -> None:
    assert validate(tmp_path / "absent.json", signature_verified=True) == 2


def test_instructions_never_offer_to_sign_on_the_projects_behalf() -> None:
    text = instructions()
    assert "ssh-keygen -Y sign" in text
    assert SIGNATURE_NAMESPACE in text
    # The maintainer signs on their own machine with their own key; the project only verifies.
    assert "Never the archive" in text
    assert "refuse" in text


def test_the_kit_cannot_execute_a_signing_command() -> None:
    """It prints ssh-keygen instructions; it must have no way to run them.

    Without a process or network module in its import graph the kit cannot produce a signature,
    so the project cannot use it to attest its own independence even by accident.
    """

    import ast

    source = Path(__file__).resolve().parents[1] / "metamorphosis/m075_intake_kit.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported.isdisjoint({"subprocess", "os", "shutil", "socket", "urllib", "requests"})


def test_the_kit_never_opens_payload() -> None:
    """It reads only the envelope the maintainer hands over, never task content.

    Checked structurally rather than by searching the text, so that prose describing the boundary
    does not trip the assertion that enforces it.
    """

    import ast

    source = Path(__file__).resolve().parents[1] / "metamorphosis/m075_intake_kit.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    imported: set[str] = set()
    attributes: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
        elif isinstance(node, ast.Attribute):
            attributes.add(node.attr)
    assert imported.isdisjoint({"tarfile", "zipfile", "gzip", "shutil"})
    assert attributes.isdisjoint({"extract", "extractall", "getmembers", "namelist"})
