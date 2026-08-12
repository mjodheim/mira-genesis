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
- AI development assistance is recorded in
  [`docs/AI_ASSISTED_DEVELOPMENT_PROVENANCE.md`](docs/AI_ASSISTED_DEVELOPMENT_PROVENANCE.md): OpenAI
  Codex, Anthropic Claude, OpenAI ChatGPT where historically used, and repository automation.
- Externally authored copyrightable material is not currently accepted for merge unless an
  appropriate contributor-rights arrangement has first been approved. DCO sign-off is provenance,
  not copyright assignment.
- The initial third-party/tooling inventory is recorded in
  [`docs/THIRD_PARTY_DEPENDENCIES.md`](docs/THIRD_PARTY_DEPENDENCIES.md).

The sole-human declaration and current Git history materially simplify diligence relative to a
repository with multiple uncontracted human copyright holders. They remain evidence, not a substitute
for claim-specific legal analysis of authorship, inventorship, copyrightability, third-party
provenance or contractual encumbrances.

## Licensing model

The project's intended operating model is now:

**public `AGPL-3.0-only` software + separately negotiated alternative commercial licensing for rights
controlled by the project owner.**

The public AGPL grant permits commercial use subject to its terms. It is not a non-commercial
licence. The commercial offering exists for customers that need negotiated rights beyond the public
AGPL grant, for example proprietary/closed-source integration or redistribution where the signed
agreement permits it.

See:

- [`LICENSE_POLICY.md`](LICENSE_POLICY.md);
- [`COMMERCIAL_LICENSING.md`](COMMERCIAL_LICENSING.md);
- [`docs/DUAL_LICENSING_STRATEGY.md`](docs/DUAL_LICENSING_STRATEGY.md).

## Asset classes

| Asset class | Current status | Current / intended treatment | Due-diligence note |
|---|---|---|---|
| Public project-controlled software | Public | `AGPL-3.0-only`; alternative commercial permissions may be sold separately where rights permit | Public AGPL rights remain available after any commercial deal or acquisition. |
| Public research prose, protocols and records | Public | `CC-BY-4.0` where `LICENSE_POLICY.md` applies | Preserve attribution/provenance. |
| M085 external-bank preparation | Public; readiness infrastructure | Existing repository licensing; no qualifying G4 result merely from preparation | Independent external-maintainer boundary remains genuine. |
| M086+ research mechanisms | **Public after pre-publication review by default** | Expected disposition: `PUBLIC_AGPL_COMMERCIAL_OPTION` unless a specific confidentiality reason is recorded | New/commercially valuable does not itself imply private. |
| Patent-sensitive candidate | Prospective | `PATENT_FIRST` temporarily before disclosure | Public disclosure can affect novelty; obtain qualified advice before filing decision. |
| Intentional trade secret | Prospective | `TRADE_SECRET_PRIVATE` | Requires actual confidentiality/access controls; cannot be reconstructed as secret after disclosure. |
| Product-specific implementation and operations | Prospective | Public or `COMMERCIAL_PRIVATE` by explicit decision | Product layer can remain proprietary even while research core stays public. |
| `Mira Genesis` name and visual identity | Publicly used; registration not asserted | Controlled by `TRADEMARKS.md`; registration decision pending | Search/file before claiming registration. |
| External task banks / maintainer payloads | Third-party / future | Rights/confidentiality defined by owner/protocol | Never treat external material as project-owned without basis. |
| Third-party software/tooling | Mixed | Governed by upstream terms/licences | Commercial licence cannot grant rights the project does not control. |

## Publication/disclosure ledger

Add or update one row **before the first enabling public disclosure** of each materially new core
mechanism.

| ID | Mechanism / asset | Publication posture | Human provenance | Third-party review | Disposition | Decision date | Evidence / notes |
|---|---|---|---|---|---|---|---|
| P-001 | M086 / evolvable improvement mechanism | **Protocol publicly disclosed on `research/m086-evolvable-improvement-mechanism`**; implementation not yet recorded as publicly disclosed at this snapshot | Sole-human/AI-assisted framework established; mechanism-specific provenance remains required as implementation lands | Initial repository inventory complete; milestone-specific scan pending | **`PUBLIC_AGPL_COMMERCIAL_OPTION` for the disclosed protocol/research design** | 2026-08-12 | `experiments/M086/PROTOCOL.md`, `PROTOCOL.json` and `docs/HYPERAGENTS_COMPARISON.md` were pushed publicly before this ledger update. Do not claim those disclosed design details remain secret. Any materially new implementation-specific invention not already disclosed may receive a separate pre-disclosure review before first public push. |

| P-002 | `mira-blind-bank-v1` / blind externally materialized sealed task-bank contract (M075-B) | **Publicly disclosed on `research/m075b-blind-bank-generation`**: contract, schemas, isolation boundary, sealing chain, reveal gate, checkers and tests | Sole-human/AI-assisted framework established; see `docs/AI_ASSISTED_DEVELOPMENT_PROVENANCE.md` | Initial repository inventory complete | **`PUBLIC_AGPL_COMMERCIAL_OPTION`** | 2026-08-12 | Method and instrument only. It holds **no** task content: no bank exists, no generator is chosen and no reveal is authorized. Any future sealed payload is confidential by construction and may never enter this repository, a pull request or a public workflow artifact — `scripts/check_blind_bank_leakage.py` enforces that as a decisive CI step. Publishing the contract does not disclose any bank materialized under it later. |
| P-003 | M087 / evolvable evidence-acquisition and candidate-selection mechanism | **Publicly disclosed on `research/m087-evolvable-evidence-acquisition`**: protocol, selection-policy DSL and interpreter, meta-primitive language, evidence boundary, three problem families, checker, tests and preserved result | Sole-human/AI-assisted framework established; see `docs/AI_ASSISTED_DEVELOPMENT_PROVENANCE.md`. Track A: no external model participates in the scientific run, and the result records 0 model calls | Initial repository inventory complete; milestone-specific scan complete for this mechanism | **`PUBLIC_AGPL_COMMERCIAL_OPTION`** | 2026-08-13 | Successor to M086 under the same public research disposition recorded for P-001. The mechanism is a bounded meta-transformation language over a serialized selection policy; the meta-primitives, instruction set, experiment space and problem families are authored and disclosed. No confidential third-party material, no security-sensitive material, and no sealed task-bank content is involved. |

Allowed dispositions:

- `PUBLIC_AGPL_COMMERCIAL_OPTION`
- `PUBLIC_RESEARCH`
- `PATENT_FIRST`
- `TRADE_SECRET_PRIVATE`
- `CONFIDENTIAL_THIRD_PARTY`
- `CONTRACTUAL_EMBARGO`
- `COMMERCIAL_PRIVATE`
- `ABANDONED`

The disposition must describe reality. Do not retroactively mark already public information as
secret.

## Alternative commercial licensing chain-of-title rule

Alternative commercial licensing is only possible to the extent the project controls the rights
needed for the requested permissions.

Until a qualified contributor agreement is adopted, externally authored copyrightable code,
documentation, tests or other substantive material must not be merged merely under DCO sign-off.

Any future contributor agreement intended to preserve commercial relicensing or acquisition
optionality should explicitly address the rights needed for:

- public AGPL licensing;
- alternative proprietary/commercial licensing;
- modification and distribution;
- assignment/acquisition of the project owner's controlled rights.

## AI-assisted-development diligence

OpenAI Codex and Anthropic Claude are recorded as substantial development tools, not human
contributors. OpenAI ChatGPT is also recorded where historically used. Preserve human problem
formulation, architecture/protocol decisions, selection/rejection/editing and release decisions for
material future assets.

Provider terms are a separate contractual layer. Do not assume provider output-ownership language
clears third-party code licences, establishes copyrightability, or resolves inventorship.

See [`docs/AI_ASSISTED_DEVELOPMENT_PROVENANCE.md`](docs/AI_ASSISTED_DEVELOPMENT_PROVENANCE.md).

## Third-party and dependency review

The initial repository-level inventory is in
[`docs/THIRD_PARTY_DEPENDENCIES.md`](docs/THIRD_PARTY_DEPENDENCIES.md). Before a commercial release
or acquisition data-room snapshot, generate a release-specific SBOM/licence inventory covering all
components actually distributed.

The alternative commercial licence must exclude or separately account for third-party material that
cannot be relicensed under the negotiated terms.

## Acquisition-readiness checklist

| Item | Status | Note |
|---|---|---|
| Human contributor snapshot | **RECORDED** | Sole-human development declaration + GitHub enumeration recorded |
| AI-assisted development provenance | **RECORDED** | Codex, Claude, historical ChatGPT and automation roles documented |
| Public AGPL + commercial-option strategy | **ACTIVE** | Public research is default after review; commercial rights sold separately where controlled |
| Historical public-licence boundary | **RECORDED** | Public history is not retroactively restricted |
| Initial third-party dependency inventory | **RECORDED** | Repository-level inventory exists; release SBOM still needed |
| Release-specific SPDX/CycloneDX SBOM | **PENDING** | Generate for exact commercial artefact/data room |
| External contributor agreements | **NOT CURRENTLY NEEDED / POLICY READY** | Required before future substantive external merge |
| Trademark search/filing | **PENDING** | Registration not asserted |
| Patent screening/filing | **PENDING PER CANDIDATE** | Must precede enabling disclosure when patent-first is considered |
| Standard commercial customer agreement | **PENDING** | Have first binding agreement reviewed by qualified counsel |
| Commercial licence/customer register | **PENDING UNTIL FIRST DEAL** | Preserve signed grants, versions, scope, fees and encumbrances |

Before presenting the project for acquisition or exclusive licensing, additionally verify:

- chain of title for every material right proposed for transfer;
- list of public AGPL/CC assets that remain public after the transaction;
- complete release-specific third-party licence/dependency inventory;
- every alternative commercial licence already granted and any surviving obligations;
- trademark/patent status accurately recorded;
- private trade-secret assets, if any, backed by real confidentiality measures;
- reproducible scientific evidence separated from proprietary product assets where relevant.

## Non-claims

This register does not claim that:

- public AGPL rights can be revoked;
- AGPL prohibits commercial activity;
- every commercial user must buy a licence;
- every line in the repository is copyrightable or exclusively controlled;
- sole-human development automatically proves ownership of every AI-generated or third-party-derived
  fragment;
- a commercial agreement can relicense third-party material beyond upstream rights;
- M086 or any other mechanism is patentable;
- `Mira Genesis` is a registered trademark;
- an AI system is a legal author or inventor;
- an external maintainer's material belongs to Mira Genesis.
