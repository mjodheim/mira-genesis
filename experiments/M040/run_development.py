from __future__ import annotations

import argparse
import json
from pathlib import Path

from metamorphosis.m040_engine import (
    DEVELOPMENT_COMMITMENT,
    DEVELOPMENT_SEED,
    run_m040_development,
)


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
    payload = result.mapping(include_records=True)
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
