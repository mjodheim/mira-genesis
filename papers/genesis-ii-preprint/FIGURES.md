# Genesis II — figures and tables

Each entry names the frozen artifact it is read from. Nothing is drawn from a development run, and
nothing may be recomputed with a changed parameter to make a figure cleaner.

## Figure 1 — the chain, and where each generation came from

The lineage from M107 to M111 as a single diagram: interpreter extension, machinery modification,
second machinery generation, transfer, diagnosis. Each arrow labelled with the decision slot and the
state digest the successor restores.

Source: D076–D080; `experiments/M109/RESULT.json` `stage_two_resolution.final_state_digest`
(`5c08fa30…`), which is the state M111 restores.

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

## Table 4 — the preserved negatives

M095, M098, M103 and M105, each with what it cost and what it bought. A paper that reports only the
positives on this line is misreporting the line.

Source: `DECISIONS.md`, `FAILURE_LOG.md`.

## Table 5 — what did not move

The G1–G10 evidence map before and after M107–M111: unchanged. Placed in the body, not an appendix.

Source: `MIRA_GENERALITY_CRITERIA.md`.
