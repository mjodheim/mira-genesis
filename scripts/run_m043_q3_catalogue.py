from __future__ import annotations

import argparse
import json
from pathlib import Path

from metamorphosis.m043_tasks import run_q3_development_catalogue


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the deterministic, unselected M043 Q3 development catalogue."
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = run_q3_development_catalogue()
    payload = {
        **result.to_dict(),
        "entries": [entry.evaluator_mapping() for entry in result.entries],
        "target_tables_exported": False,
        "witness_traces_exported": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": result.status.value,
                "entry_count": len(result.entries),
                "entry_digests": [entry.digest() for entry in result.entries],
                "explicit_negative_termination": payload[
                    "explicit_negative_termination"
                ],
            },
            sort_keys=True,
        )
    )
    return 0 if result.status.value == "qualified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
