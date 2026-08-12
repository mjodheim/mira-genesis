# M086-C result — NEGATIVE, and this one is about H32

**NEGATIVE SCIENTIFIC RESULT — TRACK A, MODEL-FREE. ATTEMPT 1, NO RERUN. NO GATE MOVES.**

Protocol `09ed0d3` frozen before any harness. Harness `5056a56`. Bank and holdout materialized at
`5948f9a`. Result `67786012…30d14`, attempt 1, no rerun, no model, no network.

**Nine of the ten conditions passed. P2 failed, and it failed on exactly the risk the frozen protocol
named in advance.** Unlike M086-A, whose threshold could not fail, and M086-B, whose bank no mechanism
could repair, this attempt put H32 at risk and H32 lost.

## The verdict table

| | Result | Evidence |
|---|---|---|
| P1 | PASS | adopted 1 meta-transformation, 7 alternatives rejected |
| P2 | **FAIL** | `evolvable_meta` did not solve the holdout on the hidden cases |
| P3 | PASS | `fixed_meta` did not solve it; starting mechanism's image is 0 candidates |
| P4 | PASS | `meta_acquisition_ablated` did not solve it |
| P5 | PASS | `task_only_mutable` did not solve it at triple budget |
| P6 | PASS | the adopted patch is outside the starting mechanism's image |
| P7 | PASS | the causal chain runs from limitation to adoption under forced fault |
| P8 | PASS | fault detected, restored to `2762e65f`, byte-identical to the independent record |
| P9 | PASS | chronology proved from recorded digests |
| P10 | PASS | 6 differential probes against M047's frozen pair |

## What the mechanism did, and where it stopped

Everything up to generalization worked. The lineage met a limitation its mechanism could not express,
searched its four meta-primitives on disposable descendants, rejected seven combinations, adopted
`widen_hypothesis`, survived a forced fault during the adoption transaction with a byte-identical
restore, and on the holdout produced a patch — `synthesize_tool:mean:midpoint` — that the starting
mechanism could never have emitted, since its constructive image for that evidence is empty.

That patch passes the public evidence and is **wrong**.

```
public  : mean 1 2 3  ->  2.0
          mean expression     : (1+2+3)/3 = 2.0   passes
          midpoint expression : (1+3)/2   = 2.0   passes

hidden  : mean 3 4 6  ->  4.333…        midpoint gives 4.5    fails
          mean 2 3 8  ->  4.333…        midpoint gives 5.0    fails
```

The salt drew `1 2 3` — an arithmetic sequence, where the midpoint and the mean coincide. Two
expressions pass the public case, the cycle takes the first in the frozen expression order, and that
is `midpoint`. The evaluator's hidden cases, which the mechanism never saw, reject it.

## Why this is a real negative rather than another instrument failure

The protocol said this before the run, in the section on what was at risk:

> a `mean a b c` case is passed by the `mean` expression always, and by `midpoint` whenever
> `(a + c) / 2 == (a + b + c) / 3`. When both pass the public case, the cycle adopts the first in the
> frozen expression order — which is `midpoint` — and the evaluator's hidden cases then decide whether
> that generalizes. Nothing in this protocol arranges for it to. So P2 can fail on a bank where
> everything else succeeds.

It named the mechanism, the direction and the consequence, and then the draw produced it. This is the
predicted falsifier firing, not a defect discovered afterwards.

## What H32 now stands at

**Not supported.** In this construction, a lineage that modifies the mechanism generating its future
transformations does gain the ability to *emit* transformations the frozen mechanism could not — P6
and P3 together establish that — but the transformation it emitted did not hold beyond the evidence
that selected it. Capability to generate is not capability to solve.

H32 as frozen asks for "a correct outcome the same lineage with a frozen mechanism does not reach".
The lineage reached an *incorrect* outcome the frozen mechanism could not reach. That is a weaker and
different thing, and the hypothesis does not get credit for it.

**H32 is refuted on this bank.** It is not refuted in general: one bank, one salt, one draw whose
public case happened not to discriminate. The honest statement is that the first attempt to put H32
at genuine risk found the meta-improvement insufficient, because widening what the mechanism can
*hypothesise* did nothing about how it *chooses among* the candidates that hypothesis admits.

## The limitation this exposes, which is not the one the experiment was designed around

The meta-primitives all act on the hypothesis schema and the rule set. None acts on the **selection
rule** — the greedy first-past-the-post over public score that decides which generated candidate is
adopted. That rule is frozen, human-authored, and it is what failed here.

M086 has been treating "the mechanism that produces transformations" as diagnosis plus generation.
This result says the pair is incomplete: a mechanism that generates a correct candidate and then picks
a wrong one is not improved by generating more. A successor would have to make the selection rule
mutable too — and would then have to face that selecting well requires evidence the lineage does not
have, which is the same wall from a different side.

That is a candidate M087 and may not be added to this result.

## CI

Run 31582950744: **1,797 passed, 11 skipped** on Python 3.11 and 3.13, plus repository integrity;
attribution run 31582949069 passed.

An earlier run failed on a disqualification regression that asserted the H32 status line still began
UNTESTED — a line this refutation had just changed. The check is now anchored to the sentence
recording M086-A as disqualified, which is what it was actually protecting. **The experiment was not
rerun**: 67786012 is attempt 1 and the bank was never redrawn.

## Claim boundary

No gate moves. This is not evidence for endogenous transformation of an improvement mechanism being
*useful*; it is evidence that in this bounded construction it was not sufficient. Not AGI, not
open-ended evolution, not arbitrary self-improvement, not general autonomy, not a reproduction, and
no contact with M085's fail-closed boundary. No foundation model was called at any point.

The bank is materialized and is not redrawn. A different salt would very likely have produced a
public case that discriminates, and a positive result; that is precisely why it may not be drawn now.
