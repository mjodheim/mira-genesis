# M020 — Status

**CONTROLLED SELF-REWRITE DEVELOPMENT BASE PASSED**

## Implemented and verified

- a bounded, terminating Python policy language;
- exact rejection of imports, calls, attributes, loops and other unsafe syntax;
- serialisable constant, arithmetic-operator and comparison-operator edits;
- deterministic beam search over candidate source bodies;
- candidate selection from development cases only;
- held-out evaluation kept outside the rewrite engine;
- strict-improvement adoption;
- stale-result protection through baseline digests;
- byte-exact source archive and rollback;
- absorption of an accepted multi-edit trace as a reusable learned tool;
- a task that requires two independent source edits;
- held-out transfer after selection without held-out answers entering the engine;
- deterministic replay of the selected source, trace and candidate count;
- refusal to replace a body that already reaches the development optimum.

## Verification

The complete repository CI passed on Python 3.11 and Python 3.13 at commit
`cf7c5fd93662198e0ff7313eb3436da8f0867cf7`. Importability, orphan-module and
dependency audits also passed.

CI exposed and helped correct one real implementation defect before this status was
assigned: proposal targets were enumerated in breadth-first AST order while patches were
applied in depth-first order. The mismatch allowed the first edit to succeed but made a
second structural edit address the wrong node. Proposal and application now share one
explicit preorder traversal.

## What this establishes

Within the bounded policy language, Mira can:

1. search modifications to executable source that controls its behaviour;
2. perform those modifications through tools represented in its own registry;
3. select a strict improvement without access to held-out answers;
4. adopt the new body while archiving the parent exactly;
5. roll back to the previous code and behaviour;
6. absorb the successful multi-edit transformation as a reusable internal tool.

This is the first verified executable self-rewrite base in the repository.

## Not implemented

- candidate subprocesses with operating-system resource limits;
- arbitrary multi-file repository rewriting;
- autonomous fault diagnosis;
- test generation;
- invention of new AST operation types;
- mutation of the rewrite engine itself;
- cross-substrate embodiment of the rewritten policy and tool registry;
- long-horizon lineage comparison;
- repeated independent improvement cycles;
- a frozen or canonical protocol.

## Scientific status

**DEVELOPMENT GATES PASSED.** This demonstrates bounded, reversible and proof-gated
self-rewrite. It does not establish open-ended intelligence improvement or complete
self-metamorphosis. The next required layer is a disposable multi-file workspace with
resource-limited candidate execution and an unchanged external release boundary.
