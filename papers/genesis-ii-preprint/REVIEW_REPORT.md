# Genesis II — manuscript review report

Date: 2026-08-26  
Scope reviewed: `papers/genesis-ii-preprint/`, manuscript M107–M112

## Status

The manuscript received a separate AI-assisted self-review after the long-form rewrite. This is **not independent peer review** and must never be described as such. The purpose of this file is to make the review work visible and to record the issues that were actively searched for before author handoff.

Current reviewed build: **22 pages**, including references and appendices.

## Pass 1 — scientific consistency against frozen artifacts

The manuscript was checked against the preserved result summaries and repository state for M107–M112, plus M103/M105 where the paper discusses fail-closed instrumentation.

Verified claim anchors:

| claim | frozen source checked |
|---|---|
| M107 complete image 4/16 → 16/16; P1–P16 | `experiments/M107/RESULT_SUMMARY.md`, D076 |
| M108 state-held attribution rule; P1–P16; 14 isolated processes | `experiments/M108/RESULT_SUMMARY.md`, D077 |
| M109 two successive machinery generations; `ReachImprove` 6 ⊂ 20 ⊂ 243; P1–P18 | `experiments/M109/RESULT_SUMMARY.md`, D078 |
| M110 row 7/3 positive transfer, row 5 harm 6/6 → 0/6, strict capacity chain, P1–P24, 186 processes | `experiments/M110/RESULT_SUMMARY.md` and `RESULT.json`, D079 |
| M111 identical-row ambiguity, one-probe budget, 18→127 policy space, 0→25 separating programs, P1–P24, 127 processes | `experiments/M111/RESULT_SUMMARY.md` and `RESULT.json`, D080 |
| M112 one generator invocation, 100 records → 20 worlds, 5 ambiguous, 6 witness, diagnosis 24/24, transfer 22/24, P5 17→18 closure discrepancy | `experiments/M112/RESULT_SUMMARY.md`, D081 |
| M103 first checker left P15 uncomputed and became permanently negative | `experiments/M103/README.md`, D072 |
| M105 first checker left P1–P16 uncomputed and became permanently negative | `experiments/M105/README.md`, D074 |

No M113 development result is used as evidence. M113 appears only as an explicitly result-free future boundary.

## Pass 2 — adversarial reviewer pass

The manuscript was reread as if the reviewer were trying to reject the strongest interpretation. The main objections and resulting changes were:

### 1. “Transfer only within the producer census” sounded universal

**Concern:** one designed consumer family cannot establish a universal transfer law.

**Resolution:** the abstract and body now say that, **in the tested carrier**, transfer is positive on in-census rows and harmful on one realizable out-of-census row. The paper keeps “census-conditional” as the bounded mechanistic interpretation, not a population theorem.

### 2. “Recursive depth three” could be read as open-ended recursive self-improvement

**Concern:** the phrase is nonstandard and easy to hype.

**Resolution:** the paper defines “machinery generation” operationally, uses “third machinery generation” in the abstract and submission claim, and repeatedly states that no open-endedness or acceleration is established.

### 3. M112 blindness could be mistaken for data independence

**Concern:** container isolation cannot prove that a public model never saw public project material during training.

**Resolution:** the manuscript explicitly distinguishes execution-time **context blindness** from training-data independence, human independence, and third-party custody. All three stronger claims are denied.

### 4. “M112 reproduced transfer” could hide the inherited 22/24 negative verdict

**Concern:** reporting the outcome table without the checker verdict would weaken the precommitment.

**Resolution:** the paper separates **scientific outcome reproduction** from **formal inherited checker verdict** and keeps transfer negative at 22/24. P1 and P5 are both described; P5 is treated as a real blind-world measurement.

### 5. M110 is a designed stress test and could be accused of cherry-picking

**Concern:** the consumer family was chosen to realize row 5.

**Resolution:** this is stated in the main text, limitations, evidence ledger, and submission metadata. The claim is a causal stress-test result, not neutral target-distribution performance.

### 6. Small populations could invite inappropriate statistical claims

**Concern:** 3, 5, 6, or 20 worlds are too small for broad frequency estimates.

**Resolution:** a dedicated statistical-validity section now states that M107–M111 are primarily structural/deterministic tests, not population estimates. M112’s 25% versus ~6% ambiguity rates are described as qualitative/descriptive, not inferential.

### 7. Project-authored checkers are not independent verification

**Concern:** runner and checker may share project assumptions.

**Resolution:** internal-validity and reproducibility sections explicitly state this. M103/M105 are used as evidence that the fail-closed instrument rule can invalidate a run, not as proof of checker independence.

### 8. Related work was too concentrated on recent self-improving agents

**Concern:** the first short manuscript under-positioned the work relative to meta-learning and learned update procedures.

**Resolution:** a dedicated meta-learning subsection and citations to MAML and learned optimizers were added, alongside negative transfer, active learning/selective prediction, program synthesis, persistent skills, and current self-improving-agent systems.

## Pass 3 — literature verification

Recent references that are easy to mistype were checked against current public paper records on 2026-08-26:

- `arXiv:2603.19461` — *Hyperagents*;
- `arXiv:2607.05297` — *MetaSkill-Evolve: Recursive Self-Improvement of LLM Agents via Two-Timescale Meta-Skill Evolution*;
- `arXiv:2607.13104` — *Self-Improvements in Modern Agentic Systems: A Survey*;
- `arXiv:2608.15165` — *SkillCommit: Evolving Agent Skills through Behaviorally Validated Scope Expansion*;
- `arXiv:2505.22954` — *Darwin Gödel Machine: Open-Ended Evolution of Self-Improving Agents*;
- `arXiv:2504.15228` — *A Self-Improving Coding Agent*;
- `arXiv:2410.04444` — *Gödel Agent: A Self-Referential Agent Framework for Recursive Self-Improvement*;
- `arXiv:2506.10943` — *Self-Adapting Language Models*;
- Finn, Abbeel & Levine (ICML/PMLR 2017) — *Model-Agnostic Meta-Learning for Fast Adaptation of Deep Networks*;
- `arXiv:1606.04474` — *Learning to Learn by Gradient Descent by Gradient Descent*.

The bibliography remains a normal scholarly bibliography; this verification is not a literature-review claim that the related-work search is exhaustive.

## Pass 4 — technical manuscript checks

Completed:

- LaTeX compilation from source;
- BibTeX resolution and two final LaTeX passes;
- no unresolved citations or cross-references;
- `chktex` and `lacheck` pass reviewed (remaining spacing warnings are macro/typography false positives, not broken syntax);
- PDF rendered to **22 page images** and visually inspected in contact sheets;
- figures checked for clipping and legibility;
- tables checked for page overflow;
- high-risk language search for `AGI`, `independent`, `open-ended`, `recursive`, `training-data`, `human`, and `blind` to ensure boundaries are stated where needed;
- source/PDF preflight repeated after final edits.

## Residual issues that require a real external reviewer

These cannot be closed by self-review:

1. independent reimplementation of the checkers/mechanisms;
2. assessment of whether the novelty is sufficient for a particular venue;
3. evaluation by a domain expert with no involvement in the project;
4. a human-maintained sealed evaluation bank;
5. external adversarial audit.

The manuscript is ready for preprint submission, but none of the above should be implied by the phrase “reviewed manuscript.”
