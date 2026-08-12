"""Exercise the blind sealed-bank instrument end to end on a development fixture.

This never contacts a model, never opens a network socket and never writes inside the repository.
It exists so that the validators, the isolation planner and the sealing chain can be driven by
hand without any path existing by which the exercise becomes the qualifying bank: every payload
it emits carries the development schema, which the readiness gate does not accept.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.blind_bank_devkit import (  # noqa: E402
    DEVELOPMENT_PROMPT,
    development_bank,
    development_generator_spec,
)
from metamorphosis.blind_bank_isolation import (  # noqa: E402
    CONTAINER_OUTPUT_DIRECTORY,
    build_attestation,
    plan_invocation,
)
from metamorphosis.blind_bank_protocol import (  # noqa: E402
    generator_commitment,
    sha256_hex,
    validate_bank_payload,
    validate_generator_spec,
)
from metamorphosis.blind_bank_sealing import (  # noqa: E402
    canonicalize_payload,
    finalize_seal,
    sealing_plan,
)


def _emit(label: str, value: object) -> None:
    print(f"\n== {label} ==")
    print(json.dumps(value, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domains", type=int, default=4)
    parser.add_argument("--pairs-per-domain", type=int, default=2)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--workspace", default=None,
        help="a directory outside the repository; a temporary one is used when omitted",
    )
    parser.add_argument(
        "--print-prompt", action="store_true",
        help="print the development prompt and exit",
    )
    arguments = parser.parse_args()

    if arguments.print_prompt:
        print(DEVELOPMENT_PROMPT, end="")
        return 0

    spec = development_generator_spec(
        domain_count=arguments.domains, pairs_per_domain=arguments.pairs_per_domain,
    )
    validate_generator_spec(spec)
    _emit("frozen development specification", {
        "spec_id": spec["spec_id"],
        "spec_commitment_sha256": spec["spec_commitment_sha256"],
        "composition": spec["composition"],
    })

    payload = development_bank(spec, seed=arguments.seed)
    validate_bank_payload(payload, spec=spec, development=True)
    canonical = canonicalize_payload(payload)
    _emit("materialized development bank", {
        "bank_id": payload["bank_id"],
        "schema": payload["schema"],
        "payload_sha256": sha256_hex(canonical),
        "payload_bytes": len(canonical),
    })

    with tempfile.TemporaryDirectory() as scratch:
        workspace = Path(arguments.workspace) if arguments.workspace else Path(scratch)
        workspace.mkdir(parents=True, exist_ok=True)
        request = workspace / "request.json"
        request.write_text(
            json.dumps({"prompt_sha256": spec["prompt"]["template_sha256"]}, sort_keys=True),
            encoding="utf-8",
        )
        output = workspace / "out"
        output.mkdir(exist_ok=True)

        plan = plan_invocation(
            repository_root=ROOT,
            image_reference="localhost/blind-bank-development",
            image_digest_sha256="0" * 64,
            input_path=request,
            output_directory=output,
            environment={
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "BLIND_BANK_INPUT": "/blind/input/request.json",
                "BLIND_BANK_OUTPUT": str(CONTAINER_OUTPUT_DIRECTORY),
            },
            command=["/usr/local/bin/emit-bank"],
        )
        _emit("planned container invocation", plan["argv"])

        attestation = build_attestation(
            plan=plan,
            repository_root=ROOT,
            input_sha256=sha256_hex(request.read_bytes()),
            output_sha256=sha256_hex(canonical),
            stdout_sha256=sha256_hex(b""),
            stderr_sha256=sha256_hex(b""),
            started_at="2026-08-12T00:00:00Z",
            finished_at="2026-08-12T00:04:00Z",
            exit_status=0,
            runtime_name="development",
            runtime_version="0",
        )
        _emit("isolation attestation", {
            "attestation_sha256": attestation["attestation_sha256"],
            "environment_keys": attestation["environment_keys"],
            "network": attestation["network"],
        })

        plaintext = workspace / "bank.blind-bank-payload.json"
        plaintext.write_bytes(canonical)
        seal = sealing_plan(
            repository_root=ROOT,
            plaintext_path=plaintext,
            ciphertext_path=workspace / "bank.blind-bank.age",
            cipher="age-v1-x25519",
            recipient="age1developmentrecipientplaceholder",
        )
        _emit("sealing command", seal["argv"])

        commitment = finalize_seal(
            payload=payload,
            spec=spec,
            generator_commitment_sha256=generator_commitment(spec["generator"]),
            isolation_attestation_sha256=str(attestation["attestation_sha256"]),
            # A development exercise seals nothing, so the ciphertext digest stands in for one
            # that would exist after the external encryption command had run.
            ciphertext_sha256=sha256_hex(b"development-ciphertext"),
            cipher="age-v1-x25519",
            key_custody="offline-project-holder",
            sealed_at="2026-08-12T00:05:00Z",
            milestone="M075B",
        )
        _emit("public commitment", commitment)

    print(
        "\nThis was a development exercise. No scientific bank exists, "
        "no reveal is authorized, and none of these artifacts may be committed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
