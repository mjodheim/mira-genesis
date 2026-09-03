# M121 pre-publication review

**Prepared:** 3 September 2026
**Decision date:** *not yet recorded*
**Proposed disposition:** `PUBLIC_AGPL_COMMERCIAL_OPTION`
**Status:** **PENDING — this review is prepared for the owner and records no decision.**

Anthony Mets is the sole human research director and the sole acceptance and release
decision-maker. No `IP_ASSET_REGISTER.md` row has been written for M121, and the row proposed at the
end of this file is a draft to accept, amend or refuse.

**Enabling implementation has not begun and will not begin before this decision exists.** M121 is a
materially new core mechanism with no predecessor disposition covering it, so `AGENTS.md` §2 applies
directly. What exists today is a frozen preregistration, a machine-readable protocol commitment and
a schedule salt — the design, and nothing that implements it.

## Asset

M121/H66 targets **G7 — long-horizon autonomy**, the only one of the ten generality gates recorded
`open` in `MIRA_GENERALITY_CRITERIA.md`.

Its predecessor M077 is closed as a valid negative under D043. D043 did more than record the
failure: it wrote the successor's constraint — a successor *"must introduce corruption that can stay
quiescent indefinitely, or a body whose operations do not guard the corrupted state"* — and M077's
result adds that a successor may not reuse its schedule or body. Both bind M121, and neither is
relaxed.

The mechanism to be disclosed is a shift harness over an in-memory typed pool carrying two classes
of injected fault: **operational** corruption that eventually makes a guarded operation impossible,
and **quiescent** corruption that no guarded operation reads during the shift and that, when finally
read, makes an operation *succeed with a wrong result*. The scientific question is whether a periodic
boundary monitor purchases coverage rather than merely detection latency in the second regime, and
whether the coverage it purchases grows with the horizon.

The primary endpoint is the count of work items whose recorded outcome diverges from ground truth
the lineage cannot read — measured from environment state, never from the agent's self-report.

## Prior disclosure

The predecessor line is public. M077's protocol, result, schedule commitment and negative are
published, as is D043 and the generality register that records G7 as open. Nothing in M121's design
depends on material that has been withheld.

No part of M121 has been disclosed outside the repository at the time of writing.

## Provenance and dependencies

Anthony Mets remains the sole human research director and the sole acceptance and release
decision-maker for this milestone.

Anthropic Claude provided the design assistance recorded here: the reading of D043's successor
constraint, the operational/quiescent fault taxonomy, the internal positive control that keeps the
claim falsifiable rather than built into the body, the divergence endpoint, and the drafting of the
preregistration and this review. That work is proposed for the owner's review; it was not accepted
into the scientific record by the assisting system.

OpenAI Codex, OpenAI ChatGPT or comparable tooling may additionally be used for independent review,
local test or execution assistance.

All of the above are recorded as AI tooling and AI development assistance. None is recorded as human
authorship, and none holds acceptance authority. This production-provenance record does not mean
provider terms clear third-party rights or settle legal authorship or inventorship.

The planned implementation uses Python standard-library facilities and the repository's existing
development tooling only. **Track A: no external model, no network, no external task, no credential,
no third-party attestation, no new system authority.** Faults are mutations of an in-memory pool,
never of a real filesystem, process or device.

## Rights and publication decision

The work is project-controlled public research under the repository's AGPL and documentation licence
boundary. No patent-first, intentional trade-secret, contractual-embargo, confidential-third-party
or security-sensitive reason for temporary private treatment is identified.

Nothing here is asserted to be patentable. The mechanism is a fault-injection and invariant-audit
harness over an authored in-memory body; its predecessor is already public, and withholding it would
not preserve novelty the published M077 record has not already spent.

## Scientific boundary

- M077 remains closed and immutable. Its schedule, salt and body are not reused; its artifacts are
  read only as a closed record.
- The preregistration is frozen **before** the harness exists, and the schedule salt was drawn
  before any implementation was begun. That order is the method, not a formality: a schedule chosen
  after the body exists is a degree of freedom over the result.
- The human-equivalent component of G7 is **refused mechanically**, not merely in prose. The result
  schema will carry no field able to express wall-clock duration, human-equivalent time or a fitted
  horizon, its field list will be an enforced allowlist, and the checker will fail closed if such a
  field appears.
- **Even a fully positive result does not close G7**, does not establish real-environment autonomy,
  does not supply a cost model, and is not AGI evidence. The most it can do is move G7's evidence
  line from `open` to a bounded partial entry and state what is still missing.
- The three requirements recorded as **external blockers** — a human-maintained sealed bank,
  independent reproduction, external adversarial audit — are untouched. Each requires a person
  outside the project, and no internal result may be read as progress toward them.

## Owner gates that remain open

1. **The publication disposition** — the register row below. Until it exists, no harness is written.
2. **Owner authorisation of the frozen protocol**, if this milestone follows the M104/M105 pattern
   of authorising preregistration and implementation together.
3. **Acceptance of the result**, whichever way it comes out.

## Proposed register row

For the owner to accept, amend or refuse. Not written to `IP_ASSET_REGISTER.md` by this review.

> | P-025 | M121 / H66 quiescent-corruption long-horizon autonomy successor to M077 | **Proposed for
> public pre-registration, enabling implementation, schedule materialization and one canonical
> attempt**: build a shift harness whose fault schedule carries both operational and quiescent
> corruption, measure whether a periodic boundary monitor purchases coverage rather than latency
> against corruption that does not announce itself, and measure whether that coverage grows with
> the episode horizon. M077 remains closed and its schedule and body are not reused | Sole-human/
> AI-assisted framework established; Anthony Mets remains the sole human research director and the
> sole acceptance/release decision-maker. Anthropic Claude provided substantial design,
> preregistration and review assistance; OpenAI Codex or comparable tooling may provide independent
> review or execution assistance. All are recorded as AI tooling, none as human authorship, and
> none holds acceptance authority | Python standard library and existing development tooling only.
> Track A: no external model, network, task, credential, sealed bank, third-party attestation or
> new system authority. Faults mutate an in-memory pool only | **`PUBLIC_AGPL_COMMERCIAL_OPTION`** |
> *pending* | D043-prescribed successor to the M077 negative, which established that a boundary
> monitor is redundant with operational failure in a body where every corruption eventually reaches
> a guarded operation. M121 tests the complementary regime, with an internal positive control that
> reproduces M077 so the result cannot be true by construction. Horizons are episode counts and the
> human-equivalent component of G7 is refused mechanically. A positive result would be bounded
> mechanism evidence inside one project-authored in-memory body; **G7 would remain open** and no
> external blocker is approached. See `docs/IP_REVIEWS/M121_PUBLICATION_REVIEW.md`. |
