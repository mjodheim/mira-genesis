# M032 — verified trans-substrate rewrite development base

## Result

M032 supports the following bounded development claim:

> One M025 lineage can independently validate and adopt an executable rewrite, compile
> the adopted policy into a complete finite DFA, discover an opaque Boolean substrate
> through the M013e probe interface, synthesise a native body there, and serialise the
> rewritten body, learned rewrite tools and declared learning state in one validated
> canonical packet. Compilation or migration failure restores the exact pre-run source,
> archive, digest ledger and learned-tool registry.

This is an integration result. It is not a canonical scientific evaluation and does
not show that the transported memory or tools improve later learning.

## Evaluated identity

- implementation commit: `4080ccc4b9381b1a2b0f8714e904c57335330877`;
- focused workflow run: `30769852599`;
- complete CI run: `30769852609`;
- focused M032 controls: 5 passed;
- complete repository suite: 211 passed on Python 3.11 and 211 passed on Python 3.13;
- repository integrity audit: passed.

## Controls passed

1. A strict M025 development improvement was independently adopted.
2. Exhaustive calls over every declared state-symbol pair compiled that adopted policy
   into the intended two-state parity DFA.
3. M013e discovered the destination opcode semantics without receiving its truth table
   and produced an equivalent opaque native body.
4. The M025 passport, source DFA, opaque body, opcode registry, memory, uncertainty and
   exploration frontier round-tripped canonically.
5. The embedded learned rewrite tool rehydrated from the transported M025 passport.
6. Identical inputs produced byte-identical packet JSON and SHA-256.
7. Forced substrate-probe exhaustion restored source, archive, digest ledger and learned
   tools exactly.
8. A policy that passed narrow M025 cases but left the declared finite state space was
   rejected after adoption and rolled back exactly.
9. Tampered source-DFA transitions, opaque-body versioning and opcode provenance were
   rejected during packet rehydration.

## What remains open

M032 transports a declared learning-state surface but does not yet demonstrate its
functional value. The next experiment must reveal a new task only after migration and
compare:

- the complete migrated M032 lineage;
- a fresh organism on substrate B;
- the unchanged parent lineage migrated to B;
- an output-only migrated body without plasticity;
- the improved lineage with learning state ablated;
- the improved lineage with learned rewrite tools ablated.

Autonomous diagnosis, operating-system sandboxing, repeated improvement cycles and a
single frozen ten-gate Genesis lineage remain unvalidated.
