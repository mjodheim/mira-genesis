# M123 pre-publication review

**Prepared:** 4 September 2026
**Decision date:** *not yet recorded*
**Proposed disposition:** `PUBLIC_AGPL_COMMERCIAL_OPTION`
**Status:** **PENDING — this review is prepared for the owner and records no decision.**

Anthony Mets is the sole human research director and the sole acceptance and release
decision-maker. No `IP_ASSET_REGISTER.md` row has been written for M123, and the row proposed at
the end of this file is a draft to accept, amend or refuse.

## First, a disclosure about this line as a whole

This review should not be read on its own, because the backlog behind it is the more important
fact:

| milestone | review drafted | register row recorded |
|---|---|---|
| M120 | yes, P-024 | **no** |
| M121 | yes, P-025 | **no** |
| M122 | **no** | **no** |
| M123 | this file, P-026 | **no** |

Four milestones of this line have been implemented, tested, merged and published against **zero**
recorded dispositions, and one of them was published without even a draft. That is stated here
rather than quietly corrected, because drafts are not decisions and accumulating them does not
become one.

The mitigating facts, for what they are worth: every milestone in this line inherits M119's
already-public mechanism family rather than introducing a new one, M119 does carry an
owner-authorised public disposition (P-023, `PUBLIC_AGPL_COMMERCIAL_OPTION`, 2026-09-02), and
nothing in M120–M123 withholds material or claims a scientific result. The unmitigated fact is that
the *scope* of P-023 was never extended by anyone with the authority to extend it.

**This is an owner gate, and it is the fourth open one on this line.** It is not something a
successor milestone can close for itself.

## Asset

M123/H68 is the fourth attempt to obtain an interpretable verdict on a proposition that has never
been tested. H64's proposition is carried forward unchanged, for the reason that it has never been
measured: nothing about the target has been revised because there is nothing to revise it against.

Its predecessors closed, in order, on the instrument and never on the science:

- **M119** — `instrument_aborted`; H64 untested.
- **M120** — the carrier contract needed eight array-of-object levels and the route enforces five.
- **M122** — the contract was validated, nine of nine capability classes enforced, and the stress
  fell 3.3% short of an inherited threshold because its size had been extrapolated from a single
  observation.

M123 introduces no new mechanism. It **inherits M122's carrier contract by import** — the first
milestone in this line not to redesign it — and changes exactly three things, each a correction to
a disclosed defect rather than a new capability:

1. the stress size, fit from two observations at different scales instead of extrapolated from one;
2. the distinction between a probe that was answered and refused and a probe that never answered,
   which both M120 and M122 recorded identically as an unenforced capability;
3. the delivery ceiling's scan, which claimed to count across every instrument and in fact globbed
   only the milestone's own directory, so that opening a successor reset the bound that exists to
   survive apparatus revisions.

None of the three is novel machinery. All three are the milestone paying for errors its own records
disclose.

## Prior disclosure

The entire predecessor line is public: M115–M119 protocols, outcomes and negative or aborted
records; M120's closure and route-depth finding; M122's readiness result, its five archived
attempts and its `not_ready_stress` outcome. M123 depends on no withheld material, and its two
sizing observations are read directly from M122's published attempt archive.

Nothing in M123 has been disclosed outside the repository at the time of writing.

## Provenance and dependencies

Anthony Mets remains the sole human research director and the sole acceptance and release
decision-maker for this milestone.

Anthropic Claude provided the work recorded here: the two-point fit and its margin analysis, the
three corrections above, the preregistration, the readiness gate, the tests and this review. That
work is proposed for the owner's review; it was not accepted into the scientific record by the
assisting system. OpenAI Codex, OpenAI ChatGPT or comparable tooling may additionally be used for
independent review or execution assistance.

All are recorded as AI tooling and AI development assistance. None is recorded as human authorship
and none holds acceptance authority. This production-provenance record does not mean provider terms
clear third-party rights or settle legal authorship or inventorship.

**Track B.** M123 sends requests to an external model over the network under a credential the owner
supplied. The credential is read from the environment and is never written, printed or committed.
The DEVELOPMENT readiness gate is repeatable and consumes no single-use scientific budget; the
qualifying generation, if the milestone ever reaches one, is single-use and gated separately.

## Rights and publication decision

Project-controlled public research under the repository's AGPL and documentation licence boundary.
No patent-first, intentional trade-secret, contractual-embargo, confidential-third-party or
security-sensitive reason for temporary private treatment is identified.

Nothing here is asserted to be patentable. The three corrections are ordinary measurement hygiene —
fitting a line through two points rather than one, distinguishing a null observation from a
negative one, and making a guard's scan match the sentence describing it. Withholding them would
preserve no novelty and would suppress exactly the kind of disclosure this project's records exist
to make.

## Scientific boundary

- M115 through M122 remain closed and immutable. M122's two disclosed defects are read as
  requirements for this milestone and its record is not edited.
- The **32,000-token threshold is inherited from M118 and is not touched**. A threshold rewritten to
  fit a stress is a gate tuned to pass itself, and the temptation to do it was live: M122 missed by
  3.3%. The stress moves; the bar does not.
- The sizing model is fit from two points and is stated as such in the preregistration's
  limitations. Two parameters through two points reproduce both exactly, which is arithmetic and
  not evidence of extrapolation. The margin exists for that reason.
- The readiness gate runs **before** the rest of the apparatus is written, as in M122. If it fails,
  almost nothing is wasted — which is the whole reason that ordering was introduced.
- H59, H60, H62, H63, H64, H65 and H67 are all recorded untested. **H68 would be the first test on
  this chain**, and a first test is not a multiple comparison.
- **A positive result would not be AGI evidence**, would not close any generality gate, and would
  not approach any of the three external blockers — human-maintained sealed bank, independent
  reproduction, external adversarial audit — each of which requires a person outside this project.

## Owner gates that remain open

1. **This disposition**, and the three behind it: P-024 (M120), P-025 (M121), and a review for M122
   that was never drafted.
2. **Authorisation of the frozen protocol**, if M123 reaches a freeze.
3. **The reveal authorisation**, if it reaches a seal.
4. **Acceptance of the result**, whichever way it comes out.

No agent may cross any of these.

## Proposed register row

For the owner to accept, amend or refuse. Not written to `IP_ASSET_REGISTER.md` by this review.

> | P-026 | M123 / H68 two-point-sized readiness successor to M122 | **Proposed for public
> disclosure of the corrected instrument**: M122's route-validated carrier contract inherited by
> import, a stress schema sized from two observations at different scales rather than extrapolated
> from one, a readiness gate that distinguishes an unanswered probe from a refused one, and a
> delivery ceiling whose scan crosses milestones as its own description always claimed. H68 remains
> UNTESTED; no carrier bank exists and no qualifying invocation has been spent | Sole-human/
> AI-assisted framework established; Anthony Mets remains the sole human research director and the
> sole acceptance/release decision-maker. Anthropic Claude provided the fit, the corrections, the
> preregistration, the gate, the tests and this review; OpenAI Codex or comparable tooling may
> provide independent review or execution assistance. All are recorded as AI tooling, none as human
> authorship, and none holds acceptance authority | Track B: external model over the network under
> an owner-supplied credential, read from the environment and never written, printed or committed.
> The DEVELOPMENT readiness gate is repeatable and consumes no single-use budget. No sealed bank, no
> third-party attestation, no new system authority | **`PUBLIC_AGPL_COMMERCIAL_OPTION`** | *pending*
> | Fourth attempt at a proposition never yet measured; the three predecessors closed on the
> instrument and never on the science. M123 introduces no new mechanism and its three changes are
> each payment for a defect its own predecessors disclosed. The M118 threshold is inherited
> unchanged, and the readiness gate runs before the rest of the apparatus is built. **This line has
> been developed and published against no recorded disposition at all**: P-024 and P-025 are drafts,
> M122 has no draft, and the scope of M119's P-023 was never extended by anyone with authority to
> extend it. See `docs/IP_REVIEWS/M123_PUBLICATION_REVIEW.md`. |
