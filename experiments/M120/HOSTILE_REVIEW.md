# M120 pre-freeze hostile review

**Written before the scientific freeze, before the readiness run, and before any qualifying
generation.** Its purpose is to find ways to invalidate this instrument while doing so is still
free. Everything it found is either fixed below or disclosed as a limit.

An `instrument_abort` that was detectable before the freeze is a preflight failure. This document is
the preflight.

## What the review actually found

Two findings, and the first is the important one because review did not find it — the rehearsal did.

### Finding 1 — the checker accepted a forged measurements file. **Fixed.**

The first draft of `scripts/check_m120_result.py` did everything M119's disclosed defects asked for:
no evidence path from argv, the plan re-derived from code, the measurements resolved from the
chronology's own constants and proved committed at HEAD byte-identically to disk.

The DEVELOPMENT rehearsal's substitution suite then rewrote every score in the committed
measurements, recomputed `measurements_sha256`, committed it over the canonical path — and the
checker **accepted it**. Every binding held. The file was at HEAD, matched its own digest, named the
committed reveal and carried the right freeze commitment. The numbers were invented.

The defect is M119's, one level up again: *authenticating a file is not the same as knowing what is
in it.* Three passes over that class in M119 found it three times in three places and stopped one
short; this is the fourth place.

The fix is not another binding. The measurement is a **pure function** of the committed carrier
bank, the re-derived plan and the committed nonce, under the frozen arms, evaluator, runtime and
host. So `metamorphosis/m120_measurement.py` holds it once, the runner calls it to produce the
record and the checker calls it to **reproduce** the record, requiring canonical-byte equality. A
forged measurement is now not a file that must be caught by a rule someone remembered to write; it
is a file that does not reproduce.

### Finding 2 — the custody chain was read at its two ends and not in the middle. **Fixed.**

With the measurement reproduced, an attacker who replaced the *carrier bank* would simply have the
measurement reproduce from the replaced bank. The reveal record names the bank by digest, so the
attacker rewrites the reveal record too — and every check the checker performed still passed,
because it compared the measurement against the reveal and never asked whether the reveal was the
one custody produced.

`assert_custody_chain` now walks every link, in the order custody ran:

    sealed ciphertext on disk  ->  public commitment ciphertext_sha256
    pre-seal admission record  ->  public commitment admission_sha256
    pre-seal adequacy record   ->  public commitment preseal_adequacy_sha256
    public commitment          ->  reveal authorization commitment_sha256
    reveal authorization       ->  reveal record authorization_sha256
    public commitment          ->  reveal record ciphertext / generation_response digests
    carrier bank               ->  reveal record carrier_bank_sha256
    carrier bank               ->  admission payload_sha256, committed *before* the seal

The last link is load-bearing: the admission record digested the enveloped payload before anything
was sealed, so the bytes being scored were committed to before the bank was ever encrypted.

## The nine questions, answered against the apparatus

Every "no" below is backed by a test or a rehearsal attack, named. Every "yes" is a disclosed limit.

### 1. Can I fabricate an input that passes the generator contract and is refused by the host?

**No, and this is the milestone's central claim.** The candidate schema states no relation between
two fields, and the decoder is total. Established by exhausting 240 constraint-relevant corners
(`test_every_corner_of_the_constraint_relevant_space_decodes_into_an_accepted_carrier`), fuzzing
1,200 draws across three shapes, replaying M119's own committed bank through the decoder — **0 of 37
refused**, against 34 of 37 under M115's schema — and asserting that the host's constant refusal
messages and the contract's census are still the same set
(`test_the_host_refusal_census_is_still_complete`, which caught one message the census had missed).

The rehearsal asserts `carriers_refused == 0` on its 48-machine bank and fails if it is not.

### 2. Can I substitute the measurements with another file?

**No.** The checker resolves the path itself — there is no argv option, asserted by
`test_the_checker_offers_no_argument_that_selects_evidence` — and reproduces the record rather than
reading it. Rehearsal attack `forged_measurements_with_a_self_consistent_digest`: refused. This is
the attack that succeeded before Finding 1 was fixed.

### 3. Can I modify the plan or the thresholds to change the verdict?

**No.** `m120_bank.validate_analysis_plan` recomputes the commitment from the plan's own contents
and then rebuilds the plan from code, comparing canonical bytes. Rehearsal attacks
`zeroed_plan_minimums_keeping_the_commitment_string` (M119's exact defect) and
`rewritten_plan_with_a_recomputed_commitment`: both refused. Unit fixtures cover both directly.

### 4. Can I use an alternative, uncommitted path?

**No.** Every stage proves its predecessors are committed at HEAD under a declared digest mode; the
freeze binds the interpreting closure computed from source and separately scans the disk for
measurement entry points no root declares. `test_every_m120_entry_point_on_disk_is_answered` fails
if a new `run_m120_*`, `check_m120_*` or `build_m120_*` script appears unanswered. Rehearsal attack
`tested_system_edited_after_the_freeze`: refused.

### 5. Can I obtain a result without going through the canonical path?

**No, for the scoring path.** The single scoring entry point requires the replay stage's whole
predecessor list committed, the freeze unchanged, the custody chain intact and the measurement
reproducible.

**Qualified yes at the repository level**, and this is disclosed rather than papered over: an
operator with write access who rewrites *every* committed artifact and re-seals a fabricated
completion under a passphrase of their own is not detectable by any unkeyed checker. There is no
secret and no external timestamp in this chain. That boundary is bounded by the public commit
history, and the checker's own report says so.

### 6. Can I cause an `instrument_abort` after the freeze that was detectable before it?

**The two that M119 suffered, no.** Host refusal is closed by the contract. Bank inadequacy is now
decided *before the seal*, so it closes the milestone with the reveal unspent rather than after it.

**Some remain, and they are honest ones**: the route may fail to serve the frozen request, runtime
identity may not hold, the completion may not finish cleanly, the provider may change behaviour
between the readiness run and the generation. None is detectable in advance, which is why admission
is the live check and why its failure is terminal rather than redrawn.

**And one is real and unavoidable**: the blind generator may simply produce a bank in which fewer
than three carriers qualify. That is not an instrument defect — the qualification clauses are
M113's, unchanged, and they are supposed to be able to fail. What M120 changes is that this costs a
generation and not a reveal, and that it is described in counts rather than guessed at.

### 7. Can I exploit a difference between DEVELOPMENT and the qualifying path?

**No qualifying script contains a DEVELOPMENT branch.** The rehearsal replaces exactly one function
— the single HTTP call — from outside, in a copy of the tree, and runs the real
`run_m120_generation.py`, `run_m120_seal.py`, `run_m120_authorize.py`, `run_m120_reveal.py`,
`run_m120_qualification.py` and `check_m120_result.py` unchanged.

Two differences remain and are stated:

- the rehearsal writes sandbox **fixtures** for the three DEVELOPMENT records the chronology
  requires, including a readiness result. Each says so in its own bytes and none leaves the sandbox.
  The readiness gate's real refusals are covered by unit fixtures instead.
- the network delivery itself, the retry rule and the identity attestation are exercised by the
  inherited M114/M118 machinery and its tests, not by the rehearsal.

### 8. Does the replay reproduce the same bytes and the same decision?

**Yes.** The rehearsal clones the sandbox into a second clean checkout and runs the scoring entry
point again; `report_sha256` must match or the rehearsal fails. It matched.

### 9. Is there a post-reveal choice that could influence the interpretation?

**No choice this apparatus offers.** The verdict comes from the frozen rule; the strongest
supportable statement comes from the frozen decomposition mapping over the four cells, not from
whoever writes the summary; the diagnostic arm is fenced out of both. The runner takes no parameter
that could change a number, and the checker takes none at all.

**One residual, disclosed:** the *narrowing of the carrier family* was chosen after reading M119's
closed public bank. That is a pre-generation choice, not a post-reveal one, and it cannot select
among H65 outputs — but it is a dependency on a closed record and it is recorded in the
preregistration, the plan's limitations and the derivation report.

## Two more things the review changed

**The digest mode is declared.** M119 compared raw bytes when authenticating predecessors, which
makes the gate a property of the checkout: on this repository's own default configuration every
committed-at-HEAD check fails for reasons that have nothing to do with the experiment. The obvious
repair — a `.gitattributes` entry — is unavailable, because that file is itself a raw-byte-frozen
member of M106's apparatus and appending to it breaks a closed milestone's freeze. Verified: it
does. So `m120_chronology.DIGEST_MODE` declares LF normalization, the stage permission record
carries it, and a test proves a real content difference is still refused.

**The readiness stress is not the candidate schema.** A stress run against the real carrier contract
would hand the project a preview of the bank the frozen contract is about to draw, which is a degree
of freedom over the contract. M117 already paid that cost once and disclosed five apparatus
revisions. The stress is a wholly unrelated domain whose census dominates the candidate schema's,
and the readiness record carries no qualification statistic and no carrier count.

## Readiness gates

Machine-checkable, and each currently reports the state shown.

| gate | command | state |
|---|---|---|
| the contract leaves the host nothing to refuse | `pytest tests/test_m120_carrier_contract.py` | green |
| the instrument gates hold | `pytest tests/test_m120_instrument.py` | green |
| the closure is fully bound and every entry point is answered | `pytest tests/test_m120_instrument.py -k closure or entry_point` | green |
| the full success path and replay reproduce, and nine substitutions fail closed | `python scripts/run_m120_rehearsal.py --run` | green |
| the bank sizing derivation reproduces | `python scripts/build_m120_bank_sizing.py` | green |
| repository integrity | `pytest tests/test_repository_integrity.py` | green |
| the complete suite | `pytest -q -n 10 --dist loadscope` | green on Linux CI; see below |
| DEVELOPMENT route readiness for this schema | `python scripts/run_m120_readiness.py --execute` | **not run — needs the owner's credential** |
| the scientific freeze | `python scripts/build_m120_freeze.py --freeze` | **not taken — blocked on readiness** |
| the qualifying generation | `python scripts/run_m120_generation.py --deliver` | **not spent** |

A note on the local suite: this repository's checkout on Windows converts line endings, and 31 tests
belonging to M106, M116 and M118 fail there for that reason alone, on `main` as well as on this
branch — verified by running the same tests against a clean `origin/main` worktree and diffing the
failure sets. M120 introduced two regressions into that comparison and both were fixed: a naming
convention violation caught by `test_repository_integrity`, and the `.gitattributes` edit that broke
M106's freeze. The authoritative run is Linux CI.

## What is still open

Everything that costs something. The five owner gates are listed in
[`../../docs/IP_REVIEWS/M120_PUBLICATION_REVIEW.md`](../../docs/IP_REVIEWS/M120_PUBLICATION_REVIEW.md)
and in `PROJECT_STATE.md`. No qualifying scientific invocation has been spent, no freeze has been
taken, and H65 is untested.
