# M108 / H53 — canonical result

> **VERDICT: POSITIVE (attempt 1). H53 supported within its frozen bounds. D077.**

Deliberately **outside** the protocol's bound apparatus list, so every bound member keeps the exact
bytes it had at freeze time and `experiment/m108-frozen-protocol-v1` stays verifiable by anyone.

| | |
|---|---|
| frozen protocol | `0160def2dad96c6478648cf1c2809570fbcfa8cebf3516acfacd098db72af5cd` |
| bound apparatus | `3851bce5a1d2d77018ef52e9839634ffadd39dd8ec1401c3331e77fb0aabff25` |
| result | `9bb97e2dcc907841332abad0daf97ddc264b9ba1636fc184e60997c2ddf5e9d5` |
| stable evidence | `0f976f9e5d4717c727938f42e45c5bbc98f0f24d057859dff39cb638982cbb51` |
| raw result bytes | `1b0c530bf25d42d1d862df864dc6199fcd38a7935fc6a455b2be10f8326131c4` |
| check report | `9c5627fb7cca23033d24297510ae6a5b6c5509f0c7e6353da4f11453ff74d7e5` |
| runtime | CPython 3.11.16 |

P1-P16 all computed true; replay performed and equal; zero model, network and remote-execution
calls; fourteen isolated processes.

## The causal chain

| | |
|---|---|
| `M0` operator table | `{AND, OR, ACQUIRED_153c9dbcc7}` — **M107's own acquisition, replayed** |
| `M0` reach at base width | **16 of 16**: saturated, so no failure of its can be an operator failure |
| `M0` attribution | hardwired to the operator axis |
| attribution domain | rows `{0, 2, 3}`; row 1 **unreachable**, by census over 63 states and 14 303 pairs |
| monotone control | rule space **4**, consistent rules **0** — generation 1 is a precondition |
| episodes covering rows `{0,3}` | 2 surviving attribution classes, **refused** |
| episodes covering `{0,2,3}` | 16-program space exhausted, 2 consistent rules, **1** class |
| adopted | `[1,0,1,0]`, two nodes, non-monotone, content-addressed lineage state |
| `M1` on `B` | blames the **signal interface**, extends it, builds `B` in 6 nodes, executes to target |
| `M0` on `B` | exhausts all 20 operators, refuses — at bound 9 **and** at bound 13 |
| equal budget | 1 machinery step of 2, for both |
| ablation | byte-exact rollback to `M0`; capability gone |
| mutation | attribution returns to the operator axis; capability gone |
| corruption | fails closed on identity mismatch |

`B` was outside reach for **two independent structural reasons**, both budget-independent: outside
all 16 liftable images of 256 world functions at the base interface width, for any operator set; and
outside the monotone image at full width by the monotonicity lemma. It became constructible only
once both generations were in place.

**This is the first Genesis result in which an acquisition changes the machinery that performs later
acquisitions**, rather than the vocabulary that machinery searches.

It is **not** recursive self-improvement. One attribution rule, over two authored features, chosen
from sixteen programs, in a three-signal Boolean world. Recursive depth of two remains unmeasured.

## Conceded, and declared

The episode blame labels are authored supervision. `B`'s feature row is one the episode set already
covers, so what is shown is generalization to a **new demand with a recorded feature pattern**, not
extrapolation into an unobserved feature region. Both concessions were written into
`ADVERSARIAL_REVIEW.md` before the freeze.

See `../../DECISIONS.md` (D077), `PRE_REGISTRATION.md` and `ADVERSARIAL_REVIEW.md`.
