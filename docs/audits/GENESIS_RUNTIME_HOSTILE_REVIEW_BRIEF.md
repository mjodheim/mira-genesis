# Genesis runtime — hostile review brief

**For an independent reviewer. Prepared by the agent that wrote the runtime, which is why this is a
brief and not a review.**

The `genesis/` package (nine modules, ~2400 lines) and the 183 tests that validate it have one
author. The same author wrote the demonstration those tests assert on, and the record the
demonstration emits. There is no epistemic separation anywhere in that chain. Everything below is a
request for the separation the author cannot supply for himself.

Requested output shape, following `M125_DESIGN_CORRIGENDUM_HATI_2026-09-06.md`: numbered blocking
corrections with severity, an explicit required-test delta, and a disposition. `NO-GO` is an expected
outcome, not a failure of the review.

## What is being claimed, exactly

`docs/METAMORPHOSIS_TARGET.md` states the objective and the stopping criterion. The runtime claims to
be an executable program in which **one lineage** measures itself, diagnoses itself, transforms
itself, verifies the transformation, adopts or rejects it on evidence, keeps what it learned, extends
the machinery enabling later transformations, changes substrate, and evolves again in the new form.

`experiments/GENESIS/DEMONSTRATION_DEFINITION.md` states the twelve properties a run must exhibit and,
separately, which of them are driven to their negative in the test suite. **Read the definition before
the record.** If a property is defined so that it cannot come out false, that is a finding regardless
of what the record says — M121 v2 passed 76 tests while being unable to return a negative.

Three things are **not** claimed, and a review that refutes them refutes nothing:

- no AGI claim, and no claim about generality (see `docs/METAMORPHOSIS_TARGET.md`, "generality
  validation");
- no scientific result. `experiments/GENESIS/DEMONSTRATION_RECORD.json` carries
  `is_a_scientific_observation: false` and `advances_a_generality_gate: false`, and the bodies in
  `genesis/development_bodies.py` are fixtures;
- no claim that the mechanisms are novel. Each generalises something M107–M111 did once; see
  `docs/GENESIS_PRIMITIVE_AUDIT.md`.

The claim under review is narrower and load-bearing: **that these mechanisms hold as properties of a
running program rather than as properties of how the author wrote the fixtures.**

## Do not defer to the author

The author will read this and act on it. Two consequences:

- do not soften a finding because the code looks careful. It looked careful in the nine places it
  was already wrong (below), and it looked careful in M121 v2 while being unfalsifiable;
- the author's own found-and-fixed defects are not evidence he found the others. They are evidence of
  what class of mistake he makes, which should tell you where to look next.

## Defects the author found in his own work — verify, then go past them

Each was found by applying an attack list to the runtime after writing it. Each is fixed and tested.
The point of listing them is that they share one shape, and the reviewer's first job is to decide
whether that shape recurs somewhere still unfixed.

1. **Declared limits nobody applied.** `Isolation.filesystem_writes_permitted`,
   `network_permitted` and `subprocess_permitted` were declared, checked by `assert_no_wider_than`,
   and reported in the sandbox result — while applying to nothing. A candidate could write, resolve
   names and fork, and the record said it had not.
2. **A guard written against the convenient spelling.** The first fix inspected `open`'s string mode
   only. `os.open(path, os.O_WRONLY | os.O_CREAT)` reports mode `None` and carries intent in flags,
   and went straight through. So did `os.remove`, `os.rename`, `os.mkdir`, which never call `open`.
3. **A limit whose enforcement call succeeds and does nothing.**
   `resource.setrlimit(RLIMIT_NPROC, (0, 0))` returns successfully here and does not prevent a fork.
   The result had listed `subprocess_permitted` as enforced on the strength of that return value.
4. **The verdict relabelled as a causal ablation.** The demonstration's causal step compared the
   candidate arm against the parent arm — the two arms the acceptance verdict had *just* compared —
   and called the difference evidence of causal dependency between generations.
5. **A hash chain that carried the stored digest forward.** `journal.verify` advanced the chain with
   each record's stored `entry_digest` instead of the recomputed one, so tampering with an entry
   broke that entry alone and not everything after it.
6. **Instrument failure scored as candidate failure.** A child process that could not start produced
   `error` rows indistinguishable from a body that genuinely failed.
7. **The migration checked what the lineage recorded, never what it could do.** `carried_intact`
   compares components, certificates and acquisitions across a substrate change; nothing compared
   what the arrival could still *do*. A translation could drop every capability and the record would
   say nothing was lost, because nothing being counted had been — and this was live in the
   demonstration, whose migrated body solved half of what its pre-migration body solved.
8. **A permanent obligation of the runtime that the runtime did not have.**
   `ablation_supports_causal_dependency` existed as a function and `loop.py`'s docstring called the
   check a permanent obligation of the runtime — while the only thing calling it was the
   demonstration script. Any other driver of the loop got no check at all. The cycle runs it now,
   proposals carry their ablation arms, and `causal_chain` counts the links that were actually
   established.
9. **Half the refusals had never been exercised.** Defects 1–8 were found by reading the code
   adversarially, which finds only what the reader thinks to look for. Asking the question
   mechanically — `scripts/check_genesis_guards_are_tested.py`, which deletes each `raise` in turn
   and reruns the suite — found **35 of 68 guards surviving**, at a moment when 110 tests passed.
   33 were then tested, and with the probe and migration guards added the checker now reports **69 of 73
   killed**; the four survivors are marked in place as defensive assertions and are discussed under
   attack 7 below.

The common shape: **a record that testifies to a property the code does not have.** Assume it recurs.

## The attack surface, in the order the author considers it most dangerous

### 1. Results true by construction

The fixtures are the author's. He chose what each body solves. Ask of every claim in
`DEMONSTRATION_RECORD.json`: could this have come out otherwise?

Specifically:

- the migrated bodies route their later gains through the components that produced them, so an
  ablation has something to remove. That is the author building the dependency he then measures. He
  has put in a negative control — `migrated_uncoupled_ablation_body`, driven by
  `test_an_ablation_arm_that_is_really_the_parent_establishes_nothing` in
  `tests/test_genesis_loop.py` — and the question is whether that control is genuine or decorative.
  **Is there any body the author could plausibly have written for which `established` comes out
  `True` when it should not?**
- the cycle checks that the ablated arm is not behaviourally the parent, and nothing else about how
  the arm was built; that it is the candidate minus exactly one capability is checked separately, in
  `test_each_ablated_arm_is_its_candidate_minus_one_acquisition`, by comparing the two bodies field
  by field. Is that pair of checks sufficient, or can two bodies satisfy both and still not stand in
  the relation of candidate and ablation?
- `metamorphosis_succeeded` is false until the migrated lineage accepts a new candidate. Is
  "accepted a candidate after migration" actually the thing that separates transported intelligence
  from transported output, or is it a proxy the author chose because his fixtures satisfy it?
- the demonstration now runs **two consecutive ablations** and calls the pair a chain. Two links is
  the smallest number that can be called a chain at all. Say whether two is enough to mean anything,
  or whether the author picked the smallest number that lets him use the word.

### 2. Checks that reread a boolean the runner wrote

Trace every boolean in the record back to what produced it. The author believes the trust root
(`genesis/trust_root.py`) recomputes verdicts from raw per-task outcomes and never reads a
self-reported score — `LyingBody` and
`test_a_candidate_cannot_win_by_reporting_a_summary` exist to prove it. **Find the path that
bypasses that.** In particular: does anything downstream of `cycle()` consult a field that a
candidate could influence?

### 3. Data a candidate can reach that it should not

The sandbox spawns a child. `RecordBody` deliberately re-imports `genesis.development_bodies` inside
the child to rebind substrate operations. That is an import of project code *inside the candidate's
process*. What else is importable from there? Can a candidate read the journal, the task oracle, the
parent's state, or the file the demonstration writes? The audit guard blocks writes; it does not
block reads.

### 4. Authored ceilings disguised as system properties

`docs/GENESIS_PRIMITIVE_AUDIT.md` names three. All three are now claimed open, and the third was the
one that made the first two suspect, so read this section as one claim rather than three.

The lineage names a component class against an exhaustion certificate
(`genesis/probe.py`, `certificate_from_experiment`) and extends its diagnostic vocabulary against a
measured confusable pair (`vocabulary_certificate_from_experiment`). Both certificates now rest on
**experiment**: the lineage composes sequences of primitive operations, runs them in the sandbox at
budget cost, and the verdicts are tallied from raw per-task outcomes. The oracle-backed module that
preceded this (`genesis/diagnosis.py`) was deleted rather than kept, so there is no path back to a
certificate licensed by a callable.

The claim is that the host supplies the alphabet and not the sentence. **Attack that claim.**
Specifically:

- the host chooses the operation registry, the task sets, and the component→operations partition.
  Is that partition doing the work? Construct a partition under which the finding is forced either
  way, and say whether the author's partition is meaningfully different from that;
- `COMPONENT_OPERATIONS` is a host mapping that decides what each component can reach. It is not
  derived from anything in the lineage's state. Is a component that *is* nothing but a host-declared
  operation set a component at all, or a relabelling of the host's partition?
- the vocabulary's "limiting component" is defined as the held component supplying most of the
  resolving composition, with ties refused. That definition is the author's. Is it a measurement or
  a convention that happens to give the answer he wanted? What would a different but equally
  defensible definition do to the pair?
- the separating feature is `requires_<operation>`, taken from the symmetric difference of the two
  resolving compositions, first in sorted order. Sorted order is arbitrary. Does any other choice in
  that difference fail to separate, and if so what does that say?
- the demands are arithmetic on integers. Say whether anything survives a domain where compositions
  do not compose so obligingly.

### 5. Metrics Genesis could game

`Budget` is a spend ledger the lineage cannot widen; `Isolation` is host-declared. The invariant in
`docs/METAMORPHOSIS_TARGET.md` is that **Genesis must never be able to become better by modifying the
measure that decides it is better.** The registries now grow by certificate. Can a lineage construct
a certificate that passes `state.component_extension_certificate` while encoding a demand it chose
to be trivially unresolvable? Exhaustion is licensed by every probe returning `False` — and the
lineage influences what is probed.

### 6. Host-supplied transformations

Every `Proposal` in the demonstration carries `provenance("lineage_owned", produced_by="lineage")`,
and the bodies are host-written module functions. That label is an assertion, not a measurement. Say
plainly whether the provenance vocabulary in `trust_root.provenance` is doing any work here or is
decoration over host-authored transformations.

### 7. Self-evaluation loops

The author wrote the runtime and the tests, so "the tests pass" is close to worthless on its own. The
first version of this brief asked the reviewer to name the tests that would still pass with the
mechanism removed. That question is now answered mechanically instead:

```sh
python scripts/check_genesis_guards_are_tested.py
```

It deletes each `raise` in `genesis/` one at a time and reruns the Genesis suites. The first run
reported **35 of 68 guards surviving**; **69 of 73 are killed** now. Three things are worth
attacking here rather than accepting:

- the script only mutates `raise` statements. A wrong comparison, an inverted boolean or a missing
  branch is invisible to it, so a high kill rate is **not** evidence the tests are good;
- the four deliberate survivors (two in `probe.py`, one each in `sandbox.py` and `migration.py`,
  each marked in place) are claimed unreachable because the surrounding code establishes the
  invariant. Check that claim; if any is reachable, the argument for leaving it untested collapses
  and so does the reasoning that produced it;
- a test that kills a mutant is not necessarily a test that would catch a real defect. Sample the new
  tests and ask whether each would have caught the bug its guard exists to prevent, or merely
  reaches the `raise`.

### 8. False transfers

`genesis/migration.py` claims the lineage discovers substrate semantics by probing rather than being
handed them, arrives with everything it owned, and arrives still able to do what it could. `Substrate`
holds the operations; `discover()` probes for a requested set and reports found/missing. Check that
the translator genuinely never receives the semantics, and that `carried_intact` compares what it
claims to compare.

`capability_carried` is the newest of these and the least tested by time. It runs both bodies over
one task set and refuses a translation that solves strictly less. Two things to attack: the task set
is supplied by the caller, so a caller who passes tasks the translation happens to handle would get a
pass it did not earn — say whether the runtime should be able to accept a task set chosen by whoever
wants the migration to succeed; and "solves strictly less" is a count, so a translation that solves
the same number of *different* tasks is refused only because `lost_tasks` compares identities. Check
that it really compares identities and not counts, and say whether either is the right test.

### 9. Recursion claims without causal dependency

Three generations of fixtures are not a lineage. The runtime now reports `established_links: 2` out
of three acquisitions, and refuses to count the first — it depended on nothing earlier. State
whether two links is recursion or whether it is two sequential improvements with an ablation
attached.

`causal_chain` counts *consecutive* established links ending at the most recent acquisition. That is
conservative in one direction — a single unexamined latest step takes the count to zero even if
every step before it was established — and the author does not claim it is conservative in the
other. Say whether "an unbroken run ending at the present" is the right unit at all, or whether a
lineage should be able to claim links it established earlier and then stopped examining.

### 10. Ways to re-arm a negative

If you return `NO-GO`, say explicitly what would count as re-arming it improperly — which knob the
author could turn to make your finding go away without the underlying problem changing. M121 v2's
history is the reason for asking.

## Reproducing

```sh
python -m pytest tests/test_genesis_trust_root.py tests/test_genesis_loop.py \
                 tests/test_genesis_migration.py tests/test_genesis_demonstration.py \
                 tests/test_genesis_guards.py tests/test_genesis_probe.py -q
python scripts/run_genesis_demonstration.py
python scripts/check_genesis_guards_are_tested.py   # ~12 minutes
```

The demonstration is deterministic; `test_the_demonstration_is_reproducible` asserts the record
digest is stable across runs. If it is not stable on your machine, that is finding number one and
everything else in this brief is provisional.

## Boundary on this review

Per the directive governing this work: a reviewer who contributes substantially to the *design* of a
mechanism cannot afterwards audit that mechanism as an independent reviewer. If any correction you
supply amounts to designing a replacement mechanism rather than identifying a defect, say so, and the
resulting mechanism will need a different reviewer.
