# M018 — Status

- Protocol: **DEVELOPMENT DRAFT**
- Canonical results permitted: **NO**
- Scientific status: `DEVELOPMENT — HYPOTHESIS NOT SUPPORTED`
- Development tests: **7 passing**

## The prediction was wrong

It had been written before the measurement, in `PROTOCOL_DRAFT.md`:

> `(1)` and `(2)` will reduce the liability without cancelling it, `(3)` will cancel it
> but will cost dearly on stable environments.

The second half holds. **The first is false, and it is the half that carried the
hypothesis.** None of the three mechanisms cancels the transport liability.

## What the measurement says

Three environment pairs, four policies. The reference is `NoForgetting`, that is M017's
organism, which accumulates and never discards.

| | stable | shift | transport |
|---|---|---|---|
| `budget` | **identical** | +3% | +6% |
| `utility` | up to 177× worse | +2% | +4% |
| `dissolution` | **350× worse** | −18% | 0% |

- **Dissolution is a disaster.** 14,898 nodes against 42 in a stable environment. It
  throws the good out with the bad and wins nowhere.
- **A hard budget is the only mechanism with no downside**: strictly identical cost when
  stable, and a few percent elsewhere. Its benefit stays marginal.
- **None restores improvement.** The 0.69× liability measured by M017 survives.

## Why, and this is the useful part

Three reasons, in order of importance:

1. **Forgetting is reactive.** A useless symbol is paid for up front, on every episode,
   at every search node. By the time the organism knows a macro does not serve, it has
   already financed it. Discarding afterwards refunds nothing.
2. **Destruction is indiscriminate.** Dissolution cannot tell what has stopped serving
   from what is about to serve again, and pays 350× for that ignorance.
3. **A useless macro's cost is real but modest.** The branching factor goes from 36 to
   about 48 symbols, and searches often end early. There is no 45% sitting there to be
   recovered by deletion alone.

## What it redirects

The problem is not that the organism cannot destroy. It is that **every symbol is
unconditionally available, at every step**.

The remedy the measurement points at is not deletion but **selection at the moment of
use**: cheaply predicting whether a macro can apply to *this* source before expanding it.
That is not forgetting, it is conditional activation — and it destroys nothing, so it
costs nothing in a stable regime.

This is also where the caterpillar metaphor shows its limit. It dissolves because it
builds another body **once**. An organism facing repeatedly shifting distributions cannot
dissolve every time: it has to contextualise, not destroy.

## Second reading, which opened M019

The result does not say that destroying is useless. It says that **destroying is
untenable for an isolated individual**: the caterpillar dissolves once, and if that
fails, that caterpillar dies — not the species.

It also points at a deeper cause: the search budget was 200,000 nodes and failure cost
nothing. **There was nothing to be efficient for.** That is what M019 put to the test.

## Next gate

Implement the gating mechanism and measure it on the same three regimes, against the four
policies already in place. The rig exists; it needs a fifth column.
