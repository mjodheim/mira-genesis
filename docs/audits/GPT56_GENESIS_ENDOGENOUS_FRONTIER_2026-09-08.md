# GPT-5.6 Genesis hostile review — endogenous frontier, 8 September 2026

Status: prospective engineering review. This creates no scientific observation, reinterprets no frozen result, and moves no gate.

The controller/authority hardening materially changes the frontier. The runtime now owns architectural sequencing, acquired component/feature machinery is executable, causal ablations are runtime-derived, the evaluator/task boundary is substantially harder to rewrite, checkpoints are recoverable, and lineage-owned mechanism code can be kept outside the evaluator process.

Those are real apparatus gains. They also make the next gap easier to state precisely: **the program still does not generate or persist the machinery that chooses its own transformations.**

## E1 — the controller mechanism is called lineage-owned but is not part of the persistent lineage

`controller.run(genesis, world, mechanism)` receives the mechanism from its caller. The mechanism is content-addressed for an invocation and its digest is written into the controller run record, but neither `LineageState` nor `Genesis.checkpoint()` binds it.

Consequently a process can run under mechanism A, persist, die, restore the same state/body/journal/budget/evaluator, and then continue under mechanism B without an adoption, migration or re-admission transaction. The body is protected against exactly this substitution; the acquisition/controller machinery is not.

A valid repair may take either of two forms:

- persist and adopt a `MechanismArtifact` as lineage state; or
- reclassify the Python mechanism as immutable host executor code and move the mutable decision policy into a content-addressed lineage-owned `AcquisitionPolicyArtifact` that the executor interprets.

What is not sufficient is a run record saying which callback happened to be supplied.

## E2 — transformation generation/search is still host preinstallation

`Transform.body` is a string reference. `_transform()` resolves it only through `World.artifacts`. The DEVELOPMENT demonstration preinstalls `regressed`, `improved`, `generation_2`, `generation_3`, `generation_4` and the migration translation as importable host artifacts.

The lineage therefore chooses among candidates that already exist in the host world. It does not yet construct a new executable candidate artifact. This is explicitly acknowledged in the controller source and is directly inside the objective: `METAMORPHOSIS_TARGET.md` requires **transformation generation and search**, not only selection from an authored menu.

The next mechanism should make candidate identity exact while keeping code transport inert. A bounded declarative program/IR is preferable to executable deserialisation: the lineage can generate canonical data, the evaluator can content-address it, and a fixed sandbox-side interpreter can execute it after limits exist.

## E3 — the acquisition machinery cannot yet be adopted as a descendant

The intent vocabulary can transform the body, acquire a component, extend diagnostic vocabulary, migrate, or stop. There is no evidence-backed transaction by which the lineage changes the policy/mechanism that proposes later intents.

This matters because M108/M109 are not merely repeated body improvements. Their substantive property is depth: a lineage-held attribution/acquisition rule changes, and the changed machinery produces the next modification. The integrated program must carry that property as runtime state rather than inherit it from the host function that drives the controller.

## E4 — restoration still relies on a caller to resolve the executable body

Checkpointing authenticates the body artifact and refuses a different body, which is a major improvement. But `Genesis.restore(..., body_factory=...)` still requires the caller to provide the executable object. That is adequate for DEVELOPMENT importable fixtures; it is not yet enough for an endogenously generated body.

Generated descendants need a persistent content-addressed artifact store (or equivalent exact package/blob store) so process death restores the artifact the checkpoint names rather than asking a caller to recreate it from outside the lineage.

## E5 — the demonstration is integrated but the strategy remains a fixed host programme

The demonstration script now correctly delegates effects and state transitions to `genesis.controller`. It no longer *is* the architecture. But its `PROGRAMME` is still a fixed tuple, and `mechanism(context)` is a deterministic lookup into that tuple. The file says this explicitly.

That means the current demonstration establishes integrated execution, not endogenous search. This is an honest DEVELOPMENT result and should remain described that way until a lineage derives at least one transformation from its own observation/diagnosis rather than reading the next prepared intent.

## E6 — the lineage-owned mechanism cannot inspect the evidence the lineage says it retained

`LineageContext` exposes component names, vocabulary names, acquisition names, a count of observations, budget remaining, evaluated-task-set digests and current body identity. `observations` is an integer. The mechanism does not receive the retained rejection records, verdict reasons, probe evidence or acquisition certificates as inert data.

That is enough for the demonstration's fixed programme: its next step can be selected from counters. It is not enough for endogenous hypothesis formation. A mechanism cannot read *why* the last candidate failed and choose a new candidate because of that evidence; the history is retained by the runtime but opaque to the lineage policy that is supposed to learn from it.

The repair must not hand the mechanism live state/journal references. It should expose a bounded immutable `LineageView`: canonical evidence summaries or digests plus a read-only inert content store, excluding graders, withheld answers, runtime services and mutable capability handles.

## Repair order

1. Decide the identity boundary: immutable executor + mutable policy artifact is the smallest safe design.
2. Put the current policy/mechanism identity into persistent lineage state/checkpoint and refuse substitution after restore.
3. Give that policy a bounded immutable evidence view rich enough to condition the next hypothesis on retained failures/experiments.
4. Add a canonical generated-candidate representation whose exact data digest is executable identity.
5. Add a bounded search/generation operation that produces candidate artifacts from lineage observations/diagnoses under budget.
6. Evaluate and adopt/reject those artifacts through the existing trust-root path; do not give the generator evaluator authority.
7. Add an evidence-backed policy/machinery update so an acquired machinery change can produce the next search/modification.
8. Persist generated body + policy artifacts and demonstrate process-death restoration without caller reconstruction.
9. Only then replace the fixed demonstration programme with a searched one and ask whether the metamorphosis stopping criterion is actually met.

## Current reading

Genesis has moved past "a bag of primitives" into a real integrated runtime. The remaining gap is no longer primarily orchestration. It is **endogeneity**: who constructs the next executable candidate, what retained evidence that process can actually read, and who owns the machinery that decides what to try next.

Closing that gap is now more valuable than opening another generality milestone.