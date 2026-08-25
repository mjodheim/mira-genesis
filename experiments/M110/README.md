# M110 — does the acquired machinery work outside the laboratory that produced it?

**Hypothesis:** H55 · **Decision slot:** D079 (reserved) · **Track:** A — endogenous bounded lineage

M109 qualified two successive lineage-acquired machinery generations. All of it happened inside one
three-signal Boolean laboratory, so the strongest objection left standing is not *"can it do it a
third time?"* but **"it works because that laboratory was built for it."**

M110 attacks that objection and only that one. It adds no generation, widens no registry, and does
not touch M109.

## The consumer family

Reference-bearing JSON documents over the chain `0 < 1 < 2 < 3`, with a side table. A document's
`zeta` lives in a **different document**, reached by following its `ref`. No interface width exposes
it; only adopting an **accessor** does.

That one structural fact is the whole point. In the producer's world the interface truncates the
signal row, so `g0 ⟹ g1`: a signal the interface cannot read is a signal no operator can recover. A
reference edge breaks that implication — and with it, feature **row 5 = (T, F, T)** becomes reachable
in a domain where it was structurally impossible before.

Expressions are executed twice: by an interpreter that holds no operator semantics, and by rendering
them as Python source, compiling it and running it against the parsed documents.

## Why row 5 decides the milestone

Conservative adoption pins an acquired rule only on rows the producer's census declares reachable.
Rows `{0, 4, 5}` were unreachable there, so **row 5 was never pinned** — yet generation 1's adopted
rule is the program `g0 ∧ g2`, and a program has a value everywhere.

| row | (g0,g1,g2) | in producer census | `M0` | `M1` | `M2` |
|---|---|---|---|---|---|
| 7 | (T,T,T) | yes | operator table | **signal interface** | **signal interface** |
| 3 | (F,T,T) | yes | operator table | operator table | **candidate space** |
| **5** | **(T,F,T)** | **no** | operator table | **signal interface** | **signal interface** |
| 1 | (F,F,T) | yes | operator table | operator table | operator table |

Rows 7 and 3 are where the restored cascades should help. Row 5 is where they fire on evidence they
never had, and the consumer's own controlled trial says the answer there is the operator table.

## H55, both halves

- **H55-a** — inside the producer's census, the restored cascades strictly *increase* capability.
- **H55-b** — outside it, they strictly *decrease* it: a fresh `M0` resolves the demand and both
  `M1` and `M2` refuse.

Either failure refutes H55 and either is a publishable qualified result.

## What transfers, and what does not

**Transferred:** exactly the rule cascade, restored from `experiments/M109/RESULT.json`, verified to
reproduce the frozen `M1` and `M2` state digests, and executed by `m109_runtime.attribute` unchanged.

**Authored on both sides, excluded from the claim:** the component registry and its names, the
three-feature vocabulary, and the consumer carrier, bounds and evaluator. The adapter is identical
across arms — the serialized states differ in `rules` and in no other field, and that is measured.

## Impossibility, not an exhausted budget

Three budget-independent lemmas, measured on every world: every image member is a function of the
visible signals; everything reachable through the monotone candidate space is monotone in the full
signal vector; and the image is a fixed point at node bounds 7, 9, 11 and 13. A deeper-bound control
at 13 nodes is a second line of defence, not the argument.

## Files

| | |
|---|---|
| `PRE_REGISTRATION.md` | H55, the consumer family, P1–P24, and four corrections recorded before freeze |
| `ADVERSARIAL_REVIEW.md` | the strongest objections, and the ones that are conceded |
| `POPULATION.json` | the canonical consumer worlds — worlds only, no census, no label, no target |
| `ADMISSION_LOG.json` | which seeds were admitted and why the rest were not |
| `PROTOCOL.json` | the frozen protocol, once it exists |
| `RESULT.json`, `CHECK_REPORT.json` | the single canonical attempt and its single checker replay |

## Status

Pre-registered, apparatus complete, development rehearsal passed. **No protocol and no result exist
until the owner authorizes a freeze.**

One canonical attempt and one canonical checker replay are permitted. The first result is preserved
even if negative and may not be repaired.

## What a positive M110 would not license

Independent external-domain transfer — the consumer family is project-authored. Open-ended machinery
growth; recursive depth of three; measured acceleration; autonomous invention of the registry, the
vocabulary or the carrier; G1–G10 closure; general-agent evidence; AGI.

The defensible phrasing is **bounded multi-generation acquisition-machinery improvement with
census-conditional causal transfer**, and nothing stronger.
