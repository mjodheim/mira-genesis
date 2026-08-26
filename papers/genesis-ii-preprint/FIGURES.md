# Genesis II — figures and tables

Each entry names the frozen artifact it is read from. Nothing is drawn from a development run, and
nothing may be recomputed with a changed parameter to make a figure cleaner.

## Figure 1 — the chain, and where each generation came from

The lineage from M107 to M112 as a single diagram: interpreter extension, machinery modification,
second machinery generation, transfer, diagnosis, and then the same instruments re-run on worlds the
project did not choose. Each arrow labelled with the decision slot and the state digest the successor
restores; the last arrow labelled with the published bank commitment rather than a state, because
M112 changes the population and not the lineage.

Source: D076–D081; `experiments/M109/RESULT.json` `stage_two_resolution.final_state_digest`
(`5c08fa30…`), which is the state M111 restores; `experiments/M112/PUBLIC_BANK_COMMITMENT.json`.

## Table 1 — census-conditional transfer (M110)

| demand | producer census | ground truth | `M0` | `M1` | `M2` |
|---|---|---|---|---|---|
| row 7 | inside | signal interface | 0/6 | 6/6 | 6/6 |
| row 3 | inside | candidate space | 0/6 | 0/6 | 6/6 |
| **row 5** | **outside** | **operator table** | **6/6** | **0/6** | **0/6** |
| row 1 | inside | operator table | 6/6 | 6/6 | 6/6 |

Source: `experiments/M110/RESULT.json`, six canonical worlds, unanimous.

## Figure 2 — capacity against competence

`ReachImprove` per arm across the six M110 worlds (`M0` 94–261, `M1` 134–449, `M2` 324–558, strict on
every world) plotted against resolved row-5 demands (1, 0, 0). The two lines cross. This is the
paper's central image and should be its first figure after the chain.

Source: `experiments/M110/RESULT.json` `reach_improve` and `rows.5.solved`.

## Table 2 — the derivable boundary

Feature rows against the producer's reachable census, the conservatism pinning, and the acquired
program's value at each row — showing that the row-5 failure follows from the producer's own record
before any consumer world runs.

Source: `experiments/M109/RESULT.json` `domain.rows`, `domain.unreachable_rows`,
`generation_one.acquisition.unobserved_relevant_rows_held_non_firing`.

## Table 3 — self-directed diagnosis under a scarce budget (M111)

| arm | `A` | `B` | probes |
|---|---|---|---|
| `M0`, `M1` | 0/3, 0/3 | 0/3, 0/3 | 0 |
| `M2` | 3/3 | 0/3 | 0 |
| `always_signal` | 0/3 | 3/3 | 0 |
| never-probe | 3/3 | 0/3 | 0 |
| always-probe | 3/3 | 0/3 | 3 |
| **acquired policy** | **3/3** | **3/3** | 3 |

Source: `experiments/M111/RESULT.json`, three ambiguous worlds, both probe orders.

## Figure 3 — expressibility created by the previous generation

The policy rule space at `M1` (18 programs, 0 separating row 3 from row 7) beside `M2` (127 programs,
25 separating), with the operator that made the difference — truth table `[1, 0]` — labelled as
adopted by the lineage while resolving M109's own stage two.

Source: `experiments/M111/RESULT.json` `expressibility`, `provenance.acquired_operator`.

## Table 4 — the same instruments, on worlds the project did not choose (M112)

The M110 transfer table and the M111 diagnosis table, recomputed on the revealed blind bank, beside
the originals. Every scientific outcome reproduces — including the row-5 harm — while the transfer
arm is recorded **negative at 22/24**:

| demand | ground truth | `M0` | `M1` | `M2` |
|---|---|---|---|---|
| row 7 | signal interface | 0/6 | 6/6 | 6/6 |
| row 3 | candidate space | 0/6 | 0/6 | 6/6 |
| **row 5** | **operator table** | **6/6** | **0/6** | **0/6** |
| row 1 | operator table | 6/6 | 6/6 | 6/6 |

Diagnosis: 24/24, five ambiguous blind worlds, both probe orders, unanimous.

The two false predicates must be named in the caption, not in a footnote: `P1` is an invocation
artifact — a preflight asserting a `canonical`-tagged population at the canonical path, while the
revealed bank sits at a scratch path — and `P5` is a real measurement. Both are reported rather than
suppressed, and neither was weakened after the fact.

Source: `experiments/M112/RESULT.json`, `CHECK_REPORT.json`, `RESULT_SUMMARY.md`.

## Figure 4 — a bound that was an empirical regularity, not a certificate

The constructive image size against fixed-point bound for the blind world that failed `P5`: **17 at
bound 7, 18 at 9, 11 and 13**, beside the 1 160 project-generated worlds on which seven nodes always
sufficed. The declared operating bound is 9 and the image is stable at and above it, so no reach
claim is disturbed — but the certificate demanded all four bounds agree and they do not.

This is the package's cleanest evidence that project-authored worlds are not a neutral sample, and it
was produced by the project being wrong under a commitment published in advance. It belongs beside
Figure 2, not in an appendix.

Source: `experiments/M112/RESULT.json`; base rate from the 1 160 project-generated worlds recorded in
`MATERIALIZATION_DEFECT.md`.

## Table 5 — a defect recorded before the seal, and not repaired

M112's frozen spec set `requested_record_count = requested_world_count` while a world is five
records, so a request for 100 bought 20. The note recording it was written **after the single
invocation and before the bank was sealed, committed, revealed or read**, and it states the expected
cost — a drop from ~94 per cent to ~12 per cent of meeting the plan's minimum — before the outcome
was knowable.

The bank met the minimum anyway, at an ambiguous rate of 25 per cent against the project's own 6.
Both halves belong in the paper: the defect was not repaired because repairing it would have been a
second qualifying invocation after learning something about the first.

Source: `experiments/M112/MATERIALIZATION_DEFECT.md`.

## Table 6 — the preserved negatives

M095, M098, M103 and M105, each with what it cost and what it bought. A paper that reports only the
positives on this line is misreporting the line.

Source: `DECISIONS.md`, `FAILURE_LOG.md`.

## Table 7 — what did not move

The G1–G10 evidence map before and after M107–M112: unchanged. Placed in the body, not an appendix.
M112 removed **world** authorship and left the carrier, the evaluator, the component registry, the
feature vocabulary and the probe primitive where they were, so no row moves and the caption says
which authorship was removed and which was not.

Source: `MIRA_GENERALITY_CRITERIA.md`.
