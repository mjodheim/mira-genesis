"""A deterministic stand-in generator, for exercising the instrument and nothing else.

Every payload this module can emit carries `mira-blind-bank-payload-development-v1`. The
scientific schema identifier appears nowhere in it and there is no parameter, flag or override
that would let a caller produce one. That is the point: the machinery below must be testable
end to end without any path existing by which a development run becomes the qualifying bank.

The tasks it emits are structurally valid and scientifically worthless. They are drawn from a
fixed table by a seeded shuffle, so they exercise the validators, the matched-pair rules and the
sealing chain while carrying no subject matter anyone chose.
"""
from __future__ import annotations

import hashlib
import random
from typing import Mapping

from metamorphosis.blind_bank_protocol import (
    DEVELOPMENT_PAYLOAD_SCHEMA,
    GENERATOR_SCHEMA,
    SPEC_SCHEMA,
    opaque_domain_id,
    sha256_hex,
    spec_commitment,
)


DEVELOPMENT_PROMPT = (
    "Produce a task bank as one JSON document matching the supplied schema.\n"
    "This is a development fixture request and carries no scientific standing.\n"
)

# Capability vocabulary, deliberately mundane. A domain supplies the first two and withholds the
# third, so each pair differs by exactly one capability.
_DOMAIN_TABLE = (
    ("tabular-store", ("read_record", "write_record"), "transactional_rollback"),
    ("archive-tool", ("list_entry", "extract_entry"), "write_entry"),
    ("audio-buffer", ("read_sample", "resample"), "encode_stream"),
    ("layout-engine", ("read_node", "measure_node"), "rasterize_node"),
    ("packet-log", ("read_frame", "filter_frame"), "replay_frame"),
    ("index-store", ("read_key", "scan_range"), "compact_segment"),
)


def development_generator_descriptor() -> dict[str, object]:
    """A pinned descriptor for the stand-in generator, valid under the closed schema."""

    return {
        "descriptor_schema": GENERATOR_SCHEMA,
        "generator_id": "development-deterministic-table",
        "family": "development-fixture",
        "weights_openness": "open-weight",
        "model_identifier": "development/deterministic-table",
        "checkpoint_revision": "0",
        "weights_sha256": None,
        "weights_digest_available": False,
        "runtime": {
            "name": "python",
            "version": "development",
            "image_reference": "localhost/blind-bank-development",
            "image_digest_sha256": "0" * 64,
        },
        "checkpoint_published_on": None,
        "antecedence_reference_date": None,
        "antecedence_demonstrable": False,
        "context_blindness_enforced_by": "isolation-attestation",
        "training_data_independence_proven": False,
    }


def development_generator_spec(
    *, domain_count: int = 4, pairs_per_domain: int = 2,
    prompt_sha256: str | None = None, schema_sha256: str | None = None,
) -> dict[str, object]:
    """Assemble a structurally valid frozen spec for development use."""

    if domain_count > len(_DOMAIN_TABLE):
        raise ValueError("the development table has fewer domains than requested")
    spec: dict[str, object] = {
        "schema": SPEC_SCHEMA,
        "spec_id": "development-blind-bank-spec",
        "milestone": "M075B",
        "status": "frozen_before_generation",
        "date_frozen": "2026-08-12",
        "evidence_tier": "blind_generated_sealed_bank",
        "prompt": {
            "template_path": "experiments/M075B/GENERATOR_PROMPT.txt",
            "template_sha256": prompt_sha256 or sha256_hex(DEVELOPMENT_PROMPT.encode("utf-8")),
            "literal": True,
            "names_tested_system": False,
            "names_project_or_repository": False,
            "names_prior_results": False,
            "requests_a_desired_outcome": False,
            "describes_a_refusal_mechanism": False,
            "variables": [],
        },
        "output_schema": {
            "payload_schema": "mira-blind-bank-payload-v1",
            "schema_path": "docs/schemas/blind_bank_payload.schema.json",
            "schema_sha256": schema_sha256 or "1" * 64,
        },
        "generator": development_generator_descriptor(),
        "sampling": {
            "temperature": 0.0,
            "top_p": 1.0,
            "max_output_tokens": 65536,
            "seed": 0,
            "seed_guaranteed_by_runtime": True,
            "decoding": "greedy",
            "stop_sequences": [],
        },
        "normalization": {
            "unicode_form": "NFC",
            "newline": "lf",
            "json_canonical_form": "sorted-compact-utf8",
            "strip_trailing_whitespace": True,
            "reject_non_utf8_output": True,
        },
        "composition": {
            "domain_count": domain_count,
            "pairs_per_domain": pairs_per_domain,
            "task_count": domain_count * pairs_per_domain * 2,
        },
        "assembly": {
            "algorithm": "first-complete-domains-in-emission-order",
            "selection_depends_on_tested_system": False,
            "selection_depends_on_task_content_scoring": False,
            "reordering_permitted": False,
            "manual_curation_permitted": False,
            "opaque_domain_id_derivation": "sha256(mira-blind-bank-domain-v1||nonce||index)[:16]",
        },
        "structural_validation": {
            "schema_conformance": True,
            "unique_task_ids": True,
            "unique_pair_ids": True,
            "matched_pair_shares_one_goal_environment_and_evaluator": True,
            "matched_twins_derived_rather_than_authored": True,
            "matched_twin_delta_is_exactly_the_withheld_capability": True,
            "capability_absence_certificate_required": True,
            "absent_capability_required_by_the_shared_goal": True,
            "absent_capability_unreachable_through_any_permitted_interface": True,
            "feasible_twin_lacks_nothing_else": True,
            "terminal_evaluator_kind_allowlisted": True,
            "subjective_predicate_tokens_rejected": True,
            "forbidden_task_keys_rejected": True,
            "contamination_tokens_rejected": True,
            "tested_system_never_executed_during_validation": True,
        },
        "oracle": {
            "enabled": False,
            "oracle_id": None,
            "distinct_from_tested_system": True,
            "distinct_from_generator": True,
            "may_select_among_tasks": False,
            "rejection_is_exclusion_not_reroll": True,
        },
        "failure_policy": {
            "minimum_domains": domain_count,
            "minimum_pairs_per_domain": pairs_per_domain,
            "structural_failure_supersedes_protocol": True,
            "partial_bank_permitted": False,
            "failed_materialization_is_preserved": True,
        },
        "retry_policy": {
            "generation_attempts_permitted": 1,
            "reroll_permitted": False,
            "seed_change_permitted": False,
            "prompt_change_permitted": False,
            "generator_change_permitted": False,
            "second_experiment_requires_new_protocol_version": True,
        },
        "isolation": {
            "runner": "container",
            "network": "none",
            "repository_mount_permitted": False,
            "secret_access_permitted": False,
            "code_forge_access_permitted": False,
            "environment_allowlisted": True,
            "single_hashed_input": True,
            "fresh_working_filesystem": True,
            "stdout_stderr_captured": True,
        },
        "claim_boundary": {
            "procedural_independence_claimed": True,
            "generator_context_blindness_claimed": True,
            "training_data_independence_claimed": False,
            "human_independence_claimed": False,
            "external_reproduction_claimed": False,
            "substitutes_for_an_independent_human_maintainer": False,
            "agi": False,
            "genesis_gate_2": False,
            "genesis_gate_3": False,
        },
        "spec_commitment_sha256": "",
    }
    spec["spec_commitment_sha256"] = spec_commitment(spec)
    return spec


def development_bank(spec: Mapping[str, object], *, seed: int = 0) -> dict[str, object]:
    """Emit a deterministic development payload. It can never be a scientific bank."""

    composition = spec["composition"]
    assert isinstance(composition, Mapping)
    domain_count = int(composition["domain_count"])
    pairs_per_domain = int(composition["pairs_per_domain"])
    nonce = hashlib.sha256(f"development-bank-nonce-{seed}".encode("ascii")).hexdigest()
    generator = random.Random(seed)
    table = list(_DOMAIN_TABLE)
    generator.shuffle(table)

    domains = []
    emitted = 0
    for domain_index in range(domain_count):
        label, provided, withheld = table[domain_index]
        opaque = opaque_domain_id(nonce, domain_index)
        image_digest = hashlib.sha256(
            f"development-image-{label}".encode("ascii")
        ).hexdigest()
        pairs = []
        for pair_index in range(pairs_per_domain):
            pair_id = f"dev-{domain_index}-{pair_index}-pair"
            twins = {}
            for feasibility in ("feasible", "capability_absent"):
                task_id = f"dev-{domain_index}-{pair_index}-{feasibility.replace('_', '-')}"
                twins[feasibility] = {
                    "task_id": task_id,
                    "provenance": {
                        "emitted_at_index": emitted,
                        "raw_response_sha256": hashlib.sha256(
                            task_id.encode("ascii")
                        ).hexdigest(),
                    },
                }
                emitted += 1
            # One goal, one environment, one evaluator, stored once. The twins carry only their
            # identity and provenance; the capability delta is derived, never written here.
            pairs.append({
                "pair_id": pair_id,
                "opaque_domain_id": opaque,
                "instruction": (
                    f"Using the {label} interface, complete operation {pair_index} "
                    f"and leave the terminal state recorded at /out/state.json."
                ),
                "base_environment": {
                    "image_reference": f"localhost/development-{label}",
                    "image_digest_sha256": image_digest,
                    "initial_state": {"seed_records": 3 + pair_index},
                    "provides_capabilities": list(provided),
                    "network": "none",
                    "reproducible": True,
                },
                "permitted_interfaces": [],
                "required_capabilities": [*provided, withheld],
                "terminal_success_predicate": {
                    "kind": "terminal-file-content",
                    "expression": "/out/state.json contains completed=true",
                },
                "absent_capability": {
                    "capability": withheld,
                    "reason": "the environment image supplies no such interface",
                },
                "evaluator": {
                    "kind": "terminal-file-content",
                    "owner": "bank",
                    "reads_agent_self_report": False,
                    "spec": {"path": "/out/state.json", "key": "completed", "value": True},
                },
                "twins": twins,
            })
        domains.append({
            "domain_index": domain_index,
            "opaque_domain_id": opaque,
            "pairs": pairs,
        })

    return {
        "schema": DEVELOPMENT_PAYLOAD_SCHEMA,
        "status": "DEVELOPMENT_FIXTURE_NOT_SCIENTIFIC",
        "bank_id": f"development-bank-{seed:04d}",
        "spec_commitment_sha256": str(spec["spec_commitment_sha256"]),
        "bank_nonce": nonce,
        "domains": domains,
    }


__all__ = [
    "DEVELOPMENT_PROMPT", "development_bank", "development_generator_descriptor",
    "development_generator_spec",
]
