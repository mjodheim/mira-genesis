"""Execute the first M038 canonical run after a valid arming commit.

The script refuses ordinary execution. It requires the workflow-only environment
flag, a valid marker bound to the exact parent, the frozen protocol digest and the
immutable arming head. A negative scientific result is written and exits normally;
only integrity failures abort the workflow.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re

from metamorphosis.m038_sealed import sealed_spec
from metamorphosis.m038_two_speed import run_m038_development_cycle

SCHEMA = "m038-canonical-result/1"
_ARM_SCHEMA = "m038-canonical-arm/1"
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


def render_canonical_result(
    *,
    head_sha: str,
    parent_sha: str,
    marker_path: Path,
    protocol_path: Path,
) -> bytes:
    if os.environ.get("M038_CANONICAL_RUN") != "1":
        raise CanonicalRunError("M038 canonical execution is available only to the guarded workflow")
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
    comparison = run_m038_development_cycle(
        spec.task_seed,
        protocol_commitment=f"sha256:{protocol_sha256}",
    )
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
        "result": comparison.summary(),
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
