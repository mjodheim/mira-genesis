# A withdrawn M114 freeze, recorded rather than erased

On **27 August 2026 at 11:34:19Z** this milestone's analysis plan and generator spec were frozen.
That freeze is **withdrawn**. This file exists so the withdrawal is part of the record instead of a
gap in it.

## What was frozen

| | |
|---|---|
| `ANALYSIS_PLAN.json` | `cd359081dabb3ba8c57133de0538bea648159bef1e97d8f4a8f59819adb868d9` |
| `GENERATOR_SPEC.json` | `bb56275a5ed115a607346a0a8210ca1122c8787f78a1d3238a981576d7b523dd` |
| plan commitment | `d191f74df43526b35e39095c62b2329fe47fb467d9c5167f0eb3bf935b1c0339` |
| spec commitment | `85b864426fbb97467062978119b60b5c0c65ea93fbee9fafaa739aa85d697c73` |
| frozen at | `2026-08-27T11:34:19.526156Z` |
| commit | `b98116d8e8cf92478876bfb9ba6c48c3d541db4b` |

Those bytes are still reachable in the history at that commit. Nothing about them is being denied.

## Why it is withdrawn

The freeze was consumed one step too early. The owner's authorization sequences the freeze **after**
the apparatus PR merges, and a pre-freeze defect was still open at the moment the freeze ran:

> M113 defines `P15`'s generator half as the number of **physical invocations**, on the stated
> ground that a series of physical requests must not be presentable afterwards as one logical
> invocation. M114's first form set `model_calls_in_bank_generation = bank_materializations`, which
> silently changed what `P15` means — while the same milestone claimed `P1`–`P22` were imported
> unchanged and that delivery semantics were the only thing that moved.

That is a real inconsistency between what M114 claimed and what M114 did, and it is a defect in the
predicate rather than in a result. Repairing it changes the analysis plan, and therefore the plan
commitment and the spec commitment that binds it.

## Why withdrawing costs nothing scientifically

The freeze exists to make an instrument un-choosable before it produces anything. Between the freeze
and this withdrawal:

- **no delivery attempt was made** — `DELIVERY_LEDGER.json` never existed;
- **no bank was materialized** — `GENERATION_RESPONSE.json` never existed;
- **no seal, no public commitment, no tested-system freeze, no reveal, no result** existed;
- **nothing about `H59` was observed**, because nothing was ever sent.

So no choice was made under the withdrawn freeze that this milestone could now be selecting on. The
freeze constrained an instrument that never acted. That is the whole reason a withdrawal here is a
correction and not a repair of a result — and it is exactly the distinction M113's record exists to
protect, applied to M114's own procedure.

## What is not affected

M113 is untouched. Its four pinned digests, its `aborted` ledger entry, its closed record and its
`H58 untested` status are exactly as they were, and `tests/test_m113_record_is_closed.py` still
fails if any of that moves.

## What happens next

The `P15` correction lands first, in the open, as `m114-phase-boundary-v1`. The plan and spec are
then re-frozen under the owner's authorization, after the apparatus PR merges, with new commitments
recorded in the ordinary way. A freeze that had been quietly re-run over this one would have left the
record claiming a single freeze where there were two.
