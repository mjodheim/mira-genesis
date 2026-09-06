# M125/H70 binding design corrigendum — Hati audit — 6 September 2026

**Status:** BINDING BEFORE IMPLEMENTATION  
**Applies to:** `docs/audits/M125_PREIMPLEMENTATION_REVIEW_2026-09-06.md`  
**Scientific observations added:** 0  
**Network authority added:** none  
**Scientific-run authority added:** none

Hati independently reviewed the prospective M125/H70 handoff after P-029 and returned `GO OFFLINE IMPLEMENTATION` subject to three blocking design corrections. This corrigendum records those corrections prospectively, before any M125 implementation or network request.

If any wording in the earlier M125 preimplementation review conflicts with this corrigendum, **this corrigendum controls**. It does not reinterpret M122, M123 or M124 and does not authorize any M125 network observation.

A subsequent Codex hostile review of this corrigendum identified two additional bypasses inside C1/C2. They are incorporated below as part of the same binding corrections: archived attempts must be enumerated from committed `HEAD` as well as the working tree, and every interpreting working-tree source must itself match the committed `HEAD` blob before Python may execute it.

## C1 — terminal-result anti-rearm guard — HIGH

The M125 network-capable entry point must fail closed before any request if a terminal M125 readiness result already exists in **any** authoritative result surface:

1. the working-tree `experiments/M125/READINESS_RESULT.json`, if present;
2. the `HEAD` blob for that canonical path, even if the working-tree copy was deleted or replaced;
3. every M125 archived readiness attempt/result present in the working-tree milestone archive;
4. every M125 archived readiness attempt/result path present in the committed `HEAD` tree, enumerated from Git rather than inferred from the working-tree directory.

The archived-attempt path set used by the guard is the **union** of the working-tree archive paths and the paths enumerated from committed `HEAD`. For every path present at `HEAD`, the committed blob must be read and classified even if the file was deleted, renamed or replaced locally. A working-tree glob alone is not an authoritative archive inventory.

A terminal result means any M125 verdict other than the specifically predeclared whole-instrument delivery-only closure that the frozen retry policy permits to consume a remaining global delivery slot. Missing, malformed or unrecognized verdict fields are refusal conditions, not permission.

A terminal committed/archive result cannot be superseded by deleting, replacing, renaming or editing the mutable result or an archived attempt. The guard must inspect all four surfaces and refuse if **any one** proves a terminal M125 result exists.

Offline tests must cover at least:

- terminal working-tree result -> refuse;
- terminal canonical `HEAD` blob replaced locally by delivery-only result -> refuse;
- terminal canonical `HEAD` blob deleted locally -> refuse;
- terminal working-tree archived attempt with mutable result removed -> refuse;
- terminal archived-attempt blob present in `HEAD` but deleted locally -> refuse;
- terminal archived-attempt blob present in `HEAD` but replaced locally by a delivery-only record -> refuse;
- archive enumeration from `HEAD` cannot be reduced by local rename/delete operations;
- missing/unrecognized verdict in any existing working-tree or committed result surface -> refuse;
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

Immediately before any network-capable execution, the entry point must perform **both** checks below for every manifest-listed path before importing/executing measurement logic:

1. read the committed `HEAD` blob, LF-normalize it, hash it and require exact equality with the manifest entry bound by the frozen protocol;
2. read the working-tree file, LF-normalize it and require byte equality with that committed `HEAD` blob.

A missing working-tree source, an uncommitted edit, a locally substituted module, or a committed source change after freeze is therefore a refusal condition. It is not sufficient to recompute hashes from `HEAD` while Python later imports potentially dirty working-tree bytes. If the implementation instead executes committed blobs through an isolated mechanism, that mechanism itself must be manifest-bound and demonstrated by tests; the default design is working-tree/HEAD equality before import.

The protocol/freezing gate must run before importing any M125 helper whose local bytes could affect measurement semantics, except for a minimal gate module whose own bytes are themselves bound and whose job is only to verify committed identities. No interpreting source may become executable merely because the committed copy hashes correctly while the working tree differs.

Offline tests must cover at least:

- changing a manifest digest -> refuse before credential/network;
- modifying a manifest-listed working-tree source without committing it while `HEAD` still matches the frozen manifest -> refuse;
- deleting or substituting a manifest-listed working-tree source -> refuse;
- changing a committed manifest-listed source after freeze -> protocol mismatch/refuse.

## C3 — execution gate precedes credential access — MEDIUM

The M125 `--execute` ordering is mandatory and fail-closed:

1. parse non-secret local arguments;
2. inspect anti-rearm result surfaces, including canonical and archived working-tree/`HEAD` records;
3. load the committed frozen protocol record;
4. prove that the protocol record is committed at `HEAD` and matches the working tree;
5. verify `protocol_sha256`, the committed interpreting-source manifest **and working-tree equality for every manifest-listed source**, before importing/executing those interpreting sources;
6. load the separately committed network-authorization record, when one exists;
7. verify that authorization is committed at `HEAD`, authorizes DEVELOPMENT network observation only, and names the exact `protocol_sha256`;
8. verify global/local delivery accounting and logical-step resume state;
9. **only then** read `OPENROUTER_API_KEY` or any other credential source;
10. only after credential success may transport construction or network I/O become reachable.

Today no M125 network-authorization record exists, so step 6 must fail closed and steps 9–10 must remain unreachable.

Offline tests must set a sentinel credential accessor that raises or records access and prove that every missing/stale/mismatched protocol, dirty-source, anti-rearm or authorization condition refuses **without touching the credential accessor**. A test that merely proves "no HTTP request occurred" is insufficient.

## Updated required-test delta

The earlier test list remains binding and gains these explicit requirements:

23. terminal M125 canonical result surfaces are checked across working tree and `HEAD` and cannot be rearmed by delete/replace;
24. archived M125 attempt paths are enumerated independently from both working tree and committed `HEAD`, and the union is inspected;
25. a terminal archived attempt committed at `HEAD` still refuses when its working-tree file is deleted, renamed or replaced;
26. missing or unrecognized verdict fields in any existing M125 result surface fail closed;
27. the frozen protocol contains a deterministic interpreting-source SHA256 manifest;
28. changing any bound committed interpreting-source digest invalidates the protocol before execution;
29. an uncommitted working-tree edit to a manifest-listed source refuses even when the corresponding `HEAD` blob still matches the frozen manifest;
30. a missing/substituted manifest-listed working-tree source refuses before interpreting code, credential access or network I/O;
31. protocol and network authorization are verified before credential access;
32. credential access is mechanically proven unreachable for missing/stale/mismatched protocol, dirty-source or authorization state;
33. any future authorization record must bind the exact frozen `protocol_sha256` and DEVELOPMENT-only scope.

## Result of the Hati audit

With C1–C3, including the Codex refinements above, made binding here, the design disposition is:

**`GO OFFLINE IMPLEMENTATION`**

That disposition authorizes only the implementation and offline tests already allowed by P-029. It does **not** authorize creation of a network authorization, any M125 request, any H70 qualifying generation, bank materialization, seal, reveal, scoring or result acceptance.

The next owner gate remains the separately reviewed authorization of the exact frozen M125 DEVELOPMENT network protocol after implementation, offline tests, CI, hostile review and protocol digest verification are complete.
