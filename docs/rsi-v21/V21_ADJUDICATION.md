# Genesis RSI V21 — Brewstead cross-stack transfer adjudication

Status: **positive process-dominance evidence; formal L4 gate not fully reproducible from the retained V21 artifacts**.

## What V21 tested

V21 transferred the already-frozen G1/G2 search policies to three independent repair processes in the external `mjodheim/mjodheim-brewstead` Java/Spring host at commit `720b27c8bc80de16c04953e13d5f9e8425beea8c`:

1. `brewstead-chat-rate-window`
2. `brewstead-farm-plant-ownership`
3. `brewstead-brew-quality-bonus`

The proposer did not receive evaluator-only tests or evaluator results. G2 was already canonical before V21. Its observed stopping rule is `best_quality_milli >= 780`; G1 retained its broader two-parent search and one-round stall rule.

The preregistered L4 success condition recovered from the frozen design record was: G2 resolves **3/3** tasks without regression, is strictly better than G1 on at least **2/3** repair processes, and has higher global utility.

## Frozen observations

Each task produced a shared R1 champion at `quality_milli = 1000` before the G1-only R2 bundles were built. The R2 manifests therefore bind the laboratory-observed champion quality rather than a later reconstruction.

| task | R1 champion | quality | source relation to oracle | G2 | G1 |
|---|---|---:|---|---|---|
| chat rate window | `...child-e9959d71ac62` | 1000 | byte-identical Git blob to host oracle | stops | opens two R2 slots |
| farm ownership | `...child-82618bd9b063` | 1000 | byte-identical Git blob to host oracle | stops | opens two R2 slots |
| brew quality | `...child-c0530c8c4399` | 1000 | same quality summands as oracle, opposite addition order | stops | opens two R2 slots |

Across all three processes, G2 therefore consumes **3 represented proposal observations total** (one per task). G1 consumes **9** (the same three R1 observations plus six R2 observations). Because the shared R1 champion is already at the 1000 ceiling, the additional G1 observations cannot improve best quality. G2 strictly Pareto-dominates G1 on best-quality/observation cost on **3/3 processes**, exceeding the preregistered `>=2/3` process condition.

## R2 result shape

The six R2 outputs were mechanically valid under their exact supplied bundles. Chat and Brew produced no functional gain over their already-1000 child; Farm found a validation-order refinement, but its parent was already at the quality ceiling. G1 therefore stopped after R2 under its one-round stall rule. No R3 is warranted.

## Traceability defect

The original frozen V21 evaluator-only source and the exact V21 scalar global-utility formula are not present in the currently retained Library or reachable Git refs. They must **not** be reconstructed after observing V21 outcomes.

This does **not** erase the frozen facts that the R1 champions were recorded at 1000 before R2, that Chat/Farm restore the exact oracle source blobs, or that G2 uses fewer observations at identical best quality. It does mean that the final scalar `global_utility(G2) > global_utility(G1)` predicate cannot be independently recomputed byte-for-byte from the surviving V21 package.

Accordingly this record does not silently upgrade V21 to a fully reproducible L4 proof. It records the positive transfer evidence and the archival failure separately. The clean successor experiment must precommit and retain its evaluator identity, utility implementation, task-selection rule and reveal boundary before any proposer output.
