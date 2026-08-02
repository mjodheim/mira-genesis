# M032 status

**Status: IMPLEMENTATION OPEN — DEVELOPMENT EVIDENCE PENDING**

The first bridge implementation now exists on the M032 research branch:

- M025 remains the sole rewrite, independent-adoption and passport mechanism;
- an exhaustive finite compiler converts an adopted two-argument policy into a DFA;
- M013e remains the sole opaque-substrate discovery and native synthesis mechanism;
- a canonical packet carries the M025 passport, source DFA, opaque body, discovered
  opcode identifiers, memory, uncertainty and exploration frontier;
- bridge or migration failure restores the original body and learned-tool registry.

Three focused tests are present but their GitHub Actions result has not yet been observed:

1. successful rewritten-body migration with exact learning-state transport;
2. forced substrate-probe failure with exact rollback;
3. an adopted source that leaves the declared finite state space with exact rollback.

No scientific or development claim is supported until the branch CI and repository
integrity checks pass. Post-migration learning controls and the new task family remain
unimplemented.
