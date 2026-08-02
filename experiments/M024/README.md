# M024 — Portable rewrite passport

M024 carries the bounded M020 self-rewrite state across a serialisation boundary:
executable source, rollback history, integrity evidence, primitive rewrite tools and
learned patch tools.

- [`PROTOCOL_DRAFT.md`](PROTOCOL_DRAFT.md) defines the information boundary, import
  invariants and development gates;
- [`STATUS.md`](STATUS.md) records implemented and missing capabilities;
- `metamorphosis/m024_rewrite_passport.py` implements canonical export and verified
  import;
- `tests/test_m024_rewrite_passport.py` covers exact migration, replay, rollback and
  corruption rejection.

This is not yet cross-substrate metamorphosis. It preserves one bounded executable
rewrite state so later substrate work has an explicit object to transport.
