# M024 — Rewrite-passport protocol draft

**Status: DEVELOPMENT ONLY. Not frozen or canonical.**

## Question

Can the complete bounded M020 self-rewrite state cross a serialisation boundary while
preserving executable behaviour, learned rewrite capability and exact rollback, with
inconsistent or corrupted state rejected before any live body is created?

## Passport boundary

One passport contains:

- the active policy source and function name;
- the exact rollback-source stack;
- the adopted-body digest ledger;
- the primitive rewrite-tool configuration;
- every learned patch-tool name and ordered operation trace.

The payload is canonical JSON. An outer envelope records the payload's SHA-256 digest.
Import verifies the envelope and every semantic invariant before rehydrating a
`VersionedCodeBody` or `ToolRegistry`.

## Import invariants

Import must reject the bundle unless all of the following hold:

1. envelope and passport versions are known;
2. the payload digest matches its canonical representation;
3. active and archived sources belong to M020's bounded policy language;
4. every recorded digest is a lowercase SHA-256 value;
5. the active source matches the latest adopted digest;
6. archived sources occur in order in the prior adopted-digest history;
7. primitive tool names match their declared kinds and configuration;
8. learned tool names are unique and derived from their exact operation traces;
9. each learned trace can still be replayed on at least one source in the lineage.

Validation completes before the imported state is returned to the caller. A rejected
passport must not expose a partially populated body or registry.

## Development gates

- two exports of the same state are byte-identical;
- active source, archive, digest history and tool state round-trip exactly;
- the migrated body preserves held-out behaviour;
- a learned two-edit tool remains reusable on a structurally equivalent body;
- rollback after migration restores the exact parent source and behaviour;
- direct envelope tampering is rejected;
- rehashed but internally inconsistent active or archived source is rejected;
- malformed digest, primitive-tool and learned-operation records are rejected.

## Security boundary

SHA-256 detects corruption and inconsistent evidence; it is not a digital signature.
An actor allowed to replace the full payload and all of its evidence can create a new
self-consistent passport. Authentic provenance therefore requires a later signed or
content-addressed release boundary.

M024 does not translate Python source into a new substrate, provide M023's operating-
system isolation, encrypt state, migrate autobiographical memory, or establish
post-migration learning advantage.
