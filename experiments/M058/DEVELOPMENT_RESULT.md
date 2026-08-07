# M058 — development result

## Status

**POSITIVE ON ITS CENTRAL QUESTION — PENDING QUALIFICATION.**

The lineage discovered which instructions exist, and found operations no authored list contained.
This is a bounded, noncanonical development result.

## What was observed

| Observation | Value |
|---|---|
| Opcode space scanned | **256** bytes |
| Refused by the substrate's validator | **247** |
| **Operations discovered** | **9** |
| Authored by M057 | 6 |
| **Added by discovery** | **`0x0f`, `0x1a`, `0xa6`** |
| Admissible space, three parameters | 943,636 |
| Candidates constructed for `mean` | 82,693 — **8.8 %** |
| Composed tool | `mean` → `0xa3(0xa0(p0,0xa0(p1,p2)),k)` |
| Hidden-domain verification | all four tools |
| Inherited capabilities on the discovered set | **32 / 32** |
| Declared imports | **0** |

## What discovery found that a person had not

`0xa6` is `copysign` — a genuine arithmetic operation that M057's authored list simply omitted.
An oversight, and exactly the kind a hand-written list produces.

`0x0f` and `0x1a` are more interesting. They are `return` and `drop`, and in this position they
behave as **projections**: `0x0f` returns its second argument, `0x1a` its first, on every scan
pair. No designer writing a list of "binary operations" would have entered them, because they are
not arithmetic at all. The substrate accepts them; the category was the human's, not the
machine's.

So the authored list was both **too narrow** — it lacked `copysign` — and **wrongly conceived**,
because it assumed *operation* meant *arithmetic*. That is the substance of this result, and it
is what M057 could not have shown.

## The margin, and why it improved honestly

M057 constructed about a sixth of its admissible space. M058 constructs **8.8 %** of a space
three times larger.

The improvement is earned rather than declared. The space grew because the lineage **found more
operations**, not because a bound was widened after the fact. M057's result refused to inflate
its ratio by declaring a larger maximum expression size, on the grounds that it would change
nothing the search does; this margin changes because the search really has more to work with.

## Ablation

Denying composition fails on `mean` alone, and on nothing else. Without composition the lineage
reaches `add`, `max` and `mul` — the tools a single operation satisfies — and stops. Discovery
without construction is not enough, which is the same falsifier M057 recorded and the same
outcome.

## The boundary that remains

**The signature shape is authored by a human**: two `f64` values in, one out. The lineage
discovers which operations exist *in that shape*, not that the shape exists.

An operation of another arity, of another type, or one acting on linear memory would not be found
by this scan. M058 does not claim otherwise, and this is the next thing to remove.

The request shell also stays in JavaScript, as in M056 and M057.

M058 does not establish arbitrary runtime discovery, unrestricted code generation, open-ended
evolution, general intelligence, consciousness or production safety. Network, repository,
credential, deployment and external-system authority remain human-controlled.

M058 is noncanonical. **M042 remains the only positive canonical continuous-lineage
completion.**

## The line this completes

| Experiment | What the lineage was given | What it had to find |
|---|---|---|
| M048 | a compiler, a target runtime, a migration instruction | nothing about the crossing |
| M056 | a compiler, a target substrate | that its acquisitions survive a second crossing |
| M057 | six named operations | what they do, and how to compose them |
| M058 | a signature shape | **which operations exist**, what they do, how to compose them |

Each step removed something the previous one was handed. What remains handed is the shape of the
question, and the fact that a substrate is worth moving to at all.
