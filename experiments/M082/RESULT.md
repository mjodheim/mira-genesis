# M082 — first result

**POSITIVE QUALIFIED DEVELOPMENT RESULT — TRACK A, MODEL-FREE, REAL BROWSER.**

Date: 2026-08-11. No external model, no external task, no third-party attestation.

## Outcome

| Arm | shell | service | browser | Environments covered | Browser over-report |
|---|---:|---:|---:|---:|---:|
| shared_interface | **5 / 5** | **5 / 5** | **5 / 5** | **3** | 1 |
| crossed_drivers | **0** | **0** | **0** | 0 | 6 |
| self_report_scored | 6 | 6 | 6 | 3 | 1 |

One unchanged agent, emitting the same four abstract actions, completed every completable task in a
container shell, an HTTP service and a **real Chromium browser** — the first of the three environment
kinds G6 names to be added since M071 supplied the terminal.

## Why the browser is not the M081 service in a costume

The page exposes **no HTTP route for its store**. State lives in `localStorage`, which is per-origin
browser state with no network endpoint, and the driver reaches it only by filling inputs, clicking
and reading rendered DOM nodes.

`crossed_drivers` proves it: browser tasks driven by the HTTP driver, and service tasks driven by the
browser driver, complete **nothing** in all three environments. An HTTP client fetching the page
receives markup and cannot touch the store at all. The browser therefore adds a rendering engine, a
JavaScript event loop and DOM state — a materially different substrate.

## One interface, imported rather than restated

M082 imports M081's `Agent`, `ShellEnvironment`, `ServiceEnvironment` and `Action` unchanged. A
three-environment claim only means something if one interface object drives all three; a regression
and the checker both parse this module and fail if any of those classes is redefined here.

## Self-report fails again, in a browser-specific way

The page displays `saved` for every submission, including names it validates and then declines to
persist. The agent reads that confirmation and claims success; the rendered list does not contain the
item. Scored by the page's own confirmation the browser looks 6/6; scored by the DOM it is 5/6.

This is the browser's version of M081's swallowed shell write and discarded `204`, and it is the same
G6 clause measured rather than restated.

## Three transport defects found while proving the mechanics

All three are recorded in `RESULT.json` because each would have produced a quietly wrong result.

1. **MSYS path conversion.** `docker exec … /agent/driver.mjs` under Git Bash on Windows becomes
   `C:/Program Files/Git/agent/driver.mjs`, failing with a confusing module error. Every container
   command is now wrapped in `sh -c`. This is the same defect class that produced the negative M070.
2. **A fresh browser profile per action** discarded `localStorage`, so the harness was replaying
   accumulated intent to reconstruct state. That would have meant *the harness* held the state rather
   than the browser, emptying the claim while every test still passed. A persistent profile now keeps
   state in the browser, verified by a read-only action returning items written by earlier launches.
3. **The page passed through an environment variable** had to be flattened to one line, which turned
   a `//` comment into a comment over the whole script and silently disabled the save handler. The
   page is now written to a file so newlines survive.

## Preserved evidence

- Protocol and image recipe frozen before the harness: commit `0c35847`; salt
  `e9427a3eda9a2ba96b6066671bdc2347ded3fcb5e14c13b873facb34bdab0b6e`.
- Browser environment: commit `958c52f`.
- Base image pinned at
  `mcr.microsoft.com/playwright@sha256:98b1ad488de36b22d41fdd1b0c5b9cceaa78a8d2661c6ab02d2108a07c182338`;
  the derived image is a local build whose Dockerfile digest is bound into the bank.
- Bank commitment `04916c2825c2b834e1a432b1ee995b6df3d76b3d8d54e4cc6338d83bb91878a1`.
- First result, attempt 1, no retry:
  `20fac3690d24134d23eaadca13f1d3ee49b055737fe082fa7db4e5da05b65890`.

`python scripts/check_m082_result.py` replays the bank, re-verifies that the interface is imported,
that the store has no HTTP route, that state is read from the DOM and that the profile is persistent,
then re-derives every arm against live containers. It reported `failures: []` with
`live_rederivation: performed`.

Local regressions: 16 without Docker, 18 with `MIRA_RUN_DOCKER_TESTS=1`. The container-backed tests
skip in CI under the repository's existing opt-in, so **CI attests the structural half only** and the
live half is local evidence, reproducible on demand.

## What this supports

One unchanged interface across three real isolated environments including a real browser, and
DOM-state scoring catching what a page's own confirmation misses.

## What this does not support

G6 remains **open**. There is **no desktop VM**, no physical simulator or device, and no external
suite. The page is authored by this project, so this is DOM competence on one local page, **not
general web competence**. Closure additionally requires uncontaminated private tasks frozen after the
agent design plus independent reproduction. No Genesis Gate 2 evidence and no AGI claim.
