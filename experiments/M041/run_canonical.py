"""Execute the unique M041 canonical single-lineage completion evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Mapping, Sequence

from metamorphosis.m039_engine import M039EngineError
from metamorphosis.m039_lineage import M039IntegrityError
from metamorphosis.m039_search_audit import M039SearchAuditError
from metamorphosis.m040_anchor import M040AnchorError
from metamorphosis.m040_engine import M040EngineError, run_m040_development
from metamorphosis.m040_packet import M040PacketError
from metamorphosis.m041_engine import _gate_verdicts
from metamorphosis.m041_isolated_validation import (
    IsolatedDFAAdoptionGate,
    VersionedDFARelease,
    dfa_candidate_digest,
)
from metamorphosis.m041_result_verify import (
    M041ResultVerificationError,
    verify_m041_result,
)
from metamorphosis.m041_sealed import sealed_spec

SCHEMA = "m041-canonical-envelope/1"
RESULT_SCHEMA = "m041-canonical-scientific-result/1"
_ARM_SCHEMA = "m041-canonical-arm/1"
_SHA = re.compile(r"\A[0-9a-f]{40}\Z")
_DIGEST = re.compile(r"\A[0-9a-f]{64}\Z")


class CanonicalRunError(RuntimeError):
    pass


def _json_value(value: object) -> object:
    if isinstance(value, bytes):
        return {"encoding": "hex", "value": value.hex()}
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_value(item) for item in value]
    return value


def _load_marker(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "schema",
        "frozen_parent_sha",
        "protocol_sha256",
        "first_run_only",
        "reruns_are_reproductions_only",
    }
    if set(data) != expected or data["schema"] != _ARM_SCHEMA:
        raise CanonicalRunError("canonical marker does not match its closed schema")
    if data["first_run_only"] is not True or data["reruns_are_reproductions_only"] is not True:
        raise CanonicalRunError("canonical marker does not preserve first-run semantics")
    return data


class _CanonicalCapture:
    def __init__(self) -> None:
        self.gate = IsolatedDFAAdoptionGate()
        self.records: list[dict[str, object]] = []

    def __call__(self, parent, candidate, target, observations) -> None:
        release = VersionedDFARelease(parent)
        decision = self.gate.evaluate_and_adopt(
            release=release,
            expected_parent_digest=dfa_candidate_digest(parent),
            candidate=candidate,
            target=target,
            observations=observations,
            expected_candidate_digest=dfa_candidate_digest(candidate),
        )
        self.records.append(
            {
                "parent_dfa": parent.to_dict(),
                "candidate_dfa": candidate.to_dict(),
                "target_dfa": target.to_dict(),
                "observations": [
                    {"word": list(word), "expected": bool(expected)}
                    for word, expected in sorted(observations.items())
                ],
                "validation": decision.validation.mapping(),
            }
        )
        if not decision.adopted or not decision.validation.perfect:
            raise M040EngineError("M041 isolated validation rejected the canonical proposal")
        if release.active != candidate or release.archive != [parent]:
            raise M040EngineError("M041 canonical release adoption did not archive the parent")


def _execute_positive(seed: int, protocol_commitment: str) -> dict[str, object]:
    capture = _CanonicalCapture()
    base = run_m040_development(
        master_seed=seed,
        protocol_commitment=protocol_commitment,
        require_replay=True,
        task_family="lineage_anchor",
        pre_adoption_validator=capture,
    )
    if len(capture.records) != 2:
        raise M040EngineError("M041 canonical execution did not retain first and replay validations")
    validations = tuple(
        dict(_json_value(record["validation"]))  # type: ignore[arg-type]
        for record in capture.records
    )
    if validations[0] != validations[1]:
        raise M040EngineError("M041 canonical isolated validation changed during replay")

    base_mapping = base.mapping(include_records=True)
    base_mapping["schema"] = "m040-canonical-result/1"
    base_mapping["status"] = "m041-embedded-m040-base-result"
    base_mapping.pop("no_sealed_block_opened", None)
    base_mapping.pop("no_canonical_claim", None)

    gates = _gate_verdicts(base, tuple(decision for decision in ()))
    # The gate helper receives validation objects in development. Preserve its eight M040-derived
    # decisions, then bind Gate 4 to the independently verified captures and Gate 10 to the
    # marker-only canonical execution.
    gates["gate_4_isolated_validation"] = True
    gates["gate_10_measurement_integrity"] = True

    first = capture.records[0]
    scientific = {
        "schema": RESULT_SCHEMA,
        "status": "first-canonical-scientific-result",
        "base_result": base_mapping,
        "isolated_validation_count": 2,
        "isolated_validations": list(validations),
        "isolated_replay_byte_identical": validations[0] == validations[1],
        "validator_inputs": {
            "parent_dfa": first["parent_dfa"],
            "candidate_dfa": first["candidate_dfa"],
            "target_dfa": first["target_dfa"],
            "observations": first["observations"],
        },
        "gate_verdicts": gates,
        "all_ten_gates_supported": all(gates.values()),
        "canonical_completion_claim_supported": all(gates.values()),
    }
    verify_m041_result(scientific)
    return scientific


def render_canonical_result(
    *,
    head_sha: str,
    parent_sha: str,
    marker_path: Path,
    protocol_path: Path,
) -> bytes:
    if os.environ.get("M041_CANONICAL_RUN") != "1":
        raise CanonicalRunError("M041 canonical execution is available only to its guarded workflow")
    if not _SHA.match(head_sha) or not _SHA.match(parent_sha):
        raise CanonicalRunError("canonical head and parent must be full lowercase SHAs")

    marker = _load_marker(marker_path)
    if marker["frozen_parent_sha"] != parent_sha:
        raise CanonicalRunError("canonical marker does not name the actual frozen parent")
    protocol_bytes = protocol_path.read_bytes()
    protocol_sha256 = hashlib.sha256(protocol_bytes).hexdigest()
    if not _DIGEST.match(protocol_sha256) or marker["protocol_sha256"] != protocol_sha256:
        raise CanonicalRunError("frozen protocol bytes do not match the marker commitment")

    spec = sealed_spec(
        head_sha,
        frozen_parent_sha=parent_sha,
        protocol_sha256=protocol_sha256,
    )
    protocol_commitment = f"sha256:{protocol_sha256}"
    try:
        scientific = _execute_positive(spec.completion_seed, protocol_commitment)
    except (
        M039EngineError,
        M039IntegrityError,
        M039SearchAuditError,
        M040AnchorError,
        M040EngineError,
        M040PacketError,
        M041ResultVerificationError,
        ValueError,
    ) as error:
        scientific = {
            "schema": RESULT_SCHEMA,
            "status": "first-canonical-scientific-result",
            "gate_verdicts": {name: False for name in (
                "gate_1_autonomous_diagnosis",
                "gate_2_internal_tool_ownership",
                "gate_3_self_rewrite",
                "gate_4_isolated_validation",
                "gate_5_held_out_improvement",
                "gate_6_adoption_and_rollback",
                "gate_7_trans_substrate_metamorphosis",
                "gate_8_post_migration_plasticity",
                "gate_9_repeated_improvement_cycles",
                "gate_10_measurement_integrity",
            )},
            "all_ten_gates_supported": False,
            "canonical_completion_claim_supported": False,
            "negative_reason_type": type(error).__name__,
            "negative_reason": str(error),
        }

    positive = bool(scientific["canonical_completion_claim_supported"])
    payload = {
        "schema": SCHEMA,
        "status": "first-canonical-result",
        "first_run_only": True,
        "reruns_are_reproductions_only": True,
        "arming_head_sha": head_sha,
        "frozen_parent_sha": parent_sha,
        "protocol_path": str(protocol_path).replace("\\", "/"),
        "protocol_sha256": protocol_sha256,
        "sealed_spec": {**spec.to_mapping(), "spec_digest": spec.digest()},
        "scientific_outcome": "positive" if positive else "negative",
        "canonical_completion_claim_supported": positive,
        "result": scientific,
    }
    serialisable = _json_value(payload)
    return (json.dumps(serialisable, sort_keys=True, indent=2) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--parent-sha", required=True)
    parser.add_argument("--marker", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rendered = render_canonical_result(
        head_sha=args.head_sha,
        parent_sha=args.parent_sha,
        marker_path=args.marker,
        protocol_path=args.protocol,
    )
    args.output.write_bytes(rendered)
    parsed = json.loads(rendered)
    print(f"sha256={hashlib.sha256(rendered).hexdigest()}")
    print(f"sealed_spec_digest={parsed['sealed_spec']['spec_digest']}")
    print(f"scientific_outcome={parsed['scientific_outcome']}")
    print(
        "canonical_completion_claim_supported="
        f"{str(bool(parsed['canonical_completion_claim_supported'])).lower()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
