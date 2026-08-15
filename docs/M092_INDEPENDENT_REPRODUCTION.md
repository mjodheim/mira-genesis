# M092 independent reproduction boundary

## Status

This apparatus is **pre-arm** and **pre-qualification**. It is authored before the first M092 target
criterion search exists so the project cannot invent a convenient reproduction rule after seeing a
positive or negative canonical result.

M092-F does not arm the target search, execute a selected candidate on qualification examples,
register a substrate operation, create `SUBSTRATE_B` or `LANGUAGE_B`, or support H38/D062.

## Why independent reproduction is required

The canonical M092 search is deterministic, but determinism alone does not make a preserved result
trustworthy. A long search can span many hosted jobs, so its transport also contains operational
state: workflow dispatches, artifact identifiers, checkpoint files and segment receipts. Before a
canonical terminal result may be used as the input to qualification, a second computation must
reconstruct the exact terminal criterion state from the frozen criterion genesis.

The reproduction is deliberately a second logical run, not a retry that can change the search:

- it uses the same frozen target theorem, program stream, certificate-policy order, scanner and
  independent verifier;
- it starts from `CriterionSearchState.fresh(...)`, never from the canonical terminal state;
- it has its own segment schema, artifact namespace and checkpoint chain;
- it carries the canonical artifact **identity** while searching so chains cannot be mixed, but it
  does not read the canonical artifact **content**;
- canonical result content is downloaded only after the reproduced search state is already terminal;
- the complete serialized criterion states are then compared byte-for-byte;
- a mismatch is preserved as an immutable reproduction result and leaves qualification closed.

There is no alternate seed, alternate ordering, repair loop or "try again until equal" rule.

## Separation from the canonical result

`scripts/run_m092_independent_reproduction.py` has no canonical-result command-line argument. Its
imports are limited to the frozen criterion engine and the independent reproduction resume validator.
It therefore cannot use the selected program, certificate, terminal status, refusal histogram or
criterion-event digest from the first run to guide the reproduction trajectory.

The workflow authenticates the source canonical artifact by GitHub run id, artifact id, deterministic
name, SHA-256 artifact digest and arming head before reproduction begins, but does not download that
artifact. The identity is recorded in each reproduction receipt solely to prevent one chain from
being compared with another result later.

Only when a reproduction checkpoint is terminal may the workflow download
`m092-first-canonical-search`. The post-hoc packager independently validates the canonical result
schema, result digest, marker, terminal segment, criterion state, theorem binding, implementation
bindings, counters and first-run flags before comparing it with the reproduced state.

## Independent segment chain

Each reproduction segment uses schema `m092-independent-reproduction-segment/1` and binds:

- exact arming head and parent;
- source canonical workflow run id, artifact id and artifact digest;
- zero-based reproduction segment index;
- predecessor reproduction segment digest and artifact identity when present;
- input and output criterion-state digests;
- generated-program and certificate-attempt counters before and after the segment;
- GitHub run id and run attempt;
- whether the checkpoint is terminal;
- an explicit assertion that canonical result content was not loaded during the trajectory;
- explicit false values for qualification access and candidate execution for selection.

Segment zero starts at criterion genesis. A continuation can resume only a non-terminal checkpoint
whose reproduction receipt, theorem, current implementation bindings, counters and exact state digest
all validate. Duplicate segment indices and zero-progress automatic retry loops fail closed.

As in the canonical transport, checkpointing is operational rather than scientific. One-program
atomic checkpoints cannot change proposal order, policy order or the first accepted candidate.

## Frozen workflow provenance

M092-E originally dispatched continuation jobs with `ref: main`. The post-merge review identified a
pre-arm provenance weakness: GitHub chooses workflow YAML from the dispatch ref before the job can
check out the immutable arming commit. A later change to `main` could therefore alter orchestration
between canonical segments even though the scientific code checkout remained frozen.

M092-F closes this before any target search is consumed. The canonical workflow resolves the exact
still-open arming PR branch, confirms that its head and base are unchanged, and dispatches every
continuation from that branch instead of mutable `main`. The independent reproduction workflow uses
the same rule. The future arming marker binds both workflows and every reproduction implementation
file by SHA-256.

This is a pre-result transport correction. It was derived from provenance review, not from target
candidate feedback or qualification evidence.

## Terminal reproduction result

After the reproduced trajectory terminates, `scripts/package_m092_independent_reproduction.py`
creates schema `m092-independent-reproduction-result/1`.

A matching result records:

- the authenticated canonical source identity and result digest;
- the terminal reproduction segment digest;
- canonical and reproduced terminal statuses;
- canonical and reproduced criterion-state digests;
- `state_byte_identical: true`;
- `qualification_gate_open: true`;
- `reproduction_from_genesis: true`;
- `target_search_rerolled: false`;
- no qualification access and no candidate execution for selection.

A mismatch is also a valid preserved reproduction outcome. It records
`state_byte_identical: false` and `qualification_gate_open: false`. The workflow uploads that result
before failing, so an undesirable mismatch cannot disappear merely because the job exits non-zero.
Qualification must not proceed from a mismatch.

## Neutral pre-arm rehearsal

`.github/workflows/m092-reproduction-transport-rehearsal.yml` exercises the transport without the M092
target theorem. It uses the neutral countdown requirement and three hosted runs:

1. build and upload a four-program neutral source prefix;
2. without downloading source content, independently reproduce the first two programs from genesis,
   preserve the reproduction segment and dispatch a continuation;
3. authenticate both artifacts, resume the reproduction for two more programs, mark the reproduced
   prefix complete, only then download the source content, and require byte-identical criterion
   states.

The rehearsal must report `cross_run_reproduction_state_byte_identical: true` on `main` before the
first target arming is considered.

## Qualification gate

A successful independent reproduction does **not** itself qualify M092. It only permits the next
protocol phase to be designed and executed. Qualification must remain separate and must still test
the causal chain required by M092: a genuinely acquired substrate operation, a language primitive
that depends on it, new qualifying reach, persistence, exact rollback, fresh-process survival and
reuse, with the corresponding ablations.
