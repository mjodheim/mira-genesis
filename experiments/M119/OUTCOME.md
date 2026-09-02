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
