# GPT-5.6 Genesis hostile review round 2 — critical addendum

Status: engineering review only. No scientific gate, observation or frozen result moves.

This addendum records two late findings that cut across several earlier round-two items and therefore deserve their own explicit treatment.

## R2-19 — commit-last persistence does not retain the previous committed payloads

`Genesis.persist()` writes, in order:

1. `lineage_state.json` — replacing the previous state file;
2. `descent_journal.json` — replacing the previous journal file;
3. `runtime_checkpoint.json` — the manifest, published last.

Publishing the manifest last prevents a half-written *new* checkpoint from being accepted. It does **not** make the previous checkpoint recoverable. If the process dies after step 1, the old manifest still names the old state/journal digests, but the only state file has already been replaced by the new one. `restore()` therefore sees a mismatch and fails closed; it cannot return to the last committed lineage because the payload that manifest referred to was destroyed before commit.

That is safer than accepting torn history, but it is not the transactional property claimed in `persist()`'s comment that a crash leaves the previous committed lineage available.

### Counterexample

`tests/test_genesis_gpt56_round2_persistence_semantics.py::test_crash_before_manifest_publish_can_restore_the_previous_committed_checkpoint`

The test persists a checkpoint, advances the in-memory lineage, writes only the next state file to simulate death between writes, then asks restore to recover the prior manifest. The current fixed filenames make that impossible.

### Repair shape

Persist immutable/content-addressed payloads first, for example:

- `states/<state_digest>.json`
- `journals/<journal_head-or-record-digest>.json`
- `checkpoints/<checkpoint_digest>.json`

Then atomically update a tiny `CURRENT`/manifest pointer last. Never overwrite a payload still named by the previous committed pointer. A crash before the pointer swap then genuinely leaves the old checkpoint fully resolvable; a crash after it leaves the new one resolvable.

The same design also makes rollback/audit of prior generations possible without asking one mutable filename to represent all history.

## R2-20 — `multiprocessing` pickle defeats the candidate process boundary in both directions

`sandbox.run_candidate()` uses the `spawn` multiprocessing context and a `multiprocessing.Pipe`. Both rely on Python pickle for objects crossing the process boundary.

That is incompatible with the threat model stated by `sandbox.py`: the candidate body is explicitly untrusted Python.

### Inbound: code can execute before limits are installed

The `Process` arguments include `body_factory`. Under `spawn`, the child must unpickle the process object and its arguments *before* it enters `_child()`. `_child()` is where `_apply_limits()` and the audit hook are installed.

A hostile callable/factory object can implement `__reduce__`. Its reconstruction callable therefore executes in the new child process before CPU/memory/audit restrictions are applied. The sandbox has not started yet, but candidate-controlled code already has.

Counterexample:

`tests/test_genesis_gpt56_round2_sandbox_transport.py::test_body_factory_transport_cannot_execute_before_sandbox_limits_are_installed`

### Outbound: code can execute in the evaluator while receiving an answer

A candidate's returned answer is inserted into the result dictionary and sent over `multiprocessing.Connection`. The parent calls `recv()`, which unpickles that candidate-controlled object before `_outcomes_from()` or the grader sees it.

An answer object with a hostile `__reduce__` can therefore execute Python in the parent/evaluator process merely because the parent decoded the result. This bypasses the process separation completely and can reach exactly the state, filesystem and module globals the sandbox is supposed to protect.

Counterexample:

`tests/test_genesis_gpt56_round2_sandbox_transport.py::test_candidate_output_transport_cannot_execute_code_in_the_parent_process`

### Repair shape

Do not pass untrusted Python objects through pickle at either edge.

A safer architecture is:

1. launch a **fixed trusted bootstrap** child containing no candidate-controlled Python object in its spawn arguments;
2. install OS/process limits before resolving the candidate artifact;
3. identify the candidate by an admitted content-addressed descriptor/package, not a live callable object;
4. communicate through a non-executable, schema-validated wire format such as canonical JSON for the current primitive task/answer domain;
5. reject values outside the allowed data schema rather than serialising arbitrary Python objects;
6. keep grading in the parent, but only after strict data decoding that cannot invoke candidate-defined constructors;
7. for a real mechanism, prefer an OS/container boundary appropriate to the candidate language rather than treating a Python audit hook as complete isolation.

This finding is P0 for attaching a real self-generated mechanism. The current sandbox remains useful as DEVELOPMENT apparatus against honest/pure-Python fixtures, but it is not a security boundary for adversarial Python objects while pickle crosses it.

## Consequence for the repair order

The authority boundary now has two layers that must both close before the runtime can safely host real self-generated code:

1. proposal/search/translation code cannot share the evaluator interpreter (R2-14/R2-15);
2. candidate execution cannot cross the supposedly isolated child boundary using executable object serialisation (R2-20).

Only after those are closed does it make sense to rely on content-addressed body identities, structural ablations and persistent acquisitions as security-relevant properties rather than bookkeeping around a permeable boundary.
