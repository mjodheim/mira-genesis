# Genesis II — publication status and remaining actions

This file is a publication handoff checklist, not part of the frozen scientific record.

## Completed

- Genesis II long-form manuscript prepared from M107–M112 only.
- Zenodo record published: `https://zenodo.org/records/22118735`.
- DOI assigned: `10.5281/zenodo.22118735`.
- Manuscript/research prose licensed `CC-BY-4.0`; project-controlled software remains `AGPL-3.0-only`.
- Root `CITATION.cff` should prefer Genesis II while keeping Genesis I discoverable in the paper/package metadata.

## Repository publication snapshot

The scientific scope anchor remains the M112 merge (PR #211; short SHA `8176c53`). The publication-package merge SHA is recorded in `SUBMISSION_METADATA.md` after the GitHub merge; it is intentionally later than the scientific evidence. No frozen M107–M112 artifact is modified by publication prose.

Recommended human-readable publication tag:

```text
publication/genesis-ii-preprint-v1
```

Do not reuse an experiment tag for publication prose.

## arXiv

Upload the tested source archive described in `BUILD.md`.

Recommended categories:

- primary `cs.AI`;
- cross-list `cs.SE`;
- optional `cs.LG` if appropriate at submission time.

Use the short abstract in `SUBMISSION_METADATA.md` and certify authorship personally. Any endorsement or identity step remains an author action.

## GitHub release

Optional but useful: create a release for `publication/genesis-ii-preprint-v1` and attach the DOI-bearing publication PDF/source archive. Link `https://doi.org/10.5281/zenodo.22118735` in the release notes.

## Scope boundary

Do not fold M113 back into Genesis II. M113 begins a new question—blind carrier interaction-language generation—and has no canonical result in the Genesis II snapshot. It belongs to the Genesis III line unless a future publication decision explicitly changes scope.
