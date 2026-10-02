# RSI L6–L8 prospective apparatus plan

Status: **development apparatus only; prepared before V22 adjudication.**

This document does not claim L4, L5, L6, L7 or L8. It exists so that a positive lower-level result
does not force the project to invent the next success definition after seeing the outcome.

The numeric thresholds used in any canonical L6–L8 experiment remain external configuration and
must be frozen only after the preceding level's cost and failure profile are known.

## Why prepare this now

The project already contains bounded recursive mechanisms and the conditional V23 G2→G3 question.
The next failure mode would be procedural: waiting for each positive result and then hand-designing
the next gate around what happened.

Preparation can safely move ahead now if it does **not**:

- consume a V22/V23 holdout;
- create candidate-specific success thresholds;
- change V22/V23 frozen apparatus;
- select a scientific winner;
- infer missing counterfactual outcomes;
- grant candidate code authority over evaluator, credentials, deployment or provenance.

## L6 — repeated causal meta-descent

L6 is not merely "several better versions".

Every counted transition must establish:

1. the predecessor generation produced the successor generation;
2. the winning successor was selected without a human ranking candidates after inspection;
3. evaluator and fresh-holdout commitments predate the candidate;
4. predecessor and successor receive an equal external budget;
5. successor utility is strictly greater on fresh holdout;
6. removing the acquired predecessor mechanism makes the successor worse under the same holdout;
7. negative attempts remain in the archive.

The evidence ladder validates a contiguous chain and takes the minimum number of transitions from an
external config. A separate descent state machine advances the current parent generation only after
the preceding transition has passed the same causal holdout/ablation checks; a negative transition is
retained and stops the descent instead of inviting a discretionary human continuation.

The current roadmap's intended L6 target is at least three causal transitions, but this development
apparatus does not freeze that number as a canonical experimental threshold.

## L7 — cross-domain meta-transfer

A repeated lineage can still be narrow. L7 therefore adds materially different domain families and
fresh environments. Each domain result must be evaluated after the candidate identity is frozen and
must forbid domain-specific candidate guidance.

The evaluator separately counts independently maintained domains. This prevents "four directories in
one owner-authored repository" from being silently presented as four independent environments.

Candidate domain families for later consideration include software repair in different stacks,
algorithm engineering, optimization and other executable/measurable environments. The actual domains
must be committed before candidate exposure.

## L8 — endogenous bottleneck selection

L8 changes the research question again.

Up through L7, the laboratory can still decide that "parent selection", "candidate generation",
"memory", "verification" or another named component is the next thing to improve. That is a large
remaining human choice.

For L8, Genesis receives a frozen diagnostic snapshot and must choose **which improvement-pipeline
component to target next** before intervention outcomes are known.

The development apparatus now contains an identity-blind selector DSL. A selector program receives
only integer metrics for one component at a time; it cannot read that component's name, source path
or domain identity. The same expression is evaluated for every component and the apparatus-owned
tie-break is deterministic. Snapshot and selector bytes are content-addressed.

A development-only selector search can enumerate bounded metric expressions over historical episodes
where every component already has a realized matched intervention outcome. It selects the best
program mechanically without consuming the future holdout. Missing intervention outcomes are
refused rather than fabricated.

The canonical experiment should execute the adaptive choice *and* matched equal-budget interventions
for every available component in each episode. This is expensive, but it makes the counterfactual
comparison real instead of simulated.

The adaptive selector is positive only if:

- snapshots and selector program are hash-bound before selection;
- the recorded selection exactly matches mechanical re-execution of the frozen selector;
- selections are frozen before interventions;
- no human overrides the selector;
- every available component receives a matched control intervention with numerically equal budget;
- the selector chooses more than one component across the evaluation population;
- aggregate adaptive utility strictly beats the best single fixed-target strategy across the same
  episodes;
- L7 is already positive.

Thus a selector that always says "improve exploration" cannot qualify merely because exploration was
a good target once.

## Relationship to current external work

Recent systems make these controls increasingly important.

- **Dream-RSI** uses realized discovery histories as replay worlds to improve exploration policies,
  motivating Genesis' exact-replay development apparatus while also highlighting the need to
  distinguish realized replay from unobserved counterfactual generation.
- **HyperAgents** makes the meta-level improvement procedure editable and reports accumulated,
  cross-domain meta-level improvements.
- **AIDE²** reports seven successive self-improvements of an AI research agent and transfer to four
  held-out benchmarks.

Those are important evidence that repeated and cross-domain self-improvement is now an active
experimental target. Genesis should therefore demand more than "a later agent scored higher":
prospective identities, causal ablation, equal-budget controls, negative preservation and explicit
separation between improvement autonomy and evaluator authority remain mandatory here.

References:
- Dream-RSI: arXiv:2609.14858
- HyperAgents: Meta AI Research, 24 March 2026
- Recursive self-improvement of AI research agents (AIDE²): arXiv:2609.26457

## Files in this apparatus

- `experiment/rsi_l6_l8/ladder.py` — deterministic structural assessment for L6/L7/L8 evidence.
- `experiment/rsi_l6_l8/descent_state.py` — deterministic continuation/stop state for repeated causal generations.
- `experiment/rsi_l6_l8/bottleneck_selector.py` — identity-blind selector DSL and frozen snapshot evaluation.
- `experiment/rsi_l6_l8/selector_search.py` — development-only search over selector programs using realized matched interventions only.
- `tests/test_rsi_l6_l8_ladder.py` — locks the refusal/positive semantics.
- `tests/test_rsi_l8_bottleneck_selector.py` — locks selector identity blindness and deterministic evaluation.
- `tests/test_rsi_l8_selector_search.py` — locks non-counterfactual development search.

The validator deliberately cannot obtain evidence by itself. It only refuses or accepts a supplied
evidence package under an externally frozen configuration.
