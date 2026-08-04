# M042 — constructive canonical-lineage continuation

**Status: development protocol draft. No frozen M042 block, selected bank entry or outcome
exists.**

## Question

Can the exact positive M040 canonical lineage be regenerated from its immutable seed, pass the
M041 passive pre-adoption validator, and then complete one further hidden post-migration rewrite
selected from a pre-verified finite bank in which every entry is constructively available?

M042 addresses only the failure exposed by M041: a fresh cumulative generator may reach a
cycle for which no admissible tool-dependent target exists. It does not rerun M041 and does not
alter any M038–M041 artefact.

## Immutable lineage base

The development and later frozen mechanism regenerate the M040 canonical lineage from:

- master seed `18441616668168956400`;
- protocol commitment
  `sha256:4816bc3c32e4fc04df5de4fad784a8935f0b8757c544dbc3862a1d2cb7b59d30`;
- task family `lineage_anchor`;
- complete seed-only replay;
- the M041 passive validator before the first post-migration adoption.

This base is not selected from M041's failed seed. It is the already preserved positive M040
canonical lineage and must reproduce its exact result identity before M042 continues it.

## Constructive task bank

After the M040 body is accepted on substrate B, M042 computes a finite bank from a disjoint,
predeclared task-seed range. An entry is admitted only when independent exhaustive checks prove
all of the following before selection:

- the hidden target is generated after the M040 packet has been rehydrated;
- the target has strictly greater minimal state count than the active M040 body;
- structural incapacity is proved from the committed 127 observations;
- the complete lineage reaches the exact target under symbolic depth four and 4,096 nodes;
- fresh-on-B, unchanged-parent, output-only and learned-tool-ablated controls are non-exact
  under the same depth and node budget;
- the complete lineage is strictly cheaper than the learning-state ablation;
- the accepted program causally uses a lineage-owned pre-migration tool;
- passive isolated validation passes before release adoption;
- exact native synthesis on the already discovered opaque substrate is possible;
- the fixed provisional failure rolls back to the accepted source/native pair exactly.

Every admitted bank entry is therefore usable by construction. The later sealed M042 seed may
choose only an index into this committed bank; it cannot create an unavailable task.

The bank range, admission rule, ordering, minimum size and selected-index derivation must be
frozen before any M042 canonical seed exists. The failed M041 seed may not influence the range,
entry ordering, thresholds or selected index.

## Continued controls

The further hidden task compares:

- the complete continued M040 lineage;
- a fresh learner on B starting from the same active M040 body;
- the unchanged pre-M040 migrated parent;
- output-only active competence without portable rewrite state;
- the continued lineage with learning state removed;
- the continued lineage with lineage-owned tools removed.

Every search-capable arm receives the same observations, depth and 4,096-node budget.

## Isolated adoption

Both post-migration adoptions—the original M040 rewrite and the new M042 rewrite—must pass the
M041 fixed passive-data workspace before the corresponding release body changes. First and
replay workspace identities must match byte for byte.

## Completion rule

A later canonical M042 result supports the bounded Genesis completion claim only if:

- the immutable M040 base reproduces exactly;
- the selected entry belongs to the frozen constructively available bank;
- the new continued cycle satisfies its complete control and native-rewrite rules;
- both post-migration isolated validations are exact, fail-closed and replay-identical;
- all ten `GENESIS_COMPLETION_CRITERIA.md` gates are true in the continuous replayed lineage;
- the unique marker-only M042 workflow preserves the first result regardless of sign.

## Development order

1. implement deterministic bank enumeration on the immutable M040 base;
2. retain all admitted entries and prove the entire bank, not only one selected task;
3. execute a consumed development selection from an independent development index;
4. integrate native synthesis, rollback, controls and passive validation;
5. reproduce the complete base and continuation from immutable inputs;
6. freeze only after the complete Python 3.11/3.13 suites and all historical guardrails pass;
7. execute one immutable M042 canonical selection.

## Non-claims

M042 remains a finite deterministic-DFA construction. A positive result would not establish
arbitrary-code safety, open-ended evolution, general intelligence, consciousness or production
permission.
