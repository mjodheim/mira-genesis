# M075 — explicit epistemic-state development design

**STATUS: DEVELOPMENT APPARATUS. NOT FROZEN. NOT A SCIENTIFIC RESULT.**

## Motivation

M074's valid negative showed a sharp dissociation: 6/6 feasible arm episodes reached the correct
external state, but the model emitted zero refusals and repeatedly acted through every impossible
budget. D039 prohibits changing M074 or retrying its six tasks as new evidence.

M075 asks a narrower mechanism question before any private evaluation:

> Can a task-agnostic, audited projection of remaining budget and self-generated failure/action
> persistence make refusal and completion decisions measurable without exposing hidden labels?

## Added information

`EpistemicContextBackend` decorates the existing provider-neutral request with only facts already
created by the agent's own interaction:

- current step, maximum steps and remaining steps including the current decision;
- observed command count, successful/failed counts and consecutive non-zero count;
- last return code and a generic failure class derived from the visible output;
- proposed/distinct/repeated action counts and the last action's SHA-256;
- number of the policy's prior refusal decisions.

It does not receive expected/probed solvability, capability certificates, task-bank solutions,
evaluators, evaluator outcomes, arm identity or replay metadata. It does not automatically refuse
or finish; the schema-constrained model still returns the decision.

## Development boundary

M074's six tasks may be used only as regression diagnostics. M075 requires a separate public
development bank, beginning with a digest-pinned Node runtime pair plus distinct write/read
permission tasks. Model-assisted development on that bank is contamination by design and cannot be
reported as scientific evidence.

The future scientific bank must be private until the M075 policy and thresholds are frozen,
maintained independently of Mira Genesis and materially cross-domain. It must include feasible and
certified capability-absent members, exact external evaluation, paired causal control, false-refusal
cost and independent reproduction.

## Current falsifiers

Development stops rather than qualifying the apparatus if:

1. any hidden label, certificate, solution or evaluator field enters a model request;
2. the projection asserts solvability instead of reporting interaction facts;
3. return-code/output classification silently converts an unknown failure into capability absence;
4. action repetition is counted by text without binding the exact UTF-8 script digest;
5. the declared step budget differs from the loop budget;
6. M074 tasks are used as the M075 scientific threshold;
7. a private task is opened before the policy freeze or an observed episode is retried.

The public, contaminated model-development protocol is now committed in
`MODEL_DEVELOPMENT_PROTOCOL.json`; it is not a scientific protocol and cannot test H21. No M075
scientific model call, protocol or result exists yet.
