# M110 / H55 — canonical result

> **VERDICT: POSITIVE (attempt 1). H55 supported within its frozen bounds — both halves. D079.**

Deliberately **outside** the protocol's bound apparatus list, so every bound member keeps the exact
bytes it had at freeze time and `experiment/m110-frozen-protocol-v1` stays verifiable by anyone.

| | |
|---|---|
| frozen protocol | `05826a375eb1106e1a98dd0e66e804f7a7abee8964569e1b37c7ba25d7796c8e` |
| bound apparatus | `becccc1c94327eed55b622b224522d041166d7edb6e9323835ba7c9b338c9bbc` |
| population | `d4e8ae471eb46bbf1bc40f51746cef83d6f5ea3a65c1eadd4388b8b07cdaa33e` |
| producer result (M109) | `262e0bd5b67b573a01f00293ec1fef79da94908819006f08acb8bd30d6941f09` |
| producer raw bytes | `0af98fb45a279fec9224bddbb4fa069d140cf21e94a3bb00699ba8c85e0c8009` |
| result | `cbd3ea3e98986584c54ed02c41e5fbc1afc5a25dec2cbc9f1a9d6b9e46802744` |
| stable evidence | `92ee5e051d9a955c500f6006f273b17e8d70dd0ffeda48cba8aca17a7146bfb7` |
| raw result bytes | `163a46dadd815d98d03fede22905a181c4d406a19d391c5ee2631efc3a2488e3` |
| check report | `e598b95cea85d6b1dff53afa81a03c3f6d2ab307e512edc0d8abbc928beeec83` |
| runtime | CPython 3.11.16 |

P1–P24 all computed true; replay performed and equal; zero model, network and remote-execution calls
across **186 isolated processes** over six canonical worlds.

**The stable evidence digest is byte-identical to the one `PRE_FREEZE_REHEARSAL.md` predicted before
the freeze**, in a throwaway clone that received the sources with CRLF. That prediction sat inside a
bound apparatus member, so it could not have been reconciled after the fact.

## The chain, unanimous across all six worlds

| demand | producer census | ground truth | `M0` | `M1` | `M2` |
|---|---|---|---|---|---|
| row 7 | inside | signal interface | **0/6** | **6/6** | **6/6** |
| row 3 | inside | candidate space | **0/6** | **0/6** | **6/6** |
| **row 5** | **outside** | **operator table** | **6/6** | **0/6** | **0/6** |
| row 1 | inside | operator table | 6/6 | 6/6 | 6/6 |

Both halves of H55 hold, and they hold with no world dissenting.

**H55-a.** Inside the producer's reachable attribution census, the restored cascades strictly add
capability: `effect(M2) > effect(M1) > effect(M0)`. The rules were derived in a three-signal Boolean
truth-table laboratory and carried, unchanged and unretrained, into reference-bearing JSON documents
over a four-valued chain.

**H55-b.** Outside it, they strictly *remove* capability. At row 5 a fresh `M0` resolves the demand
on every world and both `M1` and `M2` refuse on every world — because the acquired program `g0 ∧ g2`
fires there and names the signal interface, while the consumer's own controlled trial says the answer
is the operator table.

## The dissociation this milestone exists to measure

`ReachImprove` is strict on **every** world, `M0` ⊂ `M1` ⊂ `M2`, ranging across the population from
94–261 for `M0` to 134–449 for `M1` to 324–558 for `M2`.

So **capacity rises monotonically across the generational chain while realized competence does not**.
The acquired machinery enlarges the set of targets the lineage could in principle reach and, on a
failure geometry its producer could not present, misroutes the one step it is allowed and ends up
strictly worse than the predecessor it improved on.

## Why the negative half was derivable, and why it still had to be run

Conservative adoption pins an acquired rule only on rows the producer's census declares reachable.
That census found rows `{1, 2, 3, 6, 7}`; rows `{0, 4, 5}` were unreachable. Rows 0 and 4 are
impossible in **any** domain implementing these feature semantics, because `¬g1 ⟹ g2`. Row 5 is
different: it is excluded only by `g0 ⟹ g1`, which is a property of prefix truncation, not of the
vocabulary. A reference edge breaks it.

The conservatism guarantee therefore says nothing off the producer's reachable row set, and an
expressible program extrapolates there whether or not it should. The consumer census confirms the
geometry is genuinely new: **row 5 is reached by the consumer and by no producer state**, while
labels agree with the producer on every shared row and are world-invariant across the population.

## What the controls returned

| | |
|---|---|
| deeper bound, 13 nodes | `M0` still refuses rows 7 and 3 — reach, not budget |
| monotone-closure certificate | confirmed on every world, budget-independent |
| visible-function lemma | zero violations at every interface width, every world |
| fixed point at bounds 7/9/11/13 | confirmed on every world |
| ablation of generation 2 | byte-exact return to `M1`; row 3 lost |
| ablation of generation 1 | byte-exact return to `M0`; row 7 lost, **row 5 regained** |
| mutation of generation 2 | row 3 lost |
| built but unregistered | capsule held the rule bytes, state held none: refuses |
| corruption | fails closed on identity mismatch |
| arms | differ in `rules` and in no other field; identical world and demand bytes |
| host shortcut | a host-widened space resolves row 3, a host-widened interface resolves row 7 |

## Conceded, and declared inside the frozen protocol

The consumer family is **project-authored and not independently maintained**, so **G4 does not
advance** to independent transfer. The component registry and the three-feature vocabulary are shared
authored vocabulary, imported from the producer module rather than transferred content. The family
was **chosen** to reach row 5 — a deliberate stress test, not a neutral sample. The host can widen
either component directly, which is why the claim is about *which component the cascade decides to
extend*, not about reach the host lacks.

Recursive depth of **three** is unaddressed, and acceleration is unmeasured.

It is **not** recursive self-improvement, and it is not evidence of generality: two rules of three
nodes each, restored from a frozen file, over three authored features, in five-document worlds with
fixed budgets and a fixed evaluator.

## The defensible claim

**Bounded multi-generation acquisition-machinery improvement with census-conditional causal
transfer** — and the condition is the point. The acquired machinery is generic within the failure
geometry its producer could present, and actively harmful outside it.

See `../../DECISIONS.md` (D079), `PRE_REGISTRATION.md`, `ADVERSARIAL_REVIEW.md` and
`PRE_FREEZE_REHEARSAL.md`.
