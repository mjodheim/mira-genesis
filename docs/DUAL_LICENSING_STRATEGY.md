# Mira Genesis — public AGPL and alternative commercial licensing strategy

**Effective strategy date: 12 August 2026.**

This document records the project's intended licensing model. It is an operational policy and
commercial-positioning statement, not a substitute for a signed commercial licence or legal advice.

## 1. Public research remains the default

Mira Genesis is intended to remain a public, auditable research project. Software deliberately
published in `mjodheim/mira-genesis` remains available to the public under `AGPL-3.0-only` as defined
by `LICENSE_POLICY.md`. Public non-software research material remains under the documentation licence
stated there.

Starting with M086, a milestone is **not private merely because it is new or commercially valuable**.
The normal path is:

1. perform the short pre-publication IP/provenance review in `docs/IP_PUBLICATION_POLICY.md`;
2. if no temporary confidentiality reason applies, publish the software under `AGPL-3.0-only` and
   preserve the public scientific record;
3. retain the option for the project owner to grant a separate alternative commercial licence to a
   customer under a written agreement.

## 2. What the public AGPL grant means

The public AGPL licence already permits commercial activity subject to its terms. A person or company
that is willing to comply with the AGPL does not need to purchase a separate licence merely because
its activity is commercial.

Nothing in this strategy attempts to forbid rights already granted by the AGPL or to relabel AGPL use
as infringement.

## 3. What the alternative commercial licence sells

For software for which Anthony Mets controls the rights necessary to do so, the project owner may
separately grant a customer additional permissions under a written commercial agreement.

Typical reasons a customer may want such an agreement include permission, subject to the signed
terms, to:

- integrate covered Mira Genesis software into proprietary products or services without relying on
  the AGPL grant for that covered copy;
- keep the customer's proprietary source or covered modifications confidential where the agreement
  permits it;
- redistribute covered software under negotiated proprietary terms;
- obtain OEM/embedded rights, support, warranties, indemnity allocations, service levels or other
  commercial terms not supplied by the public AGPL release;
- receive commercially supported releases or separately controlled product components.

The exact rights, field of use, territory, term, fees, warranties, liability, support and termination
rules belong in the signed customer agreement. They are **not** granted by this document.

This is best understood as a public copyleft release plus separately sold commercial permissions. It
must not be described as if every public user automatically receives the commercial terms.

## 4. Rights-control requirement

Alternative commercial licensing is only offered for material for which the project controls the
rights necessary to grant the requested permissions.

Therefore:

- third-party components remain governed by their own licences;
- externally authored copyrightable contributions are not accepted without a contributor-rights
  arrangement that preserves the permissions needed for public AGPL licensing, alternative
  commercial licensing and a future assignment/acquisition;
- AI-assisted output is reviewed for provenance and possible third-party obligations rather than
  presumed unencumbered;
- release-specific dependency and licence inventories remain required for commercial distribution.

## 5. Selective temporary confidentiality

A public repository and commercial licensing are compatible. Private R&D is therefore an exception,
not the default.

A materially new mechanism should be held temporarily outside the public repository only when a
specific reason has been recorded, such as:

- patent-first review because public disclosure could affect novelty;
- intentional trade-secret treatment;
- confidential third-party or independent-maintainer material;
- contractual embargo;
- security-sensitive information or credentials;
- product-specific proprietary implementation that is deliberately not part of the public research
  release.

Once a mechanism has been intentionally published, do not later describe the same disclosed
information as secret.

## 6. Acquisition optionality

The public research history does not prevent acquisition of the project or of rights controlled by
the project owner. A transaction can still include, subject to due diligence and contract:

- the owner's copyright and alternative-relicensing rights in controlled material;
- the right to continue offering commercial exceptions/licences;
- trademark rights;
- private product components and unpublished R&D, if any;
- confidential know-how;
- commercial contracts and customer relationships;
- patent applications or patents, if any;
- scientific provenance and reproducibility infrastructure.

An acquirer must be told which historical/public copies remain available under AGPL/CC terms after
any transaction. Public copies are not made private retroactively by an acquisition.

## 7. Commercial-positioning language

The project may accurately state:

> Mira Genesis software is available publicly under AGPL-3.0-only. Alternative commercial licensing
> for proprietary use may be available from the project owner under a separate written agreement.

Do not state:

- that commercial activity is prohibited by the AGPL;
- that every commercial user must pay;
- that a commercial licence automatically covers third-party components;
- that the commercial licence is already granted merely because this repository mentions it;
- that public release preserves patent novelty or trade-secret status.

## 8. Formal customer agreement

Before the first paid commercial licence is signed, have the actual customer agreement reviewed by a
qualified Belgian/European IP lawyer. The public repository should record only the licensing model
and contact route unless the project owner deliberately chooses to publish a standard commercial
contract.
