# M043 Q3 — constructively available Mealy tasks

**Status: development implementation complete; complete repository CI running.**

## Question

Can M043 admit finite hidden tasks only when the declared parent is exactly incapable of
the target behaviour and an admissible Q2 rewrite trace can still reach that behaviour
inside one fixed depth, node and state budget?

This gate repairs the failure exposed by M041. A generated task is not considered valid
merely because it is difficult or because a larger machine could express it. Admission must
prove necessity and constructive reachability before the task can influence any later
selection.

Q3 is development rig qualification only. It does not select a seed, freeze a hidden bank,
authorise a canonical workflow or establish a new continuous-lineage result.

## Exact structural incapacity

`metamorphosis/m043_task_model.py` defines an independently checkable certificate. The
declared parent must already be canonical, reachable and behaviourally minimal. For an
admitted target:

```text
minimal_states(target) > physical_states(parent) = minimal_states(parent)
```

Because exact Mealy minimisation is available from Q1, this is a theorem rather than a
sampling heuristic: no machine within the parent's declared state capacity can implement
the target behaviour exactly.

The certificate records exact parent identity, minimal behavioural identities, both state
counts and the required growth. Alphabet mismatches, nonminimal parents and targets that fit
inside the parent capacity fail closed.

## Target-blind constructive search

`metamorphosis/m043_task_search.py` performs deterministic breadth-first search over the Q2
rewrite language. Candidate proposals receive only:

- the current body;
- its finite alphabets;
- a declared causal capability surface;
- one immutable search budget.

The proposal function has no target or evaluator argument. The evaluator retains the hidden
body privately and exposes only bounded input/output observations plus an exact commitment.
It may answer whether a completed candidate is exactly equivalent, but it never provides a
transition table, output table, witness trace or target-derived rewrite argument.

The development budget is fixed at depth 2, 512 visited nodes and 4 states. Search terminates
with one explicit status: exact target found, finite space exhausted, depth limit reached or
node budget exhausted.

## Constructive admission

The evaluator enumerates finite history-splitting targets independently of the learner. A
candidate enters the development catalogue only when all of the following hold:

1. the minimal-state incapacity certificate passes;
2. complete target-blind search finds an exact candidate within the declared budget;
3. rebuilding the ordered Q2 operations yields an exact, parent-bound replay trace;
4. the trace first grows reachable capacity and then edits or redirects the new state;
5. every control receives the identical budget;
6. no target behaviour is admitted twice.

The known evaluator-side construction is never placed on the public task surface. It proves
availability only; the search must rediscover an admissible trace from generic Q2 proposals.

## Causal controls

Q3 instantiates six distinct search surfaces before interpreting results:

| Arm | Causally available mechanism |
|---|---|
| Complete | Q2 primitives, lineage-composed split tool and portable proposal ordering. |
| Fresh | Q2 primitives with default ordering; no composed tool or portable state. |
| Unchanged parent | No rewrite operation. |
| Output only | Emission replacement only; no structural growth. |
| Learning-state ablated | Composed tool retained, portable ordering removed. |
| Tool ablated | Portable ordering retained, composed tool removed. |

A permanent guard rejects any pair of controls with the same causal surface. Q3 does not
require every active control to lose; its purpose is to prove that the comparison is real,
equal-budget and structurally meaningful before a later integrated experiment is defined.

## Deterministic development catalogue

`run_q3_development_catalogue()` uses one public, seed-free, minimal two-state parent. The
catalogue requires three distinct admitted targets and examines at most 32 deterministic
candidates. Each admitted target requires three minimal states, while the parent requires
two.

The catalogue records commitments, certificates, exact trace identities, search outcomes
and control outcomes. It explicitly records that:

- no seed was selected;
- no canonical workflow exists;
- target tables were not exported;
- witness traces were not exposed to the public surface.

`scripts/run_m043_q3_catalogue.py` reproduces the evaluator-side development report without
exporting hidden target tables or witness trace bodies.

If the generator cannot produce the required number of admissible tasks, it returns
`insufficient` with explicit negative termination. It does not retry with weaker criteria,
increase the budget or silently substitute an unreachable task.

## Permanent falsification suite

The focused suite contains 29 tests covering:

- the exact minimal-state incapacity theorem;
- rejection of expressible targets and nonminimal parents;
- target-blind proposal signatures and source inspection;
- generic composed-tool enumeration;
- six distinct causal control surfaces and collapse rejection;
- exact search and Q2 trace replay;
- unchanged-parent and output-only structural failure;
- deterministic depth and node exhaustion;
- necessary-and-reachable catalogue admission;
- mandatory growth followed by exploitation of the new state;
- a public surface containing commitments but no hidden tables or operation arguments;
- strict observation and budget limits;
- deterministic catalogue identities;
- explicit negative termination;
- seed-free development qualification without canonical authority.

The focused local suite passes. Q3 is not marked passed until the complete repository suite
and integrity audit pass on Python 3.11 and Python 3.13 in GitHub Actions.

## Next boundary

After Q3 qualification, Q4 may integrate disposable candidate validation, versioned
adoption and exact rollback for Mealy bodies. No hidden task bank, selected seed or canonical
M043 workflow is authorised by Q3.
