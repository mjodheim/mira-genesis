# P-031 — Real-project transfer apparatus pre-publication review

**Decision date:** 12 September 2026  
**Disposition:** `PUBLIC_AGPL_COMMERCIAL_OPTION`  
**Owner / research director:** Anthony Mets  
**Scope:** generic Genesis adapter and non-confidential evidence for evaluating bounded mutations of an external software host

## Asset being disclosed

This review covers a generic DEVELOPMENT adapter that binds Genesis to an externally supplied project snapshot and host-owned evaluation manifest. The adapter may create disposable workspaces, apply bounded candidate file mutations, execute finite evaluator commands, compare externally measured outcomes and emit provenance/evidence records.

The prospectively frozen scientific target is `docs/REAL_PROJECT_TRANSFER_TARGET.md`.

## Private-host boundary

The first canonical host may be a private project. This public review does **not** authorize publication of private host source, credentials, environment files, deployment configuration, confidential logs, private prompts or other material that is not already intentionally public.

Public Genesis code must remain host-agnostic. Host-specific source paths, tests, candidate content and operational configuration stay in the host repository unless the owner separately decides to publish them.

A public reproduction record may retain non-confidential content identities, aggregate verdicts and generic evidence needed to audit the Genesis mechanism, provided those records do not reconstruct private host content.

## Provenance and dependencies

Anthony Mets remains the sole human research director and publication/acceptance authority. Substantial AI assistance is handled under the existing AI-assisted development provenance record.

The intended generic adapter uses project-controlled Python, the standard library, Git/process/filesystem interfaces and the repository's existing test tooling. No new external dataset, model weight or confidential third-party code is required by the generic mechanism itself.

If host-side integration introduces a new third-party dependency or confidential asset, that asset remains subject to the host repository's own review and licensing obligations.

## IP / publication decision

No concrete `PATENT_FIRST`, `TRADE_SECRET_PRIVATE`, `CONFIDENTIAL_THIRD_PARTY`, `CONTRACTUAL_EMBARGO`, `SECURITY_SENSITIVE` or `COMMERCIAL_PRIVATE` reason has been identified for the **generic** adapter. It therefore follows the project's public-first policy:

- project-controlled software: `AGPL-3.0-only`;
- research prose/results: repository documentation licence (`CC-BY-4.0` where applicable);
- separate commercial permissions remain possible for rights controlled by the project owner.

Private host material remains private and is not relicensed merely because Genesis evaluates it.

## Scientific and authority boundary

The adapter must preserve the existing Genesis trust/evaluation boundary. The mutable candidate may not rewrite the evaluator, the acceptance rule, the bound manifest or Genesis trust-root authority. Candidate execution must occur in disposable workspace state rather than in the live deployment.

A successful real-project transfer is one bounded DEVELOPMENT case. It is not evidence of cross-project generality or permission for autonomous production deployment.

## Owner decision

Proceed publicly with the generic real-project transfer apparatus under `PUBLIC_AGPL_COMMERCIAL_OPTION`, while keeping private-host source and operational material confined to the host repository and preserving the frozen target and authority boundaries above.
