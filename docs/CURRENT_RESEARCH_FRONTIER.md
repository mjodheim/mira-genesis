# Mira Genesis — Current Research Frontier

**Reader-facing status snapshot — 2 September 2026**

This document explains where the active research line stands now. It is a navigation layer, not a
replacement for frozen protocols, immutable results, `PROJECT_STATE.md`, `PROJECT_STATE.yaml`,
`DECISIONS.md`, `SCIENTIFIC_HYPOTHESES.md`, or experiment-local evidence.

The previous 26 August snapshot is preserved byte-for-byte at
[`state-history/CURRENT_RESEARCH_FRONTIER_2026-08-26.md`](state-history/CURRENT_RESEARCH_FRONTIER_2026-08-26.md).

## Where the project is now

The current research line is **not waiting on another implementation of the same M119 instrument**.
M119 is closed. Its one qualifying generation was spent and produced an inadequate carrier bank, so
H64 remains untested.

The immediate problem is therefore instrumental and prospective:

> Can the next one-shot carrier-blind experiment prove, before spending its qualifying generation,
> that generator-conformant outputs are accepted by the frozen host, that the resulting bank is
> scientifically adequate for the frozen plan, and that the checker scores only the exact committed
> plan and evidence it authenticates?

An actual scientific comparison should occur only after those questions are answered mechanically.

There is **no active frozen successor hypothesis** at this snapshot. `M120` / `H65` is a proposed
working label only; neither identifier is currently registered in the repository.

## The recent instrument sequence

| Milestone | Status | What was learned | Scientific hypothesis |
|---|---|---|---|
| M115 / H60 | `instrument-aborted` after one materialized completion and legitimate reveal | strict-JSON failure prevented a carrier payload; terminal class was too weakly evidenced to infer a cause such as truncation | **untested** |
| M116 / H61 | instrument-development closed before freeze | catalogue structured-output capability did not imply enforcement: fixed route enforced 0/9 required schema feature classes | **untested** |
| M117 / H62 | route calibration / instrument development closed | OpenInference on the fixed DeepSeek checkpoint passed all final DEVELOPMENT qualification clauses and large constrained-output stress; apparatus revisions were transparently disclosed | **untested** |
| M118 / H63 | instrument-design and hostile-audit closed before scientific generation | readiness passed, but repeated Tier-1 measurement-design defects showed the scientific instrument was too complicated for a one-shot test | **untested** |
| M119 / H64 | `instrument_aborted` after one qualifying generation | clean delivery and schema conformance still produced a bank the frozen host/evaluator could not qualify | **untested** |

No M113–M119 milestone advanced G1–G10.

## M119 in one page

The frozen route returned HTTP 200 in one attempt, with the exact requested model/provider,
`finish_reason: stop`, a parsed completion and frozen output-schema conformance.

The generator was asked for 36 machines and emitted 37. After the one seal and authorized reveal:

- 3 carriers were accepted by the frozen host;
- 34 were refused;
- 0 cleared the qualification clauses;
- 0 paired demands were posed;
- no arm ran.

The plan required at least three qualifying carriers and three distinct qualifying structures. The
correct frozen verdict is therefore `instrument_aborted`, not negative, inconclusive or positive.

Refusal counts reveal the primary mismatch:

- 25: action argument domain outside 2–4;
- 8: carrier observes none of its own state;
- 1: copy source cell outside 0–1.

The first two are permitted by the generator-facing schema as written but forbidden by the host.
That means **schema-valid generation was not mechanically sufficient for host-valid carriers**.

The second important gap is timing: pre-seal admission established that a payload was admissible,
but did not establish that it contained enough qualifying and structurally distinct carriers to
satisfy the frozen scientific plan. An inadequate bank could therefore consume the one reveal.

## Two frozen checker findings

Closing review reproduced two defects in M119's checker:

1. the supplied analysis plan was not independently re-derived before its thresholds were trusted;
2. the canonical measurements file was authenticated, but a different caller-selected measurement
   path could be scored.

They do not change the canonical M119 outcome because the committed canonical plan and measurements
were actually used and the committed report replays byte-identically.

They **must not be fixed inside M119**. The checker is part of the tested-system freeze and a
post-reveal edit would contaminate the closed record.

## What the next successor must prove before one-shot science

A successor should be smaller and more mechanical than M119, not merely more elaborate.

### 1. Generator schema and host acceptance must agree

There should be no prose-only carrier constraint on the scientific path. Every generator output
accepted by the structured-output contract must either:

- already satisfy the frozen host's acceptance predicate; or
- pass through a predeclared, total and content-independent envelope whose equivalence to the host
  acceptance surface is mechanically checked before generation.

A synthetic adversarial census should demonstrate both directions before freeze.

### 2. Adequacy must be decided before seal/reveal

The pre-seal stage must evaluate the frozen plan's scientific bank requirements, including minimum
qualifying carriers and distinct structures. If the bank is inadequate, the milestone should close
as an instrument failure **without consuming a reveal and without redrawing**.

This preflight is not permission to select, filter, repair or resample generator outputs.

### 3. The checker must bind what it scores

The scientific checker should have no caller-selectable scientific evidence path. It should load the
canonical committed measurements itself and authenticate those exact bytes before scoring them.

The analysis plan should likewise be reconstructed or independently validated against the committed
source and decision constants, not accepted because a JSON field repeats a known digest.

### 4. Exercise the real success path before freeze

A refusal-path smoke test is insufficient. Before the scientific freeze, the exact direct entry point
must be executed in a disposable DEVELOPMENT checkout against a materialized synthetic result through
the full replay/scoring path. The rehearsal must demonstrate that forged plan/evidence substitutions
fail closed.

### 5. Do not spend the qualifying invocation until all of the above is green

The next milestone should treat instrument readiness as a hard prerequisite. A failed DEVELOPMENT
preflight costs no scientific draw; another avoidable post-generation instrument abort consumes the
one-shot opportunity and teaches nothing about the hypothesis.

## What must remain untouched

- M115's terminal strict-JSON record and its evidential limitations;
- M116's capability-matrix closure;
- M117's disclosed calibration chronology;
- M118's decision to stop before scientific generation;
- M119's frozen plan, code, bank, reveal, checker and `instrument_aborted` result;
- the two disclosed M119 checker defects as historical facts.

No successor may make its own result look better by editing those records.

## Working autonomy boundary

The next development agent can independently audit `main`, implement a prospective successor, build
adversarial fixtures, run tests, conduct self-review and hostile review, and prepare a PR.

Owner/external escalation is required before:

- registering an owner-only publication/IP decision;
- freezing or authorizing a one-shot scientific protocol;
- spending a qualifying scientific invocation or reveal;
- introducing new external credentials or authority;
- changing a scientific proposition, threshold or decision rule after qualifying observation.

The implementation handoff is in
[`CLAUDE_HANDOFF_M120.md`](CLAUDE_HANDOFF_M120.md).

## Useful starting points

- [`../PROJECT_STATE.md`](../PROJECT_STATE.md)
- [`../PROJECT_STATE.yaml`](../PROJECT_STATE.yaml)
- [`../experiments/M117/STAGE1_OUTCOME.md`](../experiments/M117/STAGE1_OUTCOME.md)
- [`../experiments/M118/OUTCOME.md`](../experiments/M118/OUTCOME.md)
- [`../experiments/M119/OUTCOME.md`](../experiments/M119/OUTCOME.md)
- [`../IP_ASSET_REGISTER.md`](../IP_ASSET_REGISTER.md)
