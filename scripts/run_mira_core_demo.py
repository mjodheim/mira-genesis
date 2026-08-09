"""Run a dependency-free demonstration of the reusable governed Mira agent loop."""
from __future__ import annotations

import json

from mira_core import Action, Authority, Goal, MiraAgent, Observation


class DemoBody:
    body_id = "demo-counter-body"

    def __init__(self) -> None:
        self.value = 0

    def reset(self, goal: Goal) -> Observation:
        self.value = 0
        return Observation("demo-0", {"value": self.value})

    def act(self, action: Action) -> Observation:
        if action.kind != "increment":
            return Observation("demo-invalid", {"value": self.value}, True, False, "invalid action")
        self.value += int(action.payload["amount"])
        complete = self.value >= 3
        return Observation(f"demo-{self.value}", {"value": self.value}, complete, complete)


class DemoPolicy:
    policy_id = "demo-increment-policy"

    def propose(self, goal, observation, history):
        return Action(
            f"increment-{len(history)}", "increment", {"amount": 1},
            (Authority.COMPUTE.value,),
        )


def run_demo() -> dict[str, object]:
    agent = MiraAgent(DemoPolicy(), DemoBody(), max_steps=4)
    result = agent.run(Goal("demo-reach-three", "reach a counter value of three"))
    checkpoint = agent.memory.checkpoint()
    return {
        "schema": "mira-core-demo-v1",
        "status": result.status,
        "succeeded": result.succeeded,
        "steps": result.steps,
        "final_state": dict(result.final_observation.state),
        "memory_events": len(agent.memory.events),
        "memory_digest": result.memory_digest,
        "checkpoint_bytes": len(checkpoint),
        "external_authority_granted": False,
    }


def main() -> int:
    result = run_demo()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["succeeded"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
