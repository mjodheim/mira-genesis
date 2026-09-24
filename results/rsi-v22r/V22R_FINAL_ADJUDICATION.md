# V22R final adjudication — L4 validated

Date: 2026-09-24

Status: **POSITIVE — L4 VALIDATED**

The prospectively frozen V22R replication completed with all three tasks solved without regression.

## Final utilities

- G1 global utility: `(3, 3000, -9, -6)`
- G2 global utility: `(3, 3000, -3, -3)`
- G2 strict per-task process wins: **3/3**
- G2 tasks solved without regression: **3/3**
- Frozen final adjudicator: `v22_positive = true`
- Final workflow guard: `GENESIS_RSI_V22R_L4=PASS`

For every task, both arms reached quality 1000. G2 stopped after one represented request and one round.
G1 required three represented requests and two rounds before stopping on the frozen stall rule.

Per-task process utilities:

- G1: `(1000, -3, -2)`
- G2: `(1000, -1, -1)`

Thus G2 strictly dominates G1 on process utility on all three prospectively selected Brewstead transfer tasks while preserving identical best quality.

## Evidence lineage

- V22 original stopped before any reserved evaluator observation because its freeze record contained two byte-identity mismatches. It has no scientific verdict.
- V22R was frozen prospectively with corrected byte identity and fresh slot identities.
- R1 retained-evaluator run: `35951143503`
- G1 R2 exact retained-evaluator run: `35994451674`
- Final frozen adjudication run: `35994895220`
- Final adjudication artifact id: `10805553187`

This result closes the L4 transfer milestone under the preregistered V22/V22R success semantics. It does not by itself establish L5 recursive meta-improvement; V23 is the successor experiment for that claim.
