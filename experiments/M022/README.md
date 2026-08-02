# M022 — Adaptation-stress controls

M022 tests whether a staged held-out sequence can expose competence acquired after an
audit begins. It preserves M021's transferred-quality result and treats post-selection
adaptation as a separate question.

- [`PROTOCOL_DRAFT.md`](PROTOCOL_DRAFT.md) defines the paired adaptive/frozen audit and
  its pre-written controls;
- [`STATUS.md`](STATUS.md) records the current development evidence and limitations;
- `metamorphosis/m022_adaptation_stress.py` builds and evaluates repeated-motif cases;
- `scripts/run_m022_adaptation_smoke.py` executes the real positive and negative
  controls;
- `tests/test_m022_adaptation_stress.py` covers pairing, isolation and failure guards.

Nothing in M022 is frozen or canonical.
