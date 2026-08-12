# Proposed disposition for issue #112

**No status change is made by this pull request.** Issue #112 remains open, unedited, and its
labels unchanged. This document records a recommendation for the owner to accept or reject as a
separate decision.

## What #112 is

[Issue #112](https://github.com/mjodheim/Mira-Genesis/issues/112) asks for an independent human
maintainer to hold M075's sealed private task bank. It is the external boundary M075's frozen
protocol requires before H21 can be tested at all, and
`scripts/check_m075_private_readiness.py` still reports four blockers, every one of which needs a
person outside the project.

## The three options

**A — keep #112 open as the stronger reproduction path.**
M075-B is built alongside it and neither replaces nor delays it.

**B — close #112 later as superseded**, if M075-B officially replaces the need.

**C — keep #112 as a second independent level**, to be pursued after a blind-generator
qualification.

## Recommendation: **A**, with C as the operational sequence

Option B should be rejected outright, and not merely deferred. M075-B cannot supersede #112,
because the thing #112 supplies is the one thing the audit found does **not** transfer: a mind
outside the project choosing the subject matter, and a person willing to attest independence and
sign for it. Every other element of M075's boundary — withholding, opacity, structural
impossibility, terminal-state scoring, single attempt — is mechanism, and M075-B reproduces all of
it. None of that adds up to the fourth element. Closing #112 as superseded would record a
substitution that did not happen.

So #112 stays open on its own terms (**A**). Operationally the two run in the order **C**
describes: M075-B can proceed now, and a human maintainer, whenever one appears, runs afterwards
against a separate bank at the tier that actually supports H21.

The distinction between A and C is worth keeping explicit. **A is the status of the issue**: an
open, unmet requirement, not a nice-to-have. **C is the sequence**: blind generation first because
it is available now, human maintenance second because it is stronger. If #112 were relabelled as
"second level", it would read as optional, and the register would slowly stop treating H21 as
untested.

## What should change on #112 if the owner accepts

Nothing about its state. One comment, pointing at `experiments/M075B/` and saying plainly:

> A weaker, separate instrument now exists for the same question. It uses a context-isolated
> external generator instead of an independent human maintainer, and produces evidence at the
> `blind_generated_sealed_bank` tier. It does **not** satisfy this issue. The requirement here is
> a person outside the project, and it is still open.

## What must not happen

- #112 must not be closed as `completed` on the strength of any M075-B result;
- no M075-B artifact may be cited in #112 as partial satisfaction of the maintainer requirement;
- the maintainer brief in `experiments/M075/MAINTAINER_BRIEF.md` must not be edited to mention
  blind generation as an alternative, because a prospective maintainer reading it should not be
  given the impression that their contribution is now optional;
- `AGENTS.md` §4's rule for M085 — that an external-maintainer requirement must not be replaced by
  evidence from a project-controlled AI agent — applies to M075 by the same reasoning, and this
  milestone is built to comply with it rather than around it.
