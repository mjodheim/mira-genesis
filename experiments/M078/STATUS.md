# M078 status

**POSITIVE QUALIFIED DEVELOPMENT RESULT — TRACK A, MODEL-FREE.**

- Target: the one G1 clause M068 never tested — an incompatible body must produce a calibrated
  refusal rather than an invented adapter.
- Bank: 8 opaque bodies, 4 compatible and 4 incompatible, frozen before the discoverer.
- Discoverer: **4/4** compatible adapted, all 12/12 hidden; **0** false refusals; **4/4** true
  refusals; **0** invented adapters; **0** empty-set refusals.
- `never_refuse` control: invents 4 adapters, all 4 fail hidden validation.
- `always_refuse` control: recovers 0 adapters.
- Bank commitment `c37ea3dc…c0c0e`; first result `430f7822…e4976`, attempt 1, no retry.
- Local regressions: 25 passed. Independent checker: `failures: []`. Integrity: clean.
- Gate advance: **none.** G1 stays open; this supplies the missing clause as mechanism evidence.

## Frozen ordering

1. `f8a7dc4` froze `PROTOCOL.json` and `PROTOCOL.md` before any harness code existed; the salt was
   drawn first and bank content was absent from the freeze.
2. `afc14a9` added the discoverer and the body bank.
3. The bank was bound and the result preserved in one pass, attempt 1, no retry, no body replaced
   after an outcome was observed.

## Why refusal here is not trivial

Each incompatible body admits a candidate that fits every public observation, because one command is
stitched from two skills over their disjoint public inputs. A procedure that adopts the best public
fit therefore succeeds publicly and fails hidden validation — which is exactly what the
`never_refuse` control demonstrates. Refusal requires recognising under-determination, and refusal
caused by an empty candidate set is recorded under a separate kind that the threshold does not count.

## Information boundary

`discover` reads only `body.call` and the public inputs. A regression and the checker both parse the
function and assert that `hidden`, `body_class`, `aliased_pair` and `_operations` never appear. This
is the M069 falsifier enforced structurally.

## What a successor would need

Not more bodies or longer languages in this bank — that repeats the instrument. Closing G1 requires
bodies whose interaction language is maintained outside this project, selected after the discoverer
is frozen, plus independent reproduction. A successor must also not cite M078 as evidence about
model refusal behaviour; M074 remains the only result on that question and it is negative.
