# M081 status

**POSITIVE QUALIFIED DEVELOPMENT RESULT — TRACK A, MODEL-FREE, REAL CONTAINERS.**

- Target: two G6 clauses — one interface across real isolated environments, and completion scored
  from environment state rather than self-report.
- Environments: a POSIX shell in a network-disabled Alpine container, and a real Python HTTP server
  process in its own container on a loopback port. Both digest-pinned.
- `shared_interface`: **5/5** completable tasks in each environment, both covered.
- `crossed_drivers`: **0** completions — the environments are genuinely distinct systems.
- `self_report_scored`: over-reports by **2**, one per environment.
- Scored by claim the interface looks 12/12; scored by state it is 10/12, and the gap is exactly the
  two constructed lies.
- Bank commitment `5261974e…9ccbd`; first result `cc9a6e89…41bdc`, attempt 1, no retry.
- Local regressions: 17 without Docker, 20 with `MIRA_RUN_DOCKER_TESTS=1`. Checker: `failures: []`,
  live re-derivation performed. Integrity: clean.
- Gate advance: **none.** G6 stays at partial mechanism evidence.

## Frozen ordering

1. `7ac5ad4` froze `PROTOCOL.json` and `PROTOCOL.md` before any harness code existed.
2. `54b90c5` added the harness and recorded amendment A1 plus both construction fixes.
3. The bank was bound and the result preserved in one pass, attempt 1, no retry.

## What is deliberately absent

No browser. No desktop VM. No physical simulator or device. No external suite. G6 names a terminal,
browser and desktop VM; this delivers two real environments of which neither is a browser or a VM,
so the larger part of the gate is untouched and the register must keep saying so.

## A limit on the evidence itself

The container-backed tests skip in CI under the repository's existing `MIRA_RUN_DOCKER_TESTS` opt-in.
CI therefore attests the structural half only. The live half is reproducible on demand with Docker
running, and a reader should treat it as local evidence rather than CI-attested.

## What a successor would need

A real browser or desktop VM under the same interface, which needs automation tooling this
repository does not carry, and eventually tasks maintained outside the project with independent
reproduction. Adding a third container flavour would repeat this instrument rather than extend it.
