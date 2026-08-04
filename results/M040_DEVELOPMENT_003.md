# M040 development result 003 — exact continuation frontier did not transfer

**Status: consumed negative development result. Not canonical.**

Evaluated head: `c8efe6b455ebba9ac42240f2b3787ded99a1732d`  
Development seed: `400043`  
Workflow run: `30918838375`  
Mechanism: the v4 hardening patch, syntax-normalised by the v6 workflow.

The strengthened mechanism compiled successfully and entered the real M040 execution. It
completed the pre-migration lineage, opaque migration and packet construction/rehydration.
It then failed before revealing a post-migration task:

```text
M040EngineError: no transported continuation frontier produced an admissible task
```

The new pre-migration lineage ended with a seven-state migrated parent. Its transported
continuation programs were valid registry programs, but none simultaneously:

- produced a strictly larger minimal DFA on that parent;
- remained unreachable by the birth registry at the committed depth;
- yielded a sound structural-incapacity certificate from the committed observations.

No post-migration target, control comparison, adoption or rollback result was produced.
Seed `400043` is consumed for this exact task-family mechanism.

## Interpretation

The result does not refute trans-substrate continuity. It reveals that replaying an exact
previously adopted tool sequence is too rigid as a general transfer family: a sequence can
be load-bearing on one body and cease to define a useful next task on another body.

The next repair must preserve the causal pre-migration continuation as a prefix while
allowing one new protocol-supplied operation to be discovered after migration. The packet
must not contain that new operation or the resulting target. This tests reuse plus bounded
adaptation rather than literal repetition.
