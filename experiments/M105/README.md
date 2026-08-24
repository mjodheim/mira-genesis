# M105 — executable constructor-vocabulary extension

M104 qualified a bounded improvement to hypothesis construction, but its acquired constructor was
still only a subset of seven authored feature tokens interpreted by host conditionals. M105 tests
whether the continuing lineage can acquire an executable feature definition absent from that
vocabulary and make it causally useful for later acquisition.

The intended chronology is:

```text
W0 = exact positive M104 V3 bytes + empty M105 feature registry
  -> DEVELOPMENT-only feature acquisition
W1 = W0 + content-addressed executable feature F
  -> producer death
  -> later JSON-document acquisition using live F
W2 = W1 + J
  -> producer death
  -> later SQLite acquisition using live F
W3 = W2 + Q
  -> producer death
  -> hidden execution, controls, rollback and replay
```

The lower expression substrate, signal interface, carrier adapters and evaluator remain authored.
M105 therefore targets the fixed high-level constructor vocabulary, not the lower-interpreter
ceiling. No canonical run may occur until a final `PROTOCOL.json` binds the complete apparatus and
the adversarial audit is clean.

Authoritative pre-run records:

- `PRE_REGISTRATION.md` — H50, chronology, controls and falsifiers;
- `PROTOCOL_DRAFT.json` — implementation-neutral draft boundary;
- `../../docs/IP_REVIEWS/M105_PUBLICATION_REVIEW.md` — owner publication disposition.
