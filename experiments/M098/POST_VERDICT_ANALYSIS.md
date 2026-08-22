# M098 post-verdict analysis — persistence passed, stable replay did not

M098 attempt 1 is a negative qualified result. It was armed once from clean freeze commit
`1b862ab9afaec13cf16c7fcc6da7c297956424d4`, with no model, network or remote calls. The checker
computed all twelve conditions: eleven passed and P12 failed. Result digest `3cce5155…`; checker
digest `b04513a2…`.

## What passed

The producer wrote the exact 304-byte M097 state and terminated. Eight later consumer invocations
used fresh base-Python `-I` processes. Their capsule contained exactly the generic runtime and entry
point, their search paths omitted the repository, and they imported no project module. The retained
extension executed 3/3 entirely post-M097 worlds. The empty-extension, semantic-mutation and
corrupt-digest controls all failed. A live semantic fault suppressed the capability and restoring
the exact original bytes restored it in another fresh process.

## Why P12 failed

The frozen `stable_projection` removes dictionary fields named `pid`, `producer_pid` and
`search_path`, but overlooks `process_boundary.consumer_pids`, the eight-element summary list. The
canonical run and replay necessarily recorded different process identifiers. A post-verdict
diagnostic compared the two projected records: after removing only that overlooked list, the
records were exactly equal and both had digest
`3794831aa3a13fd6711e50b3a44b9a1bcef1266c0d713d8fff0a069ea397643c`.

That diagnostic explains the failure; it does not change the verdict. Editing the frozen projection
or checker after observing the result would violate the no-post-verdict-repair rule. M098 remains
negative at 11/12.

## Successor requirement

M099 may correct the projection only under a new frozen protocol and a fresh qualification
population. It must exclude every concrete process identifier while retaining the causal process
facts: producer termination, exact invocation count, PID presence and producer/consumer separation.
The direct persistence, control and rollback conditions remain required rather than inferred from
M098.
