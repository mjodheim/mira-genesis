# M080 continual acquisition under interference

**FROZEN BEFORE IMPLEMENTING OR MATERIALIZING THE LINEAGE AND SKILL BANK.**

## The gap this addresses

G5 requires acquiring skills after deployment while retaining preregistered old capabilities, with
the evaluator measuring positive transfer, negative transfer, memory growth, replay dependence and
exact rollback.

The register is blunt about what is missing: M073 "tests only one homogeneous authored family and
**no forgetting**". Retention has never been at risk in this repository, so it has never been
measured.

## Why retention here is not free

The obvious design gives each skill its own slots. Retention is then guaranteed by construction and
the experiment measures nothing — the same emptiness as an incompatible body with no candidate
(M078) or an ambiguous goal that cannot be satisfied (M079).

All six skills here share **one bounded table of 24 slots**, and their key spaces deliberately
collide: every skill after the first demands slots an earlier skill already holds. A lineage that
writes naively destroys an earlier capability. The `no_consolidation` arm exists to demonstrate that
the interference is real rather than asserted.

## What is and is not claimed as learning

G5 states that external memory alone counts as retrieval rather than policy learning. That
distinction is taken seriously here.

The shared table **is** the policy: behaviour is fully determined by it, and acquisition rewrites it.
It is not a side store consulted alongside a fixed policy. So this is bounded policy learning over a
finite structure. It is **not** weight learning, and no such claim is made anywhere in this
experiment.

## Replay dependence is measured, not thresholded

The `no_replay` arm has **no preregistered direction**, and this is deliberate. Requiring it to fail
would be requiring replay dependence; requiring it to pass would be requiring structural retention.
Either would decide the question by assumption.

Both outcomes are named here in advance. If retention survives without replaying earlier examples,
the retention is structural. If it does not, the retention is replay-dependent and the mechanism is
weaker than it looks. The result must state which occurred, and may not select the flattering
reading afterwards.

## Falsifiable claim

One lineage acquires six skills in sequence. After every acquisition it must retain each earlier
skill at exact held-out quality, grow memory sublinearly in the number of skills, and restore a
byte-identical prior state after a rejected acquisition.

`no_consolidation` must lose at least one earlier capability. `no_rollback` must leave a state that
does not match its checkpoint. If either ablation preserves everything, the mechanism is not doing
the work the result would otherwise claim, and M080 is negative rather than redefined.

## Safety boundary

The lineage receives compute and in-process memory only. The table, skills and evaluator are
in-memory structures. No arm may reach a network, repository write path, credential, deployment
path, permission interface or physical actuator.

## Claim boundary

A positive result establishes bounded continual acquisition under genuine interference, with
forgetting measured rather than assumed away. It does **not** close G5: the skills and table are
project-authored, and closure requires capabilities maintained outside this project plus independent
reproduction. It establishes no weight learning, no open-ended skill acquisition, no cross-domain
transfer, no Genesis Gate 2 evidence and no AGI claim.
