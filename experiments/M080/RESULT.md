# M080 — first result

**POSITIVE QUALIFIED DEVELOPMENT RESULT WITH A MEASURED LIMITATION — TRACK A, MODEL-FREE.**

Date: 2026-08-11. No external model, no network, no external task, no third-party attestation.

## Outcome

| Arm | Capabilities lost | Final retention failures | Slots used | Rules reused | Rollbacks | Checkpoint mismatches |
|---|---:|---:|---:|---:|---:|---:|
| lineage | **0** | **0** | **19** | **3** | 2 | **0** |
| no_consolidation | **5** | 3 | 16 | 3 | 0 | 0 |
| no_rollback | 5 | 3 | 16 | 3 | 0 | **3** |
| no_replay | **5** | 3 | 16 | 3 | 0 | 0 |

All five measures G5 names are present:

- **positive transfer** — 3 rules reused; skills 3–5 cost no rule slot at all;
- **negative transfer** — 0 for the lineage, 5 lost capabilities without consolidation;
- **memory growth** — 19 slots against a private-slot ceiling of 24, so sublinear;
- **replay dependence** — measured below;
- **exact rollback** — 2 byte-identical restorations, 0 mismatches.

## The measured limitation

**Retention here is `replay_dependent`, not structural.** Without replaying earlier examples during
consolidation the lineage loses five capabilities — the same as having no consolidation at all. The
mechanism does not protect old skills by its structure; it protects them by rechecking them.

This is reported straight because the frozen protocol forbade preregistering a direction for this
measure. Requiring the no-replay arm to fail would have required replay dependence; requiring it to
pass would have required structural retention. Either would have decided the question by assumption
instead of measuring it.

## Why retention here was genuinely at risk

Skills 3–5 reuse an earlier skill's rule — that is where the sublinear growth comes from — and each
one also needs a **different output for an exception key its donor already owns**. The cheap path,
rewriting that shared entry in place, is always available and always destroys the donor. The
`no_consolidation` arm takes it and loses five capabilities, which is what makes the interference
real rather than asserted.

## What is claimed as learning

The shared table **is** the policy: behaviour is fully determined by it and acquisition rewrites it.
It is not a side store consulted alongside a fixed policy, which G5 would count as retrieval. It is
bounded policy learning over a finite structure and it is **not** weight learning; no such claim is
made.

## Recorded instrument fixes

Three, all before materialization, all in `RESULT.json`, none touching a threshold.

1. Capacity pressure alone never bound — 23 of 24 slots — so no arm ever evicted and no
   interference existed. Interference now comes from rule sharing with a conflicting exception key.
2. Retention is measured over a skill's complete key set. Damage lands on exception keys, which the
   split forces into the examples so the skill stays learnable; holdout-only scoring hid it
   entirely and every arm looked clean.
3. The rollback check was **tautological** — it compared the checkpoint against its own digest and
   could never fail. It now compares the live table after the rejection is handled. A regression and
   the checker both assert that a mismatch remains reachable, because a check that cannot fail
   reports green regardless of behaviour and is worse than no check.

## Preserved evidence

- Protocol frozen before the harness: commit `b3e9aba`; salt
  `5f7b41e3511c0d6ed0c8c427c66bc09bb35d7c839d19ea13e05a0b82c1bd1476`.
- Lineage and ablations: commit `d68dfd3`.
- Bank commitment `3769e8266189c3ffd33871570e016e33271026cf8d305d9dd81283c9b063ec6d`.
- First result, attempt 1, no retry:
  `421121398984cdaec066de7aaf900a7f10ee92d956f5d2b9bb2f7705975dfc99`.

`python scripts/check_m080_result.py` rebuilds the bank, re-verifies the conflict construction and
the information boundary, re-derives all four arms, confirms the rollback check can still fail, and
recomputes the digest. It reported `failures: []`.

## What this supports

Bounded continual acquisition under genuine interference, with forgetting measured rather than
assumed away — the gap the register named when it recorded that M073 tested "no forgetting".

## What this does not support

G5 remains **open**. The skills and table are project-authored; closure requires capabilities
maintained outside this project plus independent reproduction. No weight learning, no open-ended
skill acquisition, no cross-domain transfer, no Genesis Gate 2 evidence, no AGI claim.

And the retention demonstrated here is conditional on replay. A successor claiming robust continual
learning must either make retention structural or state the replay cost as part of the claim.
