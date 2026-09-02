# M119 — instrument-aborted at carrier qualification; H64 untested

**Date:** 2 September 2026

| | |
|---|---|
| Hypothesis | **H64 — untested** |
| Verdict | `instrument_aborted` |
| Qualifying scientific invocations | **1**, spent |
| Paired demands posed | **0** |
| Generality gate advanced | **none** |

**This is not a result about H64.** No arm was run, no demand was posed, no comparison was made.
The hypothesis is exactly as open as it was before the generation. It is not a negative result, it
is not weak evidence, and it may not be cited as either.

## What happened

The single qualifying request was delivered to the fixed route and admitted. Everything about the
delivery was clean:

| | |
|---|---|
| HTTP status | 200, one attempt, no retry |
| Served model / provider | exactly the frozen `deepseek/deepseek-v4-flash-0731` / OpenInference |
| Runtime identity attestation | held, no failed check |
| `finish_reason` | `stop` |
| Completion parsed | yes |
| Conformed to the frozen output schema | yes |
| Enveloped payload accepted by the frozen host | yes — admission passed |

The generator emitted **37** machines against the 36 requested. The bank was sealed, the reveal was
authorized, and the seal was broken once. Then the frozen carrier host and the frozen evaluator
were applied, and the bank did not survive them:

| stage | outcome |
|---|---|
| enveloped | 37 |
| accepted by the frozen carrier host | **3** |
| refused by the frozen carrier host | **34** |
| clearing the frozen qualification clauses | **0** |

The plan requires at least 3 qualifying carriers and at least 3 distinct qualifying structures. With
zero, the frozen rule returns `instrument_aborted`, and the checker records three instrument
failures: fewer qualifying carriers than the plan requires, fewer distinct structures than the plan
requires, and no paired demand posed.

## Why the bank did not survive — instrument diagnosis, counts only

Recorded because the bank is public after the reveal, and because a successor milestone needs it.
Nothing here reinterprets the outcome.

Host refusals, 34 of 37:

| count | refusal |
|---|---|
| 25 | action argument domain is outside 2..4 |
| 8 | carrier observes none of its own state |
| 1 | copy source cell is outside 0..1 |

Blocking qualification clauses among the 3 the host did accept:

| count | clause |
|---|---|
| 3 | `a_determined_attribution_pair_exists` |
| 2 | `the_carrier_imposes_a_protocol` |
| 1 | `demand_needs_a_sequence` |
| 1 | `an_unreachable_observation_exists` |

**The frozen output schema under-constrains what the frozen host accepts, and the model followed the
schema.** Two of the three refusal classes are constraints the prompt states in prose but JSON
Schema cannot express as written: `arg_size` must be 2–4 when `arity` is 1 and 0 when it is 0 — a
conditional the schema flattens to `minimum: 0, maximum: 4` — and `visible` must have at least one
true entry, which the schema does not require at all. A generator that satisfies the schema exactly,
as this one did, can produce machines the host must refuse.

That gap is inherited: the prompt template and output schema are M115's, byte for byte, and M115
also ended `instrument-aborted`. M119 did not introduce it and did not detect it, because nothing in
the pipeline measured schema-to-host agreement before the generation was spent.

## The second instrument finding

**Admission checks payload admissibility, not bank adequacy.** M116 moved carrier admission before
the seal precisely so an instrument failure could be described without spending the reveal. It did
its job here — the payload was genuinely admissible, and the host accepted it. But "admissible" and
"adequate for the plan's minimum" are different questions, and only the first was asked before the
seal. An admissible-but-inadequate bank therefore still consumed the reveal.

Both findings are recorded for a successor. **Neither is acted on here.** M119 is frozen, its single
generation is spent, and repairing an instrument after seeing its outcome is exactly the thing the
freeze exists to prevent.

## What is not being done

- The bank is **not** regenerated, repaired, filtered or resampled.
- The output schema is **not** tightened now and applied retroactively.
- The admissibility minimum is **not** lowered so that three schema-valid carriers would clear it.
- The verdict is **not** reinterpreted as negative, weak, or suggestive.
- No milestone before M119 is reopened or modified.

## What the apparatus did prove

The instrument worked as designed at every point where it was tested. The chronology refused a
freeze before its commitments were committed and a generation before the freeze was; identity,
finish and schema conformance were all checked before anything was called a bank; the plaintext was
removed at seal; the reveal was single-use; the recovered plaintext matched the digest the
commitment named; the runner decided nothing; and the frozen rule returned `instrument_aborted`
rather than a number, on a run where the four-verdict design is the only reason this is recorded as
*untested* instead of *refuted*.

Two pre-freeze review passes and a full DEVELOPMENT rehearsal caught seven defects before the
generation, two of which would each have wasted it on their own — including a comparator that did
not express its own uniform draw. Those are recorded in
[`DEVELOPMENT_REHEARSAL.md`](DEVELOPMENT_REHEARSAL.md).

None of that makes H64 tested. The apparatus was sound and the bank was not, and a sound instrument
pointed at an inadequate sample produces exactly this record and nothing more.

## Corrigendum — two checker defects found after the freeze, disclosed and not repaired

An automated review of the closing pull request raised two findings against `check_m119_result.py`.
**Both were reproduced and both are real.** They are recorded here rather than fixed, for the reason
given below.

**1. `check()` trusted a caller-supplied analysis plan.** It compared the measurement's
`analysis_plan_commitment_sha256` against the plan's own `plan_commitment_sha256` *string*, but never
recomputed that digest from the plan's contents and never re-derived the plan from code. A plan file
with `minimum_qualifying_carriers` and `minimum_distinct_qualifying_structures` set to zero, keeping
the frozen commitment digest verbatim, is accepted: two of this run's three instrument failures
disappear from the report. On a bank with one or two qualifying carriers this would have turned an
`instrument_aborted` into a scientific verdict.

**2. The replay gate authenticated one file and scored another.** `main()` proved the committed
`MEASUREMENTS.json` was at HEAD and unchanged, then scored whatever path `--measurements` named. A
fabricated record that copies the public freeze, reveal and carrier-bank digests and recomputes its
own unkeyed `measurements_sha256` passes every remaining check, despite never being the artifact
whose committed bytes were verified.

Both are the same root cause as the blocker the second pre-freeze review found, one level up: **the
checker authenticates one thing and scores another.** That review fixed the case it saw — the
measurement must name the committed reveal — and neither reviewer, nor the implementation, noticed
that the plan and the measurement file itself were reachable by the same route. Three passes over
the same defect class found it three times in three places, and stopped one short.

### Why they are not fixed here

`scripts/check_m119_result.py` is a tested-system path. The freeze binds its bytes, and every phase
after the generation re-proves that binding. Editing it now would be detected — verified: appending
a single comment line makes the checker refuse itself with *"the tested system changed after the
freeze"* — and the effect would be to make M119's own committed result permanently unreplayable by
the very tool that produced it. Repairing a tested system after the reveal is precisely the
contamination the freeze exists to prevent, and a defect found afterwards does not become an
exception to that. A new entry point routed around the freeze's entry-point scan would be worse: it
would be evading a guard that is working.

### What they do and do not affect

Neither touched this run. The scoring used the committed canonical `ANALYSIS_PLAN.json` and
`MEASUREMENTS.json`, and the committed result **replays byte-identically from them**:
`bf6fc9b307a1f0a3ea9f1dd6453761f75c533ab7ae3543d365f738578e481a78` recomputed from the committed
artifacts equals the committed `report_sha256`. The verdict is `instrument_aborted` on zero
qualifying carriers and zero paired demands — there was no number to inflate and no comparison to
steer, and every disclosed path leads to the same verdict on these artifacts.

What they do affect is the strength of the claim M119 can make about its own auditability. The
honest statement is narrower than the one the apparatus was built to support: *this* result replays
from *these* committed bytes, and the checker as frozen would not have stopped a determined operator
who supplied different ones. A successor must close both — validate the plan by re-derivation rather
than by its self-reported digest, and score the committed artifact rather than a named path.

## Artifacts

| | |
|---|---|
| Tested-system freeze | `9872cf655e0d0e96d867de5e2ab992c9d7588ce2b17a97efc12378f353c1c743` |
| Analysis plan | `d3be5231ea46bf9910bfa92ca6ffe39a5ffe1a6aaf2a8256f18eb64f1067f885` |
| Generator spec | `e0e4c55e953d8cbc83ffd49db5b3f1a72e06956006122937aad9221aaac054b1` |
| Canonical request body | `72ec492b25225c5aebad47c9c40ae61b801b4a6cd3998d6845b223d7ef7e2742` |
| Sealed bank (ciphertext) | `2b105fdcf34f4cfbddb058193f220672638c1ba3871b52f4b93f42a045cccb57` |
| Public bank commitment | `d0000b74cc7b6a7a7d2ce6865e169639fd4aab781e6be1376f1d58b77b13418a` |
| Reveal record | `2f3f83bf6abd77be0ffb7c0f76ca96cc7721b512cbe1abf5cf48be8f2f6c9d09` |
| Measurements | `6b0f236b0f2bf2256eed182c82a94dfcdb55aa15d709eebba10f85298b60dc9b` |
| Result | `bf6fc9b307a1f0a3ea9f1dd6453761f75c533ab7ae3543d365f738578e481a78` |

## Claim boundary

No generality gate is advanced. No claim of AGI, recursive self-improvement or open-ended
intelligence is made or implied. H64 remains untested and the decision slot for it remains reserved
and unfilled.
