# Mira Genesis — IP asset register

**Initial audit date: 12 August 2026**

This register supports provenance, licensing, publication decisions and future due diligence. It is
not a legal opinion and does not create ownership where the applicable law or a third-party licence
says otherwise.

## Control and provenance snapshot

- Project: **Mira Genesis**
- Repository: `mjodheim/mira-genesis`
- Project author / director recorded by the repository: **Anthony Mets**
- Copyright notice used by the repository: `Copyright (C) 2026 Anthony Mets.`
- Public repository visibility at this audit: **public**
- Human GitHub contributors observed in the repository contributor history at this audit: the project
  owner's account only; automated GitHub Actions activity is not treated as a human contributor.
- `AUTHORS.md` separates project authorship / direction from AI assistance.
- Existing contribution policy uses the Developer Certificate of Origin and states that contributors
  retain copyright; DCO sign-off is not a copyright assignment.
- No conclusion in this register treats machine-generated material as independently copyrightable or
  assumes a legal answer to unresolved AI-authorship questions. Human design, selection, editing,
  integration, testing and provenance should continue to be recorded.

## Asset classes

| Asset class | Current status | Current / intended treatment | Due-diligence note |
|---|---|---|---|
| Public software through current `main` / M084 | Public | `AGPL-3.0-only` under `LICENSE_POLICY.md` | Existing grants are not withdrawn by the prospective IP policy. |
| Public research prose, protocols and records | Public | `CC-BY-4.0` where `LICENSE_POLICY.md` applies | Factual content may have separate copyright limits; preserve provenance. |
| M085 public preparation | Public branch / PR | Existing repository licensing; scientific result not yet materialised | External-maintainer boundary must remain genuine; not a substitute for private R&D. |
| M086+ materially new core mechanisms | **Default private before publication review** | Licence / patent / trade-secret disposition not pre-selected | Do not expose enabling implementation through public branches, PRs, CI or logs before review. |
| Product-specific implementation and operations | Prospective | Default private | Candidate commercial asset distinct from the historical research archive. |
| Unpublished know-how, optimisation and deployment methods | Prospective | Confidential where value depends on secrecy | Apply reasonable confidentiality and access controls if treated as trade secrets. |
| `Mira Genesis` name and visual identity | Publicly used; registration not asserted | Controlled by `TRADEMARKS.md`; registration decision pending | Search and, if appropriate, file with BOIP / other relevant offices before claiming registration. |
| Patent candidates | None asserted by this register | Screen before enabling public disclosure | Public prior disclosure can affect novelty; obtain qualified advice before filing decisions. |
| External task banks / maintainer payloads | Third-party / future | Rights and confidentiality defined by their owner / protocol | Never treat external material as project-owned without an explicit basis. |

## Historical public boundary

At the time this register was created, M084 had been merged to `main`. That public history is not
reclassified as proprietary by this register.

The M085 preparation is already public. It may continue only under its scientific protocol and
independent-maintainer rules. New private IP work must not be smuggled into M085 merely to obtain a
public scientific result.

## Prospective invention / disclosure ledger

Add one row **before public disclosure** of each materially new core mechanism.

| ID | Mechanism / asset | First creation location | Publicly disclosed? | Human provenance recorded? | Third-party dependencies reviewed? | Disposition | Decision date | Evidence / notes |
|---|---|---|---|---|---|---|---|---|
| P-001 | M086 / evolvable improvement mechanism (prospective) | Private R&D by default | No new enabling disclosure authorised by this policy | Pending | Pending | **REVIEW BEFORE PUBLICATION** | 2026-08-12 | Candidate boundary for meta-plasticity research. |

Allowed dispositions for new entries:

- `PUBLIC_RESEARCH`
- `SOURCE_VISIBLE_RESTRICTED_USE`
- `PATENT_FIRST`
- `TRADE_SECRET_PRIVATE`
- `COMMERCIAL_PRIVATE`
- `ABANDONED`

The disposition should describe the actual decision. Do not retroactively mark a public disclosure as
secret.

## External contributor chain-of-title rule

Until a qualified contributor agreement is adopted, externally authored copyrightable code,
documentation, tests or other substantive material must not be merged merely under DCO sign-off.

Issues, reproducibility reports, bug reports and non-confidential suggestions may still be useful,
but submitters should not be asked to disclose proprietary or confidential information through a
public channel.

Any future contributor agreement intended to support commercial relicensing or acquisition should be
reviewed by qualified counsel and should clearly address the rights needed for those purposes.

## Third-party and dependency review

Before a commercial release or acquisition process, produce a machine-readable software bill of
materials / licence inventory covering at least:

- Python packages and tools;
- Node / browser tooling;
- Docker base images;
- WebAssembly tooling;
- copied or vendored source and fixtures;
- benchmark/task licences;
- model/API terms relevant to distributed product components;
- fonts, images, logos and other non-code assets.

Absence of a package manifest is not evidence that there are no third-party obligations. Runtime and
container dependencies must also be reviewed.

## Acquisition-readiness checklist

Before presenting the project for acquisition or exclusive licensing, verify:

- chain of title for every material proprietary component;
- list of historical AGPL / CC public assets that an acquirer cannot make undisclosed retroactively;
- contributor agreements for every external copyright holder, if any;
- complete third-party licence / dependency inventory;
- trademark ownership / applications / registrations accurately recorded;
- patent applications or decisions accurately recorded;
- trade secrets demonstrably subject to confidentiality measures;
- private repository access list and access history;
- reproducible public scientific evidence separated from proprietary implementation;
- commercial contracts, licences and encumbrances, if any;
- substantial AI assistance and human provenance documented sufficiently for diligence.

## Non-claims

This register does not claim that:

- historical AGPL rights can be revoked;
- every line in the repository is copyrightable;
- every project concept is protected by copyright;
- M086 or any other mechanism is patentable;
- `Mira Genesis` is a registered trademark;
- an AI system is a legal author;
- an external maintainer's material belongs to Mira Genesis.
