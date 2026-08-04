# M041 status

## Current phase

**Canonical result: negative. Experiment closed.**

The unique sealed lineage failed before migration because cycle 3 task generation found no
admissible tool-dependent target. No second M041 seed, rerun or widened search is permitted.

## Canonical identities

- frozen parent: `9bb971ef9c997c55326cb8a338bb6496fc26e8e6`;
- marker-only arming head: `6c404f7fce00087048dcb7d6e346bd5c84308cf8`;
- protocol SHA-256:
  `473daec4a372d5fa2e7d23870040c97e03d4e934c191afa2e8bf0a07d0bc6291`;
- sealed completion seed: `4616374729204286922`;
- sealed-spec digest:
  `bdc6656c65f663ac80d09f0a656d5ac1d646717eaa60881ad53782a825d8ee19`;
- first workflow run: `30937650241`;
- exact result SHA-256:
  `f62a74b80df7629106de22db8058ac8fc1154e0b998dfda47c5ad4f2eee9a3fe`.

The exact artefact is `results/artifacts/M041_CANONICAL_RESULT.json`; the full report is
`results/M041_CANONICAL_RESULT.md`.

## What remains established

M041 development independently established a passive, resource-limited pre-adoption validation
boundary:

- deterministic candidate, case and workspace identities;
- a fresh subprocess for every validation;
- explicit CPU, memory, filesystem, process, descriptor, wall-time, output and structural
  limits;
- schema, observation, regression, strict-improvement and exact-equivalence checks;
- fail-closed adoption and byte-identical replay.

The consumed development result supported Gates 1–9 together on seed `400047`. That result
remains development evidence only and cannot replace the sealed negative.

M038, M039 and M040 canonical artefacts and claims remain unchanged.

## Failure boundary

The M041 sealed seed generated no third-cycle target satisfying the inherited M039 requirement
that a later hidden task be genuinely tool-dependent under the frozen finite search. The
lineage therefore never reached opaque migration or M041 isolated validation.

This exposes a robustness gap in constructive task availability, not a failure of the isolated
workspace itself.

## Next legitimate experiment

A separately named experiment may define, before measurement, a task generator with
constructive availability guarantees. It must ensure that every required cycle produces a
hidden, genuinely new, tool-dependent target while preserving equal-budget ablations,
structural-incapacity proof, seed-only replay and the M041 passive validation boundary.

The M041 seed may be used only to identify the recorded failure class; it may not be used to
select thresholds, programs or a replacement result.
