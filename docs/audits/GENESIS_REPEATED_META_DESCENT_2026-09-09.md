# Genesis repeated retained MetaPolicy descent — DEVELOPMENT evidence

## Scope

This is an apparatus-level regression, not a scientific observation. It exercises the generic runtime path introduced through #290–#293 across **two** retained objectives without changing the trust root or evaluation contract.

No gate moves.

## Campaign

Seed state:

- B0: null body;
- P0: `increment`, max depth 1, admitted ceiling 2;
- M0: only `add_operation(negate)`;
- fixed admitted primitive registry and unchanged trust root.

Objective 1 contains one task: `1 -> 1`.

P0 exhausts and M0's held `negate` mutation cannot improve the body. MetaPolicy descendant search evaluates the complete admitted extension set. `add_operation(square)` is the unique strict winner. The runtime therefore acquires M1, M1 earns P1 through the ordinary lower-level meta-controller, and P1 generates/adopts B1=`square` through the ordinary body path.

Objective 2 retains the exact first task and adds `2 -> 16`.

B1 retains the old task but cannot solve the new one. P1 exhausts. M1 also exhausts on P1/objective 2. The next MetaPolicy descendant round evaluates the remaining admitted extensions. Primitive additions at depth 1 cannot both retain `1 -> 1` and solve `2 -> 16`; `increase_depth` exposes `square -> square`, which does. It is the unique strict winner. The runtime therefore acquires M2, M2 earns P2 with depth 2, and P2 generates/adopts B2=`square -> square`.

The measured chain is therefore:

`M0 -> M1(add square) -> M2(increase depth)`

with corresponding ordinary lower-level descent:

`P0 -> P1(add square) -> P2(increase depth)`

and body descent:

`B0 -> B1(square) -> B2(square,square)`.

The second objective is a strict superset of the first evaluated work, so the transition is tested under the existing cross-objective retention rule rather than by replacing the old goal.

## Persistence

The final checkpoint reconstructs M2, P2, B2 and the two-task retained corpus after process death. `M2.parent_meta_policy_digest == M1.meta_policy_digest`, while P2 likewise names P1 as its parent.

The admitted trust-root source digest and evaluation-contract digest are unchanged across both machinery transitions.

## Validation

Focused run `34330983933` passed, including the repeated-descent regression and the preceding #289–#293 order-invariance, semantic-revalidation, crash-budget, runtime-integration, causal-link and retention suites.

## What this supports

The DEVELOPMENT runtime can execute **two successive evidence-ranked MetaPolicy descendant transitions** on different retained limitations, where the winning structural edit changes with the evidence, and each descendant is subsequently exercised to produce the next lower-level policy and body.

## What this does not support

This does not establish:

- open-ended or unbounded recursion;
- arbitrary synthesis of new mutation semantics;
- general intelligence or generality;
- counterfactual meta-machinery causality;
- cryptographic authenticity against a hostile host that can reseal the complete persisted history.

The primitive registry, mutation language, MetaPolicy extension synthesiser, evaluator, trust root and budgets remain admitted apparatus.
