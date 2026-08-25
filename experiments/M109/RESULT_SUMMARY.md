# M109 / H54 — canonical result

> **VERDICT: POSITIVE (attempt 1). H54 supported within its frozen bounds. D078.**

Deliberately **outside** the protocol's bound apparatus list, so every bound member keeps the exact
bytes it had at freeze time and `experiment/m109-frozen-protocol-v1` stays verifiable by anyone.

| | |
|---|---|
| frozen protocol | `8e76b30fe8ad645d2b695a372525462d27f66990a9f8d264411c0b2ed8c75178` |
| bound apparatus | `5d5dfac1dd082c9080c9571679e0e9c8c9fe1bd3f1010a4aaa2c203794580272` |
| result | `262e0bd5b67b573a01f00293ec1fef79da94908819006f08acb8bd30d6941f09` |
| stable evidence | `0c6ad0c2930f8dd25b8ccf2e9692615845c4326da109d752672dc7f989e1a576` |
| raw result bytes | `0af98fb45a279fec9224bddbb4fa069d140cf21e94a3bb00699ba8c85e0c8009` |
| check report | `ff1675738b6aabc358d2cfb568d93dec396c7beff8b8b68e14c09ecc011ea24a` |
| runtime | CPython 3.11.16 |

P1-P18 all computed true; replay performed and equal; zero model, network and remote-execution calls
across twenty-one isolated processes. The stable projection is byte-identical to the one produced by
the pre-freeze rehearsal in a throwaway clone, so the evidence carries no accident of this checkout.

## The chain

| | |
|---|---|
| `M0` | `{AND, OR}`, width 2, monotone candidate space, attribution hardwired to the operator axis; reach **4** |
| attribution domain | rows `{1, 2, 3, 6, 7}` by census over **84 states** and all 256 world functions, **10 496** determined pairs, **no ambiguous row** |
| monotone candidate space | closed by the monotonicity lemma, budget-independent, 9 candidates |
| stage one, hardwired | refuses — and `g2` is **true** at that failure, so the axis it names still offered progress |
| — at bound 13 | refuses again: reach, not budget |
| generation 1 | trial says **signal interface**, by the lineage's own experiment; 2 consistent rules of 18, **one class** |
| `M1` resolves stage one | width 2→3, witness 5 nodes, executes to target |
| stage two, revealed only now | `M1` falls back to the hardwired axis and refuses |
| generation 2 | trial says **candidate space**; 2 consistent, **one class**; rule distinct from generation 1 |
| `M2` resolves stage two | candidate space monotone→complete, witness 4 nodes, executes to target |
| **ReachImprove** | **6 ⊂ 20 ⊂ 243** — strict at both inclusions, +14 then +223 |

## What the controls returned

| | |
|---|---|
| a fresh `M0` handed stage two's record | **refused** — `no_expressible_rule_reproduces_the_trial_record`, **0** consistent rules |
| a record naming two components | refused |
| a record with nothing left uncovered | refused |
| ablation of generation 2 | byte-exact return to the state before it; stage two lost |
| mutation of generation 2 | attribution changes; stage two lost |
| corruption | fails closed on identity mismatch |
| curriculum boundary | producer capsules held no demand; stage capsules held only their own |
| blame labels | lineage-determined in every episode; no trial at resolution time |

**This is the first Genesis result in which a modified acquisition machinery produces the next
modification**, and in which the blame labels are the lineage's own experimental findings rather than
host annotations.

The dependency between generations is a **lemma**, not a failed search: feature row 3 lies below row 7
componentwise, so every monotone program true at row 3 is true at row 7, and none of the eighteen
programs the lineage can express targets the candidate space without also targeting the signal
interface. That is the monotonicity lemma M107 and M108 used, applied one level up — to the
attribution cascade rather than to the operator table.

## Conceded, and declared before the freeze

The registry, the feature vocabulary and the staged curriculum remain **authored**. The trial's
asymmetry between components is real and declared as `minimal_necessary_component`. Conservative
adoption is **load-bearing for the positive half**: it is not what stops `M0`, which is refused under
both adoption rules, but under non-conservative adoption `M1` fails too and M109 would be negative.

Recursive depth of **three** is unmeasured, and so is acceleration.

It is **not** recursive self-improvement: two rules of three nodes each, over three authored features,
in a three-signal Boolean world, with the budgets and the evaluator fixed.

See `../../DECISIONS.md` (D078), `PRE_REGISTRATION.md` and `ADVERSARIAL_REVIEW.md`.
