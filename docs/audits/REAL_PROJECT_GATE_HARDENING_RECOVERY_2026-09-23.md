# Real-project gate hardening recovery — 23 September 2026

Status: **DEVELOPMENT instrument maintenance; no scientific result and no V22 rescore**.

## Source

Historical PR #315 (`claude/bold-lamport-psmcgu`) carried six unique commits after the generic
real-project gate had already entered the canonical repository. A consolidation audit found that the
branch still contained prospective gate hardening not present in current `main`.

Rather than merge the old branch wholesale, this recovery copies only the final versions of:

- `genesis/real_project.py`;
- `tests/test_real_project.py`;
- `scripts/run_real_project_self_application_rehearsal.py`.

Old branch-local state, superseded navigation and historical snapshot material remain on the original
branch for provenance and are not transplanted.

## Recovered protections

The recovered gate requires or records, among other things:

- explicit non-empty Genesis and host identity bindings;
- at least one explicit forbidden prefix;
- an overall evaluation budget large enough to cover a complete declared evaluation pass;
- path-policy overlap validation between writable, forbidden and authority regions;
- typed construction refusals so a stale base digest cannot masquerade as a boundary rejection;
- evidence that the complete bounded candidate image was measured;
- explicit safety/path-policy rejection witnesses;
- winner applied-path revalidation against the host path policy;
- refusal to begin a command when the remaining overall budget cannot cover its full declared
  timeout, rather than silently shortening the command;
- fail-closed handling of malformed/non-integer timeout declarations.

The accompanying self-application harness remains **non-canonical rehearsal apparatus**. It binds
Mira Genesis as its own host only to exercise the generic gate on real repository code; by design it
cannot satisfy the external-project criterion.

## Relationship to V22

V22's retained-evaluator apparatus was already frozen and merged before this recovery branch. These
changes do not alter:

- V22 task manifests;
- V22 proposer bundles;
- G1/G2 policy bytes;
- V22 reserved evaluator source;
- V22 utility;
- V22 campaign engine;
- V22 freeze identities.

They are maintenance for future real-project experiments and for the repository's generic gate.

## Historical integrity

PR #315 and its unique commits remain available as provenance until a later cleanup decision. This
recovery is not a claim that #315 itself was merged, nor does it rewrite its non-canonical rehearsal
into scientific evidence.
