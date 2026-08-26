# Mira Genesis II preprint package

**Mira Genesis II: When an Acquired Improvement Makes Things Worse — Bounded Machinery Self-Modification and the Limits of Its Transfer**

Status: **published on Zenodo as DOI `10.5281/zenodo.22118735`; arXiv submission pending.**

This directory is the Genesis II manuscript package for the frozen M107–M112 scientific record. It is strictly downstream of the experiments: no protocol, frozen apparatus member, result, checker, threshold, population, sealed bank, or decision record is changed by the manuscript.

Genesis I — *Mira Genesis: A Reproducible Case Study of Causal Cumulative Capability Acquisition in a Persistent Software Lineage* — is archived at DOI `10.5281/zenodo.22067855` and covers M094–M100. Genesis II starts at the next research question and ends at M112. M113 is deliberately excluded because it has no canonical result.

## Publication

- Genesis II DOI: [`10.5281/zenodo.22118735`](https://doi.org/10.5281/zenodo.22118735)
- Zenodo record: `https://zenodo.org/records/22118735`
- Manuscript/research-prose license: `CC-BY-4.0`
- Related software repository: `https://github.com/mjodheim/mira-genesis` (`AGPL-3.0-only`)

## Paper scope

M107–M112 form one bounded causal sequence:

- **M107 / D076:** endogenous lower-interpreter extension, complete image 4 → 16;
- **M108 / D077:** first state-held modification of the acquisition machinery;
- **M109 / D078:** two successive machinery generations, with lineage-determined blame labels;
- **M110 / D079:** census-conditional cross-carrier transfer and measured harm outside the producer census;
- **M111 / D080:** self-directed diagnosis under a scarce probe budget, with a third bounded machinery generation;
- **M112 / D081:** one blind sealed generated world bank; diagnosis 24/24, transfer 22/24 mixed/negative under the inherited rule, with the central harm reproducing.

The paper's central result is M110's capacity–competence dissociation: `ReachImprove` grows strictly across the lineage while an acquired machinery improvement becomes strictly worse than its fresh predecessor on row 5. M111 shows a bounded diagnostic recovery. M112 removes direct project selection/authorship of the worlds and reproduces both the harm and the diagnosis while preserving a real blind-world fixed-point discrepancy.

## Files

- `paper.tex` — complete long-form reviewed LaTeX manuscript source (22 pages in the current compiled build).
- `references.bib` — bibliography, including Genesis I, self-improving-agent work, meta-learning, negative transfer, active learning, and selective prediction.
- `generate_figures.py` + `figure_data.json` — deterministic regeneration of the four manuscript figures from frozen summary values; generated PDF/PNG figures are build outputs and are not committed.
- `FIGURES.md` — figure/table provenance and interpretation boundaries.
- `REPRODUCIBILITY.md` — replay instructions, the M112 one-shot distinction, hashes, and failure expectations.
- `SUBMISSION_METADATA.md` — final title, abstract, categories, keywords, Zenodo/arXiv metadata, and author-only actions.
- `BUILD.md` — local PDF and source-archive build instructions.
- `POST_PUBLICATION.md` — DOI, `CITATION.cff`, release, Zenodo, and arXiv actions after the repository push.
- `REVIEW_REPORT.md` — manuscript self-review record: scientific consistency, adversarial-review concerns, literature verification, and technical PDF checks. It is AI-assisted self-review, not independent peer review.

Compiled PDFs and submission ZIPs are build outputs and do not need to be committed to the repository. The author handoff can carry them separately.

## Scientific anchor

Recommended scope anchor: the `main` merge commit that introduced the preserved M112 result (PR #211; short SHA `8176c53`). The publication-package commit will necessarily be later and should be recorded after the author pushes/merges this package.

Required result tags:

```text
experiment/m107-positive-result
experiment/m108-positive-result
experiment/m109-positive-result
experiment/m110-positive-result
experiment/m111-positive-result
experiment/m112-canonical-first-result
experiment/m112-mixed-result
```

## Claim boundary

Do not describe this paper as evidence of AGI, general intelligence, open-ended or unbounded recursive self-improvement, intelligence explosion, training-data independence, independent reproduction, external human evaluation, or closure of any G1–G10 generality gate. M112 removes direct project selection/authorship of world contents; the carrier, evaluator, registry, feature vocabulary, probe primitive, and custody remain project-controlled.
