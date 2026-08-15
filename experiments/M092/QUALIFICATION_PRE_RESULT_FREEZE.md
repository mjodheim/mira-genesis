# M092-I pre-result qualification freeze note

Status: **pre-result, non-qualifying infrastructure only**.

This note was committed while the first canonical M092 criterion-search segment was still running and
before any canonical result, selected candidate, independent reproduction result, or hidden
qualification material was available to this branch.

It does not amend `PROTOCOL.json`.  It removes implementation ambiguity in the later qualification
runner while the result is still unknown.

## Family execution

The two frozen families reuse one and the same dynamically supplied downstream parity primitive.

- `alternating_allocation`: execute that primitive once on `(slot 0, input 0)`.
- `complementary_protocol_phase`: execute that same primitive once, then the inherited language
  primitive `APPLY_UNARY(slot 0, "neg")`, then `APPLY_UNARY(slot 0, "inc")`.

Thus family B computes `1 - parity` by composition.  No second target-specific substrate operation or
downstream primitive is permitted.

## Qualification controls

The later runner/checker must account for all eleven arms already named in the protocol.  The
`more_budget_same_substrate` arm means ten complete independent searches with state reset between
repetitions; multiplying a reported counter is not an execution.  Only `evolvable_substrate` may
score a qualifying world as solved.  Each control must pass zero complete qualifying families.

No new operation may be registered during qualification.  Model calls and network calls remain zero.
The theorem/certificate result and finite empirical qualification remain separate fields and separate
evidence.

## Hidden draw ordering

The phrase `counter-mode SHA-256 rejection sampling without replacement ... candidates are consumed
in digest order` is implemented as **acceptance order of the domain-separated counter-mode digest
stream**.  Accepted candidates are not lexicographically re-sorted after generation.  Each accepted
record retains its digest and counter so an independent checker can reconstruct the stream exactly.

This interpretation is recorded before hidden values are materialized; it cannot be chosen in
response to a favorable or unfavorable qualification draw.

## Non-claims

This freeze note contains no candidate program or certificate, no canonical or reproduction result,
no extended-state digest, and no hidden qualification value.  It does not open the qualification gate
and does not authorize materialization before committed adoption plus fresh-process reload after a
matching independent reproduction.
