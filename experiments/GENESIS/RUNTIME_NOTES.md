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
| `genesis/loop.py` | the evolution cycle: propose, run isolated, decide, adopt or reject, record |
| `genesis/diagnosis.py` | speculative extension with proven rollback; insufficiency by exhaustion |
| `genesis/migration.py` | substrate discovery by probing, migration, and the requirement to evolve again after it |
| `genesis/development_bodies.py` | neutral fixtures, including bodies that lie, throw, escape and depend |
| `scripts/run_genesis_demonstration.py` | drives one lineage through the whole cycle and emits the record |
| `scripts/check_genesis_guards_are_tested.py` | deletes each guard in turn and reports the ones no test notices |
| `tests/test_genesis_*.py` | 110 hostile offline tests |

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

### 7. Half the runtime's refusals had never been exercised

The six defects above were found by reading the code adversarially. That method has an obvious limit:
it finds what the reader thinks to look for. `scripts/check_genesis_guards_are_tested.py` asks the
question mechanically instead — it deletes each `raise` in `genesis/` one at a time and reruns the
suite, so a guard whose removal keeps the tests green is a refusal nothing ever checked.

**First run: 35 of 68 guards survived.** The suite passed 110 tests and just over half of what the
package claimed to refuse had never been driven to the point of refusing. Among the survivors were
guards carrying real weight — a candidate with unrecognised provenance, a control arm that faced
different tasks, a forged vocabulary certificate, a component certificate being used to buy a
diagnostic feature, and the journal's chain check, which was masked by the file-digest check sitting
in front of it.

33 are now tested in `tests/test_genesis_guards.py`. **Second run: 66 of 68 killed.** The two
survivors are marked in place as defensive assertions about invariants the surrounding code already
establishes — the sandbox child cannot report a task set it was not given, and `migrate` builds the
arrival state out of the departure state's own fields. Reaching them would require a contrived path
that reports coverage without adding knowledge, so they are left untested deliberately and the
intactness comparison is tested on its own.

The number is reproducible rather than quoted: rerun the script.

## Known open, not fixed

- **The third authored ceiling.** The lineage *selects* a probe from prepared ones; it does not
  compose a new experimental probe. More sharply: the demonstration supplies `speculate` and
  `feature_row` as host-written callables, so a certificate licensed by "every probe returned false"
  rests on an oracle the lineage did not write. Whether that certificate is the lineage's finding or
  the author's wearing the lineage's name is the most serious open question in the package.
- **No epistemic separation.** The runtime, its tests, the demonstration and this document have one
  source. `docs/audits/GENESIS_RUNTIME_HOSTILE_REVIEW_BRIEF.md` requests the separation that source
  cannot supply for itself; until a review returns, every claim here is self-assessed.
- **Fixtures, not a mechanism.** See the stopping criterion section above.
