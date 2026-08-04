"""Run the committed M038 development cycle.

Development only. Seed 380038 and every derived artefact become consumed for
implementation debugging. This runner never opens a sealed block and never
produces a canonical M038 result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from metamorphosis.m038_two_speed import run_m038_development_cycle

DEVELOPMENT_SEED = 380_038
SCHEMA = "m038-development-cycle/1"


def render_result(seed: int = DEVELOPMENT_SEED) -> bytes:
    comparison = run_m038_development_cycle(seed)
    payload = {
        "schema": SCHEMA,
        "status": "consumed-development-result",
        "seed": seed,
        "no_sealed_block_opened": True,
        "no_m038_outcome_claim": True,
        "result": comparison.summary(),
    }
    return (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-combined", action="store_true")
    args = parser.parse_args()

    rendered = render_result()
    parsed = json.loads(rendered)
    combined = bool(parsed["result"]["combined_expected_claim_supported"])

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(rendered)
    else:
        print(rendered.decode("utf-8"), end="")

    print(f"sha256={hashlib.sha256(rendered).hexdigest()}")
    print(f"combined_expected_claim_supported={str(combined).lower()}")

    if args.require_combined and not combined:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
