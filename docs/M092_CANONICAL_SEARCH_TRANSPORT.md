# M092 canonical criterion-search transport

## Status

This transport is **unarmed**. Merging it does not execute the M092 target search, create a target
search state, select a target candidate, reveal qualification material, register a substrate
operation, or support H38/D062.

The unique first target search may run only from a later commit whose sole changed file is
`experiments/M092/CANONICAL_SEARCH_ARMED.json` and whose commit message is exactly:

`m092(canonical): arm first immutable criterion search`

The marker must bind its actual parent commit and the exact SHA-256 digests of every decisive
selection and continuation artifact: protocol, target theorem, criterion runner/freeze/engine,
resume validator, program enumerator, certificate-policy search, certificate generator, proof search,
candidate scanner, independent verifier, K1 kernel, runtime, canonical guard/workflow, terminal
result packager and canonical segment packager. The frozen limits remain 2,000,000 programs and
2,000,000 certificate-policy attempts. No reset, reroll, alternate seed or post-result repair path is
provided.

## Why transport and arming are separate

The transport is authored experimental apparatus. It must therefore be reviewed, tested and merged
while the target search is still closed. A later marker-only commit can then open exactly that frozen
apparatus without changing it at the moment the first result is consumed.

A plain local resume still obeys the strongest M092-D rule: the complete claimed prefix is replayed
from genesis and must reproduce the supplied state byte-for-byte. Long-running canonical GitHub
execution has a separate transport-only resume path because replaying an ever-growing multi-day
prefix before every hosted job would eventually consume the whole job window. That path is accepted
only from an immutable predecessor Actions artifact whose id, run, name and artifact SHA-256 are
checked by the workflow and whose segment receipt binds the exact criterion-state digest, arming head,
arming parent and monotone counters.

This is a pre-search amendment motivated by infrastructure, not target feedback. The target theorem
has not been searched and qualification remains unopened.

## Neutral runtime evidence

The pre-search neutral runtime audit deliberately did not load `TARGET_THEOREM.json`, the criterion
selector or any qualification material. On GitHub's Ubuntu/Python 3.11 runner, the preserved
2026-08-15 measurement produced:

- 100,000 proposal enumerations in 4.749684079 seconds, or about 21,054 proposals/second;
- a linear proposal-only projection of about 94.99 seconds for 2,000,000 proposals;
- 1,000 real neutral certificate-policy attempts in 2,391.093583167 seconds;
- about 0.418218679 certificate-policy attempts/second;
- a neutral linear projection of 4,782,187.166334 seconds for 2,000,000 certificate-policy attempts;
- an additive proposal-plus-certificate projection of 4,782,282.160016 seconds, roughly 55.3 days.

The projection is explicitly **not a bound or a prediction of time to the first target candidate**.
The target search may stop much earlier, and theorem/program structure changes proof cost. The
measurement is sufficient only to reject an architecture that requires the worst case to fit inside
one six-hour hosted job. The audit's final workflow validation initially failed because it referenced
a stale report field name (`attempts_examined`); the measurement step itself succeeded and printed
the complete report. The validator now checks `sample_units == 1000` and the expensive audit is
repeated only when the current HEAD actually changes measured implementation code.

## Immutable multi-run chain

One logical canonical search may span many hosted workflow runs without changing the scientific
trajectory.

Segment zero starts from deterministic criterion genesis. Each job advances the same frozen
`advance_search` trajectory and atomically checkpoints after every completed program. The shell
execution window is 320 minutes inside a 360-minute job, reserving time to package and upload the
latest completed checkpoint.

Every segment artifact has the deterministic name
`m092-canonical-search-segment-<arming-head>-<zero-padded-index>` and contains:

- the exact output `m092-canonical-search-state.json`;
- `m092-canonical-search-segment.json`, a receipt binding input/output state digests, start/end
  program and certificate counters, arming head/parent, GitHub run identity, predecessor segment
  digest, predecessor artifact id/digest and the execution-step outcome.

Artifacts uploaded by the canonical workflow are immutable. Before segment N > 0 may execute, the
workflow requires the exact artifact id to belong to the declared previous run, requires its exact
canonical name and SHA-256, downloads only that artifact, then validates the predecessor receipt and
checkpoint against the still-open marker-only arming PR. A second live artifact for the same segment
index is a decisive refusal.

After a non-terminal segment is successfully preserved, the workflow dispatches exactly segment
N+1 on the repository's frozen transport from `main`, while checking out and executing the immutable
arming head. GitHub's constant concurrency group serializes all canonical segments and competing
arming branches.

Continuation is automatic only when the saved checkpoint made completed-program or certificate-count
progress. If a 320-minute segment cannot complete even one program, the artifact is preserved but
automatic continuation stops fail-closed rather than retrying forever. Such a case must be reviewed
as an infrastructure/atomicity limitation before any changed apparatus is considered.

## Interruption and retry semantics

Checkpoint frequency is transport-only. Tests require neutral one-chunk and multi-chunk execution
for the same program budget to end in the exact same serialized criterion state. One program is the
canonical checkpoint unit; no segment is allowed to skip an in-progress program or commit a partial
policy sequence.

If a runner is interrupted mid-program, the on-disk state remains the last completed program
boundary. A preserved non-terminal segment therefore authorizes only continuation from that exact
checkpoint. If artifact upload itself fails, that progress is not part of the canonical artifact
chain; any retry must reproduce the same segment from the same immutable predecessor. No target
outcome may be used to choose between branches, seeds or checkpoints.

## Terminal artifact and independent reproduction

A terminal checkpoint is one of:

- `candidate_selected`;
- `program_budget_exhausted`;
- `certificate_budget_exhausted`.

The terminal package schema is `m092-canonical-criterion-search-result/2`. It binds the terminal search
state to the terminal segment receipt and records the total segment count. It also records:

- `canonical_transport_mode = immutable-artifact-segment-chain`;
- `independent_reproduction_required = true`;
- `qualification_may_begin_before_reproduction = false`.

Therefore completion of the multi-run chain is **not** yet authorization to qualify or adopt a
candidate. Before qualification, a separate deterministic reproduction must start from genesis on
the same frozen arming head and reproduce the terminal state/result. That reproduction may itself
need segmented transport, but it must be logically separate from the first canonical run and may not
repair or replace an undesirable first result.

Only after that independent reproduction matches may the protocol proceed to candidate validation,
registration, downstream language construction, causal ablations, qualification, rollback,
fresh-process persistence and any H38/D062 decision.

`candidate_selected`, program-budget exhaustion and certificate-budget exhaustion are all legitimate
first-run outcomes. None by itself is an M092 scientific verdict, and no negative or inconvenient
outcome may be hidden by abandoning the arming PR or starting another search.
