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

## D016 — The M049–M052 series is closed at its own success

M049 selected one record from a frozen family of four. M050 composed frozen primitives in
a fixed three-stage grammar, giving 24 candidates. M051 allowed a bounded variable-length
prefix, giving 80. M052 proved that those 80 collapse to 38 behavioral classes on a
declared 156-input finite domain, pruning 42 syntactic duplicates before public search.

Every one of them passed. That is the reason to stop.

### The decision

A successor experiment **may not be justified solely** by any of:

- increasing the number of frozen candidates;
- increasing composition depth;
- adding another human-declared primitive to the same grammar;
- changing ranking, enumeration, caching or pruning while the admissible language stays
  fixed;
- repeating the same selection and hidden-validation pattern on another small arithmetic
  task family;
- describing a larger bounded search as open-ended self-extension.

Such work may remain valid engineering or measurement. It is outside the active
construction frontier.

### Why a passing series is closed rather than extended

Each step made the search cheaper or more exact over a language that a human wrote and
froze. None of them changed what the lineage can express. The set of reachable behaviours
after M052 is the set it inherited from M051, minus the duplicates — a strict subset.

Extending the series is attractive precisely because it is safe: the next increment is
always well-defined, always measurable and always passes. That is the failure mode D009
was written against, one experiment number at a time instead of all at once.

### Consequence

M053 must test endogenous extension: the lineage has to demonstrate that its accepted
language cannot express a solution, and then construct a primitive that was not in the
founder catalogue. The record is [`experiments/M052/SERIES_CLOSURE.md`](experiments/M052/SERIES_CLOSURE.md).

This changes the research direction, not the interpretation of M049–M052. Each remains a
valid bounded result inside its frozen grammar and probe families, and M042 remains the
only positive canonical continuous-lineage completion.

## D017 — An infrastructure failure is not a qualification verdict

M053's first CI attempt, run `31118366409`, failed during *Set up job* with
`Service Unavailable` while resolving GitHub Actions downloads. No experiment code ran.

The append-only rule that preserves M048's two failing runs and M050's one failing run
creates pressure to append this one too. The decision is that it does **not** enter the
qualification history as a negative verdict.

### The rule

A run enters the append-only qualification history as a scientific verdict only if the
experiment's own code executed and produced the failure. A run that fails before the
experiment starts — runner provisioning, action resolution, dependency mirrors, cancelled
in cascade — is recorded in [`FAILURE_LOG.md`](FAILURE_LOG.md) as an infrastructure event
and named as such.

### Why the distinction is worth a decision

A preserved negative verdict is a claim: *this construction was tested and did not hold.*
M048's run 402 says the journal schema was wrong. M050's run 410 says the fixture
contradicted the grammar. Both are about the object of study.

`Service Unavailable` says something about a third-party registry on 6 August 2026. Filed
next to the others without qualification, it would later read as evidence that endogenous
language extension had been attempted and had failed. An append-only history is only
trustworthy if every entry states what was actually observed.

### What it does not license

Re-running is permitted here because nothing was observed, but the permission is narrow.
It does not extend to re-running a job that failed after the experiment's code executed,
and it does not license retrying until a green result appears. If a re-attempt reaches the
tests and fails, that verdict is preserved under the ordinary rule.

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

## D019 — Compositional acquisition buys search cost, not expressive power

D016 closed the M049–M052 series and demanded endogenous extension of the transformation
language. Three experiments attempted it. The line is now closed too, and for a reason that is
worth stating rather than hiding in a status change.

### What the three attempts established

**M053** extends the language by filtering `META_PROGRAMS`, sixteen pair expressions
materialised at import. Its capability gain is real and structural — the founder language cannot
express any operation over adjacent elements — but the mechanism is selection from a declared
catalogue. The level moved; the shape did not.

**M054** removes the catalogue. Candidates are built from two atoms and five operators over a
space of 29,330,422 under a budget of 1,024, so enumeration is impossible by construction. It
demonstrates construction rather than selection, and second-order reuse: the acquired primitive
becomes material for the next acquisition.

**M055** puts that inside the migrated M048 body: the lineage reconstructs its accepted
version-eight native state, constructs a tool compiled to JavaScript, re-verifies all
thirty-two inherited capabilities, adopts, faults and restores. The construction works. Its
ablation refutes the point of it.

### The negative result

M055's ablation gives the from-scratch arm the same composition power as the continued lineage.
It still solves the reuse task: 737 candidates without the acquisition against 48 with it. The
acquisition made the search fifteen times cheaper and made nothing newly reachable.

Two reuse tasks were tried and both were refuted the same way. The first because applying a
candidate twice was available to every arm. The second because `max(|d|, |d|·|d|)` reduces to
`|d|·|d|`, reachable at depth two. A third task was not attempted: after two ablations, choosing
the task that flatters the hypothesis is the tuning illusion recorded in CHANGELOG 0.33.0.

### Why this is structural and not bad luck

In a language closed under composition, with a budget that reaches the relevant depth, acquiring
a sub-expression cannot enlarge what is expressible. Everything the acquisition makes reachable
was already reachable by rebuilding it. The acquisition is a cache.

A capability gain can be manufactured by lowering the depth bound or the budget until the
from-scratch arm fails, but then the gain is an artifact of the declared bound, not of the
acquisition. That is measuring the instrument.

### The decision

**A successor may not be justified by compositional acquisition inside a closed formation
language.** M053, M054 and M055 stand as valid bounded results — the construction machinery, the
second-order reuse, the inherited-regression check and the exact rollback all hold — and none of
them may be cited as evidence that the lineage grew a capability.

This is D009 reaching its own limit. D009 rejected choosing better inside a hand-written
catalogue. D019 records that replacing the catalogue with a hand-written *grammar* does not
escape it, because a grammar is a catalogue you have not enumerated yet.

### Where the frontier goes

Back to the objective the project was started for, and the one thing it has produced that
nothing else has: **M048 changed substrate and kept adapting.**

That result is a single hop, performed once, with a hand-written compiler, on a protocol that
told the lineage when to move. Nothing has migrated twice. Nothing has had to decide that its
substrate no longer suits it. Whether a capability learned *after* a migration survives the
*next* one has never been asked, and it is the question that separates continuity from
translation.

A substrate is not closed under composition. What is acquired there — a body that executes
natively, tools that run in the new runtime — is not a sub-expression of a grammar, so the
argument above does not apply to it. That is why the frontier moves rather than stops.

## D020 — A manifest field is a claim, and reading it back proves nothing

M061 recorded `copy_loop_uses_only_discovered_instructions: True` and
`structural_instructions_authored: False` while its own builder wrote seven opcodes directly
into the loop. An external review found it by reading the manifest against the code. Sixteen
permanent tests passed over it.

### Why the tests could not catch it

The test read:

    assert value["copy_loop_uses_only_discovered_instructions"] is True

That assertion is true whenever the constant is `True`. It verifies that the field holds the
value the author wrote in the same file, and nothing about the loop. A field and a test that
reads it back are one claim asserted twice, not a claim and its verification.

The same shape appears twice before in this project's history. M053's `rollback_exact` compared
a frozen dataclass to itself and could never be `False`. M048's `replay_identical` compared two
runs inside one process, where the volatile value is constant. In all three the mechanism is
identical: **the falsifier's input is downstream of the thing it is supposed to falsify.**

### The rule

A manifest field asserting a property of an artifact must be computed from that artifact, and
its test must be able to fail against a deliberately wrong artifact.

Where a property cannot be computed — because it is a statement about what a human wrote rather
than about a value — the manifest names the exception in a list at the same level as what it
claims. M061 now carries `copy_loop_discovered_instructions` beside
`copy_loop_authored_elements`, and the boolean reads `False`.

### What this does not license

This is not a demand that every claim be machine-checked before it can be recorded. It is a
demand that a claim which *looks* machine-checked actually be one. A prose sentence in a result
document is understood to be an argument; a manifest field named
`uses_only_discovered_instructions` reads as a measurement, and inherits the credibility of one
without having earned it.

Prose that over-reaches is a writing defect. A manifest field that over-reaches is a fabricated
measurement, and it belongs in `FAILURE_LOG.md`.

## D021 — Canonicalisation may not decide hidden behaviour

M062's 480-program grammar leaves sixteen arrangements that satisfy every public observation.
Its region probe also leaves two bytes, `0x02` and `0x06`, with the same observed exit-region
effect. Picking the lowest source digest or byte before independent validation would be
deterministic, but it would not be neutral: the arbitrary representation could carry a different
hidden outcome.

### The rule

**A deterministic representative may be chosen from an observational equivalence class only
after every member of the class passes the independent admission evidence.** If any member
disagrees, the evidence has not established equivalence and the result must stop as ambiguous.

M062 therefore validates the Cartesian product of all sixteen public arrangement survivors and
both exit-region candidates against all three hidden cases. All 32 complete programs pass. Only
then does the smallest digest select one arrangement, and only then does the smallest opcode serve
as the emitted representative of the region-effect class.

### Boundary

This is bounded behavioural equivalence, not semantic equivalence for all programs or inputs. The
class is admitted only for M062's committed copy grammar and hidden cases. A later task, substrate
or grammar must establish its own class again; it may not inherit the canonical representative as
an authored fact.

## D022 — Transfer requires a falsifiable change of contract

M063 reuses M062's arrangement dimensions on a checksum loop. Superficially, any second loop can
be described as transfer: both have an exit predicate, a repeated region and ordered effects. If
the target is distinguished only by prose or by a new task label, the experiment can pass while
executing the old body unchanged.

### The rule

**A claimed mechanism transfer must predeclare a target with a distinct observable contract and
must execute a source-body negative control against the target evidence.** The target evidence
must be capable of rejecting the source body for a measured reason. Interface, output, state
effect or another executable property must differ; changing only constants or case sizes is not
enough.

M063's target has two parameters instead of three, returns a byte reduction instead of a constant
and leaves memory unchanged instead of copying into a destination. The exact M062 copy body is
executed by the checksum observer. It passes the shared zero case and fails both non-zero cases,
so the distinction is observed rather than asserted.

### Boundary

One successful transfer does not make the grammar or emitter endogenous. The checksum
decomposition, atomic effects and renderer remain authored. Repeating the same control pattern on
a third small loop cannot be justified as a new structural advance without removing another
handhold or entering the frozen completion experiment.

## D023 — A freeze candidate closes construction before it sees the canonical bank

M064's four development banks all pass the same four-arm, three-cycle whole-WebAssembly decision
rule. At that point another task, grammar production, control or threshold would not improve the
measurement; it would increase the number of ways the authors can adapt the experiment before a
claim.

### The rule

**Once an integrated experiment is declared eligible for freeze, its scientific construction is
closed.** The frozen parent may receive only documentation, guards and mechanically derived
commitments that do not change its generator, task bank, thresholds, substrates, budgets or
decision rule. A scientific correction after that boundary creates a new experiment number.

The canonical first result is the first artifact produced by the guarded marker commit. A rerun
is never a replacement. M064's Python 3.13 job is a reproduction: it consumes the preserved first
artifact and must match its bytes exactly. If it disagrees, M064 is not positive even if either
individual run looks favourable.

### Boundary

This decision freezes a bounded scientific protocol, not the engineering repository forever.
After the first result, documentation may preserve the artifacts, audit their identities and
archive the consumed workflow. None of those writes grants the experimental lineage repository,
network, credential, deployment or production authority.
