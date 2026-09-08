# Genesis runtime — round-two repair design

Status: engineering design for the blockers in PR #277. This is not a scientific protocol and moves no gate.

The repair order matters. The round-one hardening showed why: persistence cannot preserve identity that has not been defined, and a causal ablation cannot be authenticated while an acquisition is only a name. The second hostile pass adds an even earlier dependency: a read-only object is irrelevant if lineage-owned code still shares the interpreter that implements the evaluator. Establish the authority boundary first, then define semantic identities, then build the workflows on top of them.

## 0. Put lineage-owned search/proposal code behind a real authority boundary

`LineageContext` is useful data minimisation, but it is not isolation. A Python callback running in the host interpreter can import mutable modules, monkey-patch evaluator globals, write files, inspect objects through `gc`, and mutate any task object handed to it.

The proposer/search mechanism should therefore execute in a separate constrained process and return only a declarative value, for example a `ProposalIntent` containing content-addressed artifact references plus rationale/provenance. It must never return live callables with ambient host authority and must never share the interpreter that holds the trust root, journal, budget or evaluation functions.

The evaluation corpus must also be frozen once, before the parent arm:

- canonicalise every evaluation-relevant task field;
- keep one immutable parent-owned snapshot for all arms;
- bind each outcome row to a canonical question digest as well as a cosmetic task ID;
- give proposal/search code only a detached problem context, with grading secrets withheld;
- reject any arm whose question digests differ from the admitted evaluation set.

The parent, candidate and control must therefore differ only in the artifact being evaluated, not in the work or measure they face.

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
- admitted isolation policy relevant to comparison;
- sandbox/evaluation apparatus identity when that code is outside the immutable trust-root source file.

`decide()` should derive these rules from one validated contract value. Remove or reject per-cycle arguments that contradict it. Every arm/result/verdict should name the same contract digest.

In-memory monkey-patching must not be able to replace an admitted evaluator merely because the source file on disk still hashes correctly. The trusted evaluator should resolve from immutable admitted artifacts inside the trusted process, not from mutable module globals after lineage-owned code has run.

## 3. Centralise provenance validation

Create one trust-root validator used everywhere provenance enters a trusted record. It should require:

- recognised provenance class;
- non-empty `produced_by`;
- optional detail as data, not as a substitute for producer identity;
- preferably a versioned provenance schema.

Do not let direct `Mapping` inputs bypass the invariant that the `provenance()` constructor enforces. Do not manufacture `lineage_owned` provenance when a caller omits it: authorship is evidence and must fail closed when unknown.

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

## 7. Harden migration as a capability and identity boundary

### Departure snapshot

Keep an immutable canonical departure snapshot for verification. Give translation code a read-only/deeply detached `MigrationContext`, never the value later used as the intactness baseline.

If translation can become lineage-owned, run it behind the same process/capability boundary as proposal/search code rather than as an unrestricted host callback.

### Discovered capabilities

Do not hand translation code raw Python callables. A callable can expose `__globals__`, closures, module registries and other ambient authority. Use opaque capability handles or an isolated invocation service whose only operation is to invoke the specifically discovered capability.

### Actual use

Derive the operations actually exercised during translation rather than trusting caller-authored `used_operations`. The migration record should be produced from capability-handle usage.

### Translation and arrival identity

Bind the translated body as an executable artifact, not a digest of `{substrate, from, via}` metadata. The arrival `LineageState.body_digest`, migration record and eventual checkpoint must all identify the same translated executable artifact before the runtime switches bodies. Translation provenance must pass the same central validator as every other trusted artifact.

## 8. Restore exactly one committed runtime envelope

A checkpoint should not merely record fields; restore must actually reconstruct each decision-relevant one.

Keep distinct:

- admitted maximum isolation;
- current, possibly narrower, isolation;
- budget limits and spent ledger;
- evaluation contract;
- body artifact;
- state digest and journal head;
- evaluated task-set identities.

Restore the exact committed current isolation by default. A caller may only request a value equal to or narrower than that current value; it must not widen back to the admitted ceiling merely because the ceiling is still legal.

## 9. Move architecture transitions into one runtime controller

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

## 10. Re-run the hostile apparatus only after the baseline is green

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

Closing these blockers would still not be scientific evidence for generality or AGI. It would do something more relevant to the current frontier: make the integrated Genesis runtime substantially closer to the repository's own stopping criterion — a continuous lineage whose acquired machinery is executable, whose measure is immutable in fact rather than in name, whose causal links are structurally testable, whose evaluation corpus cannot be rewritten between arms, and whose architecture changes are performed by the runtime rather than by an unrestricted demonstration driver.
