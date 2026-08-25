# M112 — worlds this project did not choose

**Hypothesis:** H57
**Decision slot:** D081 (reserved; unfilled until a canonical result exists)
**Track:** A — endogenous bounded lineage, evaluated on an externally materialized holdout
**Pre-registration date:** 25 August 2026
**Status:** **PRE-REGISTERED QUESTION. THE BANK DOES NOT EXIST. Phase is `draft`.**

## The ceiling M110 and M111 share

Both qualified positively. Both carry the same sentence in their own decision records: **the project
authored the worlds.** `MIRA_GENERALITY_CRITERIA.md` names it for G4 in as many words —
*independently authored held-out transfer is absent*.

No further milestone inside this repository removes it, and it is worth being exact about why. The
removal is not a piece of code, an ablation or a wider population. It is an artifact somebody outside
the project has to make. M112 is therefore **not an experiment**. It is the receiving end of one.

## What is being built, and what is deliberately not

**Built:** the binding between the milestone-agnostic `mira-blind-bank-v1` contract and the
M110/M111 consumer family — a frozen analysis plan, a blind generator prompt and spec, a
tested-system freeze, a fail-closed phase machine, and a decisive CI step.

**Not built, and not simulated:** the bank. There is no payload, no commitment, no ledger and no
attestation. `assess_world_bank_readiness` reports phase `draft` and lists six blockers, all of them
artifacts this project cannot manufacture on its own without defeating the point.

If nothing further happens, that is the honest terminal state of this milestone, and it should be
reported as such rather than quietly dropped.

## Why the generator is unusually blind here

The generator is asked for **JSON records**, not for an experiment:

> five documents; three integer fields `alpha`, `beta`, `gamma` in `0..3`; a linked object holding an
> integer `zeta` in `0..3` and a short lowercase note.

That description contains no feature, no row, no component, no lineage, no notion of ambiguity and no
mention of what a world is used for. A generator given it cannot aim, because the target is not in
the prompt. The frozen prompt says so explicitly, and tells it not to try.

**Stratification happens afterwards**, by the structural criterion M111 already froze and published:
which worlds are *ambiguous* and which are *witness* is decided by the project's own public rule,
applied to worlds the project did not choose. The generator emits; the project classifies; neither
knows what the other did.

## H57

**H57.** On a consumer-world population **this project did not author**, sealed before anyone read it
and revealed only after the tested system was frozen, the M110 transfer result and the M111 diagnosis
result reproduce under their own frozen predicate sets, with arms, budgets and evaluators unchanged.

H57 is refuted if either fails to reproduce. **A bank that yields too few worlds in either stratum is
a negative result, not a retry** — that is declared in the frozen analysis plan and there are no
retries.

## The plan can fail, and that is checked

The generic contract records the M086-A defect: a positive verdict against a threshold that could
never fail. The mirror defect is a threshold that could never pass. `validate_analysis_plan` refuses
both, by deriving from base rates **measured over 1 160 project-generated worlds** whether the
declared minima are reachable and refusable:

| | |
|---|---|
| requested worlds | 100 |
| measured ambiguous rate | ~6 per cent → about 6 expected |
| measured witness rate | ~36 per cent → about 36 expected |
| minimum ambiguous | **3** |
| minimum witness | **3** |
| verdict if the bank yields fewer | **negative** |
| retries | **forbidden** |

At those rates a bank of 100 fails the ambiguous minimum roughly one time in sixteen. That is a real
refusal probability, not a formality, and it is fixed before the bank exists.

## The ordered chain

```text
plan frozen -> generator spec and prompt frozen -> generate once, outside, blind
  -> seal -> public commitment by digest -> tested system frozen
  -> signed reveal -> one run -> preserve
```

The **plan is frozen before generation**, because a minimum chosen after the yield was known would be
fitted to it. The **tested system is frozen after sealing**, because the harness must be written
against the carrier and freezing its digests costs nothing while no content is known. The invariant
that matters is `tested_system_unmodified_after_reveal`.

## What a positive M112 would establish, exactly

It removes **world authorship**. It does not remove **carrier authorship**: the value chain, the
document shape, the reference edge, the operators, the bounds and the evaluator all remain this
project's, and so do the feature vocabulary and the component registry.

The evidence tier is `blind_generated_sealed_bank`, and the ladder above it is unchanged:

- **context blindness is provable** — the generator sees one hashed input file, no repository, no
  network;
- **training-data independence is not provable** — an antecedence argument about one corpus is not a
  proof of ignorance;
- **human independence is not obtained at all** — no person outside the project authors or holds
  anything.

**G4 does not close on this, and no tier below `human_maintained_sealed_bank` ever will.** Nothing
produced under this contract may be reported as independent human reproduction.

## What this milestone must never be allowed to become

A project-generated bank relabelled as external. The payload validator refuses any world carrying a
key a blind generator could not have known — `row`, `component`, `stratum`, `census`, `target`,
`pair`, `policy`, `label`, `lineage`, `machinery` and the rest — and the contract's own contamination
scan runs over the whole payload. The readiness assessor never opens a payload, and there is no code
path in the module that could.

## Attempt discipline

One canonical attempt and one canonical checker replay, once a bank exists. The first result is
preserved even if negative and may not be repaired, relabelled or rerun. M109, M110 and M111 are
frozen and are not touched.
