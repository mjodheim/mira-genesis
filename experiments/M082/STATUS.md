# M082 status

**POSITIVE QUALIFIED DEVELOPMENT RESULT — TRACK A, MODEL-FREE, REAL BROWSER.**

- Target: the browser clause of G6, absent since the register was written.
- Environments: container shell, HTTP service and **real Chromium**, all offline containers, all
  driven by M081's unchanged four-action interface.
- `shared_interface`: **5/5** completable tasks in each of three environments.
- `crossed_drivers`: **0** completions everywhere — the browser store has no HTTP route.
- `self_report_scored`: the browser over-reports by 1. Scored by the page's confirmation the browser
  looks 6/6; scored by the rendered DOM it is 5/6.
- Bank commitment `04916c28…78a1`; first result `20fac369…65890`, attempt 1, no retry.
- Local regressions: 16 without Docker, 18 with `MIRA_RUN_DOCKER_TESTS=1`. Checker: `failures: []`,
  live re-derivation performed. Integrity: clean.
- Gate advance: **none.** G6 stays at partial mechanism evidence.

## Frozen ordering

1. `0c35847` froze `PROTOCOL.json`, `PROTOCOL.md` and the image `Dockerfile` before any harness code.
2. `958c52f` added the browser environment and recorded all three transport defects.
3. The bank was bound and the result preserved in one pass, attempt 1, no retry.

## The design decision that makes this worth anything

A page with an HTTP API would have made the browser the M081 service with extra steps. State lives in
`localStorage` instead — no network endpoint — and the driver reaches it only through DOM
interaction. The crossed arm completing nothing is what turns that from a claim into a measurement.

## Three transport defects, all recorded

MSYS path conversion mangling `docker exec` arguments on Windows, the same class as M070. A fresh
browser profile per action, which would have left the harness holding the state instead of the
browser while every test still passed. And a page flattened into an environment variable, where a
`//` comment silently commented out the rest of the script.

The second is the one worth remembering: nothing failed, the tests were green, and the claim would
have been hollow.

## What is deliberately absent

No desktop VM. No physical simulator or device. No external suite. The page is project-authored, so
this is DOM competence on one local page and not general web competence.

## A limit on the evidence

Container-backed regressions skip in CI under the existing opt-in, so CI attests the structural half
only. The live half is reproducible locally with Docker running and the image built from
`experiments/M082/browser-image`.

## What a successor would need

A desktop VM under the same interface, or pages maintained outside this project, and eventually
independent reproduction. Adding a fourth container flavour would repeat the instrument.
