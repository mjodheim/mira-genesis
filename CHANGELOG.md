# Changelog

## 0.29.0 — 2026-08-03

- Repaired the D014 negative-constant defect in the rewrite kernel. The fix is in the
  reader rather than the writer: `_negative_int_literal` makes both `_TargetCollector` and
  `_IndexedNodeTransformer` treat a `-<int>` expression as one constant target, so a patch
  replaces the whole negation instead of the literal nested inside it.
- Constant patches are now idempotent for every sign, the AST no longer grows under
  repeated negative patches, and the effective behaviour no longer alternates.
- Measured the consequence honestly: the repair moves all four recorded M033 digests,
  because `ConstantRewriteTool.propose` filters on `value != current` and previously read a
  negative constant as positive. Every search in the construction stack was carrying
  phantom candidates; removing them lowers candidate medians by 3 to 7 per cent.
- **No finding changed.** Every paired outcome reproduces identically across the two kernel
  generations, along with exactness, held-out exactness, output-only immobility and the
  parent/ablation separation.
- Recorded D015: artifacts are scoped by the kernel generation that produced them rather
  than re-run, as M012 is scoped against M012b. A cost figure may only be compared against
  another from the same generation.
- Retired `tests/test_m020_negative_constant_defect.py`, which pinned the defective
  behaviour so a fix could not land unnoticed, and replaced it with
  `tests/test_m020_negative_constant_round_trip.py`, which guards the repair.
- Added `MacroCost`, an opt-in edit-budget rule. `PER_OPERATION` is the default and charges
  a learned tool what its constituent primitives cost; `UNIT` charges it as a single edit.
  `_rank_key` now ranks on budget rather than trace length, which is identical under the
  default and lets a one-step macro outrank the longer primitive path it replaces.
- Added `metamorphosis/m034_reachability.py`, an exact capability measure. Deterministic
  cost conflates how close a lineage started with how much it can do; the reachable
  behaviour set separates them, and is enumerable here rather than estimated.
- Established two results, both pinned: under `PER_OPERATION` a learned tool adds **nothing**
  to the reachable set at any budget, being a composition of primitives charged what they
  cost; under `UNIT` it enlarges the set — 2/16 to 4/16 at budget 1, 7/16 to 10/16 at
  budget 3 — with the old set a proper subset of the new.
- Gave M017 a decidable success criterion it lacked: does a self-extending language
  increase reachability at constant budget?

## 0.28.0 — 2026-08-03

- Added rewrite provenance: `RewriteCandidate.proposing_tools` and
  `RewriteResult.reused_learned_tools` record which tool proposed each adopted step, so
  Gate 9's reuse clause can be proved rather than guessed. Provenance is excluded from the
  ranking key, and all four recorded M033 digests reproduce exactly.
- Established that a learned tool costs the same edit budget as its constituent
  primitives: it saves search depth, not budget, since its operations count individually
  against `max_edits`.
- **Found a latent correctness defect in the M020 rewrite kernel.** `apply_patch` does not
  round-trip negative integer constants: `ast.unparse` writes `-2`, re-parsing yields
  `UnaryOp(USub, Constant(2))`, and each further patch at that index stacks another
  negation. Constant patches are non-idempotent for negative values, the AST grows without
  bound, and the search can reach bodies whose outputs leave the declared state range.
- Audited the blast radius: nothing recorded is contaminated. 776 of 776 adopted sources
  across the four M033 calibration blocks contain no negative constant.
- Recorded the defect as D014 and in `FAILURE_LOG.md`, and pinned it with
  `tests/test_m020_negative_constant_defect.py`. It is deliberately **not** repaired here,
  because correcting it changes the reachable candidate set and may move recorded digests.
- **Withdrew the Gate 9 demonstration.** An exhaustive finite check found 4 candidate
  reuse lineages out of 195 cycle-1/cycle-2 pairs; all four depended on the defect. Gate 9
  remains undemonstrated and must be re-measured on a corrected kernel.

## 0.27.0 — 2026-08-03

- Measured D013's predicted repair path instead of leaving it as an argument: a
  three-cycle lineage over three distinct finite targets accumulates three learned tools,
  one of which can still act on the final body.
- Established the exact mechanism: the newest tool is always inert, because it is by
  construction the trace that produced the current body, and an earlier tool becomes able
  to act again only once a later cycle moves the body away from what it wrote.
- Recorded that Gate 9 is a **precondition** for Gate 8's learned-tool comparison, which
  is a sequencing constraint on the roadmap rather than a threshold choice, and that
  M033's thresholds may not be frozen before repeated cycles exist.
- Added `tests/test_m020_multicycle_tool_reactivation.py`, five tests pinning the tool
  accumulation, the inert newest tool, the reactivation of an earlier tool, and the
  single-cycle contrast.

## 0.26.0 — 2026-08-03

- Established that a learned rewrite tool is a literal replay, not a generalising
  transformation: `PatchOperation` binds each edit to a positional AST index and
  `LearnedRewriteTool` returns its operations verbatim, so a tool cannot fire at an
  equivalent site with a different index.
- Established the consequence for Gate 8: the tool a single-cycle lineage carries is the
  trace that produced its body, so applying it there is a no-op and the learned-tool
  ablation compares two lineages whose only difference cannot act.
- Reclassified that control from failed to **structurally uninformative**, since a tie
  there is evidence about the rewrite language rather than about transported plasticity.
- Withdrew the requirement, added in 0.25.0, that the primary generator demand a component
  the migrated body does not encode. It was unsatisfiable: the precondition is a relation
  between registry and body, not between lineage and task.
- Recorded that Gate 8's tool control must be evaluated on a multi-cycle or rolled-back
  lineage, so Gates 8 and 9 are not independent.
- Added `tests/test_m020_learned_tool_replay_limit.py`, five tests pinning the index
  binding, the no-op property and the absence of site transfer.
- Recorded the finding as D013 and connected it to D009: the tool language is closed in
  the same way the retired catalogue was.
- Noted that the memory mechanism is unaffected, because it is decoded and re-applied
  against current evidence and can therefore act on a body it did not produce.

## 0.25.0 — 2026-08-03

- Found and repaired a control-design defect that removed one of Gate 8's four required
  controls: every earlier M033 block anchored all lineages on the task's own baseline
  source, so the migrated body was never read and the unchanged parent and the
  learned-tool ablation presented byte-identical surfaces.
- Added `TaskAnchor`, leaving `TASK_BASELINE` as the default so the fixed, structural and
  combined blocks stay byte-reproducible and are not retroactively re-scored; verified by
  re-running all three after the change and reproducing every recorded digest exactly.
- Added the body-anchored control block on the disjoint seed range 4096–4127, where the
  two collapsed controls separate on 32 of 32 seeds.
- Established that transported competence does real work: the complete lineage beats
  fresh-B 32/0/0 and its own unchanged parent 32/0/0, at a median of 26 candidates
  against 1,427.5 and 264.5.
- Established that the learned tool contributes nothing independent in this rig, tying the
  complete lineage 0/32/0 at an identical median of 26, because it encodes the same
  transformation the adopted rewrite already baked into the body.
- Recorded Gate 8 as unmet with a per-control verdict, and recorded that the remedy is a
  generator change rather than a threshold change.
- Verified the isolation and integrity audits and a byte-identical replay with raw digest
  `394f9904b675ac2a8c9d143b8265022b32285efb0d56a01799f45e43b17571a8`.
- Left the reserved primary block 0–63 uninstantiated and unobserved.

## 0.24.0 — 2026-08-03

- Added M033's combined memory-and-tool control block on the disjoint seed range
  3072–3103, running the four structural scaffolds through the memory-guided execution
  path so both transported mechanisms are measured together for the first time.
- Recorded a mixed and largely negative result: all five learning-capable variants were
  exactly equivalent on all 32 tasks, and the complete lineage beat fresh-B 24/0/8 but
  went 8/16/8 against its unchanged parent, 8/16/8 against the learned-tool ablation and
  16/0/16 against the learning-state ablation.
- Established that the two mechanisms act on disjoint scaffolds: memory carries scaffolds
  0 and 1 at a median of 264 candidates, learned tools carry scaffold 3 by cutting search
  from 1,879 to 568, and neither helps on scaffold 2.
- Established that the advantage is not attributable to the adopted rewrite, because the
  unchanged parent retains the same learning state and matches or beats the complete
  lineage on three of four scaffolds.
- Charged the memory probe honestly: one candidate evaluation whether accepted or
  rejected, which alone decides the scaffold-3 loss against the learning-state ablation
  at 569 against 568.
- Verified 236 repository tests, the isolation and integrity audits and a byte-identical
  replay with raw digest
  `0ef00f0f4168a95235f33050751b7871366ad1e2d2c08ed07bfb90b908423372`.
- Left the reserved primary block 0–63 uninstantiated and added two questions the
  threshold-freeze amendment must now answer: the status of the unchanged-parent
  comparison, and whether a one-candidate margin is a win or an abstention.

## 0.23.0 — 2026-08-03

- Added M033's post-migration plasticity rig: six lineage constructors covering the
  complete migrated M032 lineage, fresh-B, unchanged parent, output-only and the
  learning-state and learned-tool ablations.
- Added two disjoint development control blocks — fixed-structure seeds 1024–1031 and
  four-scaffold structural seeds 2048–2063 — with a static audit proving no pre-M033
  module reaches the M033 task, target or held-out surfaces.
- Isolated the learned-tool mechanism causally: median post-reveal candidates were 959
  for the complete lineage against 976 for fresh-B, the unchanged parent and the
  learned-tool ablation, cheaper on 8/8 seeds, with 0/8 on the disjoint negative family.
- Isolated the memory mechanism causally: a relevant transported trace reached a median
  of 264 candidates against 959 for empty memory and 960 for a permuted trace, cheaper on
  8/8 seeds, while all three stayed exactly equivalent.
- Recorded a deliberately mixed structural result — 12/16 complete-lineage wins with
  per-scaffold directions of 4/4, 4/4, 0/4 and 4/4 — and kept scaffold 2 as a declared
  counterexample to any rule demanding universal directional improvement.
- Reported every lifecycle cost as a separate vector rather than one synthetic score, and
  verified output-only immobility, fail-closed post-migration regression and exact
  rollback.
- Passed 27 focused tests, the repository integrity and task-isolation audits and
  byte-identical replays of both calibration families in run `30792247244`.
- Kept the reserved primary block 0–63 uninstantiated and unobserved; no post-migration
  plasticity advantage is claimed and no threshold is frozen.

## 0.22.0 — 2026-08-03

- Added M032's fail-closed bridge from M025's adopted executable rewrite to M013e's
  experimentally discovered opaque substrate and native DFA body.
- Added a canonical trans-substrate packet carrying the M025 passport, source DFA,
  opaque body, discovered opcode identifiers, memory, uncertainty and exploration
  frontier.
- Added exact rollback after finite-compilation or substrate-migration failure and
  integrity rejection for tampered passports, DFAs, opaque bodies and opcode registries.
- Verified five focused M032 controls, repository integrity and 211 repository tests on
  both Python 3.11 and Python 3.13.
- Preserved the boundary between this bounded integration result and the still-open
  post-migration learning, autonomous diagnosis and repeated-cycle claims.

## 0.21.0 — 2026-08-02

- Added M031's split-scaffold generator with length-three generic motifs and eight
  cyclic/permuted triad tasks.
- Transported the frozen component-uniform information rule: 737 per mille
  clade/exact-CMP concordance, +1,070 over development adaptive, and +500 per mille
  median paired final hidden quality with 43 wins, 18 ties and 3 losses.
- Passed every structural, probe, coverage, uniqueness, selector-isolation and aligned
  control on exactly 64 paired primary seeds.
- Recorded 256 trajectories, 65,792 expansions, 198,144 unique evaluations and a
  byte-identical 48,018,205-byte replay.

## 0.20.0 — 2026-08-02

- Added M030's pre-written confirmation of M029's component-uniform diagnostic on the
  untouched seed block 64–127.
- Confirmed every gate: component-uniform guidance reached 662 per mille
  clade/exact-CMP concordance, +1,186 over development adaptive, and +1,000 per mille
  median paired final hidden quality with 48 wins, 16 ties and no losses.
- Preserved the untouched boundary by using only seeds 128+ for unit and smoke
  validation before the frozen confirmation commit.
- Recorded 256 trajectories, 30,720 expansions, 92,928 unique evaluations and a
  byte-identical replay.

## 0.19.0 — 2026-08-02

- Added M029's hidden-disjoint compositional transfer probes and a frozen rerun of the
  M028 performance-adaptive baseline.
- Preserved the 64-seed mixed development result: component-adaptive clade/exact-CMP
  concordance reached 699 per mille, but its paired final advantage remained zero with
  31 wins, 32 ties and 1 loss, below the pre-written policy gates.
- Recorded the pre-declared component-uniform diagnostic: 50 wins, 14 ties and no
  losses against development-adaptive guidance, without promoting it to a registered
  claim on already observed seeds.
- Recorded 384 trajectories, 46,080 expansions, 139,392 unique evaluations and a
  byte-identical replay.

## 0.18.0 — 2026-08-02

- Added M028's finite adaptive evaluation-weighting comparison over the common M027
  breadth-seeded archive.
- Preserved the 64-seed negative development result: adaptive allocation improved
  clade/exact-CMP concordance by only 40 per mille, produced no median hidden-quality
  advantage and returned 2 wins, 60 ties and 2 losses against uniform allocation.
- Recorded 256 trajectories, 30,720 expansions, 92,928 unique evaluations and a
  byte-identical replay without exposing hidden fields to either selector.
- Localised the next measurement failure: performance-adaptive weighting can sharpen a
  misaligned proxy while allocating less evidence to high-potential lineages.

## 0.17.1 — 2026-08-02

- Hardened human-only attribution with exact registered identities and a trusted-base
  pull-request check that never executes proposed code.

## 0.17.0 — 2026-08-02

- Added M027's hidden-blind exhaustive coverage through the first reward-bearing depth.
- Preserved the 64-seed negative development result: exposing productive descendants
  did not align the unweighted clade estimator or improve final hidden quality.
- Added permanent human-attribution rules and pull-request checks for commit authors,
  committers, co-authors, branch names, titles and descriptions.
- Removed historical automated inline-review comments and neutralized the submitted
  review summaries that GitHub does not permit the repository owner to delete.

## 0.16.0 — 2026-08-02

- Added M026, the first direct literature-facing benchmark, with explicit mappings to
  DGM, HGM and SGM and equally explicit non-reproduction boundaries.
- Added an exact finite performance/potential reversal, an exhaustive aligned control,
  selector isolation, fixed-point stochastic policies and four-worker replay.
- Preserved the 64-seed negative development result: HGM-inspired clade aggregation
  did not beat DGM-inspired immediate guidance under the fixed expansion process.
- Recorded the frozen implementation and protocol identities, the reproducible
  512-run artifact hash and a byte-identical full replay.

## 0.15.0 — 2026-08-02

- Ran M021 across 24 paired seeds and preserved the development result: implemented
  selection measures produced different exact hidden transferred quality.
- Added M022's pre-written seed-0 positive and negative adaptation controls with full
  row-level evidence; cross-seed stability remains open.
- Hardened M023 so independent adoption fails closed when the parent workspace fails.
- Added M024's integrity-checked rewrite passport for the active body, rollback lineage
  and complete learned-tool registry.
- Added M025's transactional portable rewrite lifecycle. Rejection or exceptions now
  restore both the body and registry exactly; accepted state migrates, replays its
  learned transformation and survives forced rollback.
- Reconciled the public project narrative, state and roadmap in English and recovered
  the useful evidence that had existed only on stale local branches.

## 0.14.0 — 2026-08-01

- Reoriented the project onto what its own failures identified: **when does a proxy
  measure stop tracking what it claims to track?** (D011, H9)
- Added `MEASURES.md`, a first-class register beside `FAILURE_LOG.md`, cataloguing six
  measures that came loose from what they claimed to measure — with ground truth.
- Made that catalogue executable: `scripts/reproduce_measure_failures.py` replays every
  case on demand.
- Replaced the probabilistic confirmation with an exact conformance test
  (`metamorphosis/conformance.py`). M017's "zero false successes" had been a favourable
  draw, not a guarantee.
- M017: all six freeze gates passed. The 50-environment sweep invalidated the proposed
  10× threshold and the criterion became directional.
- M018: hypothesis not supported — destroying does not restore improvement.
- M019: rig not valid — selection too impatient to value learning.
- M021 opened: do these selection measures move true quality?
- Parallelised the measurement scripts, verified bit-identical against the sequential
  outputs.
- Repository made public and translated to English (D012).

## 0.13.0 — 2026-07-31

- Consolidated the repository around living code only: retired the orphan M012/M013b
  stack, about 2,400 lines forming a disconnected import subgraph (D007).
- Added the first permanent CI and `scripts/check_repository_integrity.py` (D008).
- Fixed `pytest -q` and `pip install -e ".[dev]"`, both of which had never worked.
- M014c halted before evaluation and replaced by M017 — self-extending language (D009).
- D010: a measured quantity must have an established dynamic range.

## 0.12.0 — 2026-07-31

- Created the canonical repository.
- Consolidated Metamorphosis M001–M011.
- Added protocols, reports, aggregated results, tests and scripts.
- Created the state, hypothesis, decision and failure registers.
- Opened phase M012: autonomous morphogenesis.
