# M112 / H57 — canonical result

> **VERDICT: MIXED (attempt 1). D081.**
> Procedural independence **established, 10/10**. Diagnosis **reproduced, 24/24**.
> Transfer **22/24, negative under the inherited rule**.

## Evidence tier, unchanged from the pre-registration

`blind_generated_sealed_bank`.

**Established:** generator context blindness; procedural independence; removal of project world
selection and authorship.

**Not established:** human independence; independent human reproduction; carrier independence;
G4 closure; AGI or general-agent evidence.

This experiment is **not** external human evaluation and must never be described as one.

## The generator

| | |
|---|---|
| model | `qwen2.5:1.5b`, blob `183715c435899236…` |
| runtime | ollama 0.32.15 |
| image | `ollama/ollama@sha256:57d60e686821ea81…` |
| sole input | `QUALIFYING_INPUT.txt`, sha256 `191dfb19636bb5d6…` |
| decoding | constrained to the frozen JSON schema; structure from the contract, values from the model |
| invocation | **one**, `done_reason` `stop`, 5 488 tokens, 617 s |
| output | 100 records, sha256 `ee6e3d5d6b76189b…` |

Measured **inside the container, before the invocation**, by resolving paths and listing mounts
rather than by matching strings: only a loopback interface; DNS resolution fails; no `/mnt/host`,
`/mnt/c` or `/host_mnt`; traversal out of the input mount fails; no symlink in it; no path or
environment variable naming the project; `HOME=/root`, working directory `/`.

## The order, and why it is checkable

| | commit |
|---|---|
| generator and input frozen | `42f0ae0` |
| defect recorded, before sealing | `849ee7b` |
| bank sealed, **commitment published** | `e00ddd5` |
| tested system frozen, bank still unread | `50c7a0e` |
| reveal authorized | `007ab86` |
| result preserved, before any checker | `2c4ffa3` |

Custody is **procedural, not third-party**: the project holds the reveal key, and the attestation
says so. What the seal buys is that ordering, in a public timestamped history — not custody by a
party that could withhold anything.

## What the reveal produced

The revealed plaintext matches the published `sealed_payload_sha256` `e6d0693a…` exactly.

The public M111 criterion was applied to **all twenty** worlds, with no filtering and no selection:

| | |
|---|---|
| ambiguous | **5** (plan minimum 3) |
| witness | **6** (plan minimum 3) |
| neither | 9 |

Both minima are met, so the thinness rule does not decide this attempt — despite the bank being
**80 worlds short of its plan** through a defect recorded before the seal.

**The blind generator's distribution is not the project's.** Over 1 160 project-generated worlds the
ambiguous rate was ~6 per cent; this bank of 20 yielded 25 per cent. That difference is itself the
point: these are not worlds drawn the way the project draws them.

## Transfer arm — M110 apparatus, unmodified

Every scientific outcome reproduces, unanimously across the six qualifying worlds:

| demand | ground truth | `M0` | `M1` | `M2` |
|---|---|---|---|---|
| row 7 | signal interface | 0/6 | 6/6 | 6/6 |
| row 3 | candidate space | 0/6 | 0/6 | 6/6 |
| **row 5** | **operator table** | **6/6** | **0/6** | **0/6** |
| row 1 | operator table | 6/6 | 6/6 | 6/6 |

`ReachImprove` strict on every world. **The harm at row 5 reproduces on worlds the project did not
choose.**

And yet the arm is **negative at 22/24**, because two predicates are false and neither was weakened
after the fact:

- **P1** is an *invocation artifact*. M110's preflight asserts that a population tagged `canonical`
  sits at the canonical path; this population is a revealed bank at a scratch path. It says nothing
  about the science, and it is reported rather than suppressed.
- **P5 is a real measurement.** On one blind world the image is **17 at bound 7** and **18 at 9, 11
  and 13**. The declared operating bound is 9 and the image is stable at and above it, so no reach
  claim is disturbed — but the fixed-point certificate demands all four bounds agree, and here they
  do not. In 1 160 project-generated worlds this never happened. The blind generator produced a world
  whose closure needs more than seven nodes.

## Diagnosis arm — M111 apparatus, unmodified

**24/24 true.** Five ambiguous worlds, both probe orders, unanimous:

| arm | `A` | `B` |
|---|---|---|
| `M0`, `M1` | 0/5 | 0/5 |
| `M2` | 5/5 | 0/5 |
| `always_signal` | 0/5 | 5/5 |
| never-probe | 5/5 | 0/5 |
| always-probe | 5/5 | 0/5 |
| **acquired policy** | **5/5** | **5/5** |

Pooled record: 44 episodes from 11 worlds; undetermined `[3]`, determined `[1, 5, 7]`. Generation 3
acquired at rule space 127 with 7 consistent policies; **generation 2 ablated → refused**.

## The verdict rule was inherited, not invented

The frozen plan named the two predicate sets but stated **no threshold over them**. That is a second
defect in the freeze. The checker takes the **stricter** available reading — each arm carries its own
milestone's rule, `positive iff every predicate is true` — because choosing the stricter reading of an
ambiguous freeze is the only choice that cannot be accused of having been fitted to the outcome.

## What this changes, and what it does not

**Changes:** the M111 diagnosis result no longer depends on the project having chosen its worlds.
The M110 transfer result's *scientific content* does not either, though its predicate set does not
come out whole.

**Does not change:** the carrier. The value chain, the document shape, the reference edge, the
operators, the bounds, the evaluator, the feature vocabulary, the component registry and the probe
primitive all remain this project's. **No generality gate advances.** `human_maintained_sealed_bank`
remains an external blocker that nothing in this repository can lift.

See `../../DECISIONS.md` (D081), `MATERIALIZATION_DEFECT.md`, `ISOLATION_ATTESTATION.json` and
`PUBLIC_BANK_COMMITMENT.json`.
