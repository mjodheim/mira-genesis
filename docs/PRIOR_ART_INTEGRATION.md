# Prior art integration

**Status: analysis only. Nothing here is implemented, and nothing here supports a Mira
gate.**

## The rule this document exists to enforce

> **A borrowed mechanism is not a transferred result.**

None of the works below proves anything about Mira Genesis. Their published numbers belong
to their own systems, benchmarks and domains. What can travel is a *mechanism*, and only
after it has been reimplemented here, tied to an explicit hypothesis, tested in isolation,
ablated, and reported with its transposition losses named.

Every entry records what is **not** taken, because that is usually the more important half.

## A constraint that shapes every entry

Mira's kernel has **no dependency on any external model**. `pyproject.toml` declares a
single runtime dependency, `numpy`. The only files mentioning language models are
`check_attribution_policy.py` and `check_repository_integrity.py` — guards *against* such a
dependency.

**Four** of the six works below place a large language model at the point where the
transformation is invented — DGM, Voyager, AlphaEvolve and Gödel Agent. POET and
AutoML-Zero are evolutionary and use none. An earlier draft said five, which was wrong.

That point is precisely what Gate 2 reserves for the organism:

> Every operation used to inspect, transform, build or test a candidate body is present in
> the organism's serialised tool registry. External infrastructure may execute a tool, but
> may not invent its transformation or choose its arguments on the organism's behalf.

So for every such work, the generative core is **not transposable**. What is transposable is
the surrounding machinery: archives, registries, evaluator cascades, curricula.

An external model may be a development tool, a named baseline, or a proposal generator in an
explicitly declared experiment. It may never be counted as a tool the lineage owns.

---

## 1. Darwin Gödel Machine

**Reference.** Zhang, Hu, Lu, Lange, Clune. *Darwin Gödel Machine: Open-Ended Evolution of
Self-Improving Agents.* [arXiv:2505.22954](https://arxiv.org/abs/2505.22954).
**Licence.** Apache-2.0 — [jennyzzt/dgm](https://github.com/jennyzzt/dgm). Commercially
usable; no code is copied here regardless.

**Mechanism taken.** The immutable archive of variants with a parent–child tree, retention
of rejected branches, the ability to restart from any ancestor, and the separation of
generation, evaluation and adoption.

**Not taken.** The self-modifying agent whose transformations are invented by a foundation
model, and empirical validation on coding benchmarks as the adoption criterion. DGM's
published improvement — 20.0% to 50.0% on SWE-bench — belongs to that system and says
nothing about any Mira gate.

**Difference from the original.** DGM's archive stores agents whose behaviour is only
sampled. Mira's would store bodies whose equivalence is *decidable*, so two bodies can be
compared exactly and a separating word produced. That is weaker than it may sound: it does
**not** make every rejected branch "proved unreachable". Unreachability is provable only
within a bounded space, against a fixed vocabulary and budget, as M035's control arm was —
0/12 by proved impossibility. A branch rejected during search is merely a branch that did
not work, and the archive must not imply otherwise.

**Gates concerned.** 6 (adoption and rollback), 9 (repeated cycles).

**Methodological risk.** An archive invites the belief that keeping more variants is itself
progress. M034 already measured the opposite shape: a learned tool that adds nothing to the
reachable set is retained just as faithfully as one that does.

**Planned ablation.** Run with the archive truncated to the current generation. If results
are unchanged, the archive is bookkeeping rather than mechanism.

**Status.** Specified.

---

## 2. Voyager

**Reference.** Wang, Xie, Jiang, Mandlekar, Xiao, Zhu, Fan, Anandkumar. *Voyager: An
Open-Ended Embodied Agent with Large Language Models.*
[arXiv:2305.16291](https://arxiv.org/abs/2305.16291).
**Licence.** MIT — [MineDojo/Voyager](https://github.com/MineDojo/Voyager).

**Mechanism taken.** The skill library as an *executable, persistent, retrievable* store:
skills composed from earlier skills, retrieved by context, reused on new tasks, and
transported.

**Not taken.** The automatic curriculum driven by a model, the iterative prompting loop, and
self-verification by the same model that wrote the code. Mira already separates proposal
from judgement, and collapsing them would undo that.

**Difference from the original.** Voyager's skills are natural-language-retrieved code
snippets. Mira's would be registry entries with declared preconditions, postconditions and
substrate requirements, retrieved by exact match rather than embedding similarity.

**Gates concerned.** 2 (internal tool ownership), 7 (tool transport).

**Methodological risk — the largest in this document.** A tool written by a development
assistant and committed to the repository must never be counted as a tool *learned by the
lineage*. Provenance is recorded on **three independent axes** rather than one exclusive
label, because origin, construction kind and introduction phase are different questions —
see ADR 0003.

**Planned ablation.** Remove the registry and re-run. M034 predicts no change in reachable
capability under the current per-operation cost rule, which would make a Voyager-style
registry decorative here until tool cost is unit.

**Status.** Specified.

---

## 3. POET

**Reference.** Wang, Lehman, Clune, Stanley. *Paired Open-Ended Trailblazer (POET).*
[arXiv:1901.01753](https://arxiv.org/abs/1901.01753). Enhanced POET: Wang et al., ICML 2020.

**Mechanism taken.** Paired generation of environments and solutions, transfer of stepping
stones between niches, and maintaining several niches at once.

**Not taken, and not implementable yet.** M035 has a single task family. A curriculum needs
several, and inventing them now would mean choosing task families without a frozen
generator — the contamination this repository has already paid for twice.

**Difference from the original.** POET's environments are continuous and its transfers are
evaluated by return. Mira's would be finite task families with decidable equivalence, so a
transfer can be proved useful rather than observed to help.

**Gates concerned.** 9 (new task families per cycle).

**Methodological risk.** A curriculum that adapts after observation can be tuned to favour a
lineage. Development may evolve it; a canonical run must freeze generators, reveal rules,
thresholds and permitted transfers before the run.

**Status.** Idea. Deferred until more than one task family exists.

---

## 4. AlphaEvolve

**Reference.** Google DeepMind. *AlphaEvolve: A coding agent for scientific and algorithmic
discovery.* [arXiv:2506.13131](https://arxiv.org/abs/2506.13131).
**Licence.** Not released. Third-party reimplementations exist and are not used here.

**Mechanism taken.** The **evaluation cascade**: cheap filters first, full evaluation only
for survivors, progressively harder stages.

Mira already does a two-stage version of this — `SelfExtendingOrganism.solve` filters on
seven short words before the full fingerprint, then confirms by W-method. The contribution
is to make the stages *separate, versioned, independently replaceable* rather than inlined.

**Not taken.** Gemini as the generator of candidate programs.

**Difference from the original.** AlphaEvolve's evaluators score; Mira's must produce a
verdict with a witness. A separating word is a proof; a score is not.

**Gates concerned.** 4 (isolated validation), 5 (held-out improvement).

**Methodological risk.** An aggregate score can hide a critical failure. No stage may be
summarised away: M017 §3 already makes admission conditions absolute rather than weighted.

**Planned scope, aligned on what M038 actually does.** M038 uses M017's kernel, requires an
adoption, and forces a rollback attempt, so a rollback verifier now has a concrete object —
an earlier draft said it had none, which was true of M035 and not of M038.

```
CertificateVerifier
CandidateIsolationEvaluator
ExactBehaviourEvaluator
RegressionEvaluator
CostRecorder
AdoptionGate
RollbackVerifier
```

`MigrationEvaluator` and `PlasticityEvaluator` are still **not** created: M038 neither
migrates nor runs a second cycle, and empty shells would later be mistaken for capability.

**Status.** Specified, reduced.

---

## 5. AutoML-Zero

**Reference.** Real, Liang, So, Le. *AutoML-Zero: Evolving Machine Learning Algorithms From
Scratch.* [arXiv:2003.03384](https://arxiv.org/abs/2003.03384).
**Licence.** Apache-2.0 — [google-research/automl_zero](https://github.com/google-research/google-research/tree/master/automl_zero).

**Mechanism of interest.** Search from elementary primitives, with no hand-written
higher-level components — the same objection D009 raised against Mira's closed catalogue.

**Not taken now, and this is a deliberate refusal.** Replacing DFAs with a general
instruction representation would forfeit decidable equivalence, which is Mira's only
distinctive asset. It is what allows the statement *"the control fails by proved
impossibility"* rather than *"the control did not find it"*. Every result in this session
that survived review rests on that distinction.

**Difference from the original.** AutoML-Zero evaluates on held-out accuracy over sampled
data. Mira evaluates by exact equivalence. Those are not the same kind of claim.

**Gates concerned.** 2, 3 — eventually.

**Status.** Idea. Any future intermediate representation must stay bounded, typed,
serialisable, sandboxable, versioned and small enough for exact verification, with DFAs as
its first body type.

---

## 6. Gödel Agent

**Reference.** Yin, Wang, Pan, Wan, Wang. *Gödel Agent: A Self-Referential Agent Framework
for Recursive Self-Improvement.* [arXiv:2410.04444](https://arxiv.org/abs/2410.04444).
**Licence.** [Arvid-pku/Godel_Agent](https://github.com/Arvid-pku/Godel_Agent) — **not verified from a primary source**. No code is reused here; verify before any reuse.

**Mechanism of interest.** Analyse failure traces, form a hypothesis about a limitation,
propose a revision, validate it, persist the new strategy.

**Tested here in a related but not identical form.** M036 tested the same broad
diagnosis-then-growth shape with a **greedy** lower-bound search. The development result was
negative — 2/8 against 6/12 for a population with no explicit diagnosis — but the trigger
was algorithmically incomplete, missing 3 of 6 cases that genuinely required growth, and the
single-organism search also explored far less volume than the M035 population.

**M038 does not inherit a negative verdict for its exact certificate.** It tests a repaired
trigger inside a different, journalled two-speed architecture. The exact search matched the
true minimal state count on 12 of 12 calibration rows where the greedy understated on 6 —
see `results/M038_TRIGGER_CALIBRATION.md`.

An earlier draft of this document said "the certificate is stronger, and it still did not
help as a trigger". That was wrong: the *greedy* certificate did not help. The exact one has
never been measured as a trigger.

**What M036 does still establish**, and these are unaffected:

- the population explored far more trajectories than a single organism;
- growth must be composable within the search, not applied as a preparatory phase;
- a size bound says *that* a body must grow, never *where* the missing distinction lives;
- the greedy bound was too incomplete to gate on.

**Difference from the original.** Gödel Agent's diagnosis and revision are both produced by
a model guided by high-level objectives. Mira's diagnosis is a verifiable certificate.

**What survives for M038.** The *shape* — persistent limitation, diagnosis, proposal,
isolated validation, adoption or rollback — as the slow path, with the diagnosis restricted
to `proved_structural_incapacity`. Not as an always-on loop: that is excluded on scope and
attributability grounds for M038, **not** as an experimental consequence of the exact
certificate, which remains untested in that role.

**Status.** Related form tested, negative result recorded in
`results/M036_GROWING_ORGANISM.md`. The exact certificate is untested as a trigger.

---

## Integration order

1. causal journal (the single source of authority);
2. lineage archive **as a projection of the journal**, never a second state;
3. tool provenance;
4. reduced evaluator cascade;
5. one integrated DFA cycle;
6. *only then* a curriculum, and later an intermediate representation.

## What this document does not claim

- that any Mira gate is closer to passing;
- that any external result transfers;
- that a mechanism is validated because its original publication reported success;
- that these six works are combinable into a system that already works.
