# M038 — protocol and mechanism freeze

**Status: frozen before the canonical task was derived or observed.**

The commit containing this record is the frozen parent that the marker-only arming commit
must name. Its SHA cannot be embedded in this file without self-reference; the child marker
records and the guard verifies it.

## Frozen protocol

| Identity | Value |
|---|---|
| Path | `experiments/M038/PROTOCOL.md` |
| Byte length | **16,877** |
| Git blob SHA | `201e0bace1bf969ce10511f8d3e23339227e4624` |
| SHA-256 | `f717740c24d5028dd660c066477e8690c9a7559f43e03cb57c4b875c1f3ee326` |

These protocol bytes are immutable. A canonical marker carrying another digest is rejected.

## Frozen mechanism parent

The complete mechanism immediately before this freeze record is:

`6c050c77d75403016b970ef1ba3043aa2cdbd12f`

It contains:

- typed canonical serialisation and immutable journal bytes;
- compact rolling commitments;
- externally anchored checkpoint and causal journal;
- exact structural-incapacity certificates with no greedy fallback;
- three-arm DFA integration;
- F0 → F1 adoption and forced rollback to F1;
- projected archive;
- deterministic cost vectors and B/C ordering;
- unopened head-derived sealed specification;
- marker-only canonical guard and canonical runner;
- archived development and freeze-candidate workflows.

No `experiments/M038/CANONICAL_ARMED.json` existed at this parent, and no sealed task seed had
been derived.

## Protocol-identity run

The protocol identity was computed by GitHub from the indexed bytes, without importing the
sealed specification:

| Identity | Value |
|---|---|
| Workflow run | `30900171596` |
| Artifact id | `8888720086` |
| Artifact name | `m038-freeze-candidate-12a2140ed9e37cba01fa0cb991527668c956b8e9` |
| Archive digest | `sha256:84fb203ed3454675084bd791e0979c64483f0e6ba8c837feaeb10ae19df62329` |
| Identity JSON SHA-256 | `1335f81ff99d4d82cfbacba2b3f2ba88ed6db4a436e0ae3f0b9a8d3a7664d03a` |
| Canonical marker absent | `true` |
| Sealed seed derived | `false` |

The protocol blob remained `201e0bace1bf969ce10511f8d3e23339227e4624` through the
mechanism parent above.

## Verification at the mechanism parent

Permanent CI run `30900851165` verified the exact mechanism parent:

| Job | Result |
|---|---|
| Repository integrity | **pass** |
| Tests — Python 3.11 | **466 passed** |
| Tests — Python 3.13 | **466 passed** |

The only failure before this final green run was a mismatch between an exception's wording
and the regex in its test. The guard already rejected the false parent. The wording was made
explicit — `actual parent commit` — without changing a mechanism, budget, generator or
consumed result.

## Consumed development result

The integrated development cycle at head
`699c162bc9b871bbb897a6c29a83d75f190b3129` is recorded in
`results/M038_DEVELOPMENT_CYCLE.md`. It is consumed and cannot confirm the canonical run.

## What is now forbidden

After this freeze record:

- `experiments/M038/PROTOCOL.md` may not change;
- mechanism code, budgets, orders, metrics, falsifiers and guard rules may not change before
  the first canonical artifact;
- no development task may select or confirm a rule;
- no second arming commit may replace the first;
- no rerun may replace the first canonical artifact;
- no negative result may trigger widening, tuning or another seed.

## Next and only permitted mechanism-changing action

No mechanism-changing action is permitted.

The only next commit allowed before the canonical artifact is a marker-only child with:

- exact commit message `m038(canonical): arm first immutable run`;
- exactly one changed file, `experiments/M038/CANONICAL_ARMED.json`;
- this freeze-record commit as `frozen_parent_sha`;
- protocol SHA-256
  `f717740c24d5028dd660c066477e8690c9a7559f43e03cb57c4b875c1f3ee326`;
- `first_run_only = true`;
- `reruns_are_reproductions_only = true`.

That child SHA reveals the single sealed task seed. Until the child exists, the task remains
uninstantiated.
