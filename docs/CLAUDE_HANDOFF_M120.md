# Claude handoff — prospective M120 successor after M119

**Prepared:** 2 September 2026  
**Starting point:** merged `main` after M119 (`a3f03efd8e86c10a1282828199e43649e3c3d807` before the documentation-only state consolidation)

## Read this first

M119 is closed. Its canonical verdict is **`instrument_aborted`** and **H64 is UNTESTED**.

Do not repair, rerun, relabel, reinterpret, filter or resample M115–M119. In particular, do not edit
M119's frozen checker to fix the two defects found after reveal. Those defects are successor
requirements, not permission for a retrospective repair.

`M120` / `H65` is a **proposed working name only** at the time of this handoff. Neither identifier is
registered in the repository. If the successor retains that numbering, register the hypothesis and
its exact scientific proposition prospectively, in the repository's normal governance order, before
any freeze or qualifying scientific execution.

## Objective

Advance the carrier-blind scientific line to an **actual hypothesis verdict** rather than another
avoidable instrument abort.

The successor should preserve M119's scientific target unless a prospectively documented reason
requires a new proposition. Its main job is to remove the specific instrument degrees of freedom that
M119 exposed before spending another one-shot generation.

## M119 facts you must preserve

- One qualifying scientific generation was spent.
- HTTP 200, one attempt, no retry.
- Exact frozen model/provider identity held.
- `finish_reason: stop`.
- Completion parsed and satisfied the frozen generator output schema.
- 36 machines were requested; 37 were emitted.
- Frozen host accepted 3 and refused 34.
- Zero carriers cleared the qualification clauses.
- Zero paired demands were posed and no scientific arm ran.
- Frozen verdict: `instrument_aborted`.
- H64 remains untested; no negative inference is allowed.
- No generality gate advanced.

Refusal counts:

- 25: action argument domain outside 2–4;
- 8: observes none of own state;
- 1: copy source cell outside 0–1.

This exposed two instrument failures:

1. generator-schema conformance did not imply frozen-host acceptance;
2. pre-seal admission checked admissibility, not adequacy against the frozen scientific plan.

Closing review also reproduced two frozen checker weaknesses:

1. caller-supplied analysis-plan content was not independently re-derived before thresholds were
   trusted;
2. the checker authenticated canonical measurements but could score a different caller-selected
   measurements path.

The canonical M119 result itself is not in doubt: committed canonical artifacts were used and replay
byte-identically. The problem is that the frozen checker would not have rejected some substituted
inputs.

## Mandatory prospective requirements

Treat the following as hard requirements for the successor design, not optional polish.

### R1 — mechanically align generator output with host acceptance

Construct one authoritative carrier acceptance specification or a mechanically proven equivalence
between:

- the schema/contract the generator can emit;
- any positional/content-independent envelope;
- `carrier_host.validate_carrier` and any acceptance predicate needed before qualification.

There must be no scientific carrier constraint that lives only in prompt prose.

Build adversarial synthetic fixtures that enumerate boundary cases including conditional arity /
argument-domain rules, own-state observability, copy-source bounds and every other host refusal class.
Prove before freeze that generator-contract-valid outputs cannot enter a host-refused state for the
relevant acceptance surface.

If JSON Schema cannot express a relation, do not pretend prose makes it enforced. Either change the
representation prospectively so the relation becomes enforceable, or add a total, predetermined,
content-independent transformation whose correctness is mechanically tested and whose use does not
select among generated candidates.

### R2 — pre-seal scientific-adequacy gate

Before sealing/reveal, compute the exact bank properties the frozen analysis plan requires:

- number of qualifying carriers;
- number of distinct qualifying structures;
- every prerequisite whose failure would make the downstream scientific statistic impossible.

An inadequate bank must close the milestone as an instrument failure without reveal. It must **not**
be repaired, filtered, resampled or regenerated.

The adequacy gate must not expose carrier content to the tested system or create a selection channel.
Its information boundary and allowed outputs should be explicit and tested.

### R3 — checker re-derives the frozen plan

The scientific checker must not trust a plan because its JSON repeats a known commitment string.
Rebuild or independently validate every decision-relevant plan value from committed code/constants and
verify the commitment from contents.

At minimum bind:

- minimum qualifying carriers;
- minimum distinct structures;
- session budget;
- endpoint definition;
- alpha and effect-size threshold;
- comparator identity/seed;
- guards;
- all verdict transitions.

Add adversarial tests showing that a forged plan preserving old self-reported digests is refused.

### R4 — checker scores only authenticated canonical evidence

Remove caller selection from the scientific evidence path. The authoritative checker entry point
should resolve the canonical committed measurement artifact itself, authenticate those exact bytes,
and score those same bytes.

Do not implement “authenticate A, score argv B”.

Add adversarial tests for forged alternate measurement files carrying copied provenance digests and
self-consistent unkeyed hashes.

### R5 — exercise the exact success/replay path before freeze

A refusal-path or missing-result smoke test is not sufficient. Before freeze:

1. materialize a DEVELOPMENT-only synthetic bank/result;
2. execute the exact direct checker entry point from a clean disposable checkout;
3. run through the real replay/scoring branch;
4. demonstrate deterministic equality;
5. demonstrate plan substitution and measurement substitution fail closed.

This rehearsal must be explicitly DEVELOPMENT-only and must not use the future qualifying input.

### R6 — no qualifying spend before hostile preflight is green

Before asking the owner to authorize any irreversible scientific generation:

- run the complete repository suite;
- run repository integrity and sealed-boundary checks;
- run targeted successor tests;
- conduct at least one hostile review focused on binding/authentication and one on
  schema/host/adequacy equivalence;
- resolve Tier-1 findings prospectively;
- produce a concise readiness report with machine-checkable pass/fail gates.

Do not spend the one-shot invocation while any gate is “probably fine”.

## Autonomy: what you should do without waiting for the owner

You are expected to move quickly and independently on reversible DEVELOPMENT work.

You may:

- audit current `main` once, then work from an explicit checklist rather than repeatedly rediscovering
  the repository;
- create a successor branch;
- draft the prospective hypothesis/register changes for review;
- redesign the carrier contract prospectively;
- implement preflight and checker binding improvements;
- add synthetic/adversarial fixtures and regression tests;
- run local tests and CI;
- inspect failures and fix pre-freeze implementation/instrument defects transparently;
- self-review and conduct hostile reviews;
- update documentation/state on the same prospective branch;
- prepare a PR with exact claim boundaries and a readiness summary.

Prefer small mechanically testable gates over prose assurances. Prefer deriving facts from committed
artifacts over copying them into another field. Prefer one canonical entry point over caller-configured
scientific paths.

## Stop and escalate to Anthony before

Do not silently cross any of these gates:

- registering/accepting an owner-only publication or IP disposition;
- final acceptance of the scientific proposition if materially changed from the inherited target;
- freezing or owner-authorizing a one-shot scientific protocol when governance requires the owner;
- spending a qualifying model/network invocation;
- sealing/revealing the qualifying scientific bank when that step is an irreversible owner gate;
- introducing a new external credential, provider authority or paid resource not already authorized;
- weakening a threshold, minimum, control, isolation boundary or negative-result rule after observing
  qualifying data;
- editing or rerunning any closed M115–M119 scientific record.

When one of these is reached, present the owner with a compact decision packet: exact commit, what is
frozen, what irreversible action is proposed, what preflight passed, what can still fail, and the
claim that would be permitted under each outcome.

## Efficiency guidance

The repository has already been audited heavily. Avoid spending cycles on broad repository tours after
the initial state verification. Use this loop:

1. read `PROJECT_STATE.md`, `PROJECT_STATE.yaml`, `docs/CURRENT_RESEARCH_FRONTIER.md` and M119 outcome;
2. inspect only predecessor modules needed for the successor;
3. turn R1–R6 into executable gates;
4. implement the smallest design that can satisfy those gates;
5. run targeted adversarial tests;
6. run full CI once the targeted surface is green;
7. hostile-review the diff, not the whole history;
8. fix only prospective/pre-freeze defects;
9. prepare the owner decision packet.

Do not add complexity unless it closes a named failure mode. M118 already demonstrated that an
instrument that needs repeated conceptual repair before one-shot use is itself a warning sign.

## Definition of “ready for owner authorization”

The successor is ready to ask for a qualifying scientific spend only when all of these are true:

- successor hypothesis/proposition registered prospectively;
- publication/governance disposition handled in the correct order;
- generator/host acceptance equivalence demonstrated mechanically;
- bank adequacy is checked pre-seal/pre-reveal without content selection;
- checker re-derives the decision-relevant plan;
- checker authenticates and scores the same canonical evidence bytes;
- exact direct success/replay entry point passed DEVELOPMENT rehearsal from a clean checkout;
- substitution/adversarial tests fail closed;
- repository integrity, sealed boundary, Python 3.11 and Python 3.13 CI are green;
- no unresolved Tier-1 review finding remains;
- no qualifying successor invocation has yet been spent.

At that point, stop and ask Anthony for the irreversible authorization rather than continuing on your
own.

## Primary sources

- `PROJECT_STATE.md`
- `PROJECT_STATE.yaml`
- `docs/CURRENT_RESEARCH_FRONTIER.md`
- `experiments/M117/STAGE1_OUTCOME.md`
- `experiments/M118/OUTCOME.md`
- `experiments/M119/OUTCOME.md`
- `experiments/M119/ANALYSIS_PLAN.json`
- `scripts/check_m119_result.py`
- `metamorphosis/carrier_host.py`
- `IP_ASSET_REGISTER.md`
