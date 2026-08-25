# M109 — two successive machinery generations, and recursive depth of two

**Hypothesis:** H54 · **Decision slot:** D078 (reserved) · **Track:** A — endogenous bounded lineage

M108 qualified one lineage-acquired modification of the acquisition machinery. M109 asks whether the
**changed machinery can itself produce the next change**.

## What is different from M108

Two limits were conceded before M108's freeze, and both are what this milestone attacks.

**The blame labels are no longer authored.** In a learning phase the lineage runs a controlled trial
on itself — extend each registered component in turn, observe which extension resolves the demand.
The label is that outcome. The test is necessity rather than sufficiency, declared as
`minimal_necessary_component`. Trials are forbidden at resolution time, where the machinery holds one
step and must attribute without them; that constraint is what makes an attribution rule worth
acquiring at all.

**There are two generations, not one.** A third registered component makes the second possible: the
**candidate space**, which operators the machinery may consider adopting. Restricted to the monotone
operators it is closed — every operator table reachable through it keeps the image monotone — so a
non-monotone demand is excluded from the operator axis by the same lemma M107 and M108 used, at every
node bound.

## The chain

| | |
|---|---|
| `M0` | `{AND, OR}`, width 2, monotone candidate space, attribution hardwired to the operator axis |
| stage one | needs the unread signal; `M0` fails with progress still available on the axis it names |
| generation 1 | trial says **signal interface**; one class survives; `M1` resolves stage one |
| stage two | revealed only now; non-monotone, so the monotone candidate space is closed against it |
| generation 2 | trial says **candidate space**; one class survives; `M2` resolves stage two |
| `ReachImprove` | **6 ⊂ 20 ⊂ 243**, strict at both inclusions, by exhaustive census |

## Why the second generation depends on the first

Two dependencies, and the second was not anticipated when the question was pre-registered.

**Evidence reachability.** `M0` never resolves stage one, therefore never encounters stage two,
therefore never runs its trial, therefore holds no record distinguishing the candidate space from the
operator table.

**Expressibility.** Feature row 3 lies below row 7 componentwise, so every monotone program true at
row 3 is true at row 7. No rule the lineage can express targets the candidate space without also
targeting the signal interface. Generation 2 becomes expressible only once generation 1 has claimed
row 7. This is the monotonicity lemma applied one level up — to the attribution cascade rather than
to the operator table — and it contradicts what the first draft predicted.

## Files

| | |
|---|---|
| `PRE_REGISTRATION.md` | H54, the attribution domain, P1-P18, and three corrections recorded before freeze |
| `ADVERSARIAL_REVIEW.md` | the strongest objections, and the ones that are conceded |
| `DEMAND_STAGE1.json`, `DEMAND_STAGE2.json` | the staged curriculum, in two files that never share a capsule |
| `PROTOCOL.json` | the frozen protocol, once it exists |
| `RESULT.json`, `CHECK_REPORT.json` | the single canonical attempt and its single checker replay |

There is deliberately **no** episodes fixture. The lineage records its own.

## Status

Pre-registered. No protocol, population or result exists until the owner authorizes a freeze.

One canonical attempt and one canonical checker replay are permitted. The first result is preserved
even if negative and may not be repaired.

## What a positive M109 would not license

Recursive depth of three or more; measured acceleration; autonomous invention of the registry, the
feature vocabulary or the curriculum; open-ended machinery growth; transfer to an independently
maintained domain; general-agent evidence; AGI.

Conservative adoption is authored and is **load-bearing for the positive half**: it is not what stops
`M0`, but under non-conservative adoption `M1` fails too and M109 would be negative.
