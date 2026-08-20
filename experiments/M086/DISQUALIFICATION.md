# M086-A — POST-HOC DISQUALIFIED DEVELOPMENT

**The attempt recorded in this directory is withdrawn as a scientific qualification. H32 is neither
confirmed nor refuted by it.**

Everything is preserved unchanged: `PROTOCOL.json`, `PROTOCOL.md`, `BANK_COMMITMENT.json`,
`RESULT.json`, `RESULT.md`, the harness, the checker, the tests, the CI run and the git history. No
digest is recomputed and no artifact is rewritten. What changes is only the claim attached to them.

This follows the M069 precedent: a run whose recorded outcomes remain exact and diagnostic, whose
positive qualification is withdrawn because the boundary the protocol promised was not the boundary
the code enforced.

## What was claimed, and what is withdrawn

The claim was that the improvement mechanism became an object of endogenous transformation and that
the acquisition was causally necessary to a later capability, at attempt 1 with no retry.

The observations behind it are unchanged and remain interesting. The **qualification** is withdrawn,
because the verdict that produced it did not test what the frozen protocol said it would.

## The four defects

### 1. The result is bound to bytes that do not exist in the repository

`RESULT.json` records `protocol_commitment: c0eeeffe…`. That digest matches the **working-tree** copy
of `PROTOCOL.json` on the machine that ran the experiment. It does not match the committed blob:

```
recorded in RESULT.json : c0eeeffe17d4fb9c4e6d…
working tree (CRLF)     : c0eeeffe17d4fb9c4e6d…  match
committed blob (LF)     : 49583ae9ae8693930277…  MISMATCH
```

The protocol was not covered by a `-text` attribute, so Git normalised it on commit and the recorded
commitment binds a byte sequence no checkout can reproduce. Any reviewer on Linux — including CI —
would compute a different digest.

This is **the M064 defect class recurring**: "the frozen hash was checkout-dependent", which cost
M064 its qualification. It is also the defect the side-car branch `claude/dreamy-swanson-d63fc5` was
opened to fix repository-wide, and which has never been merged. M086-A reproduced it in a new
experiment while that fix sat unmerged.

> **Correction, 2026-08-20 — the sentence above is preserved as written and is no longer true.**
> The repair had not been merged when this document was committed (`92039f8`, 2026-08-12 09:33),
> and it landed about seven hours later the same day as `531a447`, "protect digest-bearing
> experiment artifacts from EOL conversion". The second sentence still holds: M086-A did reproduce
> the defect while the fix was unmerged. Only the claim that it "has never been merged" has expired.
>
> The branch `claude/dreamy-swanson-d63fc5` has since been deleted. Its commit is preserved as the
> annotated tag `branch/claude-dreamy-swanson-d63fc5` (`9e0bff7`), and the account of the defect it
> carried — which never travelled with the fix — is now in `FAILURE_LOG.md` under
> "M076-M083 — the checkout-dependent hash defect recurred on a Windows clone".
>
> Nothing about M086-A's disqualification changes. This corrects a statement about repository
> history, not about the result.

It was invisible to CI because the checker is not part of the test suite and no regression asserted
the binding.

### 2. P8 was never implemented, and four of ten conditions never reached the verdict

The frozen protocol requires, for a positive result:

> **P8** exact rollback: a forced fault during meta-adoption restores a byte-identical prior
> mechanism, compared against an independently recorded digest.

No fault is injected anywhere in the harness. No checkpoint of the pre-adoption mechanism is taken.
No rollback is performed or compared.

Worse, `evaluate()` computes **P1–P6 only**. P7 (causal chain), P8 (rollback), P9 (leak boundary) and
P10 (differential equivalence) are absent from it entirely. Some are checked elsewhere — P9 and P10
by the checker — but none of them can make the verdict negative. The recorded `"verdict": "positive"`
was therefore computed against six of the ten conditions the protocol froze, and the four missing
ones include the only one that was never implemented at all.

A threshold that cannot fail is not a threshold.

### 3. The holdout existed before the meta-search that must not have seen it

The protocol requires the holdout to be "materialized only after the meta-transformation is
committed". In the harness, `HOLDOUT_PUBLIC` and `HOLDOUT_HIDDEN` are module-level constants that
exist from import, in the same module and the same process as the meta-search. The runner then
enumerates the starting mechanism's image over the holdout **before** any arm executes.

The structural check that was written verifies only that `meta_search` does not *name* those
constants. That is an argument about one function's source text, not about chronology. The protocol
promised an ordering; the code enforced an absence of references.

Nothing suggests the search actually used the holdout — it is deterministic and its source is
readable. But M069 was disqualified on exactly this distinction: not that hidden evidence *was* used,
but that the interface made it reachable. The same standard applies here.

### 4. The replay compares a fraction of what it preserved

The checker re-derives the arms and then compares **3 of 14** recorded fields per arm:
`development_solved`, `holdout_hidden_solved`, `meta_transformations_adopted`.

Never re-derived: `mechanism_start_digest`, `mechanism_after_development_digest`,
`mechanism_at_holdout_digest`, `adopted_primitives`, `rejected_primitives`, `holdout_adopted_label`,
`holdout_public_solved`, `holdout_candidates_generated`, `cycles_used`, and the entire causal
`journal` — which is the artifact P7 exists to guarantee.

The mechanism digests and the journal are the evidence for the central claim. They were preserved and
not verified.

## What remains true and is worth keeping

These observations stand as development evidence and are the motivation for the successor:

- M047's mechanism emits **zero** candidates against evidence naming two stages, and the enumeration
  of its complete constructive image is a real technique for proving a control's failure structural
  rather than budgetary;
- M0 is differentially equivalent to `diagnose_limiting_module` + `_candidate_sources` over 10 probes
  on two bodies, so the artifact under test really was the mechanism the repository froze;
- `widen_hypothesis` alone sufficed and composition was unnecessary — the lock was the hypothesis
  schema, contradicting the protocol's own prediction;
- the arm that acquired the modification and had it stripped before the holdout failed, while the arm
  that kept it succeeded.

None of that is a qualified scientific result. It is a reason to run M086-B properly.

## What must not happen

The four defects must **not** be repaired and the same bank replayed while keeping "attempt 1,
positive". That would be a result-saving retry. `fa647e27…c2a5` may not be reused as scientific
evidence, and this result may not be cited as positive qualification, as gate evidence, or as
independent reproduction of anything.

## Consequence for the registers

No gate moves. H32 returns to untested. M086-A is recorded as post-hoc disqualified development
evidence, alongside M069, and the successor M086-B is a separate experiment with its own protocol,
salt, bank and holdout, and a single scientific attempt.
