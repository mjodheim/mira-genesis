# M117 — instrument development and calibration: CLOSED

**M117 is an instrument-development and calibration milestone. Its scientific hypothesis was never
tested.**

| | |
|---|---|
| Milestone status | **instrument-development completed** |
| H62 status | **untested** — never frozen, no carrier bank, no qualifying generation |
| Qualifying scientific invocations | **0** |
| Generality gates G1–G10 | **unchanged** |
| Successor | M118 / H63 |

## The calibration result, stated narrowly

> Under the **final** apparatus revision, at least one reachable route demonstrated the complete
> instrument capabilities required for a future carrier-blind experiment.

That is the whole claim. It is a **DEVELOPMENT calibration result**. It is **not** evidence for the
Genesis scientific proposition, and it advances **no** generality gate.

### The selected calibration route

| | |
|---|---|
| Requested model | `deepseek/deepseek-v4-flash-0731` |
| Provider | **OpenInference** |
| Canonical checkpoint | `deepseek/deepseek-v4-flash-20260731` |

### Attempt 05, exactly as observed

- **16 candidates probed**; one further position skipped as an identical request.
- **144 of 160 DEVELOPMENT requests consumed.**
- **Independent checker passed.**
- **Exactly one candidate qualified**, at the **earliest qualifying position** in an order frozen
  before any candidate in that attempt was probed.
- **All twelve qualification clauses passed.**
- Token-capacity stress: **HTTP 200**, **`finish_reason = stop`**, **68,368 completion tokens**,
  output **conforming** to the census-dominating stress schema.

Also preserved: **qualifying scientific invocations 0**, **no carrier bank exists**, **H62 was never
frozen**, **G1–G10 unchanged**.

## Disclosure: the route selection was not prospective from the start of M117

**Five apparatus revisions occurred within M117, and some followed real endpoint observations.**

| attempt | plan | defect that superseded it | observations before it |
|---|---|---|---|
| 01 | `d22c3fde…` | three catalogue fields read where this API does not publish them; 2 of 3 required metrics null for 282/282 endpoints | none |
| 02 | `5cc9c648…` | stress requested more tokens than eligibility guarantees; halted at 31/160 | catalogue only |
| 03 | `687b2394…` | two clauses required router fields this API emits on no request; ceiling reached, no selection | 3 candidates probed |
| 04 | `47ff587f…` | reasoning control never sent; 15 of 90 rows the same request — **superseded before any request** | 17 candidates probed |
| 05 | `b3b34590…` | — selected a route | 20 candidates probed |

Revisions 4 and 5 followed real endpoint observations. Revisions 4 and 5 also changed what counts as
qualification or which candidates are reachable, so both were **put to the owner and authorized**
rather than decided inside the milestone. No threshold, ordering key, tie-break or budget bound was
ever changed, and the stress bar remained 32,000 throughout.

**M117 therefore does not claim that its route-selection process was prospectively clean.** That is
precisely why the scientific work moves to a new milestone with a fixed, already-calibrated route.

## Instrument findings preserved

These are the substantive results of M117 and are recorded here rather than left in implementation
history.

1. **A catalogue capability declaration is not evidence of structured-output enforcement.** Routes
   advertising `supports_structured_outputs` and accepting `require_parameters: true` enforced none
   of the required schema feature classes.

2. **The same canonical model checkpoint can exhibit radically different structured-output behaviour
   under different serving providers.**

3. **Alibaba** serving `deepseek/deepseek-v4-flash-20260731` **independently reproduced 9 of 9
   feature classes unenforced** — the M116 result, reproduced on a freshly built apparatus.

4. **OpenInference** serving **the same canonical checkpoint** enforced **all nine** required feature
   classes and passed the full-scale stress (68,368 conforming tokens, `finish_reason: stop`).

5. **The provider serving stack therefore appears capable of materially changing structured-output
   behaviour.** *Stated as suggestive instrument evidence, not a causal scientific conclusion:* the
   provider comparison was **not** a prospectively randomized within-run comparison. The two
   observations come from different attempts under different apparatus revisions.

6. **Run-to-run instability exists.** `google/gemini-2.5-pro` returned **all nine feature classes
   enforced** in one attempt and **none enforced** in another. **No cause is claimed.** The
   apparatus differed between those attempts, but nothing here establishes that as the explanation.

7. **The reasoning control materially affected the available completion budget on at least one
   observed route.** Alibaba `deepseek-v4-pro` emitted 44,791 completion tokens with the control
   unsent and 72,816 with it applied. **Causality beyond that record is not claimed**; the attempts
   differed in more than the control.

## Corrigenda

Two intermediate interpretations were wrong and were corrected explicitly rather than quietly
amended. Both corrections stand in the record alongside the claims they replace.

1. **Attempt 02's HTTP 400 was attributed to the token overage.** Attempt 03 refuted this: capped at
   exactly the declared ceiling the same endpoints still returned 400, and probes sending twice the
   declared ceiling returned 200. Recorded in
   [`ATTEMPT_02_INSTRUMENT_ABORT/README.md`](ATTEMPT_02_INSTRUMENT_ABORT/README.md).

2. **M116 was cited as having observed `attempts: []` and `pipeline: []`.** It never observed them.
   `safe_router_metadata` initialised both to `[]` and filled them only when the source key was a
   list, so an *absent* field was rendered as an *observed empty* one. Recorded in
   [`ATTEMPT_03_INSTRUMENT_ABORT/README.md`](ATTEMPT_03_INSTRUMENT_ABORT/README.md), and the
   projection was repaired with the closed milestones re-verified unchanged.

## Still unresolved, and not answered by this result

Why the census-dominating stress schema is rejected by the Google routes remains **unestablished**.
The provider returns an opaque error carrying no cause. Finding a route that *accepts* the schema
does not answer why others reject it.

## Claim boundary

M117 measured which schema features candidate endpoints enforce, on small synthetic schemas, on one
date, on a subset of eligible candidates, with a single observation per probe. It is instrument
qualification. **It is not evidence for or against any Genesis scientific proposition, and G1–G10 are
unchanged.**

**M117 has done its job: it found the instrument. M118/H63 tests Genesis.**
