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

## D024 — A failed freeze qualification and a false rollback proof require a successor experiment

M064's first frozen-parent qualification passed 1,084 of 1,085 tests on both Python versions but
failed its source-identity guard because commitments were made from a Windows checkout rather than
canonical Git text bytes. That mechanical defect alone could be repaired without changing the
experiment. External review also found that the forced rollback compared the untouched saved
input to itself instead of verifying the state actually returned by a restore operation.

The latter is a scientific correction after D023's construction boundary. **M064 is therefore
closed as a negative pre-canonical qualification; no M064 marker may be created.** M065 may reuse
the exact task bank and decision rule, but must restore a distinct returned object from committed
pre-fault bytes, audit it and bind both the corrupt and restored digests. Its marker must also be
the first occurrence in path history and its first-result job must be impossible on workflow
reruns.

## D025 — Canonical marker identity follows canonical history, not every fetched ref

M065 marker commit `a517e6bb76e8476ab6aca8c0a68c5bcfc3501d57` was the first and only occurrence
of its path on `main`. Its workflow fetched complete history and then evaluated `git rev-list
--all`, which also traversed the pull-request branch where the same marker had first been authored.
The guard therefore counted two occurrences and stopped canonical run `31287477458` before a task
bank was selected. The first-result and reproduction jobs were correctly skipped.

### The rule

**A first-history canonical marker is unique on the first-parent history of the pushed canonical
head. Lateral branch, pull-request and other fetched refs are not canonical history.** The guard
must count `git rev-list --first-parent HEAD -- <marker>`, while the marker-only diff, exact parent,
message, frozen hashes and attempt-one checks remain mandatory.

This does not permit deleting and re-adding a marker on `main`: every change to that path along
first-parent history is counted and any total other than one is rejected. A permanent Git graph
test must demonstrate that a lateral same-path commit does not affect the canonical count and that
`--all` would have produced the M065 false rejection.

### Consequence

M065 is a negative canonical guard qualification and is never rerun into success. It selected no
bank and produced no scientific artifact. M066 is a governance-only successor: it may reuse M065's
unchanged engine, bank, budgets, thresholds, arms and decision rule, but receives a new protocol
digest, marker path and immutable first run.

## D026 — Positive bounded real-substrate completion closes the construction line

M066's unique run `31291899534`, attempt 1, passed its first-parent guard, produced one preserved
Python 3.11 result and reproduced those exact bytes independently on Python 3.13. The selected
whole-WebAssembly lineage accepted three cycles and passed 18/18 hidden observations; every
equal-budget control accepted zero and passed 0/18. The preservation audit binds all ten Genesis
completion gates without changing the raw result.

### The decision

**The bounded construction objective is confirmed on the CPython → Node ESM → whole-WebAssembly
path and the M043–M066 construction line is closed.** M067 may not be justified by more banks,
larger budgets, another authored task family, a deeper finite grammar, another small body or a
repeat of the same migration pattern. Those changes enlarge the instrument without removing a
new structural handhold.

A successor requires a separately stated, falsifiable research question that changes a material
assumption and has its own verification strategy. The parallel M045 measurement question remains
distinct and open; it is not a missing completion gate and cannot retroactively widen or weaken
M066.

### Claim boundary

Closure is scientific, not operational. The result remains bounded by its authored compiler,
block structure, grammar, task families, cases and resources. Repository writes, network access,
credentials, deployment and production remain human-controlled. No open-ended evolution, general
intelligence or consciousness claim follows.

## D027 — Adaptive embodiment begins only by removing the supplied target adapter

D026 forbids an M067 justified by more of the same construction. M067 therefore opens a separate
phase around a different handhold: previous real-substrate experiments knew the target ABI and
complete compilation route even when they discovered instruction effects.

### The decision

A body-contract discovery result is admissible only when the target interface returns no complete
descriptor, discovery consumes public source behaviour alone, hidden evidence is absent from the
discovery API and every public survivor is validated before representation selection. A uniform
procedure must cover the whole precommitted body class. Empty, corrupted and semantic-default
controls must fail.

M067's finite contract grammar and four-body bank satisfy this entry rule. They remain authored,
so the claim is bounded contract-blind re-embodiment. More bodies or a larger grammar do not justify
a successor; M068 would need to remove another structural assumption with a new falsifier.

Repository writes, networks, credentials and deployments remain outside the scientific lineage.

## D028 — The M068 target language is committed before its learner

M067's learner and descriptor-product body bank were introduced together. That is sufficient for a
bounded mechanism test, but it permits unconscious co-design between target and discoverer.

M068 therefore separates construction in Git history. The opaque runtime, body-bank commitment,
generic word bound, evidence split, controls and decision rule are committed first. The discovery
engine does not exist at that boundary. Its later commit may not modify the LF-normalised runtime
digest `d6090e20f1255674fc206bd6088c39ca8512b76c213c1236be7053f4d91b096c` or protocol digest
`2c9296b8232e2ff8b8a74cdb8bc0af6b724dcb324378be2ee3a33fe783ff22b7`.

This controls freeze order, not authorship. The targets remain authored inside Mira Genesis; M068
must not call them independently authored. A target change after the freeze closes M068 without a
positive result and requires a named successor.

## D029 — M068 closes the project-authored finite command-language step

Exact learner commit `f033ac70628e79550e6263ac2bb60a6769bca42e` follows the frozen target
commit without changing it. In development, one unchanged learner scanned the complete 37,448-word
language for every body, recovered four distinct complete adapters, passed all 12 hidden cases per
body and rejected every preregistered control.

### The decision

M068 is positive mechanism evidence that M067's named descriptor-product grammar was not necessary
inside this finite bank. The project-authored finite command-language step is now closed. M069 may
not be justified by more authored bodies, a larger alphabet, longer words or a wider finite scan.

A successor must cross a materially external interface or governed real software environment and
must include at least one incompatible-body refusal trial. The same reusable Mira agent must retain
least privilege, evaluator-owned success, bounded action budgets and tamper-evident evidence.

### Claim boundary

M068 does not complete G1 because its targets and resource bounds remain authored inside the
project. It supplies no multimodal grounding, cross-domain transfer, real-device competence or
human-hour autonomy. It cannot be described as arbitrary body adaptation, a universal compiler or
AGI, regardless of exact-commit qualification.

## D030 — M069 freezes a real-terminal task bank before its repair policy

D029 requires a materially real environment and incompatible-body refusal. M069 therefore moves
the reusable Mira loop into temporary real files and evaluator-registered host processes. Four
compatible tasks, one incompatible protocol, eleven supplied replacement statements, public and
hidden cases, resources and controls are bound before the policy exists.

The frozen protocol digest is
`2da6abe85d0830f32a67415f1e4faef3316bd1ab1cf3cb461799e3c9a85fb499`; the evaluator runtime
LF digest is `6e2d1e0c510a72b4634c7bdfffcab164f82d7349531177adaa23b572d0618639` and the private task-bank
commitment is `66b7c7ffe87ecbf5c9cc42d14850b122dd933aa6235647d8dcdf6887464061ed`.

### The decision

The later policy may materialize workspaces and invoke opaque public/hidden evaluator modes, but it
may not import or read the evaluator source. It must use the same candidate language and control
flow for every compatible handle, and it must refuse the incompatible handle before a write or
process action. A post-freeze task or evaluator change closes M069 without a positive result.

### Claim boundary

The governed body constrains paths, action schemas, environment, time and output; it is not a
container or VM and does not claim strong adversarial isolation. The tasks and complete finite
replacement statements remain project-authored. Even a positive M069 result is terminal-body
mechanism evidence, not broad software engineering, external-target evidence or AGI.

## D031 — M069 closes the project-authored governed-terminal step

**Historical decision, superseded by D037 for M069's verdict and gate attribution.** Its successor
ordering constraints remain useful, but its positive interpretation does not.

Exact learner commit `c603dd52c6484034de3a11a7c3c660335fda14b0` follows the M069 freeze
without changing its runtime, protocol or bank commitment. One unchanged policy repairs all four
compatible workspaces, each passes 3/3 hidden cases, and the incompatible task refuses after one
read with zero writes and zero processes. All ten preregistered controls pass and a second process
reproduces manifest digest `c5c807017f05788dc22d21f88192279b9f177b648403b2cc41ca149b25ff6289`.

### The decision

M069 is positive mechanism evidence for real filesystem/process affordances and calibrated
incompatibility refusal. The project-authored governed-terminal step is closed. A successor may
not be justified by more marker-based tasks, more complete candidate statements, longer finite
search or another trusted evaluator registered directly on the host.

The next accepted result must use tasks maintained independently of Mira Genesis and frozen after
the evaluated agent design. Any untrusted candidate execution must occur in an independently
configured container or VM, with evaluator-owned state checks, fixed resources, least privilege,
negative controls and preserved failed attempts. A public suite alone is development evidence;
stronger claims require a private uncontaminated split and independent reproduction.

### Claim boundary

M069 was judged here to move G1, G6 and G10 only to partial mechanism evidence. D037 later withdraws
that attribution. It contains no task-specific planner,
foundation model, multimodal grounding, learned cross-domain transfer, hour-scale autonomy,
external task authorship or adversarial OS isolation. It cannot support broad software-engineering,
general-agent or AGI language.

## D032 — M070 remains negative; M071 must fix transport before a fresh blind pair

M070 obeyed D031's ordering: the task-agnostic agent was frozen, a deterministic selection rule was
committed, and only then were two independently maintained Terminal-Bench 2 tasks selected. Harbor
realized `no-network` agent phases and evaluator-owned rewards. Both Mira trials and both `nop`
controls scored `0.0`; there was no Harbor exception, valid retry or task replacement.

### The decision

M070 is closed as a negative external development result. Its frozen files, pair and outcomes are
not repaired or rerun. The observed Windows `cp1252` stdin failure and descendant pipe retention
are agent-design failures because they prevented bounded decisions inside an otherwise valid
external evaluation.

M071 may correct explicit UTF-8 transport and whole-process-tree timeout enforcement, with direct
regressions, before any new target identifier is selected. It must then create a new design freeze,
new blind salt and fresh selected pair. M070's tasks may be used only as disclosed regression
material, never as M071's scientific threshold.

### Claim boundary

M070 proves that Mira can be connected to official external container evaluation while preserving
network isolation and external success ownership. It does not prove competence on either external
task, cross-domain transfer, general agency or AGI.

## D033 — The external-model line is epistemically separate from Genesis ownership

M070 added a named external model at the point where shell actions and their arguments are
proposed. That is an intentional operational dependency even though the Python package has no
model-provider dependency. It is incompatible with counting the proposal as lineage-owned under
the frozen Genesis Gate 2.

### The decision

The Gate 2 text is not amended. The original endogenous bounded-lineage track and the M070+
model-mediated governed-agent track are reported separately. Track B may test containment,
isolation, refusal, audit, transport and the competence of an explicitly named composed system.
Model capability and task reward may not be attributed to the Mira governance layer alone.

Every Track B protocol must name the model, interface, body, budgets, authority envelope,
evaluator, attempts and contamination boundary. A governance-layer capability claim requires a
direct invariant or an isolating baseline/ablation. Shared code and chronological continuity do not
satisfy endogenous ownership.

### M071 consequence

Before selecting targets, M071 must fix transport across all affected host-process paths, add
Unicode and descendant-process regressions, and freeze the whole model-mediated design again. Its
external score remains composed-system evidence and cannot advance Genesis Gate 2 or Gate 3.

## D034 — M071 passes the narrow external threshold; the next step must isolate or broaden

M071 followed D032 and D033. Runtime `0820ebc`, bridge `132476a` and their blob commitment were
frozen before selection. A one-draw rule excluded both M070 tasks and selected a fresh pair before
inspection. Execution protocol `31d3c7bd` fixed four single no-network trials.

Official rewards were `0.0` for SQLite and `1.0` for custom-memory; both `nop` floors were `0.0`.
There were no Harbor exceptions, retries or replacements, and the agent never claimed success.

### The decision

M071 is a positive external development result for the named composed system. The M070 transport
defect is closed, and the project now has one evaluator-accepted independently maintained task.
The score is not attributed to Mira governance alone and does not amend any endogenous Genesis
ownership gate.

Repeating more public Terminal-Bench samples with the same composition is not a distinct research
advance. The next accepted experiment must either include a causal baseline/ablation that isolates
the value of Mira governance or use a frozen private uncontaminated, materially cross-domain split
with independent reproduction. Ideally it must do both.

### Claim boundary

One of two public tasks passed. There is no two-domain transfer result, multimodal grounding,
hour-scale autonomy, continual learning, governance-layer causal effect, private holdout or
independent reproduction. M071 is not general-agent or AGI evidence.

## D035 — M072 closes the authored causal-governance question, not external robustness

M072 froze its hypothesis before the harness existed and bound the exact 48-scenario suite before
evaluation. Full governance satisfied every preregistered authority and audit invariant; matched
admission and audit ablations each failed 18 invariants supplied by the removed mechanism.

### The decision

M072 is positive qualified causal-mechanism evidence. It is sufficient to reject the claim that
Mira's authority admission and hash-chained audit are merely decorative under the frozen threat
model. Because the grammar and evaluator are authored and no represented action executes, it is
not sufficient to claim independent safety robustness or external competence.

The next phase may treat these two mechanisms as causally supported components, but must retain
their limits and test calibrated refusal or adversarial robustness separately. More scenarios from
the same authored grammar are regression coverage, not a phase advance.

## D036 — M073 crosses from external examples to a lineage-owned artifact only

M073 froze the training family, teacher requests, induction procedure, controls and holdout seeds
before any teacher response. Four single calls produced four valid repairs. The lineage induced a
single identifier-generalized AST capsule and committed it before holdout programs were
materialized. With the teacher removed, the capsule passed all twelve holdouts; unchanged-source,
memorizer and corrupted-teacher controls failed as required.

### The decision

The serialized capsule and its later structural bindings count as bounded lineage-owned mechanism
evidence. The external teacher's outputs, the repair objective, the induction algorithm and the
task family do not become lineage-owned retroactively. M073 therefore bridges the epistemic tracks
without completing Genesis Gate 2 or Gate 3.

Repeating alpha-renamed division repairs is not a distinct advance. The next accepted skill result
must broaden the learned representation and use private uncontaminated, materially different task
families with an independent reproducer. Refusal calibration from the preserved local draft may be
developed as a separately numbered M074 mechanism, never rewritten into M072 or M073.

### Claim boundary

M073 shows one example-to-artifact-to-holdout pipeline. It does not show general software
engineering, autonomous goal discovery, multi-domain transfer, long-horizon learning, safe
deployment, consciousness or AGI.

## D037 — M069's interface falsifier withdraws its positive qualification

A post-M071 audit established that M069 imported candidate code in the evaluator process holding
the complete `TASKS` object, including hidden cases. The policy could write arbitrary candidate
bytes and observe public-evaluator output, so admitted actions could transport that hidden evidence
back to the learner. Falsifier 10 inspected the learner text and did not test this interface path.

### The decision

The Phase 8 rule says an experiment stops without a positive verdict when hidden evidence is
reachable by the discovery API. The governed write/evaluate/output path is part of that API, so the
rule fires. M069 is reclassified as a **post-hoc disqualified development result (evaluator-
isolation falsifier)**. H15 returns to unresolved and M069 no longer advances a generality gate.

The historical rewards, repairs, refusal and manifest remain exact diagnostic observations. The
frozen learner is not accused of exploiting the path: its source audit finds no such behavior. No
frozen protocol, bank, evaluator, learner or result byte is rewritten.

### Successor constraint

Static inspection of generated code cannot substitute for non-reachability. Any successor that
executes candidate code must isolate it from the process holding hidden evidence and must test that
the admitted action surface cannot recover those bytes. A later corrected experiment receives a
new identifier and may not retroactively rehabilitate M069.

## D038 — M074 isolates refusal termination and qualifies only its apparatus

The preserved local draft mixed refusal termination, authority enforcement and ledger integrity in
three arms. M072 already supplies positive causal evidence for authority admission and hash-chained
audit. In the first repaired real-container dry run, the raw and governed-nonterminal arms produced
identical refusal outcomes, confirming that the extra arm added no information to M074.

### The decision

M074 uses two arms with identical authority admission, isolation, budgets and tamper-evident audit.
Only `refusal_terminates_episode` differs. Capability absence must be declared by exact return code,
certificates bind the exact probe and materialized environment, and every arm must cover every label.

The locally preserved zero-token dry run qualifies this apparatus for protocol design. It is not a
scientific result, does not support H20 and moves no generality gate. Its observed margin is a wiring
control produced by a scripted policy, not evidence about a model or Mira's general competence.

### Next boundary

Before any scientific execution, a separate commit must freeze code/task/environment digests,
model identity, prompt, budgets, numeric threshold and ordered single attempts. No model may receive
expected solvability, certificate verdicts or evaluator outcomes. Any retry, missing task,
`INCONCLUSIVE` probe, realized-isolation drift or feasible-control failure invalidates that attempt.

## D039 — M074 is a valid negative; refusal requires an explicit epistemic successor

M074 froze apparatus, thresholds, model, host/runtime identities and an exact paired A→B order at
commit `28ddd8b` before every scientific model decision. The commit passed first GitHub CI without a
rerun. The single campaign then completed all twelve episodes with zero protocol defect.

### The decision

H20 is refuted under its bounded threshold. The composed system completed 6/6 feasible arm
episodes and no impossible episode passed, but emitted zero refusals. Both arms therefore recorded
0/3 true refusals, margin 0.0 and twelve wasted impossible-task steps. The terminal-refusal switch
had no refusal event to terminate and saved zero steps.

The negative result is preserved and M074 is closed. It may not be retried, have its budget changed
or be reinterpreted through the successful feasible final states. Those states demonstrate bounded
execution competence, not capability-absence judgement.

### Successor constraint

A successor receives a new identifier. It may develop an explicit task-agnostic epistemic state —
including current/remaining budget, repeated-failure evidence and a calibrated stop decision — on
a separate public development bank. Its scientific threshold must then use private,
independently maintained, materially cross-domain capability pairs frozen after the policy. M074's
six public tasks may be regression tests only, never the successor's scientific threshold.

### Claim boundary

This failure advances no Genesis or generality gate and does not erase M071, M072 or M073. It shows
only that the frozen M074 composed system did not convert repeated capability failures into refusal
on three authored pairs. It is not evidence about mathematical impossibility, general safety or
AGI.

## D040 — M075 develops explicit self-evidence without turning it into an oracle

M074 exposed missing decision context: the model could inspect command output but was not given an
explicit remaining budget or compact record of repeated actions and persistent failures. That
diagnosis does not justify an automatic capability label or an in-place M074 retry.

### The decision

M075 adds only task-agnostic audited facts to the model request: budget position, return-code
counts, consecutive failure count, generic visible-output failure class, action-script SHA-256
diversity/repetition and prior refusal count. It neither receives hidden labels nor decides refusal
itself. Unknown failures remain generic non-zero outcomes, never certified absence.

A separate public development bank is openly contaminated and may be used to revise this context.
Its zero-token scripted result qualifies plumbing only. M074's six tasks are regression material;
neither bank may be the M075 scientific threshold.

### Scientific boundary

After development closes, a pre-private commit must freeze the unchanged agent and threshold. The
scientific bank must be private until then, independently maintained and materially cross-domain.
Exact paired control, false-refusal cost, evaluator-owned success, no retry/replacement and
independent reproduction remain mandatory. Until that boundary is met, H21 is untested and no gate
moves.

## D041 — M075's public signal closes tuning but does not open the private bank

The committed public comparison completed without defect. Relative to independent baseline
samples, explicit self-evidence moved true refusal from 0/3 to 2/3, introduced no false refusal,
reduced wasted impossible-task steps from 12 to 4 and made all three successful workspaces submit.
It still failed to refuse the read-only-write task despite three visible failures and one remaining
decision.

### The decision

The outcome is promising development evidence, not a threshold result. Mira preserves the miss and
stops tuning on this six-task bank. Selecting a stricter prompt after inspecting that task would
optimize the public counterexample rather than demonstrate transfer.

M075 does not enter private execution yet. The pre-private package must first specify a defensible
causal control for a model interface without a seed or provider snapshot, plus a sealed task-bank
intake whose maintainer is outside the policy-development path. If either cannot be established,
H21 remains open rather than being weakened. The policy, model, budgets, thresholds and single-
attempt rule must be frozen before any private task content is revealed.

The readiness boundary is executable: a closed signed envelope exposes only opaque domain/pair
counts and a payload digest; the private protocol must bind those exact bytes before reveal. The
paired unit is the task instance, run once per condition on fresh clones, with post-freeze condition
order and exact McNemar analysis. Until all inputs validate, the checker reports false without
accessing a payload.

### Claim boundary

The two public conditions used independent model samples, so their difference is an association,
not an isolated treatment effect. The authored public bank is contaminated. D041 advances no
generality or Genesis gate and provides no AGI evidence.
