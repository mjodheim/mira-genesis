"""Author the M109 curriculum: two staged demands, in two files that must never share a capsule.

The second demand is revealed only once the first is resolved. Writing both into one fixture would
make that boundary a convention rather than something the instrument can enforce, and M106 already
showed that an unenforced boundary is an unfalsifiable one.

M108 also authored the attribution episodes and their blame labels. M109 authors neither: the lineage
records its own episodes and determines each label by running a controlled trial on itself. What is
authored here is only the world's curriculum.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m109_runtime as runtime  # noqa: E402

EXPERIMENT = ROOT / "experiments" / "M109"
STAGE1_PATH = EXPERIMENT / "DEMAND_STAGE1.json"
STAGE2_PATH = EXPERIMENT / "DEMAND_STAGE2.json"


def _table(function) -> list[bool]:
    return [bool(function(*row)) for row in runtime.world_rows()]


# Stage one. Monotone, and it depends on the signal the interface cannot read: extending the operator
# table cannot reach it and widening the candidate space cannot reach it. Only the interface can.
def _stage_one(x: bool, y: bool, z: bool) -> bool:
    return x and y and z


# Stage two. Non-monotone. By the time it is revealed the interface is already at the world width and
# the monotone candidate space is closed by the lemma. Only widening the candidate space can reach it.
def _stage_two(x: bool, y: bool, z: bool) -> bool:
    return (not x) and y


def build_stage(stage: int, function) -> dict:
    payload = {
        "schema": "m109-staged-demand-v1",
        "stage": int(stage),
        "revealed_after_stage": int(stage) - 1,
        "demand": runtime.capability_demand("D%d" % stage, _table(function)),
    }
    payload["stage_digest"] = runtime.digest(payload)
    return payload


def build_stage_one() -> dict:
    return build_stage(1, _stage_one)


def build_stage_two() -> dict:
    return build_stage(2, _stage_two)


def main() -> int:
    EXPERIMENT.mkdir(parents=True, exist_ok=True)
    for path, payload in ((STAGE1_PATH, build_stage_one()), (STAGE2_PATH, build_stage_two())):
        path.write_bytes(runtime.canonical_json(payload).encode("ascii"))
        target = runtime.demand_target(payload["demand"])
        print(
            "%-22s %s  target %s"
            % (
                path.name,
                runtime.sha256_bytes(path.read_bytes()),
                "".join("1" if bit else "0" for bit in target),
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
