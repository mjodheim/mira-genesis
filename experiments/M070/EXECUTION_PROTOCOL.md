# M070 external execution protocol

**FROZEN BEFORE EITHER SELECTED TASK IS EXECUTED.**

## Falsifiable claim

The task-agnostic Mira design frozen at `41ebe791605f55e7a44df8f0939d730139cf219a`
must earn an official external reward of at least `1.0` on at least one of the two blindly selected
Terminal-Bench 2 tasks. Both trials must be valid and externally scored. A refusal, step-budget
exhaustion or valid reward below `1.0` is negative evidence, not an infrastructure excuse.

This is a narrow engineering threshold. Passing it would not establish AGI, broad generality,
autonomous self-improvement or safe deployment.

## Immutable execution

- Harness: Harbor v0.20.0, peeled source commit
  `459ff6ec99417589b7f679d14ddf3b3f0ae4f1dc`.
- Bridge: commit `06c23402e443dec699d7caf11595baebd1ae8409`.
- Model interface: official Codex CLI 0.147.0 with explicit model `gpt-5.6-sol`.
- Exactly one Mira attempt and one `nop` floor-control attempt per selected task.
- Fixed task order: `rstan-to-pystan`, then `llm-inference-batching-scheduler`.
- One trial at a time; no valid scientific retry and no task replacement.
- At most 16 decisions; 120 seconds per container command; 180 seconds per model decision;
  Harbor's 1,800-second global agent timeout remains authoritative.
- Each task image is replaced only by the digest resolved from its original tag.
- `[agent].network_mode = "no-network"` is the only behavioral task-package override.

Harbor applies the agent phase override around `agent.run()`. The adapter performs no setup action
and rechecks the realized Harbor policy before the first model call. The original environment
baseline and verifier policy remain unchanged.

## Evidence boundary

The public instructions were opened only after the blind pair was committed. Reference solutions
and evaluator tests are not to be opened by the project operator and never enter model context.
Harbor alone mounts evaluator material after the agent phase and decides success. A `nop` reward
other than zero is a confound and blocks a positive conclusion.

An infrastructure retry is allowed only if the failure occurs before any model decision and before
any verifier reward. It must use identical frozen inputs and be recorded. Once a valid Mira attempt
has begun, its outcome is preserved.
