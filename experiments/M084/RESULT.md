# M084 result — one persistent lineage across three real substrates

**POSITIVE QUALIFIED DEVELOPMENT RESULT — TRACK A, MODEL-FREE.**

Protocol `ecb297c` frozen before any harness code. Harness and amendments A1–A3 at `f19af86`.
Bank `a4081e5b…7f047` bound before the run. First result `1cbeef8a…f830b`, attempt 1, no retry, no
external model, no network.

## What ran

One organism, serialized to a file between stages, each stage executed in a **separate operating
system process**:

`shell → browser → desktop → shell`

Four stages over three real isolated substrates, ending where it began. Every stage opened a fresh
container. Nothing survived between stages except the bytes the organism carried.

Four goals per stage, each a desired state of a carrier group with no decomposition supplied: one
whose cheapest carrier silently discards, one requiring a carrier to be cleared, one control with no
trap, and one whose only carrier discards. Eleven are reachable; five are not.

## The lineage arm

| Stage | Substrate | Reached | Refused | False refusals | Probes / repairs / affordance probes | Actions | Reads | Over-report | Predicate |
|---|---|---:|---:|---:|---|---:|---:|---:|---|
| 0 | shell | 3/3 | 1 | 0 | 1 / 1 / 1 | 11 | 18 | 2 | `sea` |
| 1 | browser | 3/3 | 1 | 0 | 1 / 1 / 1 | 7 | 12 | 1 | `sea` |
| 2 | desktop | 2/2 | 2 | 0 | 1 / 1 / 1 | 6 | 11 | 1 | `r3` |
| 3 | shell | 3/3 | 1 | 0 | **0 / 0 / 0** | 3 | 7 | **0** | `sea` |

**11/11** reachable goals reached, scored from environment state. **5/5** unreachable goals refused.
**0** false refusals and **0** unreachable goals recorded as reached.

## What made the fourth stage cheap

Stage 3 is the shell again, with **carrier names stage 0 never saw**. The organism did not act on the
trap at all, did not probe, did not repair and did not rediscover removal, because it still carried:

- the induced rejection predicate `sea`, which separates the discarding `sealed-*` family from the
  durable `secure-*` family on two characters and therefore applies to names it has never met;
- the fact that removal is effective in this substrate.

It also over-reported **zero** times in stage 3 — not because the substrate stopped lying, but because
the organism never gave it the chance.

## The controls

| Arm | Reached | Refused | Probes | Repairs | Cost, stages 1–3 | Transformations adopted | Final version | Continuity proofs failed |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `lineage` | 11/11 | 5 | 3 | 3 | **46** | 1 | 1 | none |
| `acquisition_ablated` | 11/11 | 5 | 4 | 4 | **85** | 4 | 4 | none |
| `fresh_each_stage` | 11/11 | 5 | 4 | 4 | 85 | 4 | 1 | 4 of 5 |

`acquisition_ablated` is the same lineage — same identity, same journal, same version — with its
facts and adopted policy cleared at every stage boundary. In the returning stage it needed **1 probe,
1 repair cycle and 1 affordance probe** where the complete lineage needed none, and it re-adopted the
identical transformation in every stage, ending at body version 4.

`fresh_each_stage` reproduced the ablated arm's behaviour **metric for metric** in all four stages,
which is what shows the ablation is not leaking. It failed four of the five continuity proofs.

**What the ablation does not cost is correctness.** Every arm reached every reachable goal and refused
every unreachable one. What persistence bought here is cost and earliness: 27 actions and 48 reads
against 43 and 71, and one wasted action on an impossible goal instead of four.

## Descent

| Proof | Result |
|---|---|
| one lineage identity across four stages | held |
| body version never resets | held |
| journal extends the genesis chain, verifying and strictly growing | held |
| serialization chain unbroken | held |
| checkpoint at every stage boundary | held |

The organism records the SHA-256 of the file it loaded, so the chain of serializations is carried by
the lineage rather than asserted by the harness. No stage ran in the parent process.

## The forced fault

After stage 1 the parent broke the journal chain and erased the browser predicate, outside the
checkpoint blob. The **stage-2 child** detected the broken chain on load, restored from the last
checkpoint and returned digest `81d9d437…`, which equals the digest **stage 1 had recorded before the
corruption existed**. The comparison is never against the checkpoint's own stored digest; that is the
tautology M080 recorded.

## Self-report, measured from inside the loop

The environment's own acceptance diverged from its state **2, 1 and 1** times in the first three
stages. M081, M082 and M083 measured that divergence from outside, with an agent that could not see
it. Here the organism has to act on it, and the divergence is what teaches it.

## Two observations worth keeping

**The desktop predicate over-generalizes.** Only one non-durable carrier is observable there — the
locked cell `r3c5` — so the shortest separating prefix is `r3`, which would also reject `r3c0` through
`r3c4`. No goal uses them, so nothing was falsely refused, but the induction is weaker than the `sea`
it forms on the name-addressed substrates and the result should not be read as if it were the same.

**A fact is not carried between substrates.** The shell and the browser discard the same authored
prefix, and the organism still re-derives it in the browser from scratch. Carrying it would have been
cheaper and would have been the relabelling this repository forbids. What crosses substrates is the
adopted policy, not the substrate-local fact.

## What this is not

Not AGI, not general autonomy, not open-ended evolution, not cross-domain transfer, not a closed G4,
G6 or G7, not general desktop competence, not structural retention without replay, and nothing about
privately maintained external tasks. Goals, carriers, applications and substrates are all
project-authored. Eleven reachable goals over four stages is a small bank. M080's retention remains
replay-dependent and nothing here changes that. The M075 pre-private boundary is untouched.

No external model was called, no network was opened, and no repository, credential, deployment or
permission authority was granted to the organism.
