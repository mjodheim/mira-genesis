# Mira Genesis — Current Research Frontier

**Reader-facing status snapshot — 2 September 2026 (M120 apparatus)**

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

Those questions are now answered mechanically, on the M120 branch, and **nothing scientific has been
spent answering them**. M120/H65 is pre-registered, built and rehearsed end to end on DEVELOPMENT
data; its qualifying scientific invocations are **0**, no bank exists, no freeze has been taken, and
H65 is **untested**.

What remains is not more instrument work. It is the five owner gates listed at the end of this
document.

## The recent instrument sequence

| Milestone | Status | What was learned | Scientific hypothesis |
|---|---|---|---|
| M115 / H60 | `instrument-aborted` after one materialized completion and legitimate reveal | strict-JSON failure prevented a carrier payload; terminal class was too weakly evidenced to infer a cause such as truncation | **untested** |
| M116 / H61 | instrument-development closed before freeze | catalogue structured-output capability did not imply enforcement: fixed route enforced 0/9 required schema feature classes | **untested** |
| M117 / H62 | route calibration / instrument development closed | OpenInference on the fixed DeepSeek checkpoint passed all final DEVELOPMENT qualification clauses and large constrained-output stress; apparatus revisions were transparently disclosed | **untested** |
| M118 / H63 | instrument-design and hostile-audit closed before scientific generation | readiness passed, but repeated Tier-1 measurement-design defects showed the scientific instrument was too complicated for a one-shot test | **untested** |
| M119 / H64 | `instrument_aborted` after one qualifying generation | clean delivery and schema conformance still produced a bank the frozen host/evaluator could not qualify | **untested** |
| M120 / H65 | pre-registered, built, DEVELOPMENT-rehearsed, unspent | a schema that states no relation between two fields plus a total decoder closes the host gap; adequacy is decided before the seal; the checker reproduces what it scores | **untested** |

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

## M120 in one page

M120 keeps the science and replaces the instrument. The proposition is H64's, unchanged, and the
arms, endpoint, exact test, α, effect floor, guards, verdicts, decomposition, comparator seed,
observation budget and admissibility minimums are inherited from M119 **by import**, with a check
that refuses to build an analysis plan if those modules' bytes move.

Five things are new, and each one names the M119 failure it closes.

**The carrier contract.** The schema handed to the generator states no relation between two fields,
because a relation between two fields is what M119 died of. `arity` and `arg_size` become one field
over `{0, 2, 3, 4}`; `initial` moves inside its own cell; `visible` becomes `hidden`, at most one
index over at least three cells; the error name becomes an index. A total, deterministic,
content-independent decoder discharges what is left. Every schema-valid candidate decodes into a
carrier the frozen host accepts — established by exhausting 240 constraint corners, fuzzing 1,200
draws, and running M119's own committed bank through it, where **0 of 37** are now refused.

**The narrowed family.** Closing the schema gap alone would not have been enough. Re-measured
against M119's committed public bank, that generator answered every range with its minimum — 22 of
37 machines had one cell — and decoding it leaves **one** machine of 37 qualifying. So the family
asked for is narrower: three to four cells, at most one latent, two to three conditional actions
plus two to three more. **That narrowing was chosen after reading a closed public record, and is
disclosed as such.** A verdict here speaks about a smaller family than M119 would have.

**Adequacy before the seal.** M119's bank was admissible and untestable, and the one reveal was
spent finding out. The gate now counts qualifying carriers, distinct structures and paired demands
before anything is sealed, with an enforced counts-only output allowlist, and an inadequate bank
closes the milestone with the reveal unspent. It is not permission to filter or redraw.

**A checker that reproduces what it scores.** It takes no evidence path from the command line,
re-derives the analysis plan from code, walks the custody chain from the sealed ciphertext down to
the carrier bank, and **re-runs the whole measurement** over the committed bank rather than reading
the committed numbers.

**Readiness re-measured for this schema.** M118's stress schema does not dominate the M120
candidate census, so inheriting its readiness would assert a measurement nobody took. The freeze is
refused without a committed M120 readiness result, and its stress schema is deliberately a
non-carrier one so that DEVELOPMENT cannot preview the bank.

### What the rehearsal found

The DEVELOPMENT rehearsal runs the real scripts in a disposable git checkout: 48 candidates, 0
refused by the host, 20 qualifying, 20 distinct structures, 90 paired demands, and a second clean
clone reproducing the report byte-identically. Nine adversarial substitutions all fail closed.

One of them did not, at first. An earlier draft of the checker **accepted** a forged measurements
file committed over the canonical path with a recomputed digest — the same defect class M119
disclosed, surviving into the successor built to remove it. That is why the checker now reproduces
the measurement instead of authenticating it. It was found before the freeze, which is where such
things are supposed to be found.

The rehearsal's own verdict is computed on synthetic devkit carriers and is **not evidence about
H65**.

### The five owner gates

Nothing below has been crossed:

1. the publication/IP disposition — reviewed and drafted at
   [`../docs/IP_REVIEWS/M120_PUBLICATION_REVIEW.md`](IP_REVIEWS/M120_PUBLICATION_REVIEW.md), with
   no register row written;
2. the DEVELOPMENT route-readiness run, which needs a credential and precedes the freeze;
3. the scientific freeze;
4. the one qualifying generation;
5. the single reveal authorization.

### What M120 still cannot promise

A verdict. The gates establish that a schema-valid completion yields a host-valid bank, and that an
inadequate bank cannot consume the reveal. Whether the blind generator produces an *adequate* bank
on this route is not knowable before the generation. The honest numbers: a development emitter
qualified at 29% at the contract's smallest corner, and M119's real blind bank qualified at one in
thirty-seven under the old contract. If the bank is inadequate, M120 closes as an instrument
failure **without** spending the reveal, and says so.

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

M120 reads M119's committed public bank as instrument evidence and changes nothing in it. That
reading is disclosed in M120's preregistration, plan limitations and derivation report.

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
