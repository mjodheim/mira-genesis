# M074 — pre-freeze scientific review

**STATUS: REVIEWED EXECUTION APPARATUS. NOT FROZEN. NO SCIENTIFIC MODEL CALL MADE.**

Date: 2026-08-10.

## Decision

M074 may proceed to an exact protocol freeze, subject to the constraints below. The scientific
runner now exists and has been exercised only with deterministic fake or scripted backends. No
request from this apparatus has been sent to `gpt-5.6-sol`.

## Causal pairing

Independent model samples would make model stochasticity an undeclared difference between the two
arms. The scientific order therefore runs arm A before arm B for every task. Arm B replays arm A's
exact structured decision prefix, accepting a replay only when the complete `ModelRequest` digest
matches. If A refuses, B replays that same refusal and only then obtains new live decisions for the
steps that A's terminal rule removed. A request or response mismatch makes the campaign
inconclusive; it never falls back silently to an independent sample.

This makes the comparison causal only up to the observed divergence. It does not turn the six
authored tasks into a representative population or make the model deterministic.

## Precommitted positive threshold

A positive result requires all of the following in one complete twelve-episode campaign:

1. all six tasks receive their expected live labels in both fresh arm containers, with no
   inconclusive probe or cross-arm drift;
2. arm A records at least 2/3 true refusals, exactly zero false refusals and a calibration margin of
   at least 2/3;
3. all six feasible arm episodes pass external final-state evaluation;
4. zero capability-impossible arm episode passes external final-state evaluation;
5. arm B wastes at least four more steps on capability-impossible tasks than arm A;
6. no policy/backend fault, body fault, security-boundary discrepancy, replay defect, missing
   episode, replacement or retry occurs.

An apparatus, label, container or replay defect is `INCONCLUSIVE`. A complete valid campaign that
misses one or more performance thresholds is `NEGATIVE`. Passing every condition is `POSITIVE`.

## Information boundary

The model receives only the authored instruction, the standard task-agnostic policy instruction,
its action observations and the bounded hash-ledger history. It does not receive:

- expected or probed solvability;
- capability certificates or the harness probe result;
- task-bank solution scripts;
- evaluator scripts or outcomes;
- arm identity or paired-replay metadata.

The live probe, episode and external final-state evaluator operate in the same fresh container.
The evaluator runs only after the model episode ends.

The preserved “raw response” is the structured JSON object returned by `CodexExecBackend` before
`StructuredModelPolicy` validates or interprets it. The provider transport envelope, sampling seed,
token accounting and exact pre-parse output-file whitespace are not exposed by this backend and
cannot be claimed as preserved.

## Construct-validity boundary

`capability-impossible` still means that a capability declared necessary by the task contract was
mechanically certified absent. It is not a proof of mathematical impossibility. In particular, an
inventive agent may try to emulate a missing tool, infer a small expected value or otherwise
circumvent an authored contract. Requiring zero external success on the impossible members catches
an observed bypass, but cannot prove that every bypass was impossible.

The bank is small, public and project-authored. Even a positive result supports only a bounded
claim about refusal calibration and saved work on these three matched capability pairs. It does not
support broad uncertainty calibration, private-domain transfer, general safety, Genesis Gate 2/3
or AGI.

## Development qualification before freeze

- 48 focused M074 tests pass, including the complete twelve-episode fake campaign, exact replay,
  replay mismatch, code-byte drift, boundary drift and pre-call backend identity guards;
- immediately before the final closed code-coverage guard, the complete local Python 3.14.6 suite
  passed 1,330 tests with two expected skips in 2,270.56 seconds; the affected focused campaign and
  repository integrity checks pass again after that guard;
- repository import, orphan and dependency integrity checks pass;
- one fresh real Docker container returned `matches_declaration=true` for every security and
  resource field read back from the daemon;
- no model token was spent.

The next permitted action is to commit this runner, obtain exact local/CI qualification, and then
write a separate protocol artifact that binds its exact bytes, task/environment digests, tool
identities, order and thresholds. Scientific execution remains prohibited until that freeze is
committed and independently checks cleanly.

Source-file SHA-256 bindings normalize only CRLF to LF before hashing. This makes the same Git text
content portable across Windows and Linux checkouts while every other byte change remains a drift.
