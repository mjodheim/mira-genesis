# M107 / H52 — canonical result

> **VERDICT: POSITIVE (attempt 1). H52 supported within its frozen bounds. D076.**

Deliberately **outside** the protocol's bound apparatus list, so every bound member keeps the exact
bytes it had at freeze time and `experiment/m107-frozen-protocol-v1` stays verifiable by anyone.

| | |
|---|---|
| frozen protocol | `928c49908611a0c2b89a72655273c5c77eaf32a623af0671e741232aa45a2987` |
| bound apparatus | `9d6ec8e753aac8bcdee521e6092e472687c07abdf003b2ffded45072c0cd74f9` |
| result | `a11d6b3b7c584c135ddbf3a740e72ed876815be99c40fa4bd55d5dd72323b362` |
| stable evidence | `5c6eadfef68db188daf83f3194e8b7e7a1ecbbd1215520d5b6708ee03ae42d2d` |
| raw result bytes | `c4746bb7905af90e8be915e73a66f93ef1b37db1f9b45f2ac036c19f73c85b8a` |
| check report | `0c5f93785f3be96d379ef2fd38b2ce0d7765db6a0f596f363133518a7e99b5b8` |
| runtime | CPython 3.11.16 |

P1-P16 all computed true; replay performed and equal; zero model, network and remote-execution
calls.

## The causal chain

| | |
|---|---|
| `complete_image(S0)` | **4** of 16, operators `{AND, OR}` |
| D1, D2 | excluded by **monotonicity lemma**, budget-independent |
| one demand alone | 2 surviving reach classes, **refused** |
| joint demands | 20-operator space exhausted, **1** reach class |
| adopted | unary operator `(1,0)`, content-addressed lineage state |
| `complete_image(S1)` | **16**, both targets construct and execute after producer death |
| ablation | back to exactly 4, targets unconstructible, rollback byte-exact |
| fresh controls | fail at bound 9 **and** bound 13 |

**This is the first Genesis result in which an acquisition changes what the interpreter can express
at all**, rather than which of its existing expressions is selected.

It is **not** recursive self-improvement: one operator, acquired once, from a space of twenty the
host codes. The acquisition machinery is untouched and authored.

See `../../DECISIONS.md` (D076), `PRE_REGISTRATION.md` and `ADVERSARIAL_REVIEW.md`.
