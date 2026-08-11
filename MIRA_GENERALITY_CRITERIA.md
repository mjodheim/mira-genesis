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

M074 contributes no gate advance but now supplies a valid negative. Its frozen, single-attempt
paired campaign completed all feasible tasks and no impossible task, yet emitted zero refusals:
true-refusal rate and margin were 0.0 and terminal refusal saved no step. H20 is refuted on the
three public authored pairs; the result cannot establish a general calibrated-refusal rate.

M075 contributes no additional gate evidence. Its committed public model-development record is a
promising but non-causal signal: explicit self-evidence produced 2/3 true refusals, no false refusal
and all three feasible submissions, while independently sampled baseline requests produced no
refusal or submission. The bank is public and authored. H21 still requires a frozen pre-private
policy, defensible causal control, sealed independent cross-domain bank and reproduction.
The pre-private checker now makes that boundary mechanical and currently returns false: no signed
external envelope, signer allowlist or frozen private protocol exists, and no payload was accessed.

M077 contributes no gate advance and is preserved as a valid negative. Its checkpoint ablation
behaved exactly as preregistered, but its constraint-monitor ablation did not lose detection: silent
corruption eventually breaks a guarded operation, so the boundary audit buys latency rather than
coverage in that body. The result may not be cited as long-horizon autonomy, and its episode-count
horizons may not be reported as human-equivalent task horizons.

M076 is positive bounded multimodal-grounding mechanism evidence on the endogenous track. Matched
ablations that preserve byte length, key order and token count show that each of three channels is
required by exactly the family that depends on it, and by neither of the others. It calls no model,
selects no external task and consumes no third-party attestation. Its rasters and families are
project-authored and confined to one domain, so it moves G2 off open without closing it and supplies
no cross-domain, perception or Gate 2 evidence.

M078 is positive bounded refusal-mechanism evidence on the endogenous track. It exercises the one G1
clause M068 left untested, under a construction where every incompatible body admits a candidate
fitting all public observations, so refusal cannot be an exhausted search. It does not advance G1:
the bodies are project-authored and closure requires an externally maintained interaction language
plus independent reproduction. It says nothing about model refusal behaviour, where M074's negative
remains the only result.

M079 is positive bounded planning-mechanism evidence on the endogenous track. It exercises all
four G3 clauses under a construction where committing on an ambiguous goal is demonstrably
harmful: a never-ask control reached six unsafe terminal states, and asking is never scored as
success. The world is project-authored, so G3 does not advance. Its planner is deterministic and
it is not evidence about model clarification behaviour.

M080 is positive bounded continual-acquisition evidence on the endogenous track, and the first
result here to measure forgetting at all. Its interference is real: the cheap in-place rewrite is
always available and always destroys an earlier skill, which the consolidation ablation
demonstrates. Its retention is replay-dependent rather than structural, and that limitation is
part of the result rather than a caveat. G5 does not advance; the skills are project-authored.

M081 is positive bounded real-environment evidence on the endogenous track. One interface drives
two genuinely distinct real containers, and its self-report control shows the cost of the scoring
rule G6 imposes: judged by the agent's claim the interface looks perfect, judged by environment
state it is not. It adds no browser and no desktop VM, so the larger part of G6 is untouched and
the gate does not advance.

M082 is positive bounded browser-environment evidence on the endogenous track. Its browser store
lives in localStorage with no network route, so the crossed-driver arm completing nothing shows a
materially different substrate rather than a relabelled service. It adds no desktop VM and its
page is project-authored, so G6 does not advance.

M083 adds a fourth environment legible only as rendered pixels and explicitly does **not** supply
G6's desktop VM: a container shares the host kernel and no hypervisor was available. Its
crossed-driver arm completes nothing, so the rendered grid is reachable only through the screen.
The application is an authored Tk grid, so G6 does not advance.

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
| G1 | stronger partial mechanism evidence | M068 induces four distinct adapters across a precommitted authored body bank. M078 now exercises the refusal clause: one unchanged procedure adapted four compatible bodies at 12/12 hidden each and refused four incompatible ones with zero false refusals, while a never-refuse control adopted a public-fitting adapter on all four and failed hidden validation. M071 adds one accepted fresh blind external task, but the task source is visible. Every body remains project-authored, so the gate does not advance. M069 contributes no qualified evidence after D037. |
| G2 | partial mechanism evidence | M076 runs one persistent agent over language, structured state and synthetic pixels, emitting both symbolic calls and embodied actions. Matched shape-preserving ablations give an exact triple dissociation against a measured guessing floor. The rasters are authored 24×24 panels in one domain, so natural-image perception and modality breadth remain absent. |
| G3 | partial bounded evidence, all four clauses exercised | Earlier lineages plan inside authored finite task languages. M079 adds one planner given only a goal predicate, affordance schemas with costs and a budget: 8/8 static and 8/8 revision tasks solved, revision on all eight, clarification on 8/8 ambiguous and 0/16 unambiguous goals, zero unsafe terminal states. A never-ask control reached six unsafe terminal states and an always-ask floor solved nothing. The world is project-authored, so the gate does not advance. |
| G4 | open | M071 used one frozen agent on two external tasks but succeeded on only one; this is competence, not demonstrated transfer across domains. |
| G5 | stronger partial bounded evidence, forgetting now measured | M066 preserves bounded causal memory and post-migration plasticity. M073 adds one post-demonstration serialized skill but tests no forgetting. M080 puts retention at risk in one bounded shared table and measures it: zero capabilities lost across six acquisitions, sublinear memory growth and byte-identical rollback, while a consolidation ablation loses five. Retention is replay-dependent, not structural. The skills are project-authored, so the gate does not advance. |
| G6 | partial mechanism evidence | M071 completes one independently maintained task in an official digest-pinned no-network container. M081, M082 and M083 then drive a container shell, an HTTP service, a real Chromium browser and a real X11 desktop session under **one unchanged interface**, each completing every completable task, with crossed-driver controls completing none and each environment's own success report diverging from its measured state at least once. **The desktop VM remains absent**: a container shares the host kernel and no hypervisor is available here. Physical device and external-suite competence remain absent, the tasks and applications are project-authored, and the container-backed evidence is local opt-in rather than CI-attested. |
| G7 | open | No human-hour task-horizon evaluation. M077 addressed only the fault-recovery and constraint-retention components and returned a valid negative on its dissociation hypothesis; its undegraded retention to 2048 episodes and its isolated checkpoint mechanism are bounded observations in one authored in-memory body, and episode counts are not human-equivalent horizons. |
| G8 | stronger partial bounded evidence | Disposable self-rewrite exists, and M073 induces then applies one executable capsule after its external teacher is removed; official adoption and the induction algorithm remain human-controlled. |
| G9 | strong bounded evidence | Frozen canonical workflows, negative preservation and exact reproduction. |
| G10 | strong bounded mechanism evidence with a negative calibration result | M071 preserves no-network isolation and evaluator-owned success; M072 causally isolates authority admission and audit chaining. M074 validly records 0/3 true refusals on authored capability-absence pairs, so no independent calibrated-refusal claim exists. |

The next accepted result must change this table by evidence, not wording.
