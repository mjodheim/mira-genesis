# Canonical benchmarks

## Currently validated domain

Deterministic finite automata and the local organs derived from them, over a discrete
alphabet, with exact equivalence computable.

## Mandatory metrics

- Exact functional equivalence whenever decidable.
- Number of queries available to the organism.
- Size of the passport and of the deltas.
- Preservation of earlier versions.
- Per-substrate exactness.
- Time and memory cost.
- Abstention on out-of-language cases.
- Comparison against learning from scratch.

## Mandatory controls

- Blank body.
- Distillation or classical relearning where applicable.
- Corrupted transformations.
- Cases outside the meta-grammar.
- Independent seeds.
- Hidden tests, separate from the learning budget.

## Measure design

A metric is not a criterion. Before a quantity may decide an experiment, four things
established by [`MEASURES.md`](MEASURES.md) must hold:

1. its **dynamic range** is established before any margin is fixed;
2. the criterion opposes two systems of **equal capability** at the start — a
   structurally incapable baseline is a control, never a criterion;
3. an admission condition is worth the **completeness of its verification procedure**,
   not the fact that a benchmark reports it satisfied;
4. the **evaluation horizon** exceeds the payback period of whatever is being rewarded.

Each of these comes from a measured failure, not from principle. Every case replays:

```bash
python scripts/reproduce_measure_failures.py
```

## External validity

No generalisation towards LLMs, consciousness, AGI or real-world environments may be
asserted without a dedicated experiment.
