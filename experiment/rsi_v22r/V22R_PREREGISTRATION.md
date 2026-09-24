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

To make accidental transcript reuse mechanically impossible, V22R R1 bundles retain the same exact
parent archive but rewrite the task manifest's `campaign_slot_id` to a `v22r-` namespace and bind
a new V22R apparatus commit. The unchanged V22 output verifier therefore rejects an old transcript
because both the slot identity and task-manifest SHA differ.

A newly generated proposal patch may coincidentally be byte-identical to an earlier V22 patch; that
is not itself a protocol violation. The returned transcript must be newly bound to the V22R task
manifest and attest the unchanged information boundary.

## Root-parent provenance

V22R does not reconstruct a new host parent. It consumes the three exact active V22 R1 bundle bytes
already supplied before the failed evaluation and rewraps only proposer-visible metadata. The
`parent.tar.gz`, reserved-evaluator commitment, allowed source path, public symptom and public guard
remain unchanged byte-for-byte.

The source V22 R1 bundle SHA-256 values are frozen in the V22R freeze record.

## Execution boundary

The V22R freeze must bind:

- the exact V22R rebundler bytes;
- the actual `utility.py` bytes rather than V22's incorrect recorded hash;
- every inherited critical V22 apparatus hash;
- the exact three source and V22R output bundle hashes;
- the exact V22R task-manifest hashes;
- the V22 pre-evaluator failure record.

No V22R proposer output may exist before that freeze commit.
