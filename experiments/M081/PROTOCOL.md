# M081 one interface across two real isolated environments

**FROZEN BEFORE IMPLEMENTING OR MATERIALIZING THE HARNESS AND TASK BANK.**

## What G6 asks, and what this covers

G6 requires the **same agent interface** to operate in isolated but real software environments —
initially a terminal, browser and desktop VM — with task completion measured from environment state
and never from the agent's self-report.

M071 supplied one terminal task in an official container. The register records that "browser/desktop
competence and broad environment coverage remain absent".

M081 addresses two of G6's clauses and no others: **one interface across two materially different
real environments**, and **scoring from environment state rather than self-report**. It delivers no
browser and no desktop VM. Those clauses stay untouched and the register must continue to say so.

## The two environments are real, not modelled

The shell environment is a POSIX shell inside an Alpine container over a real filesystem. The service
environment is a real Python HTTP server process inside a separate container, answering over a real
socket on a published loopback port. Both containers are created from **digest-pinned local images**.

Neither environment is simulated inside the harness. The harness has no model of their state and can
learn it only by executing a fresh read against them. If Docker is unavailable or a digest does not
match, the experiment is **inconclusive** — not runnable — rather than negative.

## One interface, no branching

The agent emits four abstract actions — `put`, `read`, `remove`, `list` — with the same vocabulary in
both environments. It may not branch on which environment it is in. Translation into shell commands
or HTTP requests belongs to the environment driver, not the agent.

The `crossed_drivers` arm swaps the drivers between environments. It must complete nothing. That is
what demonstrates the two environments are genuinely distinct systems rather than two names for one
mock — without it, "the same interface worked in both" could be true of a single environment wearing
two labels.

## Self-report must be shown to fail

One task per environment writes to a path the container makes read-only, in a form where the action
**returns success while the environment does not change**. A harness that trusted return values would
score that task as passed.

The `self_report_scored` arm exists to make that divergence visible. It must over-report by at least
one task. G6 forbids scoring from self-report; this measures why, instead of asserting it.

## Scoring

Completion is read through an **independent path**: a fresh `docker exec` for the shell environment
and a fresh `GET` for the service environment, issued after the action sequence finishes. The
agent's own claim is recorded and never scored.

## Safety boundary

The shell container runs with networking disabled. The service container publishes a loopback port
only. Neither mounts the host repository, the Docker socket, credentials or a deployment path. No arm
may reach a network beyond that loopback port, a repository write path, a credential, a permission
interface or a physical actuator.

## Claim boundary

A positive result establishes that one unchanged interface drives two real isolated environments and
that environment-state scoring catches what self-report misses. It does **not** close G6: browser,
desktop VM, physical device and external-suite competence are all absent, the tasks are
project-authored, and closure additionally requires uncontaminated private tasks frozen after the
agent design plus independent reproduction. No Genesis Gate 2 evidence and no AGI claim.
