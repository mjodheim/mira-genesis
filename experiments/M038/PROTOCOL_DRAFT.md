# M038 — two-speed lineage: escalation boundary and causal journal

**Status: PRE-RESULT PROTOCOL DRAFT. Not frozen.**

- No M038 outcome measurement taken.
- No sealed M038 block created or opened.
- **Development calibration has been performed**, only to select and validate the trigger
  algorithm — recorded in [`results/M038_TRIGGER_CALIBRATION.md`](../../results/M038_TRIGGER_CALIBRATION.md).
  Its twelve rows are **consumed for that decision** and may not later confirm the trigger's
  success or efficiency.

An earlier draft of this header said "no measurement taken" while the document used a
twelve-case measurement to choose the exact algorithm. That was false.

## What M038 is for

To show, in a bounded domain, that one organism can act through a compact path, detect that
its own body is provably insufficient, cross into a slow verifiable loop, change itself,
return, and keep the improvement — **without paying the full cost of proof on every
operation**.

## What M038 will not claim

It will not claim Gate 9, three cycles, trans-substrate migration, a curriculum, a new
intermediate representation, a learned model, or general intelligence.

It will not claim level-3 replay. The fast path's micro-operations are not individually
replayed. What is proved is that the slow path begins from a **committed checkpoint whose
compact history has not been altered** — level 2 plus a commitment, and the report must use
those words.

## Definitions, fixed before measurement

**Lineage.** One founder body plus an ordered chain of adopted mutations, each recorded as
the operation that produced it. Reconstructible from the founder and the chain.

**Cycle.** One traversal: fast path → escalation → diagnosis → proposal → isolated
evaluation → adoption or rejection → return to fast path. A cycle is not "a search that
succeeded".

Two kinds of cycle, kept apart from the first definition rather than only in the verdict
table below:

```
An infrastructure cycle may end in rejection.
A functional metamorphosis cycle requires the complete F0 → F1 sequence.
```

**Escalation.** Crossing the boundary, on the single active trigger below.

**Distinct task family.** Not used in M038. One family only. The definition is deferred to
whichever experiment first needs two, because inventing it now would mean choosing families
without a frozen generator.

## The active trigger, and only it

`proved_structural_incapacity`: the Myhill–Nerode lower bound over the organism's own oracle
answers exceeds the body's state count.

Computable, sound, independent of the hidden target. **M038 uses an exact maximum
pairwise-distinguishable set, not the greedy one**, and the reason is measured rather than
assumed.

Two causes of a false negative must stay distinguished, because only one is repairable:

- **algorithmic incompleteness** — a larger set exists and the search order missed it.
  Removed by the exact search;
- **evidence incompleteness** — no observed suffix separates the relevant pair. Epistemic,
  and not removable by any algorithm.

Development calibration used 12 rows at two **development observation sizes**. No prior
versioned commitment fixed those sizes. Full record in
[`results/M038_TRIGGER_CALIBRATION.md`](../../results/M038_TRIGGER_CALIBRATION.md).

```
gap_a(row) = exact_bound - greedy_bound
gap_b(row) = true_minimal_states - exact_bound
```

| Quantity | Value |
|---|---:|
| Gap A, summed over 12 rows | **8** |
| Gap B, summed over 12 rows | **0** |
| Rows where greedy understated | **6 of 12** |
| Maximum exact-search nodes | **515,432** |
| Maximum pair tests | **8,001** |
| Development safety ceiling exceeded | **no** |

Tractability is argued from **counted operations**. Wall clock is diagnostic here and is not
used to justify it — an earlier draft of this section cited "0.77 seconds", "committed
observation sizes", "measured gap: 4" and "greedy missed 3 of 6", each of which contradicted
ADR 0002, the calibration record and the reproducible script.

**`Gap B = 0` holds on these twelve consumed rows only.** It is not a general property:
evidence incompleteness survives any algorithm and was simply not exercised here.

The claim is scoped accordingly: *when the certificate exists, structural incapacity is
proved*. Never *M038 detects every situation requiring growth*.

### The M038 certificate budget, committed here before any M038 measurement

The 2,000,000 figure above is a **development safety ceiling**: it bounded the calibration,
and no versioned commitment fixed it beforehand. The M038 budget is a separate decision, and
it is taken in knowledge of those consumed cases:

```
maximum_search_nodes = 2000000
maximum_prefix_count = 512
```

On exhaustion of either, the solver emits `certificate_status =
unavailable_within_committed_budget`. The router **does not escalate** on this trigger, and
**never falls back to the greedy bound** — that fallback would reintroduce exactly the
incompleteness the exact search exists to remove.

The historical greedy in `m035_evolution.py` is not modified, so M035 stays reproducible.

Specified but **inactive**: `repeated_failure_under_comparable_conditions`,
`sustained_cost_above_committed_threshold`. Neither may be activated until its defining
fields, or its threshold, are committed.

Rejected for M038: persistent uncertainty, saturation. No exact definition exists.

## Three arms, and only three

| Arm | Description |
|---|---|
| **A — fast path only** | same kernel, no slow path, no body change. Establishes what stays impossible without escalation. |
| **B — two-speed lineage** | same fast path; escalation only on proved structural incapacity; full causal journal after the boundary; adoption or rollback. **The mechanism under study.** |
| **C — full critical-path journalling** | identical decisions and identical operations to B; **C's instrumentation is a superset of B's**, not a substitute for it. Measures the cost of putting the proof machinery in the critical path. |

### Arm C is an instrumental superset of arm B

Fixed here, because the efficiency rule is otherwise uninterpretable:

```
Arm C produces every trace, commitment and checkpoint produced by arm B,
plus a full causal event and the required state digests for every fast-path
operation.
```

Hence:

```
evidence_B ⊂ evidence_C
```

If C were allowed to *replace* B's compact trace with a different one, it could emit zero
`compact_event_serializations`, and B would score worse on that dimension for having produced
the very evidence C omitted. The comparison would then measure a difference in instrumentation
design rather than the cost of proof. Under the superset rule, every proof-cost dimension can
only be non-decreasing from B to C, and the difference is exactly the additional cost of
journalling the fast path.

A run where C fails to reproduce B's compact trace **invalidates the efficiency comparison**,
on the same footing as a decision-transcript divergence.

**B and C must produce the same decision transcript**, not merely the same final result:

admitted observations · escalation or its absence · the certificate · candidates
constructed · order of evaluations · verdicts · candidate adopted or rejected · rollback if
any · final functional state.

The only permitted differences are journalling artifacts and journalling costs. No
journalling may consume the mutation RNG, change an iteration order, alter a decision
timeout, add a tool call, change a search limit, or touch the functional state.

A B/C divergence **invalidates the whole efficiency comparison** rather than being reported
as a result.

Ablations of the tool registry, of specialists, and of the router are **secondary controls
or M039**. Introducing them here would make attribution impossible — the failure mode this
repository has already paid for.

## Two questions, kept apart

**Functional.** Can the lineage detect a structural incapacity, enter the slow path,
construct and evaluate candidates in isolation, **adopt one strictly improving candidate**
to reach F1, **roll a separate failing attempt back exactly to F1** — restoring body, tools
and memory — and **return to the fast path with F1 active**?

An earlier draft asked whether the lineage could "adopt or reject". That is the
infrastructure question, and asking it here reintroduced the ambiguity the F0 → F1 sequence
below exists to remove. A rejection answers the infrastructure question and never the
functional one.

**Efficiency.** At identical decisions, does journalling restricted to the slow path cost
less than journalling the whole fast path?

Neither compensates for the other. A good efficiency figure does not excuse a functional
failure, and a functional success does not excuse a cost explosion. Both are reported
separately, and a failure of either is a failure of M038.

## The cost rule, fixed here rather than left open

ADR 0003 observes that a macro's value depends on the cost rule: charged as the sum of its
primitives it need not enlarge the reachable set, charged as one symbol it can. M038 cannot
stay neutral, or the efficiency comparison would be undefined.

| Item | Decision |
|---|---|
| Kernel for the cycle | **M017's structural language**, where `walk` counts depth in symbols |
| Budget unit | one **symbol application** |
| Primitive tool | 1 unit |
| Composed or learned tool (macro) | **1 unit**, however many atoms it unfolds |
| Construction cost | counted once, at the construction event, in `candidates_constructed` |
| Storage cost | `peak_persistent_artifacts`, reported and not charged to the search budget |
| Call cost | 1 unit per application, identical for every tool class |
| Effect on depth | a macro consumes one unit of depth, which is exactly why it can extend reach |

M020's rewrite kernel, which charges a learned tool per operation, is **not** the kernel of
this cycle. Any figure produced here is stated relative to the rule above.

## What one cycle cannot establish about a tool

With a single cycle, a newly built tool can be registered, attributed to its constructor,
validated, and carried in the final state.

Its **causal reuse on a later cycle cannot be demonstrated**, because there is no later
cycle. That property belongs to a multi-cycle experiment, and M038 must not be read as
evidence for it. Gate 9's requirement that a later cycle reuse a tool is not addressable
here at all.

Gate 2 is addressable only under the condition below, and an earlier draft stated it flatly
as "addressable here", which registry membership alone would have satisfied:

```
Gate 2 is addressable only if a lineage-constructed tool is used causally
during candidate inspection, construction or validation and its necessity
is supported by the committed ablation.
```

If no such tool exists in the run, **M038 claims nothing about Gate 2**. A tool absorbed
from the adopted trace after adoption does not meet this condition: it was not available to
build the thing it came from — see ADR 0003.

## Measures

Reported as a **vector**, never as a synthetic score:

`functional_deterministic_operations` · `audit_deterministic_operations` · `search_nodes` ·
`candidates_constructed` · `candidates_evaluated` · `hash_operations` ·
`body_serializations` · `compact_event_serializations` · `full_event_serializations` ·
`full_checkpoint_serializations` · `journal_bytes` · `archive_projection_operations` ·
`tool_calls` · `rng_draws` · `peak_persistent_artifacts` ·
`peak_persistent_audit_artifacts` · `escalations` · `false_escalations` ·
`missed_escalations` · `wall_clock_diagnostic`

An earlier draft carried a single `deterministic_operations` and introduced
`full_event_serializations`, audit operations and audit artifacts only inside the comparison
rule. A dimension that exists solely in the rule cannot be reported, so the four names below
are part of the **primary vector** and are used under exactly these spellings throughout this
protocol:

```
functional_deterministic_operations
audit_deterministic_operations
full_event_serializations
peak_persistent_audit_artifacts
```

The functional/audit split is the same one ADR 0001 makes between `functional_state` and
`audit_state`: only the functional half must be identical between arms.

Weights collapsing these dimensions into a single cost would themselves be a policy, and
would have to be committed separately. M038 does not define them.

### What "B costs less than C" means, fixed before measurement

Falsifier 9 says arm B must reduce the cost of proof. A vector has no default ordering, so
the rule is pre-registered here.

**Dimensions that must be exactly equal** between B and C — a difference in any of them
invalidates decision equivalence, and with it the whole comparison:

`functional_deterministic_operations` · `search_nodes` · `candidates_constructed` ·
`candidates_evaluated` · `tool_calls` · `rng_draws` · `escalations` · final functional state
digest

**Proof-cost dimensions**, on which B is compared to C:

`audit_deterministic_operations` · `hash_operations` · `body_serializations` ·
`compact_event_serializations` · `full_event_serializations` ·
`full_checkpoint_serializations` · `journal_bytes` · `archive_projection_operations` ·
`peak_persistent_audit_artifacts`

**Rule.** B must be **no worse than C on every** proof-cost dimension, and **strictly better
on the primary dimensions**, designated now and not after measurement:

```
body_serializations
journal_bytes
audit_deterministic_operations
```

The superset rule above is what makes "no worse on every dimension" a meaningful test rather
than an artifact of which arm was instrumented differently.

Wall clock plays no part in this rule.

### Construction cost is not a count of candidates

An earlier draft recorded construction cost "in `candidates_constructed`". That is a
quantity, not a cost: one candidate may take a single operation or several thousand. The
counter is kept and joined by:

`candidate_construction_operations` · `candidate_construction_nodes` ·
`candidate_construction_tool_calls` · `candidate_construction_bytes`

M017's symbolic budget measures the *reach* of the language. It must not stand in for the
real cost of searching and constructing.

**Wall-clock time is diagnostic and never decisive.** This is M017 §9's rule, and it exists
because M014b's proof failed to reproduce while its result did.

**Information gain per cost** may enter the decision rule only with an exact definition —
reduction of the consistent-body set, exact reduction of a finite hypothesis set, a newly
proved distinguishable prefix pair, or a certified increase in the Myhill–Nerode bound. Any
heuristic estimate stays diagnostic.

## Determinism classes

Every component declares `pure_deterministic` or `seeded_reproducible`. A seeded component
is reproducible only if the seed, the generator algorithm and version, its initial state, the
exact order of consumptions, and every operation that may consume the stream are committed.

**No seeded operation may be recorded as purely deterministic**, even when it reproduces
under the same seed.

## Cost of proof, by design

- **Fast path**: light diagnostic trace, plus a rolling hash over compact events. No body
  digest per operation. A batched commitment every N operations is permitted with N fixed
  before measurement.
- **Boundary**: one checkpoint — cognitive state, body, portable memory, tool registry, cost
  counters, seed and RNG state, last rolling hash, and the observations justifying the
  escalation.
- **Slow path**: full causal journal, hash-chained.

## Adoption, rejection, rollback — the exact functional sequence

An earlier draft said a rejection completes a cycle, that the organism must keep an
improvement, and that rollback must be exercised. Those three are inconsistent: a bare
rejection changes nothing, and a rollback that undoes the successful adoption discards the
improvement. The sequence below removes the ambiguity.

```
F0 — pre-escalation functional state

1.  prove structural incapacity;
2.  enter the slow path;
3.  construct and evaluate candidates;
4.  reject at least one ineligible candidate, if one is generated;
5.  validate and adopt one strictly improving candidate;
6.  obtain functional state F1;
7.  initiate a forced failing provisional adoption from F1;
8.  roll that attempt back exactly to F1;
9.  return to the fast path with F1 active;
10. demonstrate a competence available at F1 and not at F0.
```

Rollback therefore restores **F1**, the state before the bad attempt — not the founder F0.
The validated improvement is kept, and the rollback is exercised on a separate, deliberately
failing attempt.

Proposal and judgement remain separate components. A rejected candidate stays archived.
Adoption is versioned. "Exact rollback" is a claim about `functional_state` only; the journal
and audit counters continue across it.

## Three verdicts, reported separately

| Verdict | Requires |
|---|---|
| `infrastructure_cycle_valid` | the journal, checkpoint, evaluation and archive behaved correctly — **a cycle ending in rejection can satisfy this** |
| `functional_metamorphosis_supported` | the full F0 → F1 sequence above |
| `efficiency_claim_supported` | the component-wise rule below |

A cycle ending in rejection **cannot** satisfy `functional_metamorphosis_supported`.

The main functional success requires all of: a valid certificate; the boundary crossed; a
candidate adopted; an exact pre-defined improvement; return to the fast path; a forced
rollback succeeding on a separate attempt; final state equal to F1; and final competence
strictly above F0 by the committed rule.

## The escalation checkpoint

```
EscalationCheckpoint
- schema_version
- protocol_commitment
- fast_trace_head
- fast_event_count
- body
- body_digest
- portable_learning_state
- tool_registry
- deterministic_counters
- rng_algorithm_and_state_if_present
- admitted_observations
- evidence_digest
- incapacity_certificate
- escalation_reason
- checkpoint_digest
```

The slow path **recomputes the certificate from the recorded body and evidence**. It never
accepts `escalation_reason` as an assertion.

## Falsifiers

Stated before measurement. Any one of these fails M038:

1. the certificate asserts a bound above the body size while its recorded witnesses do not
   prove it;
2. the certificate cannot be recomputed from the checkpoint;
3. arm A solves a task the experiment declares structurally unreachable;
4. arms B and C diverge in their decision transcript;
5. arm B does not complete the F0 → F1 sequence: no candidate adopted, or no strictly
   improving candidate, or the forced rollback not exercised, or the final functional state
   not equal to F1, or final competence not strictly above F0 by the committed rule. A cycle
   ending in bare rejection fails this falsifier, whatever the infrastructure did;
6. a rollback does not restore the functional state exactly;
7. a deleted, altered or reordered event is not detected;
8. the reconstructed archive diverges from the journal without an error;
9. arm B does not reduce the cost of proof relative to arm C.

Falsifier 9 refutes the **efficiency** claim and not functional feasibility. The wording is
fixed so the two cannot be traded against each other:

> M038 reports two independent verdicts. A functional success with an efficiency failure is
> a **supported functional result and a rejected efficiency hypothesis**. The combined
> expected claim is **not supported**.

An earlier draft said both that an efficiency failure fails M038 and that it is an honest
non-partial outcome. The formulation above replaces both.

Also failing: any tool counted toward Gate 2 without a construction event, and any external
model invoked in the lineage.

No rerun replaces the first attempt. No threshold is relaxed after observation.

## Stop condition

M038 stops after **one** DFA cycle, succeeded or falsified.

It does not extend into three cycles, POET, a new representation, a learned model,
trans-substrate migration, or Gate 9. Each of those is a separate experiment with its own
protocol.

## Expected result, stated in advance

> An exact escalation boundary allows a deterministic fast path to be left, a bounded
> metamorphosis to be executed with a causal journal, and the fast path to be re-entered,
> without imposing the full cost of proof on every operation.

A negative result is valid and is kept.

## Sealed block

**None is created or opened by this document.** Cases 0–11 and 12–23 are consumed and may
only reproduce a previous result, exercise the program, or describe a correction
retrospectively.

The sealing mechanism is written only after the measures, baselines and falsifiers above are
fixed, and it must include a guard preventing unit tests, development scripts, ordinary
workflows and parameter sweeps from opening the block.

## Remaining before freeze

- [ ] human review of this draft;
- [ ] journal implementation and its integrity tests;
- [ ] checkpoint and escalation boundary;
- [ ] one development DFA cycle;
- [ ] sealing mechanism and its guard;
- [ ] SHA-256 of the frozen protocol, recorded in `results/M038.md`.

Until the first box is checked, none of those that follow may be.
