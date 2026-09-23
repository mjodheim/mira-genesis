# Repository consolidation — 23 September 2026

Status: **repository-maintenance record; no scientific result and no experiment rescore**.

This note records branch/PR cleanup performed while the active RSI line moved from V21 to the
prospectively frozen V22 replication.

## Deletion rule

A historical branch was eligible for deletion only when Git comparison established that `main`
already contained every commit reachable from that branch: comparison `branch...main` reported
`behind_by = 0`. In other words, deletion removed a redundant ref, not unique history.

Branches with any commit not reachable from `main` were retained, even when their names or PRs were
old.

The merged V22 apparatus branch was separately deleted only after PR #330 merged successfully and
its exact head SHA was the merged PR head.

## Deleted redundant refs

The merged V22 branch:

- `research/rsi-v22-retained-evaluator`

Historical refs proven fully contained in `main` before deletion:

- `review/gpt56-genesis-artifact-immutability-20260908`
- `review/gpt56-genesis-generated-restore-20260908`
- `review/gpt56-genesis-generated-search-20260908`
- `review/gpt56-genesis-endogenous-frontier-20260908`
- `review/gpt56-genesis-durable-policy-causality-20260909`
- `review/gpt56-genesis-generated-policy-mutation-20260909`
- `review/gpt56-genesis-integrated-meta-loop-20260909`
- `review/gpt56-genesis-meta-loop-integration-20260909`
- `review/gpt56-genesis-meta-measurement-revalidation-20260909`
- `review/gpt56-genesis-meta-policy-evolution-20260909`
- `review/gpt56-genesis-meta-selection-invariance-20260909`
- `review/gpt56-genesis-objective-scoped-policy-20260909`
- `review/gpt56-genesis-repeated-meta-descent-20260909`
- `review/gpt56-genesis-repeated-meta-descent-fast-validation-20260909`
- `review/gpt56-genesis-retentive-objectives-20260909`
- `review/gpt56-genesis-campaign-evidence-form-identity-20260911`
- `review/gpt56-genesis-evidence-ranked-form-transition-20260911`
- `review/gpt56-genesis-form-transition-capability-scoring-20260911`
- `review/gpt56-genesis-persistent-metamorphic-campaign-20260911`
- `review/gpt56-genesis-policy-registry-binding-20260911`
- `publication/genesis-iv-preprint-v1`
- `publication/genesis-iii-preprint-v1`

The one-shot maintenance branches used for deletion deleted themselves and were not merged.

A later audit also identified
`review/gpt56-genesis-autonomous-policy-loop-20260909` as fully contained in `main`; it may be
removed by the next safe cleanup pass.

## PR cleanup without history deletion

The following stale/superseded PRs were closed with their branches retained because those branches
still carry unique commits:

- #282 — `feat(genesis): evolve search machinery after measured exhaustion`
- #316 — `docs: freeze Genesis Free Metamorphosis v5 prospective preregistration`
- #327 — `Record zero-spend v8 A001 proposer rejection`
- #275 — `feat: the integrated Genesis runtime, plus the G7 apparatus findings and G9 instruments`

Closing these PRs does not convert their development records into negatives or positives and does not
delete their branch history. #275 was closed only after a semantic audit found that current `main`
already contains later successor mechanisms for generated bodies, persistent policy evolution,
MetaPolicy evolution and repeated retained meta descent; its ten unique commits remain available as
historical provenance rather than being merged wholesale over newer interfaces.

## Explicitly retained classes

The consolidation did **not** delete:

- branches with `behind_by > 0` relative to `main`;
- active V23 research branches;
- the documentation synchronization branch until its PR is merged;
- old validation/review branches whose unique commits have not yet been classified;
- carrier/M125 branches merely because that line is no longer the project-wide active frontier.

Further cleanup should use the same content-preservation rule rather than branch-name age alone.
