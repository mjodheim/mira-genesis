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

M069 is post-hoc disqualified by its evaluator-isolation falsifier. Its exact run remains a
diagnostic record, but hidden evidence was reachable through the admitted candidate-execution path,
so it advances no gate. See D037.

M070 is negative external development evidence. It preserved blind independent-task selection,
container isolation and evaluator-owned success, but scored 0/2 after a model-transport failure.
It does not advance a competence gate.

M071 is positive public external development evidence for the named composed system: one of two
fresh blind tasks earned reward `1.0`, both `nop` floors earned `0.0`, and no retry or replacement
occurred. One accepted task does not demonstrate cross-domain transfer, isolate Mira governance or
change a generality-gate status.

M072 is positive bounded causal-governance mechanism evidence. Matched non-executing ablations show
that authority admission and tamper-evident audit chaining cause their respective authored
containment and integrity invariants. It is not an independent red-team or external competence
result.

M073 is positive bounded skill-appropriation mechanism evidence. One capsule induced from four
external demonstrations remains useful on twelve alpha-renamed holdouts after the teacher is
removed. The family and evaluator are authored and structurally homogeneous, so this is not
cross-domain, general-programming or Gate 2 evidence.

M074 currently contributes no gate evidence. Its real-container, label-blind development dry run
qualifies a refusal-calibration instrument, not an agent. H20 remains untested until an exact model,
prompt, threshold and single-attempt protocol are frozen before execution.

## Model-mediated attribution rule

M070–M071 use a named external model to propose actions. Task reward therefore measures the composed
model, policy wrapper, body and evaluator. It is not evidence that Mira owns the transformation and
cannot satisfy Genesis Gate 2 or Gate 3. Governance claims require direct containment/audit
evidence or a baseline that isolates the governance layer; M072 performs such an ablation without
calling a model. M073 may attribute only the induced serialized capsule and its later model-free
execution to the lineage; its teacher outputs and repair objective remain external. See
[`docs/EPISTEMIC_TRACKS.md`](docs/EPISTEMIC_TRACKS.md).

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
| G1 | stronger partial mechanism evidence | M068 induces four distinct adapters across a precommitted authored body bank. M071 adds one accepted fresh blind external task, but the task source is visible and no opaque incompatible-body test is present. M069 contributes no qualified evidence after D037. |
| G2 | open | No vision or multimodal grounding in one continuing lineage. |
| G3 | partial bounded evidence | Earlier lineages plan inside authored finite task languages. |
| G4 | open | M071 used one frozen agent on two external tasks but succeeded on only one; this is competence, not demonstrated transfer across domains. |
| G5 | stronger partial bounded evidence | M066 preserves bounded causal memory and post-migration plasticity. M073 adds one post-demonstration serialized skill that survives complete teacher removal, but tests only one homogeneous authored family and no forgetting. |
| G6 | partial mechanism evidence | M071 completes one independently maintained task in an official digest-pinned no-network container. A second task is refused; browser/desktop competence and broad environment coverage remain absent. |
| G7 | open | No human-hour task-horizon evaluation. |
| G8 | stronger partial bounded evidence | Disposable self-rewrite exists, and M073 induces then applies one executable capsule after its external teacher is removed; official adoption and the induction algorithm remain human-controlled. |
| G9 | strong bounded evidence | Frozen canonical workflows, negative preservation and exact reproduction. |
| G10 | strong bounded mechanism evidence | M071 preserves no-network isolation and evaluator-owned success; M072 causally isolates authority admission and tamper-evident audit chaining under 48 authored non-executing scenarios. No independent general-agent red-team or calibrated-refusal rate exists. |

The next accepted result must change this table by evidence, not wording.
