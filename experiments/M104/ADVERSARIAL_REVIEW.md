# M104 adversarial review before protocol candidate

## Scope

M104 is allowed to correct only the experiment/checker instrument around the unchanged M103
mechanism. The red-team question is whether the successor silently repairs science, reuses exposed
qualification identities or merely self-declares that its entry point works.

## Closed falsifiers

### A1 — The direct-script import failure could recur

The checker establishes the repository root from `__file__` before importing any `scripts` module.
Its `--entrypoint-preflight` is launched as an absolute direct script from a different working
directory. The subprocess succeeds and imports the M104 runner.

### A2 — The preflight could touch qualification data

The preflight function imports and binds the runner only. Tests hash the pool before and after,
require result/report absence, and inspect the preflight function's call surface. It does not open
pool, result or report paths. This validates the broken import boundary without executing M104
qualification.

### A3 — “Fresh” could mean renamed metadata over reused cases

The freshness audit compares every demand/case/probe/world identity, context token, actionable
descriptor value and complete initial value against M103. All four intersection sets are empty. The
M104 pool uses different configuration semantics, filesystem paths/content and sixteen hidden cases;
it is a complete population with no draw.

### A4 — The wrapper could change the mechanism

M104 imports the frozen M103 runner and changes only the pool preflight function and expected pool
digest for the duration of orchestration, restoring both in `finally`. Candidate construction binds
the exact M103 mechanism/checker file members recorded by protocol `cb21a4fa…`. No M103 mechanism or
capsule source is edited.

### A5 — The new checker could change favorable predicate meanings

M104 delegates P1-P15 evaluation and stable projection to the frozen independent M103 checker. It
adds only M104 result/protocol/pool bindings, replay through the M104 namespace, and process-entry
provenance. The expected predicate census remains exactly fifteen.

### A6 — Another checker exception could disappear without evidence

With `--write`, any checker exception is exclusively materialized as a negative fail-closed report,
blocking a second invocation. A positive report is likewise exclusive-create. M104 permits one
canonical result and one canonical checker attempt.

### A7 — M103 could be silently upgraded after a positive successor

D072, the M103 result tag, the negative tag and `CHECKER_FAILURE.json` remain immutable. M104 result
schema explicitly records that M103 result bytes are not used as evidence. D073 cannot alter D072.

### A8 — The first candidate bound an absolute Windows checkout path

Candidate `e528f564…` included the concrete `C:\\Users\\…` repository root returned by entrypoint
preflight. It was not portable and was superseded before owner review, protocol acceptance or any
qualification execution. Tag `provenance/m104-superseded-candidate-a1` preserves it. The preflight
now records only the boolean root-resolution fact, and explicit M104 LF/byte rules plus
`.gitattributes` itself are included in the bound apparatus.

### A9 — The second candidate could not satisfy its own finalization boundary

Portable candidate `62ab21c5…` was produced untracked from a clean source, but the final builder
required both a clean worktree and `HEAD == candidate_source_commit`. The candidate could therefore
be neither present untracked nor committed when finalization ran. It was superseded before review or
qualification and preserved at `provenance/m104-superseded-candidate-a2`.

Finalization now requires a candidate-only commit whose parent is the bound source commit and whose
Git blob equals the working candidate. The final protocol binds that candidate commit as its source;
the later freeze commit must be its direct child. This makes the chronology executable and audited.

### A10 — The third candidate created an unregistered full-SHA citation

Candidate `6b17901b…` was portable and its candidate-only lifecycle validated, but its full source
commit SHA triggered the repository citation guard. That SHA cannot be written into the content of
the commit it identifies without circularity. The candidate is preserved at
`provenance/m104-superseded-candidate-a3` and was not accepted.

The replacement binds named annotated provenance refs. Candidate construction requires the source
tag to resolve to `HEAD`; finalization requires the candidate tag to resolve to the candidate-only
commit; canonical preflight resolves the accepted source ref and requires it to be the freeze
parent. Exact reachability is preserved without an impossible self-citation.

### A11 — The fourth candidate did not verify every freeze blob

Candidate `9f6e1b42…` correctly used annotated refs, but canonical preflight checked only the freeze
tag/parent and clean worktree. A direct child could still alter runner or checker bytes in the same
commit as `PROTOCOL.json`. That candidate is preserved at
`provenance/m104-superseded-candidate-a4` and was not accepted.

Canonical preflight now recomputes every M104 apparatus member, both inherited M103 binding groups,
the raw pool and candidate; it also requires the freeze commit's complete changed-path census to be
exactly `experiments/M104/PROTOCOL.json`. Parent/tag checks are necessary but no longer treated as
sufficient.

### A12 — The fifth candidate omitted the inherited runner/fixture binding group

Candidate `3d765cd5…` bound M103 `mechanism` and `checker`, but M104 directly imports
`scripts/run_m103_qualification.py` and reads the DEVELOPMENT/predecessor fixtures in M103's
`apparatus` group. Those causal bytes were therefore not protected by the successor commitment.
The candidate is preserved at `provenance/m104-superseded-candidate-a5` and was not accepted.

Candidate construction and canonical preflight must therefore bind every causal inherited byte; the
exact inherited orchestration dependency may not remain implicit.

The first implementation of that correction overreached by binding the complete historical
`apparatus` group, including `.gitattributes`, which legitimately changed when M104 added its own
byte rules. A targeted test failed before any replacement candidate was generated. The binding now
names the causal inherited subset: M103 qualification runner, DEVELOPMENT fixture, predecessor
fixture, M102 result and M102 checker, alongside the exact M103 mechanism/checker groups.

### A13 — The sixth candidate did not seal the first-result commit before replay

Candidate `99cb23f5…` protected the freeze commit and every causal input, but the checker did not prove
that the commit carrying the first result changed only `RESULT.json` or that replay still used the
reviewed blobs. A code change could therefore travel with the result. The candidate is preserved at
`provenance/m104-superseded-candidate-a6` and was not accepted.

The frozen policy now names `experiment/m104-canonical-first-result`. Before predicate evaluation,
the checker independently requires `HEAD` to equal that tag, its parent to equal the freeze tag, its
changed-path census to contain only `RESULT.json`, its working result to equal the committed blob,
the tree to be clean, and every pool/candidate/apparatus/inherited binding to remain exact.

## Residual ceiling

Even if M104 is positive, the constructor feature vocabulary, subset bound, lower interpreter,
carrier adapters, tasks, evaluator and entire population remain project-authored. M104 removes an
instrument defect; it removes no scientific bound. The next milestone must attack one of those
bounds with a new hypothesis rather than add another same-shape carrier.
