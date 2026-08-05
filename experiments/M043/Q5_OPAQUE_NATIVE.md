# M043 Q5 — opaque field discovery and table-free native Mealy synthesis

**Status: passed in development. Qualification CI completed successfully.**

## Question

Can the accepted Q4 Mealy lineage migrate to a native execution substrate whose opcode
semantics are undeclared, recover a sufficient operational basis only through bounded
public probes, and synthesize exact native behaviour without serialising a renamed copy of
the source transition and output tables?

Q5 is development rig qualification only. It does not select a seed, freeze a hidden task
bank, authorise a canonical workflow or establish a continuous post-migration lineage.
Q6 remains responsible for complete founder-to-native replay.

## Opaque substrate

`metamorphosis/m043_opaque_substrate.py` defines a prime-field machine of order five. The
public surface exposes only:

- a machine identity and modulus;
- opaque opcode identifiers;
- opcode arity and cost;
- repeated behavioural probes and execution.

The hidden roles are shuffled independently for three development families. The required
basis consists of field addition, multiplication and additive negation, but those names are
never returned by `describe()` or `probe()`. Discovery classifies roles only after probing
every unary or binary input tuple three times.

The fixed development probe budget is 512 calls. The three positive families consume 345,
345 and 360 calls. Negative machines cover a missing multiplication primitive, an unstable
addition primitive and an unstable multiplication primitive. Each fails explicitly; a
budget of eight calls also terminates as exhausted.

## Native representation

`metamorphosis/m043_native_program.py` defines a strict scalar DAG. Nodes may contain only:

- the current native state register;
- the current input symbol;
- one field constant;
- a unary or binary call to a discovered opaque opcode.

There are no transition rows, output rows, lookup maps or truth-table payloads. Every node
must be reachable from the next-state or output root, call arity is at most two and parsers
reject all missing or additional fields. These restrictions prevent unused nodes from being
used as a covert source-table archive.

## Algebraic synthesis

The accepted Mealy machine has at most five states and uses symbols in the field. Q5 builds
finite-field Lagrange indicator polynomials for each observed `(state, symbol)` pair, then
combines them into two executable DAG roots:

- next native state;
- emitted native output.

The resulting coefficients are an algebraic transform, not a state-by-symbol table. DAG
common-subexpression elimination shares constants, indicators and opcode calls. The
synthesizer uses only the three experimentally discovered core opcodes.

## Exact certificate

For every positive substrate, the independent certificate records:

- the exact indexed source-body digest;
- the source behavioural digest;
- the discovery and native-program digests;
- exact agreement on every state/symbol pair;
- exact Mealy product equivalence and absence of a distinguishing word;
- absence of forbidden table keys;
- absence of the complete exact source-body bytes from native storage;
- complete root reachability of every native node;
- maximum executable call arity two.

`metamorphosis/m043_native_verify.py` independently reconstructs every certificate field
from the accepted source, native DAG, discovery record and opaque machine. Bundle audit
rejects any self-consistent-looking certificate whose metadata differs from recomputation.

The native program is reconstructed back into a `MealyMachine` and must equal the accepted
source body exactly, not only behaviourally.

## Q4 continuity binding

`metamorphosis/m043_migration.py` builds a strict native-migration bundle bound to:

- the complete Q4 snapshot digest and version;
- the accepted Mealy body digest;
- the tool-registry digest;
- the portable learning-state digest;
- the causal-journal digest;
- the target opaque machine and discovery identities;
- the exact native program and synthesis certificate.

The bundle preserves source lineage identity without embedding the source body inside the
native executable. Auditing against another snapshot, machine or discovery fails closed.

## Development qualification

`run_q5_development_qualification()` reconstructs one accepted Q4 development snapshot and
migrates it independently to all three positive opaque families. The report requires:

- three distinct machine identities;
- three distinct opaque assignments for add, multiply and negate;
- exact table-free native synthesis on every family;
- byte-identical bundle round trips;
- public-probe-only discovery;
- rejection of all three negative substrates;
- explicit probe-budget exhaustion;
- rejection of a wrong source lineage;
- rejection of a tampered discovery binding;
- rejection of direct transition-table smuggling;
- no selected seed, hidden bank or canonical workflow authority.

## Permanent falsification suite

The focused suite adds 40 tests covering public opacity, role discovery, deterministic
probing, unstable and incomplete machines, strict budgets, exact interpolation, native
execution, parser round trips, forward references, unreachable payloads, direct-table
smuggling, wrong substrate/discovery bindings, capacity limits, independent certificate
recomputation, complete-lineage bundle bindings and the deterministic Q5 development report.

## Qualification evidence

GitHub Actions workflow run `31008963611` completed successfully on the final qualification
head:

- **745 tests passed on Python 3.11** in 535.16 seconds;
- **745 tests passed on Python 3.13** in 581.31 seconds;
- every module imported cleanly;
- no orphan module remained;
- declared dependencies matched real imports.

No job failed and no rerun was used.

## Next boundary

Q6 must reproduce the complete development chain from founder-side inputs through Q1–Q5,
including constructive tasks, exact rewrites, adoption decisions, lineage state, opaque
probes, native DAGs, certificates and migration bundles. Q5 does not authorise a hidden
bank, selected seed or canonical M043 workflow.
