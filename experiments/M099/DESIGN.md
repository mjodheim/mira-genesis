# M099 — stable replay of hard process-death persistence

M098 passed every direct persistence, isolation, control and rollback condition but failed its
replay condition because the frozen evidence projection retained `consumer_pids`. M099 is a new
experiment, not a repaired or repeated M098 attempt.

## Fixed before qualification

The process mechanism is byte-identical to the preserved M098 mechanism. The only intended change
is in successor apparatus: the stable projection recursively excludes the four predeclared keys
`pid`, `producer_pid`, `consumer_pids` and `search_path`. It retains producer termination, the eight
fresh-process invocation count, PID-record presence, producer/consumer separation, capsule purity,
all runtime outcomes, state digests and rollback hashes.

Unit evidence before freeze proves that arbitrary changes to every excluded process identifier do
not alter the projection, while changing a scientific outcome does. This policy is protocol-bound
and cannot be expanded after the run.

## Fresh population

Three new worlds — storage headroom, pressure drop and inventory delta — share no class, field, key
or case identity with M097 or M098. Preflight only builds and parses them. No producer, persisted
consumer, fault or rollback execution is permitted before freeze.

## Verdict

M099 repeats all twelve hard-persistence conditions. It does not inherit M098's eleven positive
subconditions. A positive verdict requires all three new worlds, all absence/mutation/corruption
controls, the live-fault and byte-exact rollback sequence, the process-isolation census and an exact
clean replay after the frozen ephemeral projection.

The claim boundary remains M098's: one acquired symbolic operation, local disk state and an authored
generic interpreter. No self-hosting, transactional crash consistency, hostile-code sandboxing,
unrestricted repair, open-ended evolution or generality gate is claimed.
