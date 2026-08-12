# Selective private R&D operating procedure

**Effective from 12 August 2026 for assets explicitly classified as temporarily private.**

Mira Genesis is public-research-first. This procedure applies only when the pre-publication review in
[`IP_PUBLICATION_POLICY.md`](IP_PUBLICATION_POLICY.md) records a concrete private disposition such as
`PATENT_FIRST`, `TRADE_SECRET_PRIVATE`, `CONFIDENTIAL_THIRD_PARTY`, `CONTRACTUAL_EMBARGO`,
`COMMERCIAL_PRIVATE`, or a security-sensitive hold.

It is not the default workflow for M086+ and is not required merely to preserve alternative
commercial licensing.

## 1. Separate repository/workspace when confidentiality is active

Do not develop an asset that is currently classified private on a branch of the public
`mjodheim/mira-genesis` repository. A branch of a public repository is public.

Use a genuinely private repository or non-public local workspace for the duration of the hold. A
practical layout is:

- `mjodheim/mira-genesis` — public scientific/research repository;
- a separately created private workspace — only for assets whose recorded disposition currently
  requires confidentiality.

Do not move ordinary public research into the private workspace just because it may later be
commercially licensed.

## 2. Safe bootstrap from the public baseline

When a private GitHub repository is actually needed, a local bootstrap may start from the current
public baseline while disabling accidental pushes back to the public remote:

```sh
git clone git@github.com:mjodheim/mira-genesis.git mira-genesis-rnd
cd mira-genesis-rnd
git remote rename origin public
git remote set-url --push public DISABLED

git remote add private git@github.com:mjodheim/mira-genesis-rnd.git
git config remote.pushDefault private
git push -u private main
```

Confirm the target repository is private before pushing unpublished material.

## 3. Access control

For selectively private R&D:

- grant access only to the owner and services/tools actually required;
- review GitHub App/OAuth access before exposing the private repository to a coding service;
- do not create public forks, public Actions artifacts, public gists or paste links from private
  source;
- never copy confidential external-maintainer/customer material into the public repository;
- keep credentials out of Git and use appropriate secret stores;
- retain enough access/provenance history to support later diligence.

If trade-secret value is claimed, preserve evidence of actual confidentiality measures rather than
relying only on a `confidential` label.

## 4. AI-provider data controls

Private Git hosting does not by itself control what is sent to an AI service. Before sending
selectively private R&D to Codex, ChatGPT or Claude, check the data controls and contract for the
actual product/account in use.

For material relying on confidentiality, use the strictest available non-training/data-sharing
settings appropriate to the account, avoid feedback workflows that intentionally submit confidential
sessions for provider improvement, and preserve the account/product terms relevant to material R&D.

Provider settings reduce disclosure risk but do not themselves establish trade-secret status, patent
novelty, copyrightability or freedom to operate.

## 5. Private scientific record

Private does not mean scientifically ungoverned. For each private experiment:

- freeze the protocol/thresholds before observing the result where required;
- keep append-only result/failure records;
- preserve Track A / Track B attribution;
- preserve exact source commit, environment/runtime identity and dependency evidence;
- record negative and inconclusive results;
- keep checkpoint/rollback claims non-tautological and independently evaluable;
- do not call project-authored or project-controlled AI material "independent" evidence.

Publication later must not rewrite the chronology.

## 6. Private invention/disclosure ledger

For the duration of a confidentiality hold, record at least:

- asset ID and non-enabling description;
- reason for private classification;
- date/commit of first material conception/implementation;
- human formulation/conception notes;
- AI tools/products/accounts materially involved;
- third-party code/data/model dependencies;
- people/services with access;
- external disclosures and dates;
- intended end state: publish, file patent, retain trade secret, keep product-private, or abandon;
- decision/filing/release evidence.

## 7. Return to the public repository

A selectively private research asset may return to `mjodheim/mira-genesis` when the hold is resolved.
Before a public push/PR:

1. identify exactly what will be disclosed;
2. update the invention/disclosure record;
3. review third-party and AI-assisted provenance;
4. confirm patent/trade-secret/confidential obligations are resolved for the disclosed material;
5. record the public disposition, normally `PUBLIC_AGPL_COMMERCIAL_OPTION` for project-controlled
   software;
6. only then prepare the public branch.

Do not merge a private repository wholesale into the public one.

## 8. Commercial licensing does not require secrecy

Once project-controlled software is intentionally public under AGPL, Anthony Mets may still offer an
alternative commercial licence for rights he controls. Do not keep research private solely because a
future customer may want a proprietary commercial agreement.

See [`DUAL_LICENSING_STRATEGY.md`](DUAL_LICENSING_STRATEGY.md).

## 9. Acquisition/data-room evidence

For any private assets that still exist at the time of a transaction, preserve:

- public/private commit boundaries;
- contributor and AI-assistance provenance;
- private repository access history;
- invention/disclosure ledger;
- release-specific SBOM/licence reports;
- trademark/patent filings or documented decisions;
- commercial licences/contracts and encumbrances;
- reproducible scientific evidence and its relationship to proprietary implementation.
