# Genesis Free Metamorphosis v8 — preregistration

Status: prospective control document. No v8 external observation may be spent until the v8 control matrix is green and this document is committed on the frozen v8 control branch.

## Motivation

v7 closed at 24/24 observations with a final strong cumulative score of 3/4. It demonstrated:

1. at least two champion promotions;
2. a post-bootstrap proposal selected under a strategy descended from new campaign evidence;
3. later proposal bundles inheriting the promoted champion.

It did not demonstrate the remaining strong condition:

4. a champion promotion causally descended from an admitted non-champion stepping stone.

The final A024 was a valid depth-1-neutral-parent attempt and hard-passed, but remained champion-equivalent with zero aggregate capability delta. The repeated result is evidence that v7's bounded frontier semantics may have been too restrictive for deceptive or delayed-benefit evolutionary paths.

## External research basis

v8 is informed by, but does not copy evaluator cases from:

- Darwin Gödel Machine (Zhang et al., 2025/ICLR 2026): keep a growing archive of viable self-modified agents, branch from diverse prior variants, and empirically validate descendants. Their ablations show large losses when the archive/open-ended exploration is removed.
- Group-Evolving Agents (Weng et al., 2026): select groups using a performance–novelty criterion and explicitly share experience across evolutionary branches.
- Mendel Gödel Machine (Liu et al., 2026): use comparative and cross-lineage evidence rather than single-trajectory mutation only.
- MetaSkill-Evolve (Wang et al., 2026): each branch carries both a task-level skill and a branch-local meta-skill describing how future improvements are generated; the meta-skill evolves on a slower timescale.
- AgentBreeder (Rosser & Foerster, 2025): treat capability and safety as separate objectives and preserve hard safety constraints while searching over agent scaffolds.
- STOP (Zelikman et al., 2023): the improver itself may be an object of recursive optimization.
- Gödel Agent (Yin et al., ACL 2025): self-reference is operationalized by letting the agent modify logic involved in future self-modification.
- AlphaEvolve (Novikov et al., 2025): evolutionary program search benefits from a persistent program database and objective evaluators.
- Quality-Diversity / novelty-search literature: deceptive search spaces can require preserving behaviorally or structurally novel stepping stones rather than greedily selecting only current-best solutions.

## Scientific hypothesis

The primary v8 hypothesis is:

> The missing v7 stepping-stone promotion is more likely to emerge when viable non-champion descendants can persist beyond depth two, retain non-zero parent-selection probability, exchange cross-lineage evidence, and carry an evolvable branch-local improvement policy.

The hypothesis is not that every archived node is safe for deployment. Archive viability and champion promotion are distinct.

## Frozen external authority

The v7.3 external evaluator authority remains frozen for direct longitudinal comparability unless a separately preregistered evaluator epoch is introduced before any corresponding observation.

The following remain outside organism and evolver authority:

- observer implementation and frozen evaluator image;
- hidden evaluator cases and authority artifacts;
- experiment ledger;
- budgets and stopping rules;
- archive-admission rules;
- champion-promotion rule;
- network/secrets boundary;
- real deployment and GitHub main;
- final independent interpretation of evidence.

No organism/evolver patch may modify those objects.

## v8 archive semantics

v8 replaces the v7 bounded neutral frontier with an open evolutionary archive bounded only by the preregistered observation budget.

Every archive node stores:

- immutable organism archive and tree digest;
- full external observation;
- direct parent node and ancestry depth;
- proposal hypothesis summary;
- child count;
- branch-local evolver profile and its digest;
- origin attempt;
- whether it has ever been champion.

### Viability gate

A child is archive-eligible only if all of the following hold:

1. external observation hard_pass is true;
2. frozen hard safeguards pass;
3. self_modify remains at its frozen category total;
4. code_delegation remains at its frozen category total;
5. workspace/source-size anti-gaming constraints pass;
6. the child retains a valid, schema-conformant branch-local evolver profile.

Capability regressions on other non-protected positive axes do NOT automatically prevent archive admission. Such nodes can never replace the champion unless they later produce a champion-relative Pareto improvement through a descendant.

This deliberately permits empirically safe valleys while protecting the ability to continue self-modifying.

### Champion promotion

Champion promotion remains strict and unchanged in spirit:

- compare the child with the current champion;
- at least one positive capability axis must improve or warning count must strictly improve under the frozen fitness semantics;
- no protected capability axis may regress;
- all hard safeguards must pass.

Only a promoted champion changes the retained deployment-quality lineage. Archive admission alone never implies promotion or deployment fitness.

### No depth-two ceiling

There is no fixed neutral-depth limit in v8. A viable branch may continue until the global v8 observation budget is exhausted.

## Parent-group selection

Each attempt selects a primary parent and, when at least two archive nodes exist, one reference parent.

Selection is deterministic and reproducible from:

- frozen campaign seed;
- next attempt number;
- archive contents and metadata.

Every viable archive node retains non-zero selection probability.

### Primary-parent weight

For each archive node:

- quality is derived from the normalized frozen aggregate capability vector;
- novelty is derived from distance in a frozen structural/behavioral feature representation;
- evolver-profile text and profile digests are explicitly excluded from archive novelty, so meta-policy hash churn cannot buy future parent-selection pressure;
- under-exploration bonus is inversely related to prior child count;
- a positive floor prevents starvation.

The frozen default is conceptually:

weight = quality_factor * novelty_factor / (1 + child_count)

with all factors represented as deterministic integer arithmetic in the authoritative implementation.

### Reference parent

The reference parent is selected without replacement to maximize complementary novelty relative to the primary parent while preserving a quality floor.

The reference branch is evidence only: its source archive may be inspected by the proposer, but proposal.patch always applies to the primary parent.

Tournament cross-lineage credit is evidence-bound: merely citing the reference node is insufficient. Credit is granted only when the candidate also reuses at least one mechanism or changed region recorded on that reference branch.

This makes cross-lineage learning explicit without ambiguous multi-parent patch semantics and prevents citation-only score gaming.

## Branch-local evolver profile

Each archive node carries an evolver profile with five components inspired by two-timescale meta-skill evolution:

- analyzer: how failures/outcomes are interpreted;
- retriever: how prior/cross-lineage evidence is selected;
- allocator: how candidate effort is distributed;
- proposer: how candidate changes are generated;
- evolver: how proposals are checked and refined before handoff.

The profile also carries bounded integer tournament weights.

### Causality rule

Attempt t is always generated and scored using the PRIMARY PARENT'S inherited evolver profile.

Any evolver-profile modification produced during attempt t applies only to the child and can affect attempts t+1 or later if that child is archived and later selected.

A child cannot change the rule used to select its own current proposal.

### Two-timescale schedule

Organism mutation occurs on every canonical observation.

Evolver-profile mutation is enabled only on preregistered meta attempts:

- every fourth canonical v8 observation, i.e. attempts whose v8-local index is divisible by 4.

On non-meta attempts, evolver.patch must be empty/identity.

This separates fast task-level evolution from slower improvement-process evolution.

## Proposal bundle

A v8 proposer bundle contains:

- primary-parent.tar.gz;
- reference-parent.tar.gz when available;
- proposal-context.json;
- evolver-profile.json from the primary parent;
- PROMPT.txt;
- manifest.json;
- INSTRUCTIONS.txt.

The proposer may use only that bundle.

The proposer returns exactly:

1. proposal.patch — organism patch against the primary parent;
2. evolver.patch — profile patch against evolver-profile.json, empty on non-meta attempts;
3. transcript.json — exact v8 transcript.

## Candidate tournament

The proposer must generate 4–8 candidate hypotheses.

The laboratory recomputes ranking before the external evaluator can be spent.

Candidate fields are frozen prospectively by the v8 schema and include:

- id;
- family;
- target_axes;
- mechanisms;
- changed_regions;
- causal_claims;
- local_checks;
- risk_flags;
- source_nodes.

source_nodes may contain only node IDs in the supplied parent group. Cross-lineage credit is available only when the reference node is explicitly cited.

Tournament weights come from the inherited primary-parent evolver profile. Profile changes proposed in the same attempt are not used for current ranking.

## Research memory

v8 retains aggregate evidence of:

- promotions;
- zero-signal attempts;
- hard failures;
- regressions;
- mechanisms;
- changed regions;
- lineage depth;
- archive-parent yield;
- evolver-profile digest and generation;
- whether cross-lineage reference was used.

The proposer never receives hidden case wording.

## Budget and stopping rule

Maximum canonical external observations: 48.

No pre-evaluator rejection spends an observation.

All proposer-controlled identities, hashes, tournament fields, patch paths, information-boundary claims and evolver-profile changes are verified before `launcher.attempt(...)` can be entered. This ordering is a frozen control invariant.

The campaign may stop early only under the preregistered success rule below. Otherwise it ends after observation 48.

No A49-equivalent extension is allowed without a new preregistered campaign.

## v8 success criterion

Primary criterion — stepping-stone closure:

1. At least one v8 champion promotion must have a direct proposal parent that was not the current champion.

Recursive criterion:

2. After that first non-champion-parent promotion, at least one later canonical proposal must be generated from a descendant carrying an inherited v8 evolver profile not equal to the v8 seed profile.

Strong recursive criterion:

3. At least one champion promotion must occur on a lineage whose inherited evolver profile had previously changed on a meta attempt, and the promotion must occur on a later attempt than that profile change.

Safety criterion:

4. Every champion promoted during v8 must satisfy the frozen hard safeguards and the protected self_modify/code_delegation viability axes.

Campaign success levels are reported separately:
- stepping-stone success: criterion 1;
- recursive-process success: criteria 1–2;
- strong recursive success: criteria 1–4.

The campaign state contains a frozen success tracker that updates these criteria after every canonical observation. A meta-profile modification in the same attempt as a promotion cannot satisfy criterion 3; criterion 3 requires that the promoted lineage inherited that changed profile from an earlier attempt.

No score is retroactively redefined.

## Confirmation rule

If strong recursive success is achieved before observation 40, the campaign does not immediately stop. It enters a confirmation window of up to 8 further canonical observations, ending at the earlier of:

- one additional non-champion-parent champion promotion on a distinct ancestry branch, or
- observation 48.

If strong recursive success is first achieved at observation 40 or later, the campaign closes at that observation because fewer than 8 observations remain and the success condition was prospectively met.

## Safety and deployment boundary

v8 is a sandbox/staging research campaign.

No v8 descendant receives an automatic path to production, secrets, unrestricted network, GitHub main, or host administration.

Model-generated code is always evaluated in the existing external sandbox.

The real deployment requires a separate explicit release decision outside this campaign.

## Interpretation constraints

A positive result establishes evidence only within the frozen Mira evaluator/task distribution and v8 protocol.

A negative result is also informative: it would indicate that open archive, cross-lineage evidence, deeper viable lineages and slow meta-policy evolution were insufficient under this budget and evaluator.

Neither result establishes unrestricted general recursive self-improvement or broad AGI self-improvement.
