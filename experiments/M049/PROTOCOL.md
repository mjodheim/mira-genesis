# M049 — bounded migration-strategy selection

**Status: PASSED IN DEVELOPMENT.**

## Recorded qualification

CI run `31076192847` (run number `408`) qualified commit `b8a8bb064ff456c491369bd1ca25c72ca187b545` on the first attempt:

- `812` tests passed on Python `3.11.15` with Node.js `20.20.2`;
- `812` tests passed on Python `3.13` with the same pinned Node.js target runtime;
- repository integrity passed clean imports, orphan detection and dependency consistency;
- no job failed and no rerun was used.

The code-qualified head is followed only by documentation consolidation commits marked `skip ci`. The authoritative development result is preserved in `DEVELOPMENT_RESULT.md`.

## Question

Can the continuing research lineage choose one migration strategy from a fixed admissible family using public evidence only, then obtain an independent verdict from hidden evidence?

M049 narrows the next frontier after M048. It does not construct arbitrary compilers, discover unknown runtimes, search source strings or grant external authority.

## Fixed strategy family

The proposal surface is frozen to four target-runtime strategy records:

- maximum with zero on empty input;
- minimum with zero on empty input;
- sum with zero on empty input;
- floor mean with zero on empty input.

Each strategy is represented by canonical metadata and a domain-separated digest. The selector may only eliminate strategies using public probes. It receives no hidden probes.

## Independent validation

Only a uniquely selected strategy may be submitted to validation. The validator:

- receives hidden probes;
- verifies the strategy artifact digest;
- verifies membership in the frozen family;
- returns an immutable verdict digest;
- has no adoption, repository, network or deployment authority.

## Required negative episode

A separate public probe set intentionally leaves all four strategies plausible. The selector must terminate with `insufficient_evidence`, preserve the surviving strategy identities and avoid arbitrary tie-breaking.

## Resource and claim boundary

- strategy budget: exactly four;
- public selection: deterministic elimination only;
- hidden validation: independent function boundary;
- arbitrary compiler synthesis: forbidden;
- unknown-runtime discovery: absent;
- repository, credential, network and deployment authority: absent;
- canonical claim: forbidden.

M049 is a bounded development probe of migration-strategy acquisition. The positive result does not establish general translation, open-ended evolution, AGI, consciousness or production safety. M042 remains the only positive canonical continuous-lineage completion.

## Qualification criteria

M049 passed in development because permanent tests establish:

1. unique public evidence selects the correct frozen strategy;
2. ambiguous and contradictory evidence fail closed;
3. hidden validation accepts the correct artifact;
4. tampered or out-of-family artifacts are rejected;
5. empty public or hidden evidence is rejected;
6. the complete manifest is deterministic;
7. all authority and claim boundaries remain explicit and false.
