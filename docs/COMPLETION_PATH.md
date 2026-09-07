# Mira Genesis — completion path to an AGI-candidate presentation

**Navigation only — 7 September 2026.** This register creates no scientific evidence, moves no
generality gate, fills no owner decision and changes no frozen record. It collects work that is
already specified elsewhere into one ordered view, and attributes each remaining item to the party
that can actually perform it.

Authoritative sources remain [`MIRA_GENERALITY_CRITERIA.md`](../MIRA_GENERALITY_CRITERIA.md),
[`PROJECT_STATE.md`](../PROJECT_STATE.md), [`PROJECT_STATE.yaml`](../PROJECT_STATE.yaml),
[`GENESIS_COMPLETION_CRITERIA.md`](../GENESIS_COMPLETION_CRITERIA.md),
[`CURRENT_RESEARCH_FRONTIER.md`](CURRENT_RESEARCH_FRONTIER.md) and the frozen experiment records.
Where this file and any of them disagree, they win.

## What "the end of the project" means here

Two different completions exist and are routinely confused by readers.

**Phase-one completion is already recorded.** M042 satisfies the ten Genesis gates in the bounded
deterministic binary-DFA laboratory, and M066 confirms the same ten gates on the CPython → Node ESM →
WebAssembly path. That record is closed and is not what this file tracks.

**The presentation target is a different and much stronger tier.** In the status vocabulary of
`MIRA_GENERALITY_CRITERIA.md` it is **AGI candidate**: general-agent evidence that survives
independent reproduction, adversarial audit and comparison with human baselines at declared cost.

The tier above it, **AGI confirmed**, is explicitly reserved for a broader scientific and societal
conclusion and is *not a label this repository may assign to itself*. No amount of work listed below
changes that. The presentable claim is "AGI candidate", never more.

## The decision rule, restated as a checklist

A general-agent claim requires **all** of the following simultaneously:

| # | Requirement | Source |
|---|---|---|
| 1 | All ten generality gates pass | decision rule |
| 2 | In **one versioned lineage** | decision rule |
| 3 | Across **at least four materially different domains** | decision rule |
| 4 | **Independent reproduction** | decision rule + external blockers |
| 5 | **External adversarial audit** | decision rule + external blockers |
| 6 | Frozen external **and private** evaluations | status vocabulary |
| 7 | Human baselines at declared cost | G9 |
| 8 | Thresholds and benchmark subsets frozen **in the claiming experiment** | decision rule |

No mean score compensates for a failed gate. Requirement 8 means the claiming experiment must be
newly numbered and prospectively frozen; none of the existing evidence can be recomposed into it
after the fact.

## Gate ledger — nothing is closed

**Zero of ten gates are closed.** Every row below is the *remaining* work, not the accumulated
evidence; consult the evidence map in `MIRA_GENERALITY_CRITERIA.md` for what already exists.

| Gate | Status | What remains | Who |
|---|---|---|---|
| G1 interface novelty | stronger partial | interaction language and meta-schema not authored by the project; independent reproduction | EXTERNAL |
| G2 multimodal grounding | partial | perception beyond authored 24×24 rasters; modality breadth in one persistent agent | PROJECT |
| G3 novel task planning | partial, all four clauses exercised | a world the project did not author | EXTERNAL |
| G4 cross-domain transfer | partial bounded cross-family | an independently authored held-out domain; independent human reproduction | EXTERNAL |
| G5 continual learning | stronger partial bounded | retention that is structural rather than replay-dependent; skills not project-authored | PROJECT then EXTERNAL |
| G6 real-environment competence | partial | **desktop VM** (needs a hypervisor; a container shares the host kernel), physical simulator, low-risk device, uncontaminated private suite frozen after design | PROJECT then EXTERNAL |
| G7 long-horizon autonomy | **open — no evidence** | task-horizon evaluation at 10 min / 1 h / 4 h / 1 day with intervention count, fault recovery, constraint retention, verification quality and cost | PROJECT then OWNER |
| G8 governed self-improvement | stronger partial bounded | carriers, registries and evaluators not project-authored; adoption stays human-controlled by design | EXTERNAL |
| G9 evaluation integrity | strong bounded | human baselines; monetary and energy/compute cost reporting | PROJECT |
| G10 safety and calibrated refusal | strong mechanism + a negative | M074 records 0/3 true refusals, so no independent calibrated-refusal claim exists; capability and misuse thresholds before access expands | PROJECT |

The recurring ceiling across G1–G8 is one sentence: **almost everything is project-authored.** That
is a single structural limitation wearing eight different costumes, and it is why the external
blockers below dominate the schedule rather than merely appending to it.

## The three external blockers

`MIRA_GENERALITY_CRITERIA.md` records these as blockers rather than pending tasks, precisely so no
internal result is read as progress toward them. While they stand, **AGI candidate is NO regardless
of any internal result.**

| Blocker | Why nothing here can lift it | Prepared handoff |
|---|---|---|
| Human-maintained sealed bank | requires a person outside the project to author and withhold tasks | [`audits/EXTERNAL_VALIDATION_HANDOFF_2026-09-05.md`](audits/EXTERNAL_VALIDATION_HANDOFF_2026-09-05.md) |
| Independent reproduction | requires a third party who can fail | frozen protocols, pinned runtime, byte-stable replay, expected-failure lists — everything except a reproducer |
| External adversarial audit | requires an adversary the project does not choose | pre-freeze reviews and preserved negatives are self-audit, which is not the same thing |

`CLAUDE.md` forbids replacing any of these with project-authored or project-controlled AI-generated
evidence, and M085's independent-maintainer requirement must remain genuine. This constraint is
deliberate and is not a defect to engineer around.

### What the project must supply, and must not supply

The handoff already fixes the mechanical requirements: a real identity outside `Anthony Mets` /
`mjodheim`, an SSH signing key and allowed-signers entry, an `ssh-keygen -Y verify` envelope
committing to a sealed payload, custody external until protocol freeze. For H21/M075 the frozen
validator requires **two** independent maintainers and banks before the claim is supportable; one
maintainer can produce the first private result only.

The project supplies validators, schemas and signing instructions. It must not author the bank,
inspect the payload early, select a favourable domain after seeing it, replace failed tasks after
execution or silently rerun an attempt.

## Owner-only decisions currently open

None of these can be taken by a contributor or an agent. Each has permanent scientific consequence.

| Decision | Subject | Consequence if taken |
|---|---|---|
| M125 DEVELOPMENT network authorization | the exact frozen M125 protocol, after offline tests, CI, hostile review and digest verification | unblocks readiness requests; does **not** authorize an H70 qualifying generation |
| D063 | H39 / M094 register claim | H39 currently has a reproducing positive verdict but **no accepted register claim** |
| M092 / H38 canonical cursor | `first_run_only` search, currently paused | advancing it continues a unique, non-replayable scientific observation |
| M121 / H66 canonical salt, run, reveal, acceptance | the only G7-directed experiment | a positive result would still be bounded partial evidence and would **not** close G7 |

P-029 and the earlier P-024…P-028 dispositions resolve publication and IP governance only. They
authorize no scientific execution.

## The delivery ceiling is the nearest hard limit

The cross-instrument delivery allowance stands at **4 of 6 spent**, and it **does not reset when a
successor is opened**. M113 through M124 produced no qualifying scientific observation: H58–H65 and
H67–H69 are `untested`, not negative, and advance no gate.

Two delivery slots therefore remain for the entire carrier line. This is the binding operational
constraint on the fastest-moving part of the project, and it is why M125 is being hardened offline
before any request rather than retried quickly.

## Ordered critical path

Attribution matters more than sequence here: items marked EXTERNAL cannot be accelerated by any
work inside this repository, and they gate the presentation tier absolutely.

**Track A — project-executable now**

1. Complete the M125 offline instrument: bounded probes, fresh prospective calibration, C1–C3 gate
   conformance, full offline test coverage, CI and hostile review.
2. Obtain one qualifying carrier-line scientific observation, spending at most the remaining
   delivery budget.
3. Implement the hardened M121 v2 harness for G7 — the only gate at zero — leaving the canonical
   run owner-gated.
4. Close G6's desktop-VM clause where a hypervisor is available; then attempt an external suite as
   development evidence.
5. Supply G9's missing human-baseline and cost-reporting apparatus.

**Track B — owner decisions** (see the table above; each is a prerequisite for parts of Track A
and Track C, and none has a technical substitute)

**Track C — external, and on the critical path**

6. Recruit an independent maintainer for H31/M085; recruit a second for H21/M075.
7. Obtain independent reproduction by a third party who can fail.
8. Commission an external adversarial audit the project does not choose.

**Track D — only after A, B and C**

9. Open a newly numbered claiming experiment that prospectively freezes every threshold and
   benchmark subset, runs one versioned lineage across at least four materially different domains,
   and reports quality, reliability, latency, cost and every negative.

## Honest distance estimate

The presentation tier is not near. Zero of ten gates are closed; the hardest gate has no evidence at
all; the active line has spent twelve milestones without a qualifying scientific observation and has
two delivery slots left; and three requirements of the decision rule are structurally outside this
repository's reach.

The bottleneck is not engineering throughput. The repository's protocol discipline, negative
preservation, byte-stable replay and publication governance are in better shape than the science
they support. What is missing is **people the project does not control** — and no internal work,
however rigorous, substitutes for them.

## Claim boundary

This file does not claim AGI, AGI candidacy, general intelligence, consciousness, open-ended
evolution, unrestricted self-rewrite, open-ended recursive self-improvement, unrestricted repository
authority or unrestricted network authority. It asserts no gate movement and no scientific result.
It is a navigation aid for work that has not been done.
