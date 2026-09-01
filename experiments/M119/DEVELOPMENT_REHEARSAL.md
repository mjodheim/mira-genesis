# M119 — DEVELOPMENT rehearsal of the H64 pipeline

**This is not H64 evidence.** No qualifying invocation was made, no model was called, and the
carriers were emitted by the project's own devkit rather than by the blind generator. It is a
dress rehearsal of the apparatus, run in a throwaway clone, to establish that the instrument runs
before the one generation is spent on it.

## What was run

Every stage, in the frozen order, under the real chronology gates, in a scratch clone that never
touched this repository. Only the one network call was stubbed: a synthetic completion in the
generator's own shape — `{"machines": [...]}`, 36 machines from `m113_carrier_devkit`, wrapped in a
response envelope carrying the fixed route's identity metadata and `finish_reason: stop`.

    build_m119_freeze --plan / --spec / --nonce / --freeze
    run_m119_generation --deliver          (network stubbed)
    run_m119_seal
    run_m119_authorize
    run_m119_reveal
    run_m119_qualification
    check_m119_result

## What fired, and what that proves

| check | outcome |
|---|---|
| freeze taken before the commitments were committed | **refused** — "not committed at HEAD" |
| generation attempted before the freeze was committed | **refused** — "not committed at HEAD" |
| synthetic completion against the frozen output schema | conformed |
| runtime identity against the fixed route | held, no failed checks |
| machine-only admission | admitted; 36 enveloped, 36 accepted, 0 refused |
| seal | ciphertext and commitment published, plaintext removed |
| second reveal | **refused** — "the reveal is single-use" |
| reveal → carriers | 36 accepted by the frozen host, 36 distinct signatures |
| qualification | 13 qualifying carriers, 50 paired demands |
| a tested-system module edited after the freeze | **refused** at the scoring and replay gates |

## What the rehearsal found

Two defects that would each have wasted the single generation, both fixed and committed before this
record was written:

1. **The session budget was 1**, not the 4000 inherited from M113. At a budget the runtime cannot
   work within, every arm returns `undetermined` and the instrument reports a flat zero for all four
   cells — 0 of 50 demands resolved, in every arm.
2. **The runner could not read the bank the reveal produces.** Enveloped carriers carry no
   `carrier_digest`; only the frozen host adds one, and it drops `carrier_ref` while doing so. The
   runner read the field straight off the enveloped carrier and raised `KeyError` on the first
   entry. An earlier dry run missed it because it fed devkit carriers, which already carry the
   field.

Four further defects were fixed: `positive: True` could sit beside an `instrument_aborted` verdict;
the reveal reached into a sealed plaintext by subscript; a malformed provider list index-errored
rather than refusing; the checker let a chronology refusal escape as a traceback.

## The disclosure that matters

**The rehearsal produced a verdict, and this record states it rather than hiding it.** On the
devkit bank the run returned `negative`: FULL did not exceed FRESH, with a risk difference around
−0.26 and no guard failure. Repeated runs gave the same direction.

That outcome is about a devkit emitter under a stubbed network. It is not evidence about H64, and it
is not treated as any. It is recorded here for one reason: so that nobody, including the author, can
later claim the design was adjusted after a direction was already visible.

**Nothing in the design was changed in response to it.** The arms, the endpoint, the statistical
rule, α, the ten-point floor, the guards, the verdict states, the bank size and the admissibility
minimums are exactly what they were before the rehearsal ran. Every change made after it is one of
the six defect fixes listed above, each of which is a fix to something that would have crashed or
mis-scored regardless of which way the result pointed.

One design element was added *before* the second rehearsal and for a stated reason recorded in
`COMPLEXITY_BUDGET.md`: the fenced diagnostic arm `FULL_BUDGET_PLUS`, added because the
policy-holding arms returned `undetermined` on 17 of 25 unreachable demands and the 2×2 could not
say whether that was a competence cost or a budget cost. It cannot create a positive, and it did not
change the rehearsal's verdict.

If H64 returns `negative` on the real bank, that is a result. It will be reported as one, without
adjustment.
