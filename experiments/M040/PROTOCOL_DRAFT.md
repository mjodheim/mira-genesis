# M040 — post-migration plasticity in one cumulative lineage

**Status: pre-result development protocol. No M040 outcome has been measured. No sealed
M040 block, canonical seed or canonical task exists.**

## Question

Can one deterministic lineage accumulate a body and a lineage-owned tool in substrate A,
migrate the improved competence, tool registry and relevant learning state to an initially
opaque substrate B, then diagnose and complete a further self-rewrite on a task family
revealed only after migration?

M040 tests whether transported state remains functionally plastic rather than merely
preserving the old output.

## Scope

The experiment remains in the decidable binary-DFA laboratory. It does not claim arbitrary
program synthesis, unrestricted code execution, open-ended evolution, general intelligence
or consciousness.

M032 remains the source of truth for opaque-substrate discovery and native-body synthesis.
M039 remains the source of truth for cumulative lineage, lineage-owned tool provenance and
seed-to-head replay before migration. M040 composes those mechanisms without changing their
frozen canonical artefacts.

## One continuous lineage

The complete arm must:

1. generate and complete the three-cycle M039-style lineage on substrate A from a new M040
   seed and protocol commitment;
2. retain its final source DFA as portable internal representation, its complete serialised
   tool registry and an explicit learning state derived only from pre-migration events;
3. receive an opaque Boolean machine whose operation identifiers and truth tables were not
   available before the migration boundary;
4. discover the permitted operation semantics by probing;
5. synthesise an exact native body for the final pre-migration DFA;
6. commit a canonical transport packet and rehydrate the body, registry, memory and
   discovered substrate from that packet;
7. reveal a new transfer task only after the packet has been validated;
8. diagnose structural incapacity from oracle observations without receiving a fault label;
9. search with the rehydrated registry and learning-state ordering policy;
10. adopt an exact improved source body and synthesise its new exact native body on B;
11. force a bad provisional native-body adoption and restore the accepted post-migration
    body exactly;
12. replay the complete pre-migration lineage, migration, task generation, controls,
    post-migration rewrite, native synthesis and rollback from the seed and immutable inputs.

## Post-migration task family

The family is a bounded repeated-motif transfer family. After migration, the generator uses:

- the current migrated source DFA;
- the lineage-owned macro constructed before migration;
- one protocol-supplied primitive selected by a cycle seed derived after migration.

It selects the first canonical composition in seed-defined order that:

- produces a strictly larger minimal DFA;
- differs exactly from the migrated parent;
- is not reachable by the birth primitive registry within the same symbolic depth;
- has a sound exact structural-incapacity certificate from the committed observations.

This family deliberately tests transfer of a previously learned transformation motif. It
must not be described as arbitrary unseen-task generalisation.

## Learning state

The packet carries a canonical state with:

- accepted pre-migration candidate identifiers;
- lineage-owned tool identifiers;
- causal pre-migration tool-use identifiers;
- a preferred-tool ordering derived only from adopted pre-migration uses;
- an exploration frontier containing the next symbolic depth and remaining search budget.

The state may change search order and therefore cost. It may not reveal the target body,
its generating primitive or a successful candidate.

## Arms and controls

All arms receive the same post-migration oracle observations and deterministic cost budget.

### A — complete migrated lineage

Receives the exact migrated parent competence, portable source representation, full registry
and full learning state.

### B — fresh organism on B

Receives the same migrated parent competence and the same primitive language, but no
lineage-owned tool, pre-migration memory or preferred-tool ordering.

### C — unchanged parent migrated

Receives the original founder competence migrated to the same substrate B, the birth
registry and empty learning state.

### D — output-only native body

Receives only the exact native body that preserves the migrated parent output. It receives
no portable source representation, registry or rewrite state.

### E — learning-state ablation

Receives the complete source representation and registry, including the learned tool, but
its memory and preferred ordering are removed.

### F — learned-tool ablation

Receives the complete source representation and learning state, but every lineage-owned tool
is removed and the state is sanitised so that removed tool identifiers cannot influence
ordering.

## Primary verdicts

### Trans-substrate continuity supported

Requires all of:

- the pre-migration lineage completes three accepted exact cycles;
- the final pre-migration body migrates exactly to B;
- the packet round-trips canonically and rejects tampering;
- the rehydrated registry and learning state match the committed packet;
- the new task is generated only after migration and packet validation;
- the accepted post-migration source and native bodies are exactly equivalent to the new
  target;
- the forced rollback restores the accepted post-migration source/native pair exactly;
- replay reproduces every committed digest and decision transcript.

### Post-migration plasticity supported

Requires trans-substrate continuity plus:

- arm A reaches exact quality 1;
- arms B, C, D and F have lower exact quality under the equal committed budget;
- arm A is strictly cheaper than arm E on the pre-registered primary search-cost dimension;
- arm E receives no lower exact quality than A solely because of a smaller budget;
- at least one accepted post-migration proposal causally uses a lineage-owned tool created
  before migration;
- an independent ablation verifies that the learned tool is load-bearing under the same
  language depth and node budget.

A positive continuity result with a negative plasticity result remains a valid negative
plasticity finding. The two verdicts must be reported separately.

## Cost vector

No synthetic score is permitted. Report separately:

- oracle queries;
- substrate probes;
- migration candidate evaluations;
- native components and persisted native bytes;
- certificate search nodes, pair tests and suffix probes;
- symbolic search nodes;
- primitive expansion operations;
- candidates constructed and candidates exactly evaluated;
- tool-symbol uses;
- packet bytes;
- journal records and persisted journal bytes;
- replay operations;
- wall time as diagnostic only.

The primary memory comparison is `symbolic_search_nodes`; A must be strictly lower than E.
All other functional decision transcripts must remain identical after the accepted candidate
is reached.

## Replay boundary

Replay may receive only:

- the master seed;
- frozen protocol commitment;
- frozen mechanism commit;
- expected external heads and artefact digests.

It may not receive target DFAs, accepted candidates, generated programs, discovered truth
tables, migrated bodies, control outcomes or mutation traces from the expected artefact.

## Development budgets

These are development commitments and may be revised only before a sealed M040 protocol is
created:

- pre-migration mechanism: frozen M039 constants;
- observation depth: 6;
- substrate probe budget: 120;
- migration candidate budget: 75,000;
- native component budget: 320;
- post-migration symbolic depth: 2;
- post-migration symbolic-node budget: 20,000;
- task-generation attempts: 256;
- forced rollback attempts: 1.

Any budget exhaustion is a negative result for that arm. There is no silent fallback to a
different language, deeper search or hidden target access.

## Falsifiers

The corresponding verdict is rejected if any of the following occurs:

1. a task or target is observed before packet validation;
2. the substrate semantics are supplied rather than discovered by probing;
3. the migrated parent body is not exactly equivalent to the source parent;
4. packet tampering, omission or reordering is not detected;
5. the post-migration diagnosis certificate is invalid or cannot be recomputed;
6. the accepted post-migration proposal does not use a pre-migration lineage tool;
7. the tool-ablated arm solves under the same depth and node budget;
8. the output-only arm can propose a rewrite despite lacking the committed rewrite state;
9. rollback does not restore the accepted post-migration source and native bodies exactly;
10. A and E differ in anything other than learning-state-driven registry ordering before
    candidate discovery;
11. replay consumes an expected target, candidate, discovered substrate or mutation trace;
12. replay changes any packet, manifest, body, task, control, journal or transcript digest;
13. a control receives a smaller cost budget than arm A;
14. any rule, threshold or task generator changes after a sealed outcome is observed.

## Development order

1. implement the canonical M040 packet and tamper controls;
2. integrate a fresh M039-style pre-migration lineage with M013e discovery/migration;
3. implement post-migration task generation and the six arms;
4. implement exact post-migration rewrite, native re-synthesis and rollback;
5. implement seed-only replay and independent transcript verification;
6. run consumed development seeds and retain failures;
7. freeze only after the mechanism, controls, budgets and falsifiers are stable;
8. run one immutable canonical evaluation.

No sealed M040 block may be created or opened during the development steps above.
