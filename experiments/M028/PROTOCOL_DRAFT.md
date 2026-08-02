# M028 — Adaptive evaluation-weighting protocol draft

**Status: FROZEN FOR THE M028 DEVELOPMENT RUN. Not a canonical protocol.**

## Question

After hidden-blind coverage has exposed productive descendants, does adaptively
allocating finite evaluation evidence turn observed clade performance into a better
estimator and parent-selection signal than uniform evaluation allocation?

## Relationship to M027 and HGM

M027 fully evaluated every observed node once. Its clade estimator was therefore an
unweighted mean, whereas exact clade metaproductivity (CMP) is a maximum. Shortcut-heavy
clades dominated the mean even after productive descendants were present.

HGM separates evaluation from expansion. Its public implementation chooses an agent
to evaluate by Thompson sampling over that agent's individual performance, and chooses
an agent to expand by Thompson sampling over evaluations in its descendant clade. Its
default scheduler expands when `evaluations ** 0.6 >= nodes - 1`.

M028 isolates the evaluation-target mechanism; it does not reproduce HGM. M027's
pre-existing depth-three archive makes the original scheduler inapplicable, and this
finite rig has only six development cases per node. M028 therefore uses a fixed common
schedule and never evaluates the same node/case pair twice.

Primary sources:

- Zhang et al., *The Darwin Godel Machine: Open-Ended Evolution of Self-Improving
  Agents*, arXiv:2505.22954;
- Tu et al., *Darwin Godel Machine Needs a Teacher: The Case for Hierarchical
  Metaproductivity*, arXiv:2510.21614;
- the authors' public HGM implementation at `github.com/metauto-ai/HGM`.

## Fixed common intervention

Both policies receive the same M026 rigs and M027 hidden-blind exhaustive coverage
through depth three: 97 expansions and 98 nodes in the mismatch rig, 63 expansions and
64 nodes in the aligned control.

Evaluation then follows the same schedule in both policies:

1. evaluate one deterministic development case on every covered node;
2. allocate two additional unevaluated cases per covered node in aggregate;
3. perform 40 policy expansions using one common weighted-clade parent selector;
4. after each expansion, evaluate one deterministic case on the new node and allocate
   two additional unevaluated cases across the whole archive.

Each node has a seed- and state-specific SHA-256 ordering of the six development
cases. An evaluation consumes the next case in that order. A node/case pair cannot be
repeated. The schedule consequently records a total equal to three times the final
archive size while permitting unequal allocation across nodes.

## Compared evaluation policies

1. `uniform_evaluation` chooses uniformly among nodes with an unevaluated case;
2. `adaptive_evaluation` uses an integer order-statistic analogue of Thompson sampling
   with `Beta(1 + successes, 1 + failures)` on each evaluable node.

Both policies use the same integer Thompson sampler over clade-aggregated observed
successes and failures for parent selection. Selectors receive only node identifiers,
ancestry, depth, observed evaluation counts, remaining-case count, children and
expandability. Hidden cases, hidden scores, exact CMP, rewrite states and action names
remain evaluator-only. Final selection remains M027's common complete development-suite
score with node identifier as the tie-break.

## Pairing and scale

- 64 paired seeds numbered 0 through 63;
- both mismatch and aligned rigs;
- two evaluation policies, for 256 total trajectories;
- 40 post-coverage expansions per trajectory;
- deterministic common task families, case orders and per-state action orders;
- integer-only stochastic decisions;
- four worker processes by default.

Below 64 paired seeds, output must say `insufficient_paired_seeds`.

## Pre-written prediction

Adaptive evaluation weighting will concentrate finite evidence on observed
high-performing agents and thereby soften the mismatch between an unweighted clade
mean and exact maximum descendant quality. The prediction is supported only if all of
the following pass:

1. the adaptive policy's median weighted-clade/exact-CMP concordance is non-negative;
2. that concordance exceeds the uniform policy by at least 167 per mille;
3. adaptive evaluation exceeds uniform evaluation by at least 167 per mille in median
   paired final hidden quality;
4. adaptive evaluation wins at least 40 of 64 paired mismatch seeds;
5. the aligned control retains exact visible/hidden equality;
6. coverage, unique-task and selector-isolation controls all pass.

Estimator alignment without policy advantage is reported separately and does not
count as support. Allocation share on evaluator-identified high-potential observed
nodes is diagnostic only and is not a decision gate.

## Prohibited conclusions

M028 cannot establish general superiority of HGM, reproduce HGM's asynchronous
scheduler or software benchmarks, validate DGM or HGM as complete systems, establish
software-scale recursive improvement or support a canonical claim. A failed gate must
not be repaired by changing the threshold, evaluation schedule or task count after
the 64-seed result is observed.
