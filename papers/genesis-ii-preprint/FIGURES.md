# Genesis II — figure and table provenance

All publication figures are downstream of preserved M107–M112 artifacts. They may summarize frozen values; they may not re-run an experiment with altered parameters, filter worlds for presentation, or silently replace a negative predicate.

## Figure 1 — experimental chain

`figures/fig1_chain.pdf`

M107 → M108 → M109 → M110 → M111 → M112. The diagram distinguishes lineage-changing experiments (M107–M111) from M112, which changes world provenance while reusing the frozen M110/M111 instruments.

Sources: D076–D081 and the six `experiments/M10{7,8,9}/RESULT_SUMMARY.md`, `experiments/M11{0,1,2}/RESULT_SUMMARY.md` files.

## Table 1 — M110 transfer

Unanimous six-world outcomes:

| demand | producer census | ground truth | `M0` | `M1` | `M2` |
|---|---|---|---|---|---|
| row 7 | inside | signal interface | 0/6 | 6/6 | 6/6 |
| row 3 | inside | candidate space | 0/6 | 0/6 | 6/6 |
| **row 5** | **outside** | **operator table** | **6/6** | **0/6** | **0/6** |
| row 1 | inside | operator table | 6/6 | 6/6 | 6/6 |

Source: `experiments/M110/RESULT.json` and `RESULT_SUMMARY.md`.

## Figure 2 — capacity versus competence

`figures/fig2_capacity_competence.pdf`

Recorded M110 `ReachImprove` min–max across six worlds:

- `M0`: 94–261;
- `M1`: 134–449;
- `M2`: 324–558.

Row-5 solved worlds: 6/6, 0/6, 0/6. The figure deliberately plots ranges rather than inventing a representative world or average not stated in the summary.

Source: M110 preserved result/summary.

## Table 2 — M111 diagnosis

Three canonical ambiguous worlds, one probe per world. The acquired policy is the only arm that resolves both members of the ambiguous pair under the frozen sequence budget.

Source: `experiments/M111/RESULT.json` and `RESULT_SUMMARY.md`.

## Figure 3 — policy expressibility

`figures/fig3_expressibility.pdf`

- M1 policy rule space: 18; separating row 3 from row 7: 0.
- M2 policy rule space: 127; separating programs: 25.

Source: `experiments/M111/RESULT.json`, `scientific_evidence.expressibility`.

## Figure 4 — blind-world fixed point

`figures/fig4_blind_closure.pdf`

M112 transfer P5 blind world: image size 17 at node bound 7, 18 at 9, 18 at 11, 18 at 13. The manuscript caption explicitly states that P5 is a real failed predicate and that bound 7 had sufficed across 1,160 project-generated worlds.

Source: `experiments/M112/RESULT.json`, `RESULT_SUMMARY.md`, and the recorded project-world census.

## M112 interpretation rule

The blind transfer outcome table reproduces the M110 scientific outcomes, including row-5 harm, but the arm remains **22/24 negative** under the inherited rule. Captions and prose must not simplify this to “M112 transfer passed.” Diagnosis is **24/24**.
