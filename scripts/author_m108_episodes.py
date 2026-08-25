"""Author the M108 fixtures: the attribution episodes, and separately the later demand B.

Two files, never one. The producer stage is allowed to see the episodes and must never see B; the
later stage is allowed to see B and must never see the episodes. Writing them into a single fixture
would make that boundary unenforceable, and M106 already showed that an unenforced boundary is an
unfalsifiable one.

M0's operator table is not written by hand here. It is derived by replaying M107's own frozen
acquisition, so the claim that M108 begins where M107 ended is a computed fact rather than a
narrated one. M107's fixture is read at authoring time and recorded by digest; it is deliberately
NOT bound by M108's protocol, because a file an earlier frozen protocol binds must keep exactly the
bytes that protocol froze.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m107_runtime as m107  # noqa: E402
from metamorphosis import m108_runtime as runtime  # noqa: E402

EXPERIMENT = ROOT / "experiments" / "M108"
EPISODES_PATH = EXPERIMENT / "EPISODES.json"
DEMAND_PATH = EXPERIMENT / "DEMAND.json"
M107_DEMANDS = ROOT / "experiments" / "M107" / "DEMANDS.json"


def _table(function) -> list[bool]:
    return [bool(function(*row)) for row in runtime.world_rows()]


# The later capability. Non-monotone AND genuinely dependent on the signal the base interface
# cannot read, so neither generation alone can reach it.
def _later_capability(x: bool, y: bool, z: bool) -> bool:
    return z and not (x or y)


# Past failures resolved on the operator axis: readable, but outside a monotone image.
OPERATOR_AXIS_PAST = (
    ("op-negation", lambda x, y, z: not x),
    ("op-parity", lambda x, y, z: x != y),
    ("op-nand", lambda x, y, z: not (x and y)),
)

# Past failures resolved on the signal axis, recorded from both phases of the lineage so the
# feature record covers every row attribution can be asked about.
SIGNAL_AXIS_PAST_MONOTONE = (
    ("sig-mono-direct", lambda x, y, z: z),
    ("sig-mono-conjunction", lambda x, y, z: z and y),
)
SIGNAL_AXIS_PAST_EXTENDED = (
    ("sig-ext-direct", lambda x, y, z: z),
    ("sig-ext-disjunction", lambda x, y, z: z or x),
)


def m107_acquired_operators() -> tuple[list[dict], str]:
    """Replay M107's frozen acquisition to obtain the operator table M108 actually starts from."""
    raw = M107_DEMANDS.read_bytes()
    demands = json.loads(raw.decode("ascii"))
    acquired = m107.acquire_operator(
        m107.create_state(),
        [demands["joint"]["first"], demands["joint"]["second"]],
        register_result=True,
    )
    if not acquired.get("confirmed"):
        raise RuntimeError("M107 acquisition did not reproduce; M108 has no predecessor to stand on")
    return m107.decode_state(acquired["next_state"])["operators"], m107.sha256_bytes(raw)


def build_episodes() -> dict:
    base = m107.initial_operators()
    extended, predecessor_digest = m107_acquired_operators()
    episodes = []
    for episode_id, function in OPERATOR_AXIS_PAST:
        episodes.append(
            runtime.attribution_episode(
                episode_id,
                operators=base,
                signal_width=runtime.BASE_SIGNAL_WIDTH,
                target=_table(function),
                blamed_component=runtime.COMPONENT_OPERATORS,
            )
        )
    for episode_id, function in SIGNAL_AXIS_PAST_MONOTONE:
        episodes.append(
            runtime.attribution_episode(
                episode_id,
                operators=base,
                signal_width=runtime.BASE_SIGNAL_WIDTH,
                target=_table(function),
                blamed_component=runtime.COMPONENT_SIGNALS,
            )
        )
    for episode_id, function in SIGNAL_AXIS_PAST_EXTENDED:
        episodes.append(
            runtime.attribution_episode(
                episode_id,
                operators=extended,
                signal_width=runtime.BASE_SIGNAL_WIDTH,
                target=_table(function),
                blamed_component=runtime.COMPONENT_SIGNALS,
            )
        )
    payload = {
        "schema": "m108-episodes-v1",
        "episodes": episodes,
        # The subset that leaves a domain row uncovered. The lineage must refuse on it.
        "underdetermined_subset": [
            item["episode_id"]
            for item in episodes
            if item["episode_id"].startswith("op-") or item["episode_id"].startswith("sig-ext-")
        ],
        "m0_operators": extended,
        "predecessor": {
            "milestone": "M107",
            "fixture": "experiments/M107/DEMANDS.json",
            "fixture_sha256": predecessor_digest,
            "bound_by_this_protocol": False,
        },
    }
    payload["episodes_digest"] = runtime.digest(payload)
    return payload


def build_demand() -> dict:
    payload = {
        "schema": "m108-later-demand-v1",
        "demand": runtime.capability_demand("B", _table(_later_capability)),
    }
    payload["demand_fixture_digest"] = runtime.digest(payload)
    return payload


def main() -> int:
    EXPERIMENT.mkdir(parents=True, exist_ok=True)
    for path, payload in ((EPISODES_PATH, build_episodes()), (DEMAND_PATH, build_demand())):
        path.write_bytes(runtime.canonical_json(payload).encode("ascii"))
        print("%s %s" % (path.name, runtime.sha256_bytes(path.read_bytes())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
