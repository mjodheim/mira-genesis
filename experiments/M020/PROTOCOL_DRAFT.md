# M020 — Development protocol draft

**Status: DEVELOPMENT ONLY. Not frozen, not hashed, and not canonical.**

## 1. Question

Can an organism improve executable code that constitutes part of its own active body,
using only tools in its own registry, while preserving isolation, exact rollback and a
held-out measure that the rewrite search cannot inspect?

## 2. Current body

A body is a single pure Python policy function in a deliberately bounded language.
The language permits finite arithmetic, comparisons, conditionals and local integer
assignments. It forbids imports, calls, attributes, loops, exceptions, classes,
reflection, filesystem access and network access.

The restriction is scientific, not cosmetic. Candidate termination and side-effect
freedom must be decidable before the rewrite surface is widened.

## 3. Internal tool language

The initial registry contains three primitive source tools:

1. replace an integer constant;
2. replace a binary arithmetic operator;
3. replace a comparison operator.

Each edit is serialised as a `PatchOperation`. A successful multi-edit trace is
absorbed into the registry as a reusable `LearnedRewriteTool`. The organism therefore
changes both its executable body and the language with which later bodies may be
changed.

## 4. Information boundary

The rewrite engine receives only:

- the current source body;
- the function name;
- development cases;
- its registered rewrite tools;
- deterministic search limits.

Held-out cases are evaluated only after the engine has selected a candidate. Their
arguments and expected answers are not passed into the engine or any tool.

## 5. Candidate lifecycle

Every candidate must pass, in order:

1. parsing;
2. bounded-language validation;
3. isolated compilation with empty builtins;
4. deterministic execution on development cases;
5. strict score comparison against the current body.

A tie is not an improvement. A candidate with an exception, non-integer result,
unsafe syntax or invalid patch is rejected.

## 6. Adoption and rollback

Adoption is allowed only when the selected candidate strictly improves the development
score. Before replacement, the current source is archived byte for byte. The active
body records each adopted digest, and rollback restores the immediately preceding
source exactly.

A rewrite result cannot be applied to a body whose digest differs from the result's
recorded baseline. This prevents stale candidates from overwriting a newer body.

## 7. Development gates

The current kernel is development-ready only if all of the following hold:

1. unsafe source forms are rejected;
2. the engine finds a task requiring at least two source edits;
3. the selected body strictly improves development performance;
4. held-out performance improves without held-out answers entering the search;
5. the previous body is archived exactly;
6. rollback restores the previous behaviour;
7. the accepted edit trace becomes a reusable internal tool;
8. repeated runs produce the same selected source, trace and candidate count;
9. a body already optimal on the development cases is not replaced.

## 8. What this would establish

Passing these gates would establish a bounded form of self-rewrite:

- Mira can alter executable source that controls its behaviour;
- Mira performs the alteration through tools represented inside its own system;
- adoption is contingent on measured improvement rather than human preference;
- the rewrite is reversible and auditable;
- successful rewrite structure can become part of Mira's later tool vocabulary.

It would not establish unrestricted autonomy, AGI, consciousness, general code repair,
or open-ended recursive self-improvement.

## 9. Next widening steps

The language may be widened only one capability at a time:

1. expression-tree synthesis rather than substitution only;
2. multi-function modules with explicit dependency graphs;
3. candidate workspaces containing tests and source files;
4. subprocess isolation with CPU, memory, time and syscall limits;
5. tool creation from successful transformation traces;
6. cross-substrate re-embodiment of the rewritten policy;
7. comparison against an unchanged lineage over unseen task families;
8. human-independent proposal generation while preserving a human-controlled release
   boundary for real repositories.

No widening step may remove exact archive, rollback, held-out isolation or regression
gates.
