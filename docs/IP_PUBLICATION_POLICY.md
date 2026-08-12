# Mira Genesis — prospective IP publication policy

**Effective for prospective work from 12 August 2026.**

This document is an operational publication policy. It is not a retroactive licence change and it
does not withdraw, narrow or replace permissions already granted for material already published.

## 1. Public research is the normal path

Mira Genesis is intended to remain a public and auditable research project.

Starting with M086, a materially new core mechanism is **not private by default** merely because it
is new or may have commercial value. The normal path is:

1. perform the pre-publication review below before enabling disclosure;
2. if no specific temporary confidentiality reason applies, publish the software in the public
   repository under `AGPL-3.0-only` and the research material under the documentation licence stated
   in `LICENSE_POLICY.md`;
3. preserve the project owner's ability to offer separate commercial permissions for controlled
   software under a written agreement.

Public AGPL release and separate commercial licensing are compatible. See
[`docs/DUAL_LICENSING_STRATEGY.md`](DUAL_LICENSING_STRATEGY.md).

## 2. Short pre-publication review

Before the first enabling public disclosure of a materially new core mechanism, record at minimum:

- what mechanism or asset is being disclosed;
- human authorship/contribution provenance and substantial AI assistance;
- third-party code, data, models, benchmarks and licences involved;
- whether the same material has already been disclosed elsewhere;
- the intended public licence;
- whether the project controls the rights needed for alternative commercial licensing;
- whether a patent-first review is warranted before disclosure;
- whether intentional trade-secret treatment is actually desired;
- whether confidential third-party material, contractual embargo or security-sensitive information
  is involved;
- whether publication changes a frozen scientific boundary;
- the project owner's publication decision and date.

The decision should be entered in `IP_ASSET_REGISTER.md` or, if the review itself contains genuinely
confidential enabling material, in a private successor record.

## 3. Default disposition after review

If the review finds no concrete reason for temporary confidentiality, use:

**`PUBLIC_AGPL_COMMERCIAL_OPTION`**

This means:

- publish project-controlled software under `AGPL-3.0-only`;
- publish research prose/results under the documentation licence defined by `LICENSE_POLICY.md`;
- keep scientific evidence public and auditable;
- preserve the owner's right, where legally available, to grant a separate commercial licence to a
  customer that wants rights beyond the AGPL grant.

The commercial agreement is not automatically granted to public users and does not override
third-party licences.

## 4. When temporary private treatment is justified

Use a genuinely private workspace only when a specific reason has been recorded, such as:

- **PATENT_FIRST** — qualified patent review/filing decision must occur before enabling public
  disclosure;
- **TRADE_SECRET_PRIVATE** — the project deliberately chooses secrecy as part of the asset's value;
- **CONFIDENTIAL_THIRD_PARTY** — external-maintainer, customer or other third-party material cannot be
  disclosed;
- **CONTRACTUAL_EMBARGO** — a valid agreement temporarily restricts disclosure;
- **SECURITY_SENSITIVE** — credentials, exploitable secrets or other sensitive material must remain
  non-public;
- **COMMERCIAL_PRIVATE** — a product-specific implementation is intentionally kept outside the public
  research release.

Private R&D is an exception to the public research workflow, not a prerequisite for commercial
licensing.

If an invention may be patent-sensitive, decide that **before** public disclosure: public internet
publication can become prior art. Do not assume that publishing first and filing later preserves
European novelty.

## 5. No accidental disclosure of selectively private material

When a specific private disposition is active, do not place enabling details in:

- public commit messages or branch names;
- public GitHub Actions logs or artifacts;
- public issues, discussions or pull requests;
- public benchmark payloads;
- externally accessible prompts/telemetry whose confidentiality has not been reviewed.

Secrets, credentials and confidential third-party payloads must never be committed to the public
repository.

The operating procedure for these exceptional cases is
[`docs/PRIVATE_RND_OPERATIONS.md`](PRIVATE_RND_OPERATIONS.md).

## 6. Scientific integrity is independent of IP strategy

Licensing or confidentiality must never be used to:

- turn project-authored evidence into "independent" evidence;
- conceal a negative result after a frozen experiment has materialised;
- alter a frozen threshold after observation;
- attribute an external model's competence to the endogenous lineage;
- weaken the Track A / Track B boundary;
- claim a gate is closed without the evidence required by the frozen criteria.

M085's independent-maintainer boundary remains genuine regardless of commercial strategy.

## 7. Commercial and acquisition objective

The public-first strategy preserves optionality for:

- alternative commercial licences on software for which the project controls the necessary rights;
- commercial services and product implementations;
- assignment or acquisition of controlled IP/relicensing rights;
- trademark licensing;
- selective patent or trade-secret protection where appropriate.

It does **not** state or imply that every commercial user must purchase a licence. An AGPL-compliant
commercial user may rely on the public AGPL grant.

## 8. Legal review

This operational policy does not substitute for advice from a qualified Belgian/European IP
professional. A binding commercial licence, contributor-rights agreement, patent filing, trademark
filing or material transaction should be reviewed before execution.
