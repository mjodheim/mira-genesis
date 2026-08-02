# M032 — trans-substrate rewrite lifecycle

M032 joins two previously separate verified development bases:

- M025 can search, independently validate, adopt, serialise, replay and roll back a
  bounded executable rewrite;
- M013e can discover the undeclared Boolean semantics of an opaque finite substrate and
  synthesise an exact native DFA body there.

The experiment asks whether one transaction can carry the *rewritten* competence,
internal rewrite tools and relevant learning state across that unknown-substrate
boundary without a human redesigning the destination architecture.

The first development increment implements the bridge and its fail-closed transaction.
It does not yet claim post-migration learning advantage, autonomous diagnosis or three
repeated improvement cycles.

See [`PROTOCOL_DRAFT.md`](PROTOCOL_DRAFT.md) for the pre-result gates and
[`STATUS.md`](STATUS.md) for the current implementation state.
