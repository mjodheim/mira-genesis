# Mira Genesis — Current Research Frontier

**Reader-facing status snapshot — 22 August 2026**

This document explains where the active research line stands now and what the next milestones are
trying to establish. It is a navigation and interpretation layer, not a replacement for frozen
protocols, immutable results, `PROJECT_STATE.md`, `PROJECT_STATE.yaml`, `DECISIONS.md`, or the
experiment-local evidence.

## The research question now

The original bounded Genesis question has already been answered twice inside declared limits: first
in the finite DFA laboratory at M042 and later on the CPython → Node ESM → whole-WebAssembly
construction line at M066.

The active question is stronger and narrower:

> Can a software lineage make an internally selected and validated change that alters what later
> changes are reachable, then progressively acquire the machinery needed to extend that process
> without a human supplying the finished next repair?

The project is not currently claiming open-ended recursive self-improvement. It is testing the
necessary mechanisms one at a time, under conditions designed to let a negative result remain a
valid result.

## Current frontier at a glance

| Milestone | Status | What it establishes | Main remaining ceiling |
|---|---|---|---|
| M093 | Engineering rehearsal | Real repository transformation, sandbox validation, adoption, persistence and rollback | Target, diagnosis and patch were substantially authored |
| M094 | **Positive qualified scientific result** | The lineage measured the limiting real component, selected the tied top targets and assembled an executable repair from composable operations; qualification passed cross-component | Eligible components, observations, operation set and composition bound remain authored |
| M095 | **Negative qualified result — attempt 1; H40 refuted** | Development shows structural reach and failed-search descent, but 0/6 positive structural qualification worlds execution-confirm B after A; 3/3 negatives remain negative | Local subset capability satisfaction does not compose into an exact nested contract |
| Next | Required successor boundary | Establish contract-safe composition across structural variation under a new frozen protocol | Must prevent or safely project A's extra output keys without an authored target-specific patch |
| M096 plan | Deferred successor boundary | Bring endogenous transformation-language extension into the current cumulative real-software line | Premature until behaviourally compositional reach is qualified |
| M097 | Planned successor boundary | Persist an acquired transformation capability across complete process death/restart | Must reconstruct capability from lineage-owned persisted state rather than host code |
| Later | Not yet demonstrated | Repeat the causal chain across fresh tasks/domains and measure whether acquired improvements improve the ability to find later improvements | Open-endedness, transfer and long-horizon autonomy remain open research problems |

## M094 — the strongest current qualified real-software result

M094 is the current qualified anchor for the active line.

Its second preserved attempt produced a positive verdict with **12/12 protocol conditions computed
and true**. The mechanism made **zero model calls and zero network calls**. The diagnosis selected
`mira_core/contracts.py` by measurement and repaired both classes tied at the highest demand,
`Goal` and `Observation`.

Qualification was drawn only after adoption from the adopted mechanism digest and passed **2/2
cross-component requirements**:

- `AgentResult`, including a computed `@property` alongside declared fields;
- `ContainerSpec`, including a key mapped to a differently named field.

The random-selection and template-only controls closed nothing; a larger budget over the same
operations found the same mechanism.

The first positive-looking attempt remains preserved but withdrawn because its rollback evidence was
not actually byte-exact: decoded text equality hid CRLF → LF normalization. The repair was made in
the transformation store, not in the scientific target, and the second attempt reused the same
mechanism and qualification draw.

That history matters: M094 is valuable not because every first implementation was correct, but
because defects that could change the claim were allowed to invalidate evidence instead of being
silently repaired after the fact.

Authoritative material:

- `experiments/M094/`;
- `scripts/check_m094_result.py`;
- `docs/REPOSITORY_AUDIT_2026_08_18.md`;
- PR #177.

## M095 — improvement enabling improvement

M095 asks a different question from “can the lineage repair twice?”

Its development world contains an inner value object and an outer value object. The outer repair
needs to call a renderer on the inner object. At S0 that renderer does not exist, so the outer repair
is unreachable. The lineage repairs the inner object; after adoption, the same operation set can
construct the outer repair.

In the declared world the measured chain is:

```text
S0 -- A --> S1 -- B --> S2

B from S0: unreachable
A from S0: reachable and executed
B from S1: reachable and executed
B with A removed while other first-round repairs are retained: unreachable
```

The search space itself changes from 191 examined compositions before A to 239 after A.

### The descent

The first mechanism only worked when the enabling repair was ranked at least as high as the repair
it enabled. That looked like a domain boundary. Adversarial work then showed the failed search
already names the operation it cannot apply, and that operation identifies the missing supplier.

The lineage can therefore use the failure as evidence, descend to the lower-ranked enabler, repair
it, and retry the blocked target. With that change, the enabling relation is demonstrated across all
six tested arrangements in which an enabling insufficiency exists, including the two cases where
the enabler is initially outranked.

Two deliberately negative arrangements remain: if the inner class is never rendered directly, it
presents no diagnosed insufficiency of its own, so there is no visible repair to descend to.

### What the qualification found

Before freeze the branch underwent repeated adversarial review: **31 defects were recorded across
seven passes and 30 repaired**; defect 19 remained a disclosed non-decisive ceiling. Several were
especially important:

- search survivors were once accepted structurally without execution;
- hidden cases could be constructed incorrectly;
- ties were still able to decide the result after earlier fixes claimed to remove that dependence;
- two control arms could report `satisfied` while the mechanism they were supposed to test was dead;
- the original counterfactual was only the control repeated on a byte-identical world;
- a probe that never ran could be recorded as candidates that ran and failed;
- some record fields were assertions disguised as measured booleans;
- the reach operation could call a different method from the one that actually satisfied the
  rendering requirement;
- world facts counted filenames and unrelated public methods instead of measured demand and
  structural rendering supply;
- a random-target arm could exclude the inner class for a different nested target from the one
  its control actually ranked;
- the withheld-operation arm is true by construction because no alternative operation can satisfy
  the nested requirement.

H40, an eleven-condition protocol and an exhaustive nine-entry population were then frozen locally.
Attempt 1 ran once from clean commit `951c7c2`, with zero model and network calls. The result is
**negative**: all three zero-demand witnesses remained negative, but none of the six demand-bearing
entries execution-confirmed B. The checker recomputed eight passes and three failures: P3, P5 and
P6. Its P7 replay reproduced every entry exactly.

A was reached in all six positive worlds and made the nested operation applicable. The failure came
later: A's local requirement allowed extra mapping keys, while B's nested value was compared as a
complete mapping. `Coordinate`, `Vector` and `Marker` all acquired overbroad renderers, so every B
survivor disagreed with the caller at execution. This is a qualified negative, not a broken or
unrunnable instrument. No post-verdict repair is made.

Authoritative material:

- `experiments/M095/RESULT.json`;
- `experiments/M095/CHECK_REPORT.json`;
- `experiments/M095/POST_VERDICT_ANALYSIS.md`;
- D064 and H40.

## The next objective: contract-safe composition, then language

M095 keeps the operation set fixed. Its negative result now shows that structural applicability is
not sufficient: a repair accepted under a partial local contract may not compose inside an exact
nested contract.

The immediate successor must distinguish exact output contracts from subset capability
satisfaction and qualify one of three mechanisms under a new protocol: exact acceptance, minimal
synthesis, or a demand-derived projection of a broader renderer. It must not repair or rerun M095
attempt 1.

Only after that prerequisite is earned does the previously planned language boundary become live:

> encounter a transformation requirement that the inherited operation language cannot express,
> establish that insufficiency rather than merely failing to search deeply enough, acquire an
> extension from lineage-owned machinery, register it, and then use it to reach something that the
> inherited language could not reach.

M091 already demonstrated endogenous extension of a state-owned transformation language in a
bounded abstract setting. M096 should not relabel that result. The interesting successor is to
bring the same kind of ownership into the **current real-software cumulative line**, where an
acquired improvement can become part of the machinery that produces later improvements.

## Persistence after acquisition

A capability that exists only because one Python process still has host code in memory is not a
lineage-owned capability.

M097 should therefore require a hard process boundary:

1. persist the accepted lineage state;
2. terminate the process completely;
3. start a fresh process with only the allowed serialized state and fixed generic substrate;
4. reconstruct the acquired transformation capability;
5. demonstrate the capability on a fresh requirement;
6. force a fault and restore the prior lineage exactly.

Only then is it reasonable to say the lineage *kept* the acquired machinery.

## The longer-term target

The research target after M097 is a repeated causal chain, not a single spectacular benchmark:

```text
state S0
  -> acquire A
state S1 has new reach
  -> acquire B using that reach
state S2 has a larger or different transformation capability
  -> acquire C
...
```

A stronger result would additionally show that earlier acquisitions improve the **process of finding
later acquisitions** — for example by reducing search cost, exposing previously unavailable
experiments, improving selection, or extending the constructive language.

That still would not by itself establish AGI or open-ended evolution. General-agent claims are
governed separately by `MIRA_GENERALITY_CRITERIA.md`, which requires cross-domain evidence,
long-horizon autonomy, external/private evaluation, independent reproduction and adversarial audit.

## What the project does not currently claim

Mira Genesis does **not** currently establish:

- AGI;
- consciousness or sentience;
- unrestricted or open-ended recursive self-improvement;
- arbitrary self-modification;
- autonomous authority over production systems, credentials, networks or deployment;
- superiority to frontier language models;
- that model-mediated benchmark competence belongs to the endogenous lineage.

Those exclusions are not disclaimers around the result; they define the result.

## Why this line is worth continuing even if a later milestone fails

The repository already contains useful evidence about failure modes in self-improvement research:
proxy measures that choose the answer, qualification cases that do not execute, evaluators that can
leak hidden evidence, state that is serialized but not behaviorally consulted, controls that cannot
possibly falsify a claim, and apparent causal evidence that collapses under a stronger
counterfactual.

A negative M096 or M097 would therefore locate another ceiling. The program only loses scientific
value if failures are hidden, boundaries are moved after observation, or development demonstrations
are promoted into claims they did not test.

## Navigation

- `README.md` — short public introduction;
- `PROJECT_STATE.md` / `PROJECT_STATE.yaml` — long-form project registers;
- `ROADMAP.md` — historical construction roadmap;
- `GENESIS_COMPLETION_CRITERIA.md` — frozen bounded completion criteria;
- `MIRA_GENERALITY_CRITERIA.md` — stronger generality vocabulary and gates;
- `experiments/M094/` — current qualified real-software anchor;
- `experiments/M095/` — active improvement-enabling-improvement work;
- `FAILURE_LOG.md` — preserved failure history;
- `docs/EPISTEMIC_TRACKS.md` — endogenous versus model-mediated attribution boundary.
