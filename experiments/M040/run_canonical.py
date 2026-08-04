from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence

from metamorphosis.m040_engine import M040EngineError, run_m040_development

SEED_DOMAIN = b"m040-canonical-seed-v1"


def _json_value(value: object) -> object:
    if isinstance(value, bytes):
        return {"encoding": "hex", "value": value.hex()}
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_value(item) for item in value]
    return value


def _seed(protocol_sha256: str, arming_head_sha: str) -> int:
    raw = hashlib.sha256(
        SEED_DOMAIN
        + bytes.fromhex(protocol_sha256)
        + bytes.fromhex(arming_head_sha)
    ).digest()
    return int.from_bytes(raw[:8], "big", signed=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--parent-sha", required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--marker", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    protocol_bytes = args.protocol.read_bytes()
    protocol_sha256 = hashlib.sha256(protocol_bytes).hexdigest()
    marker = json.loads(args.marker.read_text(encoding="utf-8"))
    if marker != {"schema": "m040-canonical-armed/1"}:
        raise SystemExit("invalid canonical marker")
    if len(args.head_sha) != 40 or len(args.parent_sha) != 40:
        raise SystemExit("invalid immutable commit identity")

    master_seed = _seed(protocol_sha256, args.head_sha)
    envelope: dict[str, object] = {
        "schema": "m040-canonical-result/1",
        "status": "first-canonical-result",
        "first_run_only": True,
        "reruns_are_reproductions_only": True,
        "arming_head_sha": args.head_sha,
        "frozen_parent_sha": args.parent_sha,
        "protocol_path": str(args.protocol),
        "protocol_sha256": protocol_sha256,
        "sealed_master_seed": master_seed,
        "task_family": "lineage_anchor",
    }

    try:
        result = run_m040_development(
            master_seed=master_seed,
            protocol_commitment=protocol_sha256,
            require_replay=True,
            task_family="lineage_anchor",
        )
    except M040EngineError as exc:
        envelope.update(
            {
                "execution_completed": True,
                "scientific_outcome": "negative",
                "trans_substrate_continuity_supported": False,
                "post_migration_plasticity_supported": False,
                "engine_falsifier": type(exc).__name__,
                "engine_error": str(exc),
            }
        )
    else:
        result_payload = _json_value(result.mapping(include_records=True))
        positive = bool(
            result.trans_substrate_continuity_supported
            and result.post_migration_plasticity_supported
            and result.replay_supported
        )
        envelope.update(
            {
                "execution_completed": True,
                "scientific_outcome": "positive" if positive else "negative",
                "trans_substrate_continuity_supported": result.trans_substrate_continuity_supported,
                "post_migration_plasticity_supported": result.post_migration_plasticity_supported,
                "seed_only_replay_supported": result.replay_supported,
                "result_digest": result.digest(),
                "result": result_payload,
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(envelope, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "scientific_outcome": envelope["scientific_outcome"],
        "protocol_sha256": protocol_sha256,
        "sealed_master_seed": master_seed,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
