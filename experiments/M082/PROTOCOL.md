# M082 a real browser under the M081 interface

**FROZEN BEFORE IMPLEMENTING OR MATERIALIZING THE BROWSER HARNESS AND TASK BANK.**

## What this adds

G6 names a terminal, a browser and a desktop VM. M071 supplied the terminal; M081 added a second
real environment — an HTTP service — under one unchanged interface, and its register row still reads
"browser, desktop VM, physical device and external-suite competence all remain absent".

M082 removes the first of those. A real Chromium browser, running offline in a container, is driven
through the **same four abstract actions** M081 already uses. The desktop VM, physical device and
external suites stay absent, and the register must keep saying so.

## Why this is not the M081 service wearing a browser costume

That is the failure mode worth naming, because it would be easy to build and worthless.

The page exposes **no HTTP API for its store**. State lives in `localStorage`, which is per-origin
browser state with no network endpoint. The driver reaches it only by filling inputs, clicking a
button and reading rendered DOM nodes. An HTTP client that fetches the page receives markup and
cannot read or write the store at all.

The `crossed_drivers` arm proves this rather than asserting it: browser tasks driven by the service
driver, and service tasks driven by the browser driver, must complete nothing. The browser therefore
adds a rendering engine, a JavaScript event loop and DOM state — a materially different substrate,
not a second label.

## One interface means importing it, not restating it

M082 **imports M081's agent and its shell and service environments unchanged**. A three-environment
claim is only meaningful if the same interface object drives all three; re-implementing the interface
here would let it quietly diverge and would prove nothing about continuity.

## Self-report must fail again, in a browser-specific way

The page displays a save confirmation for every submission, including names it validates and then
declines to persist. The agent reads that confirmation and claims success; the rendered list does not
contain the item. A harness trusting the confirmation would score the task as passed.

This is the browser's version of M081's swallowed shell write and discarded `204`, and it is the same
clause of G6 being measured rather than restated.

## A Windows transport defect worth recording

`docker exec` arguments beginning with a slash are rewritten by MSYS path conversion on Windows:
`/agent/driver.mjs` silently becomes a host path and the command fails with a confusing module error.
Every container command must be wrapped in `sh -c`. This is the same class of Windows transport
defect that produced the negative M070 result, and it is recorded here so the next experiment does
not rediscover it.

## Isolation

The browser container runs with networking disabled. The page is served from the container's own
loopback interface, which works without external networking. The derived image is built locally from
a registry-digest-pinned Playwright base, and the Dockerfile is committed alongside this protocol.
The container mounts no host repository, no Docker socket and no credentials.

If Docker is unavailable, the derived image is absent, or Chromium cannot launch, the experiment is
**inconclusive** — not runnable — rather than negative.

## Claim boundary

A positive result establishes that one unchanged interface drives three real environments including
a real browser, and that DOM-state scoring catches what a page's own confirmation misses.

It does **not** close G6. There is no desktop VM, no physical simulator or device, and no external
suite. The page is authored by this project, so this is not general web competence: it is DOM
competence on one local page. Closure additionally requires uncontaminated private tasks frozen after
the agent design plus independent reproduction. No Genesis Gate 2 evidence and no AGI claim.
