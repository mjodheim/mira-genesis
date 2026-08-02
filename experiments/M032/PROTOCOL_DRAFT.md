# M032 — pre-result development protocol

## Question

Can one bounded lineage improve its executable body in substrate A, validate and adopt
that rewrite, discover an initially opaque substrate B, compile the improved competence
natively for B, and preserve the rewrite passport plus relevant learning state across
the boundary under one fail-closed transaction?

## Fixed construction path

1. Begin with an M020 `VersionedCodeBody`, its internal `ToolRegistry`, development
   cases and regression cases.
2. Run the unchanged M025 transaction. Candidate selection may use development evidence
   only; M023 independently checks parent, candidate and regression behaviour.
3. Compile the adopted bounded policy into a complete binary DFA by exhaustively calling
   `policy(state, symbol)` over every declared state and both symbols.
4. Reject the transaction if the policy returns a non-integer or leaves the declared
   finite state space.
5. Give M013e only the DFA passport and the public opaque-machine interface. It must
   discover opcode semantics by probing and synthesise the native body without a task
   oracle.
6. Package the exact M025 passport, source DFA, opaque body, discovered opcode
   identifiers, memory, uncertainty and exploration frontier in canonical JSON.
7. Rehydrate the packet and require byte-identical canonical serialisation.
8. If compilation, discovery, synthesis or packet validation fails, restore both the
   source body and learned-tool registry to their exact pre-run state.

## Development gates for the bridge

All gates below are required before M032 may be called a verified development base.

1. **Rewrite gate:** M025 reports an independently validated strict development
   improvement.
2. **Finite compilation gate:** the adopted source defines exactly one valid next state
   for every state-symbol pair in the declared DFA domain.
3. **Opaque discovery gate:** no evaluator truth table, opcode role or destination
   compiler is supplied to the lineage.
4. **Native equivalence gate:** the opaque native body and source DFA agree on every
   binary word through the pre-written exhaustive depth used by the test suite.
5. **State transport gate:** memory, uncertainty and exploration frontier round-trip
   exactly.
6. **Tool transport gate:** the embedded M025 passport digest and learned rewrite tool
   survive packet rehydration.
7. **Rollback gate:** forced substrate discovery failure restores source, archive,
   adopted digests and learned tools exactly.
8. **Invalid-body gate:** a source that passes the narrow M025 cases but leaves the
   declared finite state space is rejected and rolled back.
9. **Determinism gate:** repeated runs from identical inputs produce identical packet
   JSON and packet SHA-256, excluding elapsed time from scientific identity.
10. **Repository gate:** the complete test suite and integrity audit pass.

## Required controls for the later development comparison

The post-migration learning experiment must compare the complete lineage against:

- a fresh organism created directly on substrate B;
- the unchanged parent lineage migrated to B;
- the improved lineage with learned rewrite tools ablated;
- the improved lineage with memory and exploration state ablated;
- the improved lineage transported as output only, without retained plasticity.

The new task family must be generated and revealed only after migration. No threshold or
seed block may be selected after observing its result.

## Non-claims

This draft does not establish autonomous fault diagnosis, arbitrary multi-file rewrite,
operating-system sandboxing, post-migration advantage, repeated improvement cycles,
open-ended recursive self-improvement, consciousness or AGI.

A future canonical protocol would require a separate frozen commit, committed seeds,
one immutable run and a pre-written decision rule. Development success under this draft
must not be promoted to canonical evidence.
