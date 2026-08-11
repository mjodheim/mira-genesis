"""Intake kit for the independent M085 cross-domain task-bank maintainer.

`m085_cross_domain_intake` states whether the project may reveal the bank. It does nothing for the
one person who can unblock it. M075's kit exists for the same reason: reconstructing a closed
envelope schema, opaque identifiers and an SSH signing namespace from source is hours of work for an
outside volunteer, and that friction is the real cost of a pre-reveal boundary.

This emits the template, prints the exact signing commands, explains the domain adapter contract and
validates a candidate envelope with the gate's own validator so the two cannot diverge.

It deliberately cannot sign: a signature produced here would let the project attest its own
independence, which is the failure the boundary exists to prevent. It never opens task content.
"""
from __future__ import annotations

import json
from pathlib import Path

from metamorphosis.m085_cross_domain_intake import (
    ADAPTER_CONTRACT_VERSION,
    ENVELOPE_SCHEMA,
    MINIMUM_CORRECTNESS_CRITICAL_TASKS_PER_DOMAIN,
    MINIMUM_DOMAINS,
    MINIMUM_TASKS_PER_DOMAIN,
    PAYLOAD_MEDIA_TYPE,
    SIGNATURE_NAMESPACE,
    M085IntakeError,
    validate_bank_envelope,
)
from metamorphosis.m075_private_readiness import PROJECT_IDENTITIES

ENVELOPE_PATH = "experiments/M085/CROSS_DOMAIN_BANK_ENVELOPE.json"
SIGNATURE_PATH = "experiments/M085/CROSS_DOMAIN_BANK_ENVELOPE.sshsig"
ALLOWED_SIGNERS_PATH = "experiments/M085/CROSS_DOMAIN_BANK_ALLOWED_SIGNERS"


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
        "payload_media_type": PAYLOAD_MEDIA_TYPE,
        "payload_custody": "external-until-protocol-freeze",
        "payload_revealed_to_policy_authors": False,
        "adapter_contract_version": ADAPTER_CONTRACT_VERSION,
        "domain_count": MINIMUM_DOMAINS,
        "task_count": MINIMUM_DOMAINS * MINIMUM_TASKS_PER_DOMAIN,
        "domains": [
            {
                "opaque_domain_id": "opaque-" + f"{index:016x}",
                "task_count": MINIMUM_TASKS_PER_DOMAIN,
                "correctness_critical_tasks": MINIMUM_CORRECTNESS_CRITICAL_TASKS_PER_DOMAIN,
                "material_difference_statement_sha256": f"{index:064x}",
            }
            for index in range(1, MINIMUM_DOMAINS + 1)
        ],
        "materially_distinct_domains_attested": True,
        "correctness_critical_definition_accepted": True,
        "evaluator_owned_success_attested": True,
        "public_task_reuse_excluded_attested": True,
        "signature_namespace": SIGNATURE_NAMESPACE,
        "maintainer_public_key_sha256": "0" * 64,
    }


def adapter_contract() -> str:
    return f"""\
The domain adapter contract ({ADAPTER_CONTRACT_VERSION})
========================================================

Each domain is a directory in your archive. The project's organism must be able to drive it without
knowing anything about what it is, so the domain exposes four things and nothing else.

1. `describe()` -> the carrier names it accepts, and a cost for each.
   A carrier is whatever your domain lets a task hold a value in: a file path, a record key, a cell,
   a field. The organism only ever sees the names and the costs.

2. `observe(carriers)` -> the value each named carrier currently holds, or null.
   This is the only way the organism learns anything about your domain's state.

3. `act(kind, carrier, value)` -> whatever your domain reports back.
   `kind` is one of `put`, `remove`, `read`, `list`. **What this returns is not trusted and is never
   scored.** In a correctness-critical task it will sometimes report success for an action that had
   no effect, and that is the point of the experiment.

4. `evaluate(task)` -> whether the task's goal holds, decided by you, from your domain's real state.
   The organism never calls this and never sees its result.

A task is a goal expressed as the values certain carriers must end up holding, a step budget, and
nothing else. **You must not supply a decomposition, a hint, or an ordering.** Working out how to
reach the goal is the thing being measured.

What makes a task correctness-critical
--------------------------------------

At least {MINIMUM_CORRECTNESS_CRITICAL_TASKS_PER_DOMAIN} of your {MINIMUM_TASKS_PER_DOMAIN} tasks per
domain must satisfy all three of these:

  (a) some action is accepted by the domain and has no effect on its state;
  (b) a later step is only correct if that action actually took effect;
  (c) committing on the false premise reaches a terminal state the task's own budget cannot undo.

The reason for (c) is specific. An earlier experiment in this project found that an agent which
trusts what an action reported merely spent more steps than one that checked — it still got there in
the end. That makes for a weak claim. Here, an agent that trusts its actions must end up **wrong**,
and unable to tell that it is.

What "materially different" means
---------------------------------

Two domains are materially different if a strategy that exploits the first's structure buys nothing
in the second: different state, different vocabulary of carriers, different way of observing. Three
flavours of the same file store are not three domains.

Write one short paragraph per domain justifying this, keep the paragraphs, and put the SHA-256 of
each into `material_difference_statement_sha256`. The digests must all differ. You do not send the
paragraphs now — the project checks them against these digests after the payload is released, so
the attestation can be falsified later rather than merely believed now.
"""


def instructions() -> str:
    return f"""\
Signing the envelope
====================

You need an SSH key you control. The project must never hold its private half.

1. Compute the payload digest on your own machine. The archive stays with you.

       sha256sum your-cross-domain-bank.tar

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

6. Keep one more secret until later: a random assignment salt. The project publishes, before it
   knows the salt, exactly how the held-out domain will be derived from it. You release it only
   after the protocol is frozen. That is what stops the project from choosing which of your domains
   it is tested on.

       python -c "import secrets; print(secrets.token_hex(32))"

The project then runs `python scripts/check_m085_readiness.py --require-ready`, freezes its
scientific protocol against your envelope digest, and only afterwards asks for the salt and the
payload. If it asks for either before that freeze, refuse: the ordering is the whole point.
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
        validate_bank_envelope(envelope, signature_verified=signature_verified)
    except M085IntakeError as error:
        print(f"envelope rejected: {error}")
        if not signature_verified:
            print(
                "note: rerun with --signature-verified once ssh-keygen -Y verify succeeds, "
                "since the gate also requires a verified signature"
            )
        return 2

    print("envelope accepted by the same validator the readiness gate enforces")
    print(f"  maintainer         : {envelope['maintainer_identity']}")
    print(f"  domains            : {envelope['domain_count']} (minimum {MINIMUM_DOMAINS})")
    print(f"  tasks              : {envelope['task_count']}")
    critical = sum(int(domain["correctness_critical_tasks"]) for domain in envelope["domains"])
    print(
        f"  correctness-critical: {critical} "
        f"(minimum {MINIMUM_CORRECTNESS_CRITICAL_TASKS_PER_DOMAIN} per domain)"
    )
    if not signature_verified:
        print("  signature          : NOT CHECKED — the gate will still refuse until it verifies")
    return 0


def project_identities() -> frozenset[str]:
    """Exposed so the brief and its regressions cannot drift from the enforced exclusion."""

    return PROJECT_IDENTITIES
