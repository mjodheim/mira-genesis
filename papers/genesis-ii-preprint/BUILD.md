# Genesis II — build instructions

## Requirements

A normal TeX Live installation with `pdflatex`, `latexmk`, and BibTeX is sufficient. The manuscript intentionally avoids shell-escape and unusual conference-specific classes.

## Figures

Generate the four vector figures from the committed `figure_data.json` before compiling:

```bash
python generate_figures.py
```

This re-renders frozen summary values only; it does not run an experiment. The generated `figures/*.pdf` and preview PNG files are build outputs and are intentionally not committed.

## PDF

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error paper.tex
```

If `latexmk` cannot find `bibtex` on a system where the executable is named differently, run the equivalent sequence manually:

```bash
pdflatex paper.tex
bibtex paper
pdflatex paper.tex
pdflatex paper.tex
```

Clean intermediates with:

```bash
latexmk -C
```

The repository assembly has been checked with the committed manuscript chunks at TeX-safe boundaries; the DOI-bearing build is 22 pages.

## arXiv source archive

Because `paper.tex` includes the files under `manuscript/`, the source upload must include that directory as well as the generated vector figures:

```text
paper.tex
references.bib
manuscript/*.tex
figures/fig1_chain.pdf
figures/fig2_capacity_competence.pdf
figures/fig3_expressibility.pdf
figures/fig4_blind_closure.pdf
```

Create the archive from the package directory with:

```bash
zip -r genesis-ii-arxiv-source.zip \
  paper.tex references.bib manuscript \
  figures/fig1_chain.pdf \
  figures/fig2_capacity_competence.pdf \
  figures/fig3_expressibility.pdf \
  figures/fig4_blind_closure.pdf
```

For a submission archive, include only the manuscript chunks actually referenced by `paper.tex`; unused historical split fragments, if present in a working tree, are not required.

## Zenodo

Genesis II is published at DOI `10.5281/zenodo.22118735`. For any future record update, keep the deposited PDF/source package synchronized with the repository publication snapshot and preserve the scientific M107–M112 artifacts unchanged.
