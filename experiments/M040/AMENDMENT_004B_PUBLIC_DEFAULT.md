# M040 amendment 004B — bind both task-family defaults

**Status: committed before seed 400047 is evaluated.**

Seed 400046 compiled and produced a positive resource-bounded prefix-adaptation result, but it
did not evaluate amendment 004. The private `_execute` default had been changed to
`lineage_anchor`; the public `run_m040_development` default remained `prefix_adaptation` and
overrode it explicitly.

The first valid lineage-anchor run must therefore:

- use untouched development seed `400047`;
- keep depth 4, equal 4,096-node arm budgets and the 2,048-program task bound unchanged;
- set both `_execute.task_family` and `run_m040_development.task_family` defaults to
  `lineage_anchor`;
- verify those two defaults by signature introspection before executing the seed;
- require the result task family to equal `lineage_anchor`;
- require the accepted program to begin with a derived lineage anchor and end in one or two
  protocol-supplied tools;
- preserve the exact seed-400046 prefix result as a distinct consumed result.

A compilation, introspection or integration failure before the M040 engine starts does not
consume seed 400047. Once the engine is called, its result is retained whether positive or
negative.
