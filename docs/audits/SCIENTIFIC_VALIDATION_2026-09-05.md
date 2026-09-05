# Independent scientific-validation audit — 2026-09-05

## Scope and authority

This branch is an audit workspace only. It starts from `main` commit
`234bff0a88a30f75fb9c6f470fff4e60fc4e3e9b` and does not alter any frozen protocol,
canonical result, reveal artifact, hypothesis verdict, threshold, publication disposition or
scientific bank.

The owner has authorised reversible/reproducible scientific validation work. Explicitly one-shot
or irreversible scientific acts remain owner-gated. External-maintainer requirements remain
external requirements and are not silently weakened.

## Evidence classes

Every action in this audit is classified before execution:

1. `reproduction` — replay/recompute an already-recorded result from preserved artifacts. It may
   test reproducibility but cannot become a new independent scientific result.
2. `prospective_development` — build/audit an instrument before a scientific draw. It is not
   evidence for or against the hypothesis.
3. `prospective_scientific` — a new pre-registered observation capable of changing a hypothesis
   status. This class may not execute past an explicit one-shot/irreversible owner gate.
4. `external_blocked` — the registered claim requires evidence or maintenance outside the project;
   an internal substitute must not be relabelled as satisfying it.

## Baseline reproduction state

The first audit action was to inspect the current `main` CI after M123 merge. GitHub Actions run
`33937619319` completed successfully. The complete suite passed on both Python 3.11 and 3.13; the
Python 3.13 job recorded `4254 passed, 11 skipped`. Repository-integrity and sealed-bank-boundary
jobs also passed.

The permanent CI is itself explicit that it never produces a canonical scientific result. Its
scientific value here is therefore reproducibility/integrity only.

The sealed-bank-boundary job currently recomputes or replays preserved M087, M088, M089, M090,
M091 and M094 results, while preserving M092 as aborted/pre-result rather than manufacturing a
retrospective verdict. Those checks all passed in the baseline run.

## Initial hypothesis triage

This audit will not treat all H labels as equivalent work items.

### Already recorded; suitable for reproduction / hostile re-analysis

Examples include H3/H4 and the later hypotheses whose frozen or qualified artifacts remain in the
repository. A successful replay preserves the recorded scope; it does not strengthen a development
result into a canonical or external result.

### Open and internally testable in principle

These require a prospective successor rather than replaying an exposed bank. The current M119–M124
line is in this class: the scientific proposition remains untested while the readiness apparatus is
being repaired prospectively.

### Open but externally blocked by their own claim

H31 is an explicit example: its held-out domain and independent reproduction require maintainers
outside this project. H21 similarly requires a private human-maintained bank and separate-maintainer
reproduction before support is allowed. Internal/generated substitutes may be useful instrument
work but cannot close those hypotheses.

### Closed negative / unsupported directions

These are reproduced to test that the falsifier still reproduces; they are not repeatedly sampled
until positive. H7, H16, H20, H23 and the qualified M086 meta-plasticity attempts are examples of
this discipline.

## Execution order

1. Build a machine-readable H→evidence→checker→status map without editing `SCIENTIFIC_HYPOTHESES.md`.
2. Re-run all read-only deterministic result checkers and isolation audits that can be executed from
   preserved public artifacts.
3. Record failures as audit findings before attempting any repair; do not repair historical frozen
   artifacts.
4. For open hypotheses, rank successors by information gain and cost, with special priority to the
   current carrier-blind line and to untested claims whose prerequisites are already satisfied.
5. Stop at any explicit owner-only freeze/generation/reveal gate and present the exact proposed act,
   frozen plan digest and irreversible budget before execution.
6. Record external blockers verbatim rather than substituting weaker internal evidence.

## Current first-wave findings

- `main` is reproducible at the repository/CI level after M123: green on both supported Python
  versions and all permanent integrity jobs.
- The current permanent CI already gives continuous reproduction coverage to M087–M091 and M094,
  and preservation checks to the aborted M092 line.
- The current M119–M123 sequence has not produced a scientific verdict on H64/H65/H67/H68; the
  correct audit target is the successor instrument, not retrospective reclassification.
- Some historical GitHub Actions run IDs cited by older hypothesis records are no longer directly
  retrievable through the current GitHub API history. Preserved repository artifacts/checkers are
  therefore the durable reproduction source; missing old Actions logs are not treated as missing
  scientific artifacts unless a claim specifically depended on them.

## Reproduction-method correction discovered by the audit

The first broad M095–M112 replay matrix was intentionally kept when it failed. It had checked every
historical result from the **current** repository checkout. That is not a valid reproduction context
for milestones whose frozen predicates include exact source-byte or runtime bindings.

The failure pattern diagnosed the mistake rather than contradicting the old results:

- M096 and M097 recomputed negative only because P1 detected that their mechanism files had moved
  after their historical freezes;
- M101 likewise detected later source/result movement in predicates designed to make such movement
  fatal;
- M104 failed closed on its canonical-runtime check because its protocol binds CPython 3.11.16 and
  SQLite 3.53.1, while a contemporary hosted runner did not provide that exact pair by default;
- M102 was called with a nonexistent `--no-write` option by the first audit workflow; its actual
  read-only invocation is simply the checker without `--write`;
- M105–M109 include checker-attempt/exclusive-create semantics, so invoking their historical
  checkers while a preserved `CHECK_REPORT.json` is present exercises the refusal path rather than
  the original replay path.

None of those failures is counted as a failed reproduction of the scientific result. They are
counted as a **failed reproduction procedure** and are preserved as such.

The corrected matrix now materializes a disposable detached worktree at each result's own
preservation tag (M095 uses result-preservation commit `47c6938…` because it predates the tag
convention), restores the exact CPython/SQLite runtime where required, and removes a canonical
checker report only from the disposable worktree when that is necessary to exercise an
exclusive-create replay. The committed canonical report and all Git history remain untouched.

## Non-goals

This audit will not:

- reinterpret a frozen historical verdict after seeing the outcome;
- turn DEVELOPMENT evidence into canonical evidence;
- claim independence when the same authored bank or mechanism is being replayed;
- replace an independent human maintainer with an AI-generated bank and keep the original claim;
- merge audit changes into `main` without a reviewed reason to do so.
