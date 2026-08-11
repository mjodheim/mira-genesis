# HyperAgents and Mira Genesis — a comparison before M086

Written before the M086 protocol, from the paper (arXiv 2603.19461), the official repository
(`facebookresearch/hyperagents`) and the Darwin Gödel Machine line it extends. Its purpose is to
decide what Mira should take, what it must refuse, and why.

## What HyperAgents does

HyperAgents integrates a **task agent** (solves the target task) and a **meta agent** (modifies both
the task agent and itself) into **one editable program**. The recurrence is `A_next = M(A_prev, E)`
where `M` lives inside `A`, which is what removes the infinite regress of layered meta-architectures:
there is no meta-meta-agent, because the meta-level code is part of what the meta-level edits.

Its instantiation, DGM-H, generalises the Darwin Gödel Machine by removing DGM's hardcoded task/meta
alignment and making the agent-generation code editable. Reported results: coding pass@1 0.084 →
0.267 on 165 held-out tasks, paper review 0.0 → 0.710, robotics reward design 0.060 → 0.372, plus a
transfer probe on olympiad math grading. Ablations include a **fixed meta-agent** arm and a
**removed archive** arm.

Mechanically: a foundation model (Claude-4.5-Sonnet is the one named) is asked to propose a new
version of the whole codebase; variants are kept in an archive of stepping stones; parents are drawn
with probability `P_i ∝ S_i / (C_i + 1)`, balancing score against how many children a parent already
produced.

## Side by side

| Dimension | HyperAgents / DGM-H | Mira Genesis |
|---|---|---|
| Task agent | `task_agent.py`, freely rewritten | versioned software body (M047) or organism policy (M084) |
| Improvement mechanism | `meta_agent.py`, freely rewritten | `diagnose_limiting_module` + `_candidate_sources`, **frozen by us** |
| Meta mechanism editable | **yes** — the central contribution | **no** — this is the M086 target |
| Archive of descendants | yes, stepping stones | no; one canonical lineage, disposable descendants |
| Parent selection | stochastic, `S_i / (C_i + 1)` | none; single lineage, deterministic |
| Empirical validation | held-out task score per domain | independent evaluator, hidden cases, precommitted threshold |
| Persistence of meta gains | across domains and runs | not yet demonstrated at the meta level |
| Transfer of improvement mechanisms | claimed across four domains | M085's open question, externally gated |
| Ownership of transformations | the composed system, FM included | Track A demands lineage ownership |
| Role of the foundation model | **writes the modification** | absent from Track A entirely |
| Evaluator boundary | outer loop immutable, acknowledged as a limit | evaluator strictly outside the mutable body |
| Rollback | not documented | exact, digest-verified, with forced-fault tests |
| Causal provenance | archive lineage only | hash-chained journal binding evidence → adoption |
| Lineage continuity | archive ancestry | one identity across substrates and serializations (M084) |
| Trans-substrate migration | not attempted | CPython → Node → WebAssembly (M048, M064–M066) |
| Safety / permissions | README warns it executes untrusted model-generated code | no repository, credential, network or deployment authority |

## 1. What HyperAgents demonstrates better than Mira

**The meta mechanism is genuinely mutable, and Mira's is not.** This is the honest headline. Every
Mira result to date — including M084 — improves a *body* or a *policy* through a procedure that we
wrote and froze. HyperAgents edits that procedure. On the specific question "can the improver be
improved", they are ahead and we are at zero.

**Compounding across domains.** Their meta-level gains persist across runs and transfer to domains
the mechanism was not tuned on. Mira has never measured meta-level persistence at all.

**Scale and breadth.** Four domains including robotics reward design; Mira's environments are all
project-authored.

## 2. What Mira demonstrates that HyperAgents does not attempt

**Ownership.** HyperAgents' modifications are written by a frontier model. Under Mira's attribution
rule that competence belongs to the composed system. HyperAgents is not making an endogeneity claim,
so this is not a criticism of their work — it is a statement that their result cannot be imported
into Track A.

**Exact rollback and a causal journal.** Mira restores byte-identical state after forced corruption
and can bind an adoption to the evidence that caused it. Neither is documented in HyperAgents.

**Trans-substrate continuity.** Whole-body migration to a different runtime, and a lineage keeping
one identity across three real substrates and four processes (M084).

**Calibrated refusal.** M078 refuses under-determined bodies; M079 asks rather than committing.
HyperAgents optimises a score, and the authors name Goodhart's law as an acknowledged failure mode.

**Fail-closed external gating.** M075 and M085 refuse to run until a non-project maintainer signs an
envelope. HyperAgents evaluates on benchmarks it holds.

## 3. Ideas worth taking

- **Meta-level mutability as the object of study.** The core idea, and the reason M086 exists.
- **The single-program trick.** Putting the improvement mechanism inside the same editable artifact
  as the body avoids a meta-meta regress. Mira can adopt this structurally without adopting the FM.
- **The `fixed_meta` ablation.** Their own control is the right primary control for us, and it being
  standard in this literature is a point in its favour.
- **Naming the immutable outer loop.** They state plainly that the evaluation protocol stays fixed.
  Mira should state it at least as plainly, and enforce it.

## 4. What would violate Genesis rules

- **Letting a foundation model write the improvement mechanism** and calling the result endogenous.
  Under Track A the FM may not invent the transformation, choose its arguments, or select which
  variant is adopted. A model-written meta-agent is Track B by construction.
- **"Everything editable", including the evaluator.** HyperAgents keeps its outer loop immutable and
  says so; an incautious reading of "self-referential" would let the mechanism edit the test that
  judges it. Mira must forbid this explicitly, not merely omit it.
- **Score-maximising selection without a hidden validation set.** Goodhart is a reported failure
  mode there; Mira's answer is evaluator-owned success on cases the generator cannot reach, and M069
  stands as the recorded precedent for what happens when that boundary leaks.
- **An archive plus a mutable meta mechanism plus transfer, all at once.** Their design entangles
  these; a positive Mira result would be causally unattributable if we introduced them together.

## 5. Endogenous improvement versus a model-written modification

The distinction Mira must hold is not about capability but about **where the constructive step
happens**.

When an FM is asked for a new version of the codebase, the search over possible improvements happens
inside the model's weights, informed by its training on millions of programs. The lineage supplies a
prompt and an acceptance test. Calling the resulting mechanism "the lineage's own" would be the same
error as calling M071's benchmark reward Mira's competence — and the repository already refuses that
in `docs/EPISTEMIC_TRACKS.md`.

An endogenous meta-improvement, in the sense M086 needs, requires that:

1. the primitives available for modifying the mechanism are declared and bounded;
2. the *particular* modification is constructed from those primitives and from evidence the lineage
   itself produced, not retrieved from a model or from a hidden list of finished answers;
3. the choice among candidate modifications is made by experiment against an independent evaluator;
4. the adopted modification is serialized, journaled against its causing evidence, and executed
   afterwards by the lineage itself.

This is a much weaker claim than HyperAgents makes, and it is bounded in a way theirs is not. It is
also the only version of the claim Mira is entitled to.

## What this implies for M086

Take the question, refuse the method. Make Mira's own frozen mechanism mutable, keep the evaluator
outside it, keep the foundation model out of Track A entirely, and postpone the archive.

One further consequence is specific to Mira and does not arise for HyperAgents: because our
mechanism is small and legible rather than a model-written program, we can **enumerate its
constructive image** and prove that a required transformation lies outside it. HyperAgents can only
observe that a fixed-meta arm scored lower. We can show a capability gap rather than a score gap —
which is exactly what M084's efficiency-only result says the next milestone must do.
