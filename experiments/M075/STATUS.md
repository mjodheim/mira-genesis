# M075 status

**PUBLIC MODEL DEVELOPMENT COMPLETE — PROMISING, NON-SCIENTIFIC, NON-CAUSAL.**

- New task-agnostic epistemic/budget context: implemented and unit-tested.
- Separate public development bank: 3 matched pairs, 6 tasks.
- Real-container dry run: 12/12 episodes, zero defect, zero model token.
- Record SHA-256: `cb194a4092c3900b0befbe259d851a8b145b14c8110f8df3b462a2ee5b745699`.
- Committed model-development run: 12/12 episodes, 43 live decisions, zero defect/retry.
- Baseline: 0/3 true refusals, 0/3 false refusals, margin 0.0, 12 wasted steps.
- Epistemic context: 2/3 true refusals, 0/3 false refusals, margin 2/3, 4 wasted steps.
- Both conditions: 3/3 feasible external success; context submitted all three, baseline none.
- Result SHA-256: `dadd202886e866e31be5cefb130e9e231f7739a0b49166f8d0c1dd2766acf949`.
- H21: still scientifically untested; public independent samples are not a causal estimate.
- Private independent scientific bank: absent and unopened.
- Pre-private causal/sealed-bank validator: implemented; 8 focused tests pass.
- Readiness: correctly blocked on missing external envelope, SSH signature, signer allowlist and
  frozen private protocol; no private payload was accessed.
- Gate advance: none.

Forward reference only; no value above is changed by it. A separate, weaker successor protocol
**M075-B** now exists at `experiments/M075B/`. It obtains a held-out bank from a context-isolated
external generator rather than an independent human maintainer, and reaches the
`blind_generated_sealed_bank` evidence tier. It does **not** satisfy the requirement recorded
above, does not support H21, and does not close issue #112, which remains open. See D055.
