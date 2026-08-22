# M098 — hard process-death persistence and byte-exact rollback

M097 acquired and serialized a new real-Python operation, but restored it inside the same
qualification process. M098 tests the stronger boundary reserved there: no live object, imported
development module or repair process may carry the capability into qualification.

## Process boundary

A standalone producer extracts the canonical operation-language state from M097, writes it to disk
and exits. Only after its termination does the runner launch fresh base-Python interpreters with
`-I`. Each consumer receives a temporary capsule containing exactly the generic M098 runtime and its
entry point. The capsule contains no acquisition, validator, qualification or Mira package, and the
repository is absent from its import search path.

The runtime observes an unambiguous binary mapping demand in real Python source, decodes the
persisted symbolic extension, instantiates it using the observed field roles and execution-checks the
generated method. It does not reacquire, revalidate or search for an operation.

## Frozen population and controls

Three entirely post-M097 worlds vary class, field, key, arity, scalar type and values. Preflight may
only construct and parse their source and cases; it may not run the producer, consumer, fault or
rollback path. A separate development world exercised the isolated runtime before freeze and is not
in the qualification population.

Qualification requires all three worlds to execute correctly after producer death. An empty
extension registry must close the capability, a well-formed `SUB` to `ADD` semantic mutation must
produce the wrong behavior, and a raw-byte corruption must fail closed on the state digest.

For rollback, the live persisted state is replaced by the semantic mutation and a fresh process must
fail. The exact original bytes are then restored and another fresh process must recover the
capability. Replay compares a stable projection that removes only process identifiers and temporary
paths; every scientific outcome remains bound.

## Boundary

This is local filesystem persistence of one acquired symbolic extension through complete producer
death, isolated consumer restart, fault and byte-exact rollback. The generic interpreter remains
authored host code. M098 does not claim self-hosting, transactional crash consistency, hostile-code
sandboxing, unrestricted repair, open-ended evolution or a generality gate.
