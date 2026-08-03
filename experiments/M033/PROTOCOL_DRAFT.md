# M033 — pre-result development protocol

## Question

After M032 has completed rewrite, independent validation, opaque-substrate discovery,
native compilation and packet transport, does the migrated lineage learn a genuinely
new post-migration task family more efficiently or to higher exact quality because it
retained useful memory, exploration state and learned rewrite tools?

The experiment tests causal post-migration plasticity. Exact transport alone is already
an M032 result and cannot satisfy M033.

## Separation boundary

The post-migration task generator is called only after all lineages have crossed the
substrate boundary or reached the equivalent control checkpoint. Before that boundary,
no lineage, parent selector, rewrite selector, packet builder or migration routine may
observe:

- the post-migration target DFA;
- its transformation trace;
- its motif or component labels;
- held-out words or exact-equivalence witnesses;
- its task seed or any value derived from that seed.

The evaluator commits the primary seed block before implementation of the primary
comparison. Tests and smoke runs must use a disjoint development block.

## Lineages

Every paired seed instantiates the following six lineages from common pre-migration
inputs and common random numbers where their mechanisms overlap.

### 1. Complete M032 lineage

- independently adopts the pre-migration rewrite through M025;
- discovers and compiles for substrate B through M032;
- retains the exact M025 passport, learned rewrite tools, memory, uncertainty and
  exploration frontier;
- remains permitted to learn and rewrite after migration.

### 2. Fresh-B control

- begins only after the new task is revealed;
- receives the same primitive operations and substrate interface;
- receives no migrated body, memory, learned tools or exploration history.

### 3. Unchanged-parent control

- migrates the exact pre-rewrite parent body to B;
- retains only state that the parent possessed before the accepted M025 rewrite;
- receives the same post-migration learning budget.

### 4. Output-only control

- receives the complete migrated native body and may execute it;
- cannot extend its tool registry, modify its body or update learning state;
- measures transported output without transported plasticity.

### 5. Learning-state ablation

- receives the improved migrated body and learned rewrite tools;
- memory, uncertainty and exploration frontier are replaced by their canonical empty
  values after packet validation and before the new task is revealed.

### 6. Learned-tool ablation

- receives the improved migrated body and learning state;
- learned rewrite tools are removed after packet validation and before task reveal;
- primitive tools remain unchanged.

No ablation may change the active body, primitive tool set, substrate semantics,
post-migration task or evaluator.

## Post-migration task family

The first development rig must satisfy all of the following before any primary run:

1. every target is a finite binary DFA with exact equivalence decidable;
2. the family is generated only from the post-migration task seed;
3. no exact target appeared in pre-migration development, regression or migration
   cases;
4. no held-out word is reused from those earlier surfaces;
5. at least one target requires a reusable transformation component available in the
   complete lineage's transported registry or memory;
5b. that component must be one the migrated body does **not** already encode. The
   body-anchored control block showed that when the single learned tool applies the same
   transformation the adopted rewrite baked into the body, the learned-tool ablation ties
   the complete lineage on every seed and the control measures nothing;
6. at least one additional operation or composition must still be discovered after
   migration, so replaying a stored answer cannot solve the task;
7. a fresh lineage can solve a non-zero fraction under the common budget;
8. the output-only control cannot improve by construction;
9. exact task difficulty and reachable solution depth are bounded and audited before
   primary seeds are opened.

The task generator may share abstract transformation structure with pre-migration
experience, but it may not share a complete answer. That distinction is the mechanism
under test.

## Cost accounting

The primary cost for the complete and unchanged-parent lineages includes:

- pre-migration diagnosis or task evidence supplied to the implemented mechanism;
- rewrite search and all failed candidates;
- independent validation and regression checks;
- opaque-substrate probes and native synthesis;
- packet validation and rehydration;
- post-migration exploration, learning, rewrite search and validation.

Fresh-B cost begins at its legitimate creation boundary after task reveal, but reports
both that conditional cost and a full-lifecycle comparison in which absent earlier
costs are zero rather than hidden. Output-only execution cost is reported separately
and may not be compared as if it were a learner.

Elapsed wall-clock time is diagnostic only. Deterministic node, probe, evaluation and
candidate counts decide the experiment.

## Ground truth and primary measures

For every lineage and seed, the evaluator records:

1. exact final behavioural equivalence to the post-migration target;
2. exact held-out quality when equivalence is not reached;
3. deterministic total cost;
4. cost to first exact solution, if any;
5. accepted post-migration rewrites;
6. reuse or extension of a transported learned tool;
7. mutations of memory, uncertainty and exploration state after reveal.

The primary comparison is the complete lineage versus each learning-capable control.
Output-only is a mechanism control, not a cost competitor.

## Development sequence and seed hygiene

### Control block

Seeds `1024+` are reserved for implementation tests, positive controls, negative
controls and calibration of the task generator. They may never enter the primary
comparison.

The control blocks are closed and disjoint: `1024–2047` fixed-structure, `2048–3071`
structural, `3072–4095` combined memory-and-tool, `4096+` body-anchored.

### Task anchor

Each lineage starts a post-migration task from the body it actually migrated. The primary
comparison must use `TaskAnchor.LINEAGE_BODY`.

The first three control blocks used `TaskAnchor.TASK_BASELINE`, which starts every lineage
from the task's own baseline source. Under that anchor the migrated body is never read, so
the unchanged-parent control and the learned-tool ablation present byte-identical surfaces
and Gate 8 silently loses one of its four required controls. `TASK_BASELINE` remains the
implementation default only so that those recorded blocks stay byte-reproducible; it may
not be used for the primary comparison.

### Confirmation block

Seeds `0–63` are reserved for the first paired development comparison. No code path may
instantiate their post-migration tasks before:

- all control gates below pass;
- the exact generator version is committed;
- the comparison statistic, advantage threshold and failure rule are written into this
  protocol;
- an implementation commit is tagged as pre-result evidence.

The current draft deliberately does **not** set a numerical advantage threshold before
the control rig establishes the useful dynamic range. D010 forbids treating a typical
pilot effect as a worst-case bound. Opening seeds `0–63` before that amendment would
contaminate M033 and require a new untouched block.

## Control gates before threshold freeze

1. **Task isolation:** a static audit proves no pre-migration object can reach the
   post-migration generator, seeds, targets or held-out evaluator.
2. **Exactness:** exhaustive finite checks prove evaluator equivalence and held-out
   quality agree on all reachable small control DFAs.
3. **Positive tool control:** supplying the required reusable component reduces
   deterministic search cost on the designated positive family.
4. **Negative tool control:** supplying an irrelevant component does not improve the
   designated disjoint family and may expose its branching cost.
5. **Memory control:** a relevant transported trace changes a pre-written exploration
   decision, while a permuted or empty trace does not.
6. **Ablation identity:** all six lineages are byte-identical at the intended surfaces
   before their explicit ablation or control difference.
7. **No answer replay:** deleting the still-required post-migration operation prevents
   exact solution even when all transported state is present.
8. **Fresh solvability:** the fresh-B lineage solves at least one control task within the
   common finite budget.
9. **Output-only immobility:** the output-only lineage's body and packet state remain
   byte-identical throughout the audit.
10. **Rollback:** a forced bad post-migration rewrite restores the migrated parent body,
    packet state and tool registry exactly.
11. **Determinism:** identical paired inputs produce byte-identical row artifacts.
12. **Repository integrity:** focused tests, complete CI and repository audits pass.

## Threshold-freeze amendment

After the control block passes, but before seeds `0–63` are instantiated, this document
must gain:

- the primary paired statistic;
- the minimum exact-quality or cost advantage;
- the required win/tie/loss rule;
- critical-regression limits;
- the maximum allowed invalid or abstained seeds;
- the exact artifact schema and SHA-256 identity rule.

That amendment is a new commit whose SHA is recorded in `STATUS.md`. Any result observed
before it exists is pilot evidence only and cannot support M033.

## Required interpretation

A positive M033 result would support only this bounded claim: in the frozen finite task
and substrate families, transported learning state and tools causally improve
post-migration adaptation over fresh, unchanged-parent and ablated controls.

A negative result remains valid. It would mean M032 transports state without yet
showing transported plasticity, or that the selected state surface is not the causal
one. Threshold relaxation, task replacement or seed substitution after observation is
not admissible.

## Non-claims

M033 cannot establish universal transfer, arbitrary architecture migration,
autonomous fault diagnosis, unrestricted self-rewrite, operating-system sandboxing,
three repeated improvement cycles, open-ended recursive self-improvement,
consciousness or AGI.
