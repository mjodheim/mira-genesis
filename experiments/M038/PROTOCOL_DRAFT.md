# M038 — two-speed lineage: escalation boundary and causal journal

**Status: PRE-RESULT PROTOCOL DRAFT. No measurement taken. No sealed block created or
opened. Not frozen.**

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
evaluation → adoption or rejection → return to fast path. A rejection completes a cycle. A
cycle is not "a search that succeeded".

**Escalation.** Crossing the boundary, on the single active trigger below.

**Distinct task family.** Not used in M038. One family only. The definition is deferred to
whichever experiment first needs two, because inventing it now would mean choosing families
without a frozen generator.

## The active trigger, and only it

`proved_structural_incapacity`: the Myhill–Nerode lower bound over the organism's own oracle
answers exceeds the body's state count.

Computable, sound, independent of the hidden target. **M038 uses an exact maximum
pairwise-distinguishable set, not the greedy one**, and the reason is measured rather than
assumed. Over twelve cases at both committed observation sizes, exact maximum-clique search
took at worst 0.77 seconds, and the exact bound equalled the true minimal state count every
time. The greedy missed 3 of 6 cases that genuinely required growth; the exact search missed
none.

Two causes of a false negative must stay distinguished, because only one is repairable:

- **algorithmic incompleteness** — a larger set exists and the search order missed it.
  Measured gap: 4. Removed by the exact search;
- **evidence incompleteness** — no observed suffix separates the relevant pair. Measured
  gap: **0** on these cases, but epistemic and not removable by any algorithm.

The claim is scoped accordingly: *when the certificate exists, structural incapacity is
proved*. Never *M038 detects every situation requiring growth*.

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
| **C — full critical-path journalling** | identical decisions and identical operations to B, with full journalling across the entire fast path. Measures the cost of putting the proof machinery in the critical path. |

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
construct a candidate, evaluate it in isolation, adopt or reject it, return to the fast path,
and — on rollback — restore body, tools and memory exactly?

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
evidence for it. Gate 2's requirement that a tool be constructed by the organism is
addressable here; Gate 9's requirement that a later cycle reuse it is not.

## Measures

Reported as a **vector**, never as a synthetic score:

`deterministic_operations` · `search_nodes` · `candidates_constructed` ·
`candidates_evaluated` · `hash_operations` · `body_serializations` ·
`compact_event_serializations` · `full_checkpoint_serializations` · `journal_bytes` ·
`archive_projection_operations` · `tool_calls` · `rng_draws` ·
`peak_persistent_artifacts` · `escalations` · `false_escalations` · `missed_escalations` ·
`wall_clock_diagnostic`

Weights collapsing these dimensions into a single cost would themselves be a policy, and
would have to be committed separately. M038 does not define them.

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

## Adoption, rejection, rollback

Proposal and judgement are separate components. A candidate is evaluated in isolation. A
rejected candidate stays archived. Adoption is versioned. Rollback restores body, tools and
memory exactly, and is exercised at least once rather than assumed.

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
5. arm B neither adopts an improvement nor produces the expected rejection or rollback;
6. a rollback does not restore the functional state exactly;
7. a deleted, altered or reordered event is not detected;
8. the reconstructed archive diverges from the journal without an error;
9. arm B does not reduce the cost of proof relative to arm C.

Falsifier 9 refutes the **efficiency** claim and not necessarily functional feasibility. The
two verdicts stay separate: M038 may report a functional success with a failed efficiency
claim, and that is an honest outcome rather than a partial success.

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
