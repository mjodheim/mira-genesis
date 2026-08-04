# M038 — trigger algorithm calibration

**Status: development calibration. Not an M038 outcome. No sealed block created or opened.**

This measurement selected the escalation trigger's algorithm. It is recorded because a
measurement that chooses a mechanism must be reproducible and its cases must be marked
consumed.

## What was decided by this measurement

Whether `proved_structural_incapacity` uses a **greedy** or an **exact** maximum
pairwise-distinguishable set.

## Cases, and their status

**Consumed for this decision.** Six consumed development cases from the generator family
used by M035–M037. They were already consumed as a development block, and this measurement
consumes them again for the algorithm choice.

An earlier version said "the same cases M035, M036 and M037 used". Those experiments did not
all use the same number of cases in every comparison, so the phrase overstated the identity.
What is shared is the generator family and the seed formulas below.

They may not confirm the new trigger's success or efficiency. That requires a block never
used to choose anything.

| | |
|---|---|
| Generator | `random_minimal_dfa(50_000 + index × 7919, 4, 6)`, normalised |
| Target | `make_out_of_language_target(base, 51_000 + index × 7919)` |
| Cases | index 0–5 |
| Observation sets | `enumerate_words(5)` = 63 words, `enumerate_words(6)` = 127 words |
| Rows | 12 (6 cases × 2 observation sets) |

The observation sizes 63 and 127 are **development observation sizes**. No prior versioned
commitment fixed them before this measurement, so they are not described as committed.

## Algorithm measured

| | |
|---|---|
| `algorithm_id` | `exact-max-pairwise-distinguishable` |
| `algorithm_version` | `1` |
| `development_safety_ceiling` | 2,000,000 |
| Python | 3.11.15, diagnostic |
| Platform | Windows, diagnostic |

### Exact identity

"`bdf5ba3` plus the calibration script" was not a Git identity — it named a commit that did
not contain the script. The identity is:

| | |
|---|---|
| Base implementation commit | `bdf5ba300b2e034238d41b600b127fea31d97293` |
| Calibration script blob SHA | `6e9903cd5c39fb951d752339a1990ff4ab6102a6` |
| First commit containing both script and report | `da104b66ebce661e23d0ae34ee97c07837c7b156` |
| Versioned output | [`results/artifacts/M038_TRIGGER_CALIBRATION.json`](artifacts/M038_TRIGGER_CALIBRATION.json) |
| SHA-256 of that output | `1a38a5d31c8e7cd1851215db5aa8b915f656d1aa3b9bff52f7f6dbfacc7ddffb` |

The JSON artifact holds only machine-independent content — algorithm identity, ceiling,
per-row figures, totals — so its digest reproduces on any platform. The interpreter version
and platform string are printed as diagnostics and deliberately excluded from the digested
payload. `.gitattributes` stores it byte-exact, because an end-of-line conversion would
change the digest.

### The ceiling is not the M038 budget

2,000,000 is a **development safety ceiling**: it bounded this calibration, and no versioned
commitment fixed it beforehand. The M038 certificate budget is committed separately, in
`experiments/M038/PROTOCOL_DRAFT.md`, before any M038 measurement — and choosing the same
figure there is a decision taken in knowledge of these consumed rows, not a value inherited
from them.

Branch-and-bound over the distinguishability graph, seeded with the greedy result as
incumbent, canonical tie-breaking (lexicographically smallest maximum clique among
equal-size maxima; shortest then lexicographically smallest separating suffix).

## Definitions, stated because the first report left them ambiguous

```
gap_a(case) = exact_bound − greedy_bound            recoverable by a better search
gap_b(case) = true_minimal_states − exact_bound      limit of the observed evidence
```

Both are summed over **all twelve rows**. An earlier note reported "Gap A = 4", which was
the per-observation-set subtotal and was not defined as such.

## Results

| Quantity | Value |
|---|---:|
| Rows measured | 12 |
| **Gap A, summed** | **8** |
| **Gap B, summed** | **0** |
| Rows where greedy understated | **6 of 12** |
| Rows where the evidence understated | **0 of 12** |
| Exact bound equal to true minimal size | **12 of 12** |
| Maximum search nodes used | **515,432** |
| Maximum pair tests | 8,001 |
| Development safety ceiling exceeded | **no** |

Per-row figures, including seeds, prefix counts, both bounds, both gaps and the
deterministic counters, are produced by the calibration script and reproduce exactly.

## What this supports

The exact search is tractable at these sizes under **counted operations**: 515,432 search
nodes at worst against a 2,000,000 development safety ceiling, never exceeded. Wall clock
plays no part in this conclusion — this repository decides on counted operations, per M017
§9.

Every observed false negative was **algorithmic**. The greedy understated on 6 of 12 rows;
the exact search matched the true minimal state count on all 12.

## What this does not support

It does not show the exact certificate works as an escalation trigger. That has never been
measured — see the correction in `docs/PRIOR_ART_INTEGRATION.md`.

It does not show Gap B is zero in general. Evidence incompleteness is epistemic and
survives any algorithm; it was simply not exercised by these twelve rows.

It does not license reuse of these cases for any later confirmation.

## Reproduction

The script derives every case from the seeds above, uses no randomness beyond them, and
emits a JSON record with per-row deterministic counters. It reads no sealed data.
