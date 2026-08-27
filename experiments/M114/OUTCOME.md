# M114 — instrument-aborted. Three capacity rejections, no bank, H59 untested.

**Date:** 27 August 2026
**Hypothesis:** H59 — **untested**
**Verdict:** `instrument-aborted`
**Decision slot:** D083 — remains reserved and unfilled

## What happened

The frozen delivery sequence ran to the end of its budget. Three physical requests, three explicit
HTTP 429s, zero bank materializations. The model was never reached.

| attempt | at | waited | status | outcome |
|---|---|---|---|---|
| 1 | `2026-08-27T13:02:39.651683Z` | 0 s | 429 | `capacity_rejected` |
| 2 | `2026-08-27T13:03:40.998453Z` | 60 s | 429 | `capacity_rejected` |
| 3 | `2026-08-27T13:04:41.963583Z` | 60 s | 429 | `capacity_rejected` |

Delivery ledger digest: `96c77d492e20b0621c6dfc3bc06dbb7d6b3c00c3537c204b1a28039d913ebac8`

## This is not a negative result for H59

Nothing ran against a bank. No carrier was produced, no qualification was attempted, `P22` was
neither computed nor approached. **H59 is exactly as untested as it was before the sequence began**,
and exactly as untested as H58 remains.

A negative result is a measurement: the machinery ran against a bank and did not do what the
hypothesis predicted. This is a fact about a queue.

## What the evidence says, and what M113's could not

All three responses are **byte-identical** — one distinct digest,
`f0a0b94cf22fdeeee8fb28abffc34bff…`, across three attempts one minute apart. Each names its own
cause, in the provider's own words:

| field | value |
|---|---|
| `provider_error_code` | `service_overloaded` |
| `limit_source` | `upstream_provider_shared_pool` |
| `provider_name` | `Morph` |
| `is_byok` | `False` |
| `retry_after_seconds` | `1` |
| `raw` | `deepseek/deepseek-v4-flash-0731 is temporarily rate-limited` |

This is the difference M114 was built to produce. M113 made one request, got a 429, and its client
discarded the body — so its record carries a status code and nothing else, and the cause had to be
inferred. M114's record names the cause three times, from three independent responses, and the
delivery contract preserved every one of them.

**The provider asked for a 1-second wait. The frozen rule waited 60, sixty times longer, and was
rejected anyway — twice.** That is worth stating plainly: the rejection is not a momentary burst
that a slightly longer pause would have cleared. A shared upstream pool with no dedicated key was
saturated for at least the two minutes the sequence spanned.

## What the frozen rule did, and did not, permit

Every clause held. The ledger validates in full:

- 3 delivery attempts against a frozen budget of 3;
- every attempt sent the byte-identical frozen body `02a71fb5…`;
- no provider or model substitution — nothing was served, so nothing could be substituted;
- each outcome recomputed from its own evidence: status exactly 429, no completion present, nothing
  indicating the model executed;
- the frozen 60-second wait honoured before attempts 2 and 3, and 0 before attempt 1;
- zero materializing responses, so nothing followed one.

**No fourth attempt exists to take.** The budget is spent, and the frozen spec
`e12337a4a78045394e4db7b39cb710d3c6dacbd435d01f9a92530e239c288fc3` can never authorize a bank: the
phase machine reads the ledger and concludes it directly — *no delivery attempt materialized a bank;
the frozen budget of 3 attempts produced none*.

Nothing is relaunched under M114. Whether a successor milestone is opened, and with what instrument,
is the owner's decision and was not taken here.

## What M114 established anyway

The milestone did not test its hypothesis. It did establish, in a way M113 could not, that:

1. **The failure is reproducible and named.** Three identical rejections from a shared pool, not one
   ambiguous event.
2. **The delivery separation works as designed.** Three physical network requests were made and
   zero model calls occurred, and the record reports those as two different numbers —
   `physical_delivery_attempts: 3`, `bank_materializations: 0`. Under M113's protocol there was no
   vocabulary in which to say that.
3. **The corrective `P15` refuses this record**, and refuses it for the right reason: the
   qualification half and the delivery half both hold, and the generator half does not, because
   there is no bank. An abort is distinguishable from a violation and from a negative.
4. **The instrument constraint is not a matter of patience.** A 60× margin over the provider's own
   `Retry-After` changed nothing.


## A redaction, recorded

OpenRouter's 429 envelope carries a `user_id` field identifying the account that sent the request.
It is not the API key and grants no access, but it identifies the owner's account and this record is
published, so it is replaced with a marker in all three attempts.

The redaction is recorded inside the ledger it touches, under `redactions`, together with the
ledger's digest before it — `6a0684f75e8a9af0e180ebcff7e76b988ae56c5963e92aa1ed5adf8d9e999ebe` — so
that the change is auditable rather than invisible. **No quantity the frozen delivery rule reads was
touched**: status, timing, waits, request-body digests, response digests, served provider and model,
completion presence, model-execution evidence, outcomes and retry permissions are all exactly as the
instrument wrote them, and the ledger still validates in full. The cause the provider named survives;
only the caller is gone.

The generation client now strips identifying fields at capture, so no future ledger can carry one.

An intermediate revision of the development branch carried the unredacted value, and the test first
written to assert its absence quoted it in order to check for it — the same defect one level up. The
branch history was **rewritten before merge** to remove both, so neither enters `main`'s ancestry,
and the test now matches the identifier's shape rather than its value. The rewrite changed no
measured quantity, and the chronology it preserves is still demonstrable in Git: the freeze precedes
attempt 1, which precedes attempts 2 and 3, which precede this record.

## What stands

M113 is untouched and remains closed; H58 remains untested. The M114 plan and generator spec remain
frozen and are not re-frozen. No seal, no public commitment, no tested-system freeze, no reveal, no
qualification, no canonical run and no result exist. **No generality gate moved.**
