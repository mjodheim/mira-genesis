# M048 development result

## Status

**PASSED IN DEVELOPMENT after two preserved failing qualification runs.**

This is a bounded, noncanonical development result. It does not replace or amend the canonical
status of M042, and it does not establish arbitrary runtime migration, unrestricted code
synthesis, open-ended evolution, general intelligence, consciousness or production safety.

## Preserved run history

The qualification history is append-only:

1. CI run `31046715149` (run number `402`) on commit
   `616f31619e7337dd0c114fc1f09e1cefa1a8f7fd` failed. Repository integrity and the M048
   checkpoint path exposed the orphan-import and `causal_journal`/`native_journal` schema
   defects. This negative verdict remains part of the M048 record.
2. CI run `31054844770` (run number `403`) on commit
   `839883d1c2353d47005d14fd8e42c073e049b0d8` failed after the schema correction. The suite
   reached the checkpoint contract and exposed the missing public `combined_digest` field.
   This second negative verdict also remains part of the record.
3. CI run `31061450556` (run number `404`) on commit
   `0dfd822ac1c81692abe45f9499ece420a947fd0f` completed successfully without rerunning either
   failed qualification commit.

The successful run used the explicitly pinned Node.js 20 target runtime in the Python 3.11 and
Python 3.13 matrix and passed the repository-integrity job and the complete permanent test
suite.

## Qualified construction

The successful development run establishes, within the fixed M048 protocol and test bank:

- exact reconstruction of the accepted M047 version-six lineage;
- compilation of its nine accepted Python modules into nine native Node.js ESM modules;
- execution of the migrated body without semantic delegation back to Python;
- preservation of all twenty-eight inherited retained capabilities;
- observed post-migration use of the inherited `mean` tool;
- bounded proposal of the unseen `maximum` capability in a separate Node process;
- independent hidden validation in a separate Node process;
- adoption of a new executable `tool_max` module as version eight;
- preservation of inherited capabilities after native learning;
- detection of forced version-nine causal-journal corruption;
- exact restoration of the version-eight body, registry, journal, memory and checkpoint;
- explicit insufficient-evidence termination for `median`, with rejection evidence retained;
- exact artifact replay of migration, accepted learning, rollback and terminal evidence,
  **within a single process**. See the reproducibility qualification below.

## Reproducibility qualification

The replay claim above is narrower than it first reads, and the difference was found after
qualification rather than during it.

`experiments/M048/PROTOCOL.md` §Replay requires the run to "reproduce the exact final native
state digest". That holds when replay happens inside one process, which is what the manifest's
`replay_identical` field checks and what the qualifying CI run exercised. It does **not** hold
across processes: two runs of `run_m048_native_runtime_migration` in the same environment
produce different `final_state_digest` and `post_migration_checkpoint` values.

The cause is exact and bounded. `metamorphosis/m048_native_lineage.py` computes

    validation_digest = _digest(b"m048-native-validation-v1\x00", selection)

over the selection mapping returned by `_validate`, and that mapping contains `worker_pid`.
The Node worker pid changes per process, so `validation_digest` changes with it, and the change
propagates into the patch registry record, the native journal, the causal memory and the final
state digest. Neutralising `worker_pid` alone restores full manifest reproducibility, which
establishes it as the sole cause.

This is the M014c defect recurring: a recorded identity that includes something environmental.
It is also the distinction `PROJECT_STATE.yaml` already draws for M044 and M046, whose records
separate `immediate_replay_byte_identical_within_each_runtime` from
`separately_archived_cross_runtime_manifest_comparison`. M048's record did not draw it.

### What is and is not affected

No recorded value is invalidated. No literal M048 state digest appears in this file, in the
protocol, or in the project registers; only commit SHAs are cited, and those are unaffected.
The accepted body itself has a stable identity: `_native_body_digest` reproduces exactly across
processes. The scientific content of M048 — the migration, the preserved capabilities, the
post-migration learning, the rollback — is unchanged.

What fails is the published traceability claim, and the correction is to state the claim
accurately rather than to restate the result.

### Why the defect is not repaired here

Removing `worker_pid` from the digested selection changes every derived digest. Under D014 that
is a protocol-owner decision rather than a repair to slip into a documentation change.
`tests/test_m048_cross_process_reproducibility.py` asserts the current behaviour, including a
genuine cross-process comparison, so a repair must update that pin deliberately instead of
passing unnoticed.

## Qualification boundary

The positive result applies only to one fixed M047 source architecture, one bounded metadata
compiler, Node.js ESM, fixed proposal templates, fixed task families and fixed hidden tests.
The proposal process has no hidden-test access, the validator has no adoption authority, and
the lineage has no repository, network, credential, deployment or production authority.

The two failed CI runs are not erased by the later successful correction. They remain the
causal development history that exposed and localized the schema and checkpoint-contract
defects before qualification.
