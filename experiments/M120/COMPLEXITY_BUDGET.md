# M120 complexity budget

Written before the analysis plan, the generator spec, the bank nonce and the tested-system freeze,
and before any H65 observation exists.

M118 stopped because its instrument had grown past the point where a one-shot test could be trusted:
nine arms, a measurement design that failed two successive hostile reviews, and a rule elaborate
enough to issue a causal claim while the descendant was losing. M119 answered that by shrinking, and
the shrinking worked — the apparatus did everything it was asked to do. What M119 lost, it lost to a
gap between two contracts nobody had measured against each other.

So the budget for M120 is not "smaller than M119". It is **exactly M119, plus the smallest thing
that closes each named failure, and nothing else**.

## What may not grow

The scientific design is inherited from M119 by import, not by restatement, and this budget forbids
touching any of it:

| | |
|---|---|
| Arms | four, the same 2×2, plus the one fenced diagnostic arm |
| Primary comparison | `FULL` against `FRESH`, fixed in code |
| Endpoint | paired per-demand correctness, one way to win |
| Test | one-sided exact McNemar, α = 0.05, ten-point effect floor, both required |
| Guards | three, one direction each, veto only |
| Verdicts | four |
| Comparator seed | the committed constant, unchanged |
| Observation budget | 4000, inherited from M113 |
| Admissibility minimums | 3 qualifying carriers, 3 distinct structures, inherited from M115 |

A milestone that changed any of these would not be a successor testing the same target; it would be
a different experiment wearing the same name. `m120_bank.assert_inherited_science_unchanged` refuses
to derive a plan if the bytes of those modules move.

## What is allowed to be added, and why each is here

Five additions. Each names the M119 failure it closes, and no addition is admitted without one.

1. **`m120_carrier_contract`** — one representation, and a total decoder.
   *Closes:* 33 of M119's 34 host refusals came from two rules JSON Schema could not state, so a
   schema-valid completion was not a host-valid bank. Nothing smaller works: the relation between
   `arity` and `arg_size` cannot be expressed, only designed away.

2. **The narrowed carrier family** — three to four cells, at most one latent, two to three
   conditional actions plus two to three further actions.
   *Closes:* M119's bank collapsed to the minimum of every range, and the minimum of M115's family
   is not testable — decoding that committed bank leaves one machine of 37 qualifying. This is the
   one addition that reads a closed record, and it is disclosed as such rather than presented as
   prospective innocence.

3. **`m120_adequacy`** — the pre-seal scientific-adequacy gate.
   *Closes:* an admissible-but-inadequate bank consumed M119's one reveal. The gate is counts-only
   with an enforced output allowlist, so asking the question earlier does not create a channel.

4. **`m120_stress_schema` and `run_m120_readiness`** — readiness re-measured for this schema.
   *Closes:* M118's stress schema does not dominate the M120 candidate census, so inheriting its
   readiness would assert a measurement nobody took. The stress is deliberately not the candidate
   schema: previewing the bank would be a degree of freedom over the contract.

5. **A checker with no caller-selectable evidence path** — `check_m120_result.py` resolves the
   committed plan and measurements itself and re-derives the plan from code.
   *Closes:* both disclosed M119 checker defects, which are the same defect twice — authenticate
   one thing, score another.

## What is refused

- No second route, no fallback, no provider substitution.
- No additional arm, ablation, rollback or budget cell beyond the one M119 already fenced.
- No second generation, no redraw, no repair, no resample, no selection among outputs.
- No threshold, minimum, guard or decision rule rewritten for M120.
- No DEVELOPMENT branch inside the qualifying scripts. The rehearsal replaces the one HTTP call
  from outside and touches nothing else, so there is no code path that behaves differently when it
  matters.
- No repair of M115–M119. The two M119 checker defects are requirements here, not edits there.

## The running count

| | M118 | M119 | M120 |
|---|---|---|---|
| Principal arms | 9 | 4 | 4 |
| Diagnostic arms | 0 | 1 | 1 |
| Primary comparisons | 1 | 1 | 1 |
| Routes | 1 | 1 | 1 |
| Generations permitted | 1 | 1 | 1 |
| Reveals permitted | 1 | 1 | 1 |
| Gates before the seal | admission | admission | admission, adequacy |
| Gates before the freeze | readiness | inherited readiness | sizing, rehearsal, readiness |

The instrument gained three pre-freeze gates and one pre-seal gate. Every one of them is cheap,
mechanical, and fails in DEVELOPMENT rather than after a spend. That is the direction the budget
permits growth in, and the only one.
