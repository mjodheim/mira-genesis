# M083 — first result

**POSITIVE QUALIFIED DEVELOPMENT RESULT — TRACK A, MODEL-FREE, REAL X11 SESSION.**

**This is not a virtual machine, and G6's desktop-VM clause remains unmet.**

Date: 2026-08-11. No external model, no external task, no third-party attestation.

## Outcome

| Arm | Completed | State reached | Claimed | Over-report |
|---|---:|---:|---:|---:|
| shared_interface | **5 / 5** | 5 | 6 | 1 |
| crossed_drivers | **0 / 5** | 0 | 6 | 6 |
| self_report_scored | 6 / 5 | 5 | 6 | **1** |

The unchanged M081 interface completed every completable task in a real X11 desktop session where the
only way to act is a mouse click at a screen coordinate and the only way to observe is decoding exact
palette colours from a screenshot.

## Why this is a fourth substrate and not a fourth label

The shell is addressed by filesystem paths, the service by HTTP routes, the browser by DOM selectors.
This environment is addressed **only by screen coordinates** and its state is legible **only as
rendered pixels**.

`crossed_drivers` drives the desktop tasks through the browser driver and completes **nothing**. The
rendered grid has no filesystem, HTTP or DOM route, so there is no path to it except the screen.

## Why the window origin is discovered, not assumed

The probe work made this concrete before the protocol was frozen. `openbox` places the window where
it chooses — here at client origin `(40, 47)` — and early attempts that assumed an origin addressed
the wrong cells **while every call still returned success**. The origin is now read from the X server
via `xwininfo` at start-up, and both a regression and the checker fail if that discovery is removed.

This is the third time in this series that a green result would have been wrong: M080's rollback check
compared a checkpoint against its own digest, M082's browser profile left the harness holding the
state, and here a hard-coded origin would have painted and read different cells.

## Self-report fails again, in the fourth substrate

One cell is locked. The application accepts the click and reports nothing wrong; the cell never
changes colour. Scored by the agent's claim the desktop looks 6/6; scored by decoded pixels it is
5/6, and the gap is exactly that cell.

## No keyboard, deliberately

`xdotool` could not give a Tk entry keyboard focus in this session, and rather than fight X focus the
design drops the keyboard entirely: a palette clicked with the mouse exercises coordinate-and-pixel
interaction fully. This is recorded in the protocol as a design choice with its reason, not as an
omission discovered later.

## Preserved evidence

- Protocol and image recipe frozen before the harness: commit `a1409bf`; salt
  `68b3f29ba5d72b26666dca7f252e4aa80b5fb425aa35a5d3d5ef5be5f07701c3`.
- Desktop environment and runner: commit `82e0bf9`.
- Bank commitment `cd549c72fb94d6a7e9aa1605d3af857dca954bb580135a24fecc63f92304372a`.
- First result, attempt 1, no retry:
  `5d5ccd631cf46bdc6b646f82db27d5418c2f79b3d6a142a5f17af93102970807`.

`python scripts/check_m083_result.py` replays the bank, re-verifies that the protocol still denies
being a VM, that the interface is imported, that the origin is discovered and that state comes from a
screenshot, then re-derives every arm against a live session. It reported `failures: []` with
`live_rederivation: performed`.

Local regressions: 21 without Docker, 23 with `MIRA_RUN_DOCKER_TESTS=1`. The container-backed tests
skip in CI, so **CI attests the structural half only**.

## What this supports

One unchanged interface across **four** real isolated environments, one of which is legible only
through rendered pixels, and a fourth independent demonstration that environment-state scoring catches
what an application's own acceptance misses.

## What this does not support

**There is no desktop VM here.** A container shares the host kernel. No hypervisor was available in
this environment — `qemu`, `VirtualBox`, `multipass` and `Vagrant` all absent, the Hyper-V feature
state unqueryable without elevation, and the only VM present being the host's own WSL2 distribution,
which is not an isolated environment created for this experiment. G6's desktop-VM clause is **unmet**
and the register must continue to say so.

The application is an authored Tk grid, so this is coordinate-and-pixel competence on one local
window, **not general desktop application competence**. No physical simulator or device, no external
suite. Closure additionally requires uncontaminated private tasks frozen after the agent design plus
independent reproduction. No Genesis Gate 2 evidence and no AGI claim.
