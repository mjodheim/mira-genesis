# Decision register

## D001 — The repository is the official memory

Project continuity rests on versioned files, not solely on conversational context.

## D002 — Refocus on Metamorphosis

The V4–V6 prototypes remain sensorimotor benches, but the main line of research targets
trans-substrate portability and continuity.

## D003 — Frozen protocols

Any significant change made after observing a result creates a new numbered experiment.

## D004 — External evaluator

Exhaustive proofs and hidden tests do not count as experiments available to the
organism.

## D005 — No AGI claim

The M001–M011 validations are limited to the formal domains described in their
protocols.

## D006 — M012 must remove specialised compilers

The next accepted advance must concern the autonomous birth of a body, not another
hand-written backend.

## D007 — The working tree holds only living code

The code of a revoked experiment leaves the working tree; its scientific record stays.
Git history is the archive, and `archives/RETIRED_CODE.md` is its index: every removal
cites the commit where the file remains readable.

Reason: the inherited M012 / M013b stack, about 2,400 lines, formed an entirely
disconnected import subgraph and broke `pytest -q` by importing `torch`. Nothing
signalled it, because the sealed workflows only ran targeted test files.

## D008 — A permanent CI, distinct from sealed evaluations

`.github/workflows/ci.yml` protects the working tree on every pull request and never
produces a scientific result. Sealed evaluation workflows are still created per
experiment, run once, then retired to `archives/workflows/`: a consumed canonical
workflow must no longer be executable, otherwise the single-run rule holds only by
convention.

`scripts/check_repository_integrity.py` makes structural the three defects that had
escaped CI: an unimportable module, an orphan module, a phantom declared dependency.

## D009 — The next accepted advance must extend the language, not the catalogue

D006 required M012 to remove specialised compilers. The same requirement applies one
level up: **an advance that consists of choosing better within a hand-written catalogue
is not an advance.**

M012b, M013e, M014b and M014c share a limit none of their criteria measured.
`MetaPlasticitySession.identify` enumerates exactly twelve structural programs; all
learning reweights counters over that closed catalogue. The organism cannot express
anything it was not given, and M014c would have measured the quality of that
reweighting, not the growth of a capability.

M014c is therefore halted before evaluation, as M014 was, and replaced by M017 —
self-extending language. The roadmap changes order, not names: M015 and M016 are
deferred because they would laterally extend a paradigm whose core is not established.

## D010 — A measured quantity must have a dynamic range

M014b compared 14 queries to 14 queries, over a window four queries wide, with a
pre-registered margin of 25%. No result there was decidable: the criterion measured
sampling noise.

Every later experiment must therefore establish, **before freezing its protocol**, that
the chosen quantity varies over several orders of magnitude between the systems
compared, and that the retained margin exceeds the dispersion between environments.

Corollary: a structurally incapable baseline is a control, not a criterion. The closed
catalogue fails 0/42 in M017 development; freezing a threshold against it would pass
trivially. A criterion must oppose two organisms of identical capability at the first
episode, which only the mechanism under test separates afterwards.

## D011 — The project follows what its own failures identified

Four experiments failed — M014b, M017 on its threshold, M018, M019 — and **none failed
in the organism**. Each time, what was being built held; what gave way was the way of
judging whether it was better.

The repository's central question therefore becomes: **when does a proxy measure stop
tracking what it claims to track, and under what optimisation pressure?**

### What this decision does not claim

The problem is neither new nor unexplored. Goodhart's law, reward hacking,
specification gaming, novelty search and quality-diversity algorithms have worked on it
for a long time. Any wording suggesting the project enters vacant ground would be false,
and stating so is part of the decision.

### The real angle

Those bodies of work operate almost entirely where **the true objective is not exactly
verifiable**: reward hacking is diagnosed because a human finds the result suspicious.
Here, the behavioural equivalence of two finite automata is provable.

The repository can therefore show **where exactly** a measure comes loose, rather than
note that a result looks wrong. It is a decidable testbed for measure design, and that
is a modest, defensible contribution.

### Consequences

- `MEASURES.md` becomes a first-class register, beside `FAILURE_LOG.md`;
- the metamorphosis line is not abandoned: it produced the decidable domain, the two
  sealed validations and the six divergence cases. It becomes the **testbed** for the
  question rather than the question;
- M017 still stands ready to freeze, its results acquired and its criterion cleaned up.

## D012 — The repository is written in English

The repository is public. Registers, protocols, comments and docstrings are written in
English so the work is readable by the people most likely to find it useful.

French text predating this decision is translated rather than left in place: a
half-translated repository is worse than either language, since a reader cannot tell
which parts they are missing.

## D013 — A replay-only tool cannot evidence transported plasticity

M033's body-anchored control block returned a perfect tie, 0 wins, 32 ties and 0 losses,
between the complete lineage and its learned-tool ablation. The tie is not a weak effect
and not a threshold problem. It is structural.

`PatchOperation` binds every edit to a positional AST index, and `LearnedRewriteTool`
returns its stored operations verbatim. A learned tool is therefore a literal replay of
past edits at past sites. It cannot fire at an equivalent site with a different index, and
it encodes a destination value rather than a relative transformation.

Two consequences follow, both measured in `tests/test_m020_learned_tool_replay_limit.py`:

- the tool that produced a body is a no-op on that body;
- a lineage that has completed one improvement cycle carries exactly that tool.

So under the correct body anchor, a single-cycle lineage's learned-tool ablation compares
two lineages whose only difference cannot act. The control measures nothing, and no change
to the post-migration task family can repair it.

### Consequences

- Gate 8's learned-tool control is **structurally uninformative** for single-cycle
  lineages. A tie there may not be reported as evidence for or against transported
  plasticity;
- the requirement this replaces — that the task must demand a component the body does not
  encode — was unsatisfiable and is withdrawn. The real precondition is a property of the
  lineage: its registry must hold a tool it is not already expressing;
- that condition arises naturally from rollback, or from the repeated improvement cycles
  Gate 9 already requires. Gate 8 and Gate 9 are therefore not independent, and Gate 8's
  tool control should be evaluated on a multi-cycle lineage;
- this is D009 recurring one level up. D009 rejected choosing better inside a closed
  catalogue; here the language of *tools* is closed in the same way, since a learned tool
  cannot abstract over the site it was learned at. Whether M017's self-extending language
  lifts this limit is now a concrete, testable question rather than a general aspiration.

The memory mechanism is unaffected: it is decoded and re-applied against current evidence,
so it can act on a body it did not produce, and it does.

### Confirmed repair path

The prediction that repeated cycles restore the condition was then measured rather than
left as an argument. A three-cycle lineage over three distinct finite targets accumulates
three learned tools, of which one can still act on the final body.

The mechanism is narrower than "more cycles help". The newest tool is *always* inert,
because it is by construction the trace that produced the current body. An earlier tool
becomes able to act again only once a later cycle moves the body away from what that tool
wrote. Pinned in `tests/test_m020_multicycle_tool_reactivation.py`.

Gate 8's learned-tool ablation is therefore measurable on a multi-cycle lineage and not on
a single-cycle one. That is a sequencing constraint on the roadmap, not a threshold
choice: Gate 9 must be built before Gate 8's tool comparison can be run at all.

## D014 — A defect in the rewrite kernel is fixed by its owner, not in passing

M020's `apply_patch` does not round-trip negative integer constants: `ast.unparse` writes
`-2`, re-parsing yields `UnaryOp(USub, Constant(2))`, and each further patch at that index
stacks another negation. Constant patches are therefore non-idempotent for negative
values, the AST grows without bound, and the search can reach bodies whose outputs leave
the declared state range.

The defect sits in the kernel every construction experiment is built on — M023, M024,
M025, M032, M033 — and `ConstantRewriteTool.values` puts it inside the search space of all
of them.

### The decision

The defect is **recorded and pinned, not silently repaired.**

Correcting `apply_patch` changes which candidate sources are reachable. That can move the
recorded calibration digests which D003 treats as evidence, and the repository's rule is
that no rerun replaces a first attempt. A kernel change with that reach is a protocol-owner
decision.

`tests/test_m020_negative_constant_defect.py` asserts the current behaviour, so a fix must
consciously update those tests rather than pass unnoticed.

### What is and is not affected

Nothing recorded is contaminated: 776 of 776 adopted sources across the four M033
calibration blocks contain no negative constant, and all four digests reproduce exactly.
The defect is latent in the evidence, not expressed in it.

It was expressed in the Gate 9 exploration that found it. Both candidate reuse lineages
relied on stacked negations, so that demonstration is withdrawn. Gate 9 remains
undemonstrated, and whether its reuse clause survives on a corrected kernel must be
re-measured rather than assumed.

### Corollary

The defect was found by attempting a construction gate, not by the test suite, the
integrity audit or any experiment's own controls. All of those passed over it for the
whole life of the stack. That is consistent with what D011 records: on this project the
judgement apparatus fails before the mechanism does, and only a new demand on the system
exposes it.

## D015 — Recorded artifacts are valid for the kernel generation that produced them

D014 recorded the negative-constant round-trip defect and deliberately left it unrepaired,
because correcting it changes the reachable candidate set. The repair has now been made,
and it does move every recorded M033 digest:

| Block | Kernel generation 1 | Kernel generation 2 |
|---|---|---|
| fixed `1024–1031` | `e189142c…` | `d5ecb380…` |
| structural `2048–2063` | `117de3c3…` | `1c639111…` |
| combined `3072–3103` | `0ef00f0f…` | `c8213448…` |
| body-anchored `4096–4127` | `394f9904…` | `1a7ac8c3…` |

### The decision

The generation-1 artifacts are **kept, not re-run and not withdrawn.**

They remain exact evidence of what the rig did under the kernel that produced them. That
is the same treatment the repository already gives M012 against M012b and M013d against
M013e: a superseded run is not deleted, it is scoped.

Every recorded digest is therefore read as a statement about a kernel generation, and any
future artifact must name the generation it belongs to.

### Why re-running was rejected

Not because it would be inconvenient, but because **no finding changes.** The paired
outcomes are identical across the two generations — `complete_vs_fresh_b`,
`complete_vs_unchanged_parent`, `complete_vs_learning_state_ablated`,
`complete_vs_learned_tools_ablated`, exactness, held-out exactness, output-only immobility
and the parent/ablation separation all reproduce. Only the candidate medians fall, by 3 to
7 per cent, which is the removal of phantom candidates the defect injected into every
search in the stack.

Re-running would replace intact evidence with cosmetically different numbers and would
contradict the rule that no rerun replaces a first attempt. Scoping costs nothing and
preserves both.

### Consequence

A cost figure may only be compared against another cost figure from the same kernel
generation. This is a narrower version of the discipline D010 already imposes: a measured
quantity needs a dynamic range, and it also needs a fixed instrument.

## D018 — An identity is computed over what was decided, not over what the producer returned

M048's `validation_digest` was computed over the whole mapping `_validate` returns. That mapping
carries `worker_pid`, the pid of the disposable Node validation process, so the digest changed
with the pid and carried that drift into the patch registry record, the native journal, the
causal memory and the final state digest.

Two runs of the same experiment in the same environment therefore produced different
`final_state_digest` values, while the protocol required replay to "reproduce the exact final
native state digest".

### The rule

**A recorded identity is derived from the fields that carry the decision, and from nothing
else.** Anything a producer attaches that describes the environment — process ids, host names,
paths, wall-clock times, durations — is evidence that something ran. It is not part of what was
decided, and it must be excluded before digesting.

The exclusion is explicit and named, not incidental: `_VOLATILE_VALIDATION_FIELDS` states which
fields are environmental, so adding one is a visible change.

### Why the earlier corrections did not settle it

The M048 history contains `M048: remove volatile process identity from manifest` and
`M048: keep manifest identity deterministic across runtime processes`. Both removed the pid from
the manifest's top level; neither removed it from the value the digests were derived from. The
visible field disappeared and the dependency remained, which is why the defect survived two
corrections aimed at it and a full qualification run.

Removing a volatile field from a *report* is cosmetic. Removing it from what an *identity* is
computed over is the fix.

### Applying D015

The repair moves `final_state_digest` and `post_migration_checkpoint`. Thirty-nine manifest
fields are unchanged, including every scientific outcome, and a permanent test runs the lineage
under both digest rules to assert the moved set is exactly those two.

M048 artifacts therefore belong to a digest generation, as M033's do to a kernel generation. The
qualifying run is not re-executed: it exercised the science, the science is untouched, and no
rerun replaces a first attempt.

### Corollary

This is M014c a third time — `consolidation_record_sha256` differed between environments because
it included floating scores. D010 asked for a fixed instrument; D018 asks for a fixed *input* to
the instrument. Both failures were found by trying to build the next thing on top, never by the
test suite or the integrity audit.
