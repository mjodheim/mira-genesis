# M066 — governance-corrected development result

## Verdict

**Positive in four-bank development; not canonical.**

## Scientific boundary

M066 introduces no scientific change. The permanent M066 campaign executed all four precommitted
banks through the unchanged M065 engine. Every bank retained three accepted cycles, version twelve,
68/68 retained cases and 18/18 hidden observations in the complete lineage. Fresh-on-B,
unchanged-parent-migrated and learned-state-ablated each retained zero accepted cycles and 0/18.

Eleven dedicated M066 tests passed in **202.78 seconds**. They include all four scientific banks, exact
preservation of the M065 negative attempt, portable frozen identities, a lateral pull-request ref
counterexample and rejection of a repeated first-parent marker. Repository integrity also passes.
An earlier terminal invocation was stopped by its 120-second local command timeout without a test
verdict; it produced no canonical observation and changed no protocol input.

The final complete local repository suite passed **1,112 tests in 1,689.93 seconds**. No source
engaged by the frozen protocol changed after this run.

## Governance evidence

The Git graph falsifier creates a lateral branch containing the M066 marker path, returns to
`main`, and introduces the canonical marker there. `git rev-list --all` sees two occurrences while
`git rev-list --first-parent HEAD` sees exactly one. A second occurrence on first-parent history is
rejected. The workflow contains the latter command, contains no `git rev-list --all`, and permits
the first-result job only on `github.run_attempt == 1`.

## Remaining gates

1. pass the complete repository suite and qualify the exact frozen parent on Python 3.11/3.13;
2. merge a separate marker-only commit bound to that parent and the 23-file commitment;
3. preserve the unique Python 3.11 result and exact Python 3.13 byte reproduction;
4. publish the bounded verdict without widening the release boundary.
