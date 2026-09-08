# Genesis runtime hardening design

**Prospective engineering design — 8 September 2026.**

This document responds to the counterexamples in
`docs/audits/GPT56_GENESIS_RUNTIME_REVIEW_2026-09-08.md`. It does not reinterpret any frozen result,
create a scientific observation or move a generality gate. It describes the minimum architectural
changes needed before the integrated DEVELOPMENT runtime can honestly claim that mutable Genesis is
unable to change the measure, admission envelope or history against which it is judged.

## 1. Replace mutable-runtime access with a serialized lineage context

The current proposal callback receives the `Genesis` instance. That gives lineage-owned code handles
to the body, budget, isolation, evaluator, journal and state. No guard downstream can make that safe:
the authority was already handed out.

The replacement interface is data-only:

```text
LineageContext (canonical, immutable value)
    state_digest
    generation
    component descriptors
    vocabulary descriptors
    acquisition descriptors
    observations
    budget_remaining (read-only report)
    evaluated-task-set digests
    current-body artifact digest

lineage mechanism(LineageContext, Demand) -> Intent
```

The mechanism receives a serialized copy in an isolated process, not the live runtime object. It can
return an `Intent`; it cannot mutate anything. The host-side executor validates the intent and is the
only code allowed to spend budget, run probes, append history or commit a new state.

This is a capability boundary, not a naming convention. Passing a frozen dataclass that still holds
references to mutable runtime services is insufficient.

## 2. Admit the complete evaluator, not only `trust_root.py`

Once task correctness is decided by a grader, the grader is part of the measure. A verdict bound to
the bytes of `trust_root.py` but not to the grader can still be produced after the measure changed.

Introduce an immutable `EvaluationContract` with at least:

```text
schema
task_identity_definition
grader_artifact_digest
outcome_vocabulary
retention_policy
strict-improvement policy
contract_digest
```

The grader must be an admitted, content-addressed artifact. For an importable development grader the
artifact can bind an import reference plus the digest of the source artifact that defines it. A
future generated or packaged grader must bind the exact bytes it executes. The runtime must not infer
identity only from a Python function name.

Every parent, candidate, control, ablation and migration-capability arm in one comparison must name
the same `EvaluationContract` digest. The final verdict records that digest alongside the trust-root
source digest.

## 3. Make task-set identity a digest of task contents

`task_id` is a label. It is useful for joining outcome rows and must not be the evidence that two
verification sets are the same work.

Define a canonical per-task identity from every evaluation-relevant field except `task_id`, then hash
the sorted list of those identities. Keep duplicates: two identical questions presented twice are
not the same multiset as one question. Include the expected target because changing the target changes
what the lineage was judged on.

```text
question_digest = H(canonical(task without task_id))
task_set_digest = H(sorted([question_digest, ...]))
```

Record a task set as evaluated **only after the parent arm completed**. Instrument aborts never enter
the evaluated-set ledger.

## 4. Content-address executable bodies and transformations

`Proposal.digest()` currently identifies proposal metadata rather than executable semantics. Replace
`body_factory` as the primary identity with a `BodyArtifact`:

```text
schema
artifact_kind
payload / importable artifact reference
artifact_bytes_digest
build/runtime requirements
provenance
artifact_digest
```

A `Proposal` then contains the candidate artifact digest plus a transformation manifest. The state’s
`body_digest` must be that executable artifact digest, not a digest of the proposal name and
rationale.

For DEVELOPMENT importable fixtures, use a reproducible artifact descriptor that binds the module
source digest and qualified symbol. For lineage-generated code or another substrate, bind the exact
content-addressed payload that is executed.

On restore, the caller may supply a resolver capable of loading an artifact, but it may not choose a
different artifact. The resolver must produce the body whose digest the checkpoint names or restore
fails closed.

## 5. Generate causal ablations from artifact structure

A proposer-supplied `ablated_body_factory` cannot prove that one earlier acquisition and only that
acquisition was removed.

The proposal instead declares a dependency by **artifact digest**. The runtime owns a reconstructable
candidate manifest such as:

```text
candidate artifact
base artifact
dependency artifact digests
transformation steps
```

For the causal arm, the host-side ablation builder removes the named dependency from that manifest,
rebuilds the candidate, and records a structural diff. The comparison is admissible only if the diff
shows exactly the intended removal and all other bound inputs are identical.

The ablation record therefore needs both behavioural evidence and construction evidence:

```text
removed_artifact_digest
candidate_manifest_digest
ablated_manifest_digest
single_difference_verified
same_evaluation_contract
same_task_set
same_isolation
same_budget_allocation
behavioural_loss
```

A deliberately weak unrelated body can then fail tasks, but cannot be called an ablation.

## 6. Preserve the positive experiment inside component acquisition

A component certificate should not turn a measured resolving composition into
`resolves_with_new_component=True` and then discard the composition.

Split the record into three content-addressed pieces:

1. **Prior-exhaustion evidence** — every held component’s search completed, did not resolve, did not
   abort and did not merely stop for budget.
2. **Positive reachability evidence** — the exact wider composition/artifact that resolved the same
   demand, including the sandbox/evaluation record digest.
3. **Acquired component artifact** — executable semantics derived from or explicitly bound to that
   resolving construction.

The new component entry stores all three digests. `create_state()` / `decode_state()` re-run the
certificate validators and refuse any acquired entry whose evidence does not reconstruct.

The caller may suggest a human-readable label, but the component’s identity is the artifact digest.
A label is not the component.

## 7. Persist one admission-bound checkpoint transaction

State and journal are necessary but insufficient. A process-death checkpoint must bind the things
that determine what lineage resumes and under which rules.

Persist state and journal to temporary/next files first, then atomically publish a commit-last
checkpoint manifest:

```text
RuntimeCheckpoint
    schema
    generation
    state_digest
    journal_head
    body_artifact_digest
    admitted_trust_root_sha256
    evaluation_contract_digest
    admitted_isolation record
    current_isolation record
    budget limits + spent ledger
    evaluated_task_set_digests
    checkpoint_digest
```

Restore performs these checks before constructing a live runtime:

- state reconstructs to `state_digest`;
- journal reconstructs to `journal_head`;
- state and journal correspond to the same committed checkpoint;
- the trust root on disk matches the admitted digest;
- the evaluation contract and grader artifact match their admitted digests;
- budget limits **and spent values** are restored, not supplied afresh;
- isolation may not be widened by the caller;
- the resolved executable body matches `body_artifact_digest`;
- evaluated task identities are restored exactly.

If a crash occurs between writing state/journal and publishing the new manifest, the previous
manifest remains the last committed lineage. Uncommitted files are ignored/recovered, not treated as
history.

## 8. Retention is set inclusion, not a larger scalar score

For a strict-improvement adoption under the default metamorphosis objective:

```text
parent_solved ⊆ candidate_solved
and
candidate_solved > parent_solved
```

The verdict records `lost_solved_tasks`. Any non-empty loss rejects the candidate unless a separate,
prospectively admitted trade-off policy explicitly allows loss. Such a policy must not be invented by
the candidate being judged.

Apply the same retention principle to migration. `metamorphosis_succeeded` requires executable
capability to have been measured and preserved; a migration with `capability.measured=false` or
`preserved=false` cannot satisfy the current target.

## 9. Move orchestration from the demonstration into the runtime

The DEVELOPMENT demonstration currently performs diagnosis, vocabulary extension, component
extension, migration and state/journal mutations itself. The end-state driver should be thin:

```text
admission = load_initial_admission(...)
genesis = Genesis(admission)
record = genesis.run(world_or_task_stream)
```

Inside the runtime, a host-side executor processes lineage-produced declarative intents:

```text
observe
  -> isolated lineage mechanism returns DiagnoseIntent / ProbeIntent / TransformIntent / MigrateIntent
  -> executor validates authority + budget
  -> experiment runs
  -> evidence becomes content-addressed artifact
  -> lineage mechanism receives next read-only context
  -> candidate construction
  -> immutable evaluation contract compares arms
  -> trust root accepts/rejects
  -> state + journal + checkpoint transaction commits
  -> continue
```

A rejection becomes an observation and returns to the loop. A migration returns to the same loop in
the new body. No demonstration script assigns `genesis.state`, appends lineage events manually or
chooses the post-restart body.

## 10. Repair order

The dependencies between fixes matter. A useful order is:

1. close mutable-runtime authority (`LineageContext` + declarative `Intent`);
2. bind the grader/evaluation contract immutably;
3. introduce executable `BodyArtifact` identity;
4. repair task-set identity and evaluated-set timing;
5. repair adoption retention;
6. strengthen component evidence and bind acquired executable semantics;
7. replace caller-authored ablation with runtime-generated structural ablation;
8. implement admission-bound transactional checkpoint/restore;
9. move demonstration orchestration behind the runtime controller;
10. rerun the full hostile suite and mutation checker, then request an independent review against the
    exact resulting tree.

Fixing persistence before body/evaluator identity would only persist ambiguous identities more
reliably. Fixing the mutation count before closing the authority surface would measure the wrong
frontier more precisely.

## Completion condition for this hardening pass

This hardening pass is complete only when every counterexample committed on the review branch passes
for the intended reason, each new guard has a non-vacuity control where appropriate, the ordinary
Genesis suites remain green on Python 3.11 and 3.13, and an independent reviewer cannot reproduce the
same authority/evidence bypasses on the exact final SHA.
