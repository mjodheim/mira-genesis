# M121 / H66 pre-implementation hostile review — 2026-09-05

## Disposition of this review

**BLOCK BEFORE ENABLING IMPLEMENTATION, BUT REPAIRABLE WITHOUT SCIENTIFIC LOSS.**

This is an audit finding only. It does not amend `experiments/M121/PREREGISTRATION.md`,
`experiments/M121/PROTOCOL.json`, P-025, G7 or any scientific verdict. No M121 harness, schedule,
arm or scientific result exists, so the defects below can still be corrected prospectively and
logged before an owner-authorised scientific freeze.

The publication/IP question and the scientific-readiness question are separate. This review finds no
new reason that the proposed work must be private; it finds reasons not to approve *enabling
implementation under the current scientific precommitment* yet.

## What is already strong

M121 preserves several good boundaries from the predecessor line:

- M077 remains a closed negative rather than being repaired or relabelled;
- an instrument abort is explicitly not a negative result;
- the human-equivalent-time component of G7 is refused rather than inferred from episode count;
- the external human-maintained bank, independent reproduction and external adversarial-audit
  blockers remain external;
- the arm logic tries to isolate checkpoint recovery from boundary monitoring and retains an idle
  floor so inactivity cannot earn a clean score;
- the primary outcome is intended to come from environment state rather than lineage self-report.

Those are worth preserving. The problems below are precommitment gaps, not a reason to discard the
question.

## Blocking finding R121-01 — a salt is frozen, but the schedule function is not

`PROTOCOL.json` contains a 32-byte schedule salt and states that every schedule element derives from
`the salt, the horizon and a deterministic index`. It does **not** define the derivation function,
the mapping to episode indices, the mapping to fault class/subtype/location, collision handling or
the number of faults per horizon.

A deterministic function selected *after* the salt is visible is still a free parameter. Because the
body also does not exist, the implementation can in principle co-adapt the body, the monitor and the
salt-to-schedule mapping while all three remain consistent with the prose.

This is a regression relative to M077. M077 froze, before its harness, the exact rule
`sha256(salt || uint32_be(horizon) || uint32_be(ordinal))`, a fault-count rule
`max(4, horizon_length // 64)`, a concrete body, four invariants, a fault grammar, thresholds and
result classification.

**Required before implementation:** freeze an exact schedule generator or explicitly demote the
current salt to DEVELOPMENT-only and draw a fresh canonical salt only after the full tested apparatus
and generator are frozen.

## Blocking finding R121-02 — the preregistration says fault proportions are fixed; they are absent

The preregistration says:

> the fault schedule carries both classes, in proportions fixed by this document before the body
> exists

No numeric proportion, count rule or balancing rule follows. Repository search finds no second M121
statement that supplies the missing proportions.

This is not just missing prose. The operational/quiescent mix directly controls how much opportunity
there is to satisfy each half of H66 and how much information each horizon contains.

**Required before implementation:** fix, mechanically, the count of injected faults per horizon and
the operational/quiescent allocation. The checker must recompute it from the frozen generator rather
than trust reported counts.

## Blocking finding R121-03 — the body, monitor and quiescent-fault grammar can still be co-designed

The preregistration correctly warns that one can manufacture a positive result by building a body in
which quiescent corruption is monitor-detectable by construction. But it then leaves the concrete
body, invariants, monitor surface and fault mutations to be implemented after that warning.

The operational positive control is useful, but it does not remove this degree of freedom. A new body
can reproduce M077 on operational faults while its quiescent region is deliberately shaped so the
boundary monitor is the only component that can possibly notice the chosen mutations.

**Required before a canonical draw:** commit a concrete state model, guarded-operation semantics,
monitor semantics, ground-truth environment and a generic fault-mutation grammar independently of
the canonical schedule. The canonical fault locations/subtypes should then be selected from that
precommitted grammar after the apparatus is frozen.

## Blocking finding R121-04 — the hypothesis, primary endpoint and verdict rule do not line up yet

H66 is phrased in terms of **detection**: operational parity, fewer quiescent detections without the
monitor, and a widening detection gap with horizon. The stated **primary endpoint**, however, is the
count of completed work items whose recorded outcome diverges from hidden ground truth.

Those quantities are related but not identical. A fault can be detected late after already causing a
wrong result, or a divergence can occur without the proposed detection-count relation. The current
protocol has no complete positive/negative verdict table that says which exact conjunction governs
H66, no minimum effect, and no result/checker schema exists yet.

That leaves the load-bearing endpoint choice to implementation time.

**Required before implementation or, at latest, before any scientific schedule exists:** define one
machine-checkable verdict rule over explicitly named quantities. Distinguish at least:

- faults injected by class;
- faults detected before first bad output;
- silent divergent work items;
- restoration success;
- completed work;
- residual corruption at the end of each horizon.

The result schema and checker must compute the same rule independently.

## Major finding R121-05 — horizon is confounded with schedule unless matching is explicit

The claim requires a gap that widens with horizon. `PROTOCOL.json` says each item derives from salt,
horizon and index, but does not say that:

- all arms receive the exact same schedule at a given horizon;
- shorter and longer horizons are prefixes of one master trajectory; or
- independent horizon schedules preserve a fixed fault density and class balance.

Without one of those constraints, a larger gap at 2048 than at 512 can be a property of the four
chosen schedules rather than a property of horizon.

**Required:** matched schedules across arms. For the horizon effect, either use a prefix-nested master
schedule or freeze a rate/balance design and a normalized endpoint that makes independent horizon
schedules comparable.

## Major finding R121-06 — the current salt should not be the canonical scientific draw

The current salt is public before the body, monitor, generator and checker are frozen. If an exact
schedule generator is now written, the resulting canonical schedule becomes knowable while the
system under test is still editable.

No observation has been made, so there is no scientific cost to fixing this.

**Recommended sequence:** retain the current salt only for DEVELOPMENT fixtures; after the apparatus
is complete, tested and frozen, draw a new canonical salt, commit its provenance, materialize the
schedule once and do not edit the apparatus afterwards.

## Major finding R121-07 — no unique-attempt / retry policy is frozen

M077 explicitly prohibited retrying its first materialized schedule and preserved its first result.
M121 defines instrument-abort conditions but does not yet define a canonical-attempt count, result
exclusive-create rule or retry policy.

**Required:** one canonical schedule and one canonical scientific result. If a prospectively defined
instrument abort occurs, preserve it and move any repair to a separately versioned successor or a
prospectively permitted pre-scientific apparatus revision. Do not rerun the same scientific draw
until it passes.

## Major finding R121-08 — hidden ground truth is asserted but not yet an information boundary

The primary endpoint says ground truth is something `the lineage cannot read`. There is currently no
harness, capsule census, object-capability boundary or checker proving that statement.

**Required:** ground truth must live in evaluator/environment state outside the lineage-facing state
and observation payload. Add an adversarial test that deliberately tries to reach it through every
lineage input, serialization surface and diagnostic path. The independent checker should derive the
endpoint from environment state, not from a value copied into the lineage's record.

## Minor finding R121-09 — pre-result claim-boundary field names read like accomplished claims

The pre-result protocol contains fields such as
`establishes_constraint_retention_across_episode_horizons: true` and
`establishes_coverage_against_quiescent_corruption_in_one_authored_body: true` while the same file
correctly records `scientific_result_exists: false`.

The intended meaning appears to be *what a positive result would establish*. Rename these fields to
`if_positive_establishes_*` or keep them false until a result exists. This is a reader-facing
hardening, not a scientific defect by itself.

## Recommended clean chronology

A corrected M121 can still be genuinely prospective if the project uses this order:

1. **Audit amendment** — record these pre-observation defects in the M121 amendment log; no result is
   reinterpreted because no result exists.
2. **Freeze the design contract** — concrete body/state semantics, invariants, monitor semantics,
   ground-truth boundary, fault grammar, exact schedule generator, class balance/counts, matched-arm
   rule, horizon-comparison rule, endpoint set, verdict rule and one-shot policy.
3. **DEVELOPMENT only** — implement and attack the harness with neutral fixtures and a development
   salt that cannot become canonical evidence.
4. **Freeze tested apparatus** — runner, result schema, checker, tests and all load-bearing source
   bytes. Re-run hostile tests before any canonical schedule exists.
5. **Draw a fresh canonical salt** after that freeze. Materialize exactly one schedule from the
   frozen generator.
6. **Canonical execution** — one scientific result, preserved whichever way it comes out.
7. **Independent checker replay** — recompute schedule, endpoints, arm matching, information
   boundary and verdict from preserved artifacts.
8. **Only then** consider a bounded G7 register update; human-equivalent and external blockers remain
   untouched.

## Owner-gate recommendation

**Do not record P-025 as approved yet.** The proposed public disposition itself can remain the likely
destination; the blocker is scientific readiness, not a newly identified confidentiality need.

Once the blocking precommitment gaps above have been corrected *before any enabling implementation*,
the owner can make the publication disposition and implementation-authorisation decision against a
much tighter experiment without losing the prospectivity M121 currently still has.
