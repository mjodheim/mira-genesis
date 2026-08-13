# M089 — Endogenous Meta-Language Extension

**The lineage extends the language it uses to improve itself.**

**STATUS: FROZEN BEFORE QUALIFICATION MATERIALIZATION. ONE ATTEMPT. NO REROLL.**

## The ceiling this attacks

D058 closed M088 by naming what remained: the lineage composed meta-operations we wrote and
invented none. M089 asks whether it can add a **new fundamental operation** to that language when
the language cannot express the modification it needs.

## Why this is not M055 again

D019 closed the M053–M055 line because the acquired capability was already reachable:

> the from-scratch arm still solves the reuse task — 737 candidates without the acquisition against
> 48 with it. **The acquisition made the search fifteen times cheaper and made nothing newly
> reachable.**

That is the central falsifier here, and it is answered structurally rather than by hope. L0 is
given an invariant that **no composition of its operations can break**, and the qualifying
transformation is one that requires breaking it.

## L0 and its invariant

Three operations over a record of four slots, given three inputs:

| Operation | Effect |
|---|---|
| `SET_CONST(slot, c)` | write a literal |
| `COPY_INPUT(slot, k)` | copy one input position |
| `APPLY_UNARY(slot, u)` | apply a one-argument function to a slot, in place |

**Invariant.** For every L0 program, every slot depends on **at most one** input position. By
induction on length: `SET_CONST` clears the dependency set, `COPY_INPUT` sets it to a single index,
and `APPLY_UNARY` is one-argument so it cannot change it. No operation reads two values. The bound
therefore holds at **any** length and **any** budget — this is a proof, not a failed search.

Confirmed twice over: the invariant argument, and an exhaustive enumeration of every source
signature reachable at length ≤ 3, whose maximum is 1.

## The extension substrate S

A typed stack machine with eight micro-operations — `PUSH_INPUT`, `PUSH_SLOT`, `PUSH_CONST`,
`BINOP`, `UNOP`, `DUP`, `SWAP`, `STORE_SLOT` — from which a primitive body is **assembled**.

**Why S is not the answer encoded.** S is *lower level* than L0, not a superset. It has no notion
of a program over an input record, no sequencing against a task, and cannot be executed by the
lineage at all unless a body is first registered as an L0 primitive. No micro-operation is a
finished primitive; several must be assembled before anything happens. Of 54,240 enumerable bodies,
904 are well-formed and only **8** can break L0's invariant.

The one structural fact that matters: `BINOP` pops **two** values. No L0 operation does.

## The task is stated as behaviour, never as a primitive

The development task says *slot 0 must equal input 1 plus input 2*. It does not say "you need a
binary operation" and it names no micro-operation. The requirement is measured behaviourally —
how many input positions must some output slot depend on — by perturbing one input at a time.

## Two capabilities, both required

**A** — build a primitive that is not macro-reducible to L0.
**B** — registering it makes a previously inexpressible transformation constructible, and that
transformation produces the correctness difference.

Each is observable missing: `extension_built_but_not_registered` has A without B — the primitive is
built and validated and simply never enters the language — and `macro_only_extension` has neither,
because its substrate is restricted to micro-operations that cannot break the invariant.

## Arms

| Arm | What it has |
|---|---|
| `evolvable_meta_language` | L1, restored from serialized form |
| `fixed_meta_language` | L0 |
| `extension_acquisition_ablated` | acquired the extension, then lost it |
| `extension_built_but_not_registered` | the primitive exists; the language does not contain it |
| `macro_only_extension` | may build primitives only from invariant-preserving micro-ops |
| `more_budget_same_meta_language` | L0 at **100× real** independent exhaustive searches |
| `fresh_agent` | L0, no history |
| `authored_correct_primitive` | **ceiling only** — handed the primitive |

## Chronology

```
T0 hypothesis and protocol frozen      T10 rollback proof before extension
T2 L0 digest frozen                    T11 stable L1 adoption
T3 substrate S frozen                  T12 L1 serialized and digested
T4 development limitation materialized T13 qualification drawn, separate process  <- after T12
T5 proof L0 insufficient               T14 transformation constructed under L1
T6 primitive candidates constructed    T15 hidden evaluation
T7 disposable validation               T17 rollback proof after extension
T8 primitive selected                  T18 result preserved
```

## Ten conditions

P1 L0 provably cannot express the transformation · P2 primitive constructed from the substrate
after rejections · P3 primitive not macro-reducible to L0 · P4 primitive independently validated ·
P5 language extended and versioned · P6 transformation constructible only under L1 · P7 capability
discordance against fixed · P8 macro-only **and** unregistered extensions both fail · P9 more budget
in the same language cannot close it · P10 language persisted and restored on **both** sides of the
extension.

## What a positive result would not establish

Not AGI, not open-ended evolution, not arbitrary self-modification, not general programming-language
invention, not recursive self-improvement, not general autonomy, no gate, no independent
reproduction, no production authority.

**The substrate S remains authored.** That is the next ceiling, and it is the honest subject of
whatever follows rather than a caveat on this.
