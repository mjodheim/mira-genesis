# M066 status

## Current phase

**Canonical result: positive. Experiment closed.**

The unique frozen execution completed on marker-only head
`2cf454ca4e393a319f89ae5afbcd5e3f9250182c`. Guard, first result and independent reproduction all
passed in workflow run `31291899534`, attempt `1`, without rerun or retuning. The selector chose
bank index `0` from the unchanged four-entry task bank.

## Canonical identities

- frozen parent: `4a4b4a1a1e4831a4e1f8a40f896e3b2921cdc6e5`;
- marker-only canonical head: `2cf454ca4e393a319f89ae5afbcd5e3f9250182c`;
- protocol SHA-256: `f66ab480dfa0631e730753b7e45e3b83da7e2938d3e28e4aa2f497a6e383d66b`;
- frozen protocol file SHA-256: `02cabd7d86a93ceaba811b591b6c271cf066653add61044af83143558e2fd1c0`;
- canonical manifest digest: `b7d4c39c4c89c85346f4b0b2ebbf390e9f8818d4369a6ed4e21fb8d0580a62b1`;
- exact first-result SHA-256: `eaf6fee975bddaae583e0f739d0a5ad050209b303d304eddc81bb6320c642ace`;
- exact reproduction-report SHA-256: `b990efa4c85c808349de046b7b7ed7477138b77c5111f7385e913f7583ab77cc`;
- first-result seal SHA-256: `0468dbccbe95d0185579b8e46500c0c9518e4912821aed1ab6a63b16b61c198a`;
- canonical audit SHA-256: `9923a385a8a73eda87c80cfa90e8841f9cb6aa9bac3d9004914ed44c49360d23`.

The immutable result, reproduction report, first-result seal and audit are preserved under
`results/artifacts/`. The human-readable report is `results/M066_CANONICAL_RESULT.md`.

## Verdict

The complete continued lineage accepted three post-migration whole-WebAssembly rewrites, reached
version twelve, passed 68/68 retained cases and 18/18 hidden observations. Fresh-on-B,
unchanged-parent-migrated and learned-state-ablated accepted zero rewrites and passed 0/18. The
forced rollback returned a separately deserialised and audited object identical to the pre-fault
commitment; memory grew from one to four native episodes and deterministic replay was exact.

Python 3.13.14 independently reproduced the 51,553 result bytes exactly. The preservation audit
therefore establishes Gate 10 in addition to the nine scientific gates already carried by the raw
manifest. All ten bounded completion gates are true in this CPython → Node ESM → whole-WebAssembly
lineage.

## Closure boundary

No second M066 canonical run is permitted. M064 and M065 remain negative and unchanged. The result
does not grant repository, network, credential, deployment or production authority and does not
support claims of open-ended evolution, general intelligence or consciousness.

The consumed workflow remains byte-identical to its frozen 23-file commitment as its immutable
execution record. It has no manual-dispatch trigger. Any later change to the marker path would have
more than one first-parent occurrence, so the guard stops before the first-result job; a workflow
rerun also fails the `github.run_attempt == 1` condition. This is the archived closed state without
rewriting the frozen workflow after observation.
