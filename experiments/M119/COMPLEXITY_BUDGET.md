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

## Amendment, before the freeze: one diagnostic arm added

The rule above admits a budget arm "only if a pre-mortem names a concrete ambiguity". Pre-freeze
review named one, with measured numbers from a DEVELOPMENT dry run over devkit carriers: on
unreachable demands the policy-holding arms returned `undetermined` **17 times in 25**, against
**2 in 25** for the comparator. The policy gates a diagnostic probe, the probe consumes
observations, and an exploration that does not close yields `undetermined` — so an arm that probes
could be losing to the *cost* of probing under a fixed budget rather than to the *competence* of
what it acquired. The 2×2 cannot separate those, and a negative that cannot tell them apart is the
M118 failure repeating.

`FULL_BUDGET_PLUS` is therefore added, and fenced:

- it is **not** in `ARM_NAMES`, so it cannot enter the primary comparison;
- it is never the descendant or the comparator, and no guard is evaluated on it;
- the decomposition sees the four principal cells only;
- it can **attribute** a negative and can never **create** a positive.

It holds exactly what `FULL` holds; only the observation budget differs, at M113's multiplier of
four, inherited rather than invented so it cannot be tuned here.

On the dry run it settled the question rather than leaving it asserted: at four times the
observations the same machinery scored identically (0.48 → 0.48), and none of the `undetermined`
outcomes sat at the invocation ceiling. The arm stays because on a real bank the answer could
differ, and because an attribution backed by evidence is worth one fenced cell.

**Running total: 4 principal arms + 1 fenced diagnostic arm. Nothing else was added.**
