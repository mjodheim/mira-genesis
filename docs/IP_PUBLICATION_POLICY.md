# Mira Genesis — prospective IP publication policy

**Effective for prospective work from 12 August 2026.**

This document is an operational publication policy. It is not a retroactive licence change and it
does not withdraw, narrow or replace permissions already granted for material that has already been
published.

## 1. Historical public research remains public under its existing terms

Material already present in the public Mira Genesis repository remains governed by the licences that
applied when it was published. In particular, the current public software is distributed under
`AGPL-3.0-only` and the public non-software research material described by `LICENSE_POLICY.md` is
distributed under `CC-BY-4.0`.

Nothing in this policy attempts to revoke those grants.

M084 and the earlier published construction and adaptive-embodiment record remain part of the public
scientific history. The already-public M085 preparation may also complete according to its frozen
scientific and independent-maintainer boundaries; this policy must not be used to weaken, replace or
simulate that external evidence requirement.

## 2. Default boundary for new core R&D

Starting with M086 and any other materially new core mechanism first created after this policy takes
effect, **private before publication** is the default.

A materially new core mechanism includes, for example, a new executable mechanism for meta-plasticity,
self-improvement, transformation generation, lineage transport, persistent adaptation, substrate
migration or another mechanism whose publication could materially transfer the project's technical
advantage.

Such work should not be pushed to a public branch, public issue, public pull request, public CI log or
other public channel until it has passed the publication review below.

This is a confidentiality boundary, not a scientific permission to hide or rewrite an already
materialised result. Where a scientific protocol requires a public commitment, the IP disposition
must be decided **before** that commitment is made.

## 3. Pre-publication classification

Before a new core mechanism is disclosed publicly, the project owner must classify it into one of
these dispositions:

1. **public research** — intentionally publish under an explicitly recorded licence;
2. **source-visible / restricted-use candidate** — publish only after a reviewed licence has been
   selected that expresses the intended restrictions;
3. **patent-first candidate** — obtain qualified patent advice and make any required filing decision
   before public disclosure;
4. **trade-secret / private R&D** — keep the enabling implementation and confidential know-how
   non-public and protect access accordingly;
5. **commercial product implementation** — keep product-specific implementation private unless a
   deliberate release decision says otherwise.

No custom legal licence should be improvised inside a research milestone to rescue a publication
schedule.

## 4. Publication review checklist

Before public disclosure of a new core mechanism, record at minimum:

- the asset or mechanism being disclosed;
- its human authorship and contribution provenance;
- substantial generative-AI assistance where relevant to provenance;
- third-party code, data, models, benchmarks and licences involved;
- whether the same material has already been disclosed elsewhere;
- the intended copyright licence, if any;
- whether commercial use is intended to be permitted;
- whether trademark rights are implicated;
- whether patent screening is warranted before disclosure;
- whether confidentiality / trade-secret treatment is intended;
- whether the disclosure changes an existing frozen scientific boundary;
- the project owner's explicit publication decision and date.

The decision should be entered in `IP_ASSET_REGISTER.md` or an equivalent private register before
publication.

## 5. No accidental public disclosure

For private R&D, do not place enabling details in:

- public commit messages;
- public branch names when the name itself reveals the mechanism;
- GitHub Actions logs or artifacts from a public repository;
- public issues, discussions or pull requests;
- public benchmark payloads;
- externally accessible model prompts or telemetry unless their terms and confidentiality are known.

Secrets, credentials and private research payloads must never be committed to the public repository.

## 6. Scientific integrity remains separate from IP strategy

IP protection must not be used to:

- turn project-authored evidence into "independent" evidence;
- conceal a negative result after a public/frozen experiment has materialised;
- alter a frozen threshold after observation;
- attribute an external model's competence to the endogenous lineage;
- weaken the Track A / Track B boundary;
- claim a gate is closed without the evidence required by the relevant frozen criteria.

A private experiment may later be published as a complete append-only record. Until publication, its
confidentiality status must be explicit.

## 7. Commercial and acquisition objective

The prospective policy is intended to preserve optionality for:

- separate commercial licences on material for which the project controls the necessary rights;
- commercial services and product implementations;
- assignment or acquisition of controlled IP assets;
- trademark licensing;
- patent or trade-secret protection where appropriate.

It does **not** state or imply that commercial use of historical AGPL-licensed copies requires a
separate commercial licence. Those copies remain governed by their existing licence.

## 8. Legal review

This operational policy is deliberately conservative and does not substitute for advice from a
qualified Belgian / European IP professional. A formal relicensing, contributor-rights agreement,
patent filing, trademark filing or commercial licence should be reviewed before execution.
