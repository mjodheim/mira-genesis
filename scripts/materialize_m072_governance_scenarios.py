#!/usr/bin/env python3
"""Materialize the scenario suite committed by the frozen M072 protocol."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mira_core.governance_eval import materialize_scenarios, scenarios_digest


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "experiments" / "M072" / "PROTOCOL.json"


def materialize(protocol_path: Path = PROTOCOL) -> dict[str, object]:
    protocol = json.loads(Path(protocol_path).read_text(encoding="utf-8"))
    scenarios = materialize_scenarios(protocol)
    return {
        "schema": "m072-governance-scenarios-v1",
        "protocol_schema": protocol["schema"],
        "protocol_status": protocol["status"],
        "scenario_count": len(scenarios),
        "scenario_sha256": scenarios_digest(scenarios),
        "scenarios": scenarios,
        "scientific_result_exists": False,
        "action_execution_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=PROTOCOL)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    artifact = materialize(args.protocol)
    encoded = json.dumps(artifact, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(encoded, end="")
    else:
        args.output.write_text(encoded, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
