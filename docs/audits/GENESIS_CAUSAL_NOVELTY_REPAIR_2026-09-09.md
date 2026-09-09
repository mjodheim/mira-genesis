# Genesis causal novelty repair — DEVELOPMENT apparatus

**Prepared:** 9 September 2026  
**Status:** runtime metrology repair; no scientific observation; no gate movement.

## Defect

The runtime called a later acquisition causally dependent on an earlier one whenever removing the
earlier acquisition reduced the **total** number of solved tasks. Because retention is required, that
criterion could be satisfied merely by breaking work the parent already solved while leaving every
task newly solved by the current generation intact.

That is retention dependence, not evidence that the new improvement needed the earlier acquisition.

## Repair

For every accepted candidate the causal comparison now receives the parent outcomes as a third arm.
It identifies `candidate_solved - parent_solved` and establishes dependency only when the runtime-
derived, equal-budget ablation loses at least one member of that newly solved set. Losses confined to
retained parent work are recorded separately and do not establish a causal link. All three arms must
carry exactly the same task identifiers or the measurement fails closed.

## Fixture finding

The stronger criterion exposed two false-positive DEVELOPMENT fixtures. Their new tasks were routed
only through the current acquisition; removing the claimed predecessor broke older retained tasks but
left the newly gained task intact. The fixture chain now requires each newly introduced routed task to
use both the immediately preceding acquisition and the acquisition introduced in its own generation.
This makes the synthetic positive control test the property it claims rather than merely total loss.

A separate counterexample keeps the old false-positive shape permanently: candidate total solved falls
from 3 to 1 after ablation while its only newly solved task remains solved. The repaired criterion must
report no causal dependency and record the two losses as retained work.

## M108 revalidation

The real M108 bridge is re-run under the stronger rule. Its causal link is accepted only if the M108
tasks newly solved over the M107 parent are themselves lost when M107 is removed.

## Boundary

No M107–M125 frozen source, protocol, result, sealed bank, reveal state or scientific decision is
modified. This changes only the integrated Genesis DEVELOPMENT measurement and its synthetic fixtures.
