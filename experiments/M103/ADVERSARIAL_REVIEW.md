# M103 pre-freeze adversarial review

Status: **clean implementation candidate; not frozen; canonical qualification not executed**  
Review date: 2026-08-24  
Scientific track: Track A, bounded mechanism evidence

## Scope and non-result boundary

This review attacks the M103 implementation against H48 and every falsifier in
`PRE_REGISTRATION.md`. It covers exact M102 migration, S0 closure, constructor-feature enumeration,
S-prime serialization, later configuration/filesystem acquisition, process death, fresh-lineage
parity, refusal, causal controls, predecessor retention, rollback, replay and the independent
checkers.

No M103 canonical qualification has run. `PROTOCOL.json`, `RESULT.json` and `CHECK_REPORT.json` are
absent. End-to-end executions cited here are DEVELOPMENT rehearsals over the complete pre-freeze
apparatus. They are apparatus validation, not evidence for H48 and cannot fill D072.

## Named pre-freeze amendments and falsifiers

### A1 — named producer PIDs escaped the stable projection

The first two DEVELOPMENT rehearsals passed P1-P14 but retained three differently named producer
PID fields in the stable projection, making P15 false. The raw evidence was correct; the recursive
projection implemented only exact-key removal.

Correction before freeze: runner and independent checker now exclude every key ending in `_pid` or
`_pids`, while raw evidence keeps those values. This is recorded separately in `FAILURE_LOG.md`.

### A2 — the first feature interpreter contained an all-features magic switch

The initial constructor implementation effectively treated the winning four-feature set as one
host-side Boolean gate. That could make the serialized feature list decorative and would collapse
the claim into selecting a prewritten transformation.

Correction before freeze: each token now performs a distinct executed step: context observation,
equality partitioning, per-partition synthesis, and guarded emission. Removing any one feature
restores the no-candidate result. The boundary audit executes all four ablations and rejects any
runtime containing an exact winning-set literal.

### A3 — the more-budget arm was initially a label, not additional work

The first runner called the S0 baseline once and described it as more budget. That could not rule
out retry or accounting explanations.

Correction before freeze: the isolated process repeats the complete S0 constructive image exactly
32 times, records total assembled candidates, and requires every repeated image to be identical.
The control remains a reach test: repeated enumeration cannot add context access.

### A4 — S0 closure was initially self-certified by the mechanism

The runtime's own closure report could agree with its own bug. Structural impossibility therefore
lacked an independent implementation.

Correction before freeze: a separate checker imports neither M103 runtime nor search, independently
executes the complete finite S0 image for development, configuration and filesystem demands, and
certifies the context-invariance witness.

### A5 — predecessor conservation was partly structural-only

The first M103 conservation report executed arithmetic probes but treated M101 A/B and M102 C
mainly as valid definition shapes. A dead retained mechanism could have passed P1/P10.

Correction before freeze: a separately copied execution-only M102 capsule now consumes the exact
M102 bytes embedded in V3 and executes seven fresh M103 probes: record policy K, real SQLite C,
M101 A, M101 B and all three M100 operations. Every process must be isolated, import no repository
module, report zero external calls and pass every case. The local runtime report is now explicitly
labelled structural-only.

### A6 — the producer runtime named the exact accepted feature subset

Even though acquisition did not consult it, the first runtime exposed a `REQUIRED_FEATURES`
constant equal to the four winning tokens. Its presence supplied the simplest alternative
explanation: the target subset was authored in the producer capsule.

Correction before freeze: the constant was removed from the production runtime. Acquisition only
enumerates every subset of the seven-token generic vocabulary up to size four and validates each on
observable DEVELOPMENT behavior. The expected set exists only in external validators and causal
controls. Static AST audit rejects an exact winning-set collection literal in the producer runtime.

### A7 — zero external-call provenance was asserted but not decisive

The process envelopes reported model/network/remote counters, but P15 initially relied mainly on
top-level zero literals written by the result builder.

Correction before freeze: P1/P14/P15 now require isolated predecessor executors, empty project
imports and aggregated zero external-call counters across every runtime scientific invocation.
Capsule membership remains digest-bound separately.

None of A1-A7 follows a scientific result. No canonical attempt existed, no qualification verdict
was observed and the qualification pool was not replaced or redrawn.

## Shortcut, leakage and authority audit

The current fail-closed audit verifies that:

- exact M102 U2 bytes are embedded unchanged in V0-V3;
- S0 actions never receive context and its complete finite image is independently closed;
- S-prime acquisition receives no target body, target digest, solution label, qualification pool or
  future demand;
- the producer runtime contains no exact accepted-feature-set constant;
- all 98 bounded feature subsets are assembled and behaviorally evaluated;
- all four adopted features are separately operational and causally necessary;
- serialized S-prime contains no DEVELOPMENT values/action ids or future carrier identities;
- configuration/filesystem records are materialized only after the preceding producer returns;
- the pool contains no DEVELOPMENT producer identity or constructor solution identity;
- fresh, equal-budget and 32-repeat S0 arms use the same predecessor, runtime, observations and
  action catalogues;
- ambiguity yields multiple semantic signatures and refuses without state change;
- compiled D/E behavior is honestly reported as independent of S-prime after compilation, while
  later acquisition requires live S-prime;
- configuration and filesystem actions operate only through evaluator-owned bounded adapters;
- filesystem paths are relative, reject `..`/absolute escape and execute in disposable roots;
- corruption fails closed and rollback restores exact accepted bytes;
- result and checker paths remain absent and the canonical writer requires final protocol plus a
  separate explicit owner authorization.

The isolated producer capsule does contain the authored generic runtime and the declared carrier
adapters, as explicitly allowed by the pre-registration. It does not contain the pool, runner,
result checker, repository root or future demand/world files. M103 therefore tests demand-data
separation and causal state reuse, not experimenter blindness or independent task authorship.

## DEVELOPMENT rehearsal only

After A1-A7, two complete non-canonical rehearsals computed P1-P15 true and produced identical
stable projections:

- stable DEVELOPMENT evidence digest:
  `967a038919e765aa3969bf3d3a94b8bc89288235aed320119274d087037bf7a3`;
- model calls: 0;
- network calls: 0;
- remote-execution calls: 0.

This digest is not a predicted canonical result and is not a qualification commitment. It only
shows that the frozen-shape apparatus can execute deterministically before owner review.

## Residual ceiling and claim boundary

Even a future 15/15 result would show only a bounded, project-authored acquisition-machinery
improvement. The seven-token feature vocabulary, subset bound, lower interpreter, observations,
action primitives, carrier adapters, tasks, evaluator and objectives remain authored. S-prime
constructs closed dispatches over public context values; it does not discover open-ended interface
semantics or invent its own task.

The strongest permissible positive reading is: **an acquired serialized constructor extension
causally increases later bounded acquisition reach across two project-authored software carriers
and remains reusable after process death**. It would not establish self-hosting, recursive or
open-ended self-improvement, independent task authorship, G1-G10 closure, general-agent evidence,
AGI, independent reproduction or production authority.
