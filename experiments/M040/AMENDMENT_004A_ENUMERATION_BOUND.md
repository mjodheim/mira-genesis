# M040 amendment 004A — lineage-anchor enumeration bound

**Status: committed before implementation and before seed 400046 is evaluated.**

The lineage-anchor task generator introduced by amendment 004 has the following deterministic
bound:

- derive every unique contiguous one- or two-tool fragment containing a lineage-owned tool;
- derive every one- or two-tool suffix over the protocol-supplied primitive registry;
- retain only combined programs of total symbolic length at most 4;
- order anchors and suffixes using the post-migration task seed;
- inspect at most `2,048` combined programs.

If no admissible task is found within this complete bounded enumeration, task generation is a
negative result. The generator may not increase its bound, add another suffix, change depth or
fall back to a target-aware search on the same seed.

The equal per-arm symbolic search budget remains `4,096` nodes. Task-generation enumeration
is reported separately and is not charged to any arm, because it defines the hidden task
before the arms run. Its counters and selected program digest must be committed to the result
and reproduced by seed-only replay.
