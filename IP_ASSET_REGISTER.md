# Mira Genesis — IP asset register

**Current audit snapshot: 12 August 2026**

This register supports provenance, licensing, publication decisions and future due diligence. It is
not a legal opinion and does not create ownership where applicable law or a third-party licence says
otherwise.

## Control and provenance snapshot

- Project: **Mira Genesis**
- Repository: `mjodheim/mira-genesis`
- Project author / research director: **Anthony Mets** (`mjodheim`)
- Human-development declaration at this snapshot: **Anthony Mets is the sole human developer and
  research director of Mira Genesis**.
- GitHub contributor enumeration observed at this audit: the `mjodheim` human account plus repository
  automation; no second human contributor account was observed.
- Copyright notice used by the repository: `Copyright (C) 2026 Anthony Mets.`
- Public repository visibility at this audit: **public**.
- AI development assistance is explicitly recorded in
  [`docs/AI_ASSISTED_DEVELOPMENT_PROVENANCE.md`](docs/AI_ASSISTED_DEVELOPMENT_PROVENANCE.md): OpenAI
  Codex, Anthropic Claude, OpenAI ChatGPT where historically used, and repository automation.
- `AUTHORS.md` separates the human project role from AI/tool assistance.
- Externally authored copyrightable material is not currently accepted for merge unless an
  appropriate contributor-rights arrangement has first been approved. DCO sign-off is provenance,
  not copyright assignment.
- The initial third-party/tooling inventory is recorded in
  [`docs/THIRD_PARTY_DEPENDENCIES.md`](docs/THIRD_PARTY_DEPENDENCIES.md).

The sole-human declaration, Git history and contributor enumeration materially simplify diligence
relative to a repository with multiple uncontracted human copyright holders. They are still evidence,
not a substitute for claim-specific legal analysis of authorship, inventorship, copyrightability,
third-party provenance or contractual encumbrances.

## Asset classes

| Asset class | Current status | Current / intended treatment | Due-diligence note |
|---|---|---|---|
| Public software through M085 / current public research line | Public | `AGPL-3.0-only` under `LICENSE_POLICY.md` | Existing grants are not withdrawn by the prospective IP policy. |
| Public research prose, protocols and records | Public | `CC-BY-4.0` where `LICENSE_POLICY.md` applies | Factual content may have separate copyright limits; preserve provenance. |
| M085 external-bank preparation | Public; readiness infrastructure | Existing repository licensing; no qualifying G4 result materialised merely by the preparation | Independent external-maintainer boundary must remain genuine. |
| M086+ materially new core mechanisms | **Default private before publication review** | Licence / patent / trade-secret disposition not pre-selected | Do not expose enabling implementation through public branches, PRs, CI or logs before review. |
| Product-specific implementation and operations | Prospective | Default private | Candidate commercial asset distinct from the historical research archive. |
| Unpublished know-how, optimisation and deployment methods | Prospective | Confidential where value depends on secrecy | Apply reasonable confidentiality and access controls if treated as trade secrets. |
| `Mira Genesis` name and visual identity | Publicly used; registration not asserted | Controlled by `TRADEMARKS.md`; registration decision pending | Search and, if appropriate, file with BOIP / other relevant offices before claiming registration. |
| Patent candidates | None asserted by this register | Screen before enabling public disclosure | Public prior disclosure can affect novelty; obtain qualified advice before filing decisions. |
| External task banks / maintainer payloads | Third-party / future | Rights and confidentiality defined by their owner / protocol | Never treat external material as project-owned without an explicit basis. |
| Third-party software/tooling | Mixed; mostly external dependencies or experiment infrastructure | Governed by upstream terms/licences | Product distribution boundary determines which notices/source obligations become relevant. |

## Historical public boundary

M085 and all earlier material already published through the repository remain on the historical
public side of the boundary. This register does not attempt to reclassify that history as secret or
to revoke rights already granted under the repository's public licences.

M085 may continue only under its scientific protocol and independent-maintainer rules. New private IP
work must not be smuggled into M085 merely to obtain a public scientific result or to pretend that a
project-authored bank is independent.

The prospective boundary begins with materially new M086+ enabling mechanisms. Publication of a
scientific conclusion need not automatically disclose every proprietary implementation detail, but
scientific claims must remain honest, reproducible to the extent claimed, and clearly separated from
private product/R&D assertions.

## Prospective invention / disclosure ledger

Add one row **before public disclosure** of each materially new core mechanism.

| ID | Mechanism / asset | First creation location | Publicly disclosed? | Human provenance recorded? | Third-party dependencies reviewed? | Disposition | Decision date | Evidence / notes |
|---|---|---|---|---|---|---|---|---|
| P-001 | M086 / evolvable improvement mechanism (prospective) | Private R&D by default | No new enabling disclosure authorised by this policy | Sole-human/AI-assisted provenance framework established; mechanism-specific record still required | Initial repository inventory complete; release-specific scan pending | **REVIEW BEFORE PUBLICATION** | 2026-08-12 | Candidate boundary for meta-plasticity research. |

Allowed dispositions for new entries:

- `PUBLIC_RESEARCH`
- `SOURCE_VISIBLE_RESTRICTED_USE`
- `PATENT_FIRST`
- `TRADE_SECRET_PRIVATE`
- `COMMERCIAL_PRIVATE`
- `ABANDONED`

The disposition must describe the actual decision. Do not retroactively mark a public disclosure as
secret.

## AI-assisted-development diligence

The project records OpenAI Codex and Anthropic Claude as substantial development tools, not as human
contributors. OpenAI ChatGPT is also recorded where historically used. The development record should
preserve human problem formulation, architecture/protocol decisions, selection/rejection/editing and
release decisions for material future assets.

Provider terms are a separate contractual layer. Before a commercial transaction or patent filing,
archive or re-check the exact terms associated with the actual account/product used for material
private R&D. Do not assume that a provider's assignment or output-ownership language clears
third-party code licences, establishes copyrightability, or resolves inventorship.

See [`docs/AI_ASSISTED_DEVELOPMENT_PROVENANCE.md`](docs/AI_ASSISTED_DEVELOPMENT_PROVENANCE.md).

## External contributor chain-of-title rule

Until a qualified contributor agreement is adopted, externally authored copyrightable code,
documentation, tests or other substantive material must not be merged merely under DCO sign-off.

Issues, reproducibility reports, bug reports and non-confidential suggestions may still be useful,
but submitters should not be asked to disclose proprietary or confidential information through a
public channel.

Any future contributor agreement intended to support commercial relicensing or acquisition should be
reviewed by qualified counsel and should clearly address the rights needed for those purposes.

## Third-party and dependency review

The initial repository-level inventory is now recorded in
[`docs/THIRD_PARTY_DEPENDENCIES.md`](docs/THIRD_PARTY_DEPENDENCIES.md). At this snapshot the direct
Python package surface is small (`numpy` runtime, `setuptools` build, `pytest` development), while
Docker images, Playwright/Chromium and the X11 desktop stack are primarily experimental
infrastructure rather than automatically distributed product dependencies.

That distinction is valuable but does not eliminate compliance work. Before a commercial release or
acquisition data-room snapshot, generate a release-specific machine-readable SBOM / licence inventory
covering at least:

- Python packages and build/test tooling actually distributed;
- Node / browser tooling actually bundled;
- exact Docker base-image digests and package notice trees if images are distributed;
- WebAssembly runtime/tooling if bundled rather than treated as an external prerequisite;
- copied or vendored source and fixtures;
- benchmark/task licences;
- model/API terms relevant to runtime product components;
- fonts, images, logos and other non-code assets.

## Acquisition-readiness checklist

Current status at the 12 August 2026 snapshot:

| Item | Status | Note |
|---|---|---|
| Human contributor snapshot | **RECORDED** | Sole-human development declaration + GitHub enumeration recorded |
| AI-assisted development provenance | **RECORDED** | Codex, Claude, historical ChatGPT and automation roles documented |
| Prospective M086+ publication boundary | **ACTIVE** | Private-before-publication review by default |
| Historical public-licence boundary | **RECORDED** | M085 and earlier public history not retroactively restricted |
| Initial third-party dependency inventory | **RECORDED** | Repository-level inventory added; not yet a release SBOM |
| Release-specific SPDX/CycloneDX SBOM | **PENDING** | Generate for the exact artefact before commercial distribution/data room |
| Exact container notice/licence bundles | **PENDING WHEN DISTRIBUTED** | Needed only for images/components actually distributed, but must be resolved before release |
| External contributor agreements | **NOT CURRENTLY NEEDED / POLICY READY** | No second human code contributor observed; agreement required before any future substantive external merge |
| AI-provider account-term archive for private inventions | **PENDING PER MATERIAL ASSET** | Preserve exact terms/product/account context used for M086+ material work |
| Trademark search/filing | **PENDING** | Registration not asserted |
| Patent screening/filing | **PENDING** | Perform before enabling disclosure of a candidate invention |
| Trade-secret access/confidentiality evidence | **PENDING FOR PRIVATE R&D** | Must exist if secrecy is relied upon as an asset |

Before presenting the project for acquisition or exclusive licensing, additionally verify:

- chain of title for every material proprietary component;
- list of historical AGPL / CC public assets that an acquirer cannot make undisclosed retroactively;
- complete release-specific third-party licence / dependency inventory;
- trademark ownership / applications / registrations accurately recorded;
- patent applications or decisions accurately recorded;
- trade secrets demonstrably subject to confidentiality measures;
- private repository access list and access history;
- reproducible public scientific evidence separated from proprietary implementation;
- commercial contracts, licences and encumbrances, if any.

## Non-claims

This register does not claim that:

- historical AGPL rights can be revoked;
- every line in the repository is copyrightable;
- every project concept is protected by copyright;
- sole-human development automatically proves ownership of every generated or third-party-derived
  fragment;
- M086 or any other mechanism is patentable;
- `Mira Genesis` is a registered trademark;
- an AI system is a legal author or inventor;
- provider output-ownership terms automatically clear third-party rights;
- an external maintainer's material belongs to Mira Genesis.
