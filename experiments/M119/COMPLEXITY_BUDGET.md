# M119 / H64 — complexity budget

Written before implementation. M118 ended because its measurement was too complicated to trust as a
one-shot instrument, so this milestone fixes its size **first** and treats growth as something that
must be justified rather than assumed.

| element | budget | rationale |
|---|---|---|
| Principal arms | **4** | the 2×2 needed to separate cascade from policy. Nothing else. |
| Primary endpoint | **1** | paired per-demand scientific correctness |
| Primary statistical comparison | **1** | FULL vs FRESH |
| Mandatory no-harm guards | **≤ 3** | invented adapters, false refusals, attribution when examined |
| Verdict states | **4** | instrument-aborted, inconclusive, negative, positive |
| Inherited P1–P22 | **none** | not carried; the historical predicates stay historical |
| Budget ablation arms | **0 unless justified** | added only if a pre-mortem names a concrete ambiguity |
| Validity predicates | minimal, and **separate from the scientific arms** | apparatus validity is not a scientific outcome |

**Default action on any proposed addition is removal.** If the design grows materially beyond this,
stop and justify each added element as strictly necessary to distinguish a live causal explanation.

## What is deliberately not here

- No `budget_plus` or `probe_only_budget_plus`. All four arms run at one fixed budget. A budget arm
  is added only if review shows the primary question cannot otherwise be answered.
- No `rollback`, `ablated`, `mutated`, `unregistered` arms. They are historical, not required to
  distinguish cascade from policy.
- No four-way disjunctive success rule, and no metric that can independently create a positive.
- No producer-death or preservation arms among the scientific treatments. Those are apparatus
  validity checks and are reported separately; a failure there makes the instrument invalid, not
  the hypothesis false.
