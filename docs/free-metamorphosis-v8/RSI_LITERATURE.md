# RSI literature review informing Genesis Free Metamorphosis v8

This note records the external methodological ideas used to design v8. It is not evaluator evidence and contains no hidden Mira cases.

## 1. Darwin Gödel Machine

Zhang, Hu, Lu, Lange, Clune. "Darwin Gödel Machine: Open-Ended Evolution of Self-Improving Agents." arXiv:2505.22954; ICLR 2026.

Key transferable ideas:
- preserve a growing archive of viable self-modified agents;
- sample parents from the archive instead of greedily using only champion/latest;
- keep lower-scoring but functional variants because later descendants can turn them into stepping stones;
- penalize repeatedly expanded parents so underexplored nodes remain reachable;
- use empirical evaluators rather than impossible formal proofs of net improvement;
- preserve full lineage and sandbox generated code.

Direct implication for v8:
- remove v7's depth-2 neutral ceiling;
- do not delete the archive on champion promotion;
- keep non-zero parent-selection probability for every viable node;
- separate archive viability from champion fitness.

## 2. Group-Evolving Agents

Weng et al. "Group-Evolving Agents: Open-Ended Self-Improvement via Experience Sharing." arXiv:2602.04837.

Key transferable ideas:
- tree branches waste discoveries when experience is isolated;
- select parent groups by performance plus novelty;
- explicitly reuse cross-branch experience;
- use task-response/behavior vectors to characterize diversity where possible.

Direct implication for v8:
- each proposer receives a primary parent and a reference parent;
- reference information can influence diagnosis and mutation while the patch remains single-parent and mechanically auditable;
- parent selection combines quality, novelty and under-exploration.

## 3. Mendel Gödel Machine

Liu et al. "Mendel Gödel Machine: Recursive Self-Improving Coding Agents via Comparative Evolution." arXiv:2608.07645.

Key transferable ideas:
- single-trajectory mutation leaves comparative information unused;
- reaction-norm mutation can reason over multiple task trajectories;
- cross-lineage hybridization can use another lineage's trajectory as evidence without requiring literal source-level crossover.

Direct implication for v8:
- cross-lineage comparison is first-class in proposal context;
- v8 does not physically merge two parent codebases; it uses a reference branch as comparative evidence, preserving exact patch causality.

## 4. MetaSkill-Evolve

Wang et al. "MetaSkill-Evolve: Recursive Self-Improvement of LLM Agents via Two-Timescale Meta-Skill Evolution." arXiv:2607.05297.

Key transferable ideas:
- self-evolution is not fully recursive if the improvement procedure is fixed;
- each branch can carry a branch-local meta-skill parameterizing Analyzer, Retriever, Allocator, Proposer and Evolver;
- task skill and meta-skill should evolve at different timescales.

Direct implication for v8:
- every archive node inherits an evolver profile;
- profile edits are slower than organism edits;
- the parent profile governs the current proposal; child profile changes influence only future descendants, preserving causal direction.

## 5. STOP

Zelikman, Lorch, Mackey, Kalai. "Self-Taught Optimizer (STOP): Recursively Self-Improving Code Generation." arXiv:2310.02304.

Key transferable ideas:
- an improver scaffold can itself be an optimization target;
- useful search strategies can emerge in code, including beam search, genetic algorithms and simulated annealing.

Direct implication for v8:
- the proposal strategy is treated as inherited mutable state rather than permanently hand-authored weights.

## 6. Gödel Agent

Yin et al. "Gödel Agent: A Self-Referential Agent Framework for Recursively Self-Improvement." ACL 2025.

Key transferable ideas:
- self-reference requires access to logic that influences future behavior;
- runtime self-modification can improve both task behavior and the procedure used for later self-modification;
- highly permissive self-editing can temporarily decrease performance, so a strict greedy gate can block useful trajectories.

Direct implication for v8:
- v8 permits safe/viable capability valleys in the archive while keeping champion promotion strict;
- the evolver profile is explicitly self-referential but remains outside evaluator/budget authority.

## 7. AgentBreeder

Rosser & Foerster. "AgentBreeder: Mitigating the AI Safety Risks of Multi-Agent Scaffolds via Self-Improvement." NeurIPS 2025.

Key transferable ideas:
- capability-only evolutionary search can discover unsafe scaffolds;
- multi-objective/Pareto treatment of capability and safety is preferable;
- safety must be evaluated as a first-class dimension rather than assumed to track capability.

Direct implication for v8:
- archive admission has a frozen hard-safety/viability gate;
- champion promotion remains Pareto and no safety gate can be optimized away by the organism.

## 8. AlphaEvolve

Novikov et al. "AlphaEvolve: A coding agent for scientific and algorithmic discovery." arXiv:2506.13131.

Key transferable ideas:
- persistent program databases let evolutionary search reuse past discoveries;
- evaluator feedback and lineage storage are central;
- multiple objective metrics can guide program evolution.

Direct implication for v8:
- archive state is content-addressed and persistent;
- parent selection is derived from stored metrics, not human taste.

## 9. Quality-Diversity and novelty search

Pugh, Soros, Stanley. "Quality Diversity: A New Frontier for Evolutionary Computation." Frontiers in Robotics and AI, 2016.

Key transferable ideas:
- objective-only search can be deceptive;
- useful stepping stones may be behaviorally novel rather than immediately high-fitness;
- archives should preserve diverse high-quality niches.

Direct implication for v8:
- parent selection explicitly includes novelty;
- every viable node gets a non-zero chance rather than being permanently shadowed by the champion.

## 10. Recursive Self-Improvement survey

Chen, Wang, Qu. "Recursive Self-Improvement in AI: From Bounded Self-Refinement to Autonomous Research Loops." arXiv:2607.07663.

Key transferable ideas:
- distinguish behavior improvement, policy/training improvement, evaluator improvement and research-process improvement;
- stronger self-improvement results correlate with stronger verification signals;
- self-evaluation is a major failure point;
- evaluator evolution requires special caution.

Direct implication for v8:
- the external evaluator remains fixed for the main campaign;
- v8 evolves the organism and its improvement process, not the authority that judges success;
- evaluator co-evolution is deferred to a separately preregistered experiment.

## 11. Red Queen Gödel Machine

Iacob et al. "The Red Queen Gödel Machine: Co-Evolving Agents and Their Evaluators." arXiv:2606.26294.

Useful but deliberately deferred:
- evaluator evolution can escape fixed-benchmark ceilings;
- within-epoch evaluators should remain frozen;
- evaluator replacement must be anchored to held-out ground truth.

Why v8 does not adopt it yet:
- v7's unresolved question is already about stepping stones under a fixed evaluator;
- changing evaluator and archive dynamics simultaneously would confound causal interpretation;
- a Red-Queen-style v9 can be considered only after v8 establishes or rejects recursive archive dynamics under fixed authority.

## Design synthesis

v8 therefore changes exactly the search/evolution layer while preserving external authority:

- DGM: persistent open archive;
- GEA: performance–novelty group selection and experience sharing;
- Mendel: comparative cross-lineage evidence;
- MetaSkill/STOP/Gödel Agent: inherited mutable improvement process;
- AgentBreeder: hard safety separation;
- AlphaEvolve/QD: persistent database, objective evaluation, diversity pressure;
- RSI survey/Red Queen: keep the evaluator frozen for this epoch.

This is intentionally a stronger RSI test than v7 without turning the experiment into unconstrained autonomous production evolution.
