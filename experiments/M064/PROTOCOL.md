# M064 — frozen whole-WebAssembly completion protocol

**Status: DEVELOPMENT-POSITIVE — ELIGIBLE FOR FREEZE, NOT YET CANONICAL.**

## Research question

Can one continuous executable lineage cross from CPython through Node ESM into an import-free
whole-WebAssembly body, then complete three accepted native rewrites on task families revealed
only after migration, while strictly outperforming three equal-budget controls and preserving an
exact archive, causal memory, rollback and replay?

M064 is the integrated experiment required by the real-substrate frontier. It is not another
component demonstration. Its canonical claim is unavailable until the separate marker-only first
run and independent reproduction have completed without repair or rerun.

## Continuous lineage

1. reconstruct the qualified M047 CPython version-six state;
2. reconstruct M048 Node ESM version eight, including the native `max` acquisition;
3. scan all 256 arithmetic opcode bytes and replay M061's six structural probe shapes;
4. compile the complete parser, planner, allocator, selector, tool dispatch, executor, critic and
   orchestrator into one WebAssembly module;
5. require zero declared imports and 32/32 inherited capabilities before revealing a task bank;
6. perform three whole-module rewrites, reaching version twelve.

Node is a passive host after step 4. It writes the ASCII request into exported linear memory and
calls `run`; no semantic pipeline module remains in JavaScript.

## Four arms

All arms receive the same 8,192-expression budget per cycle and cross into WebAssembly before the
task-bank entry is selected.

| Arm | State at migration | Constructor registry |
|---|---|---|
| Complete continued lineage | M047 v6 → M048 v8 → whole Wasm v9 | `add`, `mul`, learned `mean`, learned `max` |
| Fresh on B | native Wasm founder | `add`, `mul` |
| Unchanged parent migrated | authentic pre-`mean` M047 v2 compiled to Wasm | `add`, `mul` |
| Learned state ablated | same executable Wasm v9 as complete | learned `mean` and `max` withheld from construction |

The ablated arm retains old output competence: its module can still execute `mean` and `max`.
Only their use by the post-migration constructor is removed.

## Three task families

Each committed bank contains six public and six hidden cases per cycle. Inputs are positive
integer pairs; the whole body applies its inherited two-decimal critic.

1. `crest(x,y) = mean(max(x,y), x, y)`;
2. `lift(x,y) = add(crest(x,y), max(x,y))`;
3. `weave(x,y) = mul(lift(x,y), crest(x,y))`.

Tokens differ by bank. The constructor is not told these equations. It receives only public
request/output cases and a serialised registry of the tools the arm owns. Fractional outputs make
the no-`mean` controls structurally incapable inside the frozen integer-closed grammar. Cycle 2
requires the cycle-1 route; cycle 3 requires both earlier routes.

## Construction grammar

The grammar starts from argument atoms `p0` and `p1`. It constructs:

- every binary owned-tool application over the two atoms;
- every binary owned-tool root over those components;
- every ternary owned-tool root with at most one composite child;
- no expression larger than seven nodes.

No complete `crest`, `lift` or `weave` program is catalogued. The constructor, evaluator, renderer
and complete WebAssembly compiler source are embedded in the serialised registry and hashed. The
external Python process executes those owned tools; it does not invent a transform or its
arguments.

## Independent admission and D021

The proposal API has no hidden-case parameter. Every public survivor is compiled into a complete
WebAssembly module. A passive validator then:

1. recompiles the bytes from the serialised transformation trace;
2. verifies that the module declares zero imports;
3. executes retained, public and hidden cases;
4. admits a digest representative only if **every** public survivor passes all evidence.

If one survivor disagrees on hidden evidence, the cycle terminates as ambiguous. The validator
has no patch registry, journal or adoption call.

## Versioning, archive and rollback

Each adoption archives the complete previous module and metadata, appends a patch record, extends
the hash-chained journal, appends a causal-memory episode and increments the version exactly once.
The fixed provisional fault corrupts the first candidate's journal-to-patch binding. Audit must
reject it and restore both state bytes and retained behaviour exactly before clean adoption.

Replay begins again at whole-Wasm version nine and applies only the three independently admitted
selections. Its final state digest must equal the observed version-twelve digest.

## Isolation and resource bounds

- candidate expression budget: 8,192 per arm and cycle;
- expression node limit: 7;
- candidate module byte ceiling: 262,144;
- WebAssembly linear memory: one page;
- Node old-space ceiling: 128 MiB;
- host wall timeout: 30 seconds per invocation;
- disposable host working directory;
- zero WebAssembly imports, hence no filesystem, network, process, credential or repository call
  in the semantic body.

Cost accounting includes constructed expressions, public candidate executions, independent
module inspections, independent retained/public/hidden executions, host processes, migrations,
failed candidates and accepted rewrites.

## Bank commitment and canonical selection

Four complete entries are committed before the canonical marker. After every arm migrates, the
selected index is:

`sha256(protocol_digest || marker_parent_sha) mod 4`.

The marker parent therefore chooses an already committed entry but is unknown when this protocol
is frozen. The marker commit may change only `experiments/M064/CANONICAL_ARMED.json` and must carry
the exact guarded message.

## Canonical and reproduction rule

The first canonical job runs once on Python 3.11 and Node 20 and uploads the raw JSON. A dependent
Python 3.13/Node 20 job starts from the same immutable commit, reruns from the same marker parent
and must reproduce the first result byte-for-byte. Its report cannot replace the first artifact.
A failed first result, failed reproduction, contamination or timeout is preserved as the M064
verdict; no rerun becomes canonical and no threshold may be relaxed.

## Authorship boundary

M064 leaves authored and records as such:

- the complete whole-body compiler and its memory layout;
- WebAssembly block/loop structure, blocktypes and immediates not resolved by M061;
- the finite expression grammar;
- the four task-bank entries and three mathematical families;
- public/hidden partition sizes, budgets and decision rule.

Arithmetic opcodes and ten structural effects are probed. The compiler is owned and frozen, not
invented during the canonical run. The result cannot support unrestricted compiler synthesis,
unbounded substrate discovery, open-ended evolution, general intelligence or consciousness.

## Frozen executable identities

- executable protocol digest:
  `c5cfcf12aca73f983d8c1ba533ea9daea4a8ff9bcfa58767c2b5222a427bbe8d`;
- task-bank commitment:
  `7134e3f0ce4c3e84ccb52834bea08ce41501104e1c76245b1e97e2c1981a33da`;
- M061 structural protocol digest:
  `4b667915ad37d345526398734411f4ecea34b08746d9f5866753ce26be54f3f2`.

The separate `FROZEN_PROTOCOL.json` binds these values, the complete task bank, generator and
runtime file hashes, decision rules and workflow before arming.

## Claim and release boundaries

A development pass makes M064 eligible for freeze; it is not canonical evidence. Even a positive
canonical result grants no repository, network, credential, deployment or production authority
to the lineage. Those remain human-controlled.
