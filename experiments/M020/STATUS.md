# M020 — Status

**CONTROLLED SELF-REWRITE KERNEL IN DEVELOPMENT**

## Implemented

- a bounded, terminating Python policy language;
- exact rejection of imports, calls, attributes, loops and other unsafe syntax;
- serialisable constant, arithmetic-operator and comparison-operator edits;
- deterministic beam search over candidate source bodies;
- development-only candidate selection;
- held-out evaluation kept outside the rewrite engine;
- strict-improvement adoption;
- stale-result protection through baseline digests;
- byte-exact source archive and rollback;
- absorption of an accepted multi-edit trace as a reusable learned tool;
- targeted tests for safety, two-edit repair, held-out transfer, archive, rollback,
  learned-tool replay, non-adoption and determinism.

## Not implemented

- candidate subprocesses with operating-system resource limits;
- arbitrary multi-file repository rewriting;
- test generation;
- invention of new AST operation types;
- mutation of the rewrite engine itself;
- cross-substrate embodiment of the rewritten policy;
- long-horizon lineage comparison;
- a frozen or canonical protocol.

## Scientific status

**No result yet.** The branch must pass the repository CI before this kernel can be
considered a valid development base. Even if it passes, it demonstrates bounded
self-rewrite only, not open-ended intelligence improvement.
