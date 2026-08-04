# M040 — canonical cumulative post-migration plasticity protocol

**Status: frozen pre-result protocol.** The canonical task, seed and outcome do not exist
until the unique marker-only arming commit is created. No rule below may change after that
commit.

## Question

Can one deterministic lineage accumulate exact improvements and a lineage-owned tool in
substrate A, discover and migrate to an initially opaque substrate B, then use both its
transported tool and transported continuation state to diagnose and complete a further exact
self-rewrite on a task revealed only after migration?

The claim is bounded to the deterministic binary-DFA and opaque Boolean-machine families in
this repository. It is not a claim about arbitrary program synthesis, open-ended evolution,
general intelligence or consciousness.

## Frozen mechanism

The evaluated mechanism is the exact repository state immediately preceding the marker-only
arming commit. It must already have passed repository integrity and the complete Python 3.11
and Python 3.13 suites.

The canonical runner calls `run_m040_development` with:

- a master seed derived only after arming from the protocol SHA-256 and immutable arming head;
- the protocol SHA-256 as protocol commitment;
- `require_replay=True`;
- task family `lineage_anchor`.

No development seed is reused.

## Frozen constants

- pre-migration lineage: frozen M039 mechanism and constants;
- opaque-substrate probe budget: 120;
- migration candidate budget: 75,000;
- native component budget: 320;
- native serialisation budget: 16,777,216 bytes;
- post-migration observation depth: 6, yielding exactly 127 observations;
- post-migration symbolic depth: 4;
- equal symbolic-node budget for every search arm: 4,096;
- lineage-anchor enumeration bound: the committed M040 implementation;
- forced provisional failure and rollback attempts: one.

The 4,096-node budget was selected during consumed development before this freeze. It is not
presented as an independently chosen universal threshold.

## Continuous lineage

The complete arm must:

1. regenerate a fresh three-cycle M039-style lineage from the sealed M040 seed;
2. preserve its exact final DFA, cumulative registry and causal continuation state;
3. discover an opaque Boolean substrate through public probes only;
4. synthesise and verify an exact native body for the final pre-migration DFA;
5. commit and rehydrate an externally anchored transport packet;
6. derive the hidden post-migration task only after packet validation;
7. prove structural incapacity of the migrated parent from committed observations;
8. reuse a lineage-owned pre-migration transformation anchor and add bounded primitive
   adaptation;
9. adopt an exact larger source DFA and synthesise its exact native body on B;
10. reject a fixed bad provisional source/native pair and restore the accepted pair exactly;
11. reproduce all pre- and post-migration searches, packets, journals, controls and decisions
    from the seed and immutable inputs.

## Controls

All search-capable arms receive the same observations, symbolic depth and node budget:

- complete migrated lineage;
- fresh organism on B;
- unchanged founder migrated to B;
- output-only migrated body without portable rewrite state;
- learning-state ablation retaining the registry;
- learned-tool ablation retaining sanitised non-tool state.

The unchanged-founder control must have a separately synthesised exact native body on the same
opaque substrate. The output-only arm retains the real migrated output quality but cannot
propose a rewrite.

## Primary verdicts

### Trans-substrate continuity supported

All of the following must hold:

- three accepted exact pre-migration cycles;
- exact migration and canonical packet rehydration;
- post-migration task derivation after packet validation;
- valid recomputed incapacity certificate;
- exact accepted source and native post-migration bodies;
- exact forced rollback;
- exact seed-only replay of committed identities and journal bytes.

### Post-migration plasticity supported

Continuity must be supported and all of the following must hold:

- the complete migrated lineage reaches exact quality 127/127;
- fresh-on-B, unchanged-parent, output-only and learned-tool-ablated controls are not exact
  under the equal budget;
- the complete arm uses fewer symbolic nodes than the learning-state ablation;
- the accepted proposal causally uses a lineage-owned tool created before migration;
- the independent search audit reproduces every arm and confirms the learned-tool ablation.

A continuity-positive/plasticity-negative outcome is a valid negative M040 result.

## Replay and independent verification

Replay may receive only the sealed master seed, frozen protocol commitment, immutable code and
expected external identities. It may not receive a target DFA, accepted program, discovered
substrate, control outcome or mutation trace from the first execution.

The persisted-result verifier must recompute the causal journal chain, event order, arm/audit
agreement, equal budgets, packet and migration identities, native controls and rollback
identities. Mutation probes must reject altered persisted results.

## Canonical seed derivation

The runner computes:

`SHA-256("m040-canonical-seed-v1" || protocol_sha256 || arming_head_sha)`

and interprets the first eight bytes as an unsigned big-endian integer. The seed therefore
cannot be known before the immutable marker-only arming commit exists.

## Integrity rule

The canonical workflow runs once on the marker-only arming commit. A scientific negative is a
successful canonical execution and must be preserved. No rerun replaces the first artefact,
no budget or verdict rule is relaxed, and no second M040 seed is opened. Any later repair must
be a separately named experiment with its own frozen protocol.
