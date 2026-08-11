# Coding-agent instructions — public repository boundary

These instructions apply to every coding/research agent operating in this **public** repository.
They are a fail-closed publication boundary, not a change to any historical licence or scientific
result.

## 1. This repository is public

Treat every branch, commit, issue, pull request, workflow log, artifact, attachment and prompt copied
into this repository as potentially public disclosure.

Never place credentials, private task-bank material, confidential third-party data or unpublished
private R&D here.

## 2. M086+ core R&D must not be implemented here

Starting with M086, any materially new enabling mechanism covered by
[`docs/IP_PUBLICATION_POLICY.md`](docs/IP_PUBLICATION_POLICY.md) is **private before publication
review by default**.

Do **not** use this public repository to:

- implement, scaffold or prototype a new M086+ core mechanism;
- create a public branch whose commits contain enabling M086+ implementation details;
- place such details in an issue, PR description/comment, CI log, artifact or benchmark payload;
- reconstruct private M086+ code from descriptions and then commit it here;
- weaken the boundary by calling private core work a documentation change, refactor or experiment
  preparation.

If a requested task would require materially new M086+ core implementation, **stop before generating
or committing that implementation** and report that the task belongs in the project's private R&D
workspace. Do not create a placeholder containing the secret design.

The operating procedure for that separate workspace is documented in
[`docs/PRIVATE_RND_OPERATIONS.md`](docs/PRIVATE_RND_OPERATIONS.md). It includes repository separation,
AI-provider data controls, private scientific provenance and the controlled public hand-back rule.

M086+ is a prospective boundary. It does not make M085 or earlier public material private after the
fact.

## 3. Work that may continue in the public repository

Public work may include, when scientifically and legally appropriate:

- maintenance, bug fixes and reproducibility work on already-public M085-and-earlier material;
- completion of M085 strictly under its frozen independent-maintainer boundary;
- documentation, governance, provenance, licensing and integrity work that does not disclose private
  enabling R&D;
- publication of a future private result **only after** an explicit publication disposition has been
  recorded according to the IP policy.

Do not infer permission to publish merely because a task can be completed with public dependencies.
The mechanism itself may still be private.

## 4. Scientific boundaries remain mandatory

IP protection must never be used to alter the scientific record. In particular:

- do not repair a frozen protocol after seeing a result and present it as precommitted;
- do not hide or rewrite an already-public negative result;
- do not simulate M085's independent external maintainer with project-authored material or another
  project-controlled AI agent;
- preserve Track A / Track B attribution boundaries;
- do not claim a generality/completion gate without the evidence required by the frozen criteria.

If confidentiality and a scientific commitment conflict, resolve the IP disposition **before**
materialising or publicly committing the experiment.

## 5. Human and AI provenance

Anthony Mets (`mjodheim`) is recorded at the 12 August 2026 snapshot as the sole human developer and
research director. OpenAI Codex, Anthropic Claude and historical OpenAI ChatGPT usage are recorded as
AI development assistance, not as additional human contributors.

Read:

- [`AUTHORS.md`](AUTHORS.md)
- [`docs/AI_ASSISTED_DEVELOPMENT_PROVENANCE.md`](docs/AI_ASSISTED_DEVELOPMENT_PROVENANCE.md)
- [`IP_ASSET_REGISTER.md`](IP_ASSET_REGISTER.md)
- [`docs/THIRD_PARTY_DEPENDENCIES.md`](docs/THIRD_PARTY_DEPENDENCIES.md)
- [`docs/PRIVATE_RND_OPERATIONS.md`](docs/PRIVATE_RND_OPERATIONS.md)

Generated code is not presumed free of third-party obligations. Preserve and review provenance for
material accepted output.

## 6. External human contributions

Follow [`CONTRIBUTING.md`](CONTRIBUTING.md). Do not merge externally authored copyrightable material
merely under DCO sign-off while the current contributor-rights boundary is active.

## 7. Fail closed on publication ambiguity

When uncertain whether a requested change would disclose a materially new core mechanism, prefer
**not publishing it in this repository**. Describe the boundary, not the private mechanism, and defer
the implementation to the private R&D workspace.

The publication decision belongs to the project owner and must be recorded before disclosure under
`IP_ASSET_REGISTER.md` or its private successor.
