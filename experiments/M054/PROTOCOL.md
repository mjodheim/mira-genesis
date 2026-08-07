# M054 — bounded endogenous construction of a composable primitive

**Status: PROPOSED — unqualified.**

## Research question

Can the continuing lineage build a transformation primitive by composing formation rules,
rather than filtering a catalogue of extensions; validate it independently; adopt it
transactionally; and then reach a second task **only by composing what it acquired with
itself**, where the same budget without that acquisition does not reach it?

## Why this is not M053 again

M053 extended the language by filtering `META_PROGRAMS`, a tuple of sixteen pair expressions
materialised at import. That is selection from a declared catalogue — the shape D009 rejects
and D016 closed one level down. The level moved; the shape did not.

M054 removes the catalogue. Candidates are built from two atoms and five operators under a
declared depth. Nothing enumerates the admissible space, and the number of candidates actually
constructed is recorded so a run that enumerated in effect cannot present itself as one that
built.

## Declared parameters

Fixed before the qualification run and pinned by permanent test.

| Parameter | Value |
|---|---:|
| Atoms | `previous`, `current` |
| Operators | `add`, `subtract`, `minimum`, `maximum`, `multiply` |
| Formation depth | 3 |
| Admissible space at that depth | 29,330,422 |
| Admissible space at depth 2 | 2,422 |
| Construction budget | 1,024 |
| Beam width | 12 |
| Maximum composition length | 2 |
| Behaviour domain | 81 integer pairs, `-4..4` squared |

The budget is below the depth-2 space and five orders of magnitude below the declared space.
Exhaustive enumeration is therefore impossible by construction, not by policy.

### Disclosure on the beam width

The beam width is a declared resource parameter, and it was raised from six to twelve during
development because a width of six discarded most of the first formation level, which would
have made the experiment a test of the ranking heuristic rather than of construction.

It is not tuned toward the accepted primitive. The heuristic's own top-ranked level-one
candidate is `multiply(previous, previous)`, which is unrelated to what is finally adopted, and
the adopted primitive is not reachable in one formation step from any founder primitive.

## Creation task

Total variation: the sum of absolute first differences. Every one of the 80 founder programs
is evaluated against the public probes first; construction is forbidden unless zero survive.
The founder language applies element-wise or set-valued transforms and whole-sequence
reductions, so it cannot express any operation over adjacent elements.

The expected primitive is `maximum(previous - current, current - previous)`, which denotes
`|current - previous|` at formation depth two. It is not stored anywhere in the founder
registry and is produced only after founder insufficiency is certified.

## Ambiguity and refusal

The search commits only when every solving candidate denotes the same function on the declared
behaviour domain. Two solving candidates with different behaviour mean the public evidence does
not determine the primitive, and the lineage refuses rather than picking one. Neither the
budget nor the depth is widened after a refusal.

Ambiguity is judged on behaviour, not on syntax: `maximum(a, b)` and `maximum(b, a)` are
different trees denoting one function, and a search that treated them as rival answers would
refuse whenever it rediscovered the same function written another way. This is the M052
equivalence argument applied to construction instead of to a frozen grammar.

## Reuse task and the ablation that decides the result

The second task is the maximum of the absolute differences **of** the absolute differences. It
is reached by applying the acquired primitive to its own output and then reducing.

This is the load-bearing requirement. In M053 the adopted extension is *used* on a second
family; it never becomes *material for building a third thing*. A language has grown only when
what it acquired can participate in the next acquisition.

Three arms under the same budget:

| Arm | Required outcome |
|---|---|
| Continued lineage, acquired primitive in the registry | composes it with itself and solves |
| Empty registry, same search, same budget, **same composition power** | does not solve |
| Founder catalogue only | does not solve |

The second arm is given `max_chain = 2`, so it may construct a primitive *and* compose it. A
control denied the composition the treatment arm enjoys would be a straw man, and the claim
being tested — that the acquisition is what makes the second task reachable — would be
unfalsifiable.

A single application of the acquired primitive must also fail the second task, so the result
cannot be a replay of the creation answer.

## Independent validation

The proposer sees public probes only. A separate validator owns the hidden probes, receives
content-addressed artifacts, and holds no adoption authority. The composed second-task program
is validated by the same independent path as the single primitive, not by the proposer's
report. A contradictory hidden probe must return a negative result. A tampered artifact must be
rejected on digest mismatch. An artifact beyond the declared depth must be rejected.

## Transaction, fault and rollback

The forced post-adoption fault tampers with the accepted artifact itself, changing a recorded
field while leaving its content address untouched. The fault must be *detected* — through both
a checkpoint mismatch and a failed digest re-derivation — before anything is restored. Recovery
rebuilds the registry from a serialised snapshot rather than a retained object, and refuses it
unless the checkpoint matches and every artifact digest re-derives.

Rollback counts as exact only when the fault is detected, the intact registry reports no fault
under the same detector, and the restored accepted tuple, checkpoint and serialisation match
byte for byte. A detector that cannot answer no proves nothing, so the negative case is pinned
by its own permanent test. This requirement exists because M053's first implementation compared
an object that had never been mutated against its own checkpoint, and could not evaluate to
false for any input.

## Qualification rule

M054 may pass in development only when the complete Python 3.11 and Python 3.13 matrices and
the repository-integrity job pass on the exact documented head. Every run that executes the
experiment's own code and fails remains in append-only qualification history. A run that fails
before the experiment starts is an infrastructure event under D017 and is not a verdict.

## Anti-cheating and claim boundary

M054 does not pass if the accepted primitive is drawn from any materialised list, is reachable
in one formation step from a founder primitive, encodes a lookup table of expected answers, is
useful only on the task that created it, or if the second task is solvable by applying it once
without composition.

The formation rules are human-written. They are the grammar of construction, not a catalogue of
results; what must not be human-written is any enumeration of what those rules can produce.

This remains one bounded finite experiment over integer sequences. It does not establish
arbitrary code generation, unrestricted self-modification, open-ended evolution, unknown-runtime
discovery, general intelligence, consciousness or production safety. Network, repository,
credential, deployment and external-system authority remain human-controlled.

M054 is noncanonical. M042 remains the only positive canonical continuous-lineage completion.
