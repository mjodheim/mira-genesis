# M107 — endogenous extension of the lower interpreter

M106/H51 qualified a bounded **constructor-vocabulary** extension and could never have qualified
more: its interpreter is *semantically complete* over two signals, so all sixteen Boolean functions
already lie inside its complete image and no acquisition can enlarge Boolean reach.

M107 removes that ceiling by construction. Its interpreter holds **no operator semantics at all**.
It evaluates an expression by looking each internal node's operator up in a table carried in the
lineage's own state and applying that operator's truth table. Operators are data; the interpreter is
a generic applier. Extending the table is therefore extending what the interpreter can express.

## The substrate is incomplete on purpose

| | |
|---|---|
| initial operator table | the monotone fragment `{AND, OR}` |
| `complete_image(S0)` | **4 of 16** functions |
| exclusion of non-monotone targets | by a **monotonicity lemma**, at every node bound |
| node bound | 9, the closure fixed point (identical images at 9, 11 and 13) |
| candidate space | **all 20** one- and two-ary Boolean operators |

Monotone operators compose to monotone functions at every depth, so `XOR`, `XNOR` and every
negation-dependent function are outside reach for a **structural** reason, not because a search ran
out. No amount of extra budget can reach them from S0.

## What the lineage must do

1. prove its current interpreter structurally insufficient;
2. search the complete generic operator space;
3. acquire and register **one executable operator as lineage state**;
4. survive producer death;
5. construct functions provably outside `complete_image(S0)`.

## The underdetermination control

A single demanded behaviour does **not** determine the extension. Observing D1 alone leaves eight
candidates in **two distinct reach classes** — one reaching eight functions, one reaching sixteen —
and the lineage refuses. Only the two joint demands collapse the survivors to a single reach class,
whose canonical representative is a unary operator.

This was discovered in DEVELOPMENT and pre-registered as a decisive condition **before** any
protocol existed. An acquisition that adopted an extension under D1 alone would be selecting rather
than inferring.

## Status

Pre-registered as H52; apparatus complete; adversarial audit clean at twenty-one checks; the full
DEVELOPMENT evidence evaluates all sixteen predicates true. **No protocol, canonical attempt or
result exists.** See `PRE_REGISTRATION.md` and `ADVERSARIAL_REVIEW.md`.

## What a positive M107 would and would not establish

It would establish **bounded endogenous extension of the lower interpreter**: the first Genesis
result in which an acquisition changes what the interpreter can express at all rather than which of
its existing expressions is selected.

It would not establish modification of the acquisition machinery itself, recursive depth of two or
more, measured recursive acceleration, self-identification of which mechanism to improve, open-ended
operator growth, transfer to an independently maintained domain, G1-G10 closure, general-agent
evidence or AGI.

The signal width, the node bound, the arity ceiling, the candidate space, the demands and the
evaluator remain authored. The next ceiling is **the acquisition machinery itself**.
