# Genesis M107 bridge — DEVELOPMENT integration record

**Prepared:** 9 September 2026  
**Status:** DEVELOPMENT apparatus; no scientific observation; no gate movement.

## Purpose

The integrated Genesis runtime had been exercised end to end only with `genesis.development_bodies`
fixtures. M107 already contains a qualified interpreter-extension mechanism whose operator semantics
live in lineage state and whose initial reach is structurally incomplete. This increment connects
those two lines without modifying the frozen M107 source.

The bridge is intentionally narrow. It asks one engineering question:

> Can Genesis admit, isolate, grade, adopt, ablate and restore the state produced by the unchanged
> M107 acquisition mechanism, using the ordinary Genesis trust root rather than a fixture-specific
> body?

A positive DEVELOPMENT test answers only that composition question.

## Boundaries

- `metamorphosis/m107_runtime.py` is imported and not edited.
- `experiments/M107/DEMANDS.json` is replayed as the already-committed project-controlled demand
  record. It is not independent task evidence and is not a new M107 observation.
- The bridge never treats the current Genesis evaluation answer key as acquisition evidence.
- The body receives `target` and `signals`; `expected` remains parent-side and is withheld by the
  existing sandbox.
- The acquired M107 state is packaged in a reconstructible `ConfiguredBody`.
- `m107_operator_extension` is the one declared dependency. Removing that dependency leaves the
  configuration byte-for-byte structurally unchanged and makes the adapter execute M107 S0.
- No network, carrier bank, M125 authority, canonical salt, reveal, scientific scoring or generality
  gate is touched.

## Required DEVELOPMENT checks

1. The frozen M107 joint demand still reproduces the qualified `4 -> 16` complete-image expansion.
2. M107 S0 retains its original reachable work.
3. Under Genesis parent-side grading, the acquired state strictly improves over S0 without forgetting
   S0 work.
4. Genesis' runtime-derived dependency ablation removes the new reach and reproduces S0 outcomes.
5. The accepted configured artifact survives Genesis checkpoint/process-death restoration with the
   same executable artifact identity.

## What this does not establish

This bridge does **not** make Genesis rediscover M107 autonomously. The adapter replays an already
qualified acquisition over an already committed, project-controlled demand. It therefore does not
close the remaining authored-probe ceiling and does not turn the integrated runtime demonstration
into scientific evidence.

If the bridge remains green, the next engineering step is to adapt M108/M109's lineage-held
attribution machinery so a second Genesis generation can depend causally on this M107 extension and
the runtime can measure that dependency with its ordinary derived-ablation path.
