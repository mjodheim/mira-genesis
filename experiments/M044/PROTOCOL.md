# M044 — accelerated integrated continuous Mealy lineage

**Status: protocol and implementation prepared; primary integrated qualification pending.**

## Why M044 exists

M043 qualified the Mealy kernel, rewrite language, constructive tasks, isolated adoption,
rollback and opaque-native migration separately. M044 stops extending that gate sequence.
It composes those already-qualified mechanisms into one bounded lineage and absorbs the
former Q6 replay requirement into the experiment's exit condition.

## Frozen objective

One deterministic lineage must:

1. start from the public two-state M043 Mealy founder;
2. construct, validate and adopt two exact capacity-changing rewrites;
3. reuse an acquired abstract tool pattern on the second rewrite;
4. discover one fixed opaque field substrate through bounded public probes;
5. migrate the complete accepted snapshot to an exact table-free native DAG;
6. construct, validate and adopt one additional rewrite after migration;
7. reuse an acquired tool pattern after migration;
8. resynthesise an exact changed native body on the same opaque substrate;
9. reject a forced journal-corruption commit and restore the exact prior checkpoint;
10. reproduce the complete manifest byte-for-byte on an immediate replay.

## Fixed bounds

- pre-migration accepted cycles: `2`;
- post-migration accepted cycles: `1`;
- search depth: `2` operations;
- search node budget: `4,096`;
- state ceiling: `6`;
- catalogue candidates per cycle: `96`;
- hidden observation limit: `64`;
- opaque substrate family: development family `0`;
- forced rollback fault: causal-journal corruption.

The accepted lineage grows from two to five states. The sixth state is available only to the
provisional rollback probe and is never committed or migrated; Q5's native field remains
bounded to five declared states.

## Reused mechanisms

M044 does not define another body model, mutation language, target generator, validator,
transaction store or native compiler. It calls the M043 Q1-Q5 implementations directly:

- exact total Mealy representation and equivalence;
- Q2 duplicate-and-specialise rewrites and certificates;
- Q3 target-blind constructive catalogue admission;
- Q4 disposable replay, evaluator acceptance, versioned state and rollback;
- Q5 public opaque discovery, finite-field DAG synthesis and migration audit.

## Tool reuse interpretation

A registered Q4 tool record contains the exact validated trace identity and its abstract
effect sequence. A later cycle counts as reuse only when its new parent-bound trace applies
the same acquired effect pattern. The exact old trace is never replayed against a different
parent.

## Post-migration continuation

The first native program is independently reconstructed into its exact Mealy behaviour.
That native-reconstructed behaviour is the parent of the third task. After adoption, the
full updated snapshot is compiled again on the same discovered substrate. Success requires
a changed native-program identity and exact reconstruction of the new accepted body.

## Replay and claim boundary

The runner executes the entire experiment twice and compares canonical manifest bytes. CI
must expose the same manifest SHA-256 on Python 3.11 and Python 3.13.

M044 remains a bounded integrated development result. It does not claim open-ended
evolution, AGI, consciousness, production authority or unrestricted native self-modification.
The separate proxy-measurement experiment remains outside M044 and retains the M045 number.
