# Genesis runtime — round-two repair design

Status: engineering design for the blockers in PR #277. This is not a scientific protocol and moves no gate.

The repair order matters. The round-one hardening showed why: persistence cannot preserve identity that has not been defined, and a causal ablation cannot be authenticated while an acquisition is only a name. Fix the semantic objects first, then the workflows that depend on them.

## 1. Make executable identity semantic or fail closed

Replace the current weakest-symbol descriptor with a recursive `ExecutableArtifact` identity.

Minimum supported shapes:

- plain importable function/class: module-source digest + qualified symbol;
- `functools.partial`: recursive identity of the underlying callable **plus canonical bound args and kwargs**;
- packaged/generated body: exact package/blob digest and declared entry point;
- callable instance: class artifact plus canonical immutable configuration, only when that configuration can be reconstructed exactly.

Closures, lambdas with mutable captures, callable instances with opaque state, dynamically monkey-patched objects and C/built-in callables whose behaviour cannot be reconstructed should not silently collapse to a symbolic identity. Either package them into an exact artifact first or refuse to use them where body/grader identity is a trust boundary.

The artifact record should state whether it binds exact executed bytes or a weaker importable-source identity. Restore must require exact equality of the complete admitted descriptor.

## 2. Make `EvaluationContract` the actual decision rule

The trust root should never receive a second caller-authored policy that can disagree with the admitted contract.

Bind at minimum:

- grader artifact;
- outcome vocabulary;
- retention policy;
- strict-improvement requirement;
- control policy (`none`, `required`, or another explicit prospective rule);
- control artifact identity when a fixed control is part of the measure;
- task-identity rule/version;
- admitted isolation policy relevant to comparison.

`decide()` should derive these rules from one validated contract value. Remove or reject per-cycle arguments that contradict it. Every arm/result/verdict should name the same contract digest.

## 3. Centralise provenance validation

Create one trust-root validator used everywhere provenance enters a trusted record. It should require:

- recognised provenance class;
- non-empty `produced_by`;
- optional detail as data, not as a substitute for producer identity;
- preferably a versioned provenance schema.

Do not let direct `Mapping` inputs bypass the invariant that the `provenance()` constructor enforces.

## 4. Turn acquired components into executable lineage artifacts

A component extension certificate currently proves that a resolving composition exists but installs only a component name.

Introduce a content-addressed `ComponentArtifact` containing at least:

- component name;
- exact resolving construction/operation graph;
- executable or reconstructible implementation identity;
- certificate digest licensing the acquisition;
- provenance;
- dependency artifacts, if any.

`extend_components()` should install that artifact into lineage state. Later diagnosis must derive the held component machinery from state, not from a host-maintained `COMPONENT_OPERATIONS` mapping. Repeating the certified demand immediately after acquisition should be resolved by the newly held component without any host edit.

## 5. Turn diagnostic features into executable lineage artifacts

The current `measure()` emits one boolean per component and does not execute `LineageState.vocabulary`. That makes a vocabulary extension one-shot metadata: after adding a feature, later rows remain the old width.

Introduce a versioned `FeatureArtifact` whose semantics are reconstructible from evidence. For the current probe vocabulary, a feature such as `requires_<operation>` can be represented declaratively as an operation-membership predicate over a measured resolving composition.

`measure()` should evaluate the current ordered vocabulary from state. A second vocabulary extension must be able to use the first feature without host code changes.

## 6. Make causal ablation structural

Delete caller authority to supply an arbitrary `ablated_body_factory` as causal evidence.

A proposal should identify the candidate artifact and the acquisition artifact it claims to depend on. The runtime should construct the ablation itself by removing exactly that dependency from a reconstructible candidate configuration, then verify that the resulting artifact differs only in the licensed removal.

If the runtime cannot construct and authenticate the single-difference arm, record `established: false`; do not infer causality from a caller-supplied weaker body.

This becomes practical only after components/acquisitions have executable identities, which is why it follows sections 4–5.

## 7. Harden migration as a capability boundary

### Departure snapshot

Keep an immutable canonical departure snapshot for verification. Give translation code a read-only/deeply detached `MigrationContext`, never the value later used as the intactness baseline.

### Discovered capabilities

Do not hand translation code raw Python callables. A callable can expose `__globals__`, closures, module registries and other ambient authority. Use opaque capability handles or an isolated invocation service whose only operation is to invoke the specifically discovered capability.

### Actual use

Derive the operations actually exercised during translation rather than trusting caller-authored `used_operations`. The migration record should be produced from capability-handle usage.

### Translation identity

Bind the translated body as an executable artifact, not a digest of `{substrate, from, via}` metadata. Translation provenance must pass the same central validator as every other trusted artifact.

## 8. Move architecture transitions into one runtime controller

The repository objective requires a loop that runs without human architectural intervention. The demonstration should not assign `genesis.state` or append component/vocabulary history itself.

Add a controller surface such as `Genesis.step()` / `Genesis.run()` that owns the state machine:

```text
observe
 -> diagnose
 -> propose intent
 -> construct candidate artifact
 -> evaluate under admitted contract
 -> adopt/reject transaction
 -> install certified component/feature artifacts when evidence licenses them
 -> persist checkpoint
 -> continue
```

Migration should enter through the same controller as an evidence-backed transformation intent, not as a host script changing the body between cycles.

The demonstration then becomes a thin environment/task/fixture launcher plus record renderer. It should contain no direct lineage-state assignment and no direct journal mutation for architectural events.

## 9. Re-run the hostile apparatus only after the baseline is green

The round-two tests are counterexamples, not the implementation specification. Close the property, not only the concrete fixture.

After implementation:

1. all `tests/test_genesis_gpt56_round2*.py` pass without weakening;
2. complete Python 3.11 and 3.13 suites pass;
3. repository integrity and sealed-bank boundary pass;
4. the mutation checker first proves the unmutated Genesis baseline green;
5. mutation results record Python/platform/uid and the independent `RLIMIT_NPROC` control;
6. surviving guards receive a fresh classification based on the exact final source and complete suite;
7. the DEVELOPMENT demonstration is regenerated only after those properties hold.

## What this would establish

Closing these blockers would still not be scientific evidence for generality or AGI. It would do something more relevant to the current frontier: make the integrated Genesis runtime substantially closer to the repository's own stopping criterion — a continuous lineage whose acquired machinery is executable, whose measure is immutable in fact rather than in name, whose causal links are structurally testable, and whose architecture changes are performed by the runtime rather than by the demonstration driver.
