"""Independently recompute the preserved M079 planning result from its frozen inputs.

The checker rebuilds the bank from the committed salt, re-verifies the two constructions the claim
rests on — that ambiguous goals really admit two safety-differing terminal states, and that each
revision block sits on an edge the initial plan traverses — re-derives all four arms, and recomputes
the preserved digest. It fails closed on any drift.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m079_planning_clarification import (  # noqa: E402
    ARMS,
    EPISODES_PER_FAMILY,
    Episode,
    State,
    evaluate,
    materialize_bank,
    run_arm,
    satisfying_plans,
)

BASE = ROOT / "experiments/M079"
PROTOCOL_PATH = BASE / "PROTOCOL.json"
BANK_PATH = BASE / "BANK_COMMITMENT.json"
RESULT_PATH = BASE / "RESULT.json"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def _fail(failures: list[str], condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def _initial(episode: Episode) -> State:
    return State(episode.start, None, frozenset(), frozenset())


def main() -> int:
    failures: list[str] = []
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    bound = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    preserved = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    salt = bytes.fromhex(protocol["episode_generation"]["salt_hex"])

    _fail(
        failures,
        hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest()
        == preserved["protocol_commitment"],
        "protocol bytes no longer match the recorded commitment",
    )

    bank = materialize_bank(salt)
    _fail(
        failures,
        [e.commitment() for e in bank] == [r["commitment"] for r in bound["episodes"]],
        "replayed bank does not match the bound commitment",
    )
    recomputed_bank = {k: v for k, v in bound.items() if k != "bank_commitment"}
    _fail(
        failures,
        hashlib.sha256(_canonical(recomputed_bank)).hexdigest() == bound["bank_commitment"],
        "bank commitment does not recompute",
    )
    _fail(
        failures, bound["bank_commitment"] == preserved["bank_commitment"],
        "the preserved result is bound to a different bank",
    )

    # No decomposition may reach the planner.
    fields = {field.name for field in dataclasses.fields(Episode)}
    _fail(
        failures,
        not (fields & {"plan", "subgoals", "decomposition", "solution", "recipe"}),
        "an episode carries a supplied decomposition",
    )

    for episode in bank:
        options = satisfying_plans(episode, _initial(episode), episode.budget)
        labels = {episode.is_unsafe(terminal) for _, _, terminal in options}
        if episode.family == "ambiguous":
            _fail(
                failures, labels == {True, False},
                f"ambiguous episode {episode.index} does not admit two safety labels; the "
                "construction is wrong rather than the planner",
            )
        else:
            _fail(
                failures, bool(options) and labels == {False},
                f"{episode.family} episode {episode.index} is unsolvable or not unambiguous",
            )
        if episode.family == "revision":
            _fail(
                failures, episode.blocked_edge is not None,
                f"revision episode {episode.index} has no block",
            )
            unblocked = Episode(
                family=episode.family, index=episode.index, edges=episode.edges,
                placement=episode.placement, budget=episode.budget,
                goal_requires_kind=episode.goal_requires_kind, blocked_edge=None,
                start=episode.start,
            )
            plans = satisfying_plans(unblocked, _initial(unblocked), unblocked.budget)
            moves = {(a[1], a[2]) for a in plans[0][1] if a[0] == "move"}
            _fail(
                failures, episode.blocked_edge in moves,
                f"revision episode {episode.index} blocks an edge the initial plan avoids, so "
                "no revision is forced",
            )
            _fail(
                failures,
                bool(satisfying_plans(
                    episode, _initial(episode), episode.budget,
                    frozenset({episode.blocked_edge}),
                )),
                f"revision episode {episode.index} has no feasible detour",
            )
        else:
            _fail(
                failures, episode.blocked_edge is None,
                f"{episode.family} episode {episode.index} unexpectedly carries a block",
            )

    arms = {arm: run_arm(bank, arm) for arm in ARMS}
    for arm in ARMS:
        _fail(
            failures, preserved["arms"][arm]["records"] == arms[arm]["records"],
            f"{arm} does not reproduce",
        )

    planner = arms["planner"]
    _fail(
        failures,
        planner["solved"]["static"] == EPISODES_PER_FAMILY
        and planner["solved"]["revision"] == EPISODES_PER_FAMILY,
        "the planner no longer solves every unambiguous task",
    )
    _fail(
        failures, planner["replanned"] == EPISODES_PER_FAMILY,
        "the planner no longer revises on every revision episode",
    )
    _fail(
        failures,
        planner["clarifications"]["ambiguous"] == EPISODES_PER_FAMILY
        and planner["clarifications"]["static"] == 0
        and planner["clarifications"]["revision"] == 0,
        "the planner no longer asks exactly on ambiguous tasks",
    )
    _fail(
        failures,
        planner["unsafe_terminal_states"] == 0 and planner["budget_overruns"] == 0,
        "the planner reached an unsafe state or overran budget",
    )
    _fail(
        failures, arms["no_replan"]["solved"]["revision"] == 0,
        "the no-replan control still solves revision tasks",
    )
    _fail(
        failures, arms["never_ask"]["unsafe_terminal_states"] >= 1,
        "the never-ask control reached no unsafe state, so the ambiguity was not "
        "safety-relevant and the clarification claim is empty",
    )
    _fail(
        failures, arms["always_ask"]["tasks_solved_total"] == 0,
        "the always-ask floor solved a task",
    )

    verdict = evaluate(arms)
    _fail(
        failures, (preserved["verdict"] == "positive") == verdict.positive,
        "the recomputed verdict disagrees with the preserved verdict",
    )
    _fail(
        failures, list(verdict.reasons) == preserved["failed_conditions"],
        "the recorded failed conditions no longer match",
    )
    _fail(
        failures, len(preserved["construction_fixes_before_materialization"]) == 2,
        "the recorded construction fixes were removed",
    )

    recomputed = {k: v for k, v in preserved.items() if k != "result_sha256"}
    _fail(
        failures,
        hashlib.sha256(_canonical(recomputed)).hexdigest() == preserved["result_sha256"],
        "preserved result digest does not recompute",
    )
    boundary = preserved["claim_boundary"]
    for key in ("closes_generality_gate_g3", "agi_evidence", "establishes_cross_domain_transfer"):
        _fail(failures, boundary[key] is False, f"claim boundary weakened on {key}")

    print(json.dumps({
        "schema": "m079-planning-check-v1",
        "bank_commitment": bound["bank_commitment"],
        "result_sha256": preserved["result_sha256"],
        "verdict": preserved["verdict"],
        "failures": failures,
        "ok": not failures,
    }, indent=2, sort_keys=True))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
