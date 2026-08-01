# M020 — Controlled self-rewrite

M020 is the first executable step from trans-substrate migration toward genuine
self-metamorphosis.

The active policy source is treated as a cognitive body. Mira owns a bounded registry
of rewrite tools, searches candidate bodies, evaluates them without access to held-out
answers, and may adopt a candidate only after a strict development improvement. The
previous body remains archived exactly and can be restored.

Files:

- [`PROTOCOL_DRAFT.md`](PROTOCOL_DRAFT.md) — the development question and gates;
- [`STATUS.md`](STATUS.md) — what is implemented and what remains;
- `metamorphosis/m020_self_rewrite.py` — rewrite language, tool registry, evaluator and
  versioned body;
- `tests/test_m020_self_rewrite.py` — safety, improvement, rollback and tool-learning
  tests.

This is not unrestricted recursive self-improvement. It is the bounded, decidable core
that must work before the project widens the code language or grants external tools.
