# M017 — Protocol, signed but not frozen

**Status: §2 THRESHOLDS SIGNED. FREEZE BLOCKED — see §11. No canonical evaluation is
authorised.**

Writing the sealed generator, which §10 requires before hashing, exposed a false success
on an out-of-language negative control. That is a §7 falsifier and an unmet §3.2 admission
condition, so the remaining checklist boxes may not be ticked. §11 records it.

- Thresholds of §2 reviewed and signed by: **Anthony Mets**, 3 August 2026. That signature
  stands: the thresholds are not what failed.
- This document supersedes `FROZEN_PROTOCOL_017_CANDIDATE.md`, which was written in
  French and is retained unchanged as the pre-signature record.
- Translated to English before hashing, because D012 and `LANGUAGE_POLICY.md` govern the
  active surface and a document frozen forever must be frozen in the repository's
  language.

> **A defect was found after drafting, then corrected and re-measured.** The confirmation
> of a candidate drew 96 long words at random while claiming to cover the distinguishing
> bound of two automata. It did not: the "zero false successes over 42 episodes" was a
> favourable draw, not a guarantee. Two 9-state automata confirmed identical turned out to
> be separated by `(1,0,1,0,1,0,1)`.
>
> Corrected across three versions, two of which were wrongly announced as correct — see
> `FAILURE_LOG.md`. The retained version is a conformance test by the W-method on a
> minimised hypothesis, with transition cover and a margin computed from the source's
> state count. Complete, and shorter than the set it replaces.
>
> **The four measurements in this document were redone under that confirmation and return
> strictly identical figures.** Search cost did not depend on the confirmation; what did
> depend on it is the admission condition, now genuinely established.

The six development gates are passed. This is the complete protocol, thresholds included.

Freezing is irreversible in spirit: once hashed, no threshold moves, and the canonical
evaluation runs exactly once, without replay.

---

## 1. Hypothesis

In an environment whose compositional structure repeats, an organism that absorbs its
recurring motifs into its vocabulary acquires expressive power it did not have, and sees
its search cost collapse. A closed-catalogue organism cannot follow it. An organism that
composes without ever absorbing does not improve over time.

## 2. The decisive comparison — one only

> Median, over the late episodes of a sealed environment, of the paired ratio between the
> search cost of open search and that of the self-extending organism, measured on the same
> episode.

**Criterion: in every sealed environment, this ratio favours the self-extending
organism.** Never on average.

**Sign-test guard:** in every environment, the self-extending organism must be faster on
strictly more than half of the paired late episodes.

### Why a directional criterion and not a magnitude

A magnitude threshold was proposed first — 10×, derived from search-space arithmetic,
which predicts ~500× — then **invalidated by the fifty-environment sweep**.

Over eight environments the minimum was 95×. Over fifty it is **9.0×**: one environment
falls below the 10× threshold. The initial sample was optimistic by a factor of ten.

The derivation assumed an absorbed macro is always reached at depth 1. That is the typical
case; when a late episode carries a noise atom, macro and atom must be composed, so depth 2
is required and the ratio collapses by a factor of fifty. A derivation of the typical case
had been taken for a worst-case bound.

D010 requires a margin to exceed the observed dispersion. The magnitude's is a factor of
**69** — from 9× to 620× — which no defensible margin exceeds. The direction does not
disperse: **50 environments out of 50** favourable, none adverse. That is the only
criterion the rule permits.

Lowering the threshold to 5×, which would pass 50/50, would be precisely the post hoc
adjustment §7 forbids.

The guard is at one half because that is the neutral point of a sign test. Without it, a
degenerate absorption rule — one that swallowed everything — could satisfy the median while
degrading the majority of episodes.

## 3. Admission conditions

Unmet, the experiment is void whatever the search cost.

1. **Zero false successes.** Every announced solution is exactly equivalent to the target.
2. **Abstention on every negative control**: target outside the language, unstable oracle.
3. **Exact re-embodiment** of the old and new body on an opaque substrate.
4. **Archive intact** byte for byte.
5. **Entirely integer decision trace**, verified by `audit_m017_isolation.py`.
6. **Isolation**: the organism's code reaches no laboratory name.

## 4. Reported, never decisive

| Quantity | Why it does not decide |
|---|---|
| closed catalogue, M014c capability | Structurally incapable, 0/42 in development. A threshold set against it would pass trivially. |
| episodes solved by the self-extending organism alone | Real, but its magnitude depends on the budget, which is a parameter. |
| median description length | Follows absorption mechanically. |
| number of absorbed macros | Measures the rule's activity, not its usefulness. |
| **transport to another environment** | See §6. |

## 5. Cost of absorption — reported explicitly

Measured in development:

- worst single episode: **0.74×**, the self-extending organism is 35% slower;
- slower late episodes: **8 out of 49**, that is 16%.

A macro that does not apply still costs: it widens the branching factor. This is the
macro-operator utility problem. It is in the minority and compensated, but it must appear
in the result.

## 6. Scope — what M017 will not claim

**The extended language does not transport.**

| Inherited library | Median gain | Pairs |
|---|---|---|
| shared motifs | 118.7× | 3/4 help |
| disjoint motifs | **0.69×** | **4/4 harm** |

A library inherited from an environment with different motifs is strictly worse than no
library at all, on all four measured pairs, within a tight band of 0.65 to 0.75.

M017 will therefore claim language growth **within** a distribution of transformations,
and nothing more. That is M014b's lesson — transporting a mechanism does not transport its
advantage — carried into the protocol before freezing instead of being discovered after a
canonical evaluation.

M017 demonstrates no more: neither autobiographical memory, nor continuous physics, nor
invention of a new role, nor choice of its own body. The language remains bounded to four
roles and two atom forms, over a finite Boolean domain. **M017 is the first step toward H6,
not H6.**

## 7. What would falsify M017

Stated before the evaluation:

- a single sealed environment where the median paired ratio favours open search;
- a single environment where the sign-test guard fails;
- a single false success;
- a single missed abstention on a negative control;
- a single inexactly reconstructed body, or a modified archive.

No rerun replaces the first attempt. No threshold is relaxed after observation.

## 8. Sealed evaluation procedure

1. Create the research branch and its sealed workflow, triggered on `opened` of a pull
   request to `main`, guarded by `head_ref`.
2. The workflow extracts the immutable head, installs from the manifest, runs the tests,
   then `audit_m017_isolation.py`, **before** the evaluation.
3. Sealed environments are generated only from the nonce derived from the head SHA, and
   therefore only after that head exists.
4. One single run. The artifact and its SHA-256 are published in `results/M017.md`.
5. The workflow then moves to `archives/workflows/`, per D008.

## 9. Reproduction of the freeze evidence

GitHub Actions run `30669588931`, `workflow_dispatch` on `research/m017-freeze-gates`,
job `freeze-evidence`.

**Every number is identical** between the local execution (Windows, Python 3.14) and CI
(Ubuntu, Python 3.11): the eight dispersion environments and the four transport pairs, line
by line, including the per-environment values.

That is the direct verification that the correction imposed by M014b holds. M014b's
`consolidation_record_sha256` differed from one environment to another because it
incorporated floating-point scores: the scientific result reproduced, its proof did not.
M017 decides only on integers, and that is observed rather than postulated.

## 10. Freeze checklist

- [x] Human review and signature of the §2 thresholds — Anthony Mets, 3 August 2026.
- [x] Writing the sealed generator and its nonce deriver — `metamorphosis/m017_sealed.py`.
- [ ] **BLOCKED** — Writing the sealed evaluation workflow. See §11.
- [ ] **BLOCKED** — SHA-256 hash of this document, reported in `results/M017.md`.

Until the first box is checked, none of those that follow may be.

## 11. Why the freeze is blocked

Writing the sealed generator put the admission conditions under a seed set the development
bench had never used. The out-of-language negative control then produced a **false
success**: against a 7-state target, from a 6-state source, the organism announced
`program_identified` with a 6-state solution that is not equivalent, separated by
`(0, 0, 1, 0, 0, 0)`.

That is two §7 falsifiers at once — a false success, and a missed abstention on a negative
control — and §3.2 is therefore unmet.

### The cause is a scope assumption, not a coding error

`_confirm` states its own bound:

> The structural language does not create states, so the target cannot have more than the
> source. It is this bound — known to the organism, which holds the source — that makes
> the suite complete without assuming anything.

The W-method suite is complete **for targets within the language**. The out-of-language
control is defined by *adding a state*, so it sits outside that bound by construction.

§3.2 therefore asks the organism to abstain on targets its own confirmation is
structurally unable to detect. The control tests something the instrument cannot see.

Measured:

| Confirmation bound | Suite | Detects the mismatch |
|---|---:|---|
| source states (current) | 34 words | no |
| source states + 1 | 69 words | yes |

### The development pass was a favourable draw

Gate 5 was declared passed on **two** negative controls, both of which abstain. An
independent sweep of 24 out-of-language controls produces **2 false successes**, an escape
rate near 8 per cent. Two controls pass clean about 85 per cent of the time, so the
development bench was not unlucky — it was simply too small to see the escape.

This is the third instance in M017 of a small favourable sample taken for a guarantee: the
96-word probabilistic confirmation, the unminimised W-method hypothesis, and now the
confirmation bound. It is the failure mode D010 was written for.

### What must be decided before freezing

Raising the confirmation bound to `source + 1` restores detection at roughly double the
suite. It also changes the organism's query cost, which is part of what §2 measures. The
bound is therefore a protocol parameter and must be signed with the thresholds, not
adjusted afterwards.

Gate 5 is re-opened. It must be re-passed on a sample large enough to exclude a draw of
this size before the checklist resumes.
