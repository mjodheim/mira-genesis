# Genesis RSI V22R — retained-evaluator identity-corrected replication

Status: **prospective successor after V22 pre-evaluator identity failure**.

V22R changes no scientific success rule and does not rescore V22. It exists because V22's final
freeze document committed two incorrect SHA-256 values even though the underlying files themselves
were already committed and unchanged.

## Preserved facts

V22R keeps unchanged:

- host repository and commit:
  `mjodheim/mjodheim-brewstead@720b27c8bc80de16c04953e13d5f9e8425beea8c`;
- the same three prospectively selected Brewstead repair tasks;
- all three defect patches;
- all three reserved evaluator sources;
- exact G1 and G2 policy bytes;
- proposer protocol and information boundary;
- proposal evaluator;
- campaign semantics;
- descendant bundle builder;
- final adjudicator;
- process utility semantics:
  `(best_quality_milli, -represented_requests, -rounds)`;
- global utility semantics:
  `(tasks_solved_without_regression, sum_best_quality_milli, -total_represented_requests, -total_rounds)`;
- positive rule: G2 solves 3/3 without public regression, strictly beats G1 process utility on at
  least 2/3 tasks, and strictly beats G1 global utility.

No threshold, task or evaluator is selected from the returned V22 R1 patches.

## V22 failure boundary

The V22 R1 proposer outputs already returned on 24 September are **quarantined inputs**. No reserved
evaluator was run and no represented campaign observation exists for them.

V22R proposer calls must be fresh isolated chats. Previous V22 proposal/transcript bytes, conversation
context and task-specific hints are forbidden information.

To make accidental transcript reuse mechanically impossible, V22R R1 bundles use a `v22r-`
campaign-slot namespace, a distinct root node id and a new task-manifest digest. The unchanged V22
output verifier therefore rejects an old transcript.

A newly generated proposal patch may coincidentally be byte-identical to an earlier V22 patch; that
is not itself a protocol violation. The returned transcript must bind the V22R manifest and attest the
unchanged information boundary.

## Root-parent provenance

V22R reconstructs each root independently from only:

1. the frozen Brewstead host commit;
2. the already frozen V22 defect patch for that task;
3. the already frozen public symptom / allowed source / reserved evaluator commitment.

It does **not** reuse the old V22 ZIP or `parent.tar.gz` bytes.

The V22R root builder normalizes archive metadata: uid/gid, user/group names, mtimes and file modes
are deterministic. Directories are 0755, regular files are 0644, and only `mvnw` is 0755. ZIP entry
timestamps and modes are also fixed. Thus capsule identity no longer depends on checkout filesystem
metadata.

The parent **content** must still reproduce the original frozen tree digest for each task. If it does
not, V22R preflight fails before any proposer call.

## Execution boundary

The V22R freeze must bind:

- the exact V22R deterministic root-builder bytes;
- the actual `utility.py` bytes rather than V22's incorrect recorded hash;
- every inherited critical V22 apparatus hash;
- the exact three V22R output bundle hashes and task-manifest hashes;
- the reproduced parent tree/source identities;
- the V22 pre-evaluator failure record;
- a successful prospective CI that rebuilds every V22R bundle twice byte-identically and proves old
  V22 transcripts cannot satisfy the new slots.

No V22R proposer output may exist before that freeze commit.
