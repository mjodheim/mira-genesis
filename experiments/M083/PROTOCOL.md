# M083 a GUI desktop session as a fourth environment

**FROZEN BEFORE IMPLEMENTING OR MATERIALIZING THE DESKTOP HARNESS AND TASK BANK.**

## This is not a virtual machine, and the register must keep saying so

G6 names a terminal, a browser and a **desktop VM**. M071 supplied the terminal, M082 supplied the
browser. This experiment does **not** supply the desktop VM.

A Docker container shares the host kernel; it is not a virtual machine. No hypervisor is available
here: `qemu`, `VirtualBox`, `multipass` and `Vagrant` are all absent, the Hyper-V feature state
cannot be queried without elevation, and the only VM present is the host's own WSL2 distribution,
which is not an isolated environment created for this experiment. Obtaining a real VM would require
installing a hypervisor and downloading a guest image, under nested virtualisation that would most
likely fall back to software emulation.

Calling this a desktop VM would be exactly the relabelling that the M082 protocol prohibits, one
experiment after writing that prohibition. It is a **GUI desktop session**, and the VM clause of G6
remains unmet.

## What it does add

A fourth substrate, addressed differently from the other three. The shell is addressed by filesystem
paths, the service by HTTP routes, the browser by DOM selectors. This environment is addressed
**only by screen coordinates**, and its state is legible **only as rendered pixels**.

A real X server, a real window manager and a real GUI application run in an offline container. The
agent acts by clicking at a coordinate; the harness observes by taking a screenshot and decoding
exact palette colours. Nothing in the harness models the window layout: the client-area origin is
discovered at run time from the X server, because a window manager places the window where it
chooses and a hard-coded origin would silently address the wrong cells.

## One interface, imported not restated

M083 imports M081's agent and the environments from M081 and M082 unchanged. A four-environment
claim only means something if one interface object drives all four.

The action vocabulary is unchanged. Only what the names denote is environment-appropriate — a cell
label rather than a path or a route — exactly as a filesystem path and an HTTP route already denote
different things. The agent does not know the difference.

## No keyboard, and why

The substrate's distinguishing property is coordinate-and-pixel interaction. A palette clicked with
the mouse exercises it fully. Driving a keyboard through X focus adds an environment dependency
without adding conceptual content, and it is omitted deliberately rather than by oversight.

## Self-report must fail again

One cell is locked. Clicking it is accepted by the application, which reports the action as taken,
and the cell does not change colour. Scored by the agent's claim the desktop looks complete; scored
by the decoded pixels it is not. This is the fourth substrate in which the same G6 clause is
measured rather than restated.

## Isolation

The desktop container runs with networking disabled and mounts no host repository, Docker socket or
credentials. The derived image is built locally from a pinned base and its Dockerfile is committed
with this protocol.

If Docker is unavailable, the image is absent, or the X server or window manager fails to start, the
experiment is **inconclusive** — not runnable — rather than negative.

## Claim boundary

A positive result establishes one unchanged interface across four real isolated environments, one of
which is legible only through rendered pixels.

It does **not** close G6. There is **no desktop VM**, no physical simulator or device, and no
external suite. The application is an authored Tk grid, so this is coordinate-and-pixel competence on
one local window, not general desktop application competence. Closure additionally requires
uncontaminated private tasks frozen after the agent design plus independent reproduction. No Genesis
Gate 2 evidence and no AGI claim.
