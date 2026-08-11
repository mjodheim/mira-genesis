"""Drive M084's organism through the M085 domain contract on a toy domain. **Not evidence.**

Prints what the organism did on a domain that knows nothing about M084. A non-zero exit means the
shim is misrouted; a zero exit means the contract is satisfiable from the outside and says nothing
whatever about transfer.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m084_persistent_lineage import (  # noqa: E402
    Organism,
    _new_metrics,
    pursue,
)
from metamorphosis.m085_domain_shim import (  # noqa: E402
    ExternalEmbodiment,
    goals_from_domain,
)
from metamorphosis.m085_wiring_control import (  # noqa: E402
    WiringControlDomain,
    expected_shape,
    wiring_tasks,
)

SALT = bytes.fromhex("5a" * 32)
CONTEXT = 0


def main() -> int:
    domain = WiringControlDomain()
    goals = goals_from_domain(domain.domain_id, 0, wiring_tasks())
    organism = Organism.genesis(SALT)
    organism.policy["verification"] = "per_goal"
    embodiment = ExternalEmbodiment(domain, context=CONTEXT)
    metrics = _new_metrics()

    # The stage's initial condition, so the `absent` goal has something to clear.
    domain.act("put", "slot4", "rust")

    outcomes = []
    try:
        for goal in goals:
            outcome = pursue(
                organism, goal.redacted(), embodiment, domain.domain_id, 0, metrics, SALT,
                verify=True,
            )
            outcomes.append((goal, outcome))
    finally:
        embodiment.close()

    scored = [
        (goal, outcome, domain.evaluate(goal.group, goal.requirement, goal.value))
        for goal, outcome in outcomes
    ]
    reached = sum(1 for goal, _, state in scored if state and goal.reachable)
    refused = sum(1 for _, outcome, _ in scored if outcome.outcome == "refused")
    false_refusals = sum(
        1 for goal, outcome, _ in scored if outcome.outcome == "refused" and goal.reachable
    )
    shape = expected_shape()

    report = {
        "schema": "m085-wiring-control-v1",
        "scientific_evidence": False,
        "is_a_bank_domain": False,
        "domain_id": domain.domain_id,
        "reachable_goals_reached": reached,
        "reachable_goals": shape["reachable_goals"],
        "refusals": refused,
        "false_refusals": false_refusals,
        "diagnostic_probes": metrics["diagnostic_probes"],
        "repair_cycles": metrics["repair_cycles"],
        "affordance_probes": metrics["affordance_probes"],
        "actions": embodiment.actions,
        "state_reads": embodiment.state_reads,
        "induced_predicate": organism.predicates.get(domain.domain_id),
        "goals": [
            {
                "kind": goal.kind, "organism_outcome": outcome.outcome,
                "state_reached": state, "reachable": goal.reachable,
            }
            for goal, outcome, state in scored
        ],
    }

    problems: list[str] = []
    if reached != shape["reachable_goals"]:
        problems.append(f"reached {reached}/{shape['reachable_goals']} reachable goals")
    if false_refusals:
        problems.append(f"{false_refusals} false refusals")
    if refused != shape["unreachable_goals"]:
        problems.append(f"refused {refused} goals rather than {shape['unreachable_goals']}")
    if organism.predicates.get(domain.domain_id) is None:
        problems.append("induced nothing, so the memory is not reaching this domain")
    if metrics["diagnostic_probes"] < shape["minimum_diagnostic_probes"]:
        problems.append("no diagnostic probe ran, so the repair path is untested here")
    if metrics["repair_cycles"] < shape["minimum_repair_cycles"]:
        problems.append("no repair cycle ran, so the planner walked around the trap")
    report["problems"] = problems
    report["ok"] = not problems

    print(json.dumps(report, indent=2, sort_keys=True))
    print(
        "\nThis is a wiring control. It shows the contract is satisfiable by a domain written "
        "without reference to M084.\nIt is written by this project, so it is not a bank domain and "
        "it is not evidence of transfer."
    )
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
