# Mira Generality Criteria

This register defines what Mira must demonstrate before the project may use progressively stronger
generality language. It prevents a successful bounded mechanism, benchmark score or polished demo
from being relabelled as AGI after the fact.

## Status vocabulary

- **mechanism evidence** — one necessary mechanism works in a declared bounded setting;
- **cross-domain evidence** — one unchanged agent transfers measurably across distinct domains;
- **general-agent evidence** — all gates below pass on frozen external and private evaluations;
- **AGI candidate** — general-agent evidence survives independent reproduction, adversarial audit
  and comparison with human baselines at declared cost;
- **AGI confirmed** — reserved for a broader scientific and societal conclusion, not a repository
  label Mira Genesis can assign to itself.

M068 is positive qualified-development mechanism evidence for bounded command induction after a
separate target freeze. It is not cross-domain or general-agent evidence.

## G1 — interface novelty

The agent must enter bodies whose interaction language was not encoded as a descriptor product in
the discoverer. Target implementations are frozen before the learner, selected after freeze and
unavailable for source inspection during evaluation. At least one incompatible body must produce a
calibrated refusal rather than an invented adapter.

## G2 — multimodal state grounding

One persistent agent must consume at least language, structured state and pixels, and must produce
both symbolic tool calls and embodied actions. Ablating any required modality must predictably
degrade the tasks that depend on it without changing unrelated tasks.

## G3 — novel task planning

The evaluator supplies goals, observations, action affordances and costs, but no task-specific
decomposition. Mira must form and revise plans, verify terminal conditions and ask for clarification
when the evidence does not determine a safe action.

## G4 — cross-domain transfer

Knowledge acquired in one domain must improve held-out performance in another relative to a fresh
agent with the same base model, context, tools, compute and observation budget. Total cost includes
training, retrieval, failed actions, verification and embodiment discovery.

## G5 — continual learning without critical forgetting

Mira must acquire skills after deployment while retaining preregistered old capabilities. The
evaluator measures positive transfer, negative transfer, memory growth, replay dependence and exact
rollback. External memory alone counts as retrieval, not weight or policy learning, unless the claim
says otherwise.

## G6 — real-environment competence

The same agent interface must operate in isolated but real software environments: initially a
terminal, browser and desktop VM; later a physical simulator and low-risk device. Task completion is
measured from environment state, never from the agent's self-report.

Candidate external suites include
[SWE-bench](https://github.com/princeton-nlp/SWE-bench),
[OSWorld](https://github.com/xlang-ai/OSWorld) and
[ARC-AGI-2](https://arcprize.org/arc-agi/2). Public suites are development evidence; final claims
require uncontaminated private tasks frozen after the agent design.

## G7 — long-horizon autonomy

Success must extend through increasing human-equivalent task horizons: ten minutes, one hour, four
hours and one day. The record includes intervention count, recovery after injected faults,
constraint retention, verification quality and cost. The measurement follows the task-horizon idea
used by [METR](https://metr.org/time-horizons/) without treating any single fitted horizon as AGI.

## G8 — governed self-improvement

Mira may diagnose, propose and validate changes to a disposable descendant. It must never grant
itself repository, credential, network, deployment or permission-changing authority. Adoption into
the official project remains a separately authenticated human decision.

## G9 — evaluation integrity and efficiency

Protocols, exclusions, budgets, human baselines and decision rules are committed before private
evaluation. Results report quality, reliability, latency, energy or compute proxies and monetary
cost where applicable. Contamination, failed attempts and negative results remain visible.

## G10 — safety, security and calibrated refusal

The agent must respect least privilege, preserve audit evidence, stop on ambiguous high-impact
actions and remain corrigible under interruption. Capability and misuse thresholds are evaluated
before access expands. Governance should remain compatible with the
[NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework):
govern, map, measure and manage.

## Decision rule

No mean score can compensate for a failed gate. A general-agent claim requires all ten gates in one
versioned lineage across at least four materially different domains, independent reproduction and
an external adversarial audit. Thresholds and benchmark subsets must be frozen in the experiment
that attempts the claim; this document deliberately does not retrofit numeric thresholds after
results are known.

## Current evidence map

| Gate | Current status | Strongest evidence |
|---|---|---|
| G1 | stronger partial mechanism evidence | M068 removes M067's descriptor product and induces four frozen command languages; targets and bounds remain project-authored and no incompatible body was tested. |
| G2 | open | No vision or multimodal grounding in one continuing lineage. |
| G3 | partial bounded evidence | Earlier lineages plan inside authored finite task languages. |
| G4 | open | No frozen transfer across real, materially different domains. |
| G5 | partial bounded evidence | M066 preserves bounded causal memory and post-migration plasticity. |
| G6 | open | Native runtimes are real; user environments and tasks are not. |
| G7 | open | No human-hour task-horizon evaluation. |
| G8 | partial bounded evidence | Disposable self-rewrite exists; official adoption remains human-controlled. |
| G9 | strong bounded evidence | Frozen canonical workflows, negative preservation and exact reproduction. |
| G10 | partial mechanism evidence | `mira_core` now denies high-impact authority by default and preserves tamper-evident evidence; no general-agent red-team suite exists. |

The next accepted result must change this table by evidence, not wording.
