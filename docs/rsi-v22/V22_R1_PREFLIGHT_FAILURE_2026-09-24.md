# V22 R1 pre-evaluator identity failure — 24 September 2026

Status: **no scientific verdict; no represented V22 observation was created**.

Three isolated R1 proposer outputs were returned and archived on
`results/rsi-v22-r1-20260924`. Their proposal/transcript pairs passed the supplied
`VERIFY_OUTPUT.py` boundary locally. Before any reserved JUnit objective was executed, an exact
apparatus-identity preflight compared the bytes reachable from the frozen apparatus lineage against
`docs/rsi-v22/V22_FREEZE_002.json`.

Sixteen committed identities matched. Two did not:

- `experiment/rsi_v22/utility.py`: freeze recorded
  `ad278160…`, actual committed bytes hash to `8ebae4e0…`.
- `experiment/rsi_v22/build_root_bundles.py`: freeze recorded
  `5a130069…`, actual committed bytes hash to `1aec9f42…`.

The mismatch was detected by workflow run `35946705189`. The job exited before bundle rebuild,
Maven preflight, public guard, reserved objective, campaign recording or adjudication.

This is therefore an **apparatus identity failure**, not a task result. The three returned proposer
outputs are retained but must not be scored into V22 and must not be retroactively legitimised by
editing `V22_FREEZE_002.json`.

A successor replication may reuse the already prospectively chosen task/evaluator/policy semantics
only if it is newly frozen before any successor proposer output, binds the actual immutable bytes,
and mechanically prevents old transcripts from satisfying the new R1 identity.
