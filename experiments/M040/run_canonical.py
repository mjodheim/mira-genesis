"""Execute and preserve the unique M040 canonical post-migration result.

Marker, parent and protocol binding failures abort the workflow. Expected scientific
negatives are rendered into the first immutable artefact and exit normally; they never
authorize a replacement run.

The first execution at workflow run 30930249547 completed the mechanism and independent
verification, then failed while serialising raw journal ``bytes``. The JSON normaliser below
is the same representation already used by the development runner. A later preservation run
may reproduce only that exact arming-head seed and must identify itself as a reproduction.
"""

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
from metamorphosis.m040_result_verify import (
    M040ResultVerificationError,
    verify_m040_result,
)
from metamorphosis.m040_sealed import sealed_spec

SCHEMA = "m040-canonical-envelope/1"
RESULT_SCHEMA = "m040-canonical-result/1"
_ARM_SCHEMA = "m040-canonical-arm/1"
_SHA = re.compile(r"\A[0-9a-f]{40}\Z")
_DIGEST = re.compile(r"\A[0-9a-f]{64}\Z")
_EXECUTION_KINDS = {
    "first-execution",
    "reproduction-after-serialization-failure",
}


class CanonicalRunError(RuntimeError):
    pass


def _json_value(value: object) -> object:
    """Encode byte records exactly as the already-verified development artefacts do."""

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


def _positive_result(seed: int, protocol_commitment: str) -> dict[str, object]:
    result = run_m040_development(
        master_seed=seed,
        protocol_commitment=protocol_commitment,
        require_replay=True,
        task_family="lineage_anchor",
    )
    mapping = result.mapping(include_records=True)
    mapping["schema"] = RESULT_SCHEMA
    mapping["status"] = "first-canonical-scientific-result"
    mapping.pop("no_sealed_block_opened", None)
    mapping.pop("no_canonical_claim", None)
    mapping["scientific_outcome"] = (
        "positive"
        if (
            mapping["trans_substrate_continuity_supported"]
            and mapping["post_migration_plasticity_supported"]
            and mapping["replay_supported"]
        )
        else "negative"
    )
    mapping["combined_expected_claim_supported"] = (
        mapping["scientific_outcome"] == "positive"
    )
    verify_m040_result(mapping)
    return mapping


def render_canonical_result(
    *,
    head_sha: str,
    parent_sha: str,
    marker_path: Path,
    protocol_path: Path,
    execution_kind: str = "first-execution",
    original_run_id: str | None = None,
) -> bytes:
    if os.environ.get("M040_CANONICAL_RUN") != "1":
        raise CanonicalRunError(
            "M040 canonical execution is available only to a guarded preservation workflow"
        )
    if execution_kind not in _EXECUTION_KINDS:
        raise CanonicalRunError("unknown canonical execution kind")
    if execution_kind == "first-execution" and original_run_id is not None:
        raise CanonicalRunError("a first execution may not name an earlier workflow run")
    if execution_kind != "first-execution" and not original_run_id:
        raise CanonicalRunError("a reproduction must name the original workflow run")
    if not _SHA.match(head_sha) or not _SHA.match(parent_sha):
        raise CanonicalRunError(
            "canonical head and parent must be full lowercase 40-hex SHAs"
        )

    marker = _load_marker(marker_path)
    if marker["frozen_parent_sha"] != parent_sha:
        raise CanonicalRunError("canonical marker does not name the actual parent commit")

    protocol_bytes = protocol_path.read_bytes()
    protocol_sha256 = hashlib.sha256(protocol_bytes).hexdigest()
    if protocol_sha256 != marker["protocol_sha256"]:
        raise CanonicalRunError(
            "frozen protocol bytes do not match the marker commitment"
        )
    if not _DIGEST.match(protocol_sha256):
        raise CanonicalRunError("protocol digest is not canonical")

    spec = sealed_spec(
        head_sha,
        frozen_parent_sha=parent_sha,
        protocol_sha256=protocol_sha256,
    )
    protocol_commitment = f"sha256:{protocol_sha256}"

    try:
        result: dict[str, object] = _positive_result(
            spec.task_seed,
            protocol_commitment,
        )
    except (
        M039EngineError,
        M039IntegrityError,
        M039SearchAuditError,
        M040AnchorError,
        M040EngineError,
        M040PacketError,
        M040ResultVerificationError,
    ) as error:
        result = {
            "schema": RESULT_SCHEMA,
            "status": "first-canonical-scientific-result",
            "scientific_outcome": "negative",
            "trans_substrate_continuity_supported": False,
            "post_migration_plasticity_supported": False,
            "replay_supported": False,
            "combined_expected_claim_supported": False,
            "negative_reason_type": type(error).__name__,
            "negative_reason": str(error),
        }

    payload = {
        "schema": SCHEMA,
        "status": "first-canonical-result",
        "first_run_only": True,
        "reruns_are_reproductions_only": True,
        "execution_kind": execution_kind,
        "original_workflow_run": original_run_id,
        "arming_head_sha": head_sha,
        "frozen_parent_sha": parent_sha,
        "protocol_path": str(protocol_path).replace("\\", "/"),
        "protocol_sha256": protocol_sha256,
        "sealed_spec": {**spec.to_mapping(), "spec_digest": spec.digest()},
        "scientific_outcome": result["scientific_outcome"],
        "combined_expected_claim_supported": bool(
            result["combined_expected_claim_supported"]
        ),
        "result": result,
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
    parser.add_argument(
        "--execution-kind",
        choices=sorted(_EXECUTION_KINDS),
        default="first-execution",
    )
    parser.add_argument("--original-run-id")
    args = parser.parse_args()

    rendered = render_canonical_result(
        head_sha=args.head_sha,
        parent_sha=args.parent_sha,
        marker_path=args.marker,
        protocol_path=args.protocol,
        execution_kind=args.execution_kind,
        original_run_id=args.original_run_id,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(rendered)
    parsed = json.loads(rendered)
    print(f"sha256={hashlib.sha256(rendered).hexdigest()}")
    print(f"sealed_spec_digest={parsed['sealed_spec']['spec_digest']}")
    print(f"scientific_outcome={parsed['scientific_outcome']}")
    print(
        "combined_expected_claim_supported="
        f"{str(bool(parsed['combined_expected_claim_supported'])).lower()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
