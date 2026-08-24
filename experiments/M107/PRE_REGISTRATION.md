# M107 — endogenous extension of the lower interpreter

**Hypothesis:** H52
**Decision slot:** D076 (reserved; unfilled until a canonical result exists)
**Track:** A — endogenous bounded lineage
**Pre-registration date:** 25 August 2026
**Status:** **PRE-REGISTERED QUESTION; NO PROTOCOL, POPULATION OR RESULT EXISTS**

## Why this milestone exists, and why it could not be M106

M106/H51 positively qualified a bounded **constructor-vocabulary** extension (D075). It could never
have qualified more. Its lower interpreter hardcodes `CONST/INPUT/NOT/AND/OR` and is *semantically
complete* over two signals: all sixteen Boolean functions already lie inside its complete image, so
no acquisition in that substrate can enlarge Boolean reach. Every reach claim there is about the
consumer dispatch image, never about the interpreter.

M107 removes that ceiling by construction rather than by argument.

## The substrate

The M107 interpreter holds **no operator semantics at all**. It evaluates an expression by looking
each internal node's operator up in a table carried in the lineage's own state and applying that
operator's truth table. Operators are data; the interpreter is a generic applier.

The initial table is the monotone fragment `{AND, OR}`. Its complete image is **four of sixteen**
functions, and it is closed under its own operators: monotone operators compose to monotone
functions at every depth. A non-monotone target is therefore excluded **by a monotonicity lemma, for
every node bound**, not by a search budget. The enumerated bound is nine nodes, which is the fixed
point: complete images are identical at nine, eleven and thirteen nodes, while S0 remains at four
functions at every bound.

The candidate space is generic: **all twenty** one- and two-ary Boolean operators. The host codes
the space; it never codes the answer.

## H52

Starting from S0 whose operator table is the monotone fragment, a lineage that observes only
behavioural demands can prove its current interpreter structurally insufficient, search the complete
generic operator space, acquire and register **one executable operator as lineage state**, survive
producer death, and thereby construct functions that are provably outside `complete_image(S0)`.

Formally, with two demanded behaviours D1 and D2 and the adopted extension A:

- `D1, D2` are not in `complete_image(S0)`, excluded by the monotonicity lemma, budget-independently;
- `complete_image(S0)` has size 4; `complete_image(S1)` has size 16, where `S1 = S0 + A`;
- `D1, D2` are in `complete_image(S1)`;
- A survives serialization and producer death and is required at execution time;
- removing A returns the reach to exactly `complete_image(S0)`;
- a fresh lineage holding S0, the same observations and the same exhaustive twenty-operator search
  cannot construct D1 or D2, for a structural reason rather than exhaustion.

A positive result would establish **bounded endogenous extension of the lower interpreter**: the
first Genesis result in which an acquisition changes what the interpreter can express at all, rather
than which of its existing expressions gets selected.

## The underdetermination control, pre-registered as a decisive condition

A single demanded behaviour does **not** determine the extension. Observing D1 alone leaves eight
surviving candidates in **two distinct reach classes** — one reaching eight functions, one reaching
sixteen — and the lineage must refuse. Only the two joint demands D1 and D2 collapse the survivors
to a single reach class, whose canonical representative is a unary operator.

This is recorded here, before the protocol exists, as a required behaviour and not as an obstacle:
an acquisition mechanism that adopted an extension under D1 alone would be selecting rather than
inferring, and H52 would be unsupported by that evidence.

## Decisive conditions

- **P1** runtime and input preflight bind the canonical runtime and the exact fixtures.
- **P2** S0 is the monotone fragment and its complete image has size four.
- **P3** the insufficiency certificate confirms D1 and D2 outside `complete_image(S0)`, every
  operator monotone, the complete image monotone, and exclusion budget-independent.
- **P4** under D1 alone the lineage refuses with at least two surviving reach classes.
- **P5** under D1 and D2 the operator space is exhausted and exactly one reach class survives.
- **P6** the adopted operator is registered as lineage state and is content-addressed.
- **P7** `complete_image(S1)` has size sixteen and contains D1 and D2.
- **P8** the producer process dies; a fresh isolated process receives only the serialized state.
- **P9** the revived lineage constructs D1 and D2 and the witness expressions execute correctly.
- **P10** ablation of the acquired operator returns the complete image to exactly four functions and
  makes D1 and D2 unconstructible.
- **P11** the fresh-lineage control with S0, the same observations and the exhaustive twenty-operator
  search constructs neither D1 nor D2.
- **P12** a repeated fresh control with a larger node bound also fails, so the difference is reach
  and not budget.
- **P13** mutation of the acquired operator's table changes the reach as predicted, and corruption
  of the state fails closed.
- **P14** byte-exact rollback to S0 reproduces the S0 state digest exactly.
- **P15** every isolated process reports zero model, network and remote-execution calls.
- **P16** independent replay reproduces the stable evidence projection exactly.

**Verdict rule:** positive if and only if P1-P16 are all computed and true; negative otherwise. One
canonical attempt and one canonical checker replay are permitted. The first result is preserved even
if negative and may not be repaired.

## Instrument requirements, inherited from D072 and D074

M103 and M105 were both lost to a checker that could not start. Before any M107 freeze, the complete
`CANONICAL -> PRESERVE -> CHECK -> REPLAY` chain must be rehearsed end to end against a materialized
DEVELOPMENT result in a throwaway clean checkout, using exactly the frozen commands, exercising the
checker as a direct script through the replay branch, with exit codes asserted for result-present,
result-absent, corrupted-result and report-already-exists, and with every predicate computed.

## What M107 cannot establish

Modification of the acquisition machinery itself; recursive depth of two or more; measured recursive
acceleration; self-identification of which internal mechanism to improve; open-ended operator
growth; transfer to an independently maintained domain; G1-G10 closure; general-agent evidence;
self-hosting; AGI.

The signal width, the node bound, the operator arity ceiling, the candidate space, the demands and
the evaluator remain authored. A positive M107 moves the ceiling to **the acquisition machinery
itself**: the next question is whether an acquired extension can change the mechanism that performs
later acquisitions, not merely what those acquisitions can express.
