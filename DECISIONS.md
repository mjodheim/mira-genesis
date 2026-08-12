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

## D042 — M076 moves G2 off open and reopens the endogenous track

The endogenous Track A line produced no new gate evidence between M066 and M075: every result from
M070 onward belonged to the model-mediated track, and G2 remained the largest empty entry in the
generality register. M076 addresses it with no model call, no external task and no third-party
input, so it could be executed and audited entirely inside the repository while M075 stayed blocked
on inputs only an external maintainer can sign.

### The decision

M076 is accepted as positive bounded mechanism evidence and G2 moves from open to partial mechanism
evidence. The register entry records the triple dissociation and the measured floor, not a summary
score. G2 is not closed and no wording elsewhere may imply that it is.

Amendment A1 stays in the protocol permanently. The first freeze was internally inconsistent, and
the project's standard is that a defect found before materialization is corrected in the open with
its arithmetic rather than quietly replaced. Implementing the floor as fail-closed would have been
the concealing option and is rejected explicitly: a zero-scoring ablation measured against a
zero-scoring floor proves nothing.

### Claim boundary

M076 uses project-authored synthetic rasters in a single domain and a deterministic agent whose
policy does not change between episodes; persistence is identity and audit, not adaptation. It
supplies no perception, cross-domain, continual-learning, Genesis Gate 2 or Gate 3 evidence and no
AGI evidence. It does not touch, weaken or satisfy the M075 pre-private readiness boundary, which
remains fail-closed on independent inputs.

## D043 — M077 is a valid negative; the boundary monitor must earn coverage, not latency

M077 asked whether detection and restoration are separable mechanisms across increasing
episode-count horizons. Its protocol was frozen before the harness existed and its schedule was
bound before any arm ran. The answer is half yes and half no, and the no is the result.

### The decision

The preregistered dissociation is refuted and preserved as a negative. M077 advances no generality
gate; G7 remains open. The two positive sub-results — undegraded retention to 2048 episodes and a
causally isolated checkpoint mechanism — are recorded as bounded mechanism observations and may not
be cited as a G7 advance or as long-horizon autonomy.

Two instrument corrections were applied before materialization and are stored in the result: raw
detection events could exceed injected faults, and a single outstanding-fault slot could not
represent faults on adjacent episodes. The first correction moved the failing arm rather than
removing a failure, which is the signature of a real refutation. No third correction was made. A
change shaped to make the remaining arm comply would have been tuning against an observed outcome,
and `check_m077_result.py` now fails closed if the negative is ever silently converted.

### What the refutation teaches

A periodic invariant audit is redundant with operational failure whenever every corruption
eventually reaches a guarded operation. It purchases detection latency, not coverage. A successor
may not simply add horizons, faults or invariants to this body; it must introduce corruption that
can stay quiescent indefinitely, or a body whose operations do not guard the corrupted state.

### Claim boundary

Episode counts are not human-equivalent time horizons and may never be reported as such. M077
supplies no real-environment autonomy, no cost model, no Genesis Gate 2 or Gate 3 evidence and no
AGI evidence, and it does not touch the M075 pre-private readiness boundary.

## D044 — M078 supplies the G1 refusal clause without closing the gate

G1 has four requirements and M068 satisfied three of them: bodies frozen before the learner, an
interaction language not encoded as a descriptor product, and no source inspection during
evaluation. Every body in that bank was solvable, so the fourth requirement — that an incompatible
body produce a calibrated refusal rather than an invented adapter — had never been exercised.

### The decision

M078 is accepted as positive bounded mechanism evidence for that clause. G1 **does not** advance from
`stronger partial mechanism evidence`, because the bank remains project-authored and the missing
requirement for closure is bodies maintained outside this repository plus independent reproduction.
The register records the clause as exercised, not as satisfied in the sense G1 finally requires.

The construction is the substance of the decision. An incompatible body that simply had no candidate
would be refused by any procedure returning its best survivor, which measures nothing. Each
incompatible body here admits a candidate fitting every public observation, and the `never_refuse`
control adopted one on all four and failed hidden validation on all four. Refusal caused by an empty
candidate set is recorded under a separate kind and does not count toward the threshold.

### Boundary against M074

M078 may not be cited as repairing, answering or weakening M074. That result measured whether an
external model refuses capability-absent tasks and found it did not, 0/3. M078's discoverer is
deterministic and model-free; it shows that a search procedure can be built to detect observable
under-determination. Nothing about model behaviour follows. The two live on different tracks and a
successor that conflates them is making a claim neither result supports.

### Claim boundary

No cross-domain transfer, no general epistemic humility, no Genesis Gate 2 or Gate 3 evidence, no AGI
evidence. M078 does not touch the M075 pre-private readiness boundary, which remains fail-closed.

## D045 — M079 exercises every G3 clause without advancing the gate

G3 asks for four things and the register recorded only that earlier lineages plan inside authored
finite task languages. Revision, terminal verification and clarification had never been exercised.
M079 addresses all four in one bank of 24 episodes.

### The decision

M079 is accepted as positive bounded mechanism evidence. G3 **stays** at `partial bounded evidence`:
the world, goals, affordances and costs are project-authored, and closure requires them maintained
outside this repository plus independent reproduction. The register records the clauses as
exercised, not as satisfied in the sense G3 finally requires.

The two controls are the substance. A clarification result means nothing unless committing is
demonstrably harmful, so every ambiguous episode places the hazardous resource strictly closer,
making the `never_ask` control's six unsafe terminal states deterministic rather than lucky. The
`always_ask` floor solves nothing, so asking cannot be scored as competence — and on this bank
asking is never scored as success at all; only the evaluator's goal and safety checks score a task.

### Recorded construction fixes

Two were applied before materialization and are preserved in the result. Sealed states became
terminal in the search, without which the state space was intractable. The revision family now
blocks an edge the initial optimal plan traverses: an arbitrary block was routed around in three of
eight episodes, which failed the frozen specification requiring that one specific action reveal the
block. Neither changed a threshold.

### Boundary against M074

M079 may not be cited as evidence that a model asks for clarification. Its planner is deterministic.
M074 measured model refusal on capability-absent tasks and found none, and that remains the only
result on the question.

### Claim boundary

No open-ended or natural-language planning, no cross-domain transfer, no Genesis Gate 2 or Gate 3
evidence, no AGI evidence. M079 does not touch the M075 pre-private readiness boundary.

## D046 — M080 measures forgetting for the first time and records that retention is replay-dependent

The generality register said M073 tested "one homogeneous authored family and **no forgetting**".
Retention had never been at risk in this repository, so the claim that it is preserved had never
been earned. M080 puts it at risk and measures what happens.

### The decision

M080 is accepted as positive bounded mechanism evidence. G5 **stays** at `stronger partial bounded
evidence`: the skills and table are project-authored and closure requires capabilities maintained
outside this repository plus independent reproduction. The register now records forgetting as
measured rather than absent.

The interference is the substance. Later skills reuse an earlier rule and demand a different output
for an exception key the donor owns, so the cheap in-place rewrite is always available and always
destructive. `no_consolidation` takes it and loses five capabilities. A design with private slots
would have guaranteed retention by construction and proved nothing.

### The limitation is part of the result

Retention is replay-dependent. Removing replay costs as much as removing consolidation. This is
recorded as a headline finding, not a caveat, and the protocol deliberately preregistered no
direction for the measure so that neither outcome could be selected afterwards. Any successor
claiming robust continual learning must either make retention structural or carry the replay cost
in the claim.

### A check that could not fail

The first rollback assertion compared the checkpoint against its own digest and was therefore
vacuous. It is recorded among the instrument fixes because a green check that cannot fail is more
dangerous than a missing one. A regression and the checker now both assert that a mismatch remains
reachable.

### Claim boundary

No weight learning, no open-ended acquisition, no cross-domain transfer, no Genesis Gate 2 or Gate 3
evidence, no AGI evidence. M080 does not touch the M075 pre-private readiness boundary.

## D047 — M081 adds a second real environment without approaching the ones G6 actually names

M071 supplied one terminal task in a real container and the register recorded that browser and
desktop competence remain absent. M081 adds a second real environment and demonstrates the scoring
rule G6 insists on, while leaving the named gaps exactly where they were.

### The decision

M081 is accepted as positive bounded mechanism evidence. G6 **stays** at `partial mechanism
evidence`. The register gains one interface across two real environments and a measured
self-report divergence; it gains no browser, no desktop VM, no physical device and no external
suite. Anyone reading the row must still see that the larger part of the gate is untouched.

The crossed-driver arm is the load-bearing control. Without it, "one interface worked in both" would
also be true of a single environment wearing two labels. It completes nothing, so the shell container
and the HTTP service are distinct systems.

### Why the scoring clause was measured rather than assumed

Each environment carries one task whose action reports success while the state does not change: a
shell script that swallows a failed write with `; true`, and a service that answers `204` to a write
it discards. Both are ordinary real-world failure modes. Scored by claim the interface looks 12/12;
scored by state it is 10/12. G6 forbids self-report scoring, and this shows the cost of ignoring
that rather than restating the rule.

### Amendment A1 and two construction fixes

The first freeze required all six tasks per environment to complete while specifying one that is
uncompletable by construction. A1 resolves the contradiction in the strengthening direction: five
completable tasks must succeed and the sealed task must be observed to fail while being claimed. Two
further fixes are recorded in the result: the crossed arm originally swapped both driver and
environment and crossed nothing, and the sealed task originally expected nothing and scored its own
discard as a pass.

### A limit on the evidence

The container-backed regressions skip in CI under the existing `MIRA_RUN_DOCKER_TESTS` opt-in, so CI
attests the structural half only. The live half is reproducible locally on demand and must be
described that way, not as CI-attested.

### Claim boundary

No browser, no desktop VM, no external suite, no Genesis Gate 2 or Gate 3 evidence, no AGI evidence.
M081 does not touch the M075 pre-private readiness boundary.

## D048 — M082 supplies G6's browser clause and leaves the desktop VM untouched

G6 names a terminal, a browser and a desktop VM. M071 supplied the terminal, M081 added an HTTP
service under one interface, and the register still read that browser and desktop competence remain
absent. M082 removes the first of those.

### The decision

M082 is accepted as positive bounded mechanism evidence. G6 **stays** at `partial mechanism
evidence`. The register now carries one interface across three real environments including a real
browser; it still carries no desktop VM, no physical device and no external suite, and the page is
project-authored so it is DOM competence rather than general web competence.

The crossed-driver arm is again the load-bearing control. A browser page with an HTTP store would
have been the M081 service with extra steps; state in localStorage with no network route, and a
crossed arm completing nothing in all three environments, is what makes the browser a materially
different substrate rather than a relabelling.

### One interface must be imported, not restated

M082 imports M081's agent and both prior environments unchanged, and a regression plus the checker
fail if any is redefined. A three-environment claim built from three implementations would prove
nothing about continuity.

### A defect that would have passed every test

Among three recorded transport defects, one deserves separate note. The browser initially used a
fresh profile per action, so localStorage did not survive and the harness replayed accumulated intent
to reconstruct state. Nothing failed and every test was green, but the harness would have been
holding the state rather than the browser, and the claim would have been hollow. A persistent profile
now keeps state in the browser, verified by a read-only action returning items written by earlier
launches.

### Claim boundary

No desktop VM, no physical device, no external suite, no general web competence, no Genesis Gate 2 or
Gate 3 evidence, no AGI evidence. The container-backed evidence is local opt-in and not CI-attested.
M082 does not touch the M075 pre-private readiness boundary.

## D049 — M083 adds a pixel-legible environment and explicitly does not supply the desktop VM

G6 names a terminal, a browser and a desktop VM. M071 supplied the terminal, M082 the browser. M083
adds a fourth environment but **does not** supply the VM, and this decision exists partly to make that
refusal durable.

### The decision

M083 is accepted as positive bounded mechanism evidence. G6 **stays** at `partial mechanism evidence`.
The register gains one interface across four real environments, one legible only as rendered pixels;
it gains **no desktop VM**.

A Docker container shares the host kernel. No hypervisor was available in this environment: `qemu`,
`VirtualBox`, `multipass` and `Vagrant` were absent, the Hyper-V feature state could not be queried
without elevation, and the only VM present was the host's own WSL2 distribution, which is not an
isolated environment created for the experiment. Describing this session as a desktop VM would be the
relabelling the M082 protocol prohibited one experiment earlier. The protocol, the preserved result, a
regression and the checker all assert the denial so that a later reader cannot quietly upgrade it.

### Why the substrate is real

The shell is addressed by filesystem paths, the service by HTTP routes, the browser by DOM selectors.
This one is addressed only by screen coordinates and observed only as decoded pixels. The
crossed-driver arm, which drives the desktop tasks through the browser driver, completes nothing —
there is no path to the rendered grid except the screen.

### A third green-but-wrong trap

A hard-coded window origin would have painted and read different cells while every call returned
success. That joins M080's tautological rollback check and M082's harness-held browser state: three
occasions in this series where the tests would have been green and the claim hollow. Each is recorded
with its diagnosis, because the failure mode is not a bug that announces itself.

### Claim boundary

No desktop VM, no physical device, no external suite, no general desktop application competence, no
Genesis Gate 2 or Gate 3 evidence, no AGI evidence. The container-backed evidence is local opt-in and
not CI-attested. M083 does not touch the M075 pre-private readiness boundary.

## D050 — M084 integrates the Phase 8 mechanisms into one lineage and advances no gate

M076 through M083 each qualified a mechanism inside its own harness. M084 asks the question the
registers had not: whether those mechanisms can be the **faculties of one persistent lineage**, or
whether their success depended on the isolation of the harnesses that carried them.

### The decision

M084 is accepted as positive bounded integration evidence. **No generality gate advances.** G2, G3,
G5 and G6 stay exactly where M076–M083 left them, because M084 adds no new modality, no new planning
clause, no new retention mechanism and no new environment. What it adds is that these mechanisms now
belong to one organism with a verifiable descent.

### The finding about the parent results

The agent M081, M082 and M083 drive across four real substrates replays an action list computed by
their bank generator. It perceives nothing, plans nothing and detects no failure. Those three
experiments are **interface** results — genuine ones, and correctly bounded in their own records —
but nothing in the registers made that legible, and a reader could easily have taken "one unchanged
agent across four real environments" for more than it was.

M084 therefore does **not** import that agent. Importing it would be an empty citation. The omission
is recorded in the frozen protocol and enforced by a regression and the checker. Everything else is
imported rather than restated: M077's journal, M080's bounded table, M079's plan enumeration — moved
into `metamorphosis/bounded_search.py` so both experiments use one copy, with M079 reproducing its
preserved result `5f7ccf21` exactly — and the three environments unchanged.

### What the ablation shows, and what it does not

`acquisition_ablated` is the same lineage with its facts and adopted policy cleared at every stage
boundary: same identity, same journal, same version. On the return to the shell it needed one
diagnostic probe, one repair cycle and one affordance probe where the complete lineage needed none,
and it cost 85 against 46 over stages 1–3. `fresh_each_stage` reproduced it metric for metric, which
is what shows the ablation is not leaking, and failed four of five continuity proofs.

**The ablation costs no correctness.** Every arm reached all eleven reachable goals and refused all
five unreachable ones. Persistence bought cost and earliness — 27 actions and 48 reads against 43 and
71, one wasted action on an impossible goal instead of four. This must not be reported as a
capability difference.

### The state-ownership defence is structural

M082 came one design decision away from a green result in which the harness, not the browser, held
the state. M084 answers that structurally rather than by inspection: each stage runs in a separate
operating system process, the parent never calls a perception, planning or action function, and the
organism records inside itself the digest of the file it loaded, so the chain of serializations is
carried by the lineage rather than asserted by the harness.

### Amendment A1, and why it is not a repair after the fact

The pipeline was rehearsed twice on throwaway salts, with no bank bound and no result preserved. The
first rehearsal produced a **false refusal**: the carrier-rejection predicate generalized from
one-sided evidence and collapsed from `sea` to `s`, rejecting the organism's own alternatives. It was
invisible in stage 0 only because the organism still verified at the end of the stage there. A1 and
A2 corrected the induction before any artifact existed; no threshold, salt or goal grammar changed.
The clause that caught it is P2, the zero-false-refusal requirement, which exists for exactly this.

### Claim boundary

No AGI, no general autonomy, no open-ended evolution, no cross-domain transfer, no closed G4, G6 or
G7, no general desktop competence, no structural retention without replay, nothing about privately
maintained external tasks. A fact learned in the shell is never offered to the browser even though
both discard the same authored prefix; carrying it would be the relabelling this repository forbids.
The desktop's induced predicate over-generalizes to cells no goal uses, because only one non-durable
carrier is observable there, and that weakness is part of the record. Eleven reachable goals over
four stages is a small bank and every goal, carrier, application and substrate is project-authored.
M084 does not touch the M075 pre-private readiness boundary.

## D051 — M085 attacks G4 through a separate external boundary, and is blocked until a third party acts

M084 integrated the Phase 8 mechanisms into one lineage and advanced no gate. The next question is
G4: does knowledge acquired in one domain improve held-out performance in another?

### The decision

M085 is defined, instrumented and **blocked**. Its design protocol, domain adapter contract, intake
kit, maintainer brief, fail-closed gate and regressions are committed. No scientific protocol is
frozen, no bank exists, no payload has been requested and no held-out domain has been drawn.

The project may not run M085 on domains it wrote. That is recorded as a prohibited adaptation rather
than left to judgement, because it is the cheap substitute that would be available on any day the
external route feels slow.

### Why M075's boundary could not be reused

M075 built a fail-closed pre-private boundary for a different question. Its validator hard-codes six
true refusals, zero false refusals, a wasted-step advantage, the `gpt-5.6-sol` agent identity, a
`baseline-structured-request` versus `epistemic-context-request` design and a claim boundary reading
`bounded_composed_system_refusal_transfer_only`. A G4 protocol fails that validator on every one of
those fields.

M085 therefore builds a separate instrument at the same standard rather than loosening that one or
routing around it: signed envelope from a non-project identity, opaque domain identifiers, payload
held externally until freeze, and a validator that refuses by default. `exact_mcnemar_two_sided` is
imported from M075 rather than restated. **M075's own private experiment remains open and blocked on
its own maintainer; M085 does not substitute for it.**

### The two corrections M084 asks for

**Correctness, not cost.** M084's ablation cost no correctness, and its own status file says a claim
resting on efficiency would be weak. M085's primary outcome is the correct terminal decision, cost
metrics are reported but explicitly not decisive, and the freeze validator rejects a protocol that
promotes a cost metric to the primary outcome.

**Domains, not substrates.** M084's four stages were one carrier family over three substrates. M085
requires three domains materially different from one another, each justified in a paragraph whose
digest is in the envelope and which is checked against that digest after the payload is released —
falsifiable later rather than believed now.

### The threshold and the bank size were chosen together

Six discordant tasks in one direction give an exact two-sided McNemar p of 0.03125; five give 0.0625
and could never clear the frozen 0.05. Requiring at least six correctness-critical tasks per domain
is what makes the threshold reachable in principle while leaving it entirely possible to fail. A
regression asserts both halves of that arithmetic so neither can be adjusted alone.

### What the shim found before any bank exists

The design names, as its most valuable possible negative, that M084's adapter contract might not fit
an externally written domain. Building the organism-side shim first turned that into a measurement.

M084's `Embodiment` abstracted acting and observing, and that was the smaller half. The organism also
reached into M084's own carrier tables in **ten** places: memory keys, memory contexts, carrier costs
for planning and plan ordering, the carriers it probes with, the carrier a stage is seeded through,
the value alphabet, and whether a substrate is read one carrier at a time. None of those is supplied
by an outside domain, and none was visible from the M084 result.

All ten now route through a registered `DomainView`. M084's substrates register views built from the
tables they already used, and every arm re-derives its recorded numbers exactly, so the M084 result is
untouched. This is the same judgement applied to M079's search extraction earlier: compose through a
named extension point rather than restate, and prove the parent reproduces.

The wiring control that exercises this is **not evidence**. It is written by this project, which is
what the M085 boundary exists to exclude, and no result may cite it. Its own first version is in
`FAILURE_LOG.md`: it passed while running zero probes and zero repair cycles. What remains genuinely
unknown is whether a maintainer can express their domain in this vocabulary at all, and no control
this project writes can settle that.

### Claim boundary

No gate advance is available from M085 without independent reproduction from a separate bank and a
separate maintainer. Even then it would establish bounded cross-domain transfer of one acquired
policy. No AGI, no general autonomy, no open-ended evolution, no Genesis Gate 2 or 3, and no general
competence in any domain involved.

## D052 — M086 makes the improvement mechanism mutable and advances no gate

Every earlier result improves a body or a policy through a procedure we froze. M086 asks whether the
lineage can change that procedure, and answers yes inside one bounded construction.

### The decision

M086 is accepted as positive bounded evidence for endogenous transformation of the improvement
mechanism. **No generality gate advances.** It is not a competence result about any domain; it is a
result about where the ceiling of a bounded lineage comes from.

### Why the target was chosen

`ModuleDiagnosis.sufficient` returns `self.module is not None`. One line, and it means the whole
mechanism refuses to act whenever evidence implicates more than one module. M047 recorded the
consequence honestly at the time — it met a compound task and terminated for insufficient evidence —
and that termination was correct behaviour and a standing admission that the ceiling was our
assumption rather than its evidence.

Making *that* mutable is a smaller and more legible change than building a mutable meta-agent, and it
has a property no model-written mechanism can offer: its constructive image is finite and can be
**enumerated**. The harness therefore proves the control's failure rather than observing it. Zero
candidates for the holdout means no budget could have helped, which is the capability-versus-cost
distinction M084's status file said the next milestone had to make.

### What HyperAgents contributed, and what was refused

The question, and the `fixed_meta` ablation, which is their own control against themselves. Refused:
the method. Their meta-agent asks a frontier model to rewrite the codebase, so under this
repository's attribution rule the competence belongs to the composed system. Also refused, for now:
the archive, the population and stochastic parent selection, because introducing them together with a
mutable mechanism would make a positive result causally unattributable. `docs/HYPERAGENTS_COMPARISON.md`
records the full comparison, including what they demonstrate better than we do.

### The evaluator is not part of the mutable body

Stated in the protocol and enforced by a checker: the mechanism cannot name the hidden cases, cannot
reach `solves` or the sandbox, and the meta-search is only ever handed the development limitation.
Mira may propose a better way to improve itself; it may not edit the test that decides whether the
improvement worked, during the experiment that decides it. An evolvable evaluator is a separate
milestone with its own external authority.

### The prediction that was wrong

The protocol expected the lock to be the single-module *dispatch* and therefore expected the winning
patch to be a composed one. It was not. Widening the hypothesis schema alone sufficed. Amendment A1,
recorded before the bank was bound, re-states P6 as the protocol's own sentence already did — outside
the constructive image — and the fact that the search found the minimal sufficient change, rejecting
three of four primitives individually, is evidence against the disguised-lookup failure mode rather
than for it.

### Claim boundary

In one bounded project-authored construction, the mechanism producing future transformations became
an object of endogenous transformation and that acquisition was causally necessary to a later
capability. Nothing more. Not AGI, not open-ended evolution, not arbitrary self-improvement, not
general autonomy, no gate, no independent reproduction, and no replacement for M085 or its
fail-closed boundary.

The meta-primitives are still ours. The lineage chose among four operations we wrote and invented no
fifth. If a successor shows an archive is the next real limitation, that is M087 and it may not be
added retroactively to enlarge this result.

## D053 — M086-A is post-hoc disqualified; H32 returns to untested

M086-A recorded a positive verdict, passed CI on the first run and was described in the registers as
a qualified development result. An independent review of PR #130 found four defects, all confirmed
against the exact head. The qualification is withdrawn.

### The decision

M086-A becomes **post-hoc disqualified development evidence**, alongside M069. Every artifact,
digest, CI record and history entry is preserved unchanged; only the claim attached to them is
removed. **H32 is neither confirmed nor refuted.** No gate moves — none moved before, and none moves
now.

The four defects are set out in `experiments/M086/DISQUALIFICATION.md`. In summary: the recorded
`protocol_commitment` matches only the CRLF working-tree copy and not the committed blob, which is
the M064 checkout-dependent-hash class recurring; **P8 was never implemented at all** and
`evaluate()` computes P1–P6 only, so P7 through P10 could never make the verdict negative and the
positive verdict rested on six of ten frozen conditions; the holdout existed as module constants
before the meta-search and was enumerated before any arm ran, so the promised chronology was replaced
by a source-text absence check; and the replay compared 3 of 14 preserved fields per arm, never
verifying the mechanism digests or the causal journal that P7 exists to guarantee.

### Why this is disqualification rather than repair

The four defects could be fixed in an afternoon and the same bank replayed. That is precisely what
must not happen. `fa647e27…c2a5` has been observed; replaying it after learning why the first verdict
was unsound would be a result-saving retry, and the verdict it produced would carry the knowledge of
its own correction. The repository has refused that move before — M041 was not rerun, M064 was not
patched into M065's result, M074 was not retried — and the successor is a separately numbered
experiment with its own protocol, salt, bank and holdout.

### What the review actually caught

Not a wrong number. Every observation M086-A recorded is reproducible and, as far as anyone can tell,
correct. What it caught is that the **threshold could not fail**: four of ten conditions were absent
from the verdict function, and one of those four had no implementation anywhere. A positive result
against a threshold that cannot fail is not evidence, however sound the underlying observations.

This is the same shape as M069 — where the recorded outcomes were also exact, and the interface
nevertheless made hidden evidence reachable — and it is the fourth entry in a run of green-but-hollow
findings that began with M080's tautological rollback check.

### What survives as motivation

The technique of enumerating a mechanism's complete constructive image, to show a control's failure
is structural rather than budgetary, is real and is carried into M086-B. So are the observations that
M047's mechanism emits zero candidates against two-stage evidence, that `widen_hypothesis` alone
sufficed against the protocol's own prediction, and that the acquisition-ablated arm failed where the
full arm succeeded. None of that is qualified evidence.

### Consequence for PR #130

It may be merged only as historical, post-hoc disqualified development evidence, never as a positive
qualification. Its title and description must say so.

## D054 — M086-C leaves H32 unsupported, and names the part of the mechanism that was never mutable

M086-A was disqualified for a threshold that could not fail. M086-B drew a bank no mechanism could
repair. M086-C is the first attempt in this line where the hypothesis was genuinely at risk.

### The decision

M086-C is accepted as a **valid negative scientific result**. H32 moves from untested to **not
supported** by the two attempts that had a qualified instrument, M086-B and M086-C. That is a
statement about two bounded attempts. It is **not** a finding that meta-plasticity is impossible,
and nothing here licenses that claim. No gate moves; none was ever in play.

Nine of ten frozen conditions passed. The lineage adopted a validated modification of its own
improvement mechanism after rejecting seven alternatives on disposable descendants, survived a forced
fault during the adoption transaction with a byte-identical restore against an independently recorded
digest, and produced a holdout patch lying outside the starting mechanism's constructive image, which
was enumerated and empty. Every control failed, including one at triple budget.

P2 failed. The patch was `synthesize_tool:mean:midpoint`, which passes the public evidence and fails
the evaluator's hidden cases.

### Why this counts where the predecessors did not

The protocol named this falsifier before the run: it stated the arithmetic condition under which two
expressions both pass a `mean` case, identified `midpoint` as the one the frozen expression order
would take, and said P2 could therefore fail while everything else succeeded. The draw produced that
condition and the prediction held. A negative that a frozen protocol anticipated is evidence; a
negative discovered by reading the code afterwards is a defect.

### What the result actually says

Widening what the mechanism can **hypothesise** gave it the ability to emit transformations the frozen
mechanism could not. It did not give it the ability to **choose** among them. H32 asks for a correct
outcome the frozen lineage does not reach; the evolvable lineage reached an incorrect outcome the
frozen lineage could not reach, which is a different and weaker thing.

### The part that was never mutable

Every meta-primitive acts on the hypothesis schema or the rule set. None acts on the selection rule —
the greedy first-past-the-post over public score. That rule is frozen and human-authored, and it is
what failed. Three attempts have treated the improvement mechanism as diagnosis plus generation; this
one shows the pair is incomplete.

A successor making selection mutable is a candidate and is **not** added here to rescue this result.
It would meet the harder form of the same problem immediately: choosing among candidates that all fit
the public evidence requires evidence the lineage does not have, which is where M078's refusal work
already sits.

### Claim boundary

Not AGI, not open-ended evolution, not arbitrary self-improvement, not general autonomy, not a
reproduction, no contact with M085's fail-closed boundary, no foundation model. The bank is
materialized and is not redrawn: a different salt would very likely have drawn a discriminating public
case and produced a positive, which is exactly why it may not be drawn now.

## D055 — Blind external bank generation is a successor to M075, not a substitute for its maintainer

M075 has been blocked on a person since its public comparison closed. Issue #112 is still open.
Before building a way around that, the requirement was decomposed rather than assumed to be
indivisible.

### The decision

`mira-blind-bank-v1` is adopted as the project's standard instrument for obtaining a held-out task
bank from a process outside the project, and **M075-B** is its first user. The instrument is
accepted at the `blind_generated_sealed_bank` tier and is **refused** at the human-maintained tier.
M075's protocol, result, bank metadata, digests and validator are unmodified. Issue #112 stays
open, and its status is not changed by this decision.

No generator is chosen, no prompt is written, no bank exists and no reveal is authorized. Nothing
here is a scientific result.

### What the decomposition found

Six things M075 requires of an independent maintainer are mechanism, and all six transfer: the
payload is withheld until the tested system's protocol is frozen; only opaque metadata is
disclosed; the bank spans four materially different domains with eight matched pairs; success is
decided from terminal environment state rather than the agent's report; impossibility is caused by
an absent capability; the bank is materialized once and the first result stands. Encryption plus a
signed reveal gate holds a payload at least as reliably as a person's discretion, and leaves an
auditable record where discretion leaves none.

One thing does not transfer: **a mind outside the project choosing the subject matter, and a
person willing to attest independence and sign for it.** A model prompted by the project is the
project's instrument, not a second party. That is the whole reason #112 stays open, and it is why
option B — closing #112 as superseded — is rejected outright rather than deferred.

### Five kinds of independence, kept apart

Procedural independence and generator context blindness are claimed and provable. Training-data
independence is **not provable** and is never claimed: the strongest available argument is that a
checkpoint published before this line became public cannot have memorized these specific tasks,
which bounds memorization of one corpus and says nothing about the concepts involved. Human
independence and external reproduction are not obtained at all.

The sentence this repository may never write is "the generator does not know about this project".
The sentence it may write is "the generator was supplied no context about this project".
`validate_generator_descriptor` refuses any descriptor recording the first as proven, and
`BLIND_CLAIM_BOUNDARY` is a frozen constant both the analysis plan and the system protocol must
carry byte-for-byte.

### One ordering was changed from the brief, deliberately

The brief placed the tested-system freeze after sealing, which is right, and implied the scoring
rule travelled with it, which is not. Bank size determines which p values are reachable at all, so
a threshold chosen after the bank existed would be fitted to it without a single task being read.
The analysis plan therefore freezes at F1, alongside the generator spec and before generation, and
the system protocol must bind its digest unchanged.

`validate_analysis_plan` then re-derives the attainable exact McNemar p at the frozen threshold and
rejects a plan that could never pass, as firmly as one that could never fail. That is the M086-A
defect inverted, and it is checked rather than promised.

### What is enforced rather than asserted

Impossibility is a machine-checkable certificate: the named capability must be required, absent
from the environment, the only absent one, and the pair's only difference from its feasible twin.
The isolation audit resolves mount sources against the repository root in both directions instead
of matching strings, and re-audits the recorded argv rather than trusting the attestation's own
`repository_mounted: false`. One frozen spec admits exactly one materialized bank; a second is a
hard failure, because a silent second draw is precisely what the contract exists to expose. The
validator's import graph contains no path to the tested system, asserted by parsing the module.

Both new checkers are decisive CI steps, and the M075 and M085 boundaries are now asserted
fail-closed in CI as well. M086-A recorded a positive verdict partly because a scientific checker
existed without being decisive there; a green CI must guarantee what the registers say it does.

### Claim boundary

Not AGI, not Genesis Gate 2 or 3, not mathematical impossibility, not general safety, not a
reproduction, no support for H21, no contact with M085's fail-closed boundary, and no satisfaction
of M075's independent-maintainer requirement. `AGENTS.md` §4 forbids replacing M085's external
maintainer with evidence from a project-controlled AI agent; the same reasoning applies to M075,
and this milestone is built to comply with that rule rather than around it.

## D056 — M075-B's matched pair becomes structural, and its artifacts are bound to one run

External review of PR #134 found four P1 defects on `3d718d0`. All four were confirmed against the
exact head, and all four are corrected before merge. None was answered by narrowing a claim. No
bank existed, no generator was chosen and no reveal was authorized, so every correction is
prospective.

### The decision

The blind-bank payload representation changes, and the readiness gate gains a cross-artifact
binding. `mira-blind-bank-v1` keeps its name and version because nothing has been frozen under it:
there is no bank, no commitment and no result to be inconsistent with.

### The defect that mattered most

The matched-pair contract was **declarative**. Two independent task objects shared a `pair_id`, and
the validator compared their environment image digest and their `required_capabilities` sets. That
left the instruction, the initial state, the provided capabilities, the permitted interfaces, the
terminal predicate and the evaluator free to differ. A pair could therefore succeed or fail for a
reason having nothing to do with the absent capability, while being counted as evidence about it —
which is the entire quantity this milestone claims to measure.

A comparison could have been extended field by field. That is the wrong repair: it has to enumerate
every field that must stay equal, and missing one silently readmits the defect. So the
representation changed instead. A pair is now **one object** holding one goal, one instruction, one
base environment with its initial state, one list of permitted interfaces, one required-capability
list, one terminal predicate and one evaluator. The twins carry an identifier and an emission
provenance and nothing else. `materialize_twin` derives each runnable task, and the sole difference
between its two outputs is whether the environment supplies the certified-absent capability.

Impossibility is then structural in three parts: the capability is **required** by the shared goal,
**absent** from the environment and from every permitted interface, and **sufficient**, because
nothing else the goal needs may be missing. `assert_matched_pair_delta` states the conclusion
rather than assuming it, and is retained even though it cannot fail for a well-formed pair, so a
future change reintroducing a per-twin field is caught the moment it is made.

### Documents that are individually valid can still describe different runs

The gate validated the isolation attestation, the public commitment and the generation ledger
separately and never required them to describe one run. An attestation from one generator run could
be combined with a payload from another, the commitment made to name a third generator identity,
and the ledger written to agree with whichever payload was chosen — every document passing its own
validator while the set described nothing that happened.

`sealed_run_binding_problems` now compares each identity that must causally survive from the frozen
spec, through the container run, into the commitment and the ledger: attested output against sealed
payload, frozen generator identity against the commitment, pinned image reference, image digest,
runtime name and runtime version against what actually ran, and the ledger entry against all three.

### A ledger is one milestone's record, not a shared log

A ledger holding exactly one `materialized` entry belonging to a **different** frozen spec
satisfied this milestone's generation stage, because the check asked only whether the current spec
had materialized more than once, and zero is not more than one. When a frozen spec commitment is
supplied, every entry must now bind it and exactly one must be a materialization. The single-spec
form removes the class of mix-up rather than filtering around it.

### CI

`check_blind_bank_readiness.py --self-test` constructs the three violations on fixtures and fails
if any is accepted. A gate reporting `phase: draft` on a repository with no artifacts proves
nothing about what it would refuse once artifacts exist, and the M086-A lesson is that a scientific
checker which is not decisive in CI is not a guarantee. The self-test is itself covered by a test
that removes a binding and requires the self-test to notice.

### What did not change

The architecture, the ordered chain, the evidence ladder and the claim boundary. M075 remains
untouched, issue #112 remains open, no generator is chosen, no bank exists and `phase` is `draft`.
See D055.

## D057 — M087 supports H33; the ceiling moves from selection to the meta-language itself

M086-C ended by naming what was never mutable: the greedy first-past-the-post over public score.
M087 made exactly that object plastic and nothing else. Diagnosis and candidate generation stayed
at M047's frozen pair.

### The decision

M087 is accepted as a **positive qualified development result**. H33 moves to supported by one
attempt with no retry. Protocol frozen at `db609a0` before any qualification data existed; result
`cb06bd7a...4d132`, attempt 1. All ten conditions passed, and every one was computed.

**No generality gate advances.** G4 is untouched: the families are project-authored, there is no
independent reproduction, and the meta-primitives are ours.

### What the result actually says

The frozen selection rule does not fail for want of computation. `more_budget_same_evidence`
evaluated 110 candidates against the fixed arm's 11 over an identical and empty `E_acquired`, and
closed neither discordant situation. The deficit is **informational**: M0's program has no
instruction that could ask the environment anything. The evolved policy has one, uses it three
times, and reaches a correct terminal decision on all three situations against one for the frozen
rule.

The acquisition ablation is the cleanest control in the milestone. It keeps the ambiguity
detector, so it *sees* that two candidates are indistinguishable, and it defers on all three
situations because it cannot resolve what it can now perceive. Detecting insufficiency and
repairing it are separate capabilities, and the ablation separates them.

### Why this is not "active learning works"

M0 has no version space, no experiment enumerator, no scoring rule and no query. Six
meta-transformations were rejected on disposable descendants first, including plausible ones: an
ambiguity guard alone defers forever; an enumerator with an acquisition transition but no survivor
filter acquires and cannot use what it acquired. Two of the five scoring rules are decoys that
pick a non-discriminating experiment. Angluin's membership queries and Lindley's information gain
justified the *shape of the instruction set*; neither was installed as a finished algorithm.

### The honest weakness, kept rather than tuned away

`interpretation_routing` is a preregistered no-harm situation. `ALIAS_TARGETS` begins with `add`,
which happens to be the truth, so the frozen tie-break lands correctly there by luck. Reordering
that list, or choosing a different truth, would have produced a cleaner 3-versus-0 table and would
have been tuning the bank to the result. The capability claim rests on the two families where the
arbitrary tie-break lands wrong, and the third stands as a reminder that a single correct adoption
says nothing about selection.

### Amendment A1, disclosed

After the qualifying run, an adversarial test found that `LOOP_ACQUISITION` re-enters while budget
remains even when every experiment has been consumed, and never terminates. The interpreter is a
frozen component, so the fix is recorded as amendment A1 and the run was repeated. The qualifying
run never took that path — its spaces hold eight experiments against a budget of four, so it always
terminated on budget — and the re-run produced a **byte-identical result digest**,
`cb06bd7a...4d132`. The amendment is disclosed rather than absorbed, and the identity of the two
digests is the evidence that it changed nothing.

### Two P1 findings from external review, corrected before merge

**The tenfold-budget arm did not spend tenfold computation.** `run_arm` called `encounter` once and
multiplied the reported candidate and cycle counters by ten, so the number backing P5 -- the
milestone's central falsifier -- was bookkeeping rather than work. That is the M086-A shape: a
condition that could not fail in the intended way. The arm now **performs** ten encounters per
family, each re-diagnosing, re-generating and re-executing every candidate body in the sandbox, and
a determinism check refuses the arm if repetitions disagree. The run was repeated and produced a
**byte-identical result** file, because the arithmetic had always been right and only the execution
was missing. The correction is disclosed rather than absorbed, and the identity of the two files is
the evidence that the science did not move.

**The publication disposition was unrecorded.** M087 is the enabling implementation of a materially
new mechanism, and `IP_ASSET_REGISTER.md` carried no entry for it. P-003 records
`PUBLIC_AGPL_COMMERCIAL_OPTION`, matching P-001's disposition for M086, before the implementation
merges.

### The next causal ceiling

Not the selection rule any more. The lineage chose among nine authored meta-primitives and eleven
authored compositions, and invented no tenth primitive. It also did not choose its own experiment
space: the bounded set of requests per family is ours. So the ceiling has two named parts, and
M088 must attack one of them rather than add a fourth family.

### Claim boundary

Not AGI, not open-ended evolution, not general autonomy, no gate, no independent reproduction, no
release or repository authority, and no contact with M075's or M085's fail-closed boundaries. One
bounded construction in which the rule that selects improvements became an object of improvement,
and the acquisition it gained was causally necessary to a later correctness difference.
