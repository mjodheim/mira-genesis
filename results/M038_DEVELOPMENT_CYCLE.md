# M038 — consumed integrated development cycle

**Status: development result, consumed. Not an M038 outcome. No sealed block was created or opened.**

This is the first repository-executed integration of the M038 mechanism. It ran once in the
`M038 development cycle` workflow on pull-request head
`699c162bc9b871bbb897a6c29a83d75f190b3129`.

| Identity | Value |
|---|---|
| Workflow run | `30899489107` |
| Workflow artifact | `8888443102` |
| Artifact name | `m038-development-cycle-699c162bc9b871bbb897a6c29a83d75f190b3129` |
| GitHub archive digest | `sha256:e5a58f5f6dbd38ee051caf2d05528084bc59806f4ff91cd1b6db7c075da1ff6d` |
| Uncompressed JSON SHA-256 | `a94aab335898e479390648dc163a91d360f5df263fa58bc2e48339121ff1ee71` |
| Development seed | `380038` |

The seed, task, candidate order, witnesses, F1 and every counter below are consumed for
implementation development. They may reproduce or diagnose this run, but may not confirm a
later trigger, functional or efficiency claim.

## Pre-result commitment

The parameters were committed in `experiments/M038/IMPLEMENTATION_COMMITMENT.md` before the
workflow executed:

- four-state minimal founder;
- target derived by the first canonical structural program that both grows minimal state
  count and yields an exact structural-incapacity certificate;
- all 127 binary words of length at most six admitted as oracle evidence;
- exact certificate budget: 2,000,000 search nodes and 512 prefixes;
- proposal vocabulary: 36 M017 atoms and eight explicit growth atoms;
- proposal depth at most three and 100,000 candidate-search nodes;
- first evidence-consistent candidate passing independent exact equivalence is adopted;
- fixed rollback probe `flip(initial)`;
- C is a strict instrumentation superset of B;
- strict efficiency dimensions fixed before the run.

## Task obtained

| Property | Value |
|---|---:|
| Founder minimal states | **4** |
| Target minimal states | **5** |
| Generating-program length | **2 symbols** |
| Oracle observations | **127** |
| Certificate lower bound | **5** |
| Certificate status | `available` |
| Certificate search nodes, first computation | 60,505 |
| Certificate pair tests, first computation | 8,001 |
| Certificate suffix probes, first computation | 1,016,127 |

The proposer was not given the target. It received the founder and the 127 oracle answers.
The target was held by the independent exact evaluator.

## Functional verdict

| Arm | Outcome |
|---|---|
| A — fast path only | **unsolved**; 4-state body against a proved minimum of 5 |
| B — two-speed lineage | **functional metamorphosis supported** |
| C — full critical-path journal | **functional metamorphosis supported** |

For both B and C:

- the exact certificate triggered one escalation;
- the slow path recomputed the same certificate;
- candidate search used 1,666 nodes;
- 1,557 terminal candidates were constructed;
- two evidence-consistent candidates reached exact evaluation;
- F1 is exactly equivalent to the target;
- a separate provisional `flip(initial)` candidate failed exact evaluation;
- rollback restored the exact F1 functional-state digest;
- the lineage returned to the fast path with F1 active;
- no RNG draw and no external model were used.

The shared anchors are:

| Anchor | Digest |
|---|---|
| Compact fast-path head | `c6ed321b571481257b7bc84817e250fdda8ad2bb275926cdd0ac76720344c952` |
| Checkpoint digest | `f81b30d67dd7d3106ca121d681e7a53d97ee84923b4c9d5a0e403cf7aa702828` |
| Slow causal-journal head | `35a3a604af5a62100c7c16674fd28380d775509e40308cccb08fcf792dcb5576` |
| Final F1 functional-state digest | `7f29ec19847413c091d8e57befe9a2cbb3f2a4fe3a09abba457296640f43ea0d` |

B and C produced the same decision-transcript digest:

`ef7c283b1b264632b812953b6d56254066cda96f21969ac93d67242339f30e21`

## Efficiency verdict

B and C produced identical compact traces, functional counters, checkpoint, slow journal,
F1 and decision transcript. C added 127 full immutable fast-path records.

| Proof-cost dimension | B | C |
|---|---:|---:|
| Persisted event serialisations | **12** | 139 |
| Persisted journal bytes | **11,985** | 89,940 |
| Audit deterministic operations | **480** | 1,242 |
| Body serialisations | 1 | 128 |
| Hash operations | 164 | 418 |
| Peak persistent audit artefacts | 13 | 140 |

B is no worse on every pre-registered proof-cost dimension and is strictly better on all
three primary dimensions. The development efficiency hypothesis is therefore supported.

## Verdicts

| Verdict | Result |
|---|---|
| Decision equivalence B/C | **supported** |
| Compact-trace equality | **supported** |
| Evidence B strict subset of C | **supported** |
| Infrastructure cycle valid | **supported** in B and C |
| Functional metamorphosis | **supported** in B and C |
| Efficiency hypothesis | **supported** |
| Combined expected development claim | **supported** |

## What this does not establish

This single consumed task does not establish an M038 outcome, Gate 2, Gate 9, multi-cycle
reuse, trans-substrate migration, post-migration plasticity or general intelligence.

No tool was constructed by the lineage. Every available symbol was protocol-supplied, so
this run makes no Gate 2 claim.

The next scientific step requires a frozen protocol, a guarded head-derived sealed task and
the first immutable canonical run. None existed when this development result was produced.
