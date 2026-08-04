"""Execute and preserve the one M039 canonical three-cycle result.

Marker/head/protocol binding failures abort. Scientific negatives such as generator
exhaustion, missing reuse, ablation success or replay divergence are rendered into the first
artifact and exit normally; they never authorize a replacement run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re

from metamorphosis.m038_journal import encode
from metamorphosis.m039_engine import (
    CYCLE_ONE_SEARCH_DEPTH,
    LATER_CYCLE_SEARCH_DEPTH,
    OBSERVATION_WORDS,
    M039EngineError,
    replay_m039,
    run_m039_development,
)
from metamorphosis.m039_lineage import M039IntegrityError
from metamorphosis.m039_provenance import journal_verified_gate2_tool_ids
from metamorphosis.m039_search_audit import (
    M039SearchAuditError,
    audit_result_searches,
)
from metamorphosis.m039_sealed import sealed_spec

SCHEMA = "m039-canonical-result/1"
_ARM_SCHEMA = "m039-canonical-arm/1"
_SHA = re.compile(r"\A[0-9a-f]{40}\Z")
_DIGEST = re.compile(r"\A[0-9a-f]{64}\Z")


class CanonicalRunError(RuntimeError):
    pass


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


def _audits(result):
    return audit_result_searches(
        tasks=result.cycle_tasks,
        cycles=result.manifest.cycles,
        final_registry=result.manifest.tool_registry,
        cycle_one_depth=CYCLE_ONE_SEARCH_DEPTH,
        later_depth=LATER_CYCLE_SEARCH_DEPTH,
        observation_words=OBSERVATION_WORDS,
    )


def _positive_result(seed: int, protocol_commitment: str) -> dict[str, object]:
    result = run_m039_development(
        seed,
        protocol_commitment=protocol_commitment,
        require_replay=True,
    )
    records = tuple(result.lineage_journal_records)
    verified_tools = journal_verified_gate2_tool_ids(result.manifest, records)
    initial_audits = _audits(result)
    independently_replayed = replay_m039(result.replay_inputs)
    replay_audits = _audits(independently_replayed)
    audit_mappings = tuple(audit.mapping() for audit in initial_audits)
    replay_mappings = tuple(audit.mapping() for audit in replay_audits)
    audits_exact = audit_mappings == replay_mappings
    journal_exact = records == independently_replayed.lineage_journal_records

    rollback_exact = all(cycle.rollback_restored_exactly for cycle in result.manifest.cycles)
    gate2_supported = bool(verified_tools) and result.tool_ablation_supported
    gate9_supported = (
        result.three_cycles_accepted
        and result.later_tool_reuse_supported
        and result.seed_to_head_replay_supported
        and rollback_exact
        and journal_exact
        and audits_exact
        and all(audit.evidence_rejections > 0 for audit in initial_audits)
    )

    mapping = result.mapping()
    mapping["engine_candidate_gate2_tool_ids"] = list(result.gate2_tool_ids)
    mapping["gate2_tool_ids"] = list(verified_tools)
    mapping["gate2_eligibility_verified_from_journal"] = True
    mapping["complete_search_audits"] = list(audit_mappings)
    mapping["complete_search_audits_replayed_exactly"] = audits_exact
    mapping["lineage_journal_records"] = [record.hex() for record in records]
    mapping["lineage_journal_records_sha256"] = hashlib.sha256(encode(records)).hexdigest()
    mapping["lineage_journal_replayed_byte_exact"] = journal_exact
    mapping["rollback_exact_in_all_cycles"] = rollback_exact
    mapping["gate2_supported"] = gate2_supported
    mapping["gate9_supported"] = gate9_supported
    mapping["combined_expected_claim_supported"] = gate2_supported and gate9_supported
    mapping["scientific_outcome"] = "positive" if mapping["combined_expected_claim_supported"] else "negative"
    return mapping


def render_canonical_result(
    *,
    head_sha: str,
    parent_sha: str,
    marker_path: Path,
    protocol_path: Path,
) -> bytes:
    if os.environ.get("M039_CANONICAL_RUN") != "1":
        raise CanonicalRunError("M039 canonical execution is available only to the guarded workflow")
    if not _SHA.match(head_sha) or not _SHA.match(parent_sha):
        raise CanonicalRunError("canonical head and parent must be full lowercase 40-hex SHAs")

    marker = _load_marker(marker_path)
    if marker["frozen_parent_sha"] != parent_sha:
        raise CanonicalRunError("canonical marker does not name the actual parent commit")

    protocol_bytes = protocol_path.read_bytes()
    protocol_sha256 = hashlib.sha256(protocol_bytes).hexdigest()
    if protocol_sha256 != marker["protocol_sha256"]:
        raise CanonicalRunError("frozen protocol bytes do not match the marker commitment")
    if not _DIGEST.match(protocol_sha256):
        raise CanonicalRunError("protocol digest is not canonical")

    spec = sealed_spec(
        head_sha,
        frozen_parent_sha=parent_sha,
        protocol_sha256=protocol_sha256,
    )
    protocol_commitment = f"sha256:{protocol_sha256}"
    try:
        result: dict[str, object] = _positive_result(spec.task_seed, protocol_commitment)
    except (M039EngineError, M039IntegrityError, M039SearchAuditError) as error:
        result = {
            "scientific_outcome": "negative",
            "gate2_supported": False,
            "gate9_supported": False,
            "combined_expected_claim_supported": False,
            "negative_reason_type": type(error).__name__,
            "negative_reason": str(error),
        }

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
        "result": result,
    }
    return (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode("utf-8")


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
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(rendered)
    parsed = json.loads(rendered)
    print(f"sha256={hashlib.sha256(rendered).hexdigest()}")
    print(f"sealed_spec_digest={parsed['sealed_spec']['spec_digest']}")
    print(
        "combined_expected_claim_supported="
        f"{str(bool(parsed['result']['combined_expected_claim_supported'])).lower()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
