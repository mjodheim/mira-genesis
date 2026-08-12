"""Report or enforce the M075-B blind sealed-bank reveal gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.blind_bank_devkit import (  # noqa: E402
    development_bank,
    development_generator_spec,
)
from metamorphosis.blind_bank_protocol import (  # noqa: E402
    BlindBankError,
    assert_matched_pair_delta,
    canonical_bytes,
    generator_commitment,
    sealed_run_binding_problems,
    sha256_hex,
    validate_bank_payload,
    validate_generation_ledger,
)
from metamorphosis.m075b_blind_readiness import (  # noqa: E402
    assess_blind_bank_readiness,
)


def _verify_ssh_signature(
    message: bytes, signature_path: Path, allowed_signers: Path, identity: str, namespace: str,
) -> bool:
    executable = shutil.which("ssh-keygen")
    if executable is None:
        return False
    completed = subprocess.run(
        [
            executable, "-Y", "verify", "-f", str(allowed_signers), "-I", identity,
            "-n", namespace, "-s", str(signature_path),
        ],
        input=message,
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0


def _self_test() -> list[str]:
    """Prove the three causal guarantees bite, on fixtures, every CI run.

    A checker that reports `phase: draft` on an empty repository proves nothing about what it
    would do once artifacts exist. These three probes construct the exact violations external
    review found and require each to be refused, so `sealed-bank-boundary` fails the moment any
    of the bindings stops holding — rather than years later when a real bank is sealed.
    """

    failures: list[str] = []
    spec = development_generator_spec()
    payload = development_bank(spec, seed=0)
    runtime = spec["generator"]["runtime"]  # type: ignore[index]
    payload_digest = sha256_hex(canonical_bytes(payload))

    attestation = {
        "attestation_sha256": "f" * 64,
        "output_sha256": payload_digest,
        "image_reference": runtime["image_reference"],
        "image_digest_sha256": runtime["image_digest_sha256"],
        "runtime_name": runtime["name"],
        "runtime_version": runtime["version"],
    }
    commitment = {
        "spec_commitment_sha256": spec["spec_commitment_sha256"],
        "generator_commitment_sha256": generator_commitment(spec["generator"]),  # type: ignore[arg-type]
        "isolation_attestation_sha256": "f" * 64,
        "payload_sha256": payload_digest,
    }
    ledger = {
        "schema": "mira-blind-bank-generation-ledger-v1",
        "entries": [{
            "attempt_index": 1,
            "spec_commitment_sha256": spec["spec_commitment_sha256"],
            "started_at": "2026-08-12T00:00:00Z",
            "outcome": "materialized",
            "payload_sha256": payload_digest,
            "isolation_attestation_sha256": "f" * 64,
            "note": "",
        }],
    }

    # A consistent run must bind, or every negative below would pass vacuously.
    if sealed_run_binding_problems(
        spec=spec, attestation=attestation, commitment=commitment, ledger=ledger,
    ):
        failures.append("a consistent sealed run no longer binds")

    # P1-1: an attestation from one run combined with a payload from another.
    mismatched = dict(commitment, payload_sha256="9" * 64)
    if not sealed_run_binding_problems(
        spec=spec, attestation=attestation, commitment=mismatched, ledger=ledger,
    ):
        failures.append("an attested output unrelated to the sealed payload is accepted")
    foreign_generator = dict(commitment, generator_commitment_sha256="9" * 64)
    if not sealed_run_binding_problems(
        spec=spec, attestation=attestation, commitment=foreign_generator, ledger=ledger,
    ):
        failures.append("a commitment naming another generator is accepted")
    foreign_image = dict(attestation, image_digest_sha256="9" * 64)
    if not sealed_run_binding_problems(
        spec=spec, attestation=foreign_image, commitment=commitment, ledger=ledger,
    ):
        failures.append("an attestation recording another image is accepted")

    # P1-2: a lone materialization belonging to a different frozen spec.
    foreign_ledger = json.loads(json.dumps(ledger))
    foreign_ledger["entries"][0]["spec_commitment_sha256"] = "b" * 64
    try:
        validate_generation_ledger(
            foreign_ledger, spec_commitment_sha256=str(spec["spec_commitment_sha256"]),
        )
    except BlindBankError:
        pass
    else:
        failures.append("a ledger materialization for another frozen spec is accepted")

    # P1-3: the matched pair's twins differ only by the withheld capability.
    pair = payload["domains"][0]["pairs"][0]  # type: ignore[index]
    try:
        assert_matched_pair_delta(pair)
    except BlindBankError as exc:
        failures.append(f"a well-formed matched pair is rejected: {exc}")
    supplied = json.loads(json.dumps(pair))
    supplied["base_environment"]["provides_capabilities"].append(
        supplied["absent_capability"]["capability"]
    )
    try:
        assert_matched_pair_delta(supplied)
    except BlindBankError:
        pass
    else:
        failures.append("a pair whose twins do not differ by the withheld capability is accepted")
    diverging = json.loads(json.dumps(payload))
    diverging["domains"][0]["pairs"][0]["twins"]["feasible"]["instruction"] = "a different goal"
    try:
        validate_bank_payload(diverging, spec=spec, development=True)
    except BlindBankError:
        pass
    else:
        failures.append("a twin carrying its own instruction is accepted")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-ready", action="store_true",
        help="fail unless every pre-reveal artifact is present, bound and unrevealed",
    )
    parser.add_argument(
        "--assert-not-revealed", action="store_true",
        help="fail if a reveal has been authorized or a scientific result exists",
    )
    parser.add_argument(
        "--require-phase", default=None,
        help="fail unless the milestone is in exactly this phase",
    )
    parser.add_argument(
        "--self-test", action="store_true",
        help="prove on fixtures that the causal bindings still refuse their violations",
    )
    arguments = parser.parse_args()

    if arguments.self_test:
        failures = _self_test()
        for failure in failures:
            print(f"broken guarantee: {failure}", file=sys.stderr)
        if failures:
            return 5
        print("the sealed-run, ledger and matched-pair bindings all refuse their violations")
        return 0

    report = assess_blind_bank_readiness(ROOT, signature_verifier=_verify_ssh_signature)
    print(json.dumps(report, indent=2, sort_keys=True))

    if arguments.require_ready and report["ready_for_reveal"] is not True:
        return 2
    if arguments.assert_not_revealed and (
        report["reveal_authorized"] is not False
        or report["scientific_result_exists"] is not False
    ):
        # The decisive line in CI. A sealed bank opened, or a result committed, without the
        # ordered chain of freezes must turn the repository red rather than be noticed later.
        print(
            "a reveal has been authorized or a result exists; this must be a deliberate, "
            "separately reviewed change",
            file=sys.stderr,
        )
        return 3
    if arguments.require_phase is not None and report["phase"] != arguments.require_phase:
        print(
            f"expected phase {arguments.require_phase!r}, found {report['phase']!r}",
            file=sys.stderr,
        )
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
