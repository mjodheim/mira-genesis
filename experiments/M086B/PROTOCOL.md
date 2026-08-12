# M086-B evolvable improvement mechanism — second qualification

**FROZEN BEFORE ANY HARNESS, BANK OR HOLDOUT EXISTS. THIS IS COMMIT 1 OF FOUR.**

M086-A is post-hoc disqualified; see `experiments/M086/DISQUALIFICATION.md` and D053. M086-B is a
**new experiment**, not a repair of that one. It has its own protocol, salt, bank and holdout, and a
single scientific attempt. `fa647e27…c2a5` is not reused as evidence, and no observation from M086-A
counts toward this result.

## The question, unchanged

**H32:** a lineage permitted to modify the mechanism that turns evidence into candidate
transformations will, after meeting a limitation that mechanism cannot express, construct and adopt a
validated modification of it; and on a later, independently materialized problem the modified
mechanism will generate a corrective transformation lying outside the **constructive image** of the
original mechanism, producing a correct outcome the same lineage with a frozen mechanism does not
reach under any budget.

The target is unchanged: `ModuleDiagnosis.sufficient` returns `self.module is not None`, so M047's
mechanism refuses to act whenever evidence implicates more than one module.

## What M086-A got wrong, and what this fixes

M086-A's observations were reproducible. Its **instrument** was not enforceable. Four corrections are
mandatory here and each is a condition of the verdict rather than a note.

### 1. Every artifact is bound to committed bytes

M086-A recorded a protocol digest matching only the CRLF working-tree copy. Here:

- `experiments/M086B/*.json` are declared `-text` in `.gitattributes` **in this commit**, before any
  digest is computed;
- every recorded commitment is verified against `git show HEAD:<path>` as well as the working tree,
  and the checker fails if the two differ.

### 2. P1–P10 are each computed, and any single false makes the result negative

`evaluate()` must return a per-condition table. No condition may be documentary, checked only
elsewhere, or absent. The checker asserts that the table has exactly ten entries, that each is a
boolean, and that `positive` is their conjunction.

### 3. P8 is implemented with a real fault

Before the meta-adoption transaction, the harness writes an **independent** pre-adoption record of
the mechanism — its canonical bytes and digest — to a separate artifact the adoption path does not
touch. During adoption a fault is injected that corrupts the live mechanism. The lineage detects it,
restores, and the restored mechanism's recomputed digest must equal the independently recorded one
**byte for byte**. Comparing a restored state against its own checkpoint record is the M080 tautology
and is forbidden; the comparison is against the separately written artifact.

If no fault is injected, or no restoration occurs, or the digests differ, **P8 is false and the
result is negative.**

### 4. The holdout does not exist while the meta-search runs

This is enforced physically, not by inspecting source text.

The experiment runs as **three separate processes across three commits**:

| Step | Process | Commit | Produces |
|---|---|---|---|
| 1 | development + meta-search + adoption | 3 | `ADOPTED_MECHANISM.json`, `PHASE1.json` |
| 2 | holdout materialization | 3 | `HOLDOUT.json` |
| 3 | holdout execution + hidden evaluation | 4 | `RESULT.json` |

Step 1 runs and its outputs are committed **before** step 2 is invoked. The holdout is generated from
the frozen salt and the grammar declared below by a script that imports no lineage module, and is
written to an artifact the phase-1 process never reads because it did not exist when phase 1 ran.

The checker proves the ordering from recorded evidence rather than from absence of references:

- `PHASE1.json` records the digest of every input it read and carries no holdout digest;
- `HOLDOUT.json` records the digest of `ADOPTED_MECHANISM.json` it was generated after;
- `RESULT.json` records both, and the checker verifies the chain;
- the git history must show the phase-1 artifacts committed in an earlier commit than `HOLDOUT.json`.

### 5. The replay is total

The checker re-derives every arm and compares a **canonical digest of the complete arm record** —
every digest, every boolean, every count, every label, the adopted and rejected primitives and the
entire causal journal — not a selected subset. An omission is then impossible to hide, because the
comparison is one equality over the whole serialized record.

## The bank, generated rather than authored

M086-A's bank was hand-written, which made it easy to shape. Here the bank is generated from the
frozen salt by a declared grammar, and the generator is committed with this protocol.

**Grammar.** A starting body is rendered from M047's own renderers with an alias table and a route
table drawn from the salt. A limitation is a pair of public cases: one naming a token absent from the
alias table, one naming an operation present in the alias table and absent from the route table. The
canonical operation of the unknown token is drawn from those that already have a route, so a repair
cannot reveal a new fault. Hidden cases are drawn from the same operations with different operands.

**This may fail.** The grammar does not guarantee that any meta-primitive helps, that
`widen_hypothesis` is the one that does, or that `fixed_meta` fails. If the salt yields a bank where
the control succeeds, where no meta-transformation validates, or where a different primitive wins,
that outcome is the result and is preserved.

## Arms

Unchanged from M086-A, and matched on identity, starting body, public evidence, budget and
primitives: `evolvable_meta`, `fixed_meta`, `meta_acquisition_ablated`, `task_only_mutable`, the last
at three times the ordinary patching budget.

## The frozen threshold

| # | Condition |
|---|---|
| P1 | `evolvable_meta` adopts exactly one validated mechanism modification, with rejected alternatives recorded |
| P2 | `evolvable_meta` solves the holdout on the evaluator's hidden cases |
| P3 | `fixed_meta` does not solve the holdout, **and** the enumerated constructive image of the starting mechanism for the holdout evidence contains no passing candidate |
| P4 | `meta_acquisition_ablated` does not solve the holdout |
| P5 | `task_only_mutable` does not solve the holdout |
| P6 | the adopted holdout patch is outside the starting mechanism's constructive image |
| P7 | the causal chain is serialized and audited end to end: limitation → hypothesis → meta-transformation → experiment → outcome → adoption → the later transformation it enabled |
| P8 | a forced fault during meta-adoption is detected and restored to a byte-identical mechanism, compared against an independently recorded digest |
| P9 | the chronology is proved from recorded digests: phase 1 read no holdout, and the holdout was generated after the adopted mechanism was committed |
| P10 | the starting mechanism is differentially equivalent to M047's `diagnose_limiting_module` + `_candidate_sources` |

**Every one is computed in `evaluate()`. A single false makes the result negative.**

## Failure classification

**Negative** — any of P1–P10 false. `fixed_meta` solving the holdout, or no meta-transformation
validating, would each be an informative negative and must be preserved.

**Inconclusive** — the sandbox cannot run. Not runnable is not negative.

## Attribution

Track A. No foundation model participates in generating, selecting or ranking the meta-transformation
during the experiment. Infrastructure was authored before this freeze; the scientific execution is
deterministic and model-free. The evaluator, the sandbox, the science gates and this protocol remain
outside the mutable body.

## Claim boundary

Identical to M086-A's, and it did not become weaker by being restated: a positive result would
establish, in one bounded project-authored construction, that the mechanism producing future
transformations became an object of endogenous transformation and that the acquisition was causally
necessary to a later capability.

Not AGI, not open-ended evolution, not arbitrary self-improvement, not general autonomy. No gate — not
G4, G6 or G7. Not a replacement for M085 and no contact with its fail-closed boundary. Not an
independent reproduction. The meta-primitives remain project-authored, and the result must enumerate
what stays frozen.

## Prohibited

- reusing M086-A's bank, holdout or result as evidence;
- amending this protocol after the bank is materialized;
- rerunning a materialized bank for any reason;
- materializing the holdout before the adopted mechanism is committed;
- letting any condition be documentary rather than computed;
- comparing a restored mechanism against its own checkpoint record.
