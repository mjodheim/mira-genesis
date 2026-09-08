# Genesis endogenous search — architecture candidate

Status: DEVELOPMENT engineering design, 8 September 2026. No scientific claim or gate movement.

## Problem

The integrated controller now owns effects, but the thing choosing the next effect is still supplied by the host as a Python callback. The demonstration's callback indexes a fixed host-authored `PROGRAMME`, and body transformations resolve only through host-populated `World.artifacts`.

That is a good integrated-runtime demonstration. It is not yet the metamorphosis stopping criterion, which requires transformation generation/search and progressive modification of the acquisition machinery in the persistent lineage.

The next step should add endogeneity **without reopening evaluator authority**.

## Design choice: keep an immutable executor, make the mutable policy data

Do not make the controller itself self-modifying Python. That would recreate the authority problem just closed.

Split the current `mechanism` concept into:

1. **ControllerKernel** — host/apparatus code. Resolves no hidden answer, cannot award a verdict, and performs only validated intent execution. Its identity is admitted like other evaluator apparatus.
2. **AcquisitionPolicyArtifact** — lineage-owned, content-addressed canonical data. This is the mutable machinery that maps a bounded read-only lineage view to a declarative search/diagnosis/transformation intent.

A fixed interpreter can execute a policy artifact inside the isolated worker. The policy changes; the interpreter does not.

This matches the useful property of M108/M109 more closely than swapping arbitrary Python callbacks: the attribution/acquisition rule is lineage state, and a changed rule can produce the next change.

## 1. Persistent policy identity

Add to `LineageState` (or an explicitly bound runtime checkpoint field):

```text
policy_artifact:
  schema
  language/version
  canonical_program
  dependencies
  provenance
  artifact_digest
```

The current policy digest must be part of every checkpoint. Restore loads the exact artifact by digest. A caller supplies a resolver/store, not a replacement policy.

Changing policy requires an adoption transaction with its own evidence record. Process death is never an implicit policy update.

## 2. Read-only lineage evidence, not just counters

The present `LineageContext` gives the mechanism component/vocabulary names, acquisition names, observation **count**, budget remaining, evaluated-set digests and body identity. It does not give the retained rejection reasons or experiment evidence on which a new hypothesis could be based.

Expose a bounded immutable `LineageView` containing content-addressed evidence summaries, for example:

- recent rejected-candidate records and verdict digests;
- task-family failure/retention summaries with no withheld answers;
- component/feature artifacts and their certificates;
- probe/diagnosis summaries;
- migration capability record;
- current body and policy artifact digests;
- remaining budget.

Never expose live `Genesis`, mutable state dictionaries, grader, answer keys, journal service or capability callables.

If full evidence is large, the view can contain digests plus a read-only content store whose query surface returns inert canonical values.

## 3. Generated executable candidates as canonical data

The first generated-body format should be deliberately bounded and exact, not arbitrary Python source.

A minimal `ProgramArtifact` can be an expression/operation IR:

```text
program-v1
  inputs: named task fields
  nodes:
    - input(field)
    - constant(value)
    - call(operation, args...)
  root: node id
  declared_dependencies: [...]
```

The canonical JSON bytes are the body identity. A fixed sandbox-side interpreter executes them only after isolation exists. No pickle, `eval`, `exec`, dynamic import or candidate-controlled deserialiser is needed.

The operation vocabulary may initially be the same bounded registry already used by the probe apparatus. Later, certified acquired components can contribute operations through their state-held artifacts.

This is genuinely a new executable body even though the interpreter is fixed, in the same way bytecode is a program even though the VM is not rewritten for every program.

## 4. Content-addressed artifact store

Generated descendants must survive process death without a host recreating them.

Add an append-only artifact store keyed by full digest. A checkpoint names:

- current body artifact digest;
- current policy artifact digest;
- acquired component/feature artifact digests;
- journal/state payloads as today.

Persistence writes artifact bytes before publishing the manifest. Restore reconstructs body/policy from the store and verifies exact digest equality.

Importable DEVELOPMENT fixtures may remain supported as a weaker artifact kind, but a generated-program claim should use exact canonical bytes.

## 5. Bounded transformation generation and search

Add a declarative intent such as:

```text
SearchTransform(
  objective=<diagnosed evidence digest>,
  grammar=<admitted program language/version>,
  max_candidates=N,
  max_nodes=M,
  required_dependencies=[...]
)
```

The policy chooses **why and where to search** from lineage evidence. The executor enumerates or samples candidates deterministically under the declared budget and gives every candidate to the existing isolated evaluator/trust-root path.

Important separation:

- the generator may construct candidate programs;
- it never sees withheld answers or the grader;
- it never decides acceptance;
- failed/rejected candidates return as observations available to the next policy step;
- search spend is charged to the lineage budget.

The first bounded demonstration can use exhaustive enumeration over a tiny grammar. Search sophistication is not the claim. Endogenous candidate construction is.

## 6. Evidence-backed acquisition-policy change

Add a policy-update transaction only after generated body search works.

A candidate policy is evaluated by what it causes the lineage to produce under a matched meta-evaluation:

1. snapshot the same `LineageView`;
2. give current policy and candidate policy the same search budget and same allowed grammar;
3. let each generate intents/candidate programs in isolated workers;
4. evaluate resulting descendants under the unchanged trust root;
5. require retention and a declared improvement criterion;
6. adopt candidate policy only through a trust-root-backed policy verdict;
7. journal the policy artifact and evidence.

The policy must not grade its own descendants. The final measure remains outside both policies.

For M109-style recursive depth, a later policy modification must depend causally on an earlier policy acquisition. The same structural-ablation principle applies: remove the earlier policy feature/dependency, rerun the later meta-evaluation at equal budget, and show the loss.

## 7. Demonstration transition

Do not replace the current fixed demonstration immediately. Keep it as a controller integration regression.

Add a second DEVELOPMENT demonstration that starts from:

- a seed body that fails some visible questions;
- a seed policy artifact;
- a bounded operation grammar;
- no preinstalled improved body artifact.

A successful run should show, in one lineage:

1. parent measurement exposes a limitation;
2. the retained evidence reaches the policy view;
3. the policy asks for bounded candidate search;
4. the runtime constructs at least one new `ProgramArtifact` not present at admission;
5. candidates run under the immutable evaluator contract;
6. one is adopted or all are rejected and retained;
7. after process death, the generated body is restored from the artifact store;
8. a later evidence-backed policy change alters the next search;
9. the lineage continues after a substrate/body transition.

Only after that should the fixed `PROGRAMME` cease to be the primary metamorphosis demonstration.

## Negative controls that must exist

- replacing the policy after restore without an adoption must fail;
- changing one byte of a generated program must change/refuse its identity;
- a program artifact missing from the store must make restore fail closed;
- a generator attempting to access grader/answer-key data must have no reference/path to it;
- a policy update that produces no better descendants must be rejected;
- a policy update that loses previously retained capability must be rejected;
- a later policy claim whose ablation costs nothing must not count as recursive depth;
- search must stop at its declared candidate/node/budget bound;
- two identical runs from the same checkpoint and deterministic search seed must reproduce artifact and verdict digests.

## What this would establish

This design would close the most important distinction left in the current DEVELOPMENT apparatus:

**selection from a host-authored programme** → **persistent lineage-owned policy generating new executable candidate artifacts and changing that policy on evidence**.

It still would not imply open-ended evolution or general intelligence. It would, however, directly target the repository's empirical-metamorphosis stopping criterion instead of adding another surrounding gate.