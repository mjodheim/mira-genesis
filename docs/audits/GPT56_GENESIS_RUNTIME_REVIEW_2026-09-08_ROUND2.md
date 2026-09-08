# GPT-5.6 Genesis runtime hostile review — round 2, 8 September 2026

Target: the post-hardening PR #275 head from which this review branch was created. The exact commit identity remains in pull-request metadata; this note is engineering review, not a scientific record.

The first hardening pass materially closes the persistence, evaluator-binding, retention, task-identity, journal-copying, provenance and proposer-authority counterexamples encoded in PR #276. This round therefore does not reopen those findings casually. It asks whether the stronger properties now claimed actually follow from the repaired mechanisms.

## R2-1 — causal ablation is still caller-authored

The hardening rejects an ablation whose `depends_on` names an acquisition the lineage never held. That closes the exact first counterexample, but not the stronger property. If the lineage *does* hold an acquisition named `real_prior`, the proposer may still supply any deliberately weak `ablated_body_factory`, label it as `depends_on="real_prior"`, and obtain a measured loss. Nothing reconstructs the candidate with exactly that acquisition removed.

Expected repair shape: the runtime derives the ablated artifact structurally from a content-addressed candidate plus a content-addressed acquisition, or records `established: false` when it cannot prove that relation. Text identity is insufficient.

## R2-2 — migration translator receives the canonical departing record by mutable reference

`migrate()` decodes the current state into `departing`, then calls `translate(departing, ...)`, then constructs the arrival and runs `carried_intact(departing, arrived)`. A translator can mutate the supplied `departing` mapping before the arrival and the comparison are computed. The loss is then present in both sides of the comparison and disappears from `carried_intact`.

Expected repair shape: retain an immutable/canonical departure value for comparison and give the translator a deep, read-only copy or declarative context. Never compare against a value untrusted translation code was allowed to mutate.

## R2-3 — the sandbox task-set guard is reachable through the candidate's frame

The candidate executes inside `_child`. Python code can inspect the caller frame and obtain the mutable `rows` list from `_child`'s locals. A hostile body can append a row for a task it was never given. Therefore the final task-set guard is not merely an unreachable assertion about how `_child` itself constructs rows.

Expected repair shape: keep and test the guard, and ideally isolate candidate execution from mutable parent-frame bookkeeping rather than relying on the candidate not to inspect its caller.

## R2-4 — the probe state-mutation guard is reachable through a hostile Mapping collaborator

`diagnose_by_experiment()` accepts `component_operations: Mapping[...]` and calls `.get()` after serialising `state`. A Mapping implementation can mutate the referenced state as a side effect of `.get()`. The before/after guard is therefore reachable and should have a direct hostile test if the API continues to accept arbitrary Mapping implementations.

## R2-5 — executable artifact identity ignores bound callable state

`artifact_digest_of()` explicitly unwraps `functools.partial` objects to their underlying callable and hashes the module source plus qualified symbol. The bound positional/keyword arguments are discarded. Two zero-argument body factories can therefore execute different bodies while producing the same artifact digest. Because restore relies on that digest, process death can still substitute a different configured body when both are partial applications of the same symbol.

This is a direct reopening of the body-identity guarantee, not merely a theoretical hash weakness. The round-two tests persist one partial body and attempt to restore another with different bound capabilities.

Expected repair shape: artifact identity must include the complete executable configuration that affects behaviour: partial args/kwargs, closure cells, callable-object state where admissible, and eventually exact packaged bytes for lineage-generated artifacts. Unsupported dynamic callables should fail closed rather than collapse to a weak symbolic identity.

## R2-6 — the evaluator contract has the same bound-state collision

The grader is content-addressed through the same `artifact_digest_of()` helper. Two partial graders with the same underlying function but different bound parameters therefore produce the same evaluation-contract digest even when one grades honestly and the other marks every answer solved. Restore consequently cannot distinguish them.

Expected repair shape: the evaluation contract must bind grader semantics, including all bound configuration, and restore must reject any semantic mismatch.

## R2-7 — strict-improvement policy can be overridden outside the contract

`Genesis.__init__()` constructs an `EvaluationContract` with `strict_improvement=True`. `cycle()`, however, accepts a `required_strict_improvement` argument and passes that separate value directly to `trust_root.decide()`. Calling a cycle with `required_strict_improvement=False` can accept a candidate that solved no additional task while the verdict still names a contract whose recorded policy says strict improvement is required.

Expected repair shape: the trust root must derive the decision policy from the admitted evaluation contract, or the per-cycle contract must be rebuilt and admitted under the exact policy actually used. A verdict must not name one measure while using another.

## R2-8 — provenance records still accept a class without a producer

`provenance()` correctly requires a non-empty `produced_by`, but several validation paths only check that `record["class"]` belongs to `PROVENANCE_CLASSES`. A caller can therefore pass `{"class": "lineage_owned"}` into `decide()` and obtain a verdict whose provenance class is recognised while nobody is named as producer. State validation uses the same class-only pattern for several entries.

Expected repair shape: centralise provenance validation and require the same invariant everywhere: recognised class, non-empty producer, and a stable schema if provenance is going to be evidence rather than decoration.

## R2-9 — discovered substrate callables can reveal undiscovered operations

`Substrate.discovered` returns only names that were probed, but the values are raw Python callables. A discovered function can expose its module globals through `__globals__`; with the development substrate, the `read` callable thereby reveals the entire `SUBSTRATE_OPERATIONS` registry including `list`, even when `list` was never probed. The translator can then use that hidden operation while declaring only `read` in `used_operations`.

Expected repair shape: discovered capabilities must cross the boundary through opaque, capability-scoped handles or an isolated invocation interface, not raw Python objects that retain references to their defining environment. The migration record should derive actual capability use rather than trust a caller-authored `used_operations` list.

## R2-10 — control-arm policy is outside the evaluation contract

The target architecture names parent/candidate/control comparison as part of the integrated runtime, but the evaluation contract binds neither whether a control is required nor which control artifact is admissible. Two otherwise identical Genesis instances therefore carry the same contract digest while the same candidate is accepted without a control and rejected when an equal-performing control is supplied.

Expected repair shape: control policy and, when applicable, control identity must be part of the admitted measure. The trust root should not accept caller-selected changes to the comparison rule under an unchanged contract digest.

## R2-11 — an acquired component is certified but not operationalised

The component certificate now correctly preserves the experimentally resolving composition. `extend_components()` then adds the new component name and certificate to `LineageState`, but nothing turns that resolving composition into executable component machinery. Re-running the same demand immediately afterwards with the runtime's existing component-operation source still finds that no held component resolves it; the freshly "acquired" component has no operations unless the host edits an external mapping.

Expected repair shape: the acquisition must produce a content-addressed executable component artifact, bind that artifact to the certificate, install it into lineage-owned machinery, and make later diagnosis consume that state-derived machinery rather than a host-maintained mapping.

## R2-12 — an extended diagnostic vocabulary is also a label, not a later executable feature

`probe.measure()` always emits one boolean per held component. It does not evaluate `LineageState.vocabulary`. After a certified vocabulary extension, the state contains one more feature but later measurements still have the old width. A second extension therefore cannot build on the first without host-side redesign; the representation grew in the record but not in the diagnostic computation.

Expected repair shape: diagnostic features need executable semantics stored or reconstructible from their certificates, and later measurement must evaluate the lineage's current vocabulary from state. This is necessary for progressive modification rather than one-shot naming.

## R2-13 — the DEVELOPMENT demonstration still performs architectural transitions in the host script

The objective requires a loop that runs without human architectural intervention. The demonstration still assigns `genesis.state` directly for vocabulary/component growth and appends the corresponding journal entries from `scripts/run_genesis_demonstration.py`. The runtime owns candidate cycles and persistence, but the host script still sequences material architecture changes between those cycles.

Expected repair shape: move diagnosis, certified vocabulary/component installation, migration intent, persistence and continuation behind a runtime controller whose public driver supplies environment/tasks and receives records. The demonstration should become a thin launcher, not the actor that changes lineage architecture.

## R2-14 — a read-only context is not an authority boundary while the proposer runs in the host process

The round-one repair replaced `propose(self, tasks)` with `propose(self.context(), tasks)`. That removes the obvious object reference but the callback is still ordinary Python running inside the evaluator process. It can write the host filesystem, import mutable Genesis modules, replace `genesis.loop.run_candidate` in memory, or monkey-patch other module globals after the parent arm and before the candidate arm. No source digest changes when a Python function object is replaced in memory.

A concrete counterexample replaces the `run_candidate` global from inside the proposer with a function returning forged all-solved outcomes. The parent was measured by the real evaluator; the candidate is then measured by the replacement, while the verdict still names the original admitted trust-root/evaluation-contract identities.

Expected repair shape: lineage-owned proposal/search code must execute behind a real process/capability boundary and return a declarative intent or content-addressed candidate artifact. It must not share the interpreter whose globals implement measurement, persistence or the trust root.

## R2-15 — the proposer receives the mutable evaluation tasks after the parent arm has already run

`cycle()` evaluates the parent, records the task-set digest, then calls the proposer with the original mutable `tasks` objects, then evaluates the candidate from those same objects. The trust root compares outcome rows by `task_id`, not by the canonical question digest that the task-set ledger uses.

The proposer can therefore rewrite an answer-key/target field after the parent arm, keep every task ID unchanged, and make the same body become correct in the candidate arm. Parent and candidate are then accepted as if they faced the same work although the questions changed between arms.

Expected repair shape: canonicalise the evaluation set once before any arm, keep an immutable parent-owned snapshot, and make every arm bind each outcome to the same question digest. The proposer should receive only a detached task/problem context that cannot mutate the evaluation corpus or grading secrets.

## R2-16 — migration arrival-state identity does not bind the executable body that actually arrived

`migrate()` sets the arrival state's `body_digest` from `{substrate, departing body digest, declared used operations}` rather than from the translated executable artifact. Two distinct body factories that behave identically on the verification tasks therefore create the same arrival-state identity when substrate and declarations match.

The checkpoint later records a body artifact, but the migration event and `LineageState` already claimed an arrival identity before that checkpoint. Which executable body arrived is part of lineage identity and cannot be replaced by metadata describing how it supposedly got there.

Expected repair shape: the translated body's full executable artifact digest must be the arrival body identity and must be included in the migration record before state assignment. Translation metadata can accompany it; it cannot substitute for it.

## R2-17 — restore records the current isolation but restores only the admitted ceiling

The checkpoint contains both `admitted_isolation` and the runtime's current `isolation`. `restore()` reconstructs the admitted isolation and, when the caller supplies none, uses that as the resumed current isolation. The committed current value is ignored. A runtime that narrowed itself before persistence therefore wakes under the wider original ceiling after process death.

Expected repair shape: restore the exact committed current isolation and separately retain the admitted maximum. A caller may request an equal-or-narrower current envelope, never a value wider than the committed current one.

## R2-18 — vocabulary extension can invent lineage ownership when provenance is omitted

`extend_vocabulary()` accepts `provenance=None` and then manufactures `lineage_owned` provenance with producer `lineage vocabulary extension`. In the DEVELOPMENT demonstration the host script directly calls this function without supplying provenance, so host orchestration is recorded as lineage-owned by default.

Expected repair shape: provenance is evidence, not a convenient default. Require an explicit validated provenance record at every boundary where authorship matters; the integrated controller can supply lineage-owned provenance only when the operation actually came through the lineage-owned execution path.

## Mutation-score interpretation

The `sandbox.py` subprocess survivor is environment-sensitive. `RLIMIT_NPROC` can independently block process creation for an unprivileged process, masking removal of the Python audit-hook guard. In a root container, `setrlimit(RLIMIT_NPROC, (0, 0))` may succeed while `/bin/true` still launches. Therefore 70/6 versus 71/5 on identical source can be a platform-dependent mutation result rather than a counting error. Mutation reports should record platform/uid and whether the independent RLIMIT control actually blocks a subprocess.

The missing-operation guard in `probe.py` is only observationally equivalent through the current sandbox outcome path: removing it changes the direct exception from `ProbeError` to `TypeError`. If that direct exception is intended API behavior, test it and kill the mutant. If it is not part of the contract, the documentation should scope the equivalence claim to sandbox-observed outcomes rather than calling the mutant globally equivalent.

## Current round-two disposition

R2-3, R2-4 and the direct missing-operation contract are test-coverage corrections: the guards already reject the hostile case, but the old mutation interpretation understated reachability.

R2-1, R2-2 and R2-5 through R2-18 are mechanism or architecture blockers. They are intentionally encoded as failing counterexamples on the review branch where mechanically expressible. No scientific gate or observation should move until the runtime either closes them or narrows its claims accordingly.
