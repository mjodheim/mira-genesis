# Genesis real-project transfer target — prospective DEVELOPMENT criterion

Date: 2026-09-12
Status: **FROZEN BEFORE IMPLEMENTATION**

## Question

Can the validated Genesis lineage machinery operate against a real external software project rather than a project-authored toy body, while preserving an evaluator and authority boundary outside the mutable candidate?

This target is intentionally narrower than generality. It is a transfer/integration question over one real software host and does not reopen or reinterpret the validated Genesis v1/v2 milestones.

## Host contract

A real-project run must be bound before candidate evaluation to a host manifest containing at least:

- a content identity for the exact host snapshot;
- one or more writable project-relative path prefixes;
- explicit forbidden path prefixes;
- immutable evaluation commands represented as argv arrays, never candidate-authored shell text;
- finite per-command timeouts and an overall evaluation budget;
- a baseline evaluation record from the unchanged host snapshot;
- a deterministic acceptance rule;
- the Genesis trust/evaluation identities used for the run.

The mutable candidate may change only files inside the admitted writable prefixes. It may not change the host manifest, evaluator commands, acceptance rule, Genesis trust root, Genesis evaluation contract, or any file designated as authority/evaluation apparatus.

## Required evidence

The DEVELOPMENT real-project stopping criterion is satisfied only when one canonical run establishes all of the following mechanically:

1. **Exact external host identity.** The evaluated baseline is an exact snapshot of an external project, not a copied synthetic fixture authored for this test. The report binds its identity before candidate evaluation.
2. **Baseline first.** The unchanged host snapshot is evaluated with the same command set and limits used for candidates. A candidate is never accepted against an assumed baseline.
3. **Workspace isolation.** Candidate evaluation occurs in a disposable workspace. The source snapshot and any configured production/deployment path remain byte-identical after both rejected and accepted candidate evaluations.
4. **Complete admitted mutation image.** For the canonical objective, every candidate in the prospectively admitted bounded candidate set is either evaluated or recorded as a deterministic construction refusal. The winner is not chosen from an unreported hand-picked subset.
5. **External measurement.** Build/test/contract outcomes are derived from process exit status and captured output under the host-owned evaluator. Candidate self-report is not an acceptance input.
6. **Safety invariants.** At least one syntactically valid but contract-unsafe or boundary-violating candidate is rejected, and at least one otherwise plausible candidate that fails a real host check is rejected.
7. **Measured useful improvement.** At least one candidate is accepted because it satisfies all mandatory regressions and strictly improves a prospectively declared objective component over the baseline. Merely compiling, changing files, or receiving an LLM preference is insufficient.
8. **No evaluator mutation.** The accepted candidate's diff is proved disjoint from evaluator/authority files and from every forbidden prefix.
9. **Deterministic replay.** Re-evaluating the accepted candidate from the same bound host snapshot reproduces the same semantic verdict and objective vector without relying on process-local state.
10. **Rollback/refusal.** A rejected candidate leaves no persistent host mutation, and the acceptance path remains an artifact/patch in the isolated integration workflow rather than an automatic write to the host project's protected/default branch or live deployment.
11. **Cross-repository provenance.** The final report binds both Genesis and host identities and records the exact candidate artifact/diff digest that received the verdict.
12. **Existing Genesis guarantees remain intact.** The complete Genesis regression suite and historical scientific boundaries remain green after adding the generic adapter.

## Canonical first use

The first canonical host may supply a real self-modification or tool-promotion surface. The generic Genesis adapter must not contain host-specific source code, expected patch contents, or an answer keyed to the canonical host. Host-specific candidate generation and evaluation configuration belong in the host-side integration manifest.

## Strongest permitted claim if satisfied

> Genesis can carry its bounded evidence-based selection discipline into a real external software project, evaluate real project mutations under host-owned build/test/safety checks, and preserve an external authority boundary.

This does **not** establish cross-project generality, autonomous arbitrary software engineering, safe production self-modification, AGI, or unbounded recursive self-improvement. One host is one transfer case.

## Fail-closed publication rule

If the canonical host is private, the public record may disclose only non-confidential identities/digests and generic evidence. Private source, secrets, deployment configuration, prompts containing private material, and raw logs that expose confidential host content must remain outside the public repository.

Any broader claim requires a new prospectively written target rather than changing this criterion after seeing the result.
