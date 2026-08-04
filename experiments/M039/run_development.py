#!/usr/bin/env python3
"""Run the committed M039 development lineage and preserve its exact JSON result."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from metamorphosis.m038_journal import encode
from metamorphosis.m039_engine import (
    DEVELOPMENT_COMMITMENT,
    DEVELOPMENT_SEED,
    run_m039_development,
)
from metamorphosis.m039_provenance import journal_verified_gate2_tool_ids


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-combined", action="store_true")
    args = parser.parse_args()

    result = run_m039_development(
        DEVELOPMENT_SEED,
        protocol_commitment=DEVELOPMENT_COMMITMENT,
        require_replay=True,
    )
    records = list(result.lineage_journal_records)
    journal_verified_tools = journal_verified_gate2_tool_ids(result.manifest, records)

    payload = result.mapping()
    payload["engine_candidate_gate2_tool_ids"] = list(result.gate2_tool_ids)
    # The public field is authoritative only after independent verification from the
    # persisted journal records.  The engine's self-reported candidates remain diagnostic.
    payload["gate2_tool_ids"] = list(journal_verified_tools)
    payload["gate2_eligibility_verified_from_journal"] = True
    payload["lineage_journal_records"] = [record.hex() for record in records]
    payload["lineage_journal_records_sha256"] = hashlib.sha256(
        encode(records)
    ).hexdigest()
    payload["development_seed_consumed"] = True

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    if args.require_combined:
        required = {
            "three_cycles_accepted": result.three_cycles_accepted,
            "later_tool_reuse_supported": result.later_tool_reuse_supported,
            "tool_ablation_supported": result.tool_ablation_supported,
            "seed_to_head_replay_supported": result.seed_to_head_replay_supported,
            "journal_verified_gate2_tool": bool(journal_verified_tools),
        }
        failed = [name for name, passed in required.items() if not passed]
        if failed:
            raise SystemExit(f"M039 development expectation not met: {', '.join(failed)}")

    print(json.dumps({
        "manifest_digest": result.manifest.digest(),
        "lineage_journal_head": result.lineage_journal_head,
        "three_cycles_accepted": result.three_cycles_accepted,
        "later_tool_reuse_supported": result.later_tool_reuse_supported,
        "tool_ablation_supported": result.tool_ablation_supported,
        "seed_to_head_replay_supported": result.seed_to_head_replay_supported,
        "gate2_tool_ids": list(journal_verified_tools),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
