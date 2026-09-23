# RSI V22 pre-run amendment 001 — retain executable G1/G2 policy bytes

Status: **prospective amendment before any V22 proposer output**.

The initial V22 freeze bound G1 and G2 by SHA-256/digest but did not retain their executable source bytes in the V22 apparatus branch. That is sufficient to name the policies but insufficient for a self-contained autonomous replay.

No V22 proposer has been invoked and no V22 reserved evaluator has been run on a proposal. This amendment therefore changes no observed outcome, task, evaluator, utility rule, policy behavior, search budget, stopping rule, or success criterion.

The exact pre-existing policy bytes are now copied into:

- `experiment/rsi_v22/policies/g1_search_policy.py`
- `experiment/rsi_v22/policies/g2_search_policy.py`

Required SHA-256 identities:

- G1: `3354f887a93a08d9f00e9c54ccb097003f727ba77c1e1b4e9997adf676d35434`
- G2: `69d0d725601cd32adff27379dbb25f5c7be29946f9e9c6ac4858a0634cbd5fdf`

G2 is the already-selected V19 policy whose metadata is `(10, 6, 3, 5, 5, 4, 8, 1, 8, 3)` and whose observable-state stop condition begins with `best >= 780`. G1 is the frozen predecessor with metadata `(10, 6, 3, 5, 5, 4, 8, 2, 8, 1)`.

After these files are committed, the unchanged V22 calibration workflow must pass again. A second freeze record will then supersede the first for execution identity while preserving the first as chronology.
