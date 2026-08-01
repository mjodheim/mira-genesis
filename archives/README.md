# Archives

## What lives here

- [`RETIRED_CODE.md`](RETIRED_CODE.md) — index of code removals, each citing the commit
  where the file remains readable;
- [`workflows/`](workflows/) — readable copies of sealed evaluation workflows whose
  canonical run has been consumed, kept for the exact recipe, removed from
  `.github/workflows/` so they are no longer executable.

## Archive tags

The code of a halted or superseded experiment is not kept on a branch. A live branch
invites resumption and gets deleted by accident; an annotated tag is an immutable
reference, which is what a scientific record requires.

| Tag | Experiment |
|---|---|
| `archive/m014c-halted` | M014c — `HALTED — SUPERSEDED BY M017` |

Records cite the **tag name**, not the commit hash it currently resolves to. A tag
survives history rewriting; a raw hash does not, and a citation that breaks silently is
worse than no citation.

```bash
git show archive/m014c-halted:metamorphosis/m014c_meta.py
```

```bash
git switch --detach archive/m014c-halted
```

## What does not live here: M001 to M011

**No M001–M011 archive exists in this repository.** Git history starts on 31 July 2026
with the creation of the canonical repository.

Hypotheses H1, H2 and H3 in [`SCIENTIFIC_HYPOTHESES.md`](../SCIENTIFIC_HYPOTHESES.md)
are marked "validated within their finite domain" on the strength of M001–M011. Those
validations are therefore **asserted but not verifiable here**: no frozen protocol, no
code, no raw result, no sealed run.

D001 states that the repository is the project's official memory. Until those archives
are versioned, any claim resting on M001–M011 must be read as an inherited working
hypothesis, not as a reproducible result.

The first fully verifiable experiment in this repository is **M012b**.
