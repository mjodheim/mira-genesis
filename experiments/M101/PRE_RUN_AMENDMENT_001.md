# M101 pre-run amendment 001 — Git-object freeze verification

**Date:** 2026-08-23  
**Timing:** after the first protocol tag; before any armed M101 run, qualification evidence or result  
**Disposition:** accepted implementation-only correction; the first tag remains preserved

## Trigger

The first post-tag verification correctly refused the frozen apparatus on Windows. The candidate
commit and working tree contained the same tracked qualification-pool content, and `git hash-object`
resolved both to blob `1889a741076c3d928cb1f4f8484a5c9c3351a469`, but the runner compared raw streams: Git emitted LF
from the committed blob while the checked-out file contained CRLF. It therefore reported that the
pool had moved even though its Git object identity and frozen canonical JSON digest were unchanged.

The same audit also showed that resolving an annotated tag without peeling it returns the tag object
rather than its target commit. The canonical-source equality check must compare against the peeled
commit.

## Correction

The freeze verifier now:

1. resolves the named tag with `^{commit}`;
2. compares every bound candidate artifact by committed blob object ID versus `git hash-object` of
   the working-tree path, which applies the repository's normal text conversion rules;
3. compares the final protocol to the tagged protocol by the same Git-object rule; and
4. still requires the tag target to be the direct child of the bound candidate commit and requires
   an armed canonical run to start exactly at that peeled tag commit with a clean tree.

## Scientific invariants

This amendment changes no research question, claim, condition, falsifier, threshold, world, case,
expected value, atomic catalog, acquisition language, search bound, candidate budget, capsule,
checker semantics, stable projection or verdict rule. It does not observe or execute any M101 pool
case through the scientific mechanism.

`experiments/M101/RESULT.json` did not exist, the armed runner was never invoked, and D070 remained
unfilled. The first tag `experiment/m101-frozen-protocol` remains an immutable record of the refused
pre-run freeze. The corrected freeze uses `experiment/m101-frozen-protocol-v2` and supersedes it for
the sole purpose of canonical run authorization.
