# M087 — Evolvable Evidence Acquisition and Candidate Selection

**STATUS: FROZEN BEFORE QUALIFICATION MATERIALIZATION. ONE ATTEMPT. NO REROLL.**

## What M086 left

D054 named the part of the improvement mechanism that was never mutable:

> Every meta-primitive acts on the hypothesis schema or the rule set. None acts on the selection
> rule — the greedy first-past-the-post over public score. That rule is frozen and human-authored,
> and it is what failed.

Verified in code, not documentation. `m086_meta_lineage.run_cycle` selects with
`if best is None or passed > best[0]` over enumeration order. The comparison is strict, so a tie
silently keeps whichever candidate the generator emitted first, and `TOOL_EXPRESSIONS` begins with
`midpoint`. **The tie is not recorded anywhere.** M086-C adopted `midpoint`, which fits the public
case `mean 1 2 3 -> 2.0` because `2b = a + c` makes the average and the endpoint-midpoint coincide,
and fails the hidden cases.

The problem is not that the rule preferred `midpoint`. It is that under the acquired evidence
`mean` and `midpoint` are **observationally equivalent**, and no selection rule has an epistemic
justification for choosing either. The correct terminal action is to notice, and then to obtain
evidence that discriminates.

## The mutable object

`SelectionPolicy` — an ordered instruction program plus an acquisition budget, serialized,
digested and executed by a fixed interpreter. Not a configuration flag: `{"use_active_learning":
true}` would move a human decision into JSON rather than into the lineage.

M0 is `[SCORE_PUBLIC, ARGMAX_FIRST]`, which is M086's rule and nothing else. It has no
representation for two candidates being indistinguishable, and no action that could obtain more
evidence. That is a legitimate limitation rather than a strawman: it is the rule the repository
actually froze, and a regression drives it against `run_cycle`'s selection to prove it.

Diagnosis and candidate generation stay **fixed** at M047's frozen pair, unchanged.

## Two evidence spaces

* **E_acquired** — observations of an authorized reference source on requests the lineage chooses
  from a bounded per-family experiment space. This is a membership query in the sense of active
  automata learning (Angluin, *Learning Regular Sets from Queries and Counterexamples*, Information
  and Computation 75(2), 1987); the experiment is chosen by a general scoring rule in the sense of
  Bayesian experimental design (Lindley, *On a Measure of the Information Provided by an
  Experiment*, Annals of Mathematical Statistics 27(4), 1956) and query-by-committee (Seung, Opper
  & Sompolinsky, COLT 1992). These are imported as **justification for the shape of the instruction
  set**. None is installed as a finished algorithm, and M0 possesses none of them.
* **E_hidden** — the qualification cases, held by the evaluator.

**Disjoint by construction.** `EvidenceSpaces` refuses to build a family whose experiment space
intersects its hidden domain. The first draft of the planning family did intersect, and the check
refused to construct it. That is recorded here because it is the check working rather than a rule
being remembered.

### Why acquisition is not an evaluator leak

The reference source answers *what this input produces*, which is what running the real system
tells anyone who runs it. The evaluator answers *whether a candidate is correct on cases nobody may
see*. The first is an affordance of the environment; the second is the measurement. Observing
`mean 1 2 6 -> 3.0` eliminates a candidate predicting `3.5`; it discloses nothing about the hidden
cases, which live in a disjoint domain, and nobody is told which candidate is right. No evaluator
callable is passed into a policy, so a policy has no path to one.

M0 can see that the environment exists. It has no instruction that could query it. That is the
capability difference, and it is informational rather than computational.

## Three families

Same generic mechanism, same primitives, no truth-specific code. What differs is what is ambiguous.

| Family | Limitation | Equivalent under public evidence | Why they coincide |
|---|---|---|---|
| `tool_semantics` | unrouted `mean` | `mean`, `midpoint` | `mean 1 2 3` is an arithmetic progression |
| `interpretation_routing` | unknown token `combine` | `add`, `mul` | `2 + 2 == 2 * 2` |
| `planning_structure` | nested request refused | `one_level`, `recursive_postorder` | both plan depth two; they differ at depth three |

`interpretation_routing` is preregistered as a **no-harm situation**. `ALIAS_TARGETS` begins with
`add`, which happens to be the truth, so the frozen tie-break lands correctly there by luck. It is
kept rather than tuned away: it shows the evolved mechanism does not break what the frozen one gets
right, and it is a standing reminder that one correct adoption is not evidence about selection. The
capability claim rests on the two families where the arbitrary tie-break lands wrong.

## Chronology, enforced rather than described

```
T0  protocol frozen and digested
T1  M0 policy recorded by digest
T2  development situation materialized
T3  limitation observed — M0 adopts under an unrepresented tie
T4  meta-transformations rejected on disposable descendants
T5  one validated outside the mutable body
T6  policy adopted, serialized, DIGESTED
T7  salt consumed; qualification cases drawn      <- strictly after T6
T8  arms executed
T9  hidden evaluation sealed
T10 rollback proved
T11 leak checked
```

M086-A was disqualified partly because its holdout existed as module constants before the
meta-search ran. Here the qualifying cases are drawn from a salt released only after T6, and P10
verifies the recorded order rather than asserting it.

## Arms

| Arm | What it has |
|---|---|
| `evolvable_selection_evidence` | the adopted policy, restored from its serialized form |
| `fixed_selection_evidence` | M0's policy, never mutable |
| `selection_acquisition_ablated` | the adopted policy with every informational instruction removed |
| `more_budget_same_evidence` | M0's policy at **10×** the computational allowance, same E_acquired |
| `fresh_agent` | M0's policy with no development history |

`more_budget_same_evidence` is the arm that matters. If computation could close the gap, the
deficit was never informational and the hypothesis fails.

## Ten conditions

Each is computed and each can make the verdict negative. A test compares the declared list against
the keys `evaluate` returns, because M086-A reported positive against a threshold where four of ten
conditions were absent from the verdict function and one had no implementation anywhere.

P1 ambiguity represented · P2 meta-transformation adopted after rejections · P3 evolvable correct
on every situation · P4 capability discordance against fixed · P5 more budget over the same
evidence cannot close it · P6 acquisition ablation loses the capability · P7 cross-family reuse ·
P8 policy persisted and restored byte-identically · P9 no evidence leak · P10 chronology holds.

## Preregistered falsifiers

The result does **not** support H33 if any of these holds: `more_budget_same_evidence` closes a
discordant situation; the fixed mechanism acquires the same information; a meta-primitive names a
family, a probe, a candidate or a truth; an acquisition targets a hidden-domain request or occurs
after sealing; the adopted policy is not persisted or not restorable byte-identically; the
improvement must be re-acquired per family; every arm reaches the same correctness; the gain is
only cost or latency; the meta-language offers only one viable transformation; qualification cases
are materialized before the adopted policy is digested; an external model is called during the
scientific run.

## What a positive result would not establish

Not AGI, not open-ended evolution, not general autonomy, no generality gate, no independent
reproduction, and no release or repository authority. The meta-primitives, the instruction set and
the three families remain authored. That ceiling is the honest subject of the next milestone, not a
caveat on this one.
