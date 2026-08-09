# Mira Genesis — completion criteria

## Frozen phase-one definition

This document defines the first complete bounded form of Mira Genesis. The ten scientific
gates below were established before the M042 canonical result and are not widened by the
later Phase 2 agenda.

Mira Genesis is not complete merely because it can produce code, call an external coding
model or pass one hand-picked benchmark. The first complete form requires one lineage to
satisfy every gate under a frozen protocol.

## Target claim

A Genesis organism can diagnose a limitation in its current cognitive body, construct or
extend the tools needed to change that body, propose and validate a replacement, adopt it
without human architectural intervention, migrate the improved competence to an initially
unknown substrate, preserve relevant memory and plasticity, and continue to improve on
unseen tasks more efficiently than an unchanged lineage.

The claim is bounded to the frozen task and substrate families used by the protocol. It is
not a claim of universal intelligence, consciousness or unlimited self-improvement.

## Gate 1 — autonomous diagnosis

The organism receives outcomes, costs and permitted observations, but no labelled fault
location or prescribed repair. It must identify a limitation that predicts measurable
failure or inefficiency on future tasks.

Evidence:

- the diagnosis is emitted before held-out results are revealed;
- ablating the diagnosed component reproduces the predicted failure;
- changing an unrelated component does not produce the same recovery.

## Gate 2 — internal tool ownership

Every operation used to inspect, transform, build or test a candidate body is present in
the organism's serialised tool registry. External infrastructure may execute a tool, but
may not invent its transformation or choose its arguments on the organism's behalf.

At least one required tool must be constructed or composed by the organism from more
primitive tools during the evaluation lineage.

## Gate 3 — self-rewrite

The candidate differs in executable source, intermediate representation or native body
from the parent. The organism must generate the transformation and its arguments.

Evidence:

- exact parent and candidate digests;
- a serialised transformation trace;
- deterministic replay of the trace from the parent;
- no evaluator or hidden target imported into organism code.

## Gate 4 — isolated validation

Candidates run in a disposable environment with explicit CPU, memory, time, filesystem,
network and syscall limits. A candidate cannot alter the parent, evaluator, test set,
archive or release gate.

A candidate must pass syntax, safety, regression and task checks before it can become
eligible for adoption.

## Gate 5 — held-out improvement

Candidate selection uses development evidence only. A sealed held-out evaluator then
measures the adopted body against its parent and an unchanged control lineage.

Required result:

- strictly better primary held-out quality than the parent;
- no pre-registered critical regression;
- improvement repeated across enough paired seeds for the frozen decision rule;
- total cost includes diagnosis, search, failed candidates, validation and migration.

## Gate 6 — adoption and rollback

The organism adopts the candidate through its own versioned body mechanism. The parent is
archived exactly, and rollback restores both code and behaviour.

The evaluator must force at least one rollback scenario. A lineage that cannot survive a
bad adoption attempt does not pass.

## Gate 7 — complete trans-substrate metamorphosis

After improvement in substrate A, the organism receives substrate B with undeclared
semantics. It must:

1. discover the permitted operational semantics by probing;
2. construct a native body for B;
3. transfer the improved competence;
4. transfer the tool registry required for later self-change;
5. transfer relevant memory, uncertainty and exploration state;
6. preserve the capacity to learn and rewrite after migration.

No human may redesign the architecture for B or provide a task oracle during migration.

## Gate 8 — post-migration plasticity

On a new task family revealed only after migration, the migrated lineage must improve
faster or to a higher exact quality than:

- a fresh organism on B;
- the unchanged parent lineage migrated to B;
- the improved lineage with its learned tools or memory ablated.

This gate distinguishes transported output from transported intelligence.

## Gate 9 — repeated improvement cycles

One successful rewrite may be a lucky repair. The same lineage must complete at least
three accepted improvement cycles separated by genuinely new held-out task families.

At least one later cycle must reuse or extend a tool learned in an earlier cycle.

The full lineage must remain replayable from the original seed and immutable inputs.

## Gate 10 — measurement integrity

The protocol, generators, thresholds, seed commitments, cost accounting and decision rule
are frozen and hashed before the canonical run.

The canonical workflow runs once on an immutable commit. Failures, contaminations and
negative results remain in the repository. No rerun replaces a first attempt and no
threshold is relaxed after observation.

## Engineering release boundary

Even after all scientific gates pass, real repository writes, deployments, credentials,
network access and production changes remain behind an explicit human-controlled release
boundary. Scientific autonomy inside a sandbox does not imply permission to modify
external systems.

## Completion record

**Phase-one status: completed in the bounded deterministic binary-DFA laboratory.**

M042 is the first experiment whose continuous frozen lineage satisfies all ten audited
gates together. Its unique canonical workflow selected one task from a pre-verified
constructive bank, reached 127/127 exact observations, kept all equal-budget control arms
non-exact, passed passive isolated validation, synthesised the accepted rewrite natively
on the discovered opaque substrate and rolled back a fixed provisional failure exactly.

Gate 10 is supported by the separate immutable first-result seal and post-preservation
audit. The raw result itself was not rerun, rewritten or retuned. M041's negative first
attempt remains preserved as a separate experiment and was not replaced.

The authoritative evidence is:

- [`experiments/M042/STATUS.md`](experiments/M042/STATUS.md);
- [`results/M042_CANONICAL_RESULT.md`](results/M042_CANONICAL_RESULT.md);
- `results/artifacts/M042_CANONICAL_RESULT.json`;
- `results/artifacts/M042_CANONICAL_FIRST_RESULT_SEAL.json`;
- `results/artifacts/M042_CANONICAL_AUDIT.json`.

## Claim boundary after completion

Completion of these criteria does not authorise a universal or open-ended interpretation.
The result remains bounded to the frozen deterministic finite task and substrate families,
127-observation evaluations, symbolic depth four and 4,096-node search budgets recorded
by M042.

Phase 2 is a separately governed research program. M043 may test whether the architecture
can be reconstructed in a deterministic Mealy-machine domain, but it cannot retroactively
widen the M042 claim or change these phase-one gates.

## Phase-two real-substrate confirmation

M066 later confirmed the same ten bounded gates on the separate CPython → Node ESM → whole-
WebAssembly construction path. Its unique run `31291899534`, attempt 1, selected bank zero from a
four-entry commitment, accepted three post-migration whole-body rewrites and reached 18/18 hidden
observations against 0/18 in all three equal-budget controls. Python 3.13 independently reproduced
the exact Python 3.11 result bytes.

This does not rewrite the frozen phase-one record or make the claim open-ended. It supplies a
second, more realistic bounded confirmation with authored compiler structure, finite grammar,
precommitted task families and explicit resource limits. Its authoritative evidence is:

- [`experiments/M066/STATUS.md`](experiments/M066/STATUS.md);
- [`results/M066_CANONICAL_RESULT.md`](results/M066_CANONICAL_RESULT.md);
- `results/artifacts/M066_CANONICAL_RESULT.json`;
- `results/artifacts/M066_INDEPENDENT_REPRODUCTION.json`;
- `results/artifacts/M066_CANONICAL_FIRST_RESULT_SEAL.json`;
- `results/artifacts/M066_CANONICAL_AUDIT.json`.
