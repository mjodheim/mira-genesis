# Genesis runtime — implementation notes

**Status: DEVELOPMENT apparatus. Not a preregistration, not a protocol, not a scientific result.**

Nothing here draws a salt, records a scientific observation, or advances any generality gate.
`DEMONSTRATION_RECORD.json` carries `is_a_scientific_observation: false` and
`advances_a_generality_gate: false`, and it means both. The bodies in
`genesis/development_bodies.py` are fixtures.

These notes record what was built for the objective in
[`../../docs/METAMORPHOSIS_TARGET.md`](../../docs/METAMORPHOSIS_TARGET.md), and — more importantly —
**the defects found in it after it was built**. A package that only documented its intended
behaviour would be describing the version its author believed he had written.

## What exists

| Artifact | Role |
|---|---|
| `genesis/trust_root.py` | immutable: isolation, budget, provenance, the final accept/reject. Imports nothing from mutable Genesis |
| `genesis/state.py` | content-addressed lineage state; registries that grow **by certificate**, never by editing a tuple |
| `genesis/journal.py` | hash-chained append-only descent journal |
| `genesis/sandbox.py` | separate-process candidate execution, and an honest record of which limits were actually applied |
| `genesis/loop.py` | the evolution cycle: propose, run isolated, decide, adopt or reject, ablate, record |
| `genesis/probe.py` | probes the lineage composes and runs: insufficiency by exhaustion, established by experiment rather than by consulting an oracle |
| `genesis/migration.py` | substrate discovery by probing, migration, and the requirement to evolve again after it |
| `genesis/development_bodies.py` | neutral fixtures, including bodies that lie, throw, escape and depend |
| `scripts/run_genesis_demonstration.py` | drives one lineage through the whole cycle and emits the record; defined in [`DEMONSTRATION_DEFINITION.md`](DEMONSTRATION_DEFINITION.md) |
| `scripts/check_genesis_guards_are_tested.py` | deletes each guard in turn and reports the ones no test notices |
| `tests/test_genesis_*.py` | 204 hostile offline tests; 76 guards, 71 killed by a test (measured) |

## The stopping criterion, and where this stands against it

The criterion in `METAMORPHOSIS_TARGET.md` asks for one lineage that measures itself, diagnoses
itself, transforms itself, verifies the transformation, adopts or rejects it on evidence, keeps what
it learned, progressively modifies the machinery enabling later transformations, changes form, and
goes on evolving in the new form.

The demonstration performs each of those steps in one run. **That is not the same as satisfying the
criterion**, for a reason that has nothing to do with the runtime: the bodies are fixtures. What the
run establishes is that the mechanisms compose into a program, that the program refuses what it
claims to refuse, and that its record does not overstate what happened. Whether the same holds with a
real mechanism attached is exactly what remains, and it is the whole of the remaining work.

## Defects found after the fact

Each was found by applying a hostile attack list to the package after writing it, and each is fixed
with a test that fails when the mechanism is removed. They are recorded because they share one shape
and that shape is the thing to keep watching for: **a record testifying to a property the code does
not have.**

### 1. Isolation limits declared, checked, reported — and applied to nothing

`Isolation.filesystem_writes_permitted`, `network_permitted` and `subprocess_permitted` were declared
on the dataclass, enforced-as-a-request by `assert_no_wider_than`, and written into every sandbox
result. Nothing applied them. A candidate could write files, resolve names and fork, and the record
said it had not.

This is worse than having no limit at all: a missing limit is visible, whereas a limit that appears
in the record invites a later reader to rest a claim on a boundary that was never there.

Fixed with a `sys.addaudithook` guard. The hook covers pure Python only — a C extension calls libc
without raising an audit event — and the result reports that through
`audit_hook_covers_pure_python_only` rather than implying completeness.

### 2. The guard was written against the convenient spelling

The first version inspected `open`'s string mode. `os.open(path, os.O_WRONLY | os.O_CREAT)` reports
mode `None` and carries its intent in the flags, so it went straight through, as did `os.remove`,
`os.rename` and `os.mkdir`, which never call `open` at all. The limit was enforced against
`open(path, "w")` and nothing else.

Three tests now cover the low-level route, deletion, and the flags path, each with a non-vacuity
companion asserting the same body succeeds when nothing stops it.

### 3. An enforcement call that succeeds and does nothing

`resource.setrlimit(RLIMIT_NPROC, (0, 0))` returns successfully in this container and does not
prevent a fork; a candidate ran `/bin/true` through it. The sandbox had been listing
`subprocess_permitted` as *enforced* on the strength of that return value. The call is kept because
it costs nothing where it does work, but the "enforced" entry now comes from the audit guard, which
was verified to actually stop the fork.

### 4. The verdict relabelled as a causal ablation

The demonstration's causal step compared the candidate arm against the parent arm — the two arms the
acceptance verdict had *just* compared — and reported the difference as evidence of causal dependency
between generations. It is not an ablation to re-read the comparison that produced the verdict.

A real third arm now runs the accepted candidate with the acquired component removed and nothing else
changed. The migrated bodies route their new solutions *through* that component, so removing it
breaks them rather than degrading them into the parent; an ablated arm behaviourally identical to the
parent is now itself the signal that nothing was removed, and the check refuses on it. A
negative-control test drives the check to `False` on an arm that never depended on the acquisition.

Note what this does **not** establish. The dependency exists because the fixture was built with it.
The claim is that the runtime can hold a causal claim and refuse it, not that any real mechanism has
one.

### 5. A hash chain that carried the stored digest forward

`journal.verify` advanced the chain using each record's stored `entry_digest` rather than the digest
it recomputed. Tampering with an entry therefore broke that entry alone, and every entry after it
still verified — which is the one property a hash chain exists to provide.

### 6. Instrument failure scored as candidate failure

A child process that could not start produced `error` rows indistinguishable from a body that
genuinely failed, so a broken sandbox would have been recorded as evidence about a candidate. The
sandbox now returns `outcomes: []` with `instrument_failure: True`, and the loop aborts the cycle
rather than deciding. This is the distinction M124 had to learn between a delivery outcome and a
scientific one.

### 7. The migration checked what the lineage recorded, never what it could do

`carried_intact` compares components, certificates, acquisitions, vocabulary and observations across
a substrate change, and the record reported "nothing lost" on the strength of it. Nothing compared
what the *arrival could still do*. A translation could drop every capability the lineage had and pass
that check untouched, because nothing being counted had been lost.

That is the transported-output-versus-transported-intelligence distinction M084 forced on this
project, arriving one level lower down — and it was live in the demonstration itself, whose migrated
body solved two of the four tasks its pre-migration body solved.

Both bodies are now run over the same tasks under the same isolation, and a translation that solves
strictly less is refused unless a lossy arrival is explicitly intended. A migration nobody supplied
tasks for reports `capability.measured: false` and claims nothing, rather than reporting preservation
it never checked. A refused migration leaves the lineage where it was rather than half moved.

### 8. A permanent obligation of the runtime that the runtime did not have

`loop.py`'s docstring said causal dependency between generations is "checked every time, not once per
milestone" and called it "a permanent obligation of the runtime, so a lineage cannot accumulate
improvements that merely happened in order". `ablation_supports_causal_dependency` existed. `cycle()`
never called it. The only thing calling it was the demonstration script, so any other driver of the
loop got no check at all — and the obligation was a sentence rather than a property.

A proposal now carries its ablation arm, the cycle runs it at the same budget, and the result is
recorded on the acquisition and in the journal. An acceptance with no arm is recorded as
`established: false` with the reason — the lineage's first acquisition depended on nothing earlier,
or the proposal supplied no arm — never as an unexamined pass. An arm that cannot run aborts the
cycle rather than being scored as a candidate failure.

`Genesis.causal_chain()` then counts the consecutive acquisitions whose dependency was actually
established. On the demonstration that is **2 links out of 3 acquisitions**: the first depended on
nothing earlier and is not counted. A claim about recursive improvement now has to read a number
that can be small.

### 9. The candidate awarded its own marks

The trust root recomputes every number from raw per-task rows and never reads a score. That was
always true and it was never enough. `body.attempt(task)` **returned the outcome**: the rows the
trust root so carefully recomputed from came out of the candidate's own process, so the recomputation
was honest arithmetic over an unverified claim. A body returning `"solved"` for every task was, as
far as the whole runtime could tell, solving every task.

`trust_root.py`'s docstring said it "never consults a score, a boolean or a summary produced by the
thing being judged" — while consulting per-task outcomes produced by exactly that.

`run_candidate` now takes a host-side `grade`. Under it the body returns an **answer** and the parent
decides whether it is right, in the parent's own process, against the real task. The loop, the
migration's capability check and the probe search all carry the grader through, and the demonstration
runs on it.

The distinction is visible rather than assumed: every sandbox result and cycle record carries
`outcomes_are_self_reported`, because `decide()` cannot tell the two apart — the rows look identical
— so a reader weighing a verdict has to look. `CheatingBody` is one body with two verdicts: it wins
every task when it grades itself and scores zero when the parent grades.

One related hole closed with it. The isolation report was assembled in the child and sent *after* the
body ran, and a body sharing that process can reach local variables through the frame stack. It is
now sent before the candidate is constructed, and only the first message is read for it.

### 10. Half the runtime's refusals had never been exercised

The nine defects above were found by reading the code adversarially. That method has an obvious limit:
it finds what the reader thinks to look for. `scripts/check_genesis_guards_are_tested.py` asks the
question mechanically instead — it deletes each `raise` in `genesis/` one at a time and reruns the
suite, so a guard whose removal keeps the tests green is a refusal nothing ever checked.

**First run: 35 of 68 guards survived.** The suite passed 110 tests and just over half of what the
package claimed to refuse had never been driven to the point of refusing. Among the survivors were
guards carrying real weight — a candidate with unrecognised provenance, a control arm that faced
different tasks, a forged vocabulary certificate, a component certificate being used to buy a
diagnostic feature, and the journal's chain check, which was masked by the file-digest check sitting
in front of it.

33 were tested in `tests/test_genesis_guards.py`, and the probe module has since added its own.
**Now 69 of 74 are killed.** Four survivors are marked in place as defensive assertions about
invariants the surrounding code already establishes: the sandbox child cannot report a task set it
was not given, `migrate` builds the arrival state out of the departure state's own fields, probes
run in separate processes and cannot write to the lineage state, and a feature drawn from a
symmetric difference cannot give both demands the same value. Reaching them would require contrived
paths that report coverage without adding knowledge, so they are left untested deliberately and the
intactness comparison is tested on its own. The fifth is an *equivalent* mutant rather than an
unreachable one: deleting the probe's missing-operation guard reaches the same recorded `error` by
raising `TypeError` on the next line, so no test can distinguish the two.

The number is reproducible rather than quoted: rerun the script.

## The third authored ceiling, and what closing it did and did not buy

The sharpest open question was that a certificate licensed by "every probe returned false" rested on
`speculate`, a host-written callable, and the vocabulary extension rested on a host-written
`feature_row`. The host decided both findings and the certificates recorded the lineage agreeing with
it.

`genesis/probe.py` replaces both oracles with experiments. The lineage **composes** a probe — an
ordered sequence of primitive operations — runs it as an untrusted body in the sandbox at budget
cost, and every verdict is tallied from raw per-task outcomes.

* **Components.** Exhaustion now means *no composition its components can express solves the demand*,
  and it licenses nothing on its own: the lineage must also show that a composition drawn from the
  wider operation set **does** solve it. "Nothing I have works" is a failed search; "nothing I have
  works and something outside what I have does" is a claim about the lineage's representation.
* **Vocabulary.** A demand's row through the per-component vocabulary is measured by probing. Its
  cause is which held component the resolving composition mostly lives in, also measured, with ties
  refused rather than broken. The separating feature is then read out of the two measurements — an
  operation one resolving composition needs and the other does not — instead of being chosen and
  justified afterwards.

The oracle-backed module (`genesis/diagnosis.py`) was **deleted**, not kept alongside. Leaving an
oracle-backed path available is leaving a way back to certificates that mean nothing, and a
superseded module that still passes its tests is exactly the kind of thing that gets reused.

Something is still host-supplied, and pretending otherwise would repeat the error one level down.
The host supplies the **alphabet** — the primitive operations, the task sets, and which operations
each held component reaches. It does not supply the **sentence**, and cannot: a composition either
maps the inputs to the expected outputs when it runs, or it does not.

That difference is tested rather than asserted. With the same components, the same operations and
the same code, three task sets produce three findings:

| Demand | Registry exhausted | Reachable more widely | Licenses a new class |
|---|---|---|---|
| needs one operation from each component | yes | yes | **yes** — found `double` then `increment` |
| solved by a held component alone | no | — | no |
| solved by nothing available | yes | **no** | no |

The third row is the one that matters most: exhaustion without reachability is refused.

The vocabulary path is checked the same way. The measured pair is refused when two demands share a
cause, when the vocabulary already separates them, and when either demand resolves through nothing —
so the pair that is found is the one case the data actually supports.

## Hati's hostile review — GO with five blocking corrections, all applied

`docs/audits/GENESIS_RUNTIME_REVIEW_HATI_2026-09-08.md` (the reviewer's own copy; the summary was
relayed by the owner). Verdict `GO` with three MEDIUM and two LOW corrections. All five are applied,
and three of them were surfaces this runtime's own brief had listed as open — which is the difference
between recording a limitation and fixing it.

**1 (MEDIUM) — the sandbox blocks writes, not reads.** Pushed to its sharp edge this invalidated the
grading fix in defect 9. Every fixture returned `task["expected"]` and the task crossed the process
boundary intact, so the grader added to stop a candidate marking its own paper was comparing the
answer key against itself; a body that computed nothing scored full marks. The sandbox now withholds
named keys from the task the child receives and records what it removed. `PeekingBody` is the control
in both directions, and a third test inspects the keys that actually crossed rather than inferring
the boundary from an outcome.

**2 (LOW) — grading was optional and the difference only labelled.** `Genesis` now refuses to
construct without a grader unless `allow_self_reported_outcomes=True` says that is what was meant. A
label is not a refusal, and nobody should reach a self-reported verdict by forgetting an argument.

**3 (MEDIUM) — the migration verification set was the caller's to choose.** A caller who wanted a
migration to pass could pass tasks the translation happened to handle. The verification set must now
be one the lineage was actually evaluated on, identified by the questions in it so renaming does not
get past the check.

**4 (MEDIUM) — `metamorphosis_succeeded` accepted any candidate as success.** A migrated lineage that
improved for unrelated reasons scored the same as one that built on what it carried. At least one
post-migration acceptance must now have its causal dependency established by the ablation the cycle
already runs.

**5 (MEDIUM) — two links is not recursion.** `causal_chain` reported `links >= 2` as "a chain rather
than a sequence" — a threshold set at the smallest number that permits the word, with the threshold
doing the work the evidence was supposed to do. The boolean is gone; the count is reported and the
record carries `makes_no_recursion_claim`. The demonstration now runs four accepted cycles and
establishes three links, so the number is no longer sitting at its own minimum.

### Correction 6 (LOW), and a number this document should not have carried

Hati's guard run reported **74 guards, 68 killed, 6 survivors** against the 69 killed / 5 survivors
this document claimed. The discrepancy matters more than either number.

**The claim was not measured.** After deleting `ComposedProbeBody` — which removed one guard, and
that guard was a survivor — the counts here were adjusted arithmetically from an earlier run rather
than re-measured: 75 guards became 74, six survivors became five, and the killed count was carried
across untouched. In a document whose subject is not publishing claims the code does not support,
that is the same defect one level up. The rule it breaks is the one this file exists to state.

Measured on the corrected runtime, the current figure is **76 guards, 71 killed, 5 survivors** — the
five listed above. Rerun the script rather than trusting it.

Hati's sixth correction is that the equivalent-mutant claim on `probe.py` did not verify: no test
kills it. That is what an equivalent mutant *is*, so the prediction and the observation agree — but
the objection underneath it is fair and was the real gap. The equivalence had been **reasoned**, and
a reviewer had no way to check it except by re-deriving the argument. It is now measured:

```sh
# with the guard, then with `raise ProbeError(...)` replaced by `pass`
python - <<'EOF'
import sys; sys.path.insert(0, ".")
from genesis import probe, trust_root as tr
print(probe.search(
    registry_reference="genesis.development_bodies:PROBE_OPERATIONS",
    operations=["not_an_operation"],
    tasks=[{"task_id": "p0", "input": 3, "expected": 7}],
    isolation=tr.Isolation(), budget=tr.Budget(limits={"probes": 4}), max_length=1)["search_exhausted"])
EOF
```

Both spellings return `resolved: false`, `search_exhausted: true` and one unsolved attempt. The guard
buys a legible message and nothing else, which is what "equivalent" was supposed to mean and is now
shown rather than argued.

**One survivor remains unaccounted for.** Hati counted six on the pre-correction tree where this
runtime counted five, and the relayed summary names only four of them, so the sixth cannot be
identified from here. Their survivor list would settle it; until then the two measurements disagree
by one and this document says so rather than picking the flattering reading.

## Round two: what the second external review found, and what changed

`docs/audits/GPT56_GENESIS_RUNTIME_REVIEW_2026-09-08_ROUND2.md` reviewed the *repaired* runtime and
asked the harder question: do the stronger properties now claimed actually follow from the repaired
mechanisms. Thirteen findings; three were coverage corrections and ten were mechanism or architecture
blockers. All are closed below. The repair order came from
`docs/GENESIS_RUNTIME_ROUND2_REPAIR_DESIGN.md`: semantic objects first, then the workflows resting on
them, because fixing the later items first would only have measured the wrong frontier more
precisely.

**R2-5 / R2-6 — identity stopped at the symbol.** `artifact_digest_of` unwrapped `functools.partial`
to its underlying callable and discarded the bound arguments, so two zero-argument factories built
from one class with different configuration shared a digest. Restore could therefore hand a persisted
lineage a differently configured body, and the same collision applied to the grader — which *is* the
measure. Identity is now recursive over bound state: partial arguments and keywords, published
configurations, and nothing collapsed. Anything it cannot reconstruct — a lambda, a closure, a
callable with opaque state — is **refused** rather than reduced to a name. Failing closed is the
point: a weak identity that silently covers two executables is worse than none, because the record
then testifies to a binding that does not hold.

**R2-7 / R2-10 — the verdict could name one measure and use another.** `cycle()` took a
`required_strict_improvement` argument and passed it straight to `decide()`, so a cycle could accept a
candidate that improved nothing while its verdict named a contract recording that strict improvement
was required. Whether a control arm was part of the comparison was not in the contract at all, so two
instances sharing one contract digest could reach opposite verdicts on the same candidate. The
decision rule now comes from one admitted `EvaluationContract` and from nowhere else; a control
narrows the comparison by admitting a contract that names the control's identity; and a cycle asking
for a rule the contract does not license is refused and journalled rather than obeyed.

**R2-8 — provenance validated by class alone.** The constructor always required a producer; every
validation path checked only the class, so `{"class": "lineage_owned"}` reached verdicts and lineage
state with nobody named as having produced anything. `trust_root.validate_provenance` is now the one
rule, used wherever provenance enters a trusted record.

**R2-1 — the ablation was still the proposer's own evidence.** Naming a real acquisition was checked;
that the supplied arm *was* that acquisition removed was not, so a deliberately weak unrelated body
labelled with a real name produced a measured loss and was recorded as causal dependency. The runtime
now derives the counterfactual itself from the candidate's published configuration
(`genesis/artifacts.py`), verifies the two differ in exactly the licensed removal, and records
`established: false` when it cannot construct or authenticate the arm. `Proposal.ablated_body_factory`
survives only as a record that a proposer offered one; it is never run.

**R2-11 — an acquisition installed a name.** The certificate proved a composition outside the held
registry reaches the demand, and then `extend_components` added a name; re-running the same demand
immediately afterwards still found nothing that resolved it, unless a human edited a host mapping.
`state.component_artifact` derives the machinery from the certificate itself and `held_operations`
makes later diagnosis consume it, so the acquisition becomes part of the lineage rather than a record
of a discovery.

**R2-12 — an extended vocabulary was a label.** `measure()` emitted one boolean per held *component*
and never read `LineageState.vocabulary`, so an extension widened the history and not the
computation. Features have executable semantics now (`resolvable_by_<component>`,
`requires_<operation>`) and `measure()` evaluates the lineage's current vocabulary in order. A name
whose semantics the runtime cannot evaluate is refused: a made-up boolean in a diagnostic row is
worse than a missing one, because everything downstream reads it as a measurement.

**R2-2 / R2-9 — migration handed the translator too much.** The translator received the very mapping
later used as the intactness baseline, so it could delete the lineage's components from both sides of
the comparison; and it received raw Python callables, whose `__globals__` exposed operations nobody
had probed for. It now receives a deep copy (mutating it is refused), and capability handles rather
than callables (`genesis/capabilities.py`). `used_operations` is **derived from which handles were
invoked** and checked against the declaration in both directions.

**R2-13 — the demonstration was the architecture.** The script called the probes, assigned
`genesis.state`, appended the journal entries and sequenced the migration, so what the run showed was
that a person can call the pieces in the right order. `genesis/controller.py` owns the state machine;
the lineage-owned mechanism is a function from the frozen `LineageContext` to one declarative intent
and can spend no budget, run no probe and commit no state. The script supplies a world, a mechanism
and a renderer, and `tests/test_genesis_gpt56_round2_architecture.py` parses it to check that it
assigns no lineage state and appends no journal entry.

**R2-3 / R2-4 and the missing-operation contract — coverage, not mechanism.** Three guards were
described here as unreachable or equivalent, and the reasoning was wrong in each case in the same
way: it considered the code and not its collaborators. The sandbox task-set guard is reachable from
an ordinary candidate through caller-frame introspection; the probe state-mutation guard is reachable
through a `Mapping` whose `.get()` mutates the state being diagnosed; and the missing-operation guard
is equivalent *only through the sandbox*, since called directly it raises `ProbeError` rather than
`TypeError`. All three now have direct tests, and the comments in the source say what the earlier
claim missed rather than being quietly deleted.

### On the mutation-score discrepancy

Round two supplies the explanation the previous section could not reach. The `sandbox.py` subprocess
survivor is environment-sensitive: `RLIMIT_NPROC` can independently block process creation for an
unprivileged process and be ineffective for uid 0, so 70/6 and 71/5 on identical source can both be
correct measurements on different platforms rather than one of them being a counting error. The
checker now prints Python version, platform, uid and an independent `RLIMIT_NPROC` control, verifies
the unmutated baseline is green before scoring anything, and covers `artifacts` and `capabilities`.
Any figure quoted from it should be read together with that context block.

## Known open, not fixed

- **The host still draws the seed partition.** `COMPONENT_OPERATIONS` decides what each *seed*
  component reaches. Acquired components now derive their operations from their own certificates, so
  the partition is no longer host-drawn all the way down — but the starting one still is, and a seed
  component that is nothing but a host-declared operation set may be a relabelling rather than a
  component. No test here settles that.
- **Two definitions in the vocabulary path are conventions, not measurements.** "The limiting
  component is the one supplying most of the composition" and "take the first operation in the
  sorted symmetric difference" are both the author's choices. They are defensible and they are not
  forced by anything.
- **The mechanism is a programme, not a search.** The controller closes the *authority* question —
  lineage-owned code cannot reach the runtime — and the demonstration's mechanism is a lookup table
  of intents. That the runtime performs the transitions is what the run shows; that a lineage
  discovered which transitions to attempt is not.
- **Intents name importable artifacts.** A lineage that generates its own code needs content-addressed
  payloads the executor can build and run. `binds_exact_executed_bytes` is `false` on every artifact
  descriptor this runtime produces, and it says so.
- **Capability handles are not a sandbox.** Translation runs in this process. Severing
  `__globals__` closes the accidental aperture and the caller-authored use declaration; a determined
  translator can still walk `type(handle)`. Real isolation needs the process boundary that candidate
  execution crosses and translation does not.
- **Fixtures, not a mechanism.** See the stopping criterion section above. The probe operations are
  arithmetic on integers; that they compose is a property of the fixture, not a result.
