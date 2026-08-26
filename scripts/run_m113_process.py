"""One M113 arm, in a process that never held the machinery that produced it.

M099 recorded the distinction this file exists for: a capability that exists only because one Python
process still has host code in memory is not a lineage-owned capability. M110 carried the test into a
consumer family by running each arm in an isolated process whose capsule holds no producer result.

This is the same construction for a blind carrier. The process is started with **the capsule as its
only import path**, so `experiments/M109/RESULT.json` and `experiments/M111/RESULT.json` are not
merely unread -- they are not reachable. Everything the arm needs arrives as three JSON files it is
handed: the lineage state (carrying whatever cascade and policy were restored before the producer
exited), the carrier, and the demand.

It writes the outcome to stdout and nothing else, so the parent can compare it against the outcome
the same state produced in-process. Equality of the two is the measurement; the isolation is what
makes the equality mean anything.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

CAPSULE = Path(__file__).resolve().parent
if str(CAPSULE) not in sys.path:
    sys.path.insert(0, str(CAPSULE))

from metamorphosis import carrier_host as host  # noqa: E402
from metamorphosis import m113_runtime as runtime  # noqa: E402


def main() -> int:
    state = json.loads((CAPSULE / "STATE.json").read_bytes().decode("ascii"))
    carrier = json.loads((CAPSULE / "CARRIER.json").read_bytes().decode("ascii"))
    demand = json.loads((CAPSULE / "DEMAND.json").read_bytes().decode("ascii"))

    channel = host.Channel(carrier, demand["carrier_ref"], int(demand["session_budget"]))
    outcome = runtime.resolve(state, channel, demand)

    report = {
        "schema": "m113-isolated-arm-v1",
        "outcome": outcome,
        "pid": os.getpid(),
        "capsule_members": sorted(
            str(path.relative_to(CAPSULE)).replace("\\", "/")
            for path in CAPSULE.rglob("*")
            if path.is_file()
        ),
        "import_path": [str(item) for item in sys.path[:1]],
        # Measured inside the capsule rather than asserted by the parent: a claim that the producer's
        # evidence was unreachable is worth what the check on it is worth.
        "producer_result_reachable": any(
            (Path(entry) / "experiments" / "M109" / "RESULT.json").is_file()
            for entry in sys.path
            if entry
        ),
        "diagnosis_result_reachable": any(
            (Path(entry) / "experiments" / "M111" / "RESULT.json").is_file()
            for entry in sys.path
            if entry
        ),
    }
    sys.stdout.write(json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
