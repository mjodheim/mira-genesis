# M026 — Related-work map

**Reviewed: 2 August 2026. Public literature only.**

## Closest parent-selection work

### Darwin Gödel Machine

Zhang et al., [*Darwin Gödel Machine: Open-Ended Evolution of Self-Improving
Agents*](https://arxiv.org/abs/2505.22954), grow an archive of self-modified coding
agents. Their published parent weight combines a sigmoid of immediate benchmark
performance with an inverse direct-child count. Every non-perfect eligible node keeps a
non-zero probability, so underexplored stepping stones can survive.

M026 adapts only that parent score. It has no foundation model, SWE-bench task,
diagnostic prompt, asynchronous coding process or claim of reproducing DGM.

### Huxley-Gödel Machine

Wang et al., [*Huxley-Gödel Machine: Human-Level Coding Agent Development by an
Approximation of the Optimal Self-Improving Machine*](https://arxiv.org/abs/2510.21614),
identify the **Metaproductivity–Performance Mismatch**: immediate coding-benchmark
performance can poorly predict the quality of future descendants. HGM estimates
clade-level metaproductivity by aggregating observed successes and failures across an
agent's descendants, then uses Thompson sampling to guide expansion.

M026 adapts that clade aggregation and uses an integer order-statistic analogue of
Beta Thompson sampling. Evaluation and expansion scheduling are deliberately held
fixed so that the guidance measure is the only DGM/HGM-inspired difference.

### Statistical Gödel Machine

Wu et al., [*SGM: A Statistical Godel Machine for Risk-Controlled Recursive
Self-Modification*](https://arxiv.org/abs/2510.10232), admit modifications through
sequential statistical evidence while controlling cumulative error. M026 does not
implement SGM: its finite cases have exact outcomes and its question is parent
guidance, not statistical adoption risk.

## Adjacent foundations

- DeepMind's [goal-misgeneralisation
  work](https://arxiv.org/abs/2210.01790) establishes that training performance can
  conceal a different objective that fails under distribution shift.
- AlphaEvolve combines program evolution with automated evaluators, but optimises
  externally supplied objectives rather than auditing descendant potential against a
  separately decidable ground truth.
- Net2Net provides function-preserving knowledge transfer between known neural-network
  specifications. It does not discover undeclared substrate semantics or transport a
  self-rewrite lineage.

## Mira's narrow contribution hypothesis

Mira Genesis should not claim to originate self-improving agents, proxy failure,
open-ended archives or function-preserving transfer. M026 tests a narrower proposition:

> A finite, auditable rewrite language can expose the difference between immediate
> benchmark performance and exact hidden descendant potential without an LLM judge or
> an approximate ground-truth metric.

The potential contribution is the decidable audit boundary and its integration with
Mira's rewrite lineage. Whether clade guidance actually performs better is an empirical
question; a negative result remains informative.
