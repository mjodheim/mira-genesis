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

The enabling runtime, fixtures, isolated orchestration, independent checkers and adversarial audit
now exist. Two complete DEVELOPMENT rehearsals produced identical stable projections and all
P1-P16 evaluated true under the candidate checker. This is apparatus validation only. No
`PROTOCOL.json`, canonical `RESULT.json` or canonical checker report exists until the separate
freeze chronology is completed.

The freeze lifecycle was rehearsed end to end in a throwaway clone — candidate, accepted-candidate
tag, final protocol, freeze tag, runner preflight — and two instrument defects were corrected
before any candidate existed. See `ADVERSARIAL_REVIEW.md`. The canonical `materialize` command was
not executed in any checkout, so attempt 1 and its outcome remain unconsumed and unknown.

The owner-signed chronology is, in order, on a clean worktree at the exact reviewed commit:

1. annotate the reviewed source commit and run `build_m105_protocol.py candidate --source-ref …`;
2. commit `PROTOCOL_CANDIDATE.json` alone, annotate it, and run `build_m105_protocol.py final
   --source-ref … --freeze-tag …`;
3. commit `PROTOCOL.json` alone and create the annotated freeze tag named in it;
4. `run_m105_qualification.py preflight`, then the single
   `run_m105_qualification.py canonical --owner-authorized --understand-unique-attempt`;
5. preserve and tag the first result bytes, then the single `check_m105_result.py --replay`.

Every file in the protocol's bound apparatus list — including this README — must be final before
step 1, because the runner recomputes each bound digest and refuses if any member changed.
