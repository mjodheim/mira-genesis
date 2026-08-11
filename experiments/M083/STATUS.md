# M083 status

**POSITIVE QUALIFIED DEVELOPMENT RESULT — TRACK A, MODEL-FREE, REAL X11 SESSION.**

**NOT A VIRTUAL MACHINE. G6's DESKTOP-VM CLAUSE REMAINS UNMET.**

- Target: a fourth real environment under M081's unchanged interface, addressed only by screen
  coordinates and legible only as rendered pixels.
- `shared_interface`: **5/5** completable tasks; state read by decoding exact palette colours.
- `crossed_drivers`: **0/5** — the rendered grid has no filesystem, HTTP or DOM route.
- `self_report_scored`: over-reports by **1**. Scored by the application's acceptance the desktop
  looks 6/6; scored by decoded pixels it is 5/6.
- Client origin **discovered** at run time from the X server: `(40, 47)`.
- Bank commitment `cd549c72…4372a`; first result `5d5ccd63…70807`, attempt 1, no retry.
- Local regressions: 21 without Docker, 23 with `MIRA_RUN_DOCKER_TESTS=1`. Checker: `failures: []`,
  live re-derivation performed. Integrity: clean.
- Gate advance: **none.** G6 stays at partial mechanism evidence.

## Frozen ordering

1. `a1409bf` froze `PROTOCOL.json`, `PROTOCOL.md` and the image `Dockerfile` before any harness code.
2. `82e0bf9` added the desktop environment and runner.
3. The bank was bound and the result preserved in one pass, attempt 1, no retry.

## Why this is not the desktop VM

A container shares the host kernel. No hypervisor was available: `qemu`, `VirtualBox`, `multipass`
and `Vagrant` all absent, the Hyper-V feature state unqueryable without elevation, and the only VM
present the host's own WSL2 distribution — not an isolated environment created for this experiment.

Obtaining a real VM would require installing a hypervisor and downloading a guest image under nested
virtualisation. Calling this a VM would be the relabelling the M082 protocol prohibits one experiment
earlier, so the protocol, the result, the checker and a regression all assert the denial.

## The third green-but-wrong trap in this series

A hard-coded window origin would have painted and read different cells while every call returned
success. `openbox` places the window where it chooses. Alongside M080's tautological rollback check
and M082's harness-held browser state, that is three occasions where the tests would have been green
and the claim hollow. All three are recorded with their diagnosis.

## What is deliberately absent

No desktop VM. No physical simulator or device. No external suite. No keyboard — `xdotool` could not
focus a Tk entry, and a clicked palette exercises the substrate fully, so the keyboard was dropped by
design with the reason recorded rather than discovered later. The application is an authored Tk grid,
so this is coordinate-and-pixel competence on one window, not general desktop competence.

## What a successor would need

A genuine hypervisor and guest image for the VM clause, or applications maintained outside this
project, and eventually independent reproduction. A fifth container flavour would repeat the
instrument.
