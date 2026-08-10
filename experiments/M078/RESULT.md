# M078 — first result

**POSITIVE QUALIFIED DEVELOPMENT RESULT — TRACK A, MODEL-FREE.**

Date: 2026-08-11. No external model, no network, no external task, no third-party attestation.

## Outcome

| Arm | Compatible adapted | Hidden 12/12 | False refusals | True refusals | Invented adapters | Hidden failures |
|---|---:|---:|---:|---:|---:|---:|
| discoverer | **4 / 4** | **4 / 4** | **0** | **4 / 4** | **0** | 0 |
| always_refuse | 0 / 4 | 0 / 4 | 4 | 4 / 4 | 0 | 0 |
| never_refuse | 4 / 4 | 4 / 4 | 0 | 0 / 4 | **4** | **4** |

One unchanged procedure adapted every compatible body, validated each on twelve hidden observations,
refused every incompatible body, and refused none of the compatible ones.

## The line that carries the claim

`never_refuse` is the reason this result is not empty. It adopted an adapter on all four
incompatible bodies — each one fitting **every** public observation — and all four then failed hidden
validation. The public evidence really was insufficient, so the discoverer's refusal was informative
rather than lazy.

`always_refuse` fixes the other end: it recovers no adapter at all. Refusal cannot be earned here by
refusing everything.

## Why the refusal is calibrated and not an exhausted search

Each incompatible body carries one command stitched from two skills: it agrees with skill *j* on
*j*'s public inputs and with skill *k* on *k*'s, which is constructible because the public input sets
are disjoint. Public probing therefore finds a fit for all four skills, but the best-fit assignment
collapses two of them onto one command and cannot be made injective.

The recorded diagnosis confirms the mechanism body by body. On every incompatible body the two
aliased skills share exactly one fitting command — for instance `gamma:[1], delta:[1]` — and the
collision pair matches the constructed pair in all four cases. Zero refusals came from an empty
candidate set, an outcome the protocol excluded in advance as non-calibrated and which the harness
reports under a separate kind.

## Information boundary

The discoverer consults only `body.call` and the public inputs. It never reads hidden observations,
the body class, the aliased pair or the internal operation table. This is checked structurally, by
parsing the `discover` function and asserting those attribute names are absent — the falsifier that
post-hoc disqualified M069, verified rather than promised.

## Preserved evidence

- Protocol frozen before the harness: commit `f8a7dc4`; salt
  `1ee28780e3460f931fd4f27afb08f3fb025b962b3f74170a2cb6c09caac51960`.
- Discoverer and bank: commit `afc14a9`.
- Bank commitment `c37ea3dc6ea9ddfbaf1c0528b8fbeef225e9b24ad3ecb90f524b8985147c0c0e`.
- First result, attempt 1, no retry:
  `430f78229203a88d1f11fd36a433191fbe9af71bfd6b95d877c4ec1cb81e4976`.

`python scripts/check_m078_result.py` rebuilds the bank, re-derives all three arms, re-verifies that
every incompatible body still admits a public-fitting candidate, and re-checks the information
boundary. It reported `failures: []`.

## What this supports

The G1 clause that M068 never tested: an incompatible body produces a calibrated refusal rather than
an invented adapter, with zero false refusals on solvable bodies.

## What this does not support

G1 remains **open**. The bank is project-authored and the interaction language is maintained inside
this repository; closing G1 needs bodies maintained elsewhere and independent reproduction.

It is **not** a repair of M074 and may not be cited as one. The discoverer is deterministic, so this
shows a bounded search procedure can be built to detect observable under-determination. It says
nothing about whether any agent possesses epistemic humility, and the two results sit on different
tracks. It establishes no cross-domain transfer, no Genesis Gate 2 evidence and no AGI claim.
