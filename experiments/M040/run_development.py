from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Mapping, Sequence

from metamorphosis.m040_engine import (
    DEVELOPMENT_COMMITMENT,
    DEVELOPMENT_SEED,
    run_m040_development,
)


def _json_value(value: object) -> object:
    if isinstance(value, bytes):
        return {"encoding": "hex", "value": value.hex()}
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_value(item) for item in value]
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=DEVELOPMENT_SEED)
    parser.add_argument("--protocol-commitment", default=DEVELOPMENT_COMMITMENT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = run_m040_development(
        master_seed=args.seed,
        protocol_commitment=args.protocol_commitment,
        require_replay=True,
    )
    payload = _json_value(result.mapping(include_records=True))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "trans_substrate_continuity_supported": result.trans_substrate_continuity_supported,
        "post_migration_plasticity_supported": result.post_migration_plasticity_supported,
        "replay_supported": result.replay_supported,
        "result_digest": result.digest(),
        "packet_sha256": result.packet_sha256,
        "journal_head": result.journal_head,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
