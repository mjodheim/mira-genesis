"""Intake kit for the independent M075 task-bank maintainer.

`m075_private_readiness` states whether the project may reveal a private bank. It does not help the
one person who can unblock it. Reconstructing a 22-field closed envelope, opaque domain identifiers
and an SSH signature namespace from source is hours of work for an outside volunteer, and that
friction is the real cost of the pre-private boundary.

This module emits the template, prints the exact signing commands and validates a candidate envelope
before it is sent, reusing the very validator the gate enforces so the two can never diverge.

It deliberately cannot sign anything: producing a signature here would let the project attest its own
independence, which is exactly what the boundary exists to prevent. It never opens, lists, extracts
or transports private task content — the maintainer computes the payload digest on their own machine
and the payload stays with them until the scientific protocol is frozen.
"""
from __future__ import annotations

import json
from pathlib import Path

from metamorphosis.m075_private_readiness import (
    ENVELOPE_SCHEMA,
    MINIMUM_DOMAINS,
    MINIMUM_MATCHED_CAPABILITY_PAIRS,
    PROJECT_IDENTITIES,
    SIGNATURE_NAMESPACE,
    M075PrivateReadinessError,
    validate_private_envelope,
)

ENVELOPE_PATH = "experiments/M075/PRIVATE_BANK_ENVELOPE.json"
SIGNATURE_PATH = "experiments/M075/PRIVATE_BANK_ENVELOPE.sshsig"
ALLOWED_SIGNERS_PATH = "experiments/M075/PRIVATE_BANK_ALLOWED_SIGNERS"


def template() -> dict:
    """A structurally valid skeleton. Every value is a placeholder to be replaced."""

    return {
        "schema": ENVELOPE_SCHEMA,
        "status": "sealed_unrevealed",
        "bank_id": "REPLACE-with-your-own-bank-identifier",
        "created_at": "REPLACE-with-an-ISO-8601-date",
        "maintainer_identity": "REPLACE-with-your-name-or-handle",
        "maintainer_role": "independent-task-bank-maintainer",
        "maintainer_independence_attested": True,
        "conflicts_disclosed": "REPLACE with any relationship to the project, or the word none",
        "payload_sha256": "0" * 64,
        "payload_bytes": 1,
        "payload_media_type": "application/vnd.mira.m075-private-bank+tar",
        "payload_custody": "external-until-protocol-freeze",
        "payload_revealed_to_policy_authors": False,
        "task_count": 16,
        "matched_capability_pairs": 8,
        "domains": [
            {"opaque_domain_id": "opaque-" + f"{index:016x}", "matched_capability_pairs": 2}
            for index in range(MINIMUM_DOMAINS)
        ],
        "materially_cross_domain_attested": True,
        "public_task_reuse_excluded_attested": True,
        "evaluator_owned_success_attested": True,
        "signature_namespace": SIGNATURE_NAMESPACE,
        "maintainer_public_key_sha256": "0" * 64,
    }


def instructions() -> str:
    return f"""\
Signing the envelope
====================

You need an SSH key you control. The project must never hold its private half.

1. Compute the payload digest on your own machine. The archive stays with you.

       sha256sum your-private-bank.tar

   Put that value in "payload_sha256" and the archive size in "payload_bytes".

2. Record the SHA-256 of your public key in "maintainer_public_key_sha256".

       sha256sum ~/.ssh/id_ed25519.pub

3. Sign the envelope bytes in the project's namespace.

       ssh-keygen -Y sign -f ~/.ssh/id_ed25519 \\
           -n {SIGNATURE_NAMESPACE} \\
           {ENVELOPE_PATH}

   This writes {SIGNATURE_PATH}.

4. Publish the signer line so the project can verify without holding your key.

       echo "YOUR-IDENTITY namespaces=\\"{SIGNATURE_NAMESPACE}\\" $(cat ~/.ssh/id_ed25519.pub)" \\
           > {ALLOWED_SIGNERS_PATH}

   The identity string must match "maintainer_identity" exactly.

5. Send the project only these three files. Never the archive.

       {ENVELOPE_PATH}
       {SIGNATURE_PATH}
       {ALLOWED_SIGNERS_PATH}

The project then runs `python scripts/check_m075_private_readiness.py --require-ready`, freezes its
scientific protocol against your envelope digest, and only afterwards asks you to release the
payload. If it asks for the payload before that freeze, refuse: the ordering is the whole point.
"""


def validate(path: Path, *, signature_verified: bool) -> int:
    """Check a candidate envelope with the gate's own validator. Returns a process exit code."""

    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        print(f"cannot read {path}: {error}")
        return 2
    if not isinstance(envelope, dict):
        print("the envelope must be one JSON object")
        return 2

    placeholders = sorted(
        key for key, value in envelope.items()
        if isinstance(value, str) and value.startswith("REPLACE")
    )
    if placeholders:
        print("placeholders still present: " + ", ".join(placeholders))
        return 2

    try:
        validate_private_envelope(envelope, signature_verified=signature_verified)
    except M075PrivateReadinessError as error:
        print(f"envelope rejected: {error}")
        if not signature_verified:
            print(
                "note: rerun with --signature-verified once ssh-keygen -Y verify succeeds, "
                "since the gate also requires a verified signature"
            )
        return 2

    print("envelope accepted by the same validator the readiness gate enforces")
    print(f"  maintainer    : {envelope['maintainer_identity']}")
    print(f"  domains       : {len(envelope['domains'])} (minimum {MINIMUM_DOMAINS})")
    print(
        f"  matched pairs : {envelope['matched_capability_pairs']} "
        f"(minimum {MINIMUM_MATCHED_CAPABILITY_PAIRS})"
    )
    print(f"  tasks         : {envelope['task_count']}")
    if not signature_verified:
        print("  signature     : NOT CHECKED — the gate will still refuse until it verifies")
    return 0


def project_identities() -> frozenset[str]:
    """Exposed so the brief and its regressions cannot drift from the enforced exclusion."""

    return PROJECT_IDENTITIES
