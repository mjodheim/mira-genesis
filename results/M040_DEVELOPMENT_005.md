# M040 development result 005 — no admissible task under full-prefix adaptation

**Status: consumed negative development result. Not canonical.**

Evaluated head: `8ae968ee2909dcd0fcb39a77fb6dbaa76b201384`  
Development seed: `400045`  
Workflow run: `30920406724`  
Equal symbolic-node budget: `4,096`

The calibrated resource threshold was applied successfully, but the experiment stopped before
any arm consumed that budget.

The fresh pre-migration lineage completed and migrated. Its packet rehydrated correctly, but
none of the transported **complete continuation programs** followed by one primitive suffix
produced a post-migration target that simultaneously:

- had strictly more minimal states than the migrated parent;
- was outside the birth-registry reachability set at symbolic depth 3;
- yielded a sound exact structural-incapacity certificate from the committed observations.

The engine raised:

```text
M040EngineError: no transported prefix plus primitive produced an admissible task
```

No post-migration task, arm result, native rewrite or rollback was produced. The 4,096-node
resource hypothesis therefore remains unmeasured on seed 400045.

Seed `400045` is consumed for this task-family mechanism and may not later confirm a broader
generator or the 4,096-node separation.

## Interpretation

A full previously adopted continuation is still too rigid as the only transferable prefix.
The causal element that must persist is the lineage-owned transformation motif, not
necessarily every surrounding birth-tool invocation from the earlier adoption.

The next task family must be specified before implementation and must:

- require at least one pre-migration lineage-owned tool;
- derive candidate prefixes only from already transported continuation programs;
- allow one or two new protocol-supplied suffix operations selected after migration;
- retain the same depth-independent equal resource budget for every arm;
- keep the target, selected suffixes and successful post-migration candidate out of the packet.
