# M043 — structural-domain transfer to deterministic Mealy machines

**Status: protocol draft. No development result, frozen protocol, selected seed or canonical outcome exists.**

## Purpose

M042 completed the first bounded Genesis claim in deterministic binary-DFA worlds. M043
opens a separate second-phase question: does the architecture transfer to a formally
different behavioural domain, or was the positive result dependent on language-acceptor
specific structure?

The new domain is a deterministic total Mealy machine. Behaviour is an output stream
produced along transitions, not a final accept/reject bit. Exact equivalence, canonical
minimisation and finite counterexamples remain decidable, preserving the project's ability
to distinguish real improvement from proxy success.

## Research question

Can the domain-neutral Genesis mechanisms — diagnosis, lineage-owned tool construction,
proof-gated rewrite, isolated adoption, exact rollback, opaque-substrate discovery,
portable learning state and replay — be instantiated for deterministic Mealy machines
without importing the M042 body representation, hidden task bank or DFA-specific rewrite
language?

M043 is a rig-qualification experiment. It does not attempt a new ten-gate canonical
completion result. Its exit condition is a falsifiable, independently tested Mealy-domain
base on which a later frozen continuous-lineage experiment could be defined.

## Domain contract

The initial bounded domain uses:

- deterministic total Mealy machines;
- input alphabet `{0, 1, 2}`;
- output alphabet `{0, 1, 2}`;
- finite state sets with a declared development cap;
- canonical reachable-state ordering;
- exact equivalence by product exploration;
- exact minimisation by behavioural partition refinement;
- shortest distinguishing input words for non-equivalent machines;
- canonical serialisation and SHA-256 identities.

The evaluator may know the hidden target exactly. The organism may receive only permitted
observations, costs, counterexamples and public substrate probes. Target transition or
output tables may never be imported into organism state or candidate code.

## Independence from M042

M043 may reuse domain-neutral infrastructure only:

- typed canonical serialisation;
- immutable causal journalling;
- seed commitments and first-result preservation rules;
- disposable validation workspaces and fail-closed release gates;
- versioned adoption, archive and rollback interfaces;
- generic opaque-substrate probe orchestration.

M043 must not reuse:

- the M040/M042 canonical seed or constructive bank;
- DFA target generators or the `lineage_anchor` task family;
- DFA state/output encodings;
- the M039 `flip/grow/redirect` macro as an executable Mealy tool;
- any hidden M042 result field as a selector, threshold or task input.

A Mealy mutation language must be defined from its own semantics. Conceptual operations
may include transition redirection, emitted-symbol replacement, behaviour-preserving
state duplication and later composition, but their exact arguments, costs and replay
rules belong to M043 and must be tested independently.

## Qualification gates

### Q1 — exact formal kernel

For every generated bounded machine:

- canonical serialisation is invariant under state renaming;
- minimisation preserves behaviour exactly and is idempotent;
- equivalence is symmetric and agrees with exhaustive bounded checks;
- every reported counterexample actually distinguishes the machines;
- malformed or partial machines fail closed.

### Q2 — capacity-changing rewrite language

The language must contain at least one behaviour-preserving operation that increases the
reachable state count and at least one operation that can later exploit the new capacity.
The implementation must prove which operations preserve, increase, reduce or leave
unchanged the state count. A tool trace must replay byte-identically from the declared
parent.

### Q3 — constructively available hidden tasks

Before any sealed selection exists, a finite development bank must demonstrate tasks for
which:

- the parent is structurally incapable of exact behaviour;
- at least one admissible lineage-owned rewrite reaches the exact target within the
  declared depth and node budget;
- the target is not directly encoded in the rewrite arguments;
- fresh, unchanged-parent, output-only, learning-state-ablated and tool-ablated controls
  are meaningful and receive equal search budgets;
- generation terminates with an explicit negative result when no admissible task exists.

The M041 failure mode — generating a hidden task that no admissible lineage can reach —
must be impossible after bank admission, not merely unlikely.

### Q4 — isolated adoption and rollback

Candidate Mealy bodies run in fresh resource-limited workspaces. Validation independently
checks syntax, totality, regression preservation, strict improvement and exact equivalence.
The candidate has no release authority. A fixed invalid provisional rewrite must be
rejected and restore the exact accepted source/native pair, registry and journal head.

### Q5 — opaque native substrate

A second representation must expose undeclared transition/output operations only through
public probes. The lineage must discover the permitted semantics, synthesise an exact
native Mealy body and reject tampered packets. The substrate cannot be a renamed copy of
the source table format.

### Q6 — deterministic development replay

A complete development episode must reproduce from immutable inputs:

- founder and hidden task identities;
- permitted observation stream;
- every symbolic expansion and rejection;
- tool construction and use;
- candidate validation and adoption decision;
- migration packet and discovered substrate semantics;
- native synthesis, forced failure and rollback;
- final source/native behaviour and all journal bytes.

Python 3.11 and 3.13 must produce the same scientific identities.

## Required controls

The first integrated development comparison must include:

1. the complete Mealy lineage;
2. a fresh learner with the same observations and budget;
3. the unchanged parent lineage;
4. an output-only migrated body without portable rewrite state;
5. the complete lineage with learning state removed;
6. the complete lineage with lineage-owned tools removed.

No control may collapse into another through an unused field or inert operation. Each
ablation must be proven to alter a causally available mechanism before its result is
interpreted.

## Development order

1. implement the exact Mealy kernel and metamorphic tests;
2. define and audit the independent mutation language;
3. build structural incapacity certificates and constructive task enumeration;
4. integrate disposable validation, versioned adoption and exact rollback;
5. define and discover an opaque native representation;
6. run only consumed development seeds and preserve negative findings;
7. write an independent qualification report;
8. decide whether a distinct later experiment is justified.

No M043 canonical workflow is authorised by this draft.

## Rejected shortcuts

M043 must not be presented as stronger merely because it uses more states, a larger seed
count or a larger search budget. It must not replay M042 with outputs attached to DFA
states, and it must not freeze a canonical protocol until every qualification gate has a
permanent falsification test.

## Claim boundary

A positive M043 qualification would show that the experimental architecture can be
reconstructed in a richer decidable reactive-system model. It would not establish
open-ended evolution, arbitrary program rewriting, stochastic robustness, general
intelligence, consciousness or permission to modify external systems.
