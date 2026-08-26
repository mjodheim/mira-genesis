# M112 — a defect in the frozen spec, recorded before reveal

**Recorded after the single qualifying invocation and before the bank was sealed, committed,
revealed, stratified or read. Nothing about the bank's contents was known when this was written.**

## What is wrong

The frozen `GENERATOR_SPEC.json` sets

```
"requested_record_count": plan["requested_world_count"]
```

and the frozen `GENERATOR_PROMPT.txt` asks for **N entries, each entry being one document**. A world
in this carrier is **five documents**.

So `N = 100` asks the generator for 100 documents, which is **20 worlds** — not the 100 worlds the
analysis plan requested. The spec assigned a world count to a record count. The generator did exactly
what it was asked; the error is entirely in the freeze, and it is mine.

## What it costs

At the base rates measured over 1 160 project-generated worlds:

| | 100 worlds (planned) | 20 worlds (actual) |
|---|---|---|
| expected ambiguous | 6.0 | **1.2** |
| expected witness | 36.0 | 7.2 |
| plan minimum ambiguous | 3 | 3 |
| rough chance of meeting it | ~94 per cent | **~12 per cent** |

The materialization is therefore **under-powered against its own plan**. It is not doomed — twelve
per cent is a real probability, and the blind generator's distribution need not match the
project-generated base rate — but the likely outcome is that the bank yields fewer than three
ambiguous worlds and M112 is recorded **negative**.

## Why it is not being repaired

Re-freezing with a corrected `N` and generating again would be a **second qualifying invocation after
learning something about the first**. The stated reason would be an arithmetic bug; the effect would
be a retry that raises a threshold's chance of being met. That is the pattern this project refuses,
and it is refused here.

The frozen plan already says what happens: a bank yielding too few worlds is a **negative result, not
a retry**, and `retries_permitted` is `false`. That rule was fixed before the bank existed and it
decides this case.

So the materialization proceeds exactly as frozen: envelope, seal, commitment, tested-system freeze,
reveal, public stratification, and whatever verdict the plan produces.

## What a successor may do

A successor milestone may freeze a corrected spec — `requested_record_count = 5 × requested_world_count`
— and run **its own** single invocation. It may not reuse this bank, relabel this attempt, or describe
this defect as repaired. M103 → M104 is the precedent: the instrument was corrected in a fresh
milestone and the failed one stayed failed.

## Timing, so the order is checkable

| | |
|---|---|
| qualifying invocation completed | `created_at` `2026-08-26T05:42:37Z`, `done_reason` `stop`, 5 488 tokens, 617 s |
| raw response sha256 | `0129de5f6af27740895b68e951482eb50e51bd839bf4ab326d92bfecd073be6a` |
| generated payload sha256 | `ee6e3d5d6b76189bba72f16601e6b09e9289c4e6465c7a3ce4b736e4bf2e098f` |
| records emitted | 100 |
| this note written | before the envelope, the seal and the commitment |
| bank content read | not at the time of writing, and not for stratification until after F2 |

The record count and the response digests are transport-level facts about the invocation. No world
was constructed, classified or inspected to write this.
