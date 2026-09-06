# M125/H70 binding design corrigendum — Hati audit — 6 September 2026

**Status:** BINDING BEFORE IMPLEMENTATION  
**Applies to:** `docs/audits/M125_PREIMPLEMENTATION_REVIEW_2026-09-06.md`  
**Scientific observations added:** 0  
**Network authority added:** none  
**Scientific-run authority added:** none

Hati independently reviewed the prospective M125/H70 handoff after P-029 and returned `GO OFFLINE IMPLEMENTATION` subject to three blocking design corrections. This corrigendum records those corrections prospectively, before any M125 implementation or network request.

If any wording in the earlier M125 preimplementation review conflicts with this corrigendum, **this corrigendum controls**. It does not reinterpret M122, M123 or M124 and does not authorize any M125 network observation.

## C1 — terminal-result anti-rearm guard — HIGH

The M125 network-capable entry point must fail closed before any request if a terminal M125 readiness result already exists in **any** authoritative result surface:

1. the working-tree `experiments/M125/READINESS_RESULT.json`, if present;
2. the `HEAD` blob for that path, even if the working-tree copy was deleted or replaced;
3. every immutable archived M125 readiness attempt/result under the milestone archive.

A terminal result means any M125 verdict other than the specifically predeclared whole-instrument delivery-only closure that the frozen retry policy permits to consume a remaining global delivery slot. Missing, malformed or unrecognized verdict fields are refusal conditions, not permission.

A terminal committed/archive result cannot be superseded by deleting, replacing or editing the mutable result file. The guard must inspect all three sources and refuse if **any one** proves a terminal M125 result exists.

Offline tests must cover at least:

- terminal working-tree result -> refuse;
- terminal `HEAD` blob replaced locally by delivery-only result -> refuse;
- terminal `HEAD` blob deleted locally -> refuse;
- terminal archived attempt with mutable result removed -> refuse;
- missing/unrecognized verdict in an existing result surface -> refuse;
- a genuinely permitted delivery-only continuation may resume only at the first unanswered logical step and may never redraw a completed step.

This is an anti-reinterpretation and anti-redraw guard. It does not change M124's historical runner.

## C2 — `protocol_sha256` binds interpreting source bytes — HIGH

The frozen M125 protocol digest must bind not only parameters and schemas but also a **source manifest** of every project-controlled module whose bytes can change how an observation is transported, classified, validated, sized, resumed or turned into a verdict.

Before the first M125 request, the protocol record must contain a deterministic mapping:

`repository-relative source path -> SHA256(LF-normalized committed bytes)`

At minimum the manifest must include the final M125 equivalents of:

- the M125 readiness/network runner;
- the bounded capability-probe builder and coverage checker;
- the pinned stress-schema/calibration/sizing module;
- the chronology/network-authorization guard;
- the JSON-schema validator/census implementation actually used;
- the inherited carrier-contract module actually used;
- the fixed route identity module actually used;
- any helper module that implements the shared `answered` predicate, retry policy, `Retry-After` parsing, verdict ladder, logical-step journal, delivery accounting or final-size derivation.

The manifest itself is part of `protocol_sha256`. Paths must be explicit; importing a module by name without binding its committed source bytes is insufficient.

Immediately before any network-capable execution, the entry point must recompute the manifest from committed `HEAD` bytes and require exact equality with the frozen protocol record. A source change after freeze therefore changes the effective protocol and causes refusal; it cannot silently alter interpretation while retaining an old digest.

Offline tests must mutate or substitute at least one interpreting-source digest and prove execution refuses before credential access or network I/O.

## C3 — execution gate precedes credential access — MEDIUM

The M125 `--execute` ordering is mandatory and fail-closed:

1. parse non-secret local arguments;
2. inspect anti-rearm result surfaces;
3. load the committed frozen protocol record;
4. prove that the protocol record is committed at `HEAD` and matches the working tree;
5. recompute and verify `protocol_sha256`, including the interpreting-source manifest;
6. load the separately committed network-authorization record, when one exists;
7. verify that authorization is committed at `HEAD`, authorizes DEVELOPMENT network observation only, and names the exact `protocol_sha256`;
8. verify global/local delivery accounting and logical-step resume state;
9. **only then** read `OPENROUTER_API_KEY` or any other credential source;
10. only after credential success may transport construction or network I/O become reachable.

Today no M125 network-authorization record exists, so step 6 must fail closed and steps 9–10 must remain unreachable.

Offline tests must set a sentinel credential accessor that raises or records access and prove that every missing/stale/mismatched protocol or authorization condition refuses **without touching the credential accessor**. A test that merely proves "no HTTP request occurred" is insufficient.

## Updated required-test delta

The earlier test list remains binding and gains these explicit requirements:

23. terminal M125 result surfaces are checked across working tree, `HEAD` and archives and cannot be rearmed by delete/replace;
24. missing or unrecognized verdict fields in an existing M125 result surface fail closed;
25. the frozen protocol contains a deterministic interpreting-source SHA256 manifest;
26. changing any bound interpreting-source digest invalidates the protocol before execution;
27. protocol and network authorization are verified before credential access;
28. credential access is mechanically proven unreachable for missing/stale/mismatched authorization;
29. any future authorization record must bind the exact frozen `protocol_sha256` and DEVELOPMENT-only scope.

## Result of the Hati audit

With C1–C3 made binding here, the design disposition is:

**`GO OFFLINE IMPLEMENTATION`**

That disposition authorizes only the implementation and offline tests already allowed by P-029. It does **not** authorize creation of a network authorization, any M125 request, any H70 qualifying generation, bank materialization, seal, reveal, scoring or result acceptance.

The next owner gate remains the separately reviewed authorization of the exact frozen M125 DEVELOPMENT network protocol after implementation, offline tests, CI, hostile review and protocol digest verification are complete.
