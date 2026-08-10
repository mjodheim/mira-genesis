# G2 multimodal grounding — first result

**POSITIVE QUALIFIED DEVELOPMENT RESULT — TRACK A, MODEL-FREE. FULL CI QUALIFICATION PENDING.**

Date: 2026-08-10. No external model was called, no network was opened, no external task was
selected and no third-party attestation was consumed or required.

## Outcome

One persistent deterministic agent consumed language, structured state and pixels, emitted symbolic
`set_dial` calls on 24 episodes and embodied effector move sequences on 12, and reached exact success
on all 36 episodes of the bound suite.

| Arm | `pixel_target` | `structured_dial` | `language_route` | Total |
|---|---:|---:|---:|---:|
| full | **12 / 12** | **12 / 12** | **12 / 12** | 36 / 36 |
| pixel_ablated | **0 / 12** | 12 / 12 | 12 / 12 | 24 / 36 |
| structure_ablated | 12 / 12 | **0 / 12** | 12 / 12 | 24 / 36 |
| language_ablated | 12 / 12 | 12 / 12 | **0 / 12** | 24 / 36 |
| blind_guess (measured floor) | 0 / 12 | 1 / 12 | 2 / 12 | 3 / 36 |

Every ablation destroyed its own dependent family and left both non-dependent families at **exactly**
the full-arm score. That exact-equality half is the preregistered claim; an arm that degraded
everything would have shown only that inputs matter.

The measured floor of 3/36 sits against an expected 2.3 from the amendment arithmetic, and stays
under the bound of 8 across 50 independent alternative salts inside the regression suite.

## Preserved evidence

- Protocol frozen before the harness existed: commit `cd55035`.
- Harness and recorded amendment A1: commit `4a56de6`.
- Bound episode suite: commit `5fdf7b4`, suite commitment
  `20ff63f37e7708b175af5ab5bdfd6dd3374ef487cecb41504e489f2a214a4f7e`.
- Salt drawn before any harness code: `7d0348363ccb580e7189d90189d73ee649be007db8339c7b03d77f497be2987a`.
- First result, attempt 1, no retry:
  `aa312e9530a46556755111630f85911460fff965b428cf59905b5555d0a52639`.

`python scripts/check_m076_result.py` independently rebuilds the suite from the salt,
re-derives all five arms, re-verifies the matched-ablation invariants and marker isolation, and
recomputes the preserved digest. It reported `failures: []`.

## The recorded defect

Amendment A1 is part of the result, not a footnote. The first freeze specified a floor arm answering
"from the chance distribution" while bounding it at one success across 36 episodes. Those clauses are
inconsistent: a faithful guess over the frozen 7..12 modulus range lands on roughly one episode in
twelve. The bound was arithmetically unreachable.

The amendment was applied before any episode was materialized and before any result existed, which is
the boundary the protocol itself sets, and it is recorded in `PROTOCOL.json` with its arithmetic. The
alternative — implementing the floor as fail-closed so it scored zero — would have been a fourth
ablation arm dressed as a floor, and would have made every zero-scoring ablation self-confirming.

## What this supports

Bounded multimodal grounding with **causal per-channel dependence** in one persistent agent, under a
matched-ablation design where byte length, key order and token count are preserved so that no arm can
detect its own ablation. On the generality register this moves G2 from open to partial mechanism
evidence.

## What this does not support

It is not natural-image perception: the rasters are project-authored 24×24 synthetic panels with
exact marker triples. It is not cross-domain transfer, since one authored domain is used throughout.
It is not learning — the agent is deterministic and its policy does not change between episodes;
persistence here is identity and audit only. It does not touch Genesis Gate 2 or Gate 3, long-horizon
autonomy, or any AGI claim, and it does **not close G2**: closing G2 needs modalities the repository
does not yet handle and tasks maintained outside this project.

Like M072 and M073, this is development evidence produced inside the policy-development path. It
requires independent reproduction before any stronger language is used, and it deliberately does not
weaken or touch the M075 pre-private readiness boundary.
