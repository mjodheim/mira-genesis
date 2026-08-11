# Claude instructions — Mira Genesis public repository

This repository is **public**. Before changing it, read and follow [`AGENTS.md`](AGENTS.md), especially
the prospective IP/publication boundary.

## Non-negotiable public/private boundary

- M085 and earlier already-public material remain public under their existing licences and scientific
  records.
- M085's independent external-maintainer requirement must remain genuine; do not replace it with
  project-authored or project-controlled AI-generated evidence.
- Starting with M086, materially new enabling core R&D is **private before publication review by
  default** under [`docs/IP_PUBLICATION_POLICY.md`](docs/IP_PUBLICATION_POLICY.md).
- Do **not** implement, scaffold, prototype, commit, branch, discuss in public issues/PRs, or leak via
  CI/artifacts any unpublished M086+ core mechanism in this repository.
- If a request would require such implementation, stop before generating/committing the enabling
  details and state that the work belongs in the project's private R&D workspace.

The private-workspace procedure is
[`docs/PRIVATE_RND_OPERATIONS.md`](docs/PRIVATE_RND_OPERATIONS.md). It covers repository separation,
AI-provider data controls, private scientific provenance and controlled publication back to the
public repository.

Do not weaken this boundary by labelling new core research as a refactor, documentation task,
benchmark preparation or harmless experiment scaffolding.

## Scientific integrity

Private R&D does not permit retroactive scientific repair. Preserve frozen protocols, negative
results, Track A / Track B attribution and the evidentiary thresholds in the project registers.

## Provenance

Anthony Mets (`mjodheim`) is recorded at the 12 August 2026 snapshot as the sole human developer and
research director. Anthropic Claude, OpenAI Codex and historical OpenAI ChatGPT usage are recorded as
AI development assistance. This is a production-provenance record, not a claim that AI-provider
terms clear third-party rights or settle legal authorship/inventorship.

Review before material work:

- [`AGENTS.md`](AGENTS.md)
- [`AUTHORS.md`](AUTHORS.md)
- [`docs/AI_ASSISTED_DEVELOPMENT_PROVENANCE.md`](docs/AI_ASSISTED_DEVELOPMENT_PROVENANCE.md)
- [`IP_ASSET_REGISTER.md`](IP_ASSET_REGISTER.md)
- [`docs/THIRD_PARTY_DEPENDENCIES.md`](docs/THIRD_PARTY_DEPENDENCIES.md)
- [`docs/PRIVATE_RND_OPERATIONS.md`](docs/PRIVATE_RND_OPERATIONS.md)
- [`CONTRIBUTING.md`](CONTRIBUTING.md)

When publication status is ambiguous, fail closed: do not put the enabling implementation in the
public repository.
